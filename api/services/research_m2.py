"""Module 2's actual research output — the controlled-simulation results.

Distinct from api/services/campaigns.py, which re-runs the three policies live
against this site's visitors. This module reads the committed result files
that Module 2's own pipeline (modules/m2_automation/scripts/*) wrote, so the
numbers shown here are exactly the ones the research report cites and can
never drift from them.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = REPO_ROOT / "modules" / "m2_automation" / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

STRATEGY_COMPARISON_PATH = OUTPUTS_DIR / "strategy_comparison.csv"
MULTISEED_SUMMARY_PATH = OUTPUTS_DIR / "multiseed_summary.csv"

# The 6 figures make_figures.py produces. Also the allowlist the figure route
# validates against — nothing outside this exact set is ever served.
FIGURE_NAMES = (
    "strategy_comparison_bars.png",
    "funnel_by_strategy.png",
    "sparsity_sweep.png",
    "complexity_vs_performance.png",
    "hybrid_routing_breakdown.png",
    "ml_model_diagnostics.png",
)


def figure_path(name: str) -> Path | None:
    """Resolve a figure filename to its file, or None if not in the allowlist
    or not present on disk."""
    if name not in FIGURE_NAMES:
        return None
    path = FIGURES_DIR / name
    return path if path.is_file() else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _strategy_comparison_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _read_csv(STRATEGY_COMPARISON_PATH):
        rows.append({
            "strategy": row["strategy"],
            "sends": int(row["messages_sent"]),
            "open_rate": float(row["open_rate"]),
            "ctr": float(row["ctr"]),
            "conv_rate": float(row["conversion_rate"]),
            "conv_per_1000": float(row["conversions_per_1000_sends"]),
            "days_to_convert": float(row["avg_days_to_convert"]),
            "complexity": int(row["operational_complexity"]),
        })
    return rows


def _multiseed_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _read_csv(MULTISEED_SUMMARY_PATH):
        rows.append({
            "strategy": row["strategy"],
            "conv_per_1k_mean": float(row["conv_per_1k_mean"]),
            "conv_per_1k_std": float(row["conv_per_1k_std"]),
            "conv_rate_mean": float(row["conv_rate_mean"]),
            "conv_rate_std": float(row["conv_rate_std"]),
        })
    return rows


def get_results() -> dict[str, Any]:
    """Module 2's research output, read fresh from disk on every call.

    Returns available=False (rather than raising) when the pipeline hasn't
    been run yet, so the frontend can degrade gracefully — the same pattern
    the live campaign view uses for "no campaigns yet".
    """
    if not STRATEGY_COMPARISON_PATH.is_file() or not MULTISEED_SUMMARY_PATH.is_file():
        return {
            "available": False,
            "strategy_comparison": [],
            "multiseed_summary": [],
            "figures": [],
            "meta": None,
        }

    return {
        "available": True,
        "strategy_comparison": _strategy_comparison_rows(),
        "multiseed_summary": _multiseed_rows(),
        "figures": [name for name in FIGURE_NAMES if (FIGURES_DIR / name).is_file()],
        "meta": {
            "source": "controlled simulation, 20 seeds, calibrated intent uplift 2.5x",
            "note": "Research measurement — distinct from the live operational view on this page.",
        },
    }
