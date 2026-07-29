"""Unified closed-loop orchestrator for the AI Marketing Orchestration system.

Runs the four modules as one pipeline and assembles a single result bundle:

    M1 Segmentation ──segments──▶ M2 Automation ──event logs──▶ M3 Analytics
          ▲                                                          │
          └────────────── content priorities (feedback) ◀───────────┤
                                                                     ▼
                                                          M4 Content Refinery

Design (see INTEGRATION_PLAN.md §5, option C):
  - M1 → M2 run LIVE on the real 8,000-user dataset (fast).
  - M3 funnel/conversion analytics on the REAL M2 campaign (single-platform email).
  - M3 multi-platform attribution study consumed from its own validated artifacts.
  - M4 content generated for the product, re-prioritised by M3's platform ranking.

Usable both as a CLI (`python orchestrator.py --full`) and as a library the
Streamlit app imports (`from orchestrator import run_full`).
"""

from __future__ import annotations

# Loaded first, on purpose: torch must initialise before xgboost or fitting
# an XGBoost model later in this process segfaults on macOS.
# See openmp_guard.py and the note at the top of config.py.
import openmp_guard  # noqa: F401  (import order matters)


import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from adapters import m2_to_m3, m3_to_m4
from adapters.segment_labels import validate_titles

ROOT = Path(__file__).resolve().parent
M1_DIR = ROOT / "modules" / "m1_segmentation"
M2_DIR = ROOT / "modules" / "m2_automation"
M3_DIR = ROOT / "modules" / "m3_analytics"
M3_REPORTS = M3_DIR / "outputs" / "reports"
M3_FIGURES = M3_DIR / "outputs" / "figures"
INTEGRATED = ROOT / "data" / "integrated"

M1_SEGMENTS = M1_DIR / "user_segments.csv"


def _log(cb: Callable[[str], None] | None, msg: str) -> None:
    print(msg, flush=True)
    if cb:
        cb(msg)


# --------------------------------------------------------------------------- #
# Module 1 — Segmentation
# --------------------------------------------------------------------------- #

