"""Generate a structured marketing summary from the knowledge base using BART."""

import json

import config
from models import get_summarizer


def build(marketing_kb: dict) -> dict:
    source_text = marketing_kb["combined_text"][:3500]
    summary_text = get_summarizer()(
        source_text, max_length=180, min_length=60, do_sample=False
    )[0]["summary_text"]

    m = marketing_kb["module_input"]
    return {
        "product_name": m.get("product_name", ""),
        "website_url": m.get("website_url", ""),
        "target_audience": m.get("target_audience", ""),
        "customer_segment": m.get("customer_segment", ""),
        "campaign_goal": m.get("campaign_goal", ""),
        "tone": m.get("tone", ""),
        "preferred_platforms": m.get("preferred_platforms", []),
        "summary": summary_text,
    }


def run(marketing_kb: dict) -> dict:
    summary = build(marketing_kb)
    with open(config.SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    print(f"Marketing summary saved → {config.SUMMARY_JSON}")
    return summary


def load_cached() -> dict:
    with open(config.SUMMARY_JSON, encoding="utf-8") as f:
        return json.load(f)
