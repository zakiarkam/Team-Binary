"""
Evaluation and ranking stage.

Responsibilities:
- Calculate semantic similarity.
- Measure platform suitability.
- Combine scores.
- Rank generated marketing assets.

Cache handling is managed by:
    main.py
    pipeline_cache.py
"""

import ast

import pandas as pd

from sentence_transformers import util

import config

from models import get_semantic_model


MIN_PROMPT_WORDS = 8


def semantic_score(
    source_text: str,
    generated_text: str,
) -> float:
    """
    Calculate semantic similarity between
    business summary and generated caption.
    """

    model = get_semantic_model()

    source_embedding = model.encode(
        str(source_text),
        convert_to_tensor=True,
    )

    generated_embedding = model.encode(
        str(generated_text),
        convert_to_tensor=True,
    )

    return float(
        util.cos_sim(
            source_embedding,
            generated_embedding,
        ).item()
    )


def as_text(value) -> str:
    """
    Safely convert dataframe values into text.
    """

    if value is None:
        return ""

    try:

        if pd.isna(value):
            return ""

    except (
        TypeError,
        ValueError,
    ):
        pass

    return str(value)


def _as_list(value) -> list:
    """
    Convert hashtag strings back into lists.
    """

    if isinstance(
        value,
        list,
    ):
        return value


    if value is None:
        return []


    try:

        if pd.isna(value):
            return []

    except (
        TypeError,
        ValueError,
    ):
        pass


    text = str(value).strip()


    if not text or text == "[]":
        return []


    try:

        parsed = ast.literal_eval(text)

        if isinstance(
            parsed,
            list,
        ):
            return parsed

    except (
        ValueError,
        SyntaxError,
    ):
        pass


    return [text]


def platform_suitability(
    row,
) -> float:
    """
    Evaluate whether generated content follows
    platform requirements.
    """

    platform = str(
        row["platform"]
    ).lower()


    spec = config.platform_spec(
        platform
    )


    caption = as_text(
        row.get("caption")
    )

    cta = as_text(
        row.get("cta")
    )

    image_prompt = as_text(
        row.get("image_prompt")
    )

    shorts_prompt = as_text(
        row.get("shorts_prompt")
    )


    caption_words = len(
        caption.split()
    )


    hashtags = len(
        _as_list(
            row.get("hashtags")
        )
    )


    checks = []


    low, high = spec["caption_words"]

    checks.append(
        low <= caption_words <= high
    )


    least, maximum = spec["hashtag_range"]

    checks.append(
        least <= hashtags <= maximum
    )


    checks.append(
        len(cta.strip()) > 0
    )


    if spec["visual"] == "image":

        checks.append(
            len(
                image_prompt.split()
            )
            >= MIN_PROMPT_WORDS
        )

        checks.append(
            not shorts_prompt.strip()
        )


    elif spec["visual"] == "video":

        checks.append(
            len(
                shorts_prompt.split()
            )
            >= MIN_PROMPT_WORDS
        )

        checks.append(
            (
                "scene"
                in shorts_prompt.lower()
            )
            or
            (
                "show"
                in shorts_prompt.lower()
            )
        )

        checks.append(
            not image_prompt.strip()
        )


    if platform == "email":

        checks.append(
            "subject"
            in caption.lower()
        )


    return sum(
        bool(check)
        for check in checks
    ) / len(checks)



def run(
    generated_assets_df: pd.DataFrame,
    marketing_summary: dict,
) -> pd.DataFrame:
    """
    Evaluate and rank generated assets.
    """


    source_summary = marketing_summary.get(
        "summary",
        "",
    )


    dataframe = generated_assets_df.copy()


    dataframe["semantic_score"] = (
        dataframe["caption"]
        .apply(
            lambda text:
            semantic_score(
                source_summary,
                text,
            )
        )
    )


    dataframe[
        "platform_suitability_score"
    ] = dataframe.apply(
        platform_suitability,
        axis=1,
    )


    dataframe[
        "final_score"
    ] = (

        config.SEMANTIC_WEIGHT
        *
        dataframe["semantic_score"]

        +

        config.PLATFORM_WEIGHT
        *
        dataframe[
            "platform_suitability_score"
        ]

        +

        config.ENGAGEMENT_WEIGHT
        *
        dataframe[
            "engagement_score"
        ]

    )


    ranked = (
        dataframe
        .sort_values(
            "final_score",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


    ranked.to_csv(
        config.RANKED_CSV,
        index=False,
    )


    print(
        f"Ranked assets saved → "
        f"{config.RANKED_CSV}"
    )


    print(
        ranked[
            [
                "platform",
                "semantic_score",
                "platform_suitability_score",
                "engagement_score",
                "final_score",
            ]
        ]
        .to_string(
            index=False
        )
    )


    return ranked



def load_cached() -> pd.DataFrame:
    """
    Load cached ranking output.
    """

    return pd.read_csv(
        config.RANKED_CSV
    )