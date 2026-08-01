"""Poster-scale versions of the four headline result figures.

    venv/bin/python docs/poster/poster_figures.py

The report figures in `research/figures/` are drawn at page width — about 7 in.
Placed on an A2 poster at 95 mm they render their own axis labels at roughly
3 pt, which nobody reads from a metre away.  These are the same numbers, read
from the same result tables `research/run_all.py` wrote, drawn at the size they
are actually printed: 95 mm wide, so a 9 pt label is 9 pt on the wall.

Nothing here recomputes a statistic.  If an experiment is re-run and a number
moves, these figures move with it.
"""
from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "research" / "results"
OUT = pathlib.Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

# ── design tokens ────────────────────────────────────────────────────────────
# Categorical order validated with the dataviz palette checker (light surface):
# lightness band, chroma floor, CVD separation, normal-vision floor, contrast —
# all pass.  Do not reorder: adjacency is what the CVD check scores.
CAT = ["#2563eb", "#d97706", "#0d9488", "#7c3aed", "#16a34a"]

INK = "#16233a"
INK2 = "#33465f"
MUTED = "#5b6b7a"
GRID = "#e2e8f0"
REF = "#94a3b8"          # neutral reference marks — never a categorical slot
BLUE, AMBER, GREEN = "#2563eb", "#d97706", "#16a34a"
QUIET = "#8c9bb0"        # de-emphasised bars in a one-series highlight chart

W, H = 3.74, 2.34        # inches — exactly the width the poster prints them at

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "text.color": INK,
    "axes.labelcolor": INK2,
    "axes.edgecolor": GRID,
    "xtick.color": MUTED,
    "ytick.color": INK2,
    "xtick.labelsize": 8.4,
    "ytick.labelsize": 9,
    "axes.titlesize": 10.4,
    "figure.dpi": 400,
    "savefig.dpi": 400,
})


def table(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / f"{name}.csv")


def frame(ax) -> None:
    """Recessive axes: no box, a whisper of a grid on the value axis only."""
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def title(ax, main: str, sub: str) -> None:
    ax.set_title(main, loc="left", pad=15, fontweight="bold", color=INK)
    ax.text(0, 1.05, sub, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=7.8, color=MUTED)


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", pad_inches=0.04,
                facecolor="white")
    plt.close(fig)
    print("wrote", (OUT / f"{name}.png").relative_to(ROOT))


# ── E1 · Module 1 ────────────────────────────────────────────────────────────
def e1_ablation() -> None:
    d = table("e1_method_comparison").sort_values("separation")
    fig, ax = plt.subplots(figsize=(W, H))

    colours = [BLUE if "hybrid" in m else QUIET for m in d["method"]]
    y = range(len(d))
    ax.barh(y, d["separation"], color=colours, height=0.62)
    ax.errorbar(d["separation"], y,
                xerr=[d["separation"] - d["ci_low"], d["ci_high"] - d["separation"]],
                fmt="none", ecolor=INK2, elinewidth=1.1, capsize=3, capthick=1.1)

    for i, row in enumerate(d.itertuples()):
        note = "" if row.finds_cold_start else "   no cold-start segment"
        ax.text(row.ci_high + 0.018, i, f"{row.separation:.3f}{note}",
                va="center", fontsize=8.6, color=INK,
                fontweight="bold" if "hybrid" in row.method else "normal")

    ax.set_yticks(list(y), d["method"])
    ax.set_xlim(0, 0.80)
    ax.set_ylim(-0.62, len(d) - 0.30)
    ax.set_xlabel("conversion separation", fontsize=8.4)
    frame(ax)
    title(ax, "Module 1 — the hybrid does not beat its rules",
          "highest − lowest segment conversion rate · 95% bootstrap CI · 8,000 customers")
    save(fig, "poster_e1")


# ── E3 · Module 2 ────────────────────────────────────────────────────────────
def e3_policy() -> None:
    d = table("e3_policy_summary").sort_values("conversions_per_1000_sends")
    fig, ax = plt.subplots(figsize=(W, H))

    colours = [GREEN if s == "trigger" else QUIET for s in d["strategy"]]
    y = range(len(d))
    ax.barh(y, d["conversions_per_1000_sends"], color=colours, height=0.58)
    ax.errorbar(d["conversions_per_1000_sends"], y,
                xerr=[d["conversions_per_1000_sends"] - d["ci_low"],
                      d["ci_high"] - d["conversions_per_1000_sends"]],
                fmt="none", ecolor=INK2, elinewidth=1.1, capsize=3, capthick=1.1)

    for i, row in enumerate(d.itertuples()):
        ax.text(row.ci_high + 0.35, i,
                f"{row.conversions_per_1000_sends:.2f}"
                f"   ({row.operational_complexity} rule"
                f"{'s' if row.operational_complexity != 1 else ''})",
                va="center", fontsize=8.6, color=INK,
                fontweight="bold" if row.strategy == "trigger" else "normal")

    ax.set_yticks(list(y), d["strategy"])
    ax.set_xlim(0, 15.2)
    ax.set_ylim(-0.62, len(d) - 0.30)
    ax.set_xlabel("conversions per 1,000 sends", fontsize=8.4)
    frame(ax)
    title(ax, "Module 2 — outcome argued against cost",
          "30 paired seeds · volume-controlled · rule count = operational complexity")
    save(fig, "poster_e3")


# ── E4 · Module 3 ────────────────────────────────────────────────────────────
def e4_attribution() -> None:
    d = table("e4_live_credits")
    channels = ["email", "referral", "ppc", "seo", "social_media"]
    models = ["first_touch", "linear", "markov", "last_touch"]
    wide = d.pivot(index="model", columns="channel", values="credit").loc[models, channels]

    fig, ax = plt.subplots(figsize=(W, H))
    y = range(len(models))
    left = [0.0] * len(models)

    for ci, ch in enumerate(channels):
        vals = wide[ch].to_numpy()
        ax.barh(y, vals, left=left, height=0.62, color=CAT[ci],
                label=ch.replace("_media", ""), edgecolor="white", linewidth=1.4)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 0.10:                       # direct label — the secondary encoding
                ax.text(l + v / 2, i, f"{v:.0%}", ha="center", va="center",
                        fontsize=8.2, color="white", fontweight="bold")
        left = [l + v for l, v in zip(left, vals)]

    ax.set_yticks(list(y), [m.replace("_", "-") for m in models])
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.62, len(models) - 0.30)
    ax.set_xticks([0, .25, .5, .75, 1], ["0", "25%", "50%", "75%", "100%"])
    ax.xaxis.grid(False)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.legend(frameon=False, fontsize=7.8, ncol=5, loc="lower center",
              bbox_to_anchor=(0.5, -0.30), handlelength=0.9, handleheight=0.9,
              columnspacing=1.0, handletextpad=0.4, labelcolor=INK2)
    title(ax, "Module 3 — four models, four answers",
          "share of conversion credit · 7,811 real converting journeys")
    save(fig, "poster_e4")


# ── E6 + E7 · Module 4 ───────────────────────────────────────────────────────
# Module 4 owns two quantitative findings (results.md 3.6 and 3.7) and one
# qualitative one (3.10.1, capability detection — a 21-judgement development set
# whose honest content is the width of its intervals, so it is stated in the
# caption rather than drawn as four bars all sitting on 1.0).
#
# The two panels measure different things — macro-F1 and R² — so they are two
# axes side by side and never one chart with two scales. Colour carries the same
# meaning in both: BLUE is what the system deploys, AMBER the alternative it was
# measured against, REF/QUIET a reference that is not an identity.
def e6_e7_module4() -> None:
    goal_tone = table("e6_model_summary")
    leakage = table("e7_leakage_comparison")

    fig, (ax_left, ax_right) = plt.subplots(
        1, 2, figsize=(W, 1.55), gridspec_kw={"width_ratios": (1.06, 1.0),
                                           "wspace": 0.62})

    # ── left · goal and tone, two model families on the same test rows ────────
    targets = ["campaign_goal", "tone"]
    series = [("tfidf + logistic", "TF-IDF + logistic", BLUE),
              ("sbert + xgboost", "SBERT + XGBoost", AMBER)]

    height = 0.30
    for si, (key, label, colour) in enumerate(series):
        vals = [goal_tone[(goal_tone.target == t)
                          & (goal_tone.model == key)].macro_f1.iloc[0]
                for t in targets]
        pos = [i + (0.5 - si) * height * 1.08 for i in range(len(targets))]
        ax_left.barh(pos, vals, height=height, color=colour, label=label)
        for p, v in zip(pos, vals):
            ax_left.text(v + 0.02, p, f"{v:.3f}", va="center", fontsize=7.6,
                         color=INK)

    # the majority baseline is a reference line, not a third identity
    for i, t in enumerate(targets):
        base = goal_tone[(goal_tone.target == t)
                         & (goal_tone.model == "majority baseline")].macro_f1.iloc[0]
        ax_left.plot([base, base], [i - 0.34, i + 0.34], color=REF, linewidth=1.6,
                     linestyle=(0, (2.4, 1.8)), zorder=3)

    ax_left.set_ylim(-0.55, len(targets) - 0.22)
    ax_left.text(0.135, 1.50, "majority baseline", fontsize=6.9, color=MUTED,
                 ha="left", va="center")
    ax_left.set_yticks(range(len(targets)), ["goal", "tone"])
    ax_left.set_xlim(0, 1.02)
    ax_left.set_xlabel("macro-F1", fontsize=8.0)
    frame(ax_left)
    title(ax_left, "goal / tone", "no significant difference detected")

    # ── right · the engagement regressor, with and without the leak ───────────
    rows = [("with outcome columns (original)", "leaked", AMBER),
            ("text features only (corrected)", "text only", BLUE),
            ("baseline (predict the mean)", "mean", QUIET)]

    for i, (key, _, colour) in enumerate(rows):
        row = leakage[leakage.feature_set == key].iloc[0]
        value = float(row.r2)
        ax_right.barh(i, value, height=0.44, color=colour)

        # the corrected model is the only one carrying a bootstrap interval, and
        # that the interval sits wholly below zero is the finding
        lo, hi = row.r2_ci_low, row.r2_ci_high
        if pd.notna(lo) and pd.notna(hi):
            ax_right.plot([lo, hi], [i, i], color=INK2, linewidth=1.3, zorder=4)
            for edge in (lo, hi):
                ax_right.plot([edge, edge], [i - 0.11, i + 0.11], color=INK2,
                              linewidth=1.3, zorder=4)

        # A bar running left from zero would put its value label on top of the
        # row name and, worse, hide the minus sign that is the whole point. So a
        # negative value is labelled in the empty space to the right of zero.
        label = "0.000" if abs(value) < 5e-4 else f"{value:.3f}"
        ax_right.text(value + 0.06 if value > 0 else 0.06, i, label,
                      va="center", ha="left", fontsize=7.6, color=INK)

    ax_right.axvline(0, color=REF, linewidth=1.0, zorder=2)
    ax_right.set_ylim(-0.55, len(rows) - 0.30)
    ax_right.invert_yaxis()
    ax_right.set_yticks(range(len(rows)), [short for _, short, _ in rows])
    ax_right.set_xlim(-0.72, 1.42)
    ax_right.set_xticks([0.0, 0.5, 1.0])
    ax_right.set_xlabel("R²  (held out)", fontsize=8.0)
    frame(ax_right)
    title(ax_right, "engagement", "no skill without the leak")

    # One legend for the figure, not one per panel: it names the two model
    # families in the left panel, and a per-axes legend at this width wraps.
    handles, labels = ax_left.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=7.2, ncol=2,
               loc="lower center", bbox_to_anchor=(0.5, -0.27),
               handlelength=0.9, handleheight=0.9, columnspacing=1.4,
               handletextpad=0.4, labelcolor=INK2)

    save(fig, "poster_e6_e7")


if __name__ == "__main__":
    e1_ablation()
    e3_policy()
    e4_attribution()
    e6_e7_module4()
