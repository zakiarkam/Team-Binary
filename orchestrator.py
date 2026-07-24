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


def run_analytics(m2_events: pd.DataFrame,
                  log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Real-data funnel on the M2 campaign + M3's validated multi-platform study."""
    _log(log, "[M3] building funnel from the real campaign…")
    real_funnel = m2_to_m3.funnel_from_wide(m2_events)
    real_drop = m2_to_m3.dropoffs(real_funnel)
    by_strategy = m2_to_m3.funnel_by_strategy(m2_events).reset_index().to_dict(orient="records")

    _log(log, "[M3] loading validated attribution / prediction study…")
    analytics = {
        "real_funnel": real_funnel,
        "real_dropoffs": real_drop,
        "real_funnel_by_strategy": by_strategy,
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
