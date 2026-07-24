"""Run Campaign — the operational closed-loop flow (user input -> marketing)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import altair as alt
import pandas as pd
import streamlit as st

from app_unified import lib

lib.page_setup("Run Campaign", ":material/rocket_launch:")
lib.header("Run a Campaign",
           "Enter a product — the system segments the audience, picks the best strategy, "
           "analyses the funnel, and generates platform-native content.",
           "Dashboard › Run Campaign")

DEFAULTS = json.loads((lib.ROOT / "input.json").read_text())
ALL_PLATFORMS = ["instagram", "linkedin", "tiktok", "shorts", "email", "facebook"]

# --------------------------------------------------------------------------- #
# Product brief form
# --------------------------------------------------------------------------- #
with st.form("brief"):
    st.markdown("##### Product brief")
    st.caption("Tell the system what you're marketing.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        product_name = st.text_input("Product name", DEFAULTS.get("product_name", "Canva"))
        website_url = st.text_input("Website URL", DEFAULTS.get("website_url", "https://www.canva.com"))
        target_audience = st.text_input("Target audience",
                                        DEFAULTS.get("target_audience", "students and small businesses"))
    with c2:
        customer_segment = st.text_input("Customer segment",
                                         DEFAULTS.get("customer_segment", "design beginners"))
        product_description = st.text_area(
            "One-line description (optional)",
            "An easy design tool that helps anyone create professional graphics in minutes.",
            height=90)
        platforms = st.multiselect("Platforms", ALL_PLATFORMS,
                                   default=[p for p in DEFAULTS.get("preferred_platforms",
                                            ["instagram", "linkedin", "tiktok", "email"])
                                            if p in ALL_PLATFORMS])
    st.divider()
    b1, b2 = st.columns([2, 1], gap="large")
    with b1:
        engine = st.radio("Content engine", ["fast", "phi3"], horizontal=True,
                          captions=["Instant, model-scored — recommended",
                                    "Phi-3 LLM — higher quality, slower"])
    with b2:
        st.write("")
        submitted = st.form_submit_button("Run the closed loop", type="primary",
                                          use_container_width=True, icon=":material/play_arrow:")

if submitted:
    if not platforms:
        st.error("Pick at least one platform.")
        st.stop()
    product = {"product_name": product_name, "website_url": website_url,
               "target_audience": target_audience, "customer_segment": customer_segment,
               "product_description": product_description, "preferred_platforms": platforms}
    logbox, lines = st.empty(), []

    def on_line(l: str) -> None:
        lines.append(l)
        logbox.code("\n".join(lines[-15:]), language="text")

    with st.status("Running M1 → M2 → M3 → M4…", expanded=True) as status:
        try:
            bundle = lib.run_pipeline(product, engine, on_line)
            status.update(label=f"Completed in {bundle.get('elapsed_seconds','?')}s",
                          state="complete", expanded=False)
            st.session_state["bundle"] = bundle
        except Exception as exc:  # pragma: no cover
            status.update(label="Failed", state="error")
            st.exception(exc)
            st.stop()

bundle = st.session_state.get("bundle") or (lib.load_bundle() if lib.has_bundle() else None)
if not bundle:
    st.info("Fill the brief above and run the loop to see results.", icon=":material/info:")
    st.stop()

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
st.write("")
f = bundle["analytics"]["real_funnel"]
_seg = lib.segment_frame(bundle)
_sc = lib.strategy_frame(bundle)
_assets = bundle["content"].get("assets", [])
lib.kpi_row([
    lib.kpi_card("Audience", f"{bundle['segmentation']['n_users']:,}",
                 _seg["users"].tolist(), lib.BLUE, f"{len(_seg)} segments"),
    lib.kpi_card("Best strategy", bundle["automation"]["best_strategy_by_efficiency"].title(),
                 _sc["conversions_per_1000_sends"].tolist(), lib.PURPLE),
    lib.kpi_card("Funnel conversion", f"{(f['convert']/f['sent'] if f['sent'] else 0):.1%}",
                 [f["sent"], f["open"], f["click"], f["convert"]], lib.GREEN),
    lib.kpi_card("Content assets", str(len(_assets)),
                 [a.get("final_score", 0) for a in _assets] or [0], lib.AMBER),
])
st.write("")

tabs = st.tabs([":material/groups: Audience", ":material/campaign: Campaign",
                ":material/analytics: Analytics", ":material/auto_awesome: Content",
                ":material/sync: Closed loop"])

# ---- Audience ------------------------------------------------------------- #
with tabs[0]:
    with st.container(border=True):
        lib.section("Audience segments",
                    "Module 1 — hybrid rule + machine-learning segmentation")
        seg = lib.segment_frame(bundle)
        st.altair_chart(
            alt.Chart(seg).mark_bar(cornerRadiusEnd=5, height=26).encode(
                x=alt.X("users:Q", title="Users"),
                y=alt.Y("segment:N", sort="-x", title=None),
                color=alt.Color("segment:N", legend=None,
                                scale=alt.Scale(domain=list(lib.SEGMENT_COLOR),
                                                range=list(lib.SEGMENT_COLOR.values()))),
                tooltip=["segment", "users"]).properties(height=250),
            use_container_width=True)
        st.caption(f"Method: {bundle['segmentation']['method']} · mean confidence "
                   f"{bundle['segmentation'].get('mean_confidence','—')}")

# ---- Campaign ------------------------------------------------------------- #
with tabs[1]:
    with st.container(border=True):
        lib.section("Automation strategies",
                    "Module 2 — fixed vs trigger vs hybrid on one audience")
        sc = lib.strategy_frame(bundle)
        show = sc[["strategy", "open_rate", "ctr", "conversion_rate",
                   "conversions_per_1000_sends", "avg_days_to_convert", "operational_complexity"]]
        st.dataframe(show.style.format({
            "open_rate": "{:.1%}", "ctr": "{:.1%}", "conversion_rate": "{:.1%}",
            "conversions_per_1000_sends": "{:.1f}", "avg_days_to_convert": "{:.2f}"})
            .highlight_max(subset=["conversions_per_1000_sends"], color="#DCFCE7"),
            use_container_width=True, hide_index=True)
        g1, g2 = st.columns(2, gap="large")
        with g1:
            st.altair_chart(alt.Chart(sc).mark_bar(color="#4F46E5", cornerRadiusEnd=5).encode(
                x=alt.X("strategy:N", title=None),
                y=alt.Y("conversions_per_1000_sends:Q", title="Conversions / 1000 sends"),
                tooltip=["strategy", "conversions_per_1000_sends"]).properties(height=240),
                use_container_width=True)
        with g2:
            st.altair_chart(alt.Chart(sc).mark_bar(color="#7C3AED", cornerRadiusEnd=5).encode(
                x=alt.X("strategy:N", title=None),
                y=alt.Y("operational_complexity:Q", title="Operational complexity"),
                tooltip=["strategy", "operational_complexity"]).properties(height=240),
                use_container_width=True)

# ---- Analytics ------------------------------------------------------------ #
with tabs[2]:
    with st.container(border=True):
        lib.section("Campaign funnel", "Module 3 — built on the real Module 2 events")
        fd = pd.DataFrame({"stage": list(f.keys()), "users": list(f.values())})
        order = ["sent", "open", "click", "convert"]
        st.altair_chart(alt.Chart(fd).mark_bar(cornerRadiusEnd=5).encode(
            x=alt.X("stage:N", sort=order, title=None),
            y=alt.Y("users:Q", title="Unique users"),
            color=alt.Color("stage:N", legend=None,
                            scale=alt.Scale(domain=order,
                                            range=["#4F46E5", "#0EA5E9", "#F59E0B", "#16A34A"])),
            tooltip=["stage", "users"]).properties(height=240), use_container_width=True)
        drop = bundle["analytics"]["real_dropoffs"]
        dc = st.columns(len(drop))
        for col, (label, rate) in zip(dc, drop.items()):
            col.metric(f"Drop-off · {label}", f"{rate:.1%}")

    with st.container(border=True):
        lib.section("System insights", "Analytics → decision support")
        for ins in bundle["analytics"].get("insights", []):
            st.markdown(f"- {ins}")
        with st.expander("Attribution & prediction study (validated)"):
            st.caption("Attribution runs on a controlled multi-platform simulator; predictive "
                       "models are validated on real UCI Bank-Marketing data.")
            e1, e2 = st.columns(2)
            for col, fig in ((e1, "attribution_comparison.png"), (e2, "funnel_by_segment.png")):
                p = lib.fig_path(fig)
                if p:
                    col.image(str(p), use_container_width=True)
            vc = bundle["analytics"].get("validation_comparison", [])
            if vc:
                st.markdown("**Honest real-data validation (AUC):**")
                st.dataframe(pd.DataFrame(vc), use_container_width=True, hide_index=True)

# ---- Content -------------------------------------------------------------- #
with tabs[3]:
    content = bundle["content"]
    summ = content.get("summary", {})
    with st.container(border=True):
        lib.section("Generated posts",
                    f"Inferred goal `{summ.get('campaign_goal','?')}` · tone "
                    f"`{summ.get('tone','?')}` · engine `{content.get('engine','?')}`")
        assets = content.get("assets", [])
        for a in assets:
            plat = str(a["platform"]).lower()
            color = lib.PLATFORM_COLOR.get(plat, "#334155")
            tags = a.get("hashtags") or []
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags.replace("'", '"'))
                except Exception:
                    tags = [tags]
            prompt = a.get("image_prompt") or a.get("shorts_prompt") or ""
            st.markdown(
                f"""
                <div class="post">
                  <div class="post-head" style="background:{color}">
                    <span class="pl">{lib.platform_svg(plat)} {plat.title()}</span>
                    <span class="score-badge">score {a.get('final_score',0):.2f}</span>
                  </div>
                  <div class="post-body">{a.get('caption','')}</div>
                  <div class="post-tags">{' '.join(tags)}</div>
                  <div class="post-meta">
                    <span><span class="metak">CTA</span> {a.get('cta','')}</span>
                    <span><span class="metak">engagement</span> {a.get('engagement_score',0):.2f}</span>
                    <span><span class="metak">platform-fit</span> {a.get('platform_suitability_score',0):.2f}</span>
                    <span><span class="metak">semantic</span> {a.get('semantic_score',0):.2f}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            with st.expander(f"Creative brief & copy — {plat.title()}"):
                st.caption("Visual prompt")
                st.write(prompt or "—")
                st.caption("Copy-ready caption")
                st.code(a.get("caption", "") + ("\n\n" + " ".join(tags) if tags else ""),
                        language="text")

    with st.container(border=True):
        lib.section("Export & schedule", "Preview-only — never auto-posts to live platforms")
        e1, e2, e3 = st.columns(3)
        e1.download_button("Download JSON", json.dumps(assets, indent=2),
                           "marketing_assets.json", "application/json",
                           icon=":material/download:", use_container_width=True)
        e2.download_button("Download CSV", pd.DataFrame(assets).to_csv(index=False),
                           "marketing_assets.csv", "text/csv",
                           icon=":material/download:", use_container_width=True)
        txt = "\n\n".join(f"[{a['platform'].upper()}]\n{a['caption']}\n"
                          f"{' '.join(a.get('hashtags') or [])}\nCTA: {a.get('cta','')}"
                          for a in assets)
        e3.download_button("Download TXT", txt, "marketing_assets.txt", "text/plain",
                           icon=":material/download:", use_container_width=True)
        s1, s2 = st.columns(2)
        start = s1.date_input("Start date", datetime.now().date())
        cadence = s2.number_input("Days between posts", 1, 14, 2)
        sched = [{"when": (datetime.combine(start, datetime.min.time())
                           + timedelta(days=i * cadence, hours=10)).strftime("%a %d %b · %H:%M"),
                  "platform": a["platform"], "preview": a["caption"][:64] + "…"}
                 for i, a in enumerate(assets)]
        st.dataframe(pd.DataFrame(sched), use_container_width=True, hide_index=True)

# ---- Closed loop ---------------------------------------------------------- #
with tabs[4]:
    with st.container(border=True):
        lib.section("The feedback that closes the loop",
                    "Analytics ranks platforms by conversion credit; content targets them first")
        pr = bundle["content_priorities"]
        ranking = pr.get("platform_ranking", {})
        if ranking:
            rk = pd.DataFrame({"platform": list(ranking), "credit": list(ranking.values())})
            st.altair_chart(alt.Chart(rk).mark_bar(color="#0EA5E9", cornerRadiusEnd=5, height=24)
                            .encode(x=alt.X("credit:Q", title="Aggregate conversion credit"),
                                    y=alt.Y("platform:N", sort="-x", title=None),
                                    tooltip=["platform", "credit"]).properties(height=230),
                            use_container_width=True)
        st.write("**Content platform order (after feedback):** "
                 + " → ".join(bundle["content"].get("platform_order", [])))
        if pr.get("best_strategy"):
            st.success(f"Recommended automation strategy from analytics: "
                       f"**{pr['best_strategy']['strategy'].title()}** "
                       f"({pr['best_strategy']['conversion_rate']:.1%} conversion).",
                       icon=":material/recommend:")
