"""Dashboard — Overview."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import altair as alt
import pandas as pd
import streamlit as st

from app_unified import lib

lib.page_setup("Dashboard", ":material/dashboard:")
lib.header("Marketing Orchestration",
           "Audience → automation → analytics → content, in one closed loop.", "Dashboard")

# --------------------------------------------------------------------------- #
# Empty state
# --------------------------------------------------------------------------- #
if not lib.has_bundle():
    st.markdown(
        f"""<div class="fgrid">
        <div class="fcard"><div class="fic" style="background:#E8F0FE;color:{lib.BLUE}">
          <span class="msym">groups</span></div><b>Audience</b>
          <p>Hybrid rule + ML segmentation of 8,000 users.</p></div>
        <div class="fcard"><div class="fic" style="background:#F3ECFF;color:{lib.PURPLE}">
          <span class="msym">campaign</span></div><b>Automation</b>
          <p>Fixed, trigger, and hybrid strategies compared.</p></div>
        <div class="fcard"><div class="fic" style="background:#E7F7EE;color:{lib.GREEN}">
          <span class="msym">analytics</span></div><b>Analytics</b>
          <p>Funnel, attribution, prediction, recommendations.</p></div>
        <div class="fcard"><div class="fic" style="background:#FEF3E2;color:{lib.AMBER}">
          <span class="msym">auto_awesome</span></div><b>Content</b>
          <p>Platform-native posts, scored and ranked.</p></div></div>""",
        unsafe_allow_html=True)
    st.write("")
    st.info("No run yet — open **Run Campaign** to produce your first dashboard.",
            icon=":material/info:")
    st.page_link("pages/1_Run_Campaign.py", label="Run a campaign",
                 icon=":material/rocket_launch:")
    st.stop()

# --------------------------------------------------------------------------- #
# Dashboard (bundle exists)
# --------------------------------------------------------------------------- #
b = lib.load_bundle()
seg = lib.segment_frame(b)
sc = lib.strategy_frame(b)
f = b["analytics"]["real_funnel"]
assets = b["content"].get("assets", [])
total_users = b["segmentation"]["n_users"]

# KPI tiles
lib.kpi_row([
    lib.kpi_card("Audience", f"{total_users:,}", seg["users"].tolist(), lib.BLUE,
                 f"{len(seg)} segments"),
    lib.kpi_card("Best strategy", b["automation"]["best_strategy_by_efficiency"].title(),
                 sc["conversions_per_1000_sends"].tolist(), lib.PURPLE),
    lib.kpi_card("Funnel conversion", f"{(f['convert']/f['sent'] if f['sent'] else 0):.1%}",
                 [f["sent"], f["open"], f["click"], f["convert"]], lib.GREEN),
    lib.kpi_card("Content assets", str(len(assets)),
                 [a.get("final_score", 0) for a in assets] or [0], lib.AMBER),
])

# Row: big chart + segment mix
c1, c2 = st.columns([2, 1], gap="medium")
with c1:
    with st.container(border=True):
        lib.section("Campaign performance", "Conversions per 1,000 sends, by strategy")
        st.altair_chart(
            alt.Chart(sc).mark_bar(cornerRadiusEnd=6, size=54).encode(
                x=alt.X("strategy:N", title=None),
                y=alt.Y("conversions_per_1000_sends:Q", title=None),
                color=alt.Color("strategy:N", legend=None,
                                scale=alt.Scale(range=[lib.BLUE, lib.AMBER, lib.GREEN])),
                tooltip=["strategy", "conversions_per_1000_sends"]).properties(height=270),
            use_container_width=True)
with c2:
    with st.container(border=True):
        lib.section("Segment mix", "Share of audience")
        bars = "".join(
            lib.progress_bar(r["segment"], r["users"] / total_users * 100,
                             lib.SEGMENT_COLOR.get(r["segment"], lib.BLUE),
                             f"{r['users']/total_users:.0%}")
            for _, r in seg.iterrows())
        st.markdown(bars, unsafe_allow_html=True)

# Row: donut + insights
d1, d2 = st.columns([1, 2], gap="medium")
with d1:
    with st.container(border=True):
        lib.section("Email open rate", "Real campaign funnel")
        open_rate = (f["open"] / f["sent"] * 100) if f["sent"] else 0
        st.markdown(lib.donut(open_rate, lib.BLUE, f"{open_rate:.0f}%", "OPEN RATE"),
                    unsafe_allow_html=True)
        st.caption(f"{f['open']:,} of {f['sent']:,} sent messages were opened.")
with d2:
    with st.container(border=True):
        lib.section("System insights", "Analytics → decision support")
        insights = b["analytics"].get("insights", [])
        html = "".join(lib.news_item(f"Insight {i+1}", ins)
                       for i, ins in enumerate(insights)) or "No insights yet."
        st.markdown(html, unsafe_allow_html=True)

st.caption(f"Latest run · {b['product_input'].get('product_name','—')} · "
           f"{b.get('elapsed_seconds','?')}s · engine `{b['content'].get('engine','—')}` — "
           "Team Binary · UoM · 2026")
