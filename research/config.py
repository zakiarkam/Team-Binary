"""Shared paths, seeds and plotting style for the experiments."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RESEARCH = ROOT / "research"
RESULTS = RESEARCH / "results"
FIGURES = RESEARCH / "figures"

#: Module 1's research corpus — the 8,000 users the study is built on.
M1_DATASET = ROOT / "modules" / "m1_segmentation" / "digital_marketing_campaign_dataset.csv"

#: Module 2's inputs and its own simulator.
M2_DIR = ROOT / "modules" / "m2_automation"
M2_USERS = M2_DIR / "data" / "processed" / "users_with_ml_scores.csv"

#: Module 3's simulated journeys and the ground-truth channel influence that
#: makes attribution *scorable* rather than merely comparable.
M3_DIR = ROOT / "modules" / "m3_analytics"
M3_EVENTS = M3_DIR / "data" / "simulated" / "event_logs.csv"
M3_SEGMENTS = M3_DIR / "data" / "simulated" / "user_segments.csv"
M3_GROUND_TRUTH = M3_DIR / "data" / "simulated" / "ground_truth_influence.csv"
M3_FEATURES = M3_DIR / "data" / "processed" / "features.csv"

#: One seed for everything that can be seeded, so a rerun reproduces the run.
SEED = 42

#: Bootstrap resamples. 10,000 is the usual recommendation for a percentile
#: interval; the statistics here are cheap enough to afford it.
N_BOOTSTRAP = 10_000

#: Multi-seed repetitions for the Module 2 policy comparison. A single seed
#: cannot separate "this policy is better" from "this run was lucky".
N_SEEDS = 30

#: Segments smaller than this are reported but excluded from the conversion
#: separation statistic, where a handful of users would dominate the spread.
MIN_SEGMENT_FOR_SEPARATION = 30

# ── Plot style ───────────────────────────────────────────────────────────────
# Matches report/build/gen_figures.py so the experiment figures and the
# architecture diagrams look like one document.
INK = "#1f2933"
MUTED = "#5b6b7a"
GRID = "#e2e8f0"

PALETTE = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "amber": "#d97706",
    "purple": "#7c3aed",
    "rose": "#e11d48",
    "slate": "#64748b",
    "teal": "#0d9488",
}
SERIES = list(PALETTE.values())

#: Stable colour per segment, so a segment is the same colour in every figure.
SEGMENT_COLOURS = {
    "High Intent": PALETTE["blue"],
    "Loyal Customer": PALETTE["green"],
    "Price Sensitive": PALETTE["amber"],
    "Low Engagement": PALETTE["slate"],
    "New Cold User": PALETTE["rose"],
}

#: Stable colour per automation policy.
POLICY_COLOURS = {
    "fixed": PALETTE["slate"],
    "trigger": PALETTE["amber"],
    "hybrid": PALETTE["blue"],
}


def apply_style() -> None:
    """Set matplotlib defaults. Called once by the figure builder."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "figure.dpi": 140,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })


def ensure_dirs() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
