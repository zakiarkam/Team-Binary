#!/usr/bin/env python
"""Retrain the Module 4 models — the safe entry point.

Why this script exists rather than calling the trainers directly
----------------------------------------------------------------
On macOS, fitting an XGBoost model inside a process that has PyTorch loaded
segfaults the interpreter outright (see the note at the top of config.py). The
only mitigation that actually works is a single-threaded OpenMP runtime, and
that must be set *before* any numeric library is imported — which cannot be done
reliably from inside a library module.

So this script sets it as its very first action, then imports and trains. Run it
whenever the model artifacts under `models/` are missing or stale:

    venv/bin/python scripts/train_models.py            # all models
    venv/bin/python scripts/train_models.py --only goal_tone
"""

from __future__ import annotations

# ── MUST come before every other import ──────────────────────────────────────
import os

os.environ["PIPELINE_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# ─────────────────────────────────────────────────────────────────────────────

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(1, str(Path(__file__).resolve().parents[1] / "modules" / "m4_content"))

import config  # noqa: E402


def _report(paths: dict[str, Path]) -> None:
    for label, path in paths.items():
        mark = "✓" if path.exists() else "✗"
        size = f"{path.stat().st_size / 1024:.0f} KB" if path.exists() else "missing"
        print(f"   {mark} {label:<24} {size}")


def train_goal_tone() -> None:
    """Campaign-goal and tone classifiers (TF-IDF/LogReg vs SBERT/XGBoost)."""
    print("\n── Goal / tone classifiers " + "─" * 40)
    import goal_tone

    started = time.perf_counter()
    selection = goal_tone.train()
    print(f"   selected: {json.dumps(selection)}")
    print(f"   took {time.perf_counter() - started:.1f}s")

    # A label encoder only exists for the Sentence-BERT + XGBoost path; the
    # TF-IDF pipeline handles its own labels, and the trainer deletes any stale
    # encoder when it wins. So a missing encoder is expected, not a failure —
    # only report the ones the selected models actually need.
    artifacts = {"goal model": config.GOAL_MODEL_PKL,
                 "tone model": config.TONE_MODEL_PKL}
    if selection.get("best_goal_model_type") == "sentencebert_xgboost":
        artifacts["goal encoder"] = config.GOAL_ENCODER_PKL
    if selection.get("best_tone_model_type") == "sentencebert_xgboost":
        artifacts["tone encoder"] = config.TONE_ENCODER_PKL
    _report(artifacts)

    metrics_path = config.GOAL_TONE_METRICS_JSON
    if metrics_path.exists():
        data = json.loads(metrics_path.read_text())
        print(f"   trained on {data.get('dataset_rows', '?')} labelled rows "
              "— small, so treat single-split accuracy with caution")


def train_engagement() -> None:
    """Engagement regressor used to rank generated content."""
    print("\n── Engagement regressor " + "─" * 43)
    import engagement

    if not hasattr(engagement, "train"):
        print("   engagement.train() not available — skipped")
        return

    started = time.perf_counter()
    engagement.train()
    print(f"   took {time.perf_counter() - started:.1f}s")
    _report({
        "engagement model": config.ENGAGEMENT_MODEL_PKL,
        "feature columns": config.ENGAGEMENT_FEATURES_PKL,
    })


TRAINERS = {"goal_tone": train_goal_tone, "engagement": train_engagement}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=sorted(TRAINERS), action="append",
                    help="Train just this model (repeatable)")
    args = ap.parse_args()

    chosen = args.only or list(TRAINERS)
    print(f"Training: {', '.join(chosen)}")
    print(f"OMP_NUM_THREADS={os.environ['OMP_NUM_THREADS']} "
          "(single-threaded on purpose — see config.py)")

    failed = []
    for name in chosen:
        try:
            TRAINERS[name]()
        except Exception as exc:
            failed.append(name)
            print(f"   ✗ {name} failed: {type(exc).__name__}: {exc}")

    if failed:
        print(f"\n✗ Failed: {', '.join(failed)}")
        return 1

    print("\n✓ All requested models trained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
