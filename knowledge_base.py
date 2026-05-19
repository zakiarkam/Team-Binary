"""Clean and consolidate crawled site content into a marketing knowledge base."""

import json
import re

import config


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text))
    text = re.sub(r"http\S+", "", text)
    return text.strip()


def _clean_text_list(items, min_length: int = 3) -> list[str]:
    cleaned = [_clean_text(i) for i in items]
    cleaned = [c for c in cleaned if len(c) >= min_length]
    return list(dict.fromkeys(cleaned))


def build(website_data: dict, module_input: dict) -> dict:
    title = _clean_text(website_data.get("title", ""))
    meta_description = _clean_text(website_data.get("meta_description", ""))
    headings = _clean_text_list(website_data.get("headings", []), min_length=4)
    paragraphs = _clean_text_list(website_data.get("paragraphs", []), min_length=25)
    cta_texts = _clean_text_list(website_data.get("cta_texts", []), min_length=3)
    image_alt_texts = _clean_text_list(
        website_data.get("image_alt_texts", []), min_length=4
    )

    combined_text = _clean_text(
        " ".join(
            [
                module_input.get("product_name", ""),
                module_input.get("target_audience", ""),
                module_input.get("customer_segment", ""),
                title,
                meta_description,
                " ".join(headings[:20]),
                " ".join(paragraphs[:30]),
                " ".join(cta_texts[:20]),
                " ".join(image_alt_texts[:20]),
            ]
        )
    )

    return {
        "module_input": module_input,
        "title": title,
        "meta_description": meta_description,
        "headings": headings[:20],
        "paragraphs": paragraphs[:30],
        "cta_texts": cta_texts[:20],
        "image_alt_texts": image_alt_texts[:20],
        "combined_text": combined_text,
    }


def run(website_data: dict, module_input: dict) -> dict:
    kb = build(website_data, module_input)
    with open(config.KB_JSON, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=4, ensure_ascii=False)
    print(f"Knowledge base built ({len(kb['combined_text'])} chars).")
    return kb


def load_cached() -> dict:
    with open(config.KB_JSON, encoding="utf-8") as f:
        return json.load(f)
