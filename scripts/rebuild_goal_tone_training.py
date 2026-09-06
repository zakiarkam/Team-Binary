#!/usr/bin/env python
"""Rebuild the goal/tone training corpus using per-target confidence.

The existing file requires a row to clear *both* the goal and the tone
confidence bar, which left 114 rows — and only 3 examples of `engagement`. But
the two classifiers are trained separately, so a row whose tone label is
uncertain is still perfectly good training data for the goal model.

Filtering per target instead:

    campaign_goal   114 → ~453 rows
    tone            114 → ~173 rows

A row that clears one bar but not the other is kept, with the uncertain label
left blank; the trainer drops blanks per target. Nothing is relabelled and no
threshold is lowered — this only stops one target's uncertainty from discarding
the other target's good data.

Thresholds come from scripts/tune_goal_tone_threshold.py, which cross-validates
each candidate. 0.65 was chosen over the marginally higher-scoring 0.70 because
0.70 leaves two tone classes with too few examples to evaluate at all.

    venv/bin/python scripts/rebuild_goal_tone_training.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "modules" / "m4_content"))

RESEARCH_CSV = ROOT / "data" / "processed" / "goal_tone_dataset_research.csv"
TRAINING_CSV = ROOT / "data" / "processed" / "goal_tone_dataset_training.csv"

TARGETS = {"campaign_goal": 0.65, "tone": 0.65}
MIN_TEXT_LENGTH = 10


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goal-threshold", type=float, default=TARGETS["campaign_goal"])
    ap.add_argument("--tone-threshold", type=float, default=TARGETS["tone"])
    ap.add_argument("--out", default=str(TRAINING_CSV))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not RESEARCH_CSV.exists():
        print(f"✗ {RESEARCH_CSV} not found", file=sys.stderr)
        return 1

    df = pd.read_csv(RESEARCH_CSV)
    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df = df[df["text"].str.len() >= MIN_TEXT_LENGTH]

    thresholds = {"campaign_goal": args.goal_threshold, "tone": args.tone_threshold}
    out = pd.DataFrame({"row_id": df.get("row_id", range(len(df))), "text": df["text"]})

    for target, threshold in thresholds.items():
        conf = pd.to_numeric(df.get(f"{target}_confidence"), errors="coerce").fillna(0)
        label = df[target].fillna("").astype(str).str.lower().str.strip()

        # Blank out the label where we are not confident enough to learn from it.
        #
        # `needs_review` is deliberately NOT used as a filter. It is set on 575
        # of 689 rows, so it is closer to a blanket flag than a quality signal,
        # and cross-validation says excluding those rows makes both classifiers
        # worse while discarding three quarters of the corpus:
        #
        #   campaign_goal   453 rows macro-F1 0.574  vs  111 rows macro-F1 0.563
        #   tone            173 rows macro-F1 0.797  vs   92 rows macro-F1 0.715
        #
        # Confidence is the better gate, and it is the one kept.
        keep = (conf >= threshold) & (label != "") & (label != "nan")

        out[target] = label.where(keep, "")
        print(f"  {target:<14} {int(keep.sum()):>4} usable rows "
              f"(threshold {threshold:.2f})")

    out["joint_label_confidence"] = pd.to_numeric(
        df.get("joint_label_confidence"), errors="coerce").fillna(0).round(4)

    # A row with neither label is dead weight.
    out = out[(out["campaign_goal"] != "") | (out["tone"] != "")]

    print(f"\n  corpus: {len(out)} rows "
          f"(was {sum(1 for _ in open(TRAINING_CSV)) - 1 if TRAINING_CSV.exists() else 0})")
    for target in thresholds:
        counts = out[out[target] != ""][target].value_counts()
        print(f"  {target}: {counts.to_dict()}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"\n✓ wrote {args.out}")
    print("  Retrain with: venv/bin/python scripts/train_models.py --only goal_tone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
