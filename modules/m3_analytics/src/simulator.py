"""
M1 — Event log simulator.

Generates three CSVs that match the schemas in CLAUDE.md §5:

    user_segments.csv           — Person 1's contract output (stand-in)
    event_logs.csv              — Person 2's contract output (stand-in)
    ground_truth_influence.csv  — true per-platform influence used to validate
                                  attribution models in M3

Run:
    python -m src.simulator --users 2000 --out data/simulated/
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


# ---- Configuration -------------------------------------------------------- #

# Segment proportions reflect a typical newly-launched product:
# mostly new cold + low-engagement users, fewer high-intent, small price-sensitive slice.
SEGMENT_PROPS = {
    "new_cold_customer": 0.35,
    "low_engagement":    0.25,
    "loyal_customer":    0.20,
    "high_intent":       0.12,
    "price_sensitive":   0.08,
}

# Per-segment journey length (inclusive range) and base stage probabilities.
# `base_open`        = P(open | sent)
# `base_click`       = P(click | open)
# `base_convert`     = P(convert | click)
#
# Calibration: loyal_customer is treated as the "average user" anchor. Its
# P(convert | click) = 0.20 matches the empirical rate fitted from UCI
# Bank Marketing in src/calibration.py (n=41,188 records, P(convert|click)=0.198).
# Other segments scale relative to loyal_customer: high_intent ≈ 2x, price_sensitive ≈ 0.25x.
# Open and click rates are lower than Bank Marketing's because digital channels
# (email, social) have lower engagement than answered phone calls; the
# inter-segment ratios are the data-derived part, not the absolute levels.
SEGMENT_PARAMS = {
    "new_cold_customer": {"touches": (2, 5), "open": 0.40, "click": 0.25, "convert": 0.08},
    "low_engagement":    {"touches": (1, 4), "open": 0.30, "click": 0.20, "convert": 0.10},
    "loyal_customer":    {"touches": (2, 6), "open": 0.45, "click": 0.30, "convert": 0.20},  # anchor
    "high_intent":       {"touches": (3, 8), "open": 0.65, "click": 0.45, "convert": 0.40},
    "price_sensitive":   {"touches": (1, 3), "open": 0.20, "click": 0.10, "convert": 0.05},
}

PLATFORMS = ["email", "facebook", "instagram", "linkedin", "tiktok"]

# Per-segment platform mix (rows must sum to 1.0, same order as PLATFORMS).
# Reflects realistic targeting: new cold customers on Instagram + TikTok,
# high-intent on LinkedIn + email, price-sensitive reached via email + Facebook offers.
PLATFORM_MIX = {
    "new_cold_customer": [0.10, 0.15, 0.35, 0.05, 0.35],
    "low_engagement":    [0.20, 0.20, 0.25, 0.10, 0.25],
    "loyal_customer":    [0.30, 0.15, 0.25, 0.15, 0.15],
    "high_intent":       [0.35, 0.05, 0.10, 0.45, 0.05],
    "price_sensitive":   [0.40, 0.25, 0.20, 0.05, 0.10],
}

# Per-platform multiplier applied to ALL stage probabilities.
# Visual / professional platforms convert better; broad social (facebook) lowest.
# This is what attribution models will try to recover.
PLATFORM_POWER = {
    "email":     1.00,
    "facebook":  0.80,
    "instagram": 1.20,
    "linkedin":  1.10,
    "tiktok":    1.00,
}

# Default channel per platform. A small fraction of facebook/instagram traffic
# is paid (channel = "ad"), and a small fraction of email delivers an offer
# (channel = "offer"). Everything else uses the default below.
PLATFORM_TO_CHANNEL = {
    "email":     "email",
    "facebook":  "social",
    "instagram": "social",
    "linkedin":  "social",
    "tiktok":    "social",
}
PAID_SOCIAL_PLATFORMS = {"facebook", "instagram"}
PAID_SOCIAL_RATE = 0.20            # 20% of FB/IG touches are paid ads
OFFER_PLATFORMS = {"email"}
OFFER_RATE = 0.10                  # 10% of those touches deliver an offer

# Strategy mix and conversion lift. Hybrid > Trigger > Fixed by design,
# so M5 has a strategy-comparison story to tell.
STRATEGY_LIFTS = {"fixed": 1.00, "trigger": 1.15, "hybrid": 1.30}
STRATEGY_PROPS = {"fixed": 1 / 3, "trigger": 1 / 3, "hybrid": 1 / 3}

JOURNEY_WINDOW_DAYS = 14            # all touches happen within last N days
REFERENCE_DATE = datetime(2026, 5, 1, 12, 0, 0)


# ---- Helpers -------------------------------------------------------------- #

@dataclass
class Touch:
    """A single touchpoint with all the events it produced."""
    user_id: str
    timestamp: datetime
    channel: str
    platform: str
    campaign_id: str
    strategy: str
    opened: bool
    clicked: bool
    converted: bool


def _pick_channel(platform: str, rng: np.random.Generator) -> str:
    """Map platform → channel with paid-social and offer overrides."""
    if platform in PAID_SOCIAL_PLATFORMS and rng.random() < PAID_SOCIAL_RATE:
        return "ad"
    if platform in OFFER_PLATFORMS and rng.random() < OFFER_RATE:
        return "offer"
    return PLATFORM_TO_CHANNEL[platform]


def _stage_probs(segment: str, platform: str, strategy: str) -> tuple[float, float, float]:
    """Return (P_open, P_click_given_open, P_convert_given_click), clipped to [0, 1]."""
    base = SEGMENT_PARAMS[segment]
    mult = PLATFORM_POWER[platform]
    lift = STRATEGY_LIFTS[strategy]
    p_open = min(1.0, base["open"] * mult)
    p_click = min(1.0, base["click"] * mult)
    p_convert = min(1.0, base["convert"] * mult * lift)
    return p_open, p_click, p_convert


def _confidence(segment: str, n_touches: int) -> float:
    """Segment confidence: higher for more interactions and clearer segments."""
    base = {"new_cold_customer": 0.55, "low_engagement": 0.65, "loyal_customer": 0.75,
            "high_intent": 0.85, "price_sensitive": 0.70}[segment]
    bonus = min(0.15, 0.03 * n_touches)        # up to +0.15 for 5+ touches
    return round(min(0.99, base + bonus), 3)


# ---- Core simulation ------------------------------------------------------ #

def simulate(n_users: int, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Run the simulation. Returns three DataFrames keyed by output name."""
    rng = np.random.default_rng(seed)

    segments_list = list(SEGMENT_PROPS.keys())
    segment_probs = list(SEGMENT_PROPS.values())
    strategies_list = list(STRATEGY_PROPS.keys())
    strategy_probs = list(STRATEGY_PROPS.values())

    user_rows: list[dict] = []
    event_rows: list[dict] = []
    # Ground truth: count platform appearances in converting journeys.
    gt_counts: dict[str, int] = {p: 0 for p in PLATFORMS}

    for i in range(n_users):
        user_id = f"U{i:05d}"
        segment = rng.choice(segments_list, p=segment_probs)
        strategy = rng.choice(strategies_list, p=strategy_probs)
        lo, hi = SEGMENT_PARAMS[segment]["touches"]
        n_touches = int(rng.integers(lo, hi + 1))

        # Generate ordered touches across the journey window.
        offsets_hours = sorted(
            rng.uniform(0, JOURNEY_WINDOW_DAYS * 24, size=n_touches)
        )
        platforms_for_user = rng.choice(
            PLATFORMS, size=n_touches, p=PLATFORM_MIX[segment]
        )

        touches: list[Touch] = []
        for k in range(n_touches):
            platform = str(platforms_for_user[k])
            channel = _pick_channel(platform, rng)
            ts = REFERENCE_DATE - timedelta(
                days=JOURNEY_WINDOW_DAYS,
                hours=-float(offsets_hours[k]),
            )
            campaign_id = f"{platform}_{strategy}_v1"

            p_open, p_click, p_convert = _stage_probs(segment, platform, strategy)
            opened = bool(rng.random() < p_open)
            clicked = bool(opened and rng.random() < p_click)
            converted = bool(clicked and rng.random() < p_convert)

            touches.append(Touch(
                user_id=user_id, timestamp=ts, channel=channel, platform=platform,
                campaign_id=campaign_id, strategy=strategy,
                opened=opened, clicked=clicked, converted=converted,
            ))

        user_converted = any(t.converted for t in touches)
        if user_converted:
            # Weight each platform's ground-truth credit by its true power
            # multiplier (PLATFORM_POWER) instead of a flat +1. Rationale:
            # the generative process makes Instagram (1.20) and LinkedIn (1.10)
            # convert at higher rates than Facebook (0.80); a flat +1 erases
            # that signal and yields near-uniform ground truth, which
            # artificially favours first-touch attribution. Power-weighting
            # forces attribution models to discriminate strong vs weak
            # platforms, which is the research question.
            for t in touches:
                gt_counts[t.platform] += PLATFORM_POWER[t.platform]

        # Emit event rows: always 'sent', then conditional on stage outcomes.
        for t in touches:
            base = {
                "user_id": t.user_id,
                "timestamp": t.timestamp.isoformat(),
                "channel": t.channel,
                "platform": t.platform,
                "campaign_id": t.campaign_id,
                "strategy": t.strategy,
            }
            event_rows.append({**base, "event_type": "sent"})
            if t.opened:
                event_rows.append({**base, "event_type": "open"})
            if t.clicked:
                event_rows.append({**base, "event_type": "click"})
            if t.converted:
                event_rows.append({**base, "event_type": "convert"})

        user_rows.append({
            "user_id": user_id,
            "segment": segment,
            "confidence": _confidence(segment, n_touches),
        })

    user_segments = pd.DataFrame(user_rows)
    event_logs = pd.DataFrame(event_rows).sort_values(
        ["user_id", "timestamp"]
    ).reset_index(drop=True)

    total = sum(gt_counts.values()) or 1
    ground_truth = pd.DataFrame([
        {"platform": p, "true_influence": round(gt_counts[p] / total, 4)}
        for p in PLATFORMS
    ])

    return {
        "user_segments": user_segments,
        "event_logs": event_logs,
        "ground_truth_influence": ground_truth,
    }


