#!/usr/bin/env python
"""Choose the goal/tone label-confidence threshold by evidence, not by guess.

The labelled corpus is auto-labelled, and each row carries a confidence. The
training set is currently everything above 0.65 (goal) / 0.62 (tone), which
leaves 114 rows — and only 3 examples of `engagement`. A class with 3 examples
cannot be learned, which is exactly why macro-F1 sits far below accuracy.

Raising the cut-off gives cleaner labels and fewer of them; lowering it gives
more labels and more noise. That is an empirical question, so this sweeps the
threshold and cross-validates at each step.

Macro-F1 is the metric to optimise here, not accuracy: accuracy is dominated by
`awareness`, which is over half the corpus, so a model that ignored every other
class entirely would still look respectable.

    venv/bin/python scripts/tune_goal_tone_threshold.py
"""

from __future__ import annotations

import os

# Must precede any numeric import — see config.py.
os.environ.setdefault("PIPELINE_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESEARCH_CSV = ROOT / "data" / "processed" / "goal_tone_dataset_research.csv"
TARGETS = ("campaign_goal", "tone")


def evaluate(df: pd.DataFrame, target: str, folds: int = 5) -> dict | None:
    """Stratified cross-validated F1 for one target on one filtered corpus."""
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import f1_score

    from goal_tone import create_tfidf_pipeline

    y = df[target].astype(str)
    counts = y.value_counts()

    # Every class needs at least `folds` members for stratified CV to be valid.
    usable = counts[counts >= folds].index
    sub = df[y.isin(usable)]
    if sub[target].nunique() < 2 or len(sub) < folds * 2:
        return None

    x = sub["text"].astype(str)
    y = sub[target].astype(str)
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)

    try:
        pred = cross_val_predict(create_tfidf_pipeline(), x, y, cv=cv)
    except ValueError:
        return None

    return {
        "rows": int(len(sub)),
        "classes": int(y.nunique()),
        "dropped_classes": int(counts.size - len(usable)),
        "weighted_f1": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
        "macro_f1": round(float(f1_score(y, pred, average="macro", zero_division=0)), 4),
        "accuracy": round(float((pred == y).mean()), 4),
        "support": counts.to_dict(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--steps", type=float, nargs="*",
                    default=[0.0, 0.40, 0.50, 0.55, 0.60, 0.65, 0.70])
    args = ap.parse_args()

    if not RESEARCH_CSV.exists():
        print(f"✗ {RESEARCH_CSV} not found", file=sys.stderr)
        return 1

    df = pd.read_csv(RESEARCH_CSV)
    print(f"Full labelled corpus: {len(df)} rows\n")

    for target in TARGETS:
        conf_col = f"{target}_confidence"
        if conf_col not in df.columns:
            print(f"(no {conf_col} column — skipping {target})")
            continue

        print(f"── {target} " + "─" * (62 - len(target)))
        print(f"{'threshold':>10} {'rows':>6} {'classes':>8} {'accuracy':>9} "
              f"{'weighted F1':>12} {'macro F1':>9}")

        results = []
        for threshold in args.steps:
            subset = df[pd.to_numeric(df[conf_col], errors="coerce").fillna(0) >= threshold]
            scores = evaluate(subset, target, folds=args.folds)
            if scores is None:
                print(f"{threshold:>10.2f} {'—':>6} {'too few usable rows':>40}")
                continue
            results.append((threshold, scores))
            print(f"{threshold:>10.2f} {scores['rows']:>6} {scores['classes']:>8} "
                  f"{scores['accuracy']:>9.3f} {scores['weighted_f1']:>12.3f} "
                  f"{scores['macro_f1']:>9.3f}")

        if results:
            best = max(results, key=lambda r: r[1]["macro_f1"])
            current = next((r for r in results if abs(r[0] - 0.65) < 1e-9), None)
            print(f"\n  best macro-F1 at threshold {best[0]:.2f}: "
                  f"{best[1]['macro_f1']:.3f} over {best[1]['rows']} rows")
            if current and best[0] != current[0]:
                delta = best[1]["macro_f1"] - current[1]["macro_f1"]
                print(f"  current threshold 0.65 gives {current[1]['macro_f1']:.3f} "
                      f"({delta:+.3f} difference)")
            print(f"  class support at the best threshold: {best[1]['support']}")
            if best[1]["dropped_classes"]:
                print(f"  {best[1]['dropped_classes']} class(es) had fewer than "
                      f"{args.folds} examples and were excluded from CV — they "
                      "cannot be evaluated, and should not be claimed.")
        print()

    print("Macro-F1 weights every class equally, so it is the number that shows "
          "whether the rare\nclasses are learned at all. Accuracy is dominated by "
          "`awareness` and will look good\neither way.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
