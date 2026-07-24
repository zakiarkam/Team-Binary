"""calibration.py — Derive simulator base rates from the UCI Bank Marketing dataset.

Why this exists
---------------
The simulator's stage probabilities (P(open|sent), P(click|open), P(convert|click))
were originally hand-picked. An examiner can attack that as arbitrary. This module
fits those base rates from a real public campaign dataset (UCI Bank Marketing)
so the simulator parameters are data-derived, not subjective.

Mapping from Bank Marketing schema → our funnel
-----------------------------------------------
Bank Marketing has one row per customer-call with outcome `y` (subscribed term deposit).
It is not multi-touch, so we map a single contact to the funnel like this:

    sent     = every record                              (the bank dialled them)
    open     = duration >= 60 seconds                    (call lasted > 1 min — engaged)
    click    = duration >= 180 seconds                   (call lasted > 3 min — deep engagement)
    convert  = y == "yes"                                (subscribed)

Thresholds chosen because typical telemarketing "polite hang-up" is under 30s;
60s implies the prospect listened to the pitch (≈ email open); 180s implies a
real conversation (≈ click-through to product page).

This gives us realistic global P(open|sent), P(click|open), P(convert|click)
that we use as the *baseline* (multiplier = 1.0) calibration anchor. Per-segment
lifts in SEGMENT_PARAMS are then expressed relative to this anchor.

Run
---
    python -m src.calibration
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BANK_CSV = Path("data/raw/bank_marketing/bank-additional-full.csv")
OUT_PATH = Path("outputs/reports/calibration.csv")


def calibrate(csv_path: Path = BANK_CSV) -> dict[str, float]:
    """Return calibrated P(open|sent), P(click|open), P(convert|click), overall_conv."""
    df = pd.read_csv(csv_path, sep=";")

    n_sent = len(df)
    opened = df["duration"] >= 60
    n_open = int(opened.sum())

    clicked = df["duration"] >= 180
    n_click = int(clicked.sum())

    converters = df["y"] == "yes"
    n_convert = int((clicked & converters).sum())

    p_open = n_open / n_sent if n_sent else 0.0
    p_click_open = n_click / n_open if n_open else 0.0
    p_convert_click = n_convert / n_click if n_click else 0.0
    overall = (df["y"] == "yes").mean()

    return {
        "n_records":           n_sent,
        "p_open_given_sent":   round(p_open, 4),
        "p_click_given_open":  round(p_click_open, 4),
        "p_convert_given_click": round(p_convert_click, 4),
        "overall_conv_rate":   round(float(overall), 4),
    }


def main() -> None:
    if not BANK_CSV.exists():
        print(f"Bank Marketing CSV not found at {BANK_CSV}; skipping calibration.")
        return
    rates = calibrate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([rates]).to_csv(OUT_PATH, index=False)
    print("Calibrated base rates from UCI Bank Marketing:")
    for k, v in rates.items():
        print(f"  {k:<24} {v}")
    print(f"\nSaved: {OUT_PATH}")
    print(
        "\nInterpretation:\n"
        "  These rates anchor the simulator's loyal_customer segment "
        "(treated as 'average' user behaviour). Other segments scale\n"
        "  relative to this anchor: high_intent ≈ 1.4x, low_engagement ≈ 0.7x, "
        "price_sensitive ≈ 0.4x, new_cold_customer ≈ 0.9x."
    )


if __name__ == "__main__":
    main()
