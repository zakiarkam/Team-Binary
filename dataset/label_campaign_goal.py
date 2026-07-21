"""
Create research-grade campaign-goal pseudo-labels.

Methods:

1. Explicit Goals-field rule classification.
2. BART-MNLI zero-shot classification.
3. Phi-3 verification for uncertain or disagreeing examples.
4. Ensemble decision with confidence and review columns.
"""

from __future__ import annotations

import argparse
import gc
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from transformers import pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


import config  # noqa: E402


GOAL_LABELS = [
    "awareness",
    "conversion",
    "engagement",
    "lead_generation",
    "retention",
]


ZERO_SHOT_CANDIDATES = {
    "awareness": (
        "brand awareness, reach, visibility, recognition, "
        "or product discovery"
    ),
    "conversion": (
        "sales, purchases, bookings, registrations, "
        "subscriptions, or revenue"
    ),
    "engagement": (
        "likes, comments, shares, participation, "
        "conversation, or community interaction"
    ),
    "lead_generation": (
        "collecting leads, inquiries, demos, contact details, "
        "downloads, or newsletter signups"
    ),
    "retention": (
        "customer loyalty, repeat purchase, renewal, "
        "reactivation, or reducing churn"
    ),
}


GOAL_PATTERNS: dict[
    str,
    dict[str, float],
] = {
    "retention": {
        "customer retention": 4.0,
        "reduce churn": 4.0,
        "repeat purchase": 3.5,
        "repeat customer": 3.5,
        "customer loyalty": 3.5,
        "renewal": 3.0,
        "loyalty": 3.0,
        "reactivate": 3.0,
        "re engagement": 3.0,
        "reengage": 3.0,
        "win back": 3.0,
        "existing customers": 2.0,
    },
    "lead_generation": {
        "lead generation": 4.0,
        "generate leads": 4.0,
        "qualified leads": 4.0,
        "book a demo": 3.5,
        "request a demo": 3.5,
        "contact details": 3.5,
        "newsletter signup": 3.0,
        "newsletter subscription": 3.0,
        "sign up for": 2.5,
        "inquiries": 2.5,
        "inquiry": 2.5,
        "download": 2.0,
        "whitepaper": 2.0,
        "webinar registration": 3.0,
    },
    "conversion": {
        "increase sales": 4.0,
        "drive sales": 4.0,
        "increase revenue": 4.0,
        "drive purchases": 4.0,
        "conversion rate": 3.5,
        "purchase": 3.0,
        "buy": 2.5,
        "order": 2.5,
        "checkout": 2.5,
        "booking": 2.5,
        "registration": 2.0,
        "subscribe": 2.0,
        "limited time offer": 2.0,
        "promotion": 1.5,
    },
    "engagement": {
        "increase engagement": 4.0,
        "drive engagement": 4.0,
        "comments": 3.0,
        "shares": 3.0,
        "likes": 2.5,
        "participation": 3.0,
        "community interaction": 3.5,
        "user generated content": 3.5,
        "discussion": 2.5,
        "conversation": 2.0,
        "poll": 2.0,
        "contest": 2.0,
        "challenge": 1.5,
    },
    "awareness": {
        "brand awareness": 4.0,
        "increase awareness": 4.0,
        "brand recognition": 3.5,
        "brand visibility": 3.5,
        "increase reach": 3.5,
        "visibility": 2.5,
        "impressions": 2.5,
        "reach": 2.0,
        "followers": 2.0,
        "website traffic": 2.0,
        "product launch": 2.0,
        "introduce": 1.5,
        "showcase": 1.0,
    },
}


