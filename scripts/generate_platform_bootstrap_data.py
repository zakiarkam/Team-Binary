#!/usr/bin/env python3
"""Create clearly marked synthetic bootstrap data for the four M4 platforms.

This corpus is only for schema/UI/candidate-flow testing. Its outcome fields
are simulated and must never be mixed with real analytics for reported results.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "feedback" / "synthetic_bootstrap"
ROWS_PER_PLATFORM = 1_000
FIELDS = ["record_id", "data_origin", "platform", "account_id", "product_context", "caption", "creative_prompt", "campaign_goal", "tone", "published_at", "followers_at_post_time", "impressions", "reach", "likes", "comments", "shares", "clicks", "opens", "conversions", "engagement_rate", "measurement_window_days"]
PRODUCTS = [("A refillable skincare serum for sensitive skin", "skincare serum"), ("A B2B appointment scheduling tool for small clinics", "scheduling tool"), ("An online sustainable fashion store", "sustainable collection"), ("A healthy meal-planning mobile app", "meal-planning app"), ("A cloud accounting tool for freelance designers", "accounting tool"), ("A reusable insulated water bottle", "insulated bottle")]
RULES = {
    "instagram": {"goals": ["awareness", "engagement", "conversion"], "tones": ["friendly", "emotional", "persuasive"], "followers": (2000, 85000), "reach": (0.22, 1.20), "caption": "{hook} {product} for {benefit}. {cta} {tags}", "prompt": "Vertical lifestyle product photograph of {product}, warm natural light, authentic creator aesthetic, no text overlay", "tags": ["#DiscoverMore #EverydayBetter", "#MadeForYou #TryItToday"]},
    "tiktok": {"goals": ["awareness", "engagement", "conversion"], "tones": ["friendly", "humorous", "emotional"], "followers": (1000, 65000), "reach": (0.35, 2.60), "caption": "POV: {hook} Meet the {product}. {cta} {tags}", "prompt": "9:16 short-form video storyboard for {product}: hook in first 2 seconds, hands-on demonstration, quick benefit reveal, creator-style framing", "tags": ["#ForYou #TryThis", "#TikTokMadeMeTryIt #LifeHack"]},
    "linkedin": {"goals": ["lead_generation", "awareness", "conversion", "retention"], "tones": ["professional", "persuasive", "friendly"], "followers": (500, 45000), "reach": (0.15, 0.85), "caption": "{hook} {product} helps teams {benefit}. {cta}", "prompt": "Clean professional editorial visual for {product}, diverse business team, modern workspace, confident realistic lighting, no text overlay", "tags": ["#BusinessGrowth #Innovation", "#CustomerExperience #Productivity"]},
    "email": {"goals": ["conversion", "retention", "lead_generation", "awareness"], "tones": ["persuasive", "professional", "friendly"], "followers": (800, 100000), "reach": (0.55, 0.98), "caption": "Subject: {hook}\n\n{product} can help you {benefit}. {cta}", "prompt": "Email hero image for {product}, uncluttered product-focused composition, accessible high contrast, room for subject line and CTA button", "tags": [""]},
}
HOOKS = ["A simpler way to make progress", "Your next small upgrade starts here", "Built for the moments that matter", "The practical choice for busy people"]
BENEFITS = ["save time without losing quality", "make a confident next step", "build a routine that lasts", "focus on the work that matters"]
CTAS = {"awareness": ["See how it works.", "Explore the idea today."], "engagement": ["What would you try first? Tell us below.", "Share this with someone who needs it."], "conversion": ["Shop now and make the switch.", "Start today and see the difference."], "lead_generation": ["Book a short demo to see the workflow.", "Request your tailored walkthrough."], "retention": ["Your next best step is waiting in your account.", "Return today and keep your momentum going."]}


def outcomes(platform: str, goal: str, followers: int, rng: random.Random) -> dict:
    impressions = max(100, int(followers * rng.uniform(*RULES[platform]["reach"])))
    reach = int(impressions * rng.uniform(0.70, 0.96))
    boost = 1.15 if goal in {"conversion", "lead_generation"} else 1.0
    interactions = max(1, int(impressions * rng.uniform(0.012, 0.095) * boost))
    if platform == "email":
        likes = comments = shares = 0
        opens = int(impressions * rng.uniform(0.18, 0.52))
    else:
        likes = int(interactions * rng.uniform(0.56, 0.78))
        comments = int(interactions * rng.uniform(0.05, 0.18))
        shares = max(0, interactions - likes - comments)
        opens = 0
    clicks = int(impressions * rng.uniform(0.003, 0.045) * boost)
    conversions = int(clicks * rng.uniform(0.02, 0.18) * boost)
    return {"impressions": impressions, "reach": reach, "likes": likes, "comments": comments, "shares": shares, "clicks": clicks, "opens": opens, "conversions": conversions, "engagement_rate": round((likes + comments + shares + clicks) / impressions, 6)}


def build_row(platform: str, number: int, rng: random.Random) -> dict:
    rule = RULES[platform]
    context, product = rng.choice(PRODUCTS)
    goal, tone = rng.choice(rule["goals"]), rng.choice(rule["tones"])
    caption = rule["caption"].format(hook=rng.choice(HOOKS), product=product, benefit=rng.choice(BENEFITS), cta=rng.choice(CTAS[goal]), tags=rng.choice(rule["tags"]))
    followers = rng.randint(*rule["followers"])
    published = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=rng.randint(0, 180), hours=rng.randint(0, 23))
    return {"record_id": f"SYN-{platform.upper()}-{number:04d}", "data_origin": "synthetic_bootstrap_v1_not_real_analytics", "platform": platform, "account_id": f"SYNTHETIC_DEMO_{platform.upper()}", "product_context": context, "caption": caption, "creative_prompt": rule["prompt"].format(product=product), "campaign_goal": goal, "tone": tone, "published_at": published.isoformat(), "followers_at_post_time": followers, **outcomes(platform, goal, followers, rng), "measurement_window_days": 7}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for platform in RULES:
        path = OUT_DIR / f"synthetic_{platform}_bootstrap_1000.csv"
        rng = random.Random(f"20260730:{platform}")
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(build_row(platform, i + 1, rng) for i in range(ROWS_PER_PLATFORM))
        print(f"wrote {ROWS_PER_PLATFORM:,} synthetic rows → {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
