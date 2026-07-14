"""
Create research-grade marketing-tone pseudo-labels.

Methods:

1. Weighted tone keyword and writing-style rules.
2. BART-MNLI zero-shot classification.
3. Phi-3 verification for uncertain or disagreeing examples.
4. Ensemble label selection.
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


TONE_LABELS = [
    "friendly",
    "professional",
    "luxury",
    "emotional",
    "persuasive",
    "humorous",
]


ZERO_SHOT_CANDIDATES = {
    "friendly": (
        "friendly, warm, conversational, welcoming, "
        "casual, and approachable"
    ),
    "professional": (
        "professional, formal, credible, informative, "
        "authoritative, and businesslike"
    ),
    "luxury": (
        "luxurious, premium, exclusive, elegant, "
        "sophisticated, and refined"
    ),
    "emotional": (
        "emotional, inspiring, heartfelt, empathetic, "
        "personal, and story-driven"
    ),
    "persuasive": (
        "persuasive, promotional, urgent, benefit-led, "
        "convincing, and action-oriented"
    ),
    "humorous": (
        "humorous, witty, playful, funny, entertaining, "
        "and lighthearted"
    ),
}


TONE_PATTERNS: dict[
    str,
    dict[str, float],
] = {
    "luxury": {
        "luxury": 3.5,
        "premium": 2.5,
        "exclusive": 2.5,
        "elegant": 2.5,
        "sophisticated": 3.0,
        "refined": 2.5,
        "bespoke": 3.5,
        "prestige": 3.0,
        "crafted": 1.5,
        "timeless": 2.0,
        "exquisite": 3.0,
        "elite": 2.5,
    },
    "emotional": {
        "heartfelt": 3.5,
        "inspire": 2.5,
        "inspiring": 2.5,
        "journey": 2.0,
        "dream": 2.0,
        "feel": 1.5,
        "together": 1.5,
        "we understand": 3.0,
        "you deserve": 2.5,
        "transform your life": 3.0,
        "confidence": 1.5,
        "care": 1.5,
        "memories": 2.0,
    },
    "persuasive": {
        "buy now": 4.0,
        "shop now": 4.0,
        "order now": 4.0,
        "book now": 4.0,
        "sign up": 3.0,
        "register now": 3.5,
        "limited time": 3.5,
        "don't miss": 3.0,
        "act now": 4.0,
        "save": 2.0,
        "discount": 2.5,
        "offer": 2.0,
        "sale": 2.5,
        "today": 1.0,
        "get yours": 3.0,
    },
    "friendly": {
        "welcome": 2.5,
        "hello": 2.0,
        "hey": 2.0,
        "thank you": 2.5,
        "thanks": 2.0,
        "join us": 2.0,
        "we'd love": 3.0,
        "let's": 2.0,
        "your friends": 1.5,
        "community": 1.5,
        "share your": 2.0,
        "we're here": 2.0,
        "come along": 2.0,
    },
    "humorous": {
        "lol": 3.5,
        "haha": 3.5,
        "just kidding": 3.0,
        "plot twist": 3.0,
        "spoiler alert": 2.5,
        "pun intended": 4.0,
        "meme": 2.5,
        "funny": 2.5,
        "oops": 1.5,
        "because adulting": 3.0,
        "no pun intended": 3.5,
    },
    "professional": {
        "industry": 1.5,
        "strategy": 1.5,
        "research": 2.0,
        "report": 2.0,
        "insights": 2.0,
        "case study": 2.5,
        "webinar": 2.0,
        "business": 1.5,
        "solution": 1.5,
        "performance": 1.5,
        "expert": 1.5,
        "learn more": 1.0,
        "analysis": 2.0,
        "organization": 1.5,
    },
}


def normalize_text(
    value: object,
) -> str:
    """
    Normalize tone text.
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
        "\u00a0",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def score_rule(
    text: str,
) -> tuple[str, float, str]:
    """
    Predict tone using weighted lexical and style evidence.
    """

    normalized = normalize_text(
        text,
    )

    scores = {
        label: 0.0
        for label in TONE_LABELS
    }

    matches = {
        label: []
        for label in TONE_LABELS
    }

    for label, phrases in TONE_PATTERNS.items():

        for phrase, weight in phrases.items():

            if phrase in normalized:

                scores[label] += weight

                matches[label].append(
                    phrase,
                )

    exclamation_count = normalized.count(
        "!",
    )

    question_count = normalized.count(
        "?",
    )

    emoji_count = len(
        re.findall(
            r"[^\x00-\x7F]",
            str(text),
        )
    )

    imperative_count = len(
        re.findall(
            (
                r"\b(?:"
                r"discover|explore|try|start|join|get|"
                r"shop|book|order|register|subscribe"
                r")\b"
            ),
            normalized,
        )
    )

    scores["persuasive"] += (
        min(
            exclamation_count,
            3,
        )
        * 0.35
    )

    scores["persuasive"] += (
        min(
            imperative_count,
            3,
        )
        * 0.40
    )

    scores["friendly"] += (
        min(
            question_count,
            2,
        )
        * 0.30
    )

    scores["friendly"] += (
        min(
            emoji_count,
            4,
        )
        * 0.15
    )

    scores["humorous"] += (
        min(
            emoji_count,
            4,
        )
        * 0.05
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
    Load BART-MNLI with Apple MPS support.
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
    Run zero-shot marketing-tone classification.
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
            "The writing style of this marketing content is {}."
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


def parse_phi_label(
    raw_output: str,
) -> str:
    """
    Extract one tone label from Phi-3 output.
    """

    normalized = normalize_text(
        raw_output,
    )

    for label in TONE_LABELS:

        if re.search(
            rf"\b{re.escape(label)}\b",
            normalized,
        ):
            return label

    return ""


def phi3_verify(
    row: pd.Series,
) -> str:
    """
    Ask Phi-3 to verify the dominant writing tone.
    """

    from models import generate_with_phi3

    prompt = f"""
You are verifying the dominant writing tone of marketing content.

Allowed labels:

friendly
professional
luxury
emotional
persuasive
humorous

Definitions:

friendly:
Warm, casual, welcoming, conversational and approachable.

professional:
Formal, credible, informative, authoritative and businesslike.

luxury:
Premium, elegant, exclusive, refined and sophisticated.

emotional:
Heartfelt, inspiring, empathetic, personal or story-driven.

persuasive:
Promotional, convincing, urgent, benefit-led and action-oriented.

humorous:
Funny, witty, playful, entertaining or lighthearted.

Important:
Classify the writing style, not the campaign objective.

Marketing Content:
{row.get("text", "")}

Return exactly one allowed label.
Do not provide an explanation.
"""

    try:

        output = generate_with_phi3(
            prompt,
            max_new_tokens=12,
        )

        return parse_phi_label(
            output,
        )

    except Exception as exc:

        print(
            "Phi-3 tone verification warning "
            f"for row {row.get('row_id')}: {exc}"
        )

        return ""


def choose_final_label(
    row: pd.Series,
) -> dict[str, object]:
    """
    Combine tone predictions.
    """

    rule_label = str(
        row.get(
            "tone_rule",
            "",
        )
    )

    rule_confidence = float(
        row.get(
            "tone_rule_confidence",
            0.0,
        )
    )

    zero_shot_label = str(
        row.get(
            "tone_zero_shot",
            "",
        )
    )

    zero_shot_confidence = float(
        row.get(
            "tone_zero_shot_confidence",
            0.0,
        )
    )

    phi_label = str(
        row.get(
            "tone_phi3",
            "",
        )
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
                0.45
                * rule_confidence
                + 0.55
                * zero_shot_confidence
                + 0.10
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
            0.96,
            average_confidence + 0.07,
        )

        source = (
            "three_method_majority"
        )

    elif (
        zero_shot_label
        and zero_shot_confidence >= 0.72
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
        and rule_confidence >= 0.82
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

        final_confidence = 0.60

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
            * 0.82
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
        or final_confidence < 0.62
        or agreement < 0.5
    )

    return {
        "tone": final_label,
        "tone_confidence": round(
            float(final_confidence),
            4,
        ),
        "tone_agreement": round(
            float(agreement),
            4,
        ),
        "tone_source": source,
        "tone_needs_review": needs_review,
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
    phi_threshold: float = 0.67,
) -> pd.DataFrame:
    """
    Create tone labels and audit columns.
    """

    config.init_dirs()

    if not input_path.exists():
        raise FileNotFoundError(
            "Preprocessed dataset not found: "
            f"{input_path}"
        )

    dataframe = pd.read_csv(
        input_path,
    )

    required_columns = {
        "row_id",
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

    dataframe["text"] = (
        dataframe["text"]
        .fillna("")
        .astype(str)
    )

    if limit is not None:
        dataframe = dataframe.head(
            limit,
        ).copy()

    print(
        "Running tone rule classifier..."
    )

    rule_results = dataframe[
        "text"
    ].map(
        score_rule,
    ).apply(
        pd.Series,
    )

    rule_results.columns = [
        "tone_rule",
        "tone_rule_confidence",
        "tone_rule_matches",
    ]

    dataframe = pd.concat(
        [
            dataframe.reset_index(
                drop=True,
            ),
            rule_results.reset_index(
                drop=True,
            ),
        ],
        axis=1,
    )

    print(
        "Loading BART-MNLI tone classifier..."
    )

    classifier = load_zero_shot_classifier()

    zero_shot_results = []

    total_rows = len(
        dataframe,
    )

    for position, text in enumerate(
        dataframe["text"],
        start=1,
    ):

        prediction = zero_shot_predict(
            classifier,
            text,
        )

        zero_shot_results.append(
            prediction,
        )

        if position % 100 == 0:

            print(
                "BART-MNLI tone labels: "
                f"{position}/{total_rows}"
            )

    zero_shot_dataframe = pd.DataFrame(
        zero_shot_results,
        columns=[
            "tone_zero_shot",
            "tone_zero_shot_confidence",
            "tone_second_choice",
            "tone_second_choice_confidence",
        ],
    )

    dataframe = pd.concat(
        [
            dataframe.reset_index(
                drop=True,
            ),
            zero_shot_dataframe.reset_index(
                drop=True,
            ),
        ],
        axis=1,
    )

    release_model_memory(
        classifier,
    )

    dataframe[
        "tone_phi3"
    ] = ""

    if use_phi3:

        disagreement = dataframe[
            "tone_rule"
        ].ne(
            dataframe[
                "tone_zero_shot"
            ]
        )

        low_zero_shot_confidence = dataframe[
            "tone_zero_shot_confidence"
        ].lt(
            phi_threshold,
        )

        no_rule_prediction = dataframe[
            "tone_rule"
        ].eq(
            "",
        )

        verification_mask = (
            disagreement
            | low_zero_shot_confidence
            | no_rule_prediction
        )

        verification_indexes = dataframe.index[
            verification_mask
        ].tolist()

        print(
            "Rows selected for Phi-3 tone verification: "
            f"{len(verification_indexes)}"
        )

        verification_total = len(
            verification_indexes,
        )

        for number, row_index in enumerate(
            verification_indexes,
            start=1,
        ):

            dataframe.at[
                row_index,
                "tone_phi3",
            ] = phi3_verify(
                dataframe.loc[
                    row_index
                ]
            )

            if number % 50 == 0:

                print(
                    "Phi-3 tone checks: "
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
            dataframe.reset_index(
                drop=True,
            ),
            final_decisions.reset_index(
                drop=True,
            ),
        ],
        axis=1,
    )

    output.to_csv(
        output_path,
        index=False,
    )

    print(
        "Tone labels saved to: "
        f"{output_path}"
    )

    print(
        "\nTone distribution:"
    )

    print(
        output[
            "tone"
        ].value_counts(
            dropna=False,
        ).to_string()
    )

    review_count = int(
        output[
            "tone_needs_review"
        ].sum()
    )

    print(
        "\nTone rows needing review: "
        f"{review_count}/{len(output)}"
    )

    return output


def parse_args() -> argparse.Namespace:
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
            .TONE_LABELED_DATASET
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
        default=0.67,
    )

    return parser.parse_args()


if __name__ == "__main__":

    arguments = parse_args()

    label_dataset(
        input_path=arguments.input,
        output_path=arguments.output,
        limit=arguments.limit,
        use_phi3=not arguments.no_phi3,
        phi_threshold=arguments.phi_threshold,
    )