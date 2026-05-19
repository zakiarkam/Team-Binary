"""Train TF-IDF and SentenceBERT+XGBoost classifiers for campaign goal and tone,
select the best by weighted F1, predict for the current knowledge base."""

import json
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

import config
from models import get_semantic_model

TEXT_COLUMN = "text"
GOAL_COLUMN = "campaign_goal"
TONE_COLUMN = "tone"


def _load_labeled() -> pd.DataFrame:
    df = pd.read_csv(config.LABELED_DATASET_CSV)
    for col in (TEXT_COLUMN, GOAL_COLUMN, TONE_COLUMN):
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    df[TEXT_COLUMN] = df[TEXT_COLUMN].fillna("").astype(str)
    df[GOAL_COLUMN] = df[GOAL_COLUMN].fillna("").astype(str).str.lower().str.strip()
    df[TONE_COLUMN] = df[TONE_COLUMN].fillna("").astype(str).str.lower().str.strip()
    df = df[df[TEXT_COLUMN].str.len() > 5]
    df = df[df[GOAL_COLUMN].str.len() > 0]
    df = df[df[TONE_COLUMN].str.len() > 0]
    return df


def _tfidf_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2), stop_words="english")),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def _xgb_classifier() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=5, eval_metric="mlogloss", random_state=42
    )


def _evaluate(y_true, y_pred, model_name: str, target_name: str) -> dict:
    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    return {
        "target": target_name,
        "model": model_name,
        "accuracy": accuracy_score(y_true, y_pred),
        "weighted_f1": report["weighted avg"]["f1-score"],
    }


def train() -> dict:
    df = _load_labeled()
    embedder = get_semantic_model()
    embeddings = embedder.encode(df[TEXT_COLUMN].tolist(), show_progress_bar=True)

    results = []
    artifacts = {}

    # --- Campaign goal ---
    X_tr, X_te, y_tr, y_te = train_test_split(
        df[TEXT_COLUMN], df[GOAL_COLUMN], test_size=0.2, random_state=42, stratify=df[GOAL_COLUMN]
    )
    tfidf_goal = _tfidf_pipeline().fit(X_tr, y_tr)
    results.append(_evaluate(y_te, tfidf_goal.predict(X_te), "TF-IDF + LogisticRegression", "campaign_goal"))

    goal_enc = LabelEncoder()
    y_goal = goal_enc.fit_transform(df[GOAL_COLUMN])
    X_tr, X_te, y_tr, y_te = train_test_split(
        embeddings, y_goal, test_size=0.2, random_state=42, stratify=y_goal
    )
    xgb_goal = _xgb_classifier().fit(X_tr, y_tr)
    results.append(
        _evaluate(
            goal_enc.inverse_transform(y_te),
            goal_enc.inverse_transform(xgb_goal.predict(X_te)),
            "SentenceBERT + XGBoost",
            "campaign_goal",
        )
    )

    # --- Tone ---
    X_tr, X_te, y_tr, y_te = train_test_split(
        df[TEXT_COLUMN], df[TONE_COLUMN], test_size=0.2, random_state=42, stratify=df[TONE_COLUMN]
    )
    tfidf_tone = _tfidf_pipeline().fit(X_tr, y_tr)
    results.append(_evaluate(y_te, tfidf_tone.predict(X_te), "TF-IDF + LogisticRegression", "tone"))

    tone_enc = LabelEncoder()
    y_tone = tone_enc.fit_transform(df[TONE_COLUMN])
    X_tr, X_te, y_tr, y_te = train_test_split(
        embeddings, y_tone, test_size=0.2, random_state=42, stratify=y_tone
    )
    xgb_tone = _xgb_classifier().fit(X_tr, y_tr)
    results.append(
        _evaluate(
            tone_enc.inverse_transform(y_te),
            tone_enc.inverse_transform(xgb_tone.predict(X_te)),
            "SentenceBERT + XGBoost",
            "tone",
        )
    )

    results_df = pd.DataFrame(results)
    print(results_df.to_string())

    # Pick best per target by weighted F1
    best_goal = results_df[results_df["target"] == "campaign_goal"].sort_values("weighted_f1", ascending=False).iloc[0]
    best_tone = results_df[results_df["target"] == "tone"].sort_values("weighted_f1", ascending=False).iloc[0]

    if best_goal["model"] == "SentenceBERT + XGBoost":
        joblib.dump(xgb_goal, config.GOAL_MODEL_PKL)
        joblib.dump(goal_enc, config.GOAL_ENCODER_PKL)
        goal_type = "sentencebert_xgboost"
    else:
        joblib.dump(tfidf_goal, config.GOAL_MODEL_PKL)
        goal_type = "tfidf_logistic"

    if best_tone["model"] == "SentenceBERT + XGBoost":
        joblib.dump(xgb_tone, config.TONE_MODEL_PKL)
        joblib.dump(tone_enc, config.TONE_ENCODER_PKL)
        tone_type = "sentencebert_xgboost"
    else:
        joblib.dump(tfidf_tone, config.TONE_MODEL_PKL)
        tone_type = "tfidf_logistic"

    selection = {"best_goal_model_type": goal_type, "best_tone_model_type": tone_type}
    with open(config.GOAL_TONE_SELECTION_JSON, "w") as f:
        json.dump(selection, f, indent=4)
    print(f"Best goal: {goal_type} | Best tone: {tone_type}")
    return selection


def _predict_one(text: str, model_path, model_type: str, encoder_path=None):
    model = joblib.load(model_path)
    if model_type == "tfidf_logistic":
        return model.predict([text])[0]
    encoder = joblib.load(encoder_path)
    embedding = get_semantic_model().encode([text])
    return encoder.inverse_transform(model.predict(embedding))[0]


def predict(marketing_kb: dict, module_input: dict) -> tuple[dict, dict]:
    """Predicts goal & tone for the current KB and returns updated module_input + kb."""
    if not config.GOAL_TONE_SELECTION_JSON.exists():
        train()
    with open(config.GOAL_TONE_SELECTION_JSON) as f:
        selection = json.load(f)

    text = marketing_kb["combined_text"]
    goal = _predict_one(
        text,
        config.GOAL_MODEL_PKL,
        selection["best_goal_model_type"],
        config.GOAL_ENCODER_PKL if selection["best_goal_model_type"] == "sentencebert_xgboost" else None,
    )
    tone = _predict_one(
        text,
        config.TONE_MODEL_PKL,
        selection["best_tone_model_type"],
        config.TONE_ENCODER_PKL if selection["best_tone_model_type"] == "sentencebert_xgboost" else None,
    )
    module_input["campaign_goal"] = str(goal)
    module_input["tone"] = str(tone)
    marketing_kb["module_input"] = module_input
    print(f"Predicted goal={module_input['campaign_goal']} | tone={module_input['tone']}")
    return module_input, marketing_kb
