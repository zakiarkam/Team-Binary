"""funnel.py — Funnel metrics, drop-off analysis, and visualisations (Phase 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import pandas as pd

STAGES = ["sent", "open", "click", "convert"]


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------

def compute_funnel(events_df: pd.DataFrame) -> dict[str, int]:
    """Count unique users who reached each funnel stage (at least once)."""
    result: dict[str, int] = {}
    for stage in STAGES:
        result[stage] = events_df.loc[
            events_df["event_type"] == stage, "user_id"
        ].nunique()
    return result


def compute_dropoffs(funnel: dict[str, int]) -> dict[str, float]:
    """Return drop-off rate (0–1) between consecutive funnel stages."""
    transitions = [
        ("sent→open", "sent", "open"),
        ("open→click", "open", "click"),
        ("click→convert", "click", "convert"),
    ]
    result: dict[str, float] = {}
    for label, from_stage, to_stage in transitions:
        denom = funnel.get(from_stage, 0)
        numer = funnel.get(to_stage, 0)
        result[label] = round(1 - numer / denom, 4) if denom else 0.0
    return result


def funnel_by(
    events_df: pd.DataFrame,
    by: Literal["segment", "strategy", "channel"],
) -> pd.DataFrame:
    """Return a DataFrame of funnel counts sliced by a grouping column.

    Columns: the grouping value + one column per stage.
    The caller is responsible for merging segment data before passing when by='segment'.
    """
    if by not in events_df.columns:
        raise ValueError(f"Column '{by}' not found — merge segments data first.")

    rows = []
    for group_val, group_df in events_df.groupby(by):
        row = {by: group_val}
        for stage in STAGES:
            row[stage] = group_df.loc[
                group_df["event_type"] == stage, "user_id"
            ].nunique()
        rows.append(row)

    return pd.DataFrame(rows).set_index(by)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_funnel(
    funnel: dict[str, int] | pd.DataFrame,
    savepath: str | Path,
    title: str = "Marketing Funnel",
) -> None:
    """Save a funnel bar chart to *savepath*.

    Accepts either a plain dict (overall funnel) or a DataFrame returned by
    funnel_by (grouped funnel — renders a grouped bar chart).
    """
    savepath = Path(savepath)
    savepath.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(funnel, dict):
        _plot_single_funnel(funnel, savepath, title)
    else:
        _plot_grouped_funnel(funnel, savepath, title)


def _plot_single_funnel(
    funnel: dict[str, int], savepath: Path, title: str
) -> None:
    stages = [s for s in STAGES if s in funnel]
    counts = [funnel[s] for s in stages]
    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(stages, counts, color=colors[: len(stages)], edgecolor="white", width=0.5)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.01,
            f"{count:,}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    # Annotate drop-off rates on the axis
    dropoffs = compute_dropoffs(funnel)
    for i, (label, rate) in enumerate(dropoffs.items()):
        mid_x = i + 0.5
        mid_y = (counts[i] + counts[i + 1]) / 2
        ax.annotate(
            f"−{rate * 100:.1f}%",
            xy=(mid_x, mid_y),
            fontsize=9,
            color="#555555",
            ha="center",
        )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Unique users", fontsize=11)
    ax.set_xlabel("Funnel stage", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(savepath, dpi=150)
    plt.close(fig)
    print(f"Saved: {savepath}")


def _plot_grouped_funnel(df: pd.DataFrame, savepath: Path, title: str) -> None:
    """Grouped bar chart with one group per row in *df*."""
    stages = [s for s in STAGES if s in df.columns]
    groups = df.index.tolist()
    n_groups = len(groups)
    n_stages = len(stages)

    x = range(n_groups)
    width = 0.8 / n_stages
    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]

    fig, ax = plt.subplots(figsize=(max(10, n_groups * 1.5), 5))

    for i, (stage, color) in enumerate(zip(stages, colors)):
        offsets = [xi + (i - n_stages / 2 + 0.5) * width for xi in x]
        bars = ax.bar(offsets, df[stage].values, width=width * 0.9, label=stage, color=color)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 1,
                    str(int(h)),
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )

    ax.set_xticks(list(x))
    ax.set_xticklabels(groups, fontsize=10)
    ax.set_ylabel("Unique users", fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.legend(title="Stage", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(savepath, dpi=150)
    plt.close(fig)
    print(f"Saved: {savepath}")
