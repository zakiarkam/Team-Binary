"""E1 — Does the hybrid actually beat its own components?

Novel Contribution 1 is a hybrid: rules, K-Means and hierarchical clustering
combined by an agreement vote. The obvious question — and the first one an
examiner should ask — is whether the combination earns its complexity, or
whether one component alone does just as well.

So all four are scored on the same 8,000 users, on the same metric:

    conversion separation = (highest segment conversion rate)
                          − (lowest segment conversion rate)

Conversion is used **only to evaluate** the segments. It is never a clustering
feature and never a rule input, so a segmentation that separates conversion has
found something it was not told — which is the entire point of the metric.

Segments below `MIN_SEGMENT_FOR_SEPARATION` users are excluded from the spread
(they are still reported): a segment of four people can hit 0% or 100% by
chance and would dominate a max-minus-min statistic.

Reported alongside:
*   **silhouette**, so the geometric quality is visible next to the commercial
    quality. They disagree in this project, and that disagreement is a finding.
*   **agreement rate**, the share of users where all three methods concur.
*   **cold-start coverage**, the share the clustering could not speak for.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import config
from research.stats import bootstrap_ci, paired_difference

ID = "E1"
TITLE = "Module 1 — hybrid segmentation versus each component alone"


def _separation(labels: np.ndarray, conversion: np.ndarray,
                min_size: int = config.MIN_SEGMENT_FOR_SEPARATION) -> float:
    """Spread of conversion rate across segments that are big enough to trust."""
    rates = []
    for name in np.unique(labels):
        mask = labels == name
        if mask.sum() >= min_size:
            rates.append(conversion[mask].mean())
    return float(max(rates) - min(rates)) if len(rates) >= 2 else float("nan")


def _segment_table(method: str, labels: pd.Series, conversion: pd.Series) -> list[dict]:
    rows = []
    for name, group in conversion.groupby(labels):
        rows.append({
            "method": method,
            "segment": name,
            "users": int(len(group)),
            "share": round(len(group) / len(conversion), 4),
            "conversion_rate": round(float(group.mean()), 4),
            "counted_in_separation": bool(len(group) >= config.MIN_SEGMENT_FOR_SEPARATION),
        })
    return sorted(rows, key=lambda r: -r["users"])


def run() -> dict:
    if not config.M1_DATASET.exists():
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": f"dataset not found at {config.M1_DATASET}"}

    from modules.m1_segmentation.segment import research_segmenter

    df = pd.read_csv(config.M1_DATASET)
    result = research_segmenter().fit_predict(df)
    frame = result.frame
    diagnostics = result.diagnostics

    conversion = frame["Conversion"].astype(float)

    # One fit gives every component's labels: the engine keeps the rule, K-Means
    # and hierarchical opinions alongside the vote, so the ablation compares the
    # *same* run rather than four separately-seeded ones.
    methods = {
        "rules only": frame["rule_segment"],
        "k-means only": frame["ml_segment"],
        "hierarchical only": frame["hierarchical_segment"],
        "hybrid (vote)": frame["segment_name"],
    }

    summary, per_segment = [], []
    index = np.arange(len(frame))
    conv_values = conversion.to_numpy()

    for name, labels in methods.items():
        label_values = labels.to_numpy()
        # Bootstrap over user indices: the statistic needs label and outcome
        # together, so resampling rows keeps them aligned.
        interval = bootstrap_ci(
            index,
            lambda idx, lv=label_values: _separation(lv[idx], conv_values[idx]),
        )
        summary.append({
            "method": name,
            "n_segments": int(labels.nunique()),
            "separation": round(interval.point, 4),
            "ci_low": round(interval.low, 4),
            "ci_high": round(interval.high, 4),
            "largest_segment_share": round(float(labels.value_counts(normalize=True).max()), 4),
            "finds_cold_start": bool((labels == "New Cold User").any()),
            "cold_start_users": int((labels == "New Cold User").sum()),
        })
        per_segment.extend(_segment_table(name, labels, conversion))

    # Is the hybrid's advantage over the best single method real, or noise?
    # Bootstrapped per-user: resample the audience, recompute both separations,
    # and look at the difference on each resample.
    best_single = max(
        (s for s in summary if s["method"] != "hybrid (vote)"),
        key=lambda s: s["separation"])
    hybrid_labels = methods["hybrid (vote)"].to_numpy()
    rival_labels = methods[best_single["method"]].to_numpy()

    rng = np.random.default_rng(config.SEED)
    hybrid_draws, rival_draws = [], []
    for _ in range(2_000):          # fewer than the default: two statistics per draw
        idx = rng.integers(0, len(frame), len(frame))
        hybrid_draws.append(_separation(hybrid_labels[idx], conv_values[idx]))
        rival_draws.append(_separation(rival_labels[idx], conv_values[idx]))

    contest = paired_difference(hybrid_draws, rival_draws, n_resamples=2_000)

    notes = [
        "Conversion is an evaluation column only — never a clustering feature "
        "and never a rule input — so the separation is not circular.",
        f"Segments under {config.MIN_SEGMENT_FOR_SEPARATION} users are reported "
        "but excluded from the separation statistic.",
    ]

    # The uncomfortable result, stated first rather than buried. If the vote
    # tracks the rules this closely, the clustering is not what separates
    # conversion, and the report must not imply that it is.
    hybrid_row = next(s for s in summary if s["method"] == "hybrid (vote)")
    rules_row = next(s for s in summary if s["method"] == "rules only")
    margin = hybrid_row["separation"] - rules_row["separation"]
    if abs(margin) < 0.01:
        notes.append(
            f"The hybrid separates conversion no better than the rules alone "
            f"({hybrid_row['separation']:.4f} against {rules_row['separation']:.4f}). "
            "On this metric the clustering adds nothing, and the honest reading is "
            "that the rules carry the commercial signal. The hybrid earns its place "
            "elsewhere — it produces a calibrated confidence from the level of "
            "agreement between three independent methods, and it is the vote that "
            "makes cold start explicit — but not by separating conversion further.")
    if any(s["separation"] < 0.1 for s in summary if "only" in s["method"]
           and s["method"] != "rules only"):
        notes.append(
            "Clustering alone barely separates conversion at all. It groups users "
            "by behavioural similarity, which is not the same thing as grouping "
            "them by commercial value — and this is the measurement that shows the "
            "difference rather than assuming it.")

    silhouette = diagnostics.get("silhouette")
    if silhouette is not None and silhouette < 0.25:
        notes.append(
            f"Silhouette is {silhouette:.3f}: the clusters overlap heavily in "
            "feature space. The segments are commercially useful without being "
            "geometrically clean, and reporting only the separation would hide "
            "that.")

    unanimous = diagnostics.get("unanimous_users", 0)
    all_disagree = diagnostics.get("all_disagree_users", 0)

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "n_users": int(len(frame)),
            "silhouette": silhouette,
            "unanimous_share": round(unanimous / len(frame), 4),
            "all_disagree_share": round(all_disagree / len(frame), 4),
            "mean_confidence": diagnostics.get("mean_confidence"),
            "cold_start_users": diagnostics.get("cold_start_users"),
            "hybrid_separation": next(
                s["separation"] for s in summary if s["method"] == "hybrid (vote)"),
            "best_single_method": best_single["method"],
            "best_single_separation": best_single["separation"],
            "hybrid_advantage": round(contest["mean_difference"], 4),
            "hybrid_advantage_ci": [round(contest["ci_low"], 4),
                                    round(contest["ci_high"], 4)],
        },
        "tables": {
            "e1_method_comparison": summary,
            "e1_segment_profile": per_segment,
        },
        "notes": notes,
    }