def normalize_text(
    value: object,
) -> str:
    """
    Normalize text for rule matching.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = str(value).lower()

    text = text.replace(
        "-",
        " ",
    )

    text = text.replace(
        "_",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def score_rule(
    goal_text: str,
    instruction: str,
    raw_input: str,
) -> tuple[str, float, str]:
    """
    Classify the goal using weighted keyword rules.
    """

    explicit_goal = normalize_text(
        goal_text,
    )

    fallback_context = normalize_text(
        f"{instruction} {raw_input}"
    )

    if explicit_goal:
        source_text = explicit_goal
    else:
        source_text = fallback_context

    scores = {
        label: 0.0
        for label in GOAL_LABELS
    }

    matches = {
        label: []
        for label in GOAL_LABELS
    }

    for label, phrases in GOAL_PATTERNS.items():

        for phrase, weight in phrases.items():

            normalized_phrase = normalize_text(
                phrase,
            )

            if normalized_phrase in source_text:

                scores[label] += weight

                matches[label].append(
                    phrase,
                )

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    best_label = ranked[0][0]

    best_score = ranked[0][1]

    second_score = ranked[1][1]

    if best_score <= 0:
        return "", 0.0, ""

    evidence_score = min(
        best_score / 6.0,
        1.0,
    )

    margin_score = (
        (
            best_score
            - second_score
        )
        / best_score
    )

    confidence = (
        0.55 * evidence_score
        + 0.45 * margin_score
    )

    matched_phrases = "|".join(
        matches[best_label]
    )

    return (
        best_label,
        round(confidence, 4),
        matched_phrases,
    )


def load_zero_shot_classifier():
    """
    Load BART-MNLI using Apple MPS when available.
    """

    import torch

    if torch.backends.mps.is_available():

        device = torch.device(
            "mps",
        )

        print(
            "Using Apple MPS for BART-MNLI."
        )

    else:

        device = torch.device(
            "cpu",
        )

        print(
            "Using CPU for BART-MNLI."
        )

    classifier = pipeline(
        task="zero-shot-classification",
        model=config.DATA_FINETUNE_MODEL_NAME,
        device=device,
    )

    return classifier


def zero_shot_predict(
    classifier,
    text: str,
) -> tuple[str, float, str, float]:
    """
    Run BART-MNLI zero-shot goal classification.
    """

    text = str(
        text,
    ).strip()

    if not text:
        return "", 0.0, "", 0.0

    descriptions = list(
        ZERO_SHOT_CANDIDATES.values()
    )

    description_to_label = {
        description: label
        for label, description
        in ZERO_SHOT_CANDIDATES.items()
    }

    result = classifier(
        text[:4000],
        candidate_labels=descriptions,
        hypothesis_template=(
            "The main campaign objective is {}."
        ),
        multi_label=False,
    )

    predicted_labels = [
        description_to_label[
            description
        ]
        for description
        in result["labels"]
    ]

    predicted_scores = [
        float(score)
        for score
        in result["scores"]
    ]

    best_label = predicted_labels[0]

    best_score = predicted_scores[0]

    if len(predicted_labels) > 1:

        second_label = predicted_labels[1]

        second_score = predicted_scores[1]

    else:

        second_label = ""

        second_score = 0.0

    return (
        best_label,
        round(best_score, 4),
        second_label,
        round(second_score, 4),
    )


GOAL_LABEL_SET = set(GOAL_LABELS)


def safe_label(
    value: object,
    allowed: set[str] = GOAL_LABEL_SET,
) -> str:
    """
    Read a label column defensively.

    A CSV round-trip turns "" into NaN, and str(NaN) is the string "nan", which
    is truthy. Without this guard a resumed run treats "nan" as a real goal and
    writes it out as the final label.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = str(value).strip().lower()

    if text in allowed:
        return text

    return ""


def safe_float(
    value: object,
    default: float = 0.0,
) -> float:
    """
    Read a numeric column defensively.
    """

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_phi_label(
    raw_output: str,
) -> str:
    """
    Extract one valid label from Phi-3 output.

    Reads the earliest label mentioned in the completion rather than the first
    label in GOAL_LABELS order, so the result reflects what the model said first.
    """

    normalized = normalize_text(
        raw_output,
    ).replace(
        " ",
        "_",
    )

    if not normalized:
        return ""

    positions = []

    for label in GOAL_LABELS:

        match = re.search(
            rf"\b{re.escape(label)}\b",
            normalized,
        )

        if match:
            positions.append(
                (
                    match.start(),
                    label,
                )
            )

    if not positions:
        return ""

    positions.sort()

    return positions[0][1]


