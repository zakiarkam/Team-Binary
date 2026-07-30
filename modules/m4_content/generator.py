"""
Platform-specific marketing asset generation with Phi-3.

This module is responsible only for generating platform-specific
marketing assets. Cache validation is handled by main.py together
with pipeline_cache.py.
"""

import json
import pandas as pd

import config
from models import generate_with_phi3


ASSET_COLUMNS = [
    "platform",
    "caption",
    "hashtags",
    "cta",
    "image_prompt",
    "shorts_prompt",
    # The brand voice the classifier predicted, and the register it was spoken
    # in on this platform. Both travel with the asset so a stored asset records
    # which voice produced it rather than only the campaign-wide one.
    "brand_tone",
    "platform_tone",
]


def extract_json_from_text(text: str) -> dict | None:
    """
    Extract the first JSON object returned by Phi-3.
    """

    try:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            return None

        return json.loads(text[start:end + 1])

    except Exception:
        return None


def required_fields(spec: dict) -> list[str]:
    """
    Return the required JSON fields for a platform.
    """

    fields = [
        "caption",
    ]

    if spec["hashtags"]:
        fields.append("hashtags")

    fields.append("cta")

    if spec["visual"] == "image":
        fields.append("image_prompt")

    elif spec["visual"] == "video":
        fields.append("shorts_prompt")

    return fields


def _schema_block(
    platform: str,
    fields: list[str],
) -> str:
    """
    Build the JSON schema shown inside the prompt.
    """

    lines = [
        f'  "platform": "{platform}",'
    ]

    for field in fields:

        placeholder = (
            '["...", "...", "..."]'
            if field == "hashtags"
            else '"..."'
        )

        lines.append(
            f'  "{field}": {placeholder},'
        )

    lines[-1] = lines[-1].rstrip(",")

    return "{\n" + "\n".join(lines) + "\n}"


def _rules_block(
    spec: dict,
    tone: str = "",
) -> str:
    """
    Build platform-specific generation rules.

    `tone` is the platform-adapted tone (config.platform_tone), not the raw
    brand tone. Naming it in the rules is what stops the model from defaulting
    to one house voice on every channel; omitting it keeps the older, generic
    wording so callers that have no tone to pass still get valid rules.
    """

    low, high = spec["caption_words"]

    tone_rule = (
        f"- Caption must be written in a {tone} tone."
        if str(tone).strip()
        else "- Caption must follow the marketing tone."
    )

    rules = [

        f"- {spec['guidance']}",

        (
            f"- Caption length must be "
            f"between {low} and {high} words."
        ),

        "- Caption must align with the campaign goal.",

        tone_rule,

    ]

    if spec["hashtags"]:

        least, most = spec["hashtag_range"]

        rules.append(
            f"- Return between {least} and {most} hashtags."
        )

    else:

        rules.append(
            "- Do not use hashtags."
        )

    rules.append(
        "- CTA must match the campaign goal."
    )

    if spec["visual"] == "image":

        rules.extend(
            [

                "- image_prompt must describe a realistic image.",

                "- Do not return shorts_prompt.",

            ]
        )

    elif spec["visual"] == "video":

        rules.extend(
            [

                "- shorts_prompt must describe a vertical short video.",

                "- Do not return image_prompt.",

            ]
        )

    rules.append(
        "- Return only valid JSON."
    )

    return "\n".join(rules)


