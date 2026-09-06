"""
Create research-grade marketing-tone pseudo-labels.

Stages, each of which writes its own checkpoint so an interrupted run resumes
from the last completed stage instead of re-running the expensive models:

1. rule   -> weighted tone keyword and writing-style rules
2. bart   -> BART-MNLI zero-shot classification (+ marginal calibration)
3. phi3   -> Phi-3 verification for uncertain or disagreeing examples
4. final  -> ensemble label selection

Checkpoint paths are declared in config as TONE_RULE_CHECKPOINT,
TONE_BART_CHECKPOINT, TONE_PHI3_CHECKPOINT and TONE_FINAL_CHECKPOINT.
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


TONE_LABEL_SET = set(TONE_LABELS)


STAGES = [
    "rule",
    "bart",
    "phi3",
    "final",
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


# Match whole words only. Plain substring matching makes "hey" fire on "they",
# "sale" on "wholesale" and "care" on "career". Lookarounds rather than \b so
# that phrases containing apostrophes ("don't miss", "let's") still anchor.
COMPILED_TONE_PATTERNS: dict[
    str,
    list[tuple[re.Pattern[str], str, float]],
] = {
    label: [
        (
            re.compile(
                r"(?<!\w)"
                + re.escape(phrase)
                + r"(?!\w)"
            ),
            phrase,
            weight,
        )
        for phrase, weight in phrases.items()
    ]
    for label, phrases in TONE_PATTERNS.items()
}


# Actual emoji blocks. The previous [^\x00-\x7F] test counted every non-ASCII
# character, so accented letters, curly quotes and em dashes scored as emoji.
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U0001f1e6-\U0001f1ff"
    "\U00002600-\U000027bf"
    "\U00002b00-\U00002bff"
    "]"
)


IMPERATIVE_PATTERN = re.compile(
    r"\b(?:"
    r"discover|explore|try|start|join|get|"
    r"shop|book|order|register|subscribe"
    r")\b"
)


SMART_CHARACTERS = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    " ": " ",
}


# Column groups written by each stage.
RULE_COLUMNS = [
    "tone_rule",
    "tone_rule_confidence",
    "tone_rule_matches",
]

ZERO_SHOT_SCORE_COLUMNS = [
    f"tone_zs_score_{label}"
    for label in TONE_LABELS
]

BART_COLUMNS = (
    ZERO_SHOT_SCORE_COLUMNS
    + [
        "tone_zero_shot_scored",
        "tone_zero_shot_raw",
        "tone_zero_shot_raw_confidence",
        "tone_zero_shot",
        "tone_zero_shot_confidence",
        "tone_second_choice",
        "tone_second_choice_confidence",
    ]
)

PHI3_COLUMNS = [
    "tone_phi3",
    "tone_phi3_selected",
    "tone_phi3_done",
]

FINAL_COLUMNS = [
    "tone",
    "tone_confidence",
    "tone_agreement",
    "tone_source",
    "tone_needs_review",
]


# Which stage is responsible for which columns, so restarting a stage can
# discard exactly the work that stage and its successors produced.
STAGE_OWNED_COLUMNS = {
    "rule": RULE_COLUMNS,
    "bart": BART_COLUMNS,
    "phi3": PHI3_COLUMNS,
    "final": FINAL_COLUMNS,
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

    text = str(value)

    for source, replacement in SMART_CHARACTERS.items():
        text = text.replace(
            source,
            replacement,
        )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def safe_label(
    value: object,
    allowed: set[str] = TONE_LABEL_SET,
) -> str:
    """
    Read a label column defensively.

    A CSV round-trip turns "" into NaN, and str(NaN) is the string "nan", which
    is truthy. Without this guard a resumed run will treat "nan" as a real tone
    and write it out as the final label.
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

    for label, compiled in COMPILED_TONE_PATTERNS.items():

        for expression, phrase, weight in compiled:

            if expression.search(normalized):

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
        EMOJI_PATTERN.findall(
            str(text),
        )
    )

    imperative_count = len(
        IMPERATIVE_PATTERN.findall(
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
        best_score
        / config.TONE_RULE_SATURATION_WEIGHT,
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
        config.TONE_RULE_EVIDENCE_WEIGHT
        * evidence_score
        + config.TONE_RULE_MARGIN_WEIGHT
        * margin_score
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

    if torch.cuda.is_available():

        device = torch.device(
            "cuda",
        )

        print(
            "Using CUDA for BART-MNLI."
        )

    elif torch.backends.mps.is_available():

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


def zero_shot_scores(
    classifier,
    text: str,
) -> dict[str, float]:
    """
    Score every tone label for one row.

    The full score vector is kept, not just the winner, so that calibration and
    any later re-analysis can run from the checkpoint without re-invoking BART.
    """

    text = str(
        text,
    ).strip()

    if not text:
        return {
            label: 0.0
            for label in TONE_LABELS
        }

    descriptions = list(
        ZERO_SHOT_CANDIDATES.values()
    )

    description_to_label = {
        description: label
        for label, description
        in ZERO_SHOT_CANDIDATES.items()
    }

    result = classifier(
        text[: config.TONE_ZERO_SHOT_MAX_CHARS],
        candidate_labels=descriptions,
        hypothesis_template=(
            "The writing style of this marketing content is {}."
        ),
        multi_label=False,
    )

    return {
        description_to_label[description]: float(score)
        for description, score
        in zip(
            result["labels"],
            result["scores"],
        )
    }


def calibrate_zero_shot_scores(
    dataframe: pd.DataFrame,
    strength: float,
) -> pd.DataFrame:
    """
    Divide out each label's corpus-mean score, then renormalize per row.

    Softmax over six overlapping candidate descriptions collapses onto whichever
    description best matches the domain as a whole. On marketing copy that is
    "persuasive, promotional, urgent, benefit-led", which wins almost every row
    regardless of the individual text. Dividing each label's score by its mean
    across the corpus removes that shared prior and leaves the per-row signal.

    strength=0 returns the raw scores unchanged.
    """

    scores = dataframe[
        ZERO_SHOT_SCORE_COLUMNS
    ].astype(float)

    if strength <= 0:
        return scores

    means = scores.mean(axis=0)

    # A label that never scored anything carries no prior to remove.
    means = means.where(
        means > 0,
        1.0,
    )

    adjusted = scores / (means ** strength)

    totals = adjusted.sum(axis=1)

    totals = totals.where(
        totals > 0,
        1.0,
    )

    return adjusted.div(
        totals,
        axis=0,
    )


def derive_zero_shot_columns(
    dataframe: pd.DataFrame,
    strength: float,
) -> pd.DataFrame:
    """
    Turn the stored score matrix into the label/confidence columns.
    """

    raw = dataframe[
        ZERO_SHOT_SCORE_COLUMNS
    ].astype(float)

    calibrated = calibrate_zero_shot_scores(
        dataframe,
        strength,
    )

    scored = (
        dataframe["tone_zero_shot_scored"]
        .fillna(0)
        .astype(int)
        .eq(1)
    )

    # Column order matches TONE_LABELS, so positional argmax maps back cleanly.
    def top_two(frame: pd.DataFrame) -> pd.DataFrame:
        ordered = frame.to_numpy().argsort(axis=1)[:, ::-1]
        return pd.DataFrame(
            {
                "best_index": ordered[:, 0],
                "second_index": ordered[:, 1],
            },
            index=frame.index,
        )

    raw_top = top_two(raw)
    calibrated_top = top_two(calibrated)

    labels = pd.Series(TONE_LABELS)

    dataframe["tone_zero_shot_raw"] = (
        labels
        .reindex(raw_top["best_index"])
        .to_numpy()
    )

    dataframe["tone_zero_shot_raw_confidence"] = [
        round(raw.iat[position, index], 4)
        for position, index
        in enumerate(raw_top["best_index"])
    ]

    dataframe["tone_zero_shot"] = (
        labels
        .reindex(calibrated_top["best_index"])
        .to_numpy()
    )

    dataframe["tone_zero_shot_confidence"] = [
        round(calibrated.iat[position, index], 4)
        for position, index
        in enumerate(calibrated_top["best_index"])
    ]

    dataframe["tone_second_choice"] = (
        labels
        .reindex(calibrated_top["second_index"])
        .to_numpy()
    )

    dataframe["tone_second_choice_confidence"] = [
        round(calibrated.iat[position, index], 4)
        for position, index
        in enumerate(calibrated_top["second_index"])
    ]

    # Rows with no usable text carry no prediction at all.
    blank_columns = [
        "tone_zero_shot_raw",
        "tone_zero_shot",
        "tone_second_choice",
    ]

    for column in blank_columns:
        dataframe.loc[~scored, column] = ""

    zero_columns = [
        "tone_zero_shot_raw_confidence",
        "tone_zero_shot_confidence",
        "tone_second_choice_confidence",
    ]

    for column in zero_columns:
        dataframe.loc[~scored, column] = 0.0

    return dataframe


def parse_phi_label(
    raw_output: str,
) -> str:
    """
    Extract one tone label from Phi-3 output.

    Reads the earliest label mentioned in the completion rather than the first
    label in TONE_LABELS order, so the result reflects what the model actually
    said first.
    """

    normalized = normalize_text(
        raw_output,
    )

    if not normalized:
        return ""

    positions = []

    for label in TONE_LABELS:

        match = re.search(
            rf"(?<!\w){re.escape(label)}(?!\w)",
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
            deterministic=True,
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

    rule_label = safe_label(
        row.get("tone_rule"),
    )

    rule_confidence = safe_float(
        row.get("tone_rule_confidence"),
    )

    zero_shot_label = safe_label(
        row.get("tone_zero_shot"),
    )

    zero_shot_confidence = safe_float(
        row.get("tone_zero_shot_confidence"),
    )

    phi_label = safe_label(
        row.get("tone_phi3"),
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
        and zero_shot_confidence
        >= config.TONE_ZERO_SHOT_ACCEPT_CONFIDENCE
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
        and rule_confidence
        >= config.TONE_RULE_ACCEPT_CONFIDENCE
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
        or final_confidence < config.TONE_MIN_CONFIDENCE
        or agreement < config.TONE_MIN_AGREEMENT
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

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

    except Exception:
        pass


def save_checkpoint(
    dataframe: pd.DataFrame,
    path: Path,
    message: str = "",
) -> None:
    """
    Write a checkpoint atomically.

    A crash partway through a write would otherwise leave a truncated CSV that
    the next run happily resumes from.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp",
    )

    dataframe.to_csv(
        temporary_path,
        index=False,
    )

    temporary_path.replace(
        path,
    )

    if message:
        print(message)


def read_checkpoint(
    path: Path,
) -> pd.DataFrame:
    """
    Load a checkpoint and restore the empty-string columns pandas turned to NaN.
    """

    dataframe = pd.read_csv(
        path,
    )

    text_columns = [
        "text",
        "tone_rule",
        "tone_rule_matches",
        "tone_zero_shot",
        "tone_zero_shot_raw",
        "tone_second_choice",
        "tone_phi3",
        "tone",
        "tone_source",
    ]

    for column in text_columns:

        if column in dataframe.columns:

            dataframe[column] = (
                dataframe[column]
                .fillna("")
                .astype(str)
            )

    return dataframe


def resolve_resume_point(
    from_stage: str | None,
) -> tuple[int, pd.DataFrame | None]:
    """
    Decide which stage to start at and which checkpoint to start from.

    Returns the index of the stage to enter, plus the dataframe to start from
    (None means start from the preprocessed input).

    Auto-resume re-enters the stage that owns the newest checkpoint rather than
    skipping past it. A checkpoint is written *during* a stage as well as at the
    end of one, so its existence only proves the stage started. Each stage
    detects its own outstanding rows and costs nothing when already complete.

    An explicit --from-stage instead discards that stage's work and every later
    stage's work, so the stage genuinely re-runs.
    """

    if from_stage:

        stage_index = STAGES.index(
            from_stage,
        )

        if stage_index == 0:
            return 0, None

        previous_name, previous_path = (
            config.TONE_STAGE_CHECKPOINTS[stage_index - 1]
        )

        if not previous_path.exists():
            raise FileNotFoundError(
                f"--from-stage {from_stage} needs the '{previous_name}' "
                f"checkpoint ({previous_path}), which does not exist. "
                "Run the earlier stages first, or use --force."
            )

        print(
            f"Restarting at '{from_stage}' from {previous_path.name}"
        )

        dataframe = read_checkpoint(
            previous_path,
        )

        # Discard anything the restarted stage or a later stage produced.
        stale_columns = [
            column
            for stage_name in STAGES[stage_index:]
            for column in STAGE_OWNED_COLUMNS[stage_name]
            if column in dataframe.columns
        ]

        return (
            stage_index,
            dataframe.drop(
                columns=stale_columns,
            ),
        )

    for stage_index in range(
        len(config.TONE_STAGE_CHECKPOINTS) - 1,
        -1,
        -1,
    ):

        stage_name, checkpoint_path = (
            config.TONE_STAGE_CHECKPOINTS[stage_index]
        )

        if checkpoint_path.exists():

            print(
                f"Resuming inside '{stage_name}' stage "
                f"from {checkpoint_path.name}"
            )

            return (
                stage_index,
                read_checkpoint(checkpoint_path),
            )

    return 0, None


def load_input_dataframe(
    input_path: Path,
    limit: int | None,
) -> pd.DataFrame:
    """
    Load and validate the preprocessed dataset.
    """

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

    return dataframe.reset_index(
        drop=True,
    )


def stage_rule(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Stage 1: weighted keyword and writing-style rules.
    """

    print(
        "\n[stage 1/4] Running tone rule classifier..."
    )

    rule_results = dataframe[
        "text"
    ].map(
        score_rule,
    ).apply(
        pd.Series,
    )

    rule_results.columns = RULE_COLUMNS

    for column in RULE_COLUMNS:
        dataframe[column] = rule_results[column].to_numpy()

    save_checkpoint(
        dataframe,
        config.TONE_RULE_CHECKPOINT,
        "Rule checkpoint saved: "
        f"{config.TONE_RULE_CHECKPOINT}",
    )

    return dataframe


def stage_bart(
    dataframe: pd.DataFrame,
    calibration_strength: float,
) -> pd.DataFrame:
    """
    Stage 2: BART-MNLI zero-shot scoring, resumable row by row.
    """

    print(
        "\n[stage 2/4] Running BART-MNLI tone classifier..."
    )

    for column in ZERO_SHOT_SCORE_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = pd.NA

    if "tone_zero_shot_scored" not in dataframe.columns:
        dataframe["tone_zero_shot_scored"] = 0

    dataframe["tone_zero_shot_scored"] = (
        dataframe["tone_zero_shot_scored"]
        .fillna(0)
        .astype(int)
    )

    pending = dataframe.index[
        dataframe["tone_zero_shot_scored"].ne(1)
    ].tolist()

    total_rows = len(dataframe)

    if not pending:

        print(
            f"BART already complete for all {total_rows} rows."
        )

    else:

        print(
            f"Rows still needing BART: {len(pending)}/{total_rows}"
        )

        classifier = load_zero_shot_classifier()

        for number, row_index in enumerate(
            pending,
            start=1,
        ):

            scores = zero_shot_scores(
                classifier,
                dataframe.at[row_index, "text"],
            )

            for label, score in scores.items():
                dataframe.at[
                    row_index,
                    f"tone_zs_score_{label}",
                ] = score

            dataframe.at[
                row_index,
                "tone_zero_shot_scored",
            ] = 1

            if number % config.LABEL_CHECKPOINT_INTERVAL == 0:

                save_checkpoint(
                    dataframe,
                    config.TONE_BART_CHECKPOINT,
                    "BART checkpoint saved "
                    f"({number}/{len(pending)})",
                )

        release_model_memory(
            classifier,
        )

    for column in ZERO_SHOT_SCORE_COLUMNS:
        dataframe[column] = (
            dataframe[column]
            .astype(float)
            .fillna(0.0)
        )

    dataframe = derive_zero_shot_columns(
        dataframe,
        calibration_strength,
    )

    save_checkpoint(
        dataframe,
        config.TONE_BART_CHECKPOINT,
        "BART checkpoint saved: "
        f"{config.TONE_BART_CHECKPOINT}",
    )

    return dataframe


def stage_phi3(
    dataframe: pd.DataFrame,
    use_phi3: bool,
    phi_threshold: float,
) -> pd.DataFrame:
    """
    Stage 3: Phi-3 arbitration for uncertain or disagreeing rows, resumable.
    """

    print(
        "\n[stage 3/4] Running Phi-3 tone verification..."
    )

    for column in PHI3_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = (
                "" if column == "tone_phi3" else 0
            )

    dataframe["tone_phi3"] = (
        dataframe["tone_phi3"]
        .fillna("")
        .astype(str)
    )

    if not use_phi3:

        print(
            "Phi-3 disabled (--no-phi3). "
            "Skipping arbitration."
        )

        dataframe["tone_phi3_selected"] = 0
        dataframe["tone_phi3_done"] = 0

        save_checkpoint(
            dataframe,
            config.TONE_PHI3_CHECKPOINT,
            "Phi-3 checkpoint saved: "
            f"{config.TONE_PHI3_CHECKPOINT}",
        )

        return dataframe

    rule_labels = dataframe["tone_rule"].map(safe_label)

    zero_shot_labels = dataframe["tone_zero_shot"].map(safe_label)

    zero_shot_confidences = dataframe[
        "tone_zero_shot_confidence"
    ].map(safe_float)

    disagreement = rule_labels.ne(
        zero_shot_labels,
    )

    low_zero_shot_confidence = zero_shot_confidences.lt(
        phi_threshold,
    )

    no_rule_prediction = rule_labels.eq(
        "",
    )

    verification_mask = (
        disagreement
        | low_zero_shot_confidence
        | no_rule_prediction
    )

    dataframe["tone_phi3_selected"] = (
        verification_mask
        .astype(int)
    )

    dataframe["tone_phi3_done"] = (
        dataframe["tone_phi3_done"]
        .fillna(0)
        .astype(int)
    )

    pending = dataframe.index[
        verification_mask
        & dataframe["tone_phi3_done"].ne(1)
    ].tolist()

    print(
        "Rows selected for Phi-3 tone verification: "
        f"{int(verification_mask.sum())}"
    )

    print(
        f"Rows still needing Phi-3: {len(pending)}"
    )

    for number, row_index in enumerate(
        pending,
        start=1,
    ):

        dataframe.at[
            row_index,
            "tone_phi3",
        ] = phi3_verify(
            dataframe.loc[row_index]
        )

        dataframe.at[
            row_index,
            "tone_phi3_done",
        ] = 1

        if number % config.LABEL_CHECKPOINT_INTERVAL == 0:

            save_checkpoint(
                dataframe,
                config.TONE_PHI3_CHECKPOINT,
                "Phi-3 checkpoint saved "
                f"({number}/{len(pending)})",
            )

    save_checkpoint(
        dataframe,
        config.TONE_PHI3_CHECKPOINT,
        "Phi-3 checkpoint saved: "
        f"{config.TONE_PHI3_CHECKPOINT}",
    )

    return dataframe


def stage_final(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Stage 4: ensemble decision.
    """

    print(
        "\n[stage 4/4] Selecting final tone labels..."
    )

    final_decisions = pd.DataFrame(
        [
            choose_final_label(row)
            for _, row
            in dataframe.iterrows()
        ],
        index=dataframe.index,
    )

    for column in FINAL_COLUMNS:
        dataframe[column] = final_decisions[column]

    save_checkpoint(
        dataframe,
        config.TONE_FINAL_CHECKPOINT,
        "Final checkpoint saved: "
        f"{config.TONE_FINAL_CHECKPOINT}",
    )

    return dataframe


def clear_checkpoints() -> None:
    """
    Remove every tone checkpoint.
    """

    for _, checkpoint_path in config.TONE_STAGE_CHECKPOINTS:

        if checkpoint_path.exists():

            try:
                checkpoint_path.unlink()
                print(
                    f"Removed checkpoint: {checkpoint_path.name}"
                )
            except OSError as exc:
                print(
                    f"Could not remove {checkpoint_path.name}: {exc}"
                )


def report(
    output: pd.DataFrame,
) -> None:
    """
    Print the distributions a reviewer needs to judge the labeling run.
    """

    print(
        "\nTone distribution (final):"
    )

    print(
        output["tone"]
        .replace("", "(none)")
        .value_counts(dropna=False)
        .to_string()
    )

    if "tone_zero_shot_raw" in output.columns:

        print(
            "\nBART distribution before calibration:"
        )

        print(
            output["tone_zero_shot_raw"]
            .replace("", "(none)")
            .value_counts(dropna=False)
            .to_string()
        )

        print(
            "\nBART distribution after calibration:"
        )

        print(
            output["tone_zero_shot"]
            .replace("", "(none)")
            .value_counts(dropna=False)
            .to_string()
        )

    print(
        "\nDecision source:"
    )

    print(
        output["tone_source"]
        .value_counts(dropna=False)
        .to_string()
    )

    review_count = int(
        output["tone_needs_review"].sum()
    )

    print(
        "\nTone rows needing review: "
        f"{review_count}/{len(output)}"
    )

    print(
        "Mean tone confidence: "
        f"{output['tone_confidence'].mean():.4f}"
    )


def label_dataset(
    input_path: Path,
    output_path: Path,
    limit: int | None = None,
    use_phi3: bool = True,
    phi_threshold: float | None = None,
    calibration_strength: float | None = None,
    force: bool = False,
    from_stage: str | None = None,
    keep_checkpoints: bool = False,
) -> pd.DataFrame:
    """
    Create tone labels and audit columns, resuming from the last checkpoint.
    """

    config.init_dirs()

    if phi_threshold is None:
        phi_threshold = config.TONE_PHI3_TRIGGER_CONFIDENCE

    if calibration_strength is None:
        calibration_strength = config.TONE_PRIOR_CALIBRATION_STRENGTH

    if force:
        clear_checkpoints()

    elif (
        output_path.exists()
        and not from_stage
        and not any(
            path.exists()
            for _, path in config.TONE_STAGE_CHECKPOINTS
        )
    ):

        print(
            "Tone labels already exist. Use --force to rebuild."
        )

        return pd.read_csv(output_path)

    start_index, dataframe = resolve_resume_point(
        from_stage,
    )

    if dataframe is None:
        dataframe = load_input_dataframe(
            input_path,
            limit,
        )

    elif limit is not None:
        dataframe = dataframe.head(
            limit,
        ).copy()

    if start_index <= 0:
        dataframe = stage_rule(dataframe)
    else:
        print("\n[stage 1/4] rule — loaded from checkpoint.")

    if start_index <= 1:
        dataframe = stage_bart(
            dataframe,
            calibration_strength,
        )
    else:
        print("[stage 2/4] bart — loaded from checkpoint.")

    if start_index <= 2:
        dataframe = stage_phi3(
            dataframe,
            use_phi3,
            phi_threshold,
        )
    else:
        print("[stage 3/4] phi3 — loaded from checkpoint.")

    if start_index <= 3:
        dataframe = stage_final(dataframe)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )

    print(
        "\nTone labels saved to: "
        f"{output_path}"
    )

    report(dataframe)

    if not keep_checkpoints:
        clear_checkpoints()

    return dataframe


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
        default=config.TONE_PHI3_TRIGGER_CONFIDENCE,
    )

    parser.add_argument(
        "--calibration-strength",
        type=float,
        default=config.TONE_PRIOR_CALIBRATION_STRENGTH,
        help=(
            "Marginal calibration applied to BART scores. "
            "0 disables it and restores raw zero-shot output."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Discard checkpoints and relabel from scratch.",
    )

    parser.add_argument(
        "--from-stage",
        choices=STAGES,
        default=None,
        help="Re-run starting at this stage, reusing earlier checkpoints.",
    )

    parser.add_argument(
        "--keep-checkpoints",
        action="store_true",
        help="Keep stage checkpoints after a successful run.",
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
        calibration_strength=arguments.calibration_strength,
        force=arguments.force,
        from_stage=arguments.from_stage,
        keep_checkpoints=arguments.keep_checkpoints,
    )


if __name__ == "__main__":
    run()
