"""Research dashboards — per-module methods, figures, and honest model health."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app_unified import lib

lib.page_setup("Research", ":material/science:")
lib.header("Research Dashboards",
           "The evidence behind each module — methods, figures, and honestly-reported metrics.",
           "Dashboard › Research")

tabs = st.tabs([":material/groups: Segmentation", ":material/campaign: Automation",
                ":material/analytics: Analytics", ":material/auto_awesome: Content",
                ":material/biotech: Model health"])

# --- Module 1 -------------------------------------------------------------- #
with tabs[0]:
    with st.container(border=True):
        lib.section("Audience Targeting & Personalization", "Module 1")
        st.markdown(
            "- **Hybrid** rule-based + RandomForest segmentation over an 8,000-user "
            "behavioural dataset.\n"
            "- Five segments: *High Intent, Loyal Customer, Price Sensitive, Low "
            "Engagement, New Cold User*.\n"
            "- Built for **cold-start**: rule logic handles new users the clustering "
            "cannot separate.")
        if lib.has_bundle():
            st.bar_chart(lib.segment_frame(lib.load_bundle()).set_index("segment"),
                         color="#4F46E5", height=280)

# --- Module 2 -------------------------------------------------------------- #
with tabs[1]:
    with st.container(border=True):
        lib.section("Marketing Automation & Campaign Management", "Module 2")
        st.markdown(
            "- Compares **fixed**, **trigger-based**, and **hybrid** automation on the "
            "same users and content.\n"
            "- Event-driven Monte-Carlo simulator; a RandomForest conversion model drives "
            "the hybrid router.\n"
            "- Robustness: multi-seed runs, sparsity sweeps to 0.99, uplift-robustness "
            "checks — the ranking is stable.")
        if lib.has_bundle():
            st.dataframe(lib.strategy_frame(lib.load_bundle()),
                         use_container_width=True, hide_index=True)

# --- Module 3 -------------------------------------------------------------- #
with tabs[2]:
    with st.container(border=True):
        lib.section("Marketing Analytics & Decision Support", "Module 3")
        st.markdown(
            "- Funnel + drop-off analysis, **four attribution models** (first / last / "
            "linear multi-touch / Markov removal-effect), conversion & drop-off models, "
            "SHAP explainability, bootstrap 95% CIs.")
        figs = ["attribution_comparison.png", "attribution_mae.png",
                "eval_roc_conversion.png", "funnel_by_segment.png"]
        cols = st.columns(2)
        for i, fig in enumerate(figs):
            p = lib.fig_path(fig)
            if p:
                cols[i % 2].image(str(p), caption=fig.replace(".png", ""),
                                  use_container_width=True)
        mae = lib.M3_REPORTS / "attribution_mae.csv"
        if mae.exists():
            st.markdown("**Attribution error vs ground truth (lower = better):**")
            st.dataframe(pd.read_csv(mae), use_container_width=True, hide_index=True)

# --- Module 4 -------------------------------------------------------------- #
with tabs[3]:
    with st.container(border=True):
        lib.section("AI-Powered Content Refinery", "Module 4")
        st.markdown(
            "- Infers **campaign goal** and **tone** from the product, then generates "
            "platform-native posts.\n"
            "- Scored by `0.30·semantic + 0.25·platform-fit + 0.45·engagement`.\n"
            "- Two engines: a fast, model-backed template engine, and the Phi-3 LLM "
            "generator (as originally built).")
        mp = lib.ROOT / "models" / "goal_tone_training_metrics.json"
        if mp.exists():
            d = json.loads(mp.read_text())
            rows = [{"target": r["target"], "model": r["model"], "accuracy": r["accuracy"],
                     "weighted_f1": r.get("weighted_f1")} for r in d.get("results", [])]
            st.markdown(f"**Goal / tone classifier** (trained on {d.get('dataset_rows','?')} rows):")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# --- Model health ---------------------------------------------------------- #
with tabs[4]:
    with st.container(border=True):
        lib.section("Honest model health", "A research project reports its weaknesses")
        hp = lib.ROOT / "data" / "integrated" / "model_health.json"
        if hp.exists():
            data = json.loads(hp.read_text())
            st.caption(data.get("summary", ""))
            for item in data.get("findings", []):
                icon = {"ok": ":material/check_circle:", "caution": ":material/warning:",
                        "info": ":material/info:"}.get(item.get("level"), ":material/circle:")
                st.markdown(f"{icon} **{item['model']}** — {item['finding']}")
                st.caption(item.get("action", ""))
        else:
            st.info("Run `python model_health.py` to generate the report.",
                    icon=":material/info:")