def phi3_verify(
    row: pd.Series,
) -> str:
    """
    Ask Phi-3 to verify uncertain campaign-goal labels.
    """

    from models import generate_with_phi3

    prompt = f"""
You are verifying the primary objective of a marketing campaign.

Allowed labels:

awareness
conversion
engagement
lead_generation
retention

Definitions:

awareness:
Increase brand reach, recognition, visibility or discovery.

conversion:
Increase sales, purchases, bookings, paid subscriptions or revenue.

engagement:
Increase likes, comments, shares, participation or conversation.

lead_generation:
Collect inquiries, contact details, demo requests, downloads or signups.

retention:
Increase loyalty, repeat purchases, renewals or customer reactivation.

Explicit Goals Field:
{row.get("goal_text", "")}

Instruction:
{row.get("instruction", "")}

Business Context:
{row.get("summary", "")}

Return exactly one allowed label.
Do not provide an explanation.
"""

    try:

        output = generate_with_phi3(
            prompt,
            max_new_tokens=12,
            deterministic=True,
        )

        return parse_phi_label(
            output,
        )

    except Exception as exc:

        print(
            "Phi-3 goal verification warning "
            f"for row {row.get('row_id')}: {exc}"
        )

        return ""


def choose_final_label(
    row: pd.Series,
) -> dict[str, object]:
    """
    Combine rule, BART-MNLI and Phi-3 predictions.
    """

    rule_label = safe_label(
        row.get("campaign_goal_rule"),
    )

    rule_confidence = safe_float(
        row.get("campaign_goal_rule_confidence"),
    )

    zero_shot_label = safe_label(
        row.get("campaign_goal_zero_shot"),
    )

    zero_shot_confidence = safe_float(
        row.get("campaign_goal_zero_shot_confidence"),
    )

    phi_label = safe_label(
        row.get("campaign_goal_phi3"),
    )

    votes = [
        label
        for label in (
            rule_label,
            zero_shot_label,
            phi_label,
        )
        if label
    ]

    vote_counts = Counter(
        votes,
    )

    if vote_counts:

        majority_label, majority_count = (
            vote_counts.most_common(1)[0]
        )

    else:

        majority_label = ""

        majority_count = 0

    if (
        rule_label
        and rule_label == zero_shot_label
    ):

        final_label = rule_label

        final_confidence = min(
            0.99,
            (
                0.55
                * rule_confidence
                + 0.45
                * zero_shot_confidence
                + 0.12
            ),
        )

        source = (
            "rule_zero_shot_agreement"
        )

    elif (
        phi_label
        and majority_count >= 2
    ):

        final_label = majority_label

        supporting_confidences = []

        if final_label == rule_label:
            supporting_confidences.append(
                rule_confidence,
            )

        if final_label == zero_shot_label:
            supporting_confidences.append(
                zero_shot_confidence,
            )

        if supporting_confidences:

            average_confidence = (
                sum(supporting_confidences)
                / len(supporting_confidences)
            )

        else:

            average_confidence = 0.60

        final_confidence = min(
            0.97,
            average_confidence + 0.08,
        )

        source = (
            "three_method_majority"
        )

    elif (
        zero_shot_label
        and zero_shot_confidence >= 0.78
    ):

        final_label = zero_shot_label

        final_confidence = (
            zero_shot_confidence
        )

        source = (
            "high_confidence_zero_shot"
        )

    elif (
        rule_label
        and rule_confidence >= 0.78
    ):

        final_label = rule_label

        final_confidence = (
            rule_confidence
        )

        source = (
            "high_confidence_rule"
        )

    elif phi_label:

        final_label = phi_label

        final_confidence = 0.62

        source = "phi3_tiebreak"

    else:

        final_label = (
            zero_shot_label
            or rule_label
        )

        final_confidence = (
            max(
                zero_shot_confidence,
                rule_confidence,
            )
            * 0.85
        )

        source = (
            "low_confidence_best_available"
        )

    if votes:

        agreement = (
            majority_count
            / len(votes)
        )

    else:

        agreement = 0.0

    needs_review = bool(
        not final_label
        or final_confidence < 0.65
        or agreement < 0.5
    )

    return {
        "campaign_goal": final_label,
        "campaign_goal_confidence": round(
            float(final_confidence),
            4,
        ),
        "campaign_goal_agreement": round(
            float(agreement),
            4,
        ),
        "campaign_goal_source": source,
        "campaign_goal_needs_review": needs_review,
    }


def release_model_memory(
    model,
) -> None:
    """
    Release BART before loading Phi-3.
    """

    del model

    gc.collect()

    try:

        import torch

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

    except Exception:
        pass


