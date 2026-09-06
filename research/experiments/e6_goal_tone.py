"""E6 — Campaign goal and tone: does the transformer beat TF-IDF?

Module 4 infers two labels from a product description — the campaign goal and
the tone — and it selects between two very different approaches:

    TF-IDF + balanced logistic regression      sparse, lexical, ~200 KB
    Sentence-BERT embeddings + XGBoost         dense, semantic, ~90 MB

The pipeline picks the winner automatically. This experiment asks whether that
choice is defensible, and reports it the way it has to be read.

**Macro-F1, not accuracy.** `awareness` is 59% of the goal corpus. A model that
predicts `awareness` and nothing else scores 0.59 accuracy while being worthless
for the four other goals — which are precisely the ones a marketer would want
detected. Macro-F1 averages over classes rather than rows, so a model cannot
buy it by getting the majority class right. A majority-class baseline is scored
alongside for exactly this reason.

**McNemar, not a difference of accuracies.** Both models see the same test rows,
so the informative quantity is where they *disagree*. With ~100 test rows an
accuracy gap of several points can easily be a handful of items.

The corpus is small (527 rows, 453 with a goal, 174 with a tone) and badly
imbalanced — `humorous` has a single example and cannot be learned by anything.
That is a finding about the data, and it is reported rather than smoothed over.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import config
from research.stats import mcnemar

ID = "E6"
TITLE = "Module 4 — goal and tone classification, TF-IDF versus Sentence-BERT"

TARGETS = ("campaign_goal", "tone")
MIN_CLASS_FOR_SPLIT = 2


def _tfidf_model():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1,
                                  sublinear_tf=True, stop_words="english")),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])


def _embed(texts: list[str]) -> np.ndarray | None:
    """Sentence-BERT embeddings, or None if the model cannot be loaded.

    Forced offline: sentence-transformers otherwise spends half a minute
    retrying huggingface.co before falling back to the local cache, and a viva
    machine has no reason to be online. If the model was never downloaded the
    load fails fast and this leg is reported as unevaluated rather than
    silently skipped.
    """
    import os

    previous = {k: os.environ.get(k) for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        import models as project_models

        encoder = project_models.get_semantic_model()
        return np.asarray(encoder.encode(texts, show_progress_bar=False))
    except Exception:
        return None
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _per_class(y_true, y_pred, labels) -> list[dict]:
    from sklearn.metrics import f1_score, precision_score, recall_score

    rows = []
    for label in labels:
        mask = np.asarray(y_true) == label
        rows.append({
            "class": label,
            "support": int(mask.sum()),
            "precision": round(float(precision_score(
                y_true, y_pred, labels=[label], average="micro", zero_division=0)), 4),
            "recall": round(float(recall_score(
                y_true, y_pred, labels=[label], average="micro", zero_division=0)), 4),
            "f1": round(float(f1_score(
                y_true, y_pred, labels=[label], average="micro", zero_division=0)), 4),
        })
    return rows


def run() -> dict:
    if not config.__dict__ or not config.M1_DATASET.parent.exists():
        pass  # config import is enough; the real guard is the corpus below

    import config as project_config

    corpus_path = project_config.GOAL_TONE_TRAINING_DATASET
    if not corpus_path.exists():
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": f"goal/tone corpus not found at {corpus_path}"}

    from sklearn.dummy import DummyClassifier
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split
    from xgboost import XGBClassifier

    frame = pd.read_csv(corpus_path)
    summary, per_class, contests, notes = [], [], [], []

    for target in TARGETS:
        if target not in frame:
            notes.append(f"`{target}` column absent from the corpus — skipped.")
            continue

        subset = frame[["text", target]].dropna()
        subset = subset[subset[target].astype(str).str.strip() != ""]
        if len(subset) < 30:
            notes.append(f"`{target}` has only {len(subset)} labelled rows — "
                         "too few to evaluate.")
            continue

        texts = subset["text"].astype(str).tolist()
        labels = subset[target].astype(str).to_numpy()
        counts = pd.Series(labels).value_counts()

        rare = counts[counts < MIN_CLASS_FOR_SPLIT]
        stratify = labels if counts.min() >= MIN_CLASS_FOR_SPLIT else None
        if len(rare):
            notes.append(
                f"`{target}`: {', '.join(rare.index)} "
                f"{'has' if len(rare) == 1 else 'have'} fewer than "
                f"{MIN_CLASS_FOR_SPLIT} examples — cannot be split, cannot be "
                "learned, and cannot be evaluated. Reported, not hidden.")

        idx_train, idx_test = train_test_split(
            np.arange(len(subset)), test_size=0.25,
            random_state=config.SEED, stratify=stratify)

        y_train, y_test = labels[idx_train], labels[idx_test]
        train_texts = [texts[i] for i in idx_train]
        test_texts = [texts[i] for i in idx_test]

        predictions: dict[str, np.ndarray] = {}

        # Majority-class baseline — the number every other model must beat.
        dummy = DummyClassifier(strategy="most_frequent")
        dummy.fit(np.zeros((len(y_train), 1)), y_train)
        predictions["majority baseline"] = dummy.predict(np.zeros((len(y_test), 1)))

        # TF-IDF + logistic regression.
        tfidf = _tfidf_model()
        tfidf.fit(train_texts, y_train)
        predictions["tfidf + logistic"] = tfidf.predict(test_texts)

        # Sentence-BERT + XGBoost.
        embeddings = _embed(texts)
        if embeddings is None:
            notes.append(
                f"`{target}`: Sentence-BERT could not be loaded, so only TF-IDF "
                "was evaluated. The model-selection claim in the report needs "
                "this leg to be reproducible — rerun with the sentence-transformers "
                "cache populated.")
        else:
            codes, classes = pd.factorize(y_train)
            booster = XGBClassifier(
                n_estimators=300, learning_rate=0.1, max_depth=4,
                random_state=config.SEED, n_jobs=1, eval_metric="mlogloss")
            booster.fit(embeddings[idx_train], codes)
            predictions["sbert + xgboost"] = classes[
                booster.predict(embeddings[idx_test])]

        present = sorted(set(y_test))
        for name, y_pred in predictions.items():
            summary.append({
                "target": target,
                "model": name,
                "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
                "macro_f1": round(float(f1_score(
                    y_test, y_pred, average="macro", zero_division=0)), 4),
                "weighted_f1": round(float(f1_score(
                    y_test, y_pred, average="weighted", zero_division=0)), 4),
                "n_train": int(len(y_train)),
                "n_test": int(len(y_test)),
                "n_classes": int(len(set(labels))),
                "majority_class_share": round(float(counts.iloc[0] / len(labels)), 4),
            })
            if name != "majority baseline":
                per_class.extend(
                    {"target": target, "model": name, **row}
                    for row in _per_class(y_test, y_pred, present))

        if "sbert + xgboost" in predictions:
            test = mcnemar(predictions["tfidf + logistic"] == y_test,
                           predictions["sbert + xgboost"] == y_test)
            contests.append({"target": target,
                             "comparison": "tfidf + logistic vs sbert + xgboost",
                             **test})
            if not test["significant"]:
                notes.append(
                    f"`{target}`: the two approaches are statistically "
                    f"indistinguishable on this corpus (McNemar p="
                    f"{test['p_value']:.3f}, {test['n_discordant']} disagreements). "
                    "Choosing TF-IDF is then a decision about cost and "
                    "interpretability, not about accuracy — which is a stronger "
                    "argument than claiming it is more accurate.")

    if not summary:
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": "no target had enough labelled rows"}

    # Did anything actually beat the majority baseline on macro-F1?
    for target in {r["target"] for r in summary}:
        rows = [r for r in summary if r["target"] == target]
        baseline = next(r for r in rows if r["model"] == "majority baseline")
        best = max((r for r in rows if r["model"] != "majority baseline"),
                   key=lambda r: r["macro_f1"])
        notes.append(
            f"`{target}`: best macro-F1 {best['macro_f1']:.3f} ({best['model']}) "
            f"against a majority baseline of {baseline['macro_f1']:.3f}; accuracy "
            f"{best['accuracy']:.3f} against {baseline['accuracy']:.3f}. The "
            "accuracy gap flatters the model far more than the macro-F1 gap does.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "targets": sorted({r["target"] for r in summary}),
            "goal_best_macro_f1": max(
                (r["macro_f1"] for r in summary
                 if r["target"] == "campaign_goal" and r["model"] != "majority baseline"),
                default=None),
            "tone_best_macro_f1": max(
                (r["macro_f1"] for r in summary
                 if r["target"] == "tone" and r["model"] != "majority baseline"),
                default=None),
            "sbert_evaluated": any(r["model"] == "sbert + xgboost" for r in summary),
        },
        "tables": {
            "e6_model_summary": summary,
            "e6_per_class": per_class,
            **({"e6_mcnemar": contests} if contests else {}),
        },
        "notes": notes,
    }
