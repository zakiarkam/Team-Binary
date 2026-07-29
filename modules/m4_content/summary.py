"""
Generate a structured marketing summary from the knowledge base using BART.
"""

import json

import config
from models import get_summarizer


def build(marketing_kb: dict) -> dict:
    """
    Build a marketing summary from the knowledge base.
    """

    source_text = marketing_kb["combined_text"][:3500]

    summary_text = get_summarizer()(
        source_text,
        max_length=180,
        min_length=60,
        do_sample=False,
    )[0]["summary_text"]

    module_input = marketing_kb["module_input"]

    return {
        "product_name": module_input.get("product_name", ""),
        "website_url": module_input.get("website_url", ""),
        "target_audience": module_input.get("target_audience", ""),
        "customer_segment": module_input.get("customer_segment", ""),
        "campaign_goal": module_input.get("campaign_goal", ""),
        "tone": module_input.get("tone", ""),
        "preferred_platforms": module_input.get(
            "preferred_platforms",
            [],
        ),
        "summary": summary_text,
    }


def run(marketing_kb: dict) -> dict:
    """
    Generate and save the summary.
    """

    summary = build(marketing_kb)

    with open(
        config.SUMMARY_JSON,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(
        f"Marketing summary saved → {config.SUMMARY_JSON}"
    )

    return summary


def load_cached() -> dict:
    """
    Load the cached marketing summary.
    """

    with open(
        config.SUMMARY_JSON,
        encoding="utf-8",
    ) as file:
        return json.load(file)