def run_segmentation(log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Load Module 1's segment output and hand it to Module 2."""
    _log(log, "[M1] loading audience segments…")
    seg = pd.read_csv(M1_SEGMENTS)
    validate_titles(seg["segment_name"].unique())

    # Deliver to M2 exactly where it expects the file.
    dest = M2_DIR / "data" / "processed" / "user_segments.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    seg.to_csv(dest, index=False)

    counts = seg["segment_name"].value_counts()
    summary = {
        "n_users": int(len(seg)),
        "method": str(seg["segment_method"].iloc[0]) if "segment_method" in seg else "hybrid",
        "segment_counts": {k: int(v) for k, v in counts.items()},
        "mean_confidence": round(float(seg["segment_confidence"].mean()), 3)
        if "segment_confidence" in seg else None,
    }
    _log(log, f"[M1] {summary['n_users']:,} users across {len(counts)} segments "
              f"({summary['method']}).")
    return summary


# --------------------------------------------------------------------------- #
# Module 2 — Automation
# --------------------------------------------------------------------------- #

def _run_m2_step(args: list[str], log) -> None:
    proc = subprocess.run(
        [sys.executable, *args], cwd=M2_DIR,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"M2 step {' '.join(args)} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


def run_automation(log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Run M2: merge → ML conversion scores → 3-strategy campaign simulation."""
    _log(log, "[M2] merging users with segments…")
    _run_m2_step(["scripts/build_users_dataset.py"], log)
    _log(log, "[M2] training conversion-probability model…")
    _run_m2_step(["-m", "src.ml_model"], log)
    _log(log, "[M2] simulating fixed / trigger / hybrid strategies…")
    _run_m2_step(["scripts/run_comparison.py"], log)

    comparison = pd.read_csv(M2_DIR / "outputs" / "strategy_comparison.csv")
    events = pd.read_csv(M2_DIR / "outputs" / "event_logs.csv")

    best = comparison.sort_values("conversions_per_1000_sends", ascending=False).iloc[0]
    _log(log, f"[M2] best per-send efficiency: {best['strategy']} "
              f"({best['conversions_per_1000_sends']:.1f} conv/1k).")
    return {
        "strategy_comparison": comparison.to_dict(orient="records"),
        "best_strategy_by_efficiency": str(best["strategy"]),
        "events_path": str(M2_DIR / "outputs" / "event_logs.csv"),
        "n_events": int(len(events)),
    }, events


# --------------------------------------------------------------------------- #
# Module 3 — Analytics
# --------------------------------------------------------------------------- #

def _read_csv_records(path: Path) -> list[dict]:
    return pd.read_csv(path).to_dict(orient="records") if path.exists() else []


def _recommendation_summary(records: list[dict], source: str) -> dict[str, Any]:
    """Aggregate per-user recommendations + a diverse sample for display."""
    from collections import Counter
    n = len(records) or 1
    mix = dict(Counter(r["recommendation"] for r in records))
    top = sorted(records, key=lambda r: r["predicted_conversion"], reverse=True)[:20]
    risk = sorted(records, key=lambda r: r["drop_off_risk"], reverse=True)[:12]
    seen, sample = set(), []
    for r in top + risk:
        if r["user_id"] in seen:
            continue
        seen.add(r["user_id"])
        sample.append({k: r[k] for k in ("user_id", "predicted_conversion",
                       "drop_off_risk", "recommendation", "recommended_platform", "confidence")})
    return {
        "source": source,
        "n_users": len(records),
        "mix": mix,
        "avg_predicted_conversion": round(sum(r["predicted_conversion"] for r in records) / n, 4),
        "avg_drop_off_risk": round(sum(r["drop_off_risk"] for r in records) / n, 4),
        "high_intent_users": sum(1 for r in records if r["predicted_conversion"] >= 0.5),
        "at_risk_users": sum(1 for r in records if r["drop_off_risk"] >= 0.6),
        "sample": sample,
    }


def _per_user_recommendations(m2_events: pd.DataFrame,
                              log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Run Module 3's recommender (trained XGBoost models) on the REAL campaign users.

    Falls back to Module 3's committed validated cohort if the live run fails.
    """
    import sys as _sys
    records, source = None, ""
    try:
        _sys.path.insert(0, str(M3_DIR))
        from src.recommender import build_recommendations, validate_output  # type: ignore
        long = m2_to_m3.wide_to_long(m2_events)
        long["timestamp"] = pd.to_datetime(long["timestamp"])
        segments = m2_to_m3.segments_to_m3(pd.read_csv(M1_SEGMENTS))
        records = build_recommendations(long, segments, ROOT / "outputs" / "models")
        validate_output(records)
        source = "real campaign users (trained XGBoost models)"
        _log(log, f"[M3] per-user recommendations for {len(records):,} real users.")
    except Exception as exc:
        _log(log, f"[M3] live per-user run unavailable ({str(exc)[:80]}); using validated cohort.")
        records = json.loads((M3_REPORTS / "analytics_output.json").read_text())
        source = "validated analytics cohort (simulated)"
    finally:
        if str(M3_DIR) in _sys.path:
            _sys.path.remove(str(M3_DIR))
    return _recommendation_summary(records, source)


def run_analytics(m2_events: pd.DataFrame,
                  log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Real-data funnel on the M2 campaign + M3's validated multi-platform study."""
    _log(log, "[M3] building funnel from the real campaign…")
    real_funnel = m2_to_m3.funnel_from_wide(m2_events)
    real_drop = m2_to_m3.dropoffs(real_funnel)
    by_strategy = m2_to_m3.funnel_by_strategy(m2_events).reset_index().to_dict(orient="records")

    _log(log, "[M3] generating per-user recommendations…")
    recommendations = _per_user_recommendations(m2_events, log)

    _log(log, "[M3] loading validated attribution / prediction study…")
    analytics = {
        "real_funnel": real_funnel,
        "real_dropoffs": real_drop,
        "real_funnel_by_strategy": by_strategy,
        "recommendations": recommendations,
        # M3's validated multi-platform research artifacts (committed):
        "attribution_mae": _read_csv_records(M3_REPORTS / "attribution_mae.csv"),
        "model_metrics": _read_csv_records(M3_REPORTS / "model_metrics.csv"),
        "bootstrap_ci": _read_csv_records(M3_REPORTS / "bootstrap_ci.csv"),
        "strategy_comparison_sim": _read_csv_records(M3_REPORTS / "strategy_comparison.csv"),
        "validation_comparison": _read_csv_records(M3_REPORTS / "validation_comparison.csv"),
        "insights": [],
        "figures_dir": str(M3_FIGURES),
    }
    ins = M3_REPORTS / "insights.md"
    if ins.exists():
        analytics["insights"] = [
            l.lstrip("- ").strip() for l in ins.read_text().splitlines()
            if l.strip().startswith("-")
        ]
    _log(log, f"[M3] funnel: sent {real_funnel['sent']:,} → convert "
              f"{real_funnel['convert']:,}; {len(analytics['insights'])} insights.")
    return analytics


# --------------------------------------------------------------------------- #
# Module 4 — Content (priorities here; generation wired in content_service.py)
# --------------------------------------------------------------------------- #

def run_content(product_input: dict[str, Any],
                priorities: dict[str, Any],
                engine: str = "fast",
                with_semantic: bool = True,
                log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Generate platform content for the product, re-prioritised by analytics.

    Delegates to content_service (Phase 2). Falls back to any cached assets so
    the loop always returns something.
    """
    try:
        import content_service
    except Exception as exc:  # pragma: no cover
        _log(log, f"[M4] content_service unavailable ({exc}); using cached assets.")
        return _cached_content(product_input, priorities)

    return content_service.generate(
        product_input, priorities, engine=engine,
        with_semantic=with_semantic, log=log,
    )


def _cached_content(product_input, priorities) -> dict[str, Any]:
    import config
    path = config.GENERATED_CSV
    assets = pd.read_csv(path).to_dict(orient="records") if Path(path).exists() else []
    return {"assets": assets, "priorities": priorities, "engine": "cached", "product": product_input}


# --------------------------------------------------------------------------- #
# Full closed loop
# --------------------------------------------------------------------------- #

def run_full(product_input: dict[str, Any] | None = None,
             with_content: bool = True,
             content_engine: str = "fast",
             log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Run M1 → M2 → M3 → (feedback) → M4 and assemble one result bundle."""
    t0 = time.time()
    if product_input is None:
        product_input = json.loads((ROOT / "input.json").read_text())

    segmentation = run_segmentation(log)
    automation, m2_events = run_automation(log)
    analytics = run_analytics(m2_events, log)

    _log(log, "[loop] deriving content priorities from analytics…")
    priorities = m3_to_m4.build_content_priorities(M3_REPORTS)

    content: dict[str, Any] = {}
    if with_content:
        content = run_content(product_input, priorities, engine=content_engine, log=log)

    bundle = {
        "product_input": product_input,
        "segmentation": segmentation,
        "automation": automation,
        "analytics": analytics,
        "content_priorities": priorities,
        "content": content,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    INTEGRATED.mkdir(parents=True, exist_ok=True)
    (INTEGRATED / "run_bundle.json").write_text(json.dumps(bundle, indent=2, default=str))
    _log(log, f"[loop] done in {bundle['elapsed_seconds']}s → data/integrated/run_bundle.json")
    return bundle


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Run the unified marketing orchestration loop.")
    p.add_argument("--full", action="store_true", help="Run the whole M1→M2→M3→M4 loop.")
    p.add_argument("--no-content", action="store_true", help="Skip the M4 content stage.")
    p.add_argument("--engine", choices=["fast", "phi3"], default="fast",
                   help="Content generation engine (default: fast template engine).")
    p.add_argument("--product-json", type=str, default=None,
                   help="Path to a JSON product brief (defaults to input.json).")
    args = p.parse_args()

    product_input = None
    if args.product_json:
        product_input = json.loads(Path(args.product_json).read_text())

    run_full(product_input=product_input,
             with_content=not args.no_content,
             content_engine=args.engine)


if __name__ == "__main__":
    main()
