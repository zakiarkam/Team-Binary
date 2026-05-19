"""Platform-specific marketing asset generation with Phi-3."""

import json
import pandas as pd

import config
from models import generate_with_phi3


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


def build_prompt(marketing_summary: dict, platform: str) -> str:
    return f"""
You are an expert digital marketing content creator.

Create platform-specific marketing assets for the following product.

Product Name:
{marketing_summary["product_name"]}

Website URL:
{marketing_summary["website_url"]}

Target Audience:
{marketing_summary["target_audience"]}

Customer Segment:
{marketing_summary["customer_segment"]}

Inferred Campaign Goal:
{marketing_summary["campaign_goal"]}

Inferred Marketing Tone:
{marketing_summary["tone"]}

Business Summary:
{marketing_summary["summary"]}

Target Platform:
{platform}

Return only valid JSON in this exact format:

{{
  "platform": "{platform}",
  "caption": "...",
  "hashtags": ["...", "...", "..."],
  "cta": "...",
  "image_prompt": "...",
  "shorts_prompt": "..."
}}

Rules:
- Caption must match the target platform.
- Caption must align with the inferred campaign goal.
- Caption must follow the inferred tone.
- Hashtags must be platform-appropriate.
- CTA must support the campaign goal.
- Image prompt must describe a realistic visual concept aligned with the caption.
- Shorts prompt must describe a short-form video concept aligned with the caption.
- Do not add explanation outside JSON.
"""


def standardize(platform: str, raw_output: str) -> dict:
    parsed = extract_json_from_text(raw_output) or {
        "platform": platform,
        "caption": str(raw_output),
        "hashtags": [],
        "cta": "",
        "image_prompt": "",
        "shorts_prompt": "",
    }
    parsed.setdefault("platform", platform)
    parsed.setdefault("caption", "")
    parsed.setdefault("hashtags", [])
    parsed.setdefault("cta", "")
    parsed.setdefault("image_prompt", "")
    parsed.setdefault("shorts_prompt", "")
    if isinstance(parsed["hashtags"], str):
        parsed["hashtags"] = [parsed["hashtags"]]
    return parsed


def run(marketing_summary: dict) -> pd.DataFrame:
    platforms = marketing_summary.get("preferred_platforms", config.PLATFORMS)
    cleaned = []
    for platform in platforms:
        raw = generate_with_phi3(build_prompt(marketing_summary, platform), max_new_tokens=500)
        print(f"\n--- {platform.upper()} ---\n{raw}")
        cleaned.append(standardize(platform, raw))
    df = pd.DataFrame(cleaned)
    df.to_csv(config.GENERATED_CSV, index=False)
    print(f"Generated assets saved → {config.GENERATED_CSV}")
    return df


def load_cached() -> pd.DataFrame:
    return pd.read_csv(config.GENERATED_CSV)
