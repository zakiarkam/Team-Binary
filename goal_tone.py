"""
Train, select, save, and use campaign-goal and tone classifiers.

Models compared independently for each target:

1. TF-IDF + balanced Logistic Regression.
2. Sentence-BERT embeddings + XGBoost.

The best model is selected using weighted F1.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)

from sklearn.linear_model import (
    LogisticRegression,
)

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
)

from sklearn.model_selection import (
    train_test_split,
)

from sklearn.pipeline import (
    Pipeline,
)

from sklearn.preprocessing import (
    LabelEncoder,
)

from xgboost import (
    XGBClassifier,
)


import config

from models import (
    get_semantic_model,
)


TEXT_COLUMN = "text"

GOAL_COLUMN = "campaign_goal"

TONE_COLUMN = "tone"

RANDOM_STATE = 42


def load_labeled_dataset() -> pd.DataFrame:
    """
    Load the high-confidence goal and tone training dataset.
    """

    dataset_path = (
        config
        .GOAL_TONE_TRAINING_DATASET
    )

    if not dataset_path.exists():

        raise FileNotFoundError(
            "Goal and tone training dataset was not found:\n"
            f"{dataset_path}\n\n"
            "Run these scripts first:\n"
            "python -m dataset.preprocess_marketing\n"
            "python -m dataset.label_campaign_goal\n"
            "python -m dataset.label_tone\n"
            "python -m dataset.build_final_dataset"
        )

    dataframe = pd.read_csv(
        dataset_path,
    )

    required_columns = {
        TEXT_COLUMN,
        GOAL_COLUMN,
        TONE_COLUMN,
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:

        raise ValueError(
            "Training dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    dataframe[
        TEXT_COLUMN
    ] = (
        dataframe[
            TEXT_COLUMN
        ]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe[
        GOAL_COLUMN
    ] = (
        dataframe[
            GOAL_COLUMN
        ]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    dataframe[
        TONE_COLUMN
    ] = (
        dataframe[
            TONE_COLUMN
        ]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    dataframe = dataframe[
        dataframe[
            TEXT_COLUMN
        ].str.len() >= 10
    ]

    dataframe = dataframe[
        (
            dataframe[
                GOAL_COLUMN
            ]
            != ""
        )
        &
        (
            dataframe[
                TONE_COLUMN
            ]
            != ""
        )
    ]

    dataframe = (
        dataframe
        .drop_duplicates(
            subset=[
                TEXT_COLUMN,
            ]
        )
        .reset_index(
            drop=True,
        )
    )

    for target_column in (
        GOAL_COLUMN,
        TONE_COLUMN,
    ):

        counts = dataframe[
            target_column
        ].value_counts()

        small_classes = counts[
            counts < 2
        ]

        if not small_classes.empty:

            print(
                f"Warning: dropping {target_column} classes with fewer "
                "than two training rows (stratified train/test splitting "
                f"needs at least two): {small_classes.to_dict()}"
            )

            dataframe = dataframe[
                ~dataframe[target_column].isin(
                    small_classes.index,
                )
            ].reset_index(
                drop=True,
            )

    if dataframe.empty:

        raise ValueError(
            "No training rows remain after dropping sparse goal/tone "
            "classes. Lower the confidence thresholds in "
            "dataset/build_final_dataset.py or gather more labeled data."
        )

    print(
        "Loaded goal/tone training rows: "
        f"{len(dataframe)}"
    )

    return dataframe


def create_tfidf_pipeline() -> Pipeline:
    """
    Build the TF-IDF Logistic Regression pipeline.
    """

    pipeline_model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=20_000,
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                    stop_words="english",
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2_000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )

    return pipeline_model


def create_xgboost_classifier(
    number_of_classes: int,
) -> XGBClassifier:
    """
    Build the Sentence-BERT embedding classifier.
    """

    classifier = XGBClassifier(
        objective="multi:softprob",
        num_class=number_of_classes,
        n_estimators=350,
        learning_rate=0.05,
        max_depth=5,
        min_child_weight=2,
        subsample=0.90,
        colsample_bytree=0.90,
        reg_lambda=1.0,
        eval_metric="mlogloss",
        random_state=RANDOM_STATE,
        # Single-threaded on purpose: XGBoost's OpenMP thread pool clashes with
        # torch's on macOS and segfaults when fit runs after torch is loaded.
        n_jobs=1,
    )

    return classifier


def create_split_indexes(
    labels,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:
    """
    Create consistent stratified train and test indexes.
    """

    labels_array = np.asarray(
        labels,
    )

    indexes = np.arange(
        len(labels_array),
    )

    number_of_classes = len(
        np.unique(
            labels_array,
        )
    )

    test_rows = max(
        int(
            round(
                len(indexes)
                * 0.20
            )
        ),
        number_of_classes,
    )

    remaining_training_rows = (
        len(indexes)
        - test_rows
    )

    if test_rows >= len(indexes):

        raise ValueError(
            "The dataset is too small for train/test splitting."
        )

    if (
        remaining_training_rows
        < number_of_classes
    ):

        raise ValueError(
            "The training split would contain fewer rows "
            "than the number of classes."
        )

    train_indexes, test_indexes = train_test_split(
        indexes,
        test_size=test_rows,
        random_state=RANDOM_STATE,
        stratify=labels_array,
    )

    return (
        train_indexes,
        test_indexes,
    )


def calculate_metrics(
    y_true,
    y_pred,
    model_name: str,
    target_name: str,
) -> dict:
    """
    Calculate research evaluation metrics.
    """

    report = classification_report(
        y_true,
        y_pred,
        output_dict=True,
        zero_division=0,
    )

    accuracy = accuracy_score(
        y_true,
        y_pred,
    )

    weighted_f1 = f1_score(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0,
    )

    macro_f1 = f1_score(
        y_true,
        y_pred,
        average="macro",
        zero_division=0,
    )

    return {
        "target": target_name,
        "model": model_name,
        "accuracy": round(
            float(accuracy),
            6,
        ),
        "weighted_f1": round(
            float(weighted_f1),
            6,
        ),
        "macro_f1": round(
            float(macro_f1),
            6,
        ),
        "classification_report": report,
    }


def remove_file_if_exists(
    path: Path,
) -> None:
    """
    Remove an old artifact that is no longer needed.
    """

    if path.exists():
        path.unlink()


def train() -> dict[str, str]:
    """
    Train both model types and select the best model for each target.
    """

    config.init_dirs()

    dataframe = load_labeled_dataset()

    texts = dataframe[
        TEXT_COLUMN
    ].tolist()

    skip_xgboost = config.GOAL_TONE_SKIP_XGBOOST

    embeddings = None

    if skip_xgboost:

        print(
            "GOAL_TONE_SKIP_XGBOOST is set — training TF-IDF + Logistic "
            "Regression only, skipping Sentence-BERT + XGBoost."
        )

    else:

        print("Loading Sentence-BERT...")

        semantic_model = get_semantic_model()

        print("Creating Sentence-BERT embeddings...")

        embeddings = np.asarray(
            semantic_model.encode(
                texts,
                show_progress_bar=True,
                batch_size=32,
                normalize_embeddings=True,
            ),
            dtype=np.float32,
        )

    metric_results = []

    trained_models = {}

    target_definitions = [
        (
            GOAL_COLUMN,
            "goal",
        ),
        (
            TONE_COLUMN,
            "tone",
        ),
    ]

    for target_column, model_prefix in target_definitions:

        print(
            f"\nTraining models for {target_column}..."
        )

        target_labels = dataframe[
            target_column
        ].to_numpy()

        train_indexes, test_indexes = (
            create_split_indexes(
                target_labels,
            )
        )

        # ---------------------------------------------------------
        # TF-IDF + Logistic Regression
        # ---------------------------------------------------------

        tfidf_model = (
            create_tfidf_pipeline()
        )

        print("1")
        tfidf_model.fit(
            dataframe.iloc[
                train_indexes
            ][TEXT_COLUMN],
            target_labels[
                train_indexes
            ],
        )
        print("2")
        print("3")

        tfidf_predictions = (
            tfidf_model.predict(
                dataframe.iloc[
                    test_indexes
                ][TEXT_COLUMN]
            )
        )
        print("4")

        tfidf_metrics = (
            calculate_metrics(
                target_labels[
                    test_indexes
                ],
                tfidf_predictions,
                "tfidf_logistic",
                target_column,
            )
        )

        metric_results.append(
            tfidf_metrics,
        )

        trained_models[
            f"{model_prefix}_tfidf"
        ] = tfidf_model

        if skip_xgboost:
            continue

        # ---------------------------------------------------------
        # Sentence-BERT + XGBoost
        # ---------------------------------------------------------

        label_encoder = (
            LabelEncoder()
        )

        encoded_labels = (
            label_encoder
            .fit_transform(
                target_labels,
            )
        )

        xgboost_model = (
            create_xgboost_classifier(
                number_of_classes=len(
                    label_encoder.classes_
                ),
            )
        )
        print("5")

        print(embeddings.shape)
        print(embeddings.dtype)
        print(encoded_labels.shape)
        print(encoded_labels.dtype)
        xgboost_model.fit(
            embeddings[
                train_indexes
            ],
            encoded_labels[
                train_indexes
            ],
        )
        print("6")

        encoded_predictions = (
            xgboost_model
            .predict(
                embeddings[
                    test_indexes
                ]
            )
            .astype(int)
        )

        xgboost_predictions = (
            label_encoder
            .inverse_transform(
                encoded_predictions,
            )
        )

        xgboost_metrics = (
            calculate_metrics(
                target_labels[
                    test_indexes
                ],
                xgboost_predictions,
                "sentencebert_xgboost",
                target_column,
            )
        )

        metric_results.append(
            xgboost_metrics,
        )

        trained_models[
            f"{model_prefix}_xgboost"
        ] = xgboost_model

        trained_models[
            f"{model_prefix}_encoder"
        ] = label_encoder

    printable_results = []

    for metric in metric_results:

        printable_results.append(
            {
                key: value
                for key, value
                in metric.items()
                if key
                != "classification_report"
            }
        )

    results_dataframe = pd.DataFrame(
        printable_results,
    )

    print(
        "\nModel evaluation:"
    )

    print(
        results_dataframe.to_string(
            index=False,
        )
    )

    goal_results = [
        result
        for result in metric_results
        if result["target"]
        == GOAL_COLUMN
    ]

    tone_results = [
        result
        for result in metric_results
        if result["target"]
        == TONE_COLUMN
    ]

    best_goal_result = max(
        goal_results,
        key=lambda result: (
            result["weighted_f1"],
            result["macro_f1"],
        ),
    )

    best_tone_result = max(
        tone_results,
        key=lambda result: (
            result["weighted_f1"],
            result["macro_f1"],
        ),
    )

    # -------------------------------------------------------------
    # Save campaign-goal model
    # -------------------------------------------------------------

    if (
        best_goal_result["model"]
        == "sentencebert_xgboost"
    ):

        joblib.dump(
            trained_models[
                "goal_xgboost"
            ],
            config.GOAL_MODEL_PKL,
        )

        joblib.dump(
            trained_models[
                "goal_encoder"
            ],
            config.GOAL_ENCODER_PKL,
        )

    else:

        joblib.dump(
            trained_models[
                "goal_tfidf"
            ],
            config.GOAL_MODEL_PKL,
        )

        remove_file_if_exists(
            config.GOAL_ENCODER_PKL,
        )

    # -------------------------------------------------------------
    # Save tone model
    # -------------------------------------------------------------

    if (
        best_tone_result["model"]
        == "sentencebert_xgboost"
    ):

        joblib.dump(
            trained_models[
                "tone_xgboost"
            ],
            config.TONE_MODEL_PKL,
        )

        joblib.dump(
            trained_models[
                "tone_encoder"
            ],
            config.TONE_ENCODER_PKL,
        )

    else:

        joblib.dump(
            trained_models[
                "tone_tfidf"
            ],
            config.TONE_MODEL_PKL,
        )

        remove_file_if_exists(
            config.TONE_ENCODER_PKL,
        )

    selection = {
        "best_goal_model_type": (
            best_goal_result[
                "model"
            ]
        ),
        "best_tone_model_type": (
            best_tone_result[
                "model"
            ]
        ),
    }

    with open(
        config.GOAL_TONE_SELECTION_JSON,
        "w",
        encoding="utf-8",
    ) as selection_file:

        json.dump(
            selection,
            selection_file,
            indent=2,
        )

    metrics_artifact = {
        "dataset_path": str(
            config
            .GOAL_TONE_TRAINING_DATASET
        ),
        "dataset_rows": int(
            len(dataframe),
        ),
        "selection": selection,
        "results": metric_results,
    }

    with open(
        config.GOAL_TONE_METRICS_JSON,
        "w",
        encoding="utf-8",
    ) as metrics_file:

        json.dump(
            metrics_artifact,
            metrics_file,
            indent=2,
        )

    print(
        "\nSelected campaign-goal model: "
        f"{selection['best_goal_model_type']}"
    )

    print(
        "Selected tone model: "
        f"{selection['best_tone_model_type']}"
    )

    print(
        "Model selection saved to: "
        f"{config.GOAL_TONE_SELECTION_JSON}"
    )

    print(
        "Training metrics saved to: "
        f"{config.GOAL_TONE_METRICS_JSON}"
    )

    return selection


def predict_one(
    text: str,
    model_path: Path,
    model_type: str,
    encoder_path: Path | None = None,
) -> str:
    """
    Predict one label using a selected model.
    """

    model = joblib.load(
        model_path,
    )

    if model_type == "tfidf_logistic":

        prediction = model.predict(
            [
                text,
            ]
        )[0]

        return str(
            prediction,
        )

    if model_type != "sentencebert_xgboost":

        raise ValueError(
            f"Unknown model type: {model_type}"
        )

    if (
        encoder_path is None
        or not encoder_path.exists()
    ):

        raise FileNotFoundError(
            f"Missing label encoder: {encoder_path}"
        )

    label_encoder = joblib.load(
        encoder_path,
    )

    semantic_model = (
        get_semantic_model()
    )

    embedding = semantic_model.encode(
        [
            text,
        ],
        normalize_embeddings=True,
    )

    embedding = np.asarray(
        embedding,
        dtype=np.float32,
    )

    encoded_prediction = (
        model.predict(
            embedding,
        )
        .astype(int)
    )

    decoded_prediction = (
        label_encoder
        .inverse_transform(
            encoded_prediction,
        )[0]
    )

    return str(
        decoded_prediction,
    )


def predict(
    marketing_kb: dict,
    module_input: dict,
) -> tuple[
    dict,
    dict,
]:
    """
    Predict campaign goal and tone for the current knowledge base.
    """

    required_artifacts = [
        config.GOAL_TONE_SELECTION_JSON,
        config.GOAL_MODEL_PKL,
        config.TONE_MODEL_PKL,
    ]

    artifacts_exist = all(
        path.exists()
        for path in required_artifacts
    )

    if not artifacts_exist:

        print(
            "Goal/tone models are missing. "
            "Training models now..."
        )

        train()

    with open(
        config.GOAL_TONE_SELECTION_JSON,
        encoding="utf-8",
    ) as selection_file:

        selection = json.load(
            selection_file,
        )

    text = str(
        marketing_kb.get(
            "combined_text",
            "",
        )
    ).strip()

    if not text:

        raise ValueError(
            "marketing_kb['combined_text'] is empty."
        )

    goal_model_type = selection[
        "best_goal_model_type"
    ]

    tone_model_type = selection[
        "best_tone_model_type"
    ]

    campaign_goal = predict_one(
        text=text,
        model_path=config.GOAL_MODEL_PKL,
        model_type=goal_model_type,
        encoder_path=(
            config.GOAL_ENCODER_PKL
            if goal_model_type
            == "sentencebert_xgboost"
            else None
        ),
    )

    tone = predict_one(
        text=text,
        model_path=config.TONE_MODEL_PKL,
        model_type=tone_model_type,
        encoder_path=(
            config.TONE_ENCODER_PKL
            if tone_model_type
            == "sentencebert_xgboost"
            else None
        ),
    )

    module_input[
        "campaign_goal"
    ] = campaign_goal

    module_input[
        "tone"
    ] = tone

    marketing_kb[
        "module_input"
    ] = module_input

    print(
        f"Predicted goal={campaign_goal} | "
        f"tone={tone}"
    )

    return (
        module_input,
        marketing_kb,
    )


if __name__ == "__main__":
    train()