def build_prompt(
    marketing_summary: dict,
    platform: str,
) -> str:
    """
    Build the Phi-3 prompt.
    """

    spec = config.platform_spec(platform)

    spec["visual"] = config.select_visual(
        platform,
        marketing_summary
    )

    fields = required_fields(spec)

    # The classifier predicts one tone for the business. The platform shifts the
    # register that tone is spoken in, not the brand voice itself — the same
    # brand_tone -> platform_tone rule the fast engine applies, so the two
    # engines cannot drift apart. See config.PLATFORM_TONE_REGISTER.
    brand_tone = marketing_summary.get("tone", "")

    tone_for_platform = config.platform_tone(
        platform,
        brand_tone,
    )

    register_note = config.register_note(
        platform,
    )

    return f"""
You are an expert digital marketing content creator.

Create platform-specific marketing assets.

Product Name:
{marketing_summary.get("product_name", "")}

Website:
{marketing_summary.get("website_url", "")}

Target Audience:
{marketing_summary.get("target_audience", "")}

Customer Segment:
{marketing_summary.get("customer_segment", "")}

Campaign Goal:
{marketing_summary.get("campaign_goal", "")}

Brand Voice:
{brand_tone}

Tone for this platform:
{tone_for_platform}

How this platform is spoken:
{register_note}

Business Summary:
{marketing_summary.get("summary", "")}

Platform:
{platform}

Return ONLY valid JSON.

{_schema_block(platform, fields)}

Rules:

{_rules_block(spec, tone_for_platform)}
"""


def standardize(
    platform: str,
    raw_output: str,
    marketing_summary: dict,
) -> dict:
    """
    Convert Phi-3 output into one standardized row.
    """

    spec = config.platform_spec(platform)

    spec["visual"] = config.select_visual(
        platform,
        marketing_summary,
    )

    parsed = (
        extract_json_from_text(raw_output)
        or {"caption": raw_output}
    )

    row = {
        column: ""
        for column in ASSET_COLUMNS
    }

    row["platform"] = (
        parsed.get("platform")
        or platform
    )

    row["brand_tone"] = str(
        marketing_summary.get("tone", "")
    )

    row["platform_tone"] = config.platform_tone(
        platform,
        row["brand_tone"],
    )

    row["caption"] = str(
        parsed.get("caption", "")
    )

    row["cta"] = str(
        parsed.get("cta", "")
    )

    hashtags = (
        parsed.get("hashtags", [])
        if spec["hashtags"]
        else []
    )

    if isinstance(
        hashtags,
        str,
    ):
        hashtags = [hashtags]

    elif not isinstance(
        hashtags,
        list,
    ):
        hashtags = []

    maximum = spec["hashtag_range"][1]

    row["hashtags"] = [

        str(tag)

        for tag in hashtags

        if str(tag).strip()

    ][:maximum]

    if spec["visual"] == "image":

        row["image_prompt"] = str(
            parsed.get(
                "image_prompt",
                "",
            )
        )

    elif spec["visual"] == "video":

        row["shorts_prompt"] = str(
            parsed.get(
                "shorts_prompt",
                "",
            )
        )

    return row


def run(
    marketing_summary: dict,
) -> pd.DataFrame:
    """
    Generate marketing assets for every platform.
    """

    platforms = marketing_summary.get(
        "preferred_platforms",
        config.PLATFORMS,
    )

    generated_assets = []

    total = len(platforms)

    for index, platform in enumerate(
        platforms,
        start=1,
    ):

        spec = config.platform_spec(platform)

        visual_type = (
            "image prompt"
            if spec["visual"] == "image"
            else "short video prompt"
        )

        print(
            f"\n--- [{index}/{total}] "
            f"{platform.upper()} "
            f"({visual_type}) ---"
        )

        prompt = build_prompt(
            marketing_summary,
            platform,
        )

        raw_output = generate_with_phi3(
            prompt,
            max_new_tokens=500,
        )

        print(raw_output)

        generated_assets.append(

            standardize(
                platform,
                raw_output,
                marketing_summary,
            )

        )

    dataframe = pd.DataFrame(
        generated_assets,
        columns=ASSET_COLUMNS,
    )

    dataframe.to_csv(
        config.GENERATED_CSV,
        index=False,
    )

    print(
        f"\nGenerated assets saved → "
        f"{config.GENERATED_CSV}"
    )

    return dataframe


def load_cached() -> pd.DataFrame:
    """
    Load previously generated assets.
    """

    return pd.read_csv(
        config.GENERATED_CSV
    )