def label_dataset(
    input_path: Path,
    output_path: Path,
    limit: int | None = None,
    use_phi3: bool = True,
    phi_threshold: float = 0.72,
    force: bool = False,
) -> pd.DataFrame:
    """
    Create campaign-goal labels and audit columns.
    """

    config.init_dirs()
    
    if not input_path.exists():
        raise FileNotFoundError(
            "Preprocessed dataset not found: "
            f"{input_path}"
        )

    checkpoint_path = output_path.with_suffix(".checkpoint.csv")

    if checkpoint_path.exists() and not force:

        print("Loading checkpoint...")

        dataframe = pd.read_csv(checkpoint_path)

        print(f"Loaded {len(dataframe)} rows from checkpoint.")

        resume_from = 0

        if "campaign_goal_phi3" in dataframe.columns:

            completed_rows = (
                dataframe["campaign_goal_phi3"]
                .fillna("")
                .astype(str)
                .ne("")
            )

            resume_from = completed_rows.idxmin() if not completed_rows.all() else len(dataframe)

        print(f"Resuming Phi-3 from row {resume_from}")
    
    elif output_path.exists() and not force:
        print(
            "Goal labels already exist."
        )

        print(
            "Use --force to rebuild."
        )

        return pd.read_csv(output_path)
        
    else:
        resume_from = 0

        dataframe = pd.read_csv(input_path)

        if "campaign_goal_phi3" not in dataframe.columns:
            dataframe["campaign_goal_phi3"] = ""

    required_columns = {
        "row_id",
        "instruction",
        "raw_input",
        "goal_text",
        "summary",
        "text",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Preprocessed dataset is missing columns: "
            f"{sorted(missing_columns)}"
        )

    text_columns = [
        "instruction",
        "raw_input",
        "goal_text",
        "summary",
        "text",
    ]

    for column in text_columns:
        dataframe[column] = (
            dataframe[column]
            .fillna("")
            .astype(str)
        )

    if limit is not None:
        dataframe = dataframe.head(
            limit,
        ).copy()

    print(
        "Running campaign-goal rule classifier..."
    )

    rule_results = dataframe.apply(
        lambda row: score_rule(
            row["goal_text"],
            row["instruction"],
            row["raw_input"],
        ),
        axis=1,
        result_type="expand",
    )

    rule_columns = [
        "campaign_goal_rule",
        "campaign_goal_rule_confidence",
        "campaign_goal_rule_matches",
    ]

    rule_results.columns = rule_columns

    # Assign each column directly. DataFrame.update() only writes to columns
    # that already exist, so on a fresh run (where these columns do not exist
    # yet) it silently does nothing and the rule labels are lost.
    for column in rule_columns:
        dataframe[column] = rule_results[column].to_numpy()

    print(
        "Loading BART-MNLI campaign-goal classifier..."
    )

    dataframe.to_csv(
        checkpoint_path,
        index=False,
    )

    print("Checkpoint saved after rule labeling.")
    
    CHECKPOINT_INTERVAL = 20

    if (
        "campaign_goal_zero_shot" not in dataframe.columns
        or dataframe["campaign_goal_zero_shot"]
            .fillna("")
            .eq("")
            .any()
    ):
        classifier = load_zero_shot_classifier()

        zero_shot_results = []

        total_rows = len(
            dataframe,
        )

        if "campaign_goal_zero_shot" not in dataframe.columns:
            dataframe["campaign_goal_zero_shot"] = ""
            dataframe["campaign_goal_zero_shot_confidence"] = 0.0
            dataframe["campaign_goal_second_choice"] = ""
            dataframe["campaign_goal_second_choice_confidence"] = 0.0

        missing = dataframe["campaign_goal_zero_shot"].fillna("").eq("")

        if missing.any():
            start_row = missing.idxmax()
        else:
            start_row = len(dataframe)

        for position in range(start_row, len(dataframe)):

            row = dataframe.iloc[position]
            
            goal_context = row[
                "goal_text"
            ].strip()

            if not goal_context:

                goal_context = (
                    f"{row['instruction']} "
                    f"{row['summary']}"
                )

            prediction = zero_shot_predict(
                classifier,
                goal_context,
            )

            zero_shot_results.append(
                prediction,
            )

            completed = position + 1
            
            if completed % CHECKPOINT_INTERVAL == 0:

                temp_df = pd.DataFrame(
                    zero_shot_results,
                    columns=[
                        "campaign_goal_zero_shot",
                        "campaign_goal_zero_shot_confidence",
                        "campaign_goal_second_choice",
                        "campaign_goal_second_choice_confidence",
                    ],
                )

                dataframe.loc[
                    : completed - 1,
                    temp_df.columns,
                ] = temp_df.values

                dataframe.to_csv(
                    checkpoint_path,
                    index=False,
                )

                print(
                    f"BART checkpoint saved ({completed}/{total_rows})"
                )
            if completed % 100 == 0:

                print(
                    "BART-MNLI goal labels: "
                    f"{completed}/{total_rows}"
                )
        
        zero_shot_dataframe = pd.DataFrame(
            zero_shot_results,
            columns=[
                "campaign_goal_zero_shot",
                "campaign_goal_zero_shot_confidence",
                "campaign_goal_second_choice",
                "campaign_goal_second_choice_confidence",
            ],
        )
    else:
        print("Skipping BART. Already completed.")
    
    if "zero_shot_dataframe" in locals():

        dataframe.loc[
            start_row:,
            zero_shot_dataframe.columns,
        ] = zero_shot_dataframe.values

    dataframe.to_csv(
        checkpoint_path,
        index=False,
    )

    if "classifier" in locals():
        release_model_memory(classifier)

    if "campaign_goal_phi3" not in dataframe.columns:
        dataframe["campaign_goal_phi3"] = ""

    if use_phi3:
        disagreement = dataframe[
            "campaign_goal_rule"
        ].ne(
            dataframe[
                "campaign_goal_zero_shot"
            ]
        )

        low_zero_shot_confidence = dataframe[
            "campaign_goal_zero_shot_confidence"
        ].lt(
            phi_threshold,
        )

        no_rule_prediction = dataframe[
            "campaign_goal_rule"
        ].eq(
            "",
        )

        verification_mask = (
            disagreement
            | low_zero_shot_confidence
            | no_rule_prediction
        )

        verification_indexes = [
            idx
            for idx in dataframe.index[verification_mask]
            if idx >= resume_from
            and dataframe.at[idx, "campaign_goal_phi3"] == ""
        ]

        print(
            "Rows selected for Phi-3 goal verification: "
            f"{len(verification_indexes)}"
        )

        verification_total = len(
            verification_indexes,
        )

        for number, row_index in enumerate(
            verification_indexes,
            start=1,
        ):
            print(f"\nPhi-3 goal check {number}/{verification_total}")
            dataframe.at[
                row_index,
                "campaign_goal_phi3",
            ] = phi3_verify(
                dataframe.loc[
                    row_index
                ]
            )

            # Save progress every 20 rows
            if number % CHECKPOINT_INTERVAL == 0:

                dataframe.to_csv(
                    checkpoint_path,
                    index=False,
                )

                print(
                    f"Checkpoint saved ({number}/{verification_total})"
                )

            if number % 50 == 0:

                print(
                    "Phi-3 goal checks: "
                    f"{number}/{verification_total}"
                )

    final_decisions = pd.DataFrame(
        [
            choose_final_label(
                row,
            )
            for _, row
            in dataframe.iterrows()
        ]
    )

    output = pd.concat(
        [
            dataframe.reset_index(drop=True),
            final_decisions.reset_index(drop=True),
        ],
        axis=1,
    )
    
    output.to_csv(
        output_path,
        index=False,
    )

    if checkpoint_path.exists():
        try:
            checkpoint_path.unlink()
        except Exception:
            pass

    print(
        "Campaign-goal labels saved to: "
        f"{output_path}"
    )

    print(
        "\nCampaign-goal distribution:"
    )

    print(
        output[
            "campaign_goal"
        ].value_counts(
            dropna=False,
        ).to_string()
    )

    review_count = int(
        output[
            "campaign_goal_needs_review"
        ].sum()
    )

    print(
        "\nCampaign-goal rows needing review: "
        f"{review_count}/{len(output)}"
    )

    return output


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
        "--input",
        type=Path,
        default=(
            config
            .PREPROCESSED_MARKETING_DATASET
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            config
            .GOAL_LABELED_DATASET
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--no-phi3",
        action="store_true",
    )

    parser.add_argument(
        "--phi-threshold",
        type=float,
        default=0.72,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing labeled dataset.",
    )

    return parser.parse_args(argv)


def run(argv: list[str] | None = None):
    arguments = parse_args(argv)

    label_dataset(
        input_path=arguments.input,
        output_path=arguments.output,
        limit=arguments.limit,
        use_phi3=not arguments.no_phi3,
        phi_threshold=arguments.phi_threshold,
        force=arguments.force,
    )

if __name__ == "__main__":
    run()