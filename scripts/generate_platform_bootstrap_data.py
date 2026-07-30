#!/usr/bin/env python3
"""Create raw-export-shaped synthetic data for the four Member 4 platforms.

The files deliberately contain only fields normally available in an analytics
export. Strategy labels, product context, creative prompts, conversions and
engagement rate are not fabricated as if platforms supplied them.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "feedback" / "synthetic_bootstrap"
ROWS_PER_PLATFORM = 1_000
SOCIAL_FIELDS = ["external_post_id", "caption", "published_at", "impressions", "reach", "likes", "comments", "shares", "clicks"]
EMAIL_FIELDS = ["external_campaign_id", "subject_and_body", "sent_at", "delivered", "opens", "clicks", "unsubscribes"]
PRODUCTS = ["a skincare serum", "a scheduling tool", "a sustainable collection", "a meal-planning app", "an accounting tool", "an insulated bottle"]
HOOKS = ["A simpler way to make progress", "Your next small upgrade starts here", "Built for the moments that matter", "The practical choice for busy people"]
CTAS = ["Explore it today.", "See how it works.", "Learn more.", "Try it now."]


def social_row(platform: str, number: int, rng: random.Random) -> dict[str, object]:
    product = rng.choice(PRODUCTS)
    caption = f"{rng.choice(HOOKS)} Meet {product}. {rng.choice(CTAS)}"
    if platform == "instagram":
        caption += " #DiscoverMore #EverydayBetter"
        multiplier = rng.uniform(0.22, 1.20)
    elif platform == "tiktok":
        caption = f"POV: {caption} #ForYou #TryThis"
        multiplier = rng.uniform(0.35, 2.60)
    else:
        caption += " #BusinessGrowth"
        multiplier = rng.uniform(0.15, 0.85)
    impressions = int(rng.randint(2_000, 85_000) * multiplier)
    interactions = int(impressions * rng.uniform(0.012, 0.095))
    likes = int(interactions * rng.uniform(0.56, 0.78))
    comments = int(interactions * rng.uniform(0.05, 0.18))
    return {
        "external_post_id": f"SYN-{platform.upper()}-{number:04d}",
        "caption": caption,
        "published_at": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=rng.randint(0, 180), hours=rng.randint(0, 23))).isoformat(),
        "impressions": impressions,
        "reach": int(impressions * rng.uniform(0.70, 0.96)),
        "likes": likes,
        "comments": comments,
        "shares": max(0, interactions - likes - comments),
        "clicks": int(impressions * rng.uniform(0.003, 0.045)),
    }


def email_row(number: int, rng: random.Random) -> dict[str, object]:
    product = rng.choice(PRODUCTS)
    delivered = rng.randint(800, 100_000)
    return {
        "external_campaign_id": f"SYN-EMAIL-{number:04d}",
        "subject_and_body": f"Subject: {rng.choice(HOOKS)}\n\n{product.capitalize()} can help you get started. {rng.choice(CTAS)}",
        "sent_at": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=rng.randint(0, 180), hours=rng.randint(0, 23))).isoformat(),
        "delivered": delivered,
        "opens": int(delivered * rng.uniform(0.18, 0.52)),
        "clicks": int(delivered * rng.uniform(0.003, 0.045)),
        "unsubscribes": int(delivered * rng.uniform(0.0001, 0.004)),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for platform in ("instagram", "tiktok", "linkedin", "email"):
        path = OUT_DIR / f"synthetic_{platform}_raw_export_1000.csv"
        rng = random.Random(f"20260730:{platform}")
        fields = EMAIL_FIELDS if platform == "email" else SOCIAL_FIELDS
        rows = (email_row(i + 1, rng) if platform == "email" else social_row(platform, i + 1, rng) for i in range(ROWS_PER_PLATFORM))
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {ROWS_PER_PLATFORM:,} raw-export-shaped synthetic rows → {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
