"""Design system + helpers for the unified Streamlit app.

Reference look: muted slate sidebar, light blue-grey canvas, white soft-shadow
cards, colourful KPI tiles with SVG sparklines, a donut gauge, and progress
bars. Everything is custom CSS/SVG — no fragile third-party components.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / "venv" / "bin" / "python"
PYTHON = str(VENV_PY if VENV_PY.exists() else sys.executable)
BUNDLE = ROOT / "data" / "integrated" / "run_bundle.json"
M3_FIGURES = ROOT / "modules" / "m3_analytics" / "outputs" / "figures"
M3_REPORTS = ROOT / "modules" / "m3_analytics" / "outputs" / "reports"

# Palette (matches the reference)
BLUE, AMBER, GREEN, PURPLE, RED, CYAN = (
    "#2F80ED", "#F2A93B", "#27AE60", "#8B5CF6", "#EB5757", "#0EA5E9")
INK, MUTED = "#334155", "#7C8AA5"
SEGMENT_COLOR = {
    "High Intent": GREEN, "Loyal Customer": BLUE, "Price Sensitive": AMBER,
    "Low Engagement": "#EA580C", "New Cold User": RED,
}
PLATFORM_COLOR = {
    "instagram": "#E1306C", "linkedin": "#0A66C2", "tiktok": "#111827",
    "shorts": "#FF0000", "youtube": "#FF0000", "email": "#059669", "facebook": "#1877F2",
}
_PALETTE = [BLUE, AMBER, GREEN, PURPLE, CYAN, RED]

_SVG = {
    "instagram": "M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z",
    "linkedin": "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z",
    "tiktok": "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z",
    "facebook": "M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z",
    "shorts": "M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z",
    "email": "M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z",
}
_SVG["youtube"] = _SVG["shorts"]


def platform_svg(plat: str, size: int = 18) -> str:
    d = _SVG.get(plat.lower(), _SVG["email"])
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="currentColor" '
            f'style="vertical-align:middle"><path d="{d}"/></svg>')


def _msym(icon: str) -> str:
    return f'<span class="msym">{icon.strip(":").split("/")[-1]}</span>'


# --------------------------------------------------------------------------- #
# Page + sidebar
# --------------------------------------------------------------------------- #

def page_setup(title: str, icon: str = ":material/dashboard:") -> None:
    st.set_page_config(page_title=f"{title} · Marketing OS",
                       page_icon=icon, layout="wide", initial_sidebar_state="expanded")
    st.markdown(_CSS, unsafe_allow_html=True)
    _sidebar()
    alt.themes.register("mos", _alt_theme)
    alt.themes.enable("mos")


def _alt_theme():
    return {"config": {
        "view": {"stroke": "transparent"},
        "background": "transparent",
        "font": "Inter, -apple-system, sans-serif",
        "axis": {"labelColor": MUTED, "titleColor": MUTED, "grid": True,
                 "gridColor": "#EDF1F6", "domainColor": "#E2E8F0", "tickColor": "#E2E8F0",
                 "labelFontSize": 11, "titleFontSize": 11},
        "axisX": {"grid": False, "labelAngle": 0},
        "legend": {"labelColor": MUTED, "titleColor": MUTED},
    }}


def _sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f"""<div class="brand"><div class="brand-mark">{_msym(':material/hub:')}</div>
            <div class="brand-name">MARKETING&nbsp;OS</div></div>""",
            unsafe_allow_html=True)
        st.markdown('<div class="nav-label">MENU</div>', unsafe_allow_html=True)
        st.page_link("Home.py", label="Dashboard", icon=":material/dashboard:")
        st.page_link("pages/1_Run_Campaign.py", label="Run Campaign", icon=":material/rocket_launch:")
        st.page_link("pages/2_Research_Dashboards.py", label="Research", icon=":material/science:")
        st.markdown('<div class="nav-label" style="margin-top:18px">MODULES</div>',
                    unsafe_allow_html=True)
        for lab, ic in [("Audience", "groups"), ("Automation", "campaign"),
                        ("Analytics", "analytics"), ("Content", "auto_awesome")]:
            st.markdown(f'<div class="nav-static"><span class="msym">{ic}</span>{lab}</div>',
                        unsafe_allow_html=True)
        st.markdown('<div class="sb-foot">Team Binary · UoM · 2026</div>',
                    unsafe_allow_html=True)


def header(title: str, subtitle: str, crumb: str = "Dashboard") -> None:
    st.markdown(
        f"""<div class="topbar"><div><div class="crumb">{crumb}</div>
        <div class="ph-title">{title}</div><div class="ph-sub">{subtitle}</div></div></div>""",
        unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# SVG components
# --------------------------------------------------------------------------- #

def sparkline(values, color, w: int = 240, h: int = 46) -> str:
    vals = [float(v) for v in values] or [0.0, 0.0]
    if len(vals) == 1:
        vals = vals * 2
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pts = [(i / (n - 1) * w, h - 4 - (v - lo) / rng * (h - 12)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{h} {line} {w},{h}"
    gid = "g" + color.strip("#")
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" class="spark">'
            f'<defs><linearGradient id="{gid}" x1="0" x2="0" y1="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="0.32"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0.02"/></linearGradient></defs>'
            f'<polygon points="{area}" fill="url(#{gid})"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def kpi_card(label: str, value: str, spark_values, color: str, delta: str = "") -> str:
    dhtml = f'<span class="kpi-d">{delta}</span>' if delta else ""
    return (f'<div class="kpi"><div class="kpi-l">{label}{dhtml}</div>'
            f'<div class="kpi-v" style="color:{color}">{value}</div>'
            f'{sparkline(spark_values, color)}</div>')


def kpi_row(cards: list[str]) -> None:
    st.markdown(f'<div class="kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)


def donut(pct: float, color: str, center: str, sub: str = "") -> str:
    pct = max(0.0, min(100.0, pct))
    r = 56
    c = 2 * math.pi * r
    off = c * (1 - pct / 100)
    return (f'<div class="donut-wrap"><svg viewBox="0 0 140 140" class="donut">'
            f'<circle cx="70" cy="70" r="{r}" fill="none" stroke="#EEF2F7" stroke-width="14"/>'
            f'<circle cx="70" cy="70" r="{r}" fill="none" stroke="{color}" stroke-width="14" '
            f'stroke-linecap="round" stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" '
            f'transform="rotate(-90 70 70)"/>'
            f'<text x="70" y="72" text-anchor="middle" class="donut-c">{center}</text>'
            f'<text x="70" y="90" text-anchor="middle" class="donut-s">{sub}</text></svg></div>')


def progress_bar(label: str, pct: float, color: str, value: str = "") -> str:
    pct = max(0.0, min(100.0, pct))
    return (f'<div class="pbar"><div class="pbar-top"><span>{label}</span>'
            f'<span class="pbar-v">{value}</span></div>'
            f'<div class="pbar-track"><div class="pbar-fill" '
            f'style="width:{pct:.1f}%;background:{color}"></div></div></div>')


def news_item(title: str, body: str) -> str:
    return f'<div class="news"><div class="news-t">{title}</div><div class="news-b">{body}</div></div>'


def section(title: str, subtitle: str = "") -> None:
    html = f'<div class="sec-title">{title}</div>'
    if subtitle:
        html += f'<div class="sec-sub">{subtitle}</div>'
    st.markdown(html, unsafe_allow_html=True)


def palette(i: int) -> str:
    return _PALETTE[i % len(_PALETTE)]


# --------------------------------------------------------------------------- #
# Pipeline + data
# --------------------------------------------------------------------------- #

def run_pipeline(product: dict[str, Any], engine: str,
                 on_line: Callable[[str], None]) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(product, f)
        product_path = f.name
    env = {**os.environ, "OMP_NUM_THREADS": "1", "PIPELINE_NUM_THREADS": "1",
           "TOKENIZERS_PARALLELISM": "false"}
    cmd = [PYTHON, "orchestrator.py", "--full", "--engine", engine, "--product-json", product_path]
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line and not line.startswith("W0") and "Redirects" not in line:
            on_line(line)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("Pipeline failed — see log above.")
    return load_bundle()


def load_bundle() -> dict[str, Any]:
    return json.loads(BUNDLE.read_text())


def has_bundle() -> bool:
    return BUNDLE.exists()


def strategy_frame(bundle: dict) -> pd.DataFrame:
    return pd.DataFrame(bundle["automation"]["strategy_comparison"])


def segment_frame(bundle: dict) -> pd.DataFrame:
    c = bundle["segmentation"]["segment_counts"]
    return (pd.DataFrame({"segment": list(c.keys()), "users": list(c.values())})
            .sort_values("users", ascending=False))


def fig_path(name: str) -> Path | None:
    p = M3_FIGURES / name
    return p if p.exists() else None


# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,0,0&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown {
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
.stApp { background:#EAEEF4; }
.block-container { padding-top:3.4rem; padding-bottom:3rem; max-width:1240px; }
header[data-testid="stHeader"]{ background:transparent; box-shadow:none; }
#MainMenu, footer, [data-testid="stToolbarActions"]{ visibility:hidden; }
/* Sidebar expand/collapse control — make it clearly visible on the light canvas */
[data-testid="stSidebarCollapsedControl"]{ display:flex !important; visibility:visible !important;
  left:.6rem; top:.6rem; }
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button, [data-testid="stExpandSidebarButton"]{
  color:#4A597B !important; background:#fff !important; border:1px solid #D8DFEA !important;
  border-radius:9px !important; box-shadow:0 2px 8px rgba(30,41,59,.10) !important; }
[data-testid="stSidebarCollapseButton"] button{ color:#fff !important; background:transparent !important;
  border:0 !important; box-shadow:none !important; }
h1,h2,h3,h4{ color:#1E293B; letter-spacing:-.02em; font-weight:700; }
.msym{ font-family:'Material Symbols Rounded'; font-size:20px; line-height:1;
  vertical-align:middle; -webkit-font-feature-settings:'liga'; }

/* ---- Sidebar (muted slate) ---- */
section[data-testid="stSidebar"]{ background:linear-gradient(180deg,#5C6C8E 0%,#4A597B 100%);
  border:0; }
section[data-testid="stSidebar"] *{ color:#DCE3EF; }
[data-testid="stSidebarNav"]{ display:none; }
.brand{ display:flex; gap:11px; align-items:center; padding:6px 4px 20px; }
.brand-mark{ width:36px; height:36px; border-radius:9px; display:flex; align-items:center;
  justify-content:center; background:rgba(255,255,255,.16); color:#fff; }
.brand-mark .msym{ font-size:22px; }
.brand-name{ color:#fff; font-weight:800; font-size:1.05rem; letter-spacing:.04em; }
.nav-label{ color:#A9B5CC; font-size:.66rem; font-weight:700; letter-spacing:.14em;
  margin:4px 0 6px 8px; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]{
  border-radius:9px; padding:9px 12px; margin:2px 0; font-weight:600; font-size:.95rem; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover{
  background:rgba(255,255,255,.10); }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"]{
  background:#fff; }
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] *{
  color:#3B5BDB; }
.nav-static{ color:#B9C3D8; padding:7px 12px; font-size:.9rem; font-weight:500; opacity:.75; }
.nav-static .msym{ font-size:19px; margin-right:10px; }
.sb-foot{ margin-top:24px; color:#A9B5CC; font-size:.72rem; border-top:1px solid rgba(255,255,255,.14);
  padding-top:12px; }

/* ---- Top bar / page header ---- */
.topbar{ margin:0 0 16px; }
.crumb{ color:#94A3B8; font-size:.8rem; font-weight:600; margin-bottom:2px; }
.ph-title{ font-size:1.55rem; font-weight:800; color:#1E293B; line-height:1.15; }
.ph-sub{ color:#7C8AA5; font-size:.92rem; margin-top:2px; }

/* ---- Cards (native container) ---- */
[data-testid="stVerticalBlockBorderWrapper"]{ background:#fff; border:0 !important;
  border-radius:16px; box-shadow:0 6px 20px rgba(30,41,59,.06); }
[data-testid="stVerticalBlockBorderWrapper"]>div{ padding:16px 20px; }
.sec-title{ font-size:1.02rem; font-weight:700; color:#1E293B; }
.sec-sub{ color:#8494AC; font-size:.83rem; margin:0 0 4px; }

/* ---- KPI tiles ---- */
.kpi-row{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:16px; }
.kpi{ background:#fff; border-radius:16px; padding:16px 18px 6px;
  box-shadow:0 6px 20px rgba(30,41,59,.06); }
.kpi-l{ color:#8494AC; font-size:.82rem; font-weight:600; display:flex;
  justify-content:space-between; }
.kpi-d{ color:#27AE60; font-size:.76rem; font-weight:700; }
.kpi-v{ font-size:1.75rem; font-weight:800; margin:2px 0 4px; line-height:1.1; }
.spark{ width:100%; height:44px; display:block; }

/* ---- Donut ---- */
.donut-wrap{ display:flex; justify-content:center; padding:6px 0; }
.donut{ width:160px; height:160px; }
.donut-c{ font-size:26px; font-weight:800; fill:#1E293B; }
.donut-s{ font-size:9px; font-weight:600; fill:#8494AC; letter-spacing:.05em; }

/* ---- Progress bars ---- */
.pbar{ margin:12px 2px; }
.pbar-top{ display:flex; justify-content:space-between; font-size:.83rem; color:#475569;
  font-weight:600; margin-bottom:6px; }
.pbar-v{ color:#94A3B8; font-weight:600; }
.pbar-track{ height:9px; background:#EEF2F7; border-radius:99px; overflow:hidden; }
.pbar-fill{ height:100%; border-radius:99px; }

/* ---- News list ---- */
.news{ padding:11px 2px; border-bottom:1px solid #EEF2F7; }
.news:last-child{ border-bottom:0; }
.news-t{ font-weight:700; color:#334155; font-size:.9rem; }
.news-b{ color:#8494AC; font-size:.84rem; margin-top:2px; line-height:1.45; }

/* ---- Metric / tabs / buttons / inputs ---- */
[data-testid="stMetric"]{ background:#fff; border-radius:13px; padding:12px 16px;
  box-shadow:0 4px 14px rgba(30,41,59,.05); }
[data-testid="stMetricLabel"] p{ color:#8494AC; font-weight:600; font-size:.78rem; }
.stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid #E5E9F0; }
.stTabs [data-baseweb="tab"]{ height:40px; padding:0 15px; font-weight:600; color:#7C8AA5;
  border-radius:9px 9px 0 0; }
.stTabs [aria-selected="true"]{ color:#3B5BDB; background:#EEF2FF; }
.stTabs [data-baseweb="tab-highlight"]{ background:#3B5BDB; }
.stButton>button,.stDownloadButton>button{ border-radius:10px; font-weight:600;
  border:1px solid #E5E9F0; background:#fff; color:#334155; }
.stFormSubmitButton>button{ background:#3B5BDB; color:#fff; border:0; border-radius:10px;
  font-weight:700; padding:.62rem 1rem; }
.stFormSubmitButton>button:hover{ background:#3149c0; }
[data-testid="stForm"]{ background:#fff; border:0; border-radius:16px; padding:22px 24px;
  box-shadow:0 6px 20px rgba(30,41,59,.06); }
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{
  border-radius:10px !important; border-color:#E2E8F0 !important; }
[data-testid="stWidgetLabel"] p{ font-weight:600; color:#475569; font-size:.85rem; }
[data-testid="stExpander"]{ border:1px solid #E9EDF3 !important; border-radius:12px;
  background:#fff; }
[data-testid="stDataFrame"]{ border-radius:12px; }

/* ---- Post cards ---- */
.post{ border:1px solid #EEF1F6; border-radius:14px; overflow:hidden; background:#fff;
  margin-bottom:12px; box-shadow:0 3px 12px rgba(30,41,59,.05); }
.post-head{ padding:11px 16px; color:#fff; display:flex; justify-content:space-between;
  align-items:center; font-weight:700; }
.post-head .pl{ display:flex; gap:9px; align-items:center; }
.post-body{ padding:15px 17px; color:#334155; font-size:.93rem; white-space:pre-wrap; line-height:1.55; }
.post-tags{ padding:0 17px 12px; color:#3B5BDB; font-size:.85rem; font-weight:500; }
.post-meta{ padding:9px 17px; background:#F8FAFC; font-size:.78rem; color:#64748B;
  display:flex; gap:16px; flex-wrap:wrap; border-top:1px solid #EEF2F7; }
.score-badge{ background:rgba(255,255,255,.24); padding:2px 11px; border-radius:99px;
  font-size:.78rem; font-weight:700; }
.metak{ color:#A3AEC2; }

/* ---- Feature grid (dashboard intro) ---- */
.fgrid{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
.fcard{ background:#fff; border-radius:16px; padding:16px 18px; box-shadow:0 6px 20px rgba(30,41,59,.06); }
.fcard .fic{ width:40px; height:40px; border-radius:11px; display:flex; align-items:center;
  justify-content:center; margin-bottom:10px; }
.fcard .fic .msym{ font-size:22px; }
.fcard b{ font-size:.96rem; color:#1E293B; } .fcard p{ color:#8494AC; font-size:.82rem;
  margin:.35rem 0 0; line-height:1.45; }
</style>
"""
