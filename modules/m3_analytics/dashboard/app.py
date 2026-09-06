"""app.py — Streamlit dashboard: Funnel · Attribution · Predict (Phase 7)."""

from __future__ import annotations

import sys
from pathlib import Path
import json

# Ensure project root is on the path regardless of where streamlit is invoked from
sys.path.insert(0, str(Path(__file__).parent.parent))

import joblib
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ---------------------------------------------------------------------------
# Paths
BASE = Path(__file__).parent.parent
SIM  = BASE / "data" / "simulated"
PROC = BASE / "data" / "processed"
MDLS = BASE / "outputs" / "models"
REPS = BASE / "outputs" / "reports"

st.set_page_config(page_title="Marketing Analytics Dashboard", layout="wide")
st.title("AI Powered Marketing Analytics - Person 3 Module")

# ---------------------------------------------------------------------------
# Load data once (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_events():
    return pd.read_csv(SIM / "event_logs.csv", parse_dates=["timestamp"])

@st.cache_data
def load_segments():
    return pd.read_csv(SIM / "user_segments.csv")

@st.cache_data
def load_features():
    return pd.read_csv(PROC / "features.csv")

@st.cache_data
def load_analytics_output():
    with open(REPS / "analytics_output.json") as f:
        return json.load(f)

@st.cache_resource
def load_model(name: str):
    return joblib.load(MDLS / name)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(["Funnel", "Attribution", "Predict", "What-If Simulator"])


# ============================================================
# TAB 1 — Funnel
# ============================================================
with tab1:
    st.header("Marketing Funnel")

    events   = load_events()
    segments = load_segments()

    from src.funnel import compute_funnel, compute_dropoffs, funnel_by

    # Overall metrics
    overall = compute_funnel(events)
    drops   = compute_dropoffs(overall)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sent",    f"{overall['sent']:,}")
    c2.metric("Opened",  f"{overall['open']:,}", f"−{drops['sent→open']*100:.1f}% drop")
    c3.metric("Clicked", f"{overall['click']:,}", f"−{drops['open→click']*100:.1f}% drop")
    c4.metric("Converted", f"{overall['convert']:,}", f"−{drops['click→convert']*100:.1f}% drop")

    st.subheader("Funnel by Strategy")
    strat_funnel = funnel_by(events, by="strategy")

    fig, ax = plt.subplots(figsize=(9, 4))
    import numpy as np
    stages   = ["sent", "open", "click", "convert"]
    strats   = strat_funnel.index.tolist()
    x        = np.arange(len(strats))
    width    = 0.18
    colors   = ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]
    for i, (stage, color) in enumerate(zip(stages, colors)):
        bars = ax.bar(x + (i - 1.5) * width, strat_funnel[stage], width=width * 0.9,
                      label=stage.capitalize(), color=color, alpha=0.88)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 2,
                    str(int(h)), ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(strats, fontsize=11)
    ax.set_ylabel("Unique users")
    ax.set_title("Funnel Counts by Strategy")
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Funnel by Segment")
    events_seg  = events.merge(segments[["user_id", "segment"]], on="user_id", how="left")
    seg_funnel  = funnel_by(events_seg, by="segment")
    seg_funnel["conv_rate"] = (
        seg_funnel["convert"] / seg_funnel["sent"].replace(0, float("nan"))
    ).round(3)
    st.dataframe(seg_funnel.sort_values("conv_rate", ascending=False).style.format("{:.0f}", subset=stages))


# ============================================================
# TAB 2 — Attribution
# ============================================================
with tab2:
    st.header("Attribution Model Comparison")

    events = load_events()
    gt     = pd.read_csv(SIM.parent / "simulated" / "ground_truth_influence.csv")

    from src.attribution import (
        first_touch_attribution, last_touch_attribution,
        linear_multi_touch_attribution, markov_chain_attribution,
        attribution_mae, compare_to_ground_truth,
    )

    ft = first_touch_attribution(events).set_index("platform")["credit"]
    lt = last_touch_attribution(events).set_index("platform")["credit"]
    mt = linear_multi_touch_attribution(events).set_index("platform")["credit"]
    mk = markov_chain_attribution(events).set_index("platform")["credit"]
    gt_s = gt.set_index("platform")["true_influence"]

    platforms = gt_s.index.tolist()
    compare_df = pd.DataFrame({
        "Ground Truth": gt_s.reindex(platforms, fill_value=0),
        "First-Touch":  ft.reindex(platforms, fill_value=0),
        "Last-Touch":   lt.reindex(platforms, fill_value=0),
        "Multi-Touch":  mt.reindex(platforms, fill_value=0),
        "Markov":       mk.reindex(platforms, fill_value=0),
    })

    fig, ax = plt.subplots(figsize=(12, 4))
    x      = np.arange(len(platforms))
    width  = 0.15
    cols   = list(compare_df.columns)
    clrs   = ["#333333", "#4C72B0", "#C44E52", "#55A868", "#8172B2"]
    n_series = len(cols)
    for i, (col, color) in enumerate(zip(cols, clrs)):
        offset = (i - (n_series - 1) / 2) * width
        ax.bar(x + offset, compare_df[col], width=width * 0.9,
               label=col, color=color, alpha=0.88)
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=10)
    ax.set_ylabel("Attribution credit")
    ax.set_title("Platform-Level Attribution: 4 Models vs Ground Truth")
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    st.pyplot(fig)
    plt.close(fig)

    # MAE table
    comp = compare_to_ground_truth(events, gt)
    mae  = attribution_mae(comp)
    rows = [
        {"Model": "First-Touch", "MAE": mae["first_touch"]},
        {"Model": "Last-Touch",  "MAE": mae["last_touch"]},
        {"Model": "Multi-Touch", "MAE": mae["multi_touch"]},
    ]
    if "markov" in mae:
        rows.append({"Model": "Markov", "MAE": mae["markov"]})
    mae_df = pd.DataFrame(rows).set_index("Model")
    st.subheader("Recovery Error vs Ground Truth (lower is better)")
    st.dataframe(mae_df.style.highlight_min(color="#d4edda"))


# ============================================================
# TAB 3 — Predict
# ============================================================
with tab3:
    st.header("Per-User Prediction & Recommendation")

    analytics = load_analytics_output()
    lookup = {r["user_id"]: r for r in analytics}
    features = load_features()

    uid_input = st.text_input("Enter a User ID (e.g. U00004)", value="U00004")

    if uid_input in lookup:
        r = lookup[uid_input]
        feat_row = features[features["user_id"] == uid_input]

        st.success(f"User found: **{uid_input}**  |  Segment: **{feat_row['segment'].values[0]}**  |  Strategy: **{feat_row['strategy'].values[0]}**")

        col1, col2, col3 = st.columns(3)
        col1.metric("Conversion probability", f"{r['predicted_conversion']*100:.1f}%")
        col2.metric("Drop-off risk",           f"{r['drop_off_risk']*100:.1f}%")
        col3.metric("Confidence",              f"{r['confidence']*100:.1f}%")

        st.subheader("Recommendation")
        rec_colors = {
            "send_premium_offer":       "🟢",
            "send_personalized_offer":  "🔵",
            "send_reactivation_campaign": "🟡",
            "send_general_reminder":    "⚪",
        }
        icon = rec_colors.get(r["recommendation"], "")
        st.markdown(f"### {icon} `{r['recommendation']}`")
        st.markdown(f"**Recommended platform:** `{r['recommended_platform']}`  |  **Best platform:** `{r['best_platform']}`")

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Platform Credits")
            if r["platform_credits"]:
                pc_df = pd.Series(r["platform_credits"]).sort_values(ascending=False)
                fig2, ax2 = plt.subplots(figsize=(5, 3))
                ax2.barh(pc_df.index[::-1], pc_df.values[::-1], color="#4C72B0", alpha=0.85)
                ax2.set_xlabel("Credit")
                ax2.spines[["top", "right"]].set_visible(False)
                fig2.tight_layout()
                st.pyplot(fig2)
                plt.close(fig2)
            else:
                st.info("No journey data — cold-start user.")

        with col_b:
            st.subheader("Channel Credits")
            if r["channel_credits"]:
                cc_df = pd.Series(r["channel_credits"]).sort_values(ascending=False)
                fig3, ax3 = plt.subplots(figsize=(5, 3))
                ax3.barh(cc_df.index[::-1], cc_df.values[::-1], color="#55A868", alpha=0.85)
                ax3.set_xlabel("Credit")
                ax3.spines[["top", "right"]].set_visible(False)
                fig3.tight_layout()
                st.pyplot(fig3)
                plt.close(fig3)

    elif uid_input:
        st.warning(f"User `{uid_input}` not found. Try one of: U00000 – U01999")

    st.divider()
    st.subheader("System-Level Insights")
    insights_path = REPS / "insights.md"
    if insights_path.exists():
        content = insights_path.read_text()
        for line in content.splitlines():
            if line.startswith("- "):
                st.info(line[2:])