def write_outputs(frames: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items():
        path = out_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  wrote {path}  ({len(df):,} rows)")


def _print_summary(frames: dict[str, pd.DataFrame]) -> None:
    events = frames["event_logs"]
    users = frames["user_segments"]
    gt = frames["ground_truth_influence"]

    n_users = len(users)
    n_events = len(events)
    counts = events["event_type"].value_counts()
    sent = int(counts.get("sent", 0))
    opens = int(counts.get("open", 0))
    clicks = int(counts.get("click", 0))
    converts = int(counts.get("convert", 0))

    print("\nFunnel (raw counts):")
    print(f"  sent    {sent:>8,}")
    print(f"  open    {opens:>8,}   ({opens / sent:.1%} of sent)")
    print(f"  click   {clicks:>8,}   ({clicks / sent:.1%} of sent)")
    print(f"  convert {converts:>8,}   ({converts / sent:.1%} of sent)")

    # User-level conversion rate
    converters = events[events["event_type"] == "convert"]["user_id"].nunique()
    print(f"\nUsers: {n_users:,}   converters: {converters:,}   "
          f"({converters / n_users:.1%} of users)")

    print("\nSegment mix:")
    print(users["segment"].value_counts(normalize=True).round(3).to_string())

    print("\nGround-truth platform influence:")
    print(gt.sort_values("true_influence", ascending=False).to_string(index=False))


# ---- CLI ------------------------------------------------------------------ #

def main() -> None:
    parser = argparse.ArgumentParser(description="M1 simulator for Person 3 analytics.")
    parser.add_argument("--users", type=int, default=10000,
                        help="number of users to simulate (default: 10000)")
    parser.add_argument("--out", type=str, default="data/simulated",
                        help="output directory for CSVs")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()

    print(f"Simulating {args.users:,} users (seed={args.seed})...")
    frames = simulate(n_users=args.users, seed=args.seed)
    write_outputs(frames, Path(args.out))
    _print_summary(frames)


if __name__ == "__main__":
    main()
