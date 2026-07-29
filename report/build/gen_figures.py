"""Architecture / flow diagrams and screenshot placeholders for the report.

Run:  python3 report/build/gen_figures.py
Writes to report/assets/ and report/assets/placeholders/.

The placeholders exist so the report's layout, figure numbering and List of
Figures are complete before the real screenshots are taken. Replace the file
of the same name with a real screenshot and rebuild — nothing else changes.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = "/Users/arkamzakir/Documents/Research/Research"
OUT = f"{ROOT}/report/assets"
SHOTS = f"{OUT}/placeholders"
os.makedirs(OUT, exist_ok=True)
os.makedirs(SHOTS, exist_ok=True)

INK = "#1f2933"
MUTED = "#5b6b7a"
BLUE, BLUE_E = "#dbeafe", "#2563eb"
GREEN, GREEN_E = "#dcfce7", "#16a34a"
AMBER, AMBER_E = "#fef3c7", "#d97706"
PURPLE, PURPLE_E = "#ede9fe", "#7c3aed"
GREY, GREY_E = "#f1f5f9", "#64748b"
ROSE, ROSE_E = "#ffe4e6", "#e11d48"
TEAL, TEAL_E = "#ccfbf1", "#0d9488"

plt.rcParams["font.family"] = "DejaVu Sans"


def box(ax, x, y, w, h, text, fc=BLUE, ec=BLUE_E, fs=9, bold=False, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.006,rounding_size=0.02",
                                facecolor=fc, edgecolor=ec, linewidth=1.3,
                                linestyle=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=INK, wrap=True,
            fontweight="bold" if bold else "normal", linespacing=1.35)


def band(ax, x, y, w, h, label, fc="#fafbfc", ec="#cbd5e1"):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.004,rounding_size=0.015",
                                facecolor=fc, edgecolor=ec, linewidth=1.0,
                                linestyle=(0, (4, 3))))
    ax.text(x + 0.014, y + h - 0.038, label, ha="left", va="top",
            fontsize=8, color=MUTED, fontweight="bold")


def arrow(ax, p1, p2, text=None, color=GREY_E, rad=0.0, fs=7.5, style="-|>",
          ls="-", toff=(0, 0.018)):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13,
                                 color=color, linewidth=1.3, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}",
                                 shrinkA=2, shrinkB=2))
    if text:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx + toff[0], my + toff[1], text, ha="center", va="center",
                fontsize=fs, color=color, style="italic",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"))


def canvas(w=11, h=6.4):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def save(fig, name, folder=OUT):
    fig.savefig(f"{folder}/{name}", dpi=220, bbox_inches="tight",
                facecolor="white", pad_inches=0.12)
    plt.close(fig)
    print("wrote", name)


# ------------------------------------------------------------- Figure 1
def fig1_loop():
    fig, ax = canvas(11, 6.2)
    ax.text(0.5, 0.965, "Closed-Loop Marketing Orchestration",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    box(ax, 0.03, 0.60, 0.20, 0.15,
        "Demo e-commerce store\n8,000 imported customers\n+ live browser sessions",
        GREY, GREY_E, 8.5)
    box(ax, 0.29, 0.60, 0.19, 0.15,
        "Module 1\nAudience Targeting\n& Personalization", BLUE, BLUE_E, 9, True)
    box(ax, 0.545, 0.60, 0.19, 0.15,
        "Module 2\nCampaign Automation\nfixed · trigger · hybrid", GREEN, GREEN_E, 9, True)
    box(ax, 0.795, 0.60, 0.175, 0.15,
        "Action executed\n(the company's\nown tools)", GREY, GREY_E, 8.5)

    box(ax, 0.545, 0.26, 0.19, 0.15,
        "Module 3\nAnalytics &\nDecision Support", AMBER, AMBER_E, 9, True)
    box(ax, 0.29, 0.26, 0.19, 0.15,
        "Module 4\nAI Content Refinery\n& Distribution", PURPLE, PURPLE_E, 9, True)
    box(ax, 0.795, 0.26, 0.175, 0.15,
        "action_log\naction · propensity\n· outcome", TEAL, TEAL_E, 8.5, True)

    box(ax, 0.03, 0.26, 0.20, 0.15,
        "Action Plan\n(who · what · why)\ndelivered to marketer",
        ROSE, ROSE_E, 8.5, True)

    arrow(ax, (0.23, 0.675), (0.29, 0.675), "customers")
    arrow(ax, (0.48, 0.675), (0.545, 0.675), "segments")
    arrow(ax, (0.735, 0.675), (0.795, 0.675), "plan")
    arrow(ax, (0.8825, 0.60), (0.8825, 0.41), "outcome")
    arrow(ax, (0.795, 0.335), (0.735, 0.335), "logged\ndecisions")
    arrow(ax, (0.545, 0.335), (0.48, 0.335), "platform\npriority")
    arrow(ax, (0.29, 0.335), (0.23, 0.335), "assets")

    arrow(ax, (0.13, 0.41), (0.13, 0.60), "re-targeting", BLUE_E)
    arrow(ax, (0.64, 0.41), (0.64, 0.60), "off-policy\nevaluation", AMBER_E,
          rad=-0.45, toff=(0.085, 0))

    ax.text(0.5, 0.125,
            "The loop closes twice: analytics output re-enters segmentation, automation and content, "
            "and every decision\nis written to an append-only log with the probability it was taken "
            "under — which is what makes the policy learnable.",
            ha="center", fontsize=8.5, color=MUTED, linespacing=1.5)
    save(fig, "fig01_closed_loop.png")


# ------------------------------------------------------------- Figure 2
def fig2_architecture():
    fig, ax = canvas(11, 7.6)
    ax.text(0.5, 0.975, "High-Level System Architecture",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    band(ax, 0.02, 0.775, 0.96, 0.155, "PRESENTATION LAYER")
    box(ax, 0.05, 0.805, 0.21, 0.082, "Marketer dashboard\nNext.js 16 + Recharts\n(7 pages)",
        BLUE, BLUE_E, 8, True)
    box(ax, 0.295, 0.805, 0.185, 0.082, "Auth pages\nlogin · signup ·\nsite onboarding",
        BLUE, BLUE_E, 8)
    box(ax, 0.515, 0.805, 0.20, 0.082, "Demo e-commerce store\n(the site under study)",
        GREY, GREY_E, 8.5)
    box(ax, 0.75, 0.805, 0.20, 0.082, "Browser visitor\nfirst-party · DNT honoured",
        GREY, GREY_E, 8)

    band(ax, 0.02, 0.545, 0.96, 0.195, "APPLICATION LAYER — FastAPI")
    box(ax, 0.045, 0.585, 0.16, 0.10,
        "Routers\n/segments /campaigns\n/analytics /content\n/actions /decisions", GREEN, GREEN_E, 7.5)
    box(ax, 0.232, 0.585, 0.155, 0.10,
        "Public tracking\n/collect · /mos.js\n/track/* · /l/*", GREEN, GREEN_E, 7.5)
    box(ax, 0.414, 0.585, 0.16, 0.10,
        "Ownership\nmiddleware\n(tenant isolation)", ROSE, ROSE_E, 7.5, True)
    box(ax, 0.601, 0.585, 0.155, 0.10,
        "Decision service\naction catalogue +\npropensity logging", TEAL, TEAL_E, 7.5, True)
    box(ax, 0.783, 0.585, 0.167, 0.10,
        "Provenance service\nsource = dataset | live\n(derived, not asserted)", GREEN, GREEN_E, 7.5)

    band(ax, 0.02, 0.285, 0.96, 0.225, "RESEARCH MODULE LAYER — Python / scikit-learn / XGBoost")
    box(ax, 0.040, 0.320, 0.205, 0.145,
        "Module 1\nHybrid Segmentation\n\nrules + k-means +\nhierarchical → vote\n+ calibrated confidence",
        BLUE, BLUE_E, 7.8)
    box(ax, 0.283, 0.320, 0.205, 0.145,
        "Module 2\nCampaign Automation\n\nfixed · trigger · hybrid\npolicy engine +\nresponse simulator",
        GREEN, GREEN_E, 7.8)
    box(ax, 0.526, 0.320, 0.205, 0.145,
        "Module 3\nAnalytics & Decision\nSupport\n\nfunnel · attribution ·\nprediction · uplift · OPE",
        AMBER, AMBER_E, 7.8)
    box(ax, 0.769, 0.320, 0.20, 0.145,
        "Module 4\nAI Content Refinery\n\ncrawler · capability\ndetection · goal/tone ·\ngeneration · scoring",
        PURPLE, PURPLE_E, 7.8)

    band(ax, 0.02, 0.030, 0.96, 0.215, "DATA LAYER — PostgreSQL 16")
    cells = [("visitors / sites", "source derived"),
             ("user_segments", "segment + confidence"),
             ("interactions", "source derived"),
             ("action_log", "action · propensity ·\nreward"),
             ("content_assets", "scored assets")]
    for i, (nm, sub) in enumerate(cells):
        box(ax, 0.042 + i * 0.188, 0.068, 0.168, 0.105, f"{nm}\n\n{sub}",
            GREY, GREY_E, 7.6)

    arrow(ax, (0.15, 0.805), (0.15, 0.685), "HTTPS / JSON")
    arrow(ax, (0.615, 0.805), (0.31, 0.685), "beacon", rad=-0.15)
    arrow(ax, (0.85, 0.800), (0.715, 0.800), "browses")
    arrow(ax, (0.35, 0.585), (0.35, 0.465), "invoke")
    arrow(ax, (0.66, 0.585), (0.63, 0.465))
    arrow(ax, (0.50, 0.320), (0.50, 0.245), "read / write", toff=(0.058, 0))
    save(fig, "fig02_architecture.png")


# ------------------------------------------------------------- Figure 3
def fig3_research_pipeline():
    fig, ax = canvas(11, 5.8)
    ax.text(0.5, 0.96, "The Research Pipeline — one command, no hand-copied numbers",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    box(ax, 0.025, 0.55, 0.17, 0.21,
        "Data sources\n\n8,000-customer dataset\nHillstrom (64,000)\nengagement corpus\ngoal/tone corpus\n15 real websites",
        GREY, GREY_E, 7.8)
    box(ax, 0.235, 0.55, 0.20, 0.21,
        "research/experiments/\n\nE1 … E11\neach writes its own\nCSV tables",
        AMBER, AMBER_E, 8.2, True)
    box(ax, 0.475, 0.55, 0.155, 0.21,
        "research/stats.py\n\nbootstrap ·\nWilcoxon · McNemar ·\nWilson · Cliff's δ",
        GREEN, GREEN_E, 8)
    box(ax, 0.67, 0.55, 0.16, 0.21,
        "results.json\n\nevery metric,\ntable and note",
        TEAL, TEAL_E, 8.5, True)

    box(ax, 0.30, 0.17, 0.20, 0.19,
        "research/figures.py\n\n13 figures drawn\nfrom the tables —\nnever hand-plotted",
        PURPLE, PURPLE_E, 8)
    box(ax, 0.555, 0.17, 0.215, 0.19,
        "research/chapters.py\n\nprose authored ONCE,\nnumbers interpolated",
        BLUE, BLUE_E, 8, True)
    box(ax, 0.815, 0.17, 0.165, 0.19,
        "docs/research/*.md\n+\ncontent_research.py\n→ Chapter 7",
        ROSE, ROSE_E, 8)

    arrow(ax, (0.195, 0.655), (0.235, 0.655))
    arrow(ax, (0.435, 0.655), (0.475, 0.655))
    arrow(ax, (0.63, 0.655), (0.67, 0.655))
    arrow(ax, (0.72, 0.55), (0.42, 0.36), rad=0.18)
    arrow(ax, (0.77, 0.55), (0.665, 0.36), rad=-0.12)
    arrow(ax, (0.77, 0.265), (0.815, 0.265))
    arrow(ax, (0.50, 0.265), (0.555, 0.265), "figures")

    ax.text(0.5, 0.055,
            "`make research` runs all eleven experiments, recomputes every interval, redraws every figure and "
            "regenerates\nChapter 7. A chart therefore cannot disagree with the number it plots, and the report "
            "cannot drift from the code.",
            ha="center", fontsize=8.5, color=MUTED, linespacing=1.5)
    save(fig, "fig03_research_pipeline.png")


# ------------------------------------------------------------- Figure 4
def fig4_importer():
    fig, ax = canvas(11, 6.0)
    ax.text(0.5, 0.96, "The Importer — what is measured and what is reconstructed",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    box(ax, 0.03, 0.50, 0.20, 0.31,
        "Digital Marketing\nCampaign dataset\n\n8,000 real customers\nrecorded as\nPER-CUSTOMER TOTALS",
        GREY, GREY_E, 8.5, True)

    box(ax, 0.29, 0.605, 0.29, 0.215,
        "MEASURED — preserved exactly\n\nsessions · page views · time on site\non-site clicks · purchases\n"
        "email opens and clicks\nconversion outcome · channel",
        GREEN, GREEN_E, 8)
    box(ax, 0.29, 0.325, 0.29, 0.215,
        "RECONSTRUCTED — declared\n\ntimestamp of each visit\nwhich page each visit landed on\n"
        "scroll depth · event ordering\nbasket value",
        AMBER, AMBER_E, 8)

    box(ax, 0.645, 0.60, 0.20, 0.19,
        "One event per VISIT\ncarrying that visit's counts\n\n(a live browser writes one\nevent per page, no count)",
        BLUE, BLUE_E, 8)
    box(ax, 0.645, 0.34, 0.20, 0.175,
        "source = 'dataset'\nderived at write time\nfrom the visitor row",
        ROSE, ROSE_E, 8.5, True)

    box(ax, 0.885, 0.40, 0.10, 0.35,
        "One\nfeature\ndefinition\nserves\nboth",
        TEAL, TEAL_E, 8.5, True)

    arrow(ax, (0.23, 0.71), (0.29, 0.71))
    arrow(ax, (0.23, 0.58), (0.29, 0.43))
    arrow(ax, (0.58, 0.71), (0.645, 0.68), rad=-0.1)
    arrow(ax, (0.58, 0.43), (0.645, 0.42), rad=0.1)
    arrow(ax, (0.845, 0.66), (0.885, 0.60))
    arrow(ax, (0.845, 0.42), (0.885, 0.50))

    ax.text(0.5, 0.16,
            "Fidelity is verified against the source CSV — sessions, page views, time on site, clicks and purchases "
            "all match exactly,\nand a re-import is byte-identical. Results resting only on totals are measurements; "
            "results resting on order or timing\nare properties of the reconstruction, and Chapter 7 says which is which "
            "every time it matters.",
            ha="center", fontsize=8.3, color=MUTED, linespacing=1.55)
    save(fig, "fig04_importer.png")


# ------------------------------------------------------------- Figure 5
def fig5_m1():
    fig, ax = canvas(10.5, 6.6)
    ax.text(0.5, 0.965, "Module 1 — Audience Targeting and Personalization",
            ha="center", fontsize=12, fontweight="bold", color=INK)

    box(ax, 0.03, 0.745, 0.185, 0.125, "Customer behaviour\n\n8,000 imported +\nlive visitors",
        GREY, GREY_E, 8)
    box(ax, 0.255, 0.745, 0.185, 0.125, "Preprocessing\n\nmissing values ·\nencoding · scaling",
        GREY, GREY_E, 8)
    box(ax, 0.48, 0.745, 0.20, 0.125, "Feature engineering\n\nengagement score ·\nclick ratio · recency",
        GREY, GREY_E, 8)

    band(ax, 0.185, 0.405, 0.63, 0.27, "THREE METHODS OVER THE SAME FEATURE MATRIX")
    box(ax, 0.212, 0.465, 0.17, 0.135, "Rule-based\n\ninterpretable ·\nthe only method that\ncan say 'no evidence'",
        BLUE, BLUE_E, 7.8)
    box(ax, 0.412, 0.465, 0.17, 0.135, "k-means\n\nk = 4 ·\nscaled features",
        BLUE, BLUE_E, 8)
    box(ax, 0.612, 0.465, 0.17, 0.135, "Hierarchical\n\nWard linkage",
        BLUE, BLUE_E, 8)

    box(ax, 0.215, 0.215, 0.57, 0.145,
        "AGREEMENT VOTE — the order is the contribution\n"
        "①  all three agree  →  highest confidence\n"
        "②  cold-start rule  →  resolved NEXT, before any clustering comparison\n"
        "③  majority  →  medium         ④  all disagree  →  rules label, lowest",
        AMBER, AMBER_E, 8, True)

    box(ax, 0.04, 0.035, 0.42, 0.13,
        "Five shared segments\nHigh Intent · Loyal Customer · Price Sensitive\nLow Engagement · New Cold User",
        GREEN, GREEN_E, 8)
    box(ax, 0.53, 0.035, 0.43, 0.13,
        "user_segments → Modules 2, 3 and 4\nsegment · method · calibrated confidence\n"
        "(segments under 30 customers: reported, excluded from statistics)",
        GREEN, GREEN_E, 8)

    arrow(ax, (0.215, 0.807), (0.255, 0.807))
    arrow(ax, (0.44, 0.807), (0.48, 0.807))
    arrow(ax, (0.58, 0.745), (0.50, 0.675))
    for x in (0.297, 0.497, 0.697):
        arrow(ax, (x, 0.465), (0.50, 0.36), rad=0.05)
    arrow(ax, (0.38, 0.215), (0.25, 0.165))
    arrow(ax, (0.62, 0.215), (0.74, 0.165))
    save(fig, "fig05_module1.png")


# ------------------------------------------------------------- Figure 6
def fig6_m2():
    fig, ax = canvas(10.5, 6.0)
    ax.text(0.5, 0.965, "Module 2 — Marketing Automation and Campaign Management",
            ha="center", fontsize=12, fontweight="bold", color=INK)

    box(ax, 0.035, 0.68, 0.19, 0.14, "Inputs\n\nsegment labels (M1) ·\ncustomer profile",
        GREY, GREY_E, 8)
    box(ax, 0.275, 0.68, 0.19, 0.14, "Response model\n\nLogReg / RandomForest\nvs Dummy baseline",
        GREEN, GREEN_E, 8)
    box(ax, 0.515, 0.68, 0.19, 0.14, "Policy engine\n\nthe ONLY component\nthat differs",
        GREEN, GREEN_E, 8.5, True)
    box(ax, 0.755, 0.68, 0.20, 0.14, "Message templates\n\nwelcome · info ·\nsocial proof · offer",
        GREY, GREY_E, 8)

    band(ax, 0.09, 0.335, 0.82, 0.245, "THREE POLICIES · SAME 8,000 CUSTOMERS · 30 PAIRED SEEDS")
    box(ax, 0.125, 0.395, 0.225, 0.125, "Fixed workflow\n\n1 rule · 4.00 msgs/user\n7.15 conv / 1,000 sends",
        BLUE, BLUE_E, 8)
    box(ax, 0.388, 0.395, 0.225, 0.125, "Trigger-based\n\n4 rules · 1.32 msgs/user\n10.45 conv / 1,000 sends",
        AMBER, AMBER_E, 8, True)
    box(ax, 0.651, 0.395, 0.225, 0.125, "Hybrid\n\n9 rules · 3.05 msgs/user\n7.99 conv / 1,000 sends",
        BLUE, BLUE_E, 8)

    box(ax, 0.09, 0.155, 0.37, 0.10, "Response simulator\nsegment-level propensities",
        GREY, GREY_E, 8)
    box(ax, 0.54, 0.155, 0.37, 0.10, "Evaluation layer\nconversions per 1,000 sends · rules · cost",
        GREY, GREY_E, 8)
    box(ax, 0.27, 0.025, 0.46, 0.085, "interactions + action_log → Module 3",
        GREEN, GREEN_E, 8.5, True)

    arrow(ax, (0.225, 0.75), (0.275, 0.75))
    arrow(ax, (0.465, 0.75), (0.515, 0.75))
    arrow(ax, (0.755, 0.75), (0.705, 0.75))
    arrow(ax, (0.61, 0.68), (0.50, 0.58))
    arrow(ax, (0.275, 0.395), (0.275, 0.255))
    arrow(ax, (0.46, 0.205), (0.54, 0.205))
    arrow(ax, (0.50, 0.155), (0.50, 0.11))
    save(fig, "fig06_module2.png")


# ------------------------------------------------------------- Figure 7
def fig7_m3():
    fig, ax = canvas(11.5, 7.4)
    ax.text(0.5, 0.975, "Module 3 — Marketing Analytics and Decision Support",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    box(ax, 0.015, 0.50, 0.145, 0.18,
        "Campaign events\n(M2)\n\n+ segments (M1)\n+ action_log", GREY, GREY_E, 8)

    box(ax, 0.195, 0.800, 0.19, 0.110, "Feature builder\njourney-level matrix", GREY, GREY_E, 8.4)
    box(ax, 0.195, 0.655, 0.19, 0.110, "Funnel & drop-off\nby stage, segment, policy", AMBER, AMBER_E, 8.4)
    box(ax, 0.195, 0.510, 0.19, 0.110, "Attribution engine\nfirst · last · linear · Markov", AMBER, AMBER_E, 8.4)
    box(ax, 0.195, 0.365, 0.19, 0.110, "Uplift engine\nS-learner · T-learner (Qini)", AMBER, AMBER_E, 8.4)
    box(ax, 0.195, 0.220, 0.19, 0.110, "Off-policy evaluation\nIPS · SNIPS · DR", AMBER, AMBER_E, 8.4)

    box(ax, 0.435, 0.745, 0.195, 0.110, "Conversion model\nLogReg / RF / XGBoost", GREEN, GREEN_E, 8.4)
    box(ax, 0.435, 0.600, 0.195, 0.110, "Drop-off risk model\nLogReg / RF / XGBoost", GREEN, GREEN_E, 8.4)
    box(ax, 0.435, 0.425, 0.195, 0.135,
        "Explainability &\nvalidation\nSHAP · calibration ·\nbootstrap CIs", GREEN, GREEN_E, 8)

    box(ax, 0.69, 0.615, 0.19, 0.15,
        "Recommendation\ngenerator\n\nrule engine +\nlearned recommender", ROSE, ROSE_E, 8.5, True)
    box(ax, 0.69, 0.395, 0.19, 0.145,
        "Exploration\n10% of decisions\nrandomised on purpose", TEAL, TEAL_E, 8.5, True)
    box(ax, 0.69, 0.190, 0.19, 0.150,
        "Refusal guard\nno attribution below\n5 converting journeys;\ncalibration warnings",
        GREY, GREY_E, 8, False, ls=(0, (3, 2)))

    box(ax, 0.045, 0.030, 0.40, 0.100,
        "Dashboard: funnel · attribution · predictions\n(every figure badged dataset / live / mixed)",
        BLUE, BLUE_E, 8.4)
    box(ax, 0.53, 0.030, 0.44, 0.100,
        "analytics_output + action_log → Modules 2 and 4\n(campaign optimisation · platform priority)",
        BLUE, BLUE_E, 8.4, True)

    for y in (0.855, 0.710, 0.565, 0.420, 0.275):
        arrow(ax, (0.16, 0.590), (0.195, y), rad=0.10)
    arrow(ax, (0.385, 0.855), (0.435, 0.800))
    arrow(ax, (0.385, 0.815), (0.435, 0.655), rad=-0.15)
    arrow(ax, (0.5325, 0.600), (0.5325, 0.560))
    arrow(ax, (0.63, 0.800), (0.69, 0.720), rad=-0.12)
    arrow(ax, (0.63, 0.655), (0.69, 0.680), rad=0.10)
    arrow(ax, (0.785, 0.615), (0.785, 0.540))
    arrow(ax, (0.785, 0.395), (0.785, 0.340))
    arrow(ax, (0.785, 0.190), (0.785, 0.130))
    arrow(ax, (0.245, 0.655), (0.180, 0.130), rad=0.18)
    arrow(ax, (0.32, 0.510), (0.285, 0.130), rad=0.12)
    save(fig, "fig07_module3.png")


# ------------------------------------------------------------- Figure 8
def fig8_m4():
    fig, ax = canvas(10.5, 6.6)
    ax.text(0.5, 0.965, "Module 4 — AI Content Refinery and Multi-Platform Distribution",
            ha="center", fontsize=12, fontweight="bold", color=INK)

    box(ax, 0.03, 0.745, 0.185, 0.125, "Website crawl\n\nthe store's own copy\n& headings",
        GREY, GREY_E, 8)
    box(ax, 0.25, 0.745, 0.20, 0.125, "Capability detection\n\nwhat this site can\nactually DO",
        TEAL, TEAL_E, 8, True)
    box(ax, 0.485, 0.745, 0.185, 0.125, "Knowledge base\n\nbusiness summary ·\nbrand vocabulary",
        GREY, GREY_E, 8)
    box(ax, 0.705, 0.745, 0.255, 0.125, "Analytics feedback (M3)\n\nplatform priority from\nattribution credit",
        AMBER, AMBER_E, 8)

    box(ax, 0.09, 0.565, 0.38, 0.12, "Goal & tone classifiers\nTF-IDF + LogReg vs SBERT + XGBoost\n"
                                     "(indistinguishable → chosen on cost)",
        PURPLE, PURPLE_E, 8, True)
    box(ax, 0.53, 0.565, 0.38, 0.12, "Action catalogue\nonly the actions this site supports\n"
                                     "(a larger set costs data)",
        TEAL, TEAL_E, 8)

    box(ax, 0.20, 0.405, 0.60, 0.105,
        "Platform-aware generation engine\ncaption · hashtags · CTA · image prompt · short-video brief",
        PURPLE, PURPLE_E, 9, True)

    band(ax, 0.03, 0.135, 0.94, 0.235, "SCORING AND RANKING")
    box(ax, 0.055, 0.180, 0.20, 0.125, "Semantic similarity\nSentence-BERT cosine\n\nweight 0.40",
        GREEN, GREEN_E, 8)
    box(ax, 0.285, 0.180, 0.20, 0.125, "Platform suitability\nrule-based fit check\n\nweight 0.40",
        GREEN, GREEN_E, 8)
    box(ax, 0.515, 0.180, 0.20, 0.125, "Engagement prediction\nno demonstrated skill\n\nweight 0.20",
        ROSE, ROSE_E, 8)
    box(ax, 0.745, 0.180, 0.20, 0.125, "Human baseline\nsame scoring pipeline",
        GREY, GREY_E, 8)

    box(ax, 0.25, 0.020, 0.50, 0.080, "content_assets → ranked, platform-ready assets",
        BLUE, BLUE_E, 8.5, True)

    arrow(ax, (0.215, 0.807), (0.25, 0.807))
    arrow(ax, (0.45, 0.807), (0.485, 0.807))
    arrow(ax, (0.35, 0.745), (0.28, 0.685))
    arrow(ax, (0.83, 0.745), (0.72, 0.685), rad=0.12)
    arrow(ax, (0.28, 0.565), (0.40, 0.510))
    arrow(ax, (0.72, 0.565), (0.60, 0.510))
    arrow(ax, (0.50, 0.405), (0.50, 0.370))
    arrow(ax, (0.50, 0.135), (0.50, 0.100))
    save(fig, "fig08_module4.png")


# ------------------------------------------------------------- Figure 9
def fig9_schema():
    fig, ax = canvas(11.5, 6.6)
    ax.text(0.5, 0.965, "Database Schema (PostgreSQL 16)",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    def tbl(x, y, w, h, name, cols, fc, ec):
        box(ax, x, y, w, h, "", fc, ec)
        ax.text(x + w / 2, y + h - 0.032, name, ha="center", va="center",
                fontsize=8.8, fontweight="bold", color=INK)
        ax.plot([x + 0.012, x + w - 0.012], [y + h - 0.058, y + h - 0.058],
                color=ec, lw=0.9)
        ax.text(x + 0.016, y + h - 0.080, "\n".join(cols), ha="left", va="top",
                fontsize=6.9, color=MUTED, linespacing=1.6)

    tbl(0.030, 0.620, 0.175, 0.280, "users",
        ["id  PK", "email  UNIQUE", "password_hash (scrypt)", "created_at"], ROSE, ROSE_E)
    tbl(0.030, 0.300, 0.175, 0.225, "sessions",
        ["token  PK", "user_id  FK", "expires_at"], ROSE, ROSE_E)
    tbl(0.253, 0.620, 0.175, 0.280, "sites",
        ["id  PK", "owner_id  FK → users", "domain", "write_key",
         "capabilities  JSONB"], GREY, GREY_E)
    tbl(0.253, 0.260, 0.175, 0.265, "visitors",
        ["id  PK", "site_id  FK", "anon_id", "source ('dataset'|'live')",
         "first_seen / last_seen"], GREY, GREY_E)
    tbl(0.476, 0.620, 0.180, 0.280, "user_segments",
        ["id  PK", "visitor_id  FK", "segment_name", "segment_method",
         "segment_confidence"], BLUE, BLUE_E)
    tbl(0.476, 0.235, 0.180, 0.290, "interactions",
        ["id  PK", "visitor_id  FK", "event_type", "channel / platform",
         "campaign_id", "source  (derived)", "occurred_at"], GREEN, GREEN_E)
    tbl(0.704, 0.620, 0.180, 0.280, "analytics_output",
        ["id  PK", "visitor_id  FK", "predicted_conversion",
         "drop_off_risk", "channel_credits", "recommendation"], AMBER, AMBER_E)
    tbl(0.704, 0.235, 0.180, 0.290, "action_log",
        ["id  PK", "visitor_id  FK", "action", "propensity  ← required",
         "is_exploration", "reward", "decided_at"], TEAL, TEAL_E)
    tbl(0.925, 0.420, 0.062, 0.29, "content_\nassets",
        ["id  PK", "site_id", "platform", "caption", "scores"], PURPLE, PURPLE_E)

    arrow(ax, (0.117, 0.620), (0.117, 0.525))
    arrow(ax, (0.205, 0.760), (0.253, 0.760))
    arrow(ax, (0.341, 0.620), (0.341, 0.525))
    arrow(ax, (0.428, 0.380), (0.476, 0.380))
    arrow(ax, (0.428, 0.440), (0.476, 0.700), rad=-0.18)
    arrow(ax, (0.656, 0.380), (0.704, 0.700), rad=-0.18)
    arrow(ax, (0.656, 0.340), (0.704, 0.350))
    arrow(ax, (0.884, 0.560), (0.925, 0.560))

    ax.text(0.5, 0.075,
            "`source` is derived at write time from the visitor the row belongs to and can never be supplied by the "
            "caller;\na test fails the build if a dataset-derived customer produces a row claiming live observation. "
            "`action_log.propensity`\nis mandatory — a decision recorded without the probability it was taken under "
            "cannot be learned from.",
            ha="center", fontsize=7.9, color=MUTED, linespacing=1.6, style="italic")
    save(fig, "fig09_schema.png")


# --------------------------------------------------- screenshot placeholders
SCREENSHOTS = [
    ("shot_store_home", "Demo e-commerce store — home page",
     "The site under study. Product grid, and the mos.js tracking\n"
     "snippet installed in the page head.", "web"),
    ("shot_store_product", "Demo store — product page with tracking status",
     "A single product page. The tracking-status badge confirms events\n"
     "are being collected first-party.", "web"),
    ("shot_login", "Dashboard — sign in and website onboarding",
     "Account creation, website registration and the snippet\n"
     "installation check.", "web"),
    ("shot_dash_overview", "Dashboard — Overview",
     "Audience size, segment mix and funnel headline, each carrying its\n"
     "dataset / live / mixed provenance badge.", "web"),
    ("shot_dash_audience", "Dashboard — Audience",
     "The five segments with sizes, conversion rates and the calibrated\n"
     "confidence produced by the agreement vote.", "web"),
    ("shot_dash_campaigns", "Dashboard — Campaigns",
     "The three policies, their message volume and their measured\n"
     "conversions per 1,000 sends on the imported audience.", "web"),
    ("shot_dash_analytics", "Dashboard — Analytics",
     "Funnel, drop-off by segment and the four attribution models side\n"
     "by side, showing how far apart they are.", "web"),
    ("shot_dash_content", "Dashboard — Content",
     "Generated assets per platform with semantic, platform-fit and\n"
     "engagement component scores.", "web"),
    ("shot_dash_plan", "Dashboard — Action Plan",
     "The system's output: who to contact, with what, on which platform,\n"
     "and why.", "web"),
    ("shot_dash_research", "Dashboard — Research and provenance page",
     "Generated at request time from disk and database: which dataset\n"
     "trained which model, and what each number means.", "web"),
    ("shot_code_vote", "Code — the agreement vote (modules/m1_segmentation/segment.py)",
     "Cold start resolved immediately after unanimity, before the\n"
     "clustering comparison. This ordering is the fix for defect D2.", "code"),
    ("shot_code_importer", "Code — fidelity check (scripts/import_research_audience.py)",
     "Totals asserted against the source CSV after import, so a\n"
     "reconstruction error cannot pass silently.", "code"),
    ("shot_code_features", "Code — the shared feature definition (VISITOR_FEATURES_SQL)",
     "One SQL definition sums imported per-visit counts and live\n"
     "per-page events identically.", "code"),
    ("shot_code_policy", "Code — the Module 2 policy engine",
     "The three policies behind one interface; everything else in the\n"
     "comparison is shared.", "code"),
    ("shot_code_attribution", "Code — the attribution engine (m3_analytics/src/attribution.py)",
     "First-, last-, linear and Markov credit assignment over the same\n"
     "journeys.", "code"),
    ("shot_code_propensity", "Code — logging a decision with its propensity",
     "Every decision records the probability it was taken under, and 10%\n"
     "are randomised on purpose.", "code"),
    ("shot_code_goal_tone", "Code — model selection in goal_tone.py",
     "TF-IDF and Sentence-BERT trained on the same split; the better\n"
     "model per target is selected, not assumed.", "code"),
    ("shot_code_experiment", "Code — an experiment (research/experiments/e1_segmentation_ablation.py)",
     "Each experiment writes its own tables; nothing is copied by hand\n"
     "into the report.", "code"),
    ("shot_make_research", "Terminal — `make research` completing all eleven experiments",
     "The reproduction path: one command regenerates every table, figure\n"
     "and chapter in this report.", "code"),
    ("shot_make_test", "Terminal — `make test`, 260 tests passing",
     "Including the regression tests for each defect and the provenance\n"
     "guard.", "code"),
]


def placeholder(name, title, hint, kind):
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fc, ec = ("#f8fafc", "#94a3b8") if kind == "web" else ("#f5f3ff", "#8b5cf6")
    ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                boxstyle="round,pad=0.005,rounding_size=0.02",
                                facecolor=fc, edgecolor=ec, linewidth=2.0,
                                linestyle=(0, (7, 5))))
    badge = "SCREENSHOT — USER INTERFACE" if kind == "web" else "SCREENSHOT — SOURCE CODE"
    ax.text(0.5, 0.775, badge, ha="center", fontsize=11.5, fontweight="bold",
            color=ec)
    ax.text(0.5, 0.585, title, ha="center", fontsize=14, fontweight="bold",
            color=INK)
    ax.text(0.5, 0.385, hint, ha="center", fontsize=10.5, color=MUTED,
            linespacing=1.8)
    ax.text(0.5, 0.140,
            f"Replace  report/assets/placeholders/{name}.png  with the real capture, then rebuild.",
            ha="center", fontsize=9, color="#94a3b8", style="italic")
    save(fig, f"{name}.png", SHOTS)


if __name__ == "__main__":
    fig1_loop()
    fig2_architecture()
    fig3_research_pipeline()
    fig4_importer()
    fig5_m1()
    fig6_m2()
    fig7_m3()
    fig8_m4()
    fig9_schema()
    for name, title, hint, kind in SCREENSHOTS:
        placeholder(name, title, hint, kind)
    print(f"\ndiagrams -> {OUT}\nplaceholders -> {SHOTS}")
