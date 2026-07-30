"""Test whether a per-platform tone register can be learned from the data.

Module 4 adapts one brand voice into a per-platform register using a declared
map (config.PLATFORM_TONE_REGISTER). That map is an editorial heuristic, and
the obvious objection is "why not learn it instead?". This script is the answer:
it checks whether any corpus in this repository carries a relationship between
platform and tone at all.

Method: take the corpus that has both a `platform` column and post text, run the
trained tone classifier over a balanced sample, and test the platform x tone
contingency table for independence (chi-square).

Result on data/raw/datasets/Social Media Engagement Dataset.csv:

    chi2 = 9.63, dof = 8, p = 0.292  ->  independent

The predicted tone distribution is within a few points of identical on all five
platforms, so there is no platform-voice signal to learn. Three reasons, all
visible in the data:

  1. The text is templated — the same sentence frames recycled with different
     brand names, lengths spanning only 68-181 characters (median 118).
  2. The posts are consumer chatter ("Just tried the X from Y"), not brand
     marketing copy, so they carry no brand voice to measure.
  3. Its platforms are YouTube/Facebook/Twitter/Reddit/Instagram; M4 targets
     instagram/tiktok/linkedin/email, so only one overlaps.

This is the same situation as the engagement model documented in config.py: a
property of the available data, not a fixable modelling failure. The register
map therefore stays a declared operating point, reported as a heuristic, until
a corpus of real brand posts labelled by platform exists to tune it against.

Run:  PYTHONPATH=.:modules/m4_content python scripts/probe_platform_tone_signal.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd
from scipy.stats import chi2_contingency

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "modules" / "m4_content"))

import config  # noqa: E402  (needs the path above)

# The only corpus here carrying both a platform label and post text.
CORPUS = config.RAW_DATASETS / "Social Media Engagement Dataset.csv"

# Balanced per platform, so a platform with more rows cannot dominate the table.
SAMPLE_PER_PLATFORM = 400
RANDOM_STATE = 42


def main() -> int:
    if not CORPUS.exists():
        print(f"Corpus not found: {CORPUS}")
        return 1

    if not config.TONE_MODEL_PKL.exists():
        print(f"Tone model not found: {config.TONE_MODEL_PKL}\n"
              "Train it first: python scripts/train_models.py")
        return 1

    frame = pd.read_csv(CORPUS)

    missing = {"platform", "text_content"} - set(frame.columns)
    if missing:
        print(f"Corpus is missing columns: {sorted(missing)}")
        return 1

    smallest = frame["platform"].value_counts().min()
    if smallest < SAMPLE_PER_PLATFORM:
        print(f"Smallest platform has {smallest} rows; sampling that many "
              "instead so the table stays balanced.")

    per_platform = min(SAMPLE_PER_PLATFORM, int(smallest))

    sample = (
        frame
        .groupby("platform", group_keys=False)
        .sample(per_platform, random_state=RANDOM_STATE)
        .reset_index(drop=True)
    )

    model = joblib.load(config.TONE_MODEL_PKL)
    sample["predicted_tone"] = model.predict(
        sample["text_content"].astype(str)
    )

    print(f"Corpus: {CORPUS.name}  ({len(frame)} rows, "
          f"{per_platform} sampled per platform)\n")

    shares = pd.crosstab(
        sample["platform"],
        sample["predicted_tone"],
        normalize="index",
    ).round(3)

    print("Predicted tone distribution per platform:")
    print(shares)

    counts = pd.crosstab(
        sample["platform"],
        sample["predicted_tone"],
    )

    chi2, p_value, dof, _ = chi2_contingency(counts)

    print(f"\nchi-square test of independence: "
          f"chi2={chi2:.2f}, dof={dof}, p={p_value:.3f}")

    if p_value < 0.05:
        print("=> platform and tone are DEPENDENT: there is signal here, and "
              "the register map could be derived from data instead of declared.")
    else:
        print("=> platform and tone are INDEPENDENT: no platform-voice signal "
              "in this corpus, so the register map stays a declared heuristic.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
