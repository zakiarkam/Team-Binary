"""
Download and preprocess RafaM97/marketing_social_media.

The output contains:

- row_id
- instruction
- raw_input
- goal_text
- business_context
- summary
- text

BART summarization is optional. Without --summarize, the cleaned
business context is placed in the summary column.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from datasets import load_dataset


# Allow imports from the project root when this script is executed directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


import config  # noqa: E402


DATASET_NAME = "RafaM97/marketing_social_media"

REQUIRED_COLUMNS = {
    "instruction",
    "input",
    "response",
}


def clean_text(value: object) -> str:
    """
    Normalize whitespace and safely convert a value to text.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = str(value)

    text = text.replace(
        "\u00a0",
        " ",
    )

    text = re.sub(
        r"[\t\r\n]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s{2,}",
        " ",
        text,
    )

    return text.strip()


def extract_goal_text(
    raw_input: str,
) -> str:
    """
    Extract an explicit Goals or Objective field.

    Example input:

    Company: ABC
    Target: Students
    Goals: Increase sales and brand awareness
    """

    text = clean_text(
        raw_input,
    )

    if not text:
        return ""

    goals_match = re.search(
        (
            r"(?is)"
            r"\bgoals?\s*:\s*"
            r"(.+?)"
            r"(?="
            r"\s+(?:"
            r"tone|platform|format|output|requirements?|constraints?|"
            r"company|target|audience|product|service"
            r")\s*:"
            r"|$"
            r")"
        ),
        text,
    )

    if goals_match:
        return clean_text(
            goals_match.group(1),
        )

    objective_match = re.search(
        (
            r"(?is)"
            r"\b(?:objective|campaign objective)\s*:\s*"
            r"(.+?)"
            r"(?="
            r"\s+[A-Z][A-Za-z ]{2,25}\s*:"
            r"|$"
            r")"
        ),
        text,
    )

    if objective_match:
        return clean_text(
            objective_match.group(1),
        )

    return ""


def remove_goal_section(
    raw_input: str,
) -> str:
    """
    Remove the explicit Goals field from the business context.
    """

    text = clean_text(
        raw_input,
    )

    if not text:
        return ""

    cleaned = re.sub(
        (
            r"(?is)"
            r"\bgoals?\s*:\s*"
            r".+?"
            r"(?="
            r"\s+(?:"
            r"tone|platform|format|output|requirements?|constraints?"
            r")\s*:"
            r"|$"
            r")"
        ),
        " ",
        text,
    )

    return clean_text(
        cleaned,
    )


def summarize_context(
    text: str,
    summarizer,
) -> str:
    """
    Summarize longer business context using BART.
    """

    text = clean_text(
        text,
    )

    words = text.split()

    if len(words) < 35:
        return text

    # Limit the input size before giving it to BART.
    clipped_text = " ".join(
        words[:700],
    )

    try:
        output = summarizer(
            clipped_text,
            max_length=80,
            min_length=20,
            do_sample=False,
            truncation=True,
        )

        summary = output[0][
            "summary_text"
        ]

        return clean_text(
            summary,
        )

    except Exception as exc:
        print(
            f"BART summary warning: {exc}"
        )

        return clipped_text


def load_source_dataset() -> pd.DataFrame:
    """
    Download the Hugging Face dataset.
    """

    print(
        f"Loading dataset: {DATASET_NAME}"
    )

    dataset = load_dataset(
        DATASET_NAME,
    )

    if "train" in dataset:
        split_name = "train"
    else:
        split_name = next(
            iter(dataset.keys())
        )

    dataframe = dataset[
        split_name
    ].to_pandas()

    missing_columns = (
        REQUIRED_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "RafaM97 dataset is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    return dataframe


def preprocess(
    use_bart_summary: bool = False,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Create and save the cleaned preprocessing dataset.
    """

    config.init_dirs()

    dataframe = load_source_dataset()

    if limit is not None:
        dataframe = dataframe.head(
            limit,
        ).copy()

    raw = dataframe.loc[
        :,
        [
            "instruction",
            "input",
            "response",
        ],
    ].copy()

    raw.columns = [
        "instruction",
        "raw_input",
        "text",
    ]

    for column in (
        "instruction",
        "raw_input",
        "text",
    ):
        raw[column] = raw[
            column
        ].map(
            clean_text,
        )

    # Remove unusable marketing responses.
    raw = raw[
        raw["text"].str.len() >= 10
    ].copy()

    # Remove exact duplicate examples.
    raw = raw.drop_duplicates(
        subset=[
            "instruction",
            "raw_input",
            "text",
        ],
    )

    raw = raw.reset_index(
        drop=True,
    )

    # Stable identifier used for merging goal and tone outputs.
    raw.insert(
        0,
        "row_id",
        range(len(raw)),
    )

    # Save a reproducible local snapshot.
    raw.to_csv(
        config.RAW_MARKETING_DATASET,
        index=False,
    )

    raw["goal_text"] = raw[
        "raw_input"
    ].map(
        extract_goal_text,
    )

    raw["business_context"] = raw[
        "raw_input"
    ].map(
        remove_goal_section,
    )

    if use_bart_summary:

        from models import get_summarizer

        print(
            "Loading BART summarizer..."
        )

        summarizer = get_summarizer()

        raw["summary"] = raw[
            "business_context"
        ].map(
            lambda value: summarize_context(
                value,
                summarizer,
            )
        )

    else:

        raw["summary"] = raw[
            "business_context"
        ]

    output_columns = [
        "row_id",
        "instruction",
        "raw_input",
        "goal_text",
        "business_context",
        "summary",
        "text",
    ]

    processed = raw.loc[
        :,
        output_columns,
    ].copy()

    processed.to_csv(
        config.PREPROCESSED_MARKETING_DATASET,
        index=False,
    )

    extracted_goal_count = int(
        (
            processed["goal_text"]
            != ""
        ).sum()
    )

    print(
        f"Preprocessed rows: {len(processed)}"
    )

    print(
        "Raw dataset saved to: "
        f"{config.RAW_MARKETING_DATASET}"
    )

    print(
        "Preprocessed dataset saved to: "
        f"{config.PREPROCESSED_MARKETING_DATASET}"
    )

    print(
        "Rows with extracted Goals fields: "
        f"{extracted_goal_count}"
    )

    return processed


def parse_args() -> argparse.Namespace:
    """
    Read terminal arguments.
    """

    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--summarize",
        action="store_true",
        help=(
            "Use facebook/bart-large-cnn "
            "to summarize the business context."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Process only the first N rows. "
            "Useful for testing."
        ),
    )

    return parser.parse_args()



def run():
    arguments = parse_args()

    preprocess(
        use_bart_summary=arguments.summarize,
        limit=arguments.limit,
    )

if __name__ == "__main__":
    run()