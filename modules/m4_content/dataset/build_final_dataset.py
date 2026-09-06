"""
Merge campaign-goal and tone labels.

Creates:

1. A complete research dataset containing audit columns.
2. A filtered training dataset containing high-confidence labels.
3. A JSON file containing label statistics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


import config  # noqa: E402


GOAL_LABELS = {
    "awareness",
    "conversion",
    "engagement",
    "lead_generation",
    "retention",
}


TONE_LABELS = {
    "friendly",
    "professional",
    "luxury",
    "emotional",
    "persuasive",
    "humorous",
}


BASE_COLUMNS = [
    "row_id",
    "instruction",
    "raw_input",
    "goal_text",
    "business_context",
    "summary",
    "text",
]


GOAL_AUDIT_COLUMNS = [
    "campaign_goal_rule",
    "campaign_goal_rule_confidence",
    "campaign_goal_rule_matches",
    "campaign_goal_zero_shot",
    "campaign_goal_zero_shot_confidence",
    "campaign_goal_second_choice",
    "campaign_goal_second_choice_confidence",
    "campaign_goal_phi3",
    "campaign_goal",
    "campaign_goal_confidence",
    "campaign_goal_agreement",
    "campaign_goal_source",
    "campaign_goal_needs_review",
]


TONE_AUDIT_COLUMNS = [
    "tone_rule",
    "tone_rule_confidence",
    "tone_rule_matches",
    "tone_zero_shot",
    "tone_zero_shot_confidence",
    "tone_second_choice",
    "tone_second_choice_confidence",
    "tone_phi3",
    "tone",
    "tone_confidence",
    "tone_agreement",
    "tone_source",
    "tone_needs_review",
]


def normalize_boolean(
    series: pd.Series,
) -> pd.Series:
    """
    Convert CSV boolean strings into Python booleans.
    """

    return series.map(
        lambda value: (
            str(value)
            .strip()
            .lower()
            in {
                "true",
                "1",
                "yes",
            }
        )
    )


def validate_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    """
    Validate that a dataset contains required columns.
    """

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing columns: "
            f"{sorted(missing_columns)}"
        )


def build(
    goal_path: Path,
    tone_path: Path,
    research_path: Path,
    training_path: Path,
    min_goal_confidence: float = 0.65,
    min_tone_confidence: float = 0.62,
    keep_review_rows: bool = False,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Merge labels and generate research/training files.
    """

    config.init_dirs()

    if not goal_path.exists():
        raise FileNotFoundError(
            f"Goal dataset not found: {goal_path}"
        )

    if not tone_path.exists():
        raise FileNotFoundError(
            f"Tone dataset not found: {tone_path}"
        )

    goal_dataframe = pd.read_csv(
        goal_path,
    )

    tone_dataframe = pd.read_csv(
        tone_path,
    )

    validate_columns(
        goal_dataframe,
        set(
            BASE_COLUMNS
            + GOAL_AUDIT_COLUMNS
        ),
        "Campaign-goal dataset",
    )

    validate_columns(
        tone_dataframe,
        {
            "row_id",
            *TONE_AUDIT_COLUMNS,
        },
        "Tone dataset",
    )

    # The campaign-goal dataset provides the original source columns.
    goal_part = goal_dataframe.loc[
        :,
        BASE_COLUMNS
        + GOAL_AUDIT_COLUMNS,
    ].copy()

    tone_part = tone_dataframe.loc[
        :,
        [
            "row_id",
            *TONE_AUDIT_COLUMNS,
        ],
    ].copy()

    research_dataframe = goal_part.merge(
        tone_part,
        on="row_id",
        how="inner",
        validate="one_to_one",
    )

    research_dataframe[
        "campaign_goal"
    ] = (
        research_dataframe[
            "campaign_goal"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    research_dataframe[
        "tone"
    ] = (
        research_dataframe[
            "tone"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    research_dataframe[
        "campaign_goal_needs_review"
    ] = normalize_boolean(
        research_dataframe[
            "campaign_goal_needs_review"
        ]
    )

    research_dataframe[
        "tone_needs_review"
    ] = normalize_boolean(
        research_dataframe[
            "tone_needs_review"
        ]
    )

    research_dataframe[
        "needs_review"
    ] = (
        research_dataframe[
            "campaign_goal_needs_review"
        ]
        |
        research_dataframe[
            "tone_needs_review"
        ]
    )

    research_dataframe[
        "joint_label_confidence"
    ] = (
        research_dataframe[
            "campaign_goal_confidence"
        ].astype(float)
        *
        research_dataframe[
            "tone_confidence"
        ].astype(float)
    ) ** 0.5

    research_dataframe[
        "labeling_method"
    ] = (
        "rule_bart_mnli_phi3_ensemble"
    )

    valid_goal_mask = (
        research_dataframe[
            "campaign_goal"
        ].isin(
            GOAL_LABELS,
        )
    )

    valid_tone_mask = (
        research_dataframe[
            "tone"
        ].isin(
            TONE_LABELS,
        )
    )

    research_dataframe[
        "valid_label_pair"
    ] = (
        valid_goal_mask
        & valid_tone_mask
    )

    research_dataframe = (
        research_dataframe
        .sort_values(
            "row_id",
        )
        .reset_index(
            drop=True,
        )
    )

    research_dataframe.to_csv(
        research_path,
        index=False,
    )

    training_mask = (
        research_dataframe[
            "valid_label_pair"
        ]
        &
        research_dataframe[
            "text"
        ]
        .fillna("")
        .astype(str)
        .str.len()
        .ge(10)
        &
        research_dataframe[
            "campaign_goal_confidence"
        ]
        .astype(float)
        .ge(
            min_goal_confidence,
        )
        &
        research_dataframe[
            "tone_confidence"
        ]
        .astype(float)
        .ge(
            min_tone_confidence,
        )
    )

    if not keep_review_rows:

        training_mask = (
            training_mask
            &
            ~research_dataframe[
                "needs_review"
            ]
        )

    training_dataframe = (
        research_dataframe.loc[
            training_mask,
            [
                "row_id",
                "text",
                "campaign_goal",
                "tone",
                "joint_label_confidence",
            ],
        ]
        .copy()
    )

    training_dataframe = (
        training_dataframe
        .drop_duplicates(
            subset=[
                "text",
            ]
        )
        .reset_index(
            drop=True,
        )
    )

    training_dataframe.to_csv(
        training_path,
        index=False,
    )

    statistics = {
        "research_rows": int(
            len(
                research_dataframe,
            )
        ),
        "training_rows": int(
            len(
                training_dataframe,
            )
        ),
        "excluded_rows": int(
            len(
                research_dataframe,
            )
            -
            len(
                training_dataframe,
            )
        ),
        "needs_review_rows": int(
            research_dataframe[
                "needs_review"
            ].sum()
        ),
        "minimum_goal_confidence": (
            min_goal_confidence
        ),
        "minimum_tone_confidence": (
            min_tone_confidence
        ),
        "campaign_goal_distribution": (
            training_dataframe[
                "campaign_goal"
            ]
            .value_counts()
            .to_dict()
        ),
        "tone_distribution": (
            training_dataframe[
                "tone"
            ]
            .value_counts()
            .to_dict()
        ),
        "mean_joint_label_confidence": (
            round(
                float(
                    training_dataframe[
                        "joint_label_confidence"
                    ].mean()
                ),
                4,
            )
            if len(training_dataframe)
            else 0.0
        ),
    }

    with open(
        config.GOAL_TONE_LABEL_STATISTICS_JSON,
        "w",
        encoding="utf-8",
    ) as statistics_file:

        json.dump(
            statistics,
            statistics_file,
            indent=2,
        )

    print(
        "Research dataset saved to: "
        f"{research_path}"
    )

    print(
        "Research rows: "
        f"{len(research_dataframe)}"
    )

    print(
        "\nTraining dataset saved to: "
        f"{training_path}"
    )

    print(
        "Training rows: "
        f"{len(training_dataframe)}"
    )

    print(
        "\nCampaign-goal distribution:"
    )

    print(
        training_dataframe[
            "campaign_goal"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nTone distribution:"
    )

    print(
        training_dataframe[
            "tone"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nStatistics saved to: "
        f"{config.GOAL_TONE_LABEL_STATISTICS_JSON}"
    )

    return (
        research_dataframe,
        training_dataframe,
    )


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    """
    Read terminal arguments.
    """

    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--goal-input",
        type=Path,
        default=(
            config
            .GOAL_LABELED_DATASET
        ),
    )

    parser.add_argument(
        "--tone-input",
        type=Path,
        default=(
            config
            .TONE_LABELED_DATASET
        ),
    )

    parser.add_argument(
        "--research-output",
        type=Path,
        default=(
            config
            .GOAL_TONE_RESEARCH_DATASET
        ),
    )

    parser.add_argument(
        "--training-output",
        type=Path,
        default=(
            config
            .GOAL_TONE_TRAINING_DATASET
        ),
    )

    parser.add_argument(
        "--min-goal-confidence",
        type=float,
        default=0.65,
    )

    parser.add_argument(
        "--min-tone-confidence",
        type=float,
        default=0.62,
    )

    parser.add_argument(
        "--keep-review-rows",
        action="store_true",
    )

    return parser.parse_args(argv)



def run(argv: list[str] | None = None):
    arguments = parse_args(argv)

    build(
        goal_path=arguments.goal_input,
        tone_path=arguments.tone_input,
        research_path=arguments.research_output,
        training_path=arguments.training_output,
        min_goal_confidence=(
            arguments
            .min_goal_confidence
        ),
        min_tone_confidence=(
            arguments
            .min_tone_confidence
        ),
        keep_review_rows=(
            arguments
            .keep_review_rows
        ),
    )

if __name__ == "__main__":
    run()