"""Every figure in the report, drawn from the experiment results.

Nothing here recomputes a statistic. Each plot reads the tables that
`run_all.py` wrote, so a figure cannot drift away from the number it is
supposed to show — the failure mode where a chart and its caption quietly stop
agreeing after a rerun.

Each figure is saved as PNG (for the dashboard and for review) and PDF (for the
report, where it stays sharp at any zoom).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from research import config


def _save(fig, name: str) -> list[str]:
    written = []
    for suffix in ("png", "pdf"):
        path = config.FIGURES / f"{name}.{suffix}"
        fig.savefig(path)
        written.append(path.name)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return written


def _table(name: str) -> pd.DataFrame | None:
    path = config.RESULTS / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else None


def _caption(ax, text: str) -> None:
    """A one-line caveat under the axes — the figure carries its own warning."""
    ax.figure.text(0.5, -0.02, text, ha="center", va="top",
                   fontsize=7.5, color=config.MUTED, wrap=True)


# ── E1 ───────────────────────────────────────────────────────────────────────
def fig_segmentation_ablation() -> list[str]:
    data = _table("e1_method_comparison")
    if data is None:
        return []
    import matplotlib.pyplot as plt

    data = data.sort_values("separation")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))

    colours = [config.PALETTE["blue"] if "hybrid" in m else config.PALETTE["slate"]
               for m in data["method"]]
    y = np.arange(len(data))
    ax.barh(y, data["separation"], color=colours, height=0.6)
    ax.errorbar(data["separation"], y,
                xerr=[data["separation"] - data["ci_low"],
                      data["ci_high"] - data["separation"]],
                fmt="none", ecolor=config.INK, elinewidth=1.1, capsize=3)

    # Labels sit clear of the interval whisker, not on top of it.
    for i, (value, high, cold) in enumerate(
            zip(data["separation"], data["ci_high"], data["cold_start_users"])):
        label = f"{value:.3f}" + ("" if cold else "   (no cold-start segment)")
        ax.text(high + 0.015, i, label, va="center", fontsize=8)

    ax.set_yticks(y, data["method"])
    ax.set_xlabel("conversion separation  (highest − lowest segment conversion rate)")
    ax.set_title("Module 1 — what the hybrid adds over its components")
    ax.set_xlim(0, max(data["ci_high"]) * 1.35)
    ax.grid(axis="y", visible=False)
    _caption(ax, "95% percentile bootstrap intervals over 8,000 users. Conversion is "
                 "an evaluation column only, never an input.")
    return _save(fig, "fig_e1_segmentation_ablation")


def fig_segment_profile() -> list[str]:
    data = _table("e1_segment_profile")
    if data is None:
        return []
    import matplotlib.pyplot as plt

    hybrid = data[data["method"] == "hybrid (vote)"].sort_values("users", ascending=False)
    if hybrid.empty:
        return []

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.2, 3.6),
                                      gridspec_kw={"width_ratios": [1, 1.15]})

    colours = [config.SEGMENT_COLOURS.get(s, config.PALETTE["slate"])
               for s in hybrid["segment"]]
    left.bar(range(len(hybrid)), hybrid["users"], color=colours)
    left.set_xticks(range(len(hybrid)),
                    [s.replace(" ", "\n") for s in hybrid["segment"]], fontsize=8)
    left.set_ylabel("customers")
    left.set_title("Segment sizes")

    right.bar(range(len(hybrid)), hybrid["conversion_rate"] * 100, color=colours)
    right.set_xticks(range(len(hybrid)),
                     [s.replace(" ", "\n") for s in hybrid["segment"]], fontsize=8)
    right.set_ylabel("conversion rate (%)")
    right.set_title("Conversion by segment")
    for i, rate in enumerate(hybrid["conversion_rate"]):
        right.text(i, rate * 100 + 1.2, f"{rate:.1%}", ha="center", fontsize=8)
    right.set_ylim(0, 105)

    fig.suptitle("Module 1 — the hybrid segmentation on 8,000 customers",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "fig_e1_segment_profile")


# ── E2 ───────────────────────────────────────────────────────────────────────
def fig_defects() -> list[str]:
    votes = _table("e2_vote_order")
    leak = _table("e2_leakage")
    if votes is None or leak is None:
        return []
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.4, 3.5))

    # Defect 2 — the deleted cold-start segment.
    labels = ["notebook\n(ml == hier first)", "corrected\n(cold start second)"]
    detected = votes["cold_start_detected_by_rules"].iloc[0]
    kept = votes["cold_start_surviving"].tolist()
    left.bar(labels, kept, color=[config.PALETTE["rose"], config.PALETTE["green"]],
             width=0.55)
    left.axhline(detected, color=config.INK, linestyle="--", linewidth=1)
    left.text(0.5, detected + 3, f"{detected} detected by the rules",
              ha="center", fontsize=8, color=config.INK)
    for i, value in enumerate(kept):
        left.text(i, value + 3, str(value), ha="center", fontweight="bold")
    left.set_ylabel("New Cold User customers surviving the vote")
    left.set_title("Defect 2 — a segment deleted by its own vote")
    left.set_ylim(0, detected * 1.28)

    # Defect 1 — leakage inflates certainty, not accuracy.
    x = np.arange(2)
    accuracy = leak["held_out_accuracy"].tolist()
    certain = leak["share_at_confidence_1.00"].tolist()

    right.bar(x - 0.19, accuracy, width=0.36, label="held-out accuracy",
              color=config.PALETTE["slate"])
    right.bar(x + 0.19, certain, width=0.36, label="share at confidence 1.00",
              color=config.PALETTE["rose"])
    right.set_xticks(x, ["with rule label\n(notebook)", "behaviour only\n(corrected)"],
                     fontsize=8)
    right.set_ylim(0, 1.15)
    # Below the axes: inside the plot it sat on top of the accuracy labels.
    right.legend(frameon=False, fontsize=8, ncol=2,
                 loc="upper center", bbox_to_anchor=(0.5, -0.12))
    right.set_title("Defect 1 — leakage inflates certainty, not accuracy")
    for i, (a, c) in enumerate(zip(accuracy, certain)):
        right.text(i - 0.19, a + 0.02, f"{a:.3f}", ha="center", fontsize=8)
        right.text(i + 0.19, c + 0.02, f"{c:.1%}", ha="center", fontsize=8)

    fig.suptitle("Module 1 — the two defects, reproduced",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "fig_e2_defects")


# ── E3 ───────────────────────────────────────────────────────────────────────
def fig_policy_comparison() -> list[str]:
    summary = _table("e3_policy_summary")
    per_seed = _table("e3_per_seed")
    if summary is None:
        return []
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.4, 3.6),
                                      gridspec_kw={"width_ratios": [1.1, 1]})

    order = ["fixed", "trigger", "hybrid"]
    summary = summary.set_index("strategy").reindex(order).reset_index()
    colours = [config.POLICY_COLOURS[s] for s in summary["strategy"]]

    if per_seed is not None:
        # The full seed distribution, not just its mean: 30 points make the
        # overlap (or the lack of it) visible in a way error bars alone do not.
        data = [per_seed.loc[per_seed["strategy"] == s, "conversions_per_1000_sends"]
                for s in order]
        parts = left.violinplot(data, positions=range(len(order)), showmeans=True,
                                widths=0.7)
        for body, colour in zip(parts["bodies"], colours):
            body.set_facecolor(colour)
            body.set_alpha(0.35)
        for key in ("cbars", "cmins", "cmaxes", "cmeans"):
            if key in parts:
                parts[key].set_color(config.INK)
                parts[key].set_linewidth(1.1)
    else:
        left.bar(range(len(order)), summary["conversions_per_1000_sends"], color=colours)

    left.set_xticks(range(len(order)), order)
    left.set_ylabel("conversions per 1,000 sends")
    left.set_title(f"Efficiency across {config.N_SEEDS} paired seeds")

    # Outcome against cost — the trade the report has to argue.
    right.scatter(summary["operational_complexity"],
                  summary["conversions_per_1000_sends"],
                  s=150, c=colours, zorder=3)
    for _, row in summary.iterrows():
        right.annotate(row["strategy"],
                       (row["operational_complexity"], row["conversions_per_1000_sends"]),
                       textcoords="offset points", xytext=(0, 12),
                       ha="center", fontsize=9, fontweight="bold")
    right.set_xlabel("operational complexity  (distinct decision rules)")
    right.set_ylabel("conversions per 1,000 sends")
    right.set_title("What each policy costs to run")
    right.set_xlim(0, max(summary["operational_complexity"]) + 2)
    # Headroom for the labels, which sit above their points and would otherwise
    # run into the title.
    values = summary["conversions_per_1000_sends"]
    span = float(values.max() - values.min()) or 1.0
    right.set_ylim(float(values.min()) - span * 0.25, float(values.max()) + span * 0.35)

    fig.suptitle("Module 2 — automation policies, outcome against cost",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    _caption(left, "Simulated response: the policies are real code, the reactions "
                   "are modelled. Volume-controlled metric.")
    return _save(fig, "fig_e3_policy_comparison")


def fig_sparsity() -> list[str]:
    data = _table("e3_sparsity")
    if data is None:
        return []
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    for strategy, group in data.groupby("strategy"):
        group = group.sort_values("signal_sparsity")
        ax.plot(group["signal_sparsity"], group["conversions_per_1000_sends"],
                marker="o", label=strategy,
                color=config.POLICY_COLOURS.get(strategy, config.PALETTE["slate"]))
        ax.fill_between(group["signal_sparsity"],
                        group["conversions_per_1000_sends"] - group["sd"],
                        group["conversions_per_1000_sends"] + group["sd"],
                        alpha=0.15,
                        color=config.POLICY_COLOURS.get(strategy, config.PALETTE["slate"]))

    ax.set_xlabel("signal sparsity  (share of opens and clicks suppressed)")
    ax.set_ylabel("conversions per 1,000 sends")
    ax.set_title("Module 2 — what happens when the behavioural signal disappears")
    ax.legend(frameon=False, fontsize=8)
    _caption(ax, "A policy that reacts to behaviour should degrade as behaviour "
                 "stops being observable. Shaded band is ±1 SD across seeds.")
    return _save(fig, "fig_e3_sparsity")


# ── E4 ───────────────────────────────────────────────────────────────────────
def fig_attribution() -> list[str]:
    credits = _table("e4_live_credits")
    mae = _table("e4_ground_truth_mae")
    if credits is None and mae is None:
        return []
    import matplotlib.pyplot as plt

    panels = int(credits is not None) + int(mae is not None)
    fig, axes = plt.subplots(1, panels, figsize=(5.2 * panels, 3.8))
    axes = np.atleast_1d(axes)
    slot = 0

    if credits is not None:
        ax = axes[slot]; slot += 1
        pivot = credits.pivot(index="model", columns="channel", values="credit")
        order = [m for m in ("first_touch", "last_touch", "linear", "markov")
                 if m in pivot.index]
        pivot = pivot.reindex(order)

        bottom = np.zeros(len(pivot))
        for i, channel in enumerate(pivot.columns):
            values = pivot[channel].fillna(0).to_numpy()
            ax.barh(range(len(pivot)), values, left=bottom, height=0.62,
                    label=channel, color=config.SERIES[i % len(config.SERIES)])
            for j, (v, b) in enumerate(zip(values, bottom)):
                if v > 0.08:
                    ax.text(b + v / 2, j, f"{v:.0%}", ha="center", va="center",
                            fontsize=7.5, color="white", fontweight="bold")
            bottom += values

        ax.set_yticks(range(len(pivot)), pivot.index)
        ax.set_xlim(0, 1)
        ax.set_xlabel("share of attributed conversion credit")
        ax.set_title("The same journeys, four answers")
        ax.legend(frameon=False, fontsize=7.5, ncol=3,
                  loc="upper center", bbox_to_anchor=(0.5, -0.16))
        ax.grid(axis="y", visible=False)

    if mae is not None:
        ax = axes[slot]
        mae = mae.sort_values("mae")
        y = np.arange(len(mae))
        ax.barh(y, mae["mae"], height=0.6, color=config.PALETTE["purple"])
        ax.errorbar(mae["mae"], y,
                    xerr=[mae["mae"] - mae["ci_low"], mae["ci_high"] - mae["mae"]],
                    fmt="none", ecolor=config.INK, elinewidth=1.1, capsize=3)
        ax.set_yticks(y, mae["model"])
        ax.set_xlabel("mean absolute error against known channel influence")
        ax.set_title("Scored where ground truth exists")
        ax.grid(axis="y", visible=False)
        ax.invert_yaxis()

    fig.suptitle("Module 3 — attribution models disagree, and that is the finding",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "fig_e4_attribution")


# ── E5 ───────────────────────────────────────────────────────────────────────
def fig_prediction() -> list[str]:
    scores = _table("e5_model_scores")
    if scores is None:
        return []
    import matplotlib.pyplot as plt

    targets = sorted(scores["target"].unique())
    fig, axes = plt.subplots(1, len(targets), figsize=(5.0 * len(targets), 3.5),
                             squeeze=False)

    for ax, target in zip(axes[0], targets):
        subset = scores[scores["target"] == target].sort_values("roc_auc")
        y = np.arange(len(subset))
        colours = [config.PALETTE["slate"] if m.startswith("baseline")
                   else config.PALETTE["green"] for m in subset["model"]]
        ax.barh(y, subset["roc_auc"], height=0.6, color=colours)
        ax.errorbar(subset["roc_auc"], y,
                    xerr=[subset["roc_auc"] - subset["roc_auc_ci_low"],
                          subset["roc_auc_ci_high"] - subset["roc_auc"]],
                    fmt="none", ecolor=config.INK, elinewidth=1.1, capsize=3)
        ax.axvline(0.5, color=config.PALETTE["rose"], linestyle="--", linewidth=1)
        ax.set_yticks(y, subset["model"], fontsize=8)
        ax.set_xlim(0.4, 1.02)
        ax.set_xlabel("ROC-AUC")
        ax.set_title(target.replace("_", " "))
        ax.grid(axis="y", visible=False)

    fig.suptitle("Module 3 — prediction against a baseline, with intervals",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    _caption(axes[0][0], "Fitted on Module 3's simulator. Dashed line is chance.")
    return _save(fig, "fig_e5_prediction")


# ── E6 ───────────────────────────────────────────────────────────────────────
def fig_goal_tone() -> list[str]:
    summary = _table("e6_model_summary")
    if summary is None:
        return []
    import matplotlib.pyplot as plt

    targets = sorted(summary["target"].unique())
    fig, axes = plt.subplots(1, len(targets), figsize=(5.0 * len(targets), 3.6),
                             squeeze=False)

    for ax, target in zip(axes[0], targets):
        subset = summary[summary["target"] == target]
        models = subset["model"].tolist()
        x = np.arange(len(models))

        ax.bar(x - 0.19, subset["accuracy"], width=0.36, label="accuracy",
               color=config.PALETTE["slate"])
        ax.bar(x + 0.19, subset["macro_f1"], width=0.36, label="macro-F1",
               color=config.PALETTE["blue"])
        for i, (a, f) in enumerate(zip(subset["accuracy"], subset["macro_f1"])):
            ax.text(i - 0.19, a + 0.015, f"{a:.2f}", ha="center", fontsize=7.5)
            ax.text(i + 0.19, f + 0.015, f"{f:.2f}", ha="center", fontsize=7.5)

        share = subset["majority_class_share"].iloc[0]
        ax.axhline(share, color=config.PALETTE["rose"], linestyle="--", linewidth=1)
        # Left-aligned: on the right it sat on top of the last model's bars.
        ax.text(-0.45, share + 0.02, f"majority class {share:.0%}",
                ha="left", fontsize=7.5, color=config.PALETTE["rose"])

        ax.set_xticks(x, [m.replace(" + ", "\n+ ").replace(" ", "\n", 1)
                          for m in models], fontsize=7.5)
        ax.set_ylim(0, 1.08)
        ax.set_title(target.replace("_", " "))
        ax.legend(frameon=False, fontsize=8, loc="upper left")

    fig.suptitle("Module 4 — accuracy flatters, macro-F1 does not",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "fig_e6_goal_tone")


# ── E7 ───────────────────────────────────────────────────────────────────────
def fig_engagement() -> list[str]:
    comparison = _table("e7_leakage_comparison")
    signal = _table("e7_feature_signal")
    if comparison is None:
        return []
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.4, 3.6))

    labels = [f.replace(" (", "\n(") for f in comparison["feature_set"]]
    colours = [config.PALETTE["rose"], config.PALETTE["green"], config.PALETTE["slate"]]
    left.bar(range(len(comparison)), comparison["r2"], color=colours[:len(comparison)],
             width=0.55)
    left.axhline(0, color=config.INK, linewidth=1)
    for i, value in enumerate(comparison["r2"]):
        left.text(i, value + (0.04 if value >= 0 else -0.09), f"{value:.3f}",
                  ha="center", fontsize=8, fontweight="bold")
    left.set_xticks(range(len(comparison)), labels, fontsize=7.5)
    left.set_ylabel("R² on held-out data")
    left.set_title("Leakage: 0.99 was the model reading its own answer")

    if signal is not None:
        data = signal.sort_values("pearson_r", key=abs, ascending=True)
        colours = [config.PALETTE["green"] if s else config.PALETTE["slate"]
                   for s in data["significant_after_correction"]]
        right.barh(range(len(data)), data["pearson_r"], color=colours, height=0.6)
        right.axvline(0, color=config.INK, linewidth=1)
        right.set_yticks(range(len(data)),
                         [f.replace("_", " ") for f in data["feature"]], fontsize=7.5)
        right.set_xlabel("correlation with engagement rate")
        right.set_title("No text feature survives correction")
        right.grid(axis="y", visible=False)

    fig.suptitle("Module 4 — engagement prediction, and the missing signal",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    _caption(left, "Holm–Bonferroni correction across the text features. Green "
                   "would mark a surviving correlation.")
    return _save(fig, "fig_e7_engagement")


# ── E8 ───────────────────────────────────────────────────────────────────────
def fig_uplift() -> list[str]:
    curves = _table("e8_qini_curves")
    summary = _table("e8_policy_summary")
    if curves is None or summary is None:
        return []
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.6, 3.8),
                                      gridspec_kw={"width_ratios": [1.25, 1]})

    style = {
        "uplift (S-learner)": (config.PALETTE["green"], "-"),
        "uplift (T-learner)": (config.PALETTE["teal"], "-"),
        "predicted response (current policy)": (config.PALETTE["blue"], "-"),
        "random targeting": (config.PALETTE["slate"], ":"),
    }

    for policy, group in curves.groupby("policy"):
        colour, dash = style.get(str(policy), (config.PALETTE["slate"], "-"))
        group = group.sort_values("share_targeted")
        left.plot(group["share_targeted"], group["incremental_responders"],
                  label=policy, color=colour, linestyle=dash, linewidth=1.8)

    left.axhline(0, color=config.INK, linewidth=0.8)
    left.set_xlabel("share of the list targeted")
    left.set_ylabel("incremental visits gained")
    left.set_title("Qini — who to email first")
    left.legend(frameon=False, fontsize=7.5, loc="upper left")

    # The number a marketer can act on.
    summary = summary.sort_values("uplift_per_1000")
    colours = [style.get(str(p), (config.PALETTE["slate"], "-"))[0]
               for p in summary["policy"]]
    y = np.arange(len(summary))
    right.barh(y, summary["uplift_per_1000"], color=colours, height=0.6)
    for i, value in enumerate(summary["uplift_per_1000"]):
        right.text(value + 1.5, i, f"{value:.0f}", va="center", fontsize=8)
    right.set_yticks(y, [str(p).replace(" (", "\n(") for p in summary["policy"]],
                     fontsize=7.5)
    right.set_xlabel("extra visits per 1,000 targeted (30% budget)")
    right.set_title("What each policy buys")
    right.set_xlim(0, summary["uplift_per_1000"].max() * 1.25)
    right.grid(axis="y", visible=False)

    fig.suptitle("Module 3 — ranking by uplift is not ranking by response",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    _caption(left, "Hillstrom MineThatData: 64,000 customers, randomised arms. "
                   "Causal because assignment was random.")
    return _save(fig, "fig_e8_uplift")


# ── E9 ───────────────────────────────────────────────────────────────────────
def fig_offpolicy() -> list[str]:
    accuracy = _table("e9_estimator_accuracy")
    exploration = _table("e9_exploration")
    if accuracy is None or exploration is None:
        return []
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.6, 3.7))

    colours = {"ips": config.PALETTE["rose"],
               "snips": config.PALETTE["green"],
               "doubly_robust": config.PALETTE["blue"]}

    for estimator, group in accuracy.groupby("estimator"):
        group = group.sort_values("log_size")
        left.plot(group["log_size"], group["rmse"], marker="o",
                  label=str(estimator).replace("_", " "),
                  color=colours.get(str(estimator), config.PALETTE["slate"]))
    left.set_xscale("log")
    left.set_xlabel("logged decisions")
    left.set_ylabel("RMSE against the true policy value")
    left.set_title("The estimate sharpens as the log grows")
    left.legend(frameon=False, fontsize=8)

    # Bias against exploration — the argument for exploring at all.
    exploration = exploration.sort_values("exploration_rate")
    x = np.arange(len(exploration))
    bars = right.bar(x, exploration["bias"],
                     color=[config.PALETTE["rose"] if abs(b) > 0.01
                            else config.PALETTE["green"]
                            for b in exploration["bias"]], width=0.6)
    right.axhline(0, color=config.INK, linewidth=1)
    for i, (bias, rmse) in enumerate(zip(exploration["bias"], exploration["rmse"])):
        right.text(i, bias + (0.003 if bias >= 0 else -0.005),
                   f"{bias:+.3f}", ha="center", fontsize=7.5,
                   va="bottom" if bias >= 0 else "top")
    right.set_xticks(x, [f"{r:.0%}" for r in exploration["exploration_rate"]])
    right.set_xlabel("share of decisions made at random")
    right.set_ylabel("bias of the estimate")
    right.set_title("No exploration → confidently wrong")
    right.set_ylim(min(exploration["bias"]) - 0.015,
                   max(exploration["bias"]) + 0.015)

    fig.suptitle("Module 3 — off-policy evaluation, and the price of exploring",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    _caption(left, "Simulated world with a known reward function, so the true "
                   "policy value is computable and the estimator can be scored "
                   "against it. 40 replications per point.")
    return _save(fig, "fig_e9_offpolicy")


# ── E10 ──────────────────────────────────────────────────────────────────────
def fig_capability_detection() -> list[str]:
    data = _table("e10_per_capability")
    if data is None:
        return []
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    data = data.sort_values("judgements", ascending=True)
    y = np.arange(len(data))

    ax.barh(y, data["agreement"], height=0.6, color=config.PALETTE["green"])
    ax.errorbar(data["agreement"], y,
                xerr=[data["agreement"] - data["ci_low"],
                      data["ci_high"] - data["agreement"]],
                fmt="none", ecolor=config.INK, elinewidth=1.1, capsize=3)

    for i, (value, n) in enumerate(zip(data["agreement"], data["judgements"])):
        ax.text(1.02, i, f"{value:.0%}  (n={n})", va="center", fontsize=8)

    ax.set_yticks(y, [c.replace("_", " ") for c in data["capability"]])
    ax.set_xlim(0, 1.32)
    ax.set_xlabel("agreement with the hand label")
    ax.set_title("Module 4 — capability detection on real websites")
    ax.grid(axis="y", visible=False)
    _caption(ax, "Wilson intervals. The sample is small and was used during "
                 "development, so the point estimates are optimistic — the "
                 "width of these bars is the honest content of the figure.")
    return _save(fig, "fig_e10_capability_detection")


# ── E11 ──────────────────────────────────────────────────────────────────────
def fig_action_set_size() -> list[str]:
    grid = _table("e11_error_grid")
    requirement = _table("e11_data_requirement")
    if grid is None or requirement is None:
        return []
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.6, 3.7))

    shades = [config.PALETTE["green"], config.PALETTE["blue"],
              config.PALETTE["amber"], config.PALETTE["rose"]]
    for colour, (k, group) in zip(shades, grid.groupby("n_actions")):
        group = group.sort_values("log_size")
        left.plot(group["log_size"], group["rmse"], marker="o",
                  label=f"{k} actions", color=colour)

    left.set_xscale("log")
    left.set_yscale("log")
    left.set_xlabel("logged decisions")
    left.set_ylabel("RMSE against the true policy value")
    left.set_title("More actions, thinner evidence")
    left.legend(frameon=False, fontsize=8)

    requirement = requirement.dropna(subset=["decisions_needed"])
    x = np.arange(len(requirement))
    right.bar(x, requirement["decisions_needed"], color=config.PALETTE["purple"],
              width=0.6)
    for i, value in enumerate(requirement["decisions_needed"]):
        right.text(i, value * 1.05, f"{int(value):,}", ha="center", fontsize=8)
    right.set_xticks(x, [f"{int(k)}" for k in requirement["n_actions"]])
    right.set_yscale("log")
    right.set_xlabel("actions on offer")
    right.set_ylabel("decisions needed")
    right.set_title("Data required before a comparison means anything")

    fig.suptitle("Module 3 — what a per-website action set costs in data",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    _caption(left, "Simulated world with a known reward function. Exploration "
                   "held at 10%; 30 replications per point.")
    return _save(fig, "fig_e11_action_set_size")


BUILDERS = (
    fig_segmentation_ablation,
    fig_segment_profile,
    fig_defects,
    fig_policy_comparison,
    fig_sparsity,
    fig_attribution,
    fig_prediction,
    fig_goal_tone,
    fig_engagement,
    fig_uplift,
    fig_offpolicy,
    fig_capability_detection,
    fig_action_set_size,
)


def build_all(results: dict | None = None) -> list[str]:
    """Draw every figure whose inputs exist. Returns the filenames written."""
    config.ensure_dirs()
    config.apply_style()

    written: list[str] = []
    for builder in BUILDERS:
        try:
            written.extend(builder())
        except Exception as exc:                                   # pragma: no cover
            print(f"   ! {builder.__name__} failed: {type(exc).__name__}: {exc}")
    return written


if __name__ == "__main__":
    for name in build_all():
        print(name)