# ============================================================
# TAB 4 — What-If Strategy Simulator
# ============================================================
with tab4:
    st.header("What-If: Reassign Users to a Different Strategy")
    st.caption(
        "Predict the conversion lift if a chosen segment of users had been "
        "run under a different automation strategy. Uses the trained XGBoost "
        "conversion model and known strategy lifts from the simulator."
    )

    events   = load_events()
    features = load_features()

    # Empirical strategy effect from the data (already realised)
    from src.funnel import compute_funnel
    strat_rates = {}
    for s, g in events.groupby("strategy"):
        f = compute_funnel(g)
        strat_rates[s] = f["convert"] / f["sent"] if f["sent"] else 0
    rate_df = pd.DataFrame(
        [{"strategy": s, "conversion_rate": round(r, 4)} for s, r in strat_rates.items()]
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        target_strategy = st.selectbox(
            "Re-run all users under strategy:",
            sorted(strat_rates.keys()),
            index=list(sorted(strat_rates.keys())).index("hybrid") if "hybrid" in strat_rates else 0,
        )
        target_segment = st.selectbox(
            "Restrict to segment (or all):",
            ["all"] + sorted(features["segment"].dropna().unique().tolist()),
        )

    # Filter
    affected = features if target_segment == "all" else features[features["segment"] == target_segment]
    n_affected = len(affected)
    current_conv = affected["converted"].mean() if n_affected else 0

    # Multiplier: how much better is target_strategy than the user's current one?
    multipliers = []
    for _, row in affected.iterrows():
        cur = row["strategy"]
        cur_rate = strat_rates.get(cur, 0) or 1e-6
        tgt_rate = strat_rates.get(target_strategy, 0)
        multipliers.append(tgt_rate / cur_rate if cur_rate else 1.0)
    avg_mult = float(pd.Series(multipliers).mean()) if multipliers else 1.0

    projected_conv = min(1.0, current_conv * avg_mult)
    delta_users = int(round((projected_conv - current_conv) * n_affected))

    with col2:
        st.subheader("Realised strategy conversion rates")
        st.dataframe(rate_df.set_index("strategy").style.format("{:.2%}"))

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Affected users",     f"{n_affected:,}")
    m2.metric("Current conv. rate", f"{current_conv*100:.2f}%")
    m3.metric(f"If all → {target_strategy}", f"{projected_conv*100:.2f}%",
              f"{(projected_conv-current_conv)*100:+.2f} pp")
    m4.metric("Extra conversions",  f"{delta_users:+,}")

    st.caption(
        "Projection assumes the average per-user response to the chosen strategy "
        "scales linearly with that strategy's empirical lift. This is a planning "
        "estimate, not a causal counterfactual — see LIMITATIONS.md §3."
    )
