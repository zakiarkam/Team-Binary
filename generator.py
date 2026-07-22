"""Platform-specific marketing asset generation with Phi-3.

Each platform is asked only for the creative prompts it can actually use:
an image prompt for feed and email placements, a short-form video prompt for
vertical video, never both. The capability table lives in config.PLATFORM_SPECS
so generation, scoring and optimization all read the same definition.
"""

import json
import pandas as pd

import config
from models import generate_with_phi3


# Every row carries the full column set so the CSV stays rectangular and
# downstream stages can read a column without checking the platform first.
ASSET_COLUMNS = [
    "platform",
    "caption",
    "hashtags",
    "cta",
    "image_prompt",
    "shorts_prompt",
]


def extract_json_from_text(text: str) -> dict | None:
    """Extract the first {...} JSON object from Phi-3 output."""
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def required_fields(spec: dict) -> list[str]:
    """The JSON keys this platform should return, in prompt order."""
    fields = ["caption"]
    if spec["hashtags"]:
        fields.append("hashtags")
    fields.append("cta")
    if spec["visual"] == "image":
        fields.append("image_prompt")
    elif spec["visual"] == "video":
        fields.append("shorts_prompt")
    return fields


def _schema_block(platform: str, fields: list[str]) -> str:
    lines = [f'  "platform": "{platform}",']
    for name in fields:
        placeholder = '["...", "...", "..."]' if name == "hashtags" else '"..."'
        lines.append(f'  "{name}": {placeholder},')
    lines[-1] = lines[-1].rstrip(",")
    return "{\n" + "\n".join(lines) + "\n}"


def _rules_block(spec: dict) -> str:
    low, high = spec["caption_words"]
    rules = [
        f"- {spec['guidance']}",
        f"- Caption length must be between {low} and {high} words.",
        "- Caption must align with the inferred campaign goal.",
        "- Caption must follow the inferred tone.",
    ]

    if spec["hashtags"]:
        least, most = spec["hashtag_range"]
        rules.append(
            f"- Return between {least} and {most} platform-appropriate hashtags."
        )
    else:
        rules.append("- Do not use hashtags on this platform.")

    rules.append("- CTA must support the campaign goal.")

    if spec["visual"] == "image":
        rules.append(
            "- image_prompt must describe one realistic still visual that "
            "matches the caption. Name the subject, setting and mood."
        )
        rules.append(
            "- This platform does not use short-form video. "
            "Do not return a shorts_prompt."
        )
    elif spec["visual"] == "video":
        rules.append(
            "- shorts_prompt must describe a vertical short-form video concept "
            "that matches the caption. Name the opening shot, what happens on "
            "screen, and the closing frame."
        )
        rules.append(
            "- This platform does not use a still image. "
            "Do not return an image_prompt."
        )

    rules.append("- Do not add explanation outside JSON.")
    return "\n".join(rules)


def build_prompt(marketing_summary: dict, platform: str) -> str:
    spec = config.platform_spec(platform)
    fields = required_fields(spec)

    return f"""
You are an expert digital marketing content creator.

Create marketing assets for the following product, written specifically for
the target platform.

Product Name:
{marketing_summary.get("product_name", "")}

Website URL:
{marketing_summary.get("website_url", "")}

Target Audience:
{marketing_summary.get("target_audience", "")}

Customer Segment:
{marketing_summary.get("customer_segment", "")}

Inferred Campaign Goal:
{marketing_summary.get("campaign_goal", "")}

Inferred Marketing Tone:
{marketing_summary.get("tone", "")}

Business Summary:
{marketing_summary.get("summary", "")}

Target Platform:
{platform}

Return only valid JSON in this exact format:

{_schema_block(platform, fields)}

Rules:
{_rules_block(spec)}
"""


def standardize(platform: str, raw_output: str) -> dict:
    """Coerce model output into one asset row, blanking inapplicable fields."""
    spec = config.platform_spec(platform)
    parsed = extract_json_from_text(raw_output) or {"caption": str(raw_output)}

    item = {name: "" for name in ASSET_COLUMNS}
    item["platform"] = parsed.get("platform") or platform
    item["caption"] = str(parsed.get("caption", "") or "")
    item["cta"] = str(parsed.get("cta", "") or "")

    hashtags = parsed.get("hashtags", []) if spec["hashtags"] else []
    if isinstance(hashtags, str):
        hashtags = [hashtags]
    elif not isinstance(hashtags, list):
        hashtags = []
    most = spec["hashtag_range"][1]
    item["hashtags"] = [str(tag) for tag in hashtags if str(tag).strip()][:most]

    # Keep only the creative prompt this platform uses. A model that returns
    # both is not allowed to smuggle the unused one into the output.
    if spec["visual"] == "image":
        item["image_prompt"] = str(parsed.get("image_prompt", "") or "")
    elif spec["visual"] == "video":
        item["shorts_prompt"] = str(parsed.get("shorts_prompt", "") or "")

    return item


def run(marketing_summary: dict) -> pd.DataFrame:
    platforms = list(marketing_summary.get("preferred_platforms", config.PLATFORMS))

    cleaned = []
    for index, platform in enumerate(platforms, start=1):
        spec = config.platform_spec(platform)
        asset = {"image": "image prompt", "video": "shorts prompt"}.get(
            spec["visual"], "no creative prompt"
        )
        print(f"\n--- [{index}/{len(platforms)}] {str(platform).upper()} "
              f"(asking for {asset}) ---")
        raw = generate_with_phi3(
            build_prompt(marketing_summary, platform), max_new_tokens=500
        )
        print(raw)
        cleaned.append(standardize(platform, raw))

    df = pd.DataFrame(cleaned, columns=ASSET_COLUMNS)
    df.to_csv(config.GENERATED_CSV, index=False)
    print(f"Generated assets saved → {config.GENERATED_CSV}")
    return df


def load_cached() -> pd.DataFrame:
    return pd.read_csv(config.GENERATED_CSV)
