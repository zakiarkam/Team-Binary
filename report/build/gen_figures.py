"""Generate architecture / flow diagrams for the Team Binary final report."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = "/Users/arkamzakir/Documents/Research/Research/report/assets"
os.makedirs(OUT, exist_ok=True)

INK = "#1f2933"
MUTED = "#5b6b7a"
BLUE = "#dbeafe"
BLUE_E = "#2563eb"
GREEN = "#dcfce7"
GREEN_E = "#16a34a"
AMBER = "#fef3c7"
AMBER_E = "#d97706"
PURPLE = "#ede9fe"
PURPLE_E = "#7c3aed"
GREY = "#f1f5f9"
GREY_E = "#64748b"
ROSE = "#ffe4e6"
ROSE_E = "#e11d48"

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


def save(fig, name):
    fig.savefig(f"{OUT}/{name}", dpi=220, bbox_inches="tight",
                facecolor="white", pad_inches=0.12)
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- Figure 1
def fig1_loop():
    fig, ax = canvas(11, 6.0)
    ax.text(0.5, 0.965, "Closed-Loop Marketing Orchestration",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    box(ax, 0.03, 0.60, 0.20, 0.15,
        "Client website\n+ mos.js snippet\n(first-party visitors)",
        GREY, GREY_E, 8.5)
    box(ax, 0.29, 0.60, 0.19, 0.15,
        "Module 1\nAudience Targeting\n& Personalization", BLUE, BLUE_E, 9, True)
    box(ax, 0.545, 0.60, 0.19, 0.15,
        "Module 2\nMarketing Automation\n& Campaign Mgmt", GREEN, GREEN_E, 9, True)
    box(ax, 0.795, 0.60, 0.175, 0.15,
        "Campaign\nexecution\n(email / social)", GREY, GREY_E, 8.5)

    box(ax, 0.545, 0.26, 0.19, 0.15,
        "Module 3\nAnalytics &\nDecision Support", AMBER, AMBER_E, 9, True)
    box(ax, 0.29, 0.26, 0.19, 0.15,
        "Module 4\nAI Content Refinery\n& Distribution", PURPLE, PURPLE_E, 9, True)
    box(ax, 0.795, 0.26, 0.175, 0.15,
        "Interaction\nevent log\n(sent/open/click/\nconvert)", GREY, GREY_E, 8.5)

    box(ax, 0.03, 0.26, 0.20, 0.15,
        "Action Plan\n(who · what · why)\ndelivered to marketer",
        ROSE, ROSE_E, 8.5, True)

    arrow(ax, (0.23, 0.675), (0.29, 0.675), "visitors")
    arrow(ax, (0.48, 0.675), (0.545, 0.675), "segments")
    arrow(ax, (0.735, 0.675), (0.795, 0.675), "workflows")
    arrow(ax, (0.8825, 0.60), (0.8825, 0.41), "events")
    arrow(ax, (0.795, 0.335), (0.735, 0.335), "logs")
    arrow(ax, (0.545, 0.335), (0.48, 0.335), "analytics\nfeedback")
    arrow(ax, (0.29, 0.335), (0.23, 0.335), "assets")

    arrow(ax, (0.13, 0.41), (0.13, 0.60), "re-targeting", BLUE_E, rad=0.0)
    arrow(ax, (0.64, 0.41), (0.64, 0.60), "predicted\nconversion", AMBER_E,
          rad=-0.45, toff=(0.075, 0))

    ax.text(0.5, 0.135,
            "The loop is closed: analytics output re-enters segmentation, "
            "automation and content generation,\nso every campaign cycle is "
            "informed by the measured outcome of the previous one.",
            ha="center", fontsize=8.5, color=MUTED, linespacing=1.5)
    save(fig, "fig01_closed_loop.png")


# ---------------------------------------------------------------- Figure 2
def fig2_architecture():
    fig, ax = canvas(11, 7.4)
    ax.text(0.5, 0.975, "High-Level System Architecture",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    band(ax, 0.02, 0.765, 0.96, 0.165, "PRESENTATION LAYER")
    box(ax, 0.05, 0.80, 0.20, 0.085, "Marketer dashboard\nNext.js 16 + Recharts",
        BLUE, BLUE_E, 8.5, True)
    box(ax, 0.285, 0.80, 0.185, 0.085, "Auth pages\nlogin · signup ·\nonboarding",
        BLUE, BLUE_E, 8)
    box(ax, 0.505, 0.80, 0.20, 0.085, "Client website\n(tenant) with mos.js",
        GREY, GREY_E, 8.5)
    box(ax, 0.74, 0.80, 0.21, 0.085, "Website visitor\n(first-party, DNT honoured)",
        GREY, GREY_E, 8)

    band(ax, 0.02, 0.555, 0.96, 0.195, "APPLICATION LAYER — FastAPI")
    box(ax, 0.05, 0.60, 0.155, 0.10,
        "Routers\n/sites /segments\n/campaigns /analytics\n/content /actions", GREEN, GREEN_E, 7.5)
    box(ax, 0.235, 0.60, 0.155, 0.10,
        "Public tracking\n/collect · /mos.js\n/track/* · /l/*", GREEN, GREEN_E, 7.5)
    box(ax, 0.42, 0.60, 0.155, 0.10,
        "Ownership\nmiddleware\n(multi-tenant isolation)", ROSE, ROSE_E, 7.5, True)
    box(ax, 0.605, 0.60, 0.155, 0.10,
        "Auth service\nscrypt · DB-row\nsessions", GREEN, GREEN_E, 7.5)
    box(ax, 0.79, 0.60, 0.16, 0.10,
        "Provenance &\nresearch service\n(real / simulated)", GREEN, GREEN_E, 7.5)

    band(ax, 0.02, 0.280, 0.96, 0.255, "RESEARCH MODULE LAYER — Python / scikit-learn / XGBoost")
    box(ax, 0.040, 0.325, 0.20, 0.155,
        "Module 1\nHybrid Segmentation\n\nrules + K-Means +\nhierarchical → agreement\nvote + confidence",
        BLUE, BLUE_E, 8)
    box(ax, 0.283, 0.325, 0.20, 0.155,
        "Module 2\nCampaign Automation\n\nfixed · trigger · hybrid\nstrategy engine +\nresponse model",
        GREEN, GREEN_E, 8)
    box(ax, 0.526, 0.325, 0.20, 0.155,
        "Module 3\nAnalytics & Decision\nSupport\n\nfunnel · attribution ·\nprediction · recommender",
        AMBER, AMBER_E, 8)
    box(ax, 0.769, 0.325, 0.20, 0.155,
        "Module 4\nAI Content Refinery\n\ncrawler · goal/tone ·\ngeneration · scoring ·\nplatform routing",
        PURPLE, PURPLE_E, 8)

    band(ax, 0.02, 0.045, 0.96, 0.205, "DATA LAYER — PostgreSQL 16 (Docker)")
    for i, (nm, sub) in enumerate([
            ("visitors / sites", "is_synthetic derived"),
            ("user_segments", "segment + confidence"),
            ("interactions", "is_real derived"),
            ("analytics_output", "funnel · attribution"),
            ("content_assets", "scored assets")]):
        box(ax, 0.045 + i * 0.187, 0.085, 0.168, 0.10, f"{nm}\n\n{sub}",
            GREY, GREY_E, 7.8)

    arrow(ax, (0.15, 0.80), (0.15, 0.70), "HTTPS / JSON")
    arrow(ax, (0.60, 0.80), (0.31, 0.70), "beacon", rad=-0.15)
    arrow(ax, (0.845, 0.795), (0.71, 0.795), "browses", rad=0.0)
    arrow(ax, (0.35, 0.60), (0.35, 0.48), "invoke")
    arrow(ax, (0.62, 0.60), (0.62, 0.48))
    arrow(ax, (0.50, 0.325), (0.50, 0.255), "read / write", toff=(0.055, 0))
    save(fig, "fig02_architecture.png")


# ---------------------------------------------------------------- Figure 3
def fig3_m1():
    fig, ax = canvas(10.5, 6.2)
    ax.text(0.5, 0.965, "Module 1 — Audience Targeting and Personalization",
            ha="center", fontsize=12, fontweight="bold", color=INK)

    box(ax, 0.03, 0.70, 0.18, 0.13, "Behavioural data\n\nweb visitors  ·  8,000-user\nresearch dataset",
        GREY, GREY_E, 8)
    box(ax, 0.255, 0.70, 0.18, 0.13, "Preprocessing\n\nmissing values ·\nencoding · scaling",
        GREY, GREY_E, 8)
    box(ax, 0.485, 0.70, 0.18, 0.13, "Feature engineering\n\nengagement score ·\nclick ratio · recency",
        GREY, GREY_E, 8)

    band(ax, 0.20, 0.325, 0.60, 0.28, "THREE SEGMENTATION METHODS RUN IN PARALLEL")
    box(ax, 0.225, 0.40, 0.17, 0.14, "Rule-based\nsegmentation\n\ninterpretable ·\ncold-start safe",
        BLUE, BLUE_E, 8)
    box(ax, 0.415, 0.40, 0.17, 0.14, "K-Means\nclustering\n\nk = 4  ·  scaled\nfeatures", BLUE, BLUE_E, 8)
    box(ax, 0.605, 0.40, 0.17, 0.14, "Hierarchical\nclustering\n\nWard linkage",
        BLUE, BLUE_E, 8)

    box(ax, 0.325, 0.175, 0.35, 0.10,
        "Agreement vote  →  hybrid segment + confidence\n"
        "cold-start rule takes precedence over clustering", AMBER, AMBER_E, 8.5, True)

    box(ax, 0.05, 0.03, 0.40, 0.095,
        "Five shared segments\nHigh Intent · Loyal Customer · Price Sensitive ·\n"
        "Low Engagement · New Cold User", GREEN, GREEN_E, 8)
    box(ax, 0.55, 0.03, 0.40, 0.095,
        "user_segments table  →  Modules 2 and 3\n"
        "< 30 visitors: engine declines to cluster and says why",
        GREEN, GREEN_E, 8)

    arrow(ax, (0.21, 0.765), (0.255, 0.765))
    arrow(ax, (0.435, 0.765), (0.485, 0.765))
    arrow(ax, (0.575, 0.70), (0.50, 0.605))
    for x in (0.31, 0.50, 0.69):
        arrow(ax, (x, 0.40), (x if x == 0.50 else 0.50, 0.275), rad=0.0)
    arrow(ax, (0.42, 0.175), (0.28, 0.125))
    arrow(ax, (0.58, 0.175), (0.72, 0.125))
    save(fig, "fig03_module1.png")


# ---------------------------------------------------------------- Figure 4
def fig4_m2():
    fig, ax = canvas(10.5, 6.0)
    ax.text(0.5, 0.965, "Module 2 — Marketing Automation and Campaign Management",
            ha="center", fontsize=12, fontweight="bold", color=INK)

    box(ax, 0.035, 0.68, 0.19, 0.14, "Inputs\n\nsegment labels (M1) ·\nuser behaviour profile",
        GREY, GREY_E, 8)
    box(ax, 0.275, 0.68, 0.19, 0.14, "Response model\n\nLogReg / RandomForest\nvs Dummy baseline",
        GREEN, GREEN_E, 8)
    box(ax, 0.515, 0.68, 0.19, 0.14, "Campaign policy\nengine\n\nselects next action",
        GREEN, GREEN_E, 8.5, True)
    box(ax, 0.755, 0.68, 0.20, 0.14, "Message templates\n\nwelcome · info ·\nsocial proof · offer",
        GREY, GREY_E, 8)

    band(ax, 0.10, 0.34, 0.80, 0.24, "THREE AUTOMATION STRATEGIES COMPARED UNDER IDENTICAL CONDITIONS")
    box(ax, 0.135, 0.395, 0.22, 0.12, "Fixed workflow\n\nsame sequence for\nevery user (baseline)",
        BLUE, BLUE_E, 8)
    box(ax, 0.39, 0.395, 0.22, 0.12, "Trigger-based\n\nnext action follows\nlast observed event",
        BLUE, BLUE_E, 8)
    box(ax, 0.645, 0.395, 0.22, 0.12, "Hybrid\n\nschedule + triggers +\nsegments + prediction",
        AMBER, AMBER_E, 8, True)

    box(ax, 0.10, 0.155, 0.36, 0.10, "Event simulation layer\nsent · open · click · ignore · convert",
        GREY, GREY_E, 8)
    box(ax, 0.54, 0.155, 0.36, 0.10, "Evaluation layer\nopen rate · CTR · conversion ·\ntime-to-convert · complexity",
        GREY, GREY_E, 8)
    box(ax, 0.28, 0.02, 0.44, 0.085, "interactions table  →  Module 3 analytics",
        GREEN, GREEN_E, 8.5, True)

    arrow(ax, (0.225, 0.75), (0.275, 0.75))
    arrow(ax, (0.465, 0.75), (0.515, 0.75))
    arrow(ax, (0.755, 0.75), (0.705, 0.75), style="<|-")
    arrow(ax, (0.61, 0.68), (0.50, 0.58))
    arrow(ax, (0.28, 0.395), (0.28, 0.255))
    arrow(ax, (0.46, 0.205), (0.54, 0.205))
    arrow(ax, (0.50, 0.155), (0.50, 0.105))
    save(fig, "fig04_module2.png")


# ---------------------------------------------------------------- Figure 5
def fig5_m3():
    fig, ax = canvas(11.5, 7.0)
    ax.text(0.5, 0.975, "Module 3 — Marketing Analytics and Decision Support",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    box(ax, 0.015, 0.50, 0.15, 0.17,
        "Campaign event\nlogs (M2)\n\n+ segment labels\n(M1)", GREY, GREY_E, 8)

    box(ax, 0.205, 0.775, 0.195, 0.125,
        "Feature builder\njourney-level\nfeature matrix", GREY, GREY_E, 8.5)
    box(ax, 0.205, 0.605, 0.195, 0.125,
        "Funnel construction\nsent → open →\nclick → convert", AMBER, AMBER_E, 8.5)
    box(ax, 0.205, 0.435, 0.195, 0.125,
        "Drop-off analysis\nby stage, segment\nand strategy", AMBER, AMBER_E, 8.5)
    box(ax, 0.205, 0.265, 0.195, 0.125,
        "Attribution engine\nfirst · last · linear ·\nmulti-touch · Markov", AMBER, AMBER_E, 8.5)

    box(ax, 0.455, 0.760, 0.20, 0.125,
        "Conversion model\nLogReg / RF / XGBoost\n+ 5-fold CV", GREEN, GREEN_E, 8.5)
    box(ax, 0.455, 0.585, 0.20, 0.125,
        "Drop-off risk model\nLogReg / RF / XGBoost\n+ 5-fold CV", GREEN, GREEN_E, 8.5)
    box(ax, 0.455, 0.395, 0.20, 0.140,
        "Explainability & validation\nSHAP · calibration ·\nbootstrap CIs\n(applied to both models)",
        GREEN, GREEN_E, 8)

    box(ax, 0.715, 0.615, 0.20, 0.155,
        "Recommendation\ngenerator\n\nrule engine +\nlearned recommender", ROSE, ROSE_E, 8.5, True)
    box(ax, 0.715, 0.370, 0.20, 0.150,
        "Refusal guard\n\nno attribution below\n5 converting journeys;\ncalibration warnings",
        GREY, GREY_E, 8, False, ls=(0, (3, 2)))

    box(ax, 0.055, 0.045, 0.40, 0.115,
        "Dashboard: funnel · attribution ·\npredictions · insights\n"
        "(every figure badged real / simulated / mixed)", BLUE, BLUE_E, 8.5)
    box(ax, 0.545, 0.045, 0.42, 0.115,
        "analytics_output  →  Module 2 (campaign optimisation)\n"
        "and Module 4 (platform priority for content)", BLUE, BLUE_E, 8.5, True)

    for y in (0.8375, 0.6675, 0.4975, 0.3275):
        arrow(ax, (0.165, 0.585), (0.205, y), rad=0.10)

    arrow(ax, (0.40, 0.8375), (0.455, 0.8225))
    arrow(ax, (0.40, 0.8100), (0.455, 0.6475), rad=-0.15)
    arrow(ax, (0.555, 0.585), (0.555, 0.535), color=GREY_E)
    arrow(ax, (0.655, 0.8225), (0.715, 0.720), rad=-0.12)
    arrow(ax, (0.655, 0.6475), (0.715, 0.680), rad=0.12)
    arrow(ax, (0.815, 0.615), (0.815, 0.520))
    arrow(ax, (0.815, 0.370), (0.815, 0.160))

    arrow(ax, (0.2600, 0.605), (0.190, 0.160), rad=0.18)
    arrow(ax, (0.3400, 0.435), (0.300, 0.160), rad=0.12)
    arrow(ax, (0.40, 0.3275), (0.545, 0.135), rad=-0.18)
    save(fig, "fig05_module3.png")


# ---------------------------------------------------------------- Figure 6
def fig6_m4():
    fig, ax = canvas(10.5, 6.2)
    ax.text(0.5, 0.965, "Module 4 — AI Content Refinery and Multi-Platform Distribution",
            ha="center", fontsize=12, fontweight="bold", color=INK)

    box(ax, 0.03, 0.70, 0.185, 0.135, "Content inputs\n\nclient website crawl ·\nproduct copy · headings",
        GREY, GREY_E, 8)
    box(ax, 0.255, 0.70, 0.185, 0.135, "Knowledge base\n\nbusiness summary ·\nbrand vocabulary",
        GREY, GREY_E, 8)
    box(ax, 0.48, 0.70, 0.20, 0.135, "Goal & tone classifiers\n\nTF-IDF + LogReg vs\nSBERT + XGBoost",
        PURPLE, PURPLE_E, 8, True)
    box(ax, 0.72, 0.70, 0.235, 0.135, "Analytics feedback (M3)\n\nplatform priority from\nattribution credit",
        AMBER, AMBER_E, 8)

    box(ax, 0.20, 0.44, 0.60, 0.12,
        "Platform-aware generation engine\n"
        "caption · hashtags · CTA · image prompt · short-video brief",
        PURPLE, PURPLE_E, 9, True)

    band(ax, 0.03, 0.155, 0.94, 0.24, "SCORING AND RANKING")
    box(ax, 0.055, 0.20, 0.20, 0.125, "Semantic similarity\nSentence-BERT cosine\n\nweight 0.40",
        GREEN, GREEN_E, 8)
    box(ax, 0.285, 0.20, 0.20, 0.125, "Platform suitability\nrule-based fit check\n\nweight 0.40",
        GREEN, GREEN_E, 8)
    box(ax, 0.515, 0.20, 0.20, 0.125, "Engagement prediction\nXGBoost regressor\n\nweight 0.20 (low skill)",
        ROSE, ROSE_E, 8)
    box(ax, 0.745, 0.20, 0.20, 0.125, "Human baseline\ncomparison harness\n\nsame scoring pipeline",
        GREY, GREY_E, 8)

    box(ax, 0.25, 0.025, 0.50, 0.085,
        "content_assets table  →  ranked, platform-ready marketing assets",
        BLUE, BLUE_E, 8.5, True)

    arrow(ax, (0.215, 0.765), (0.255, 0.765))
    arrow(ax, (0.44, 0.765), (0.48, 0.765))
    arrow(ax, (0.58, 0.70), (0.52, 0.56))
    arrow(ax, (0.83, 0.70), (0.66, 0.56), rad=0.12)
    arrow(ax, (0.50, 0.44), (0.50, 0.395))
    arrow(ax, (0.50, 0.155), (0.50, 0.11))
    save(fig, "fig06_module4.png")


# ---------------------------------------------------------------- Figure 7
def fig7_schema():
    fig, ax = canvas(11, 6.2)
    ax.text(0.5, 0.965, "Database Schema (PostgreSQL)",
            ha="center", fontsize=12.5, fontweight="bold", color=INK)

    def tbl(x, y, w, h, name, cols, fc, ec):
        box(ax, x, y, w, h, "", fc, ec)
        ax.text(x + w / 2, y + h - 0.035, name, ha="center", va="center",
                fontsize=9, fontweight="bold", color=INK)
        ax.plot([x + 0.012, x + w - 0.012], [y + h - 0.062, y + h - 0.062],
                color=ec, lw=0.9)
        ax.text(x + 0.018, y + h - 0.082, "\n".join(cols), ha="left", va="top",
                fontsize=7.2, color=MUTED, linespacing=1.6)

    tbl(0.035, 0.60, 0.20, 0.30, "users",
        ["id  PK", "email  UNIQUE", "password_hash (scrypt)", "created_at"],
        ROSE, ROSE_E)
    tbl(0.035, 0.25, 0.20, 0.25, "sessions",
        ["token  PK", "user_id  FK", "expires_at"], ROSE, ROSE_E)
    tbl(0.285, 0.60, 0.20, 0.30, "sites",
        ["id  PK", "owner_id  FK → users", "domain", "write_key", "created_at"],
        GREY, GREY_E)
    tbl(0.285, 0.22, 0.20, 0.28, "visitors",
        ["id  PK", "site_id  FK", "anon_id", "is_synthetic (derived)",
         "first_seen / last_seen"], GREY, GREY_E)
    tbl(0.535, 0.60, 0.205, 0.30, "user_segments",
        ["id  PK", "site_id / visitor_id  FK", "segment_name",
         "segment_method", "segment_confidence"], BLUE, BLUE_E)
    tbl(0.535, 0.19, 0.205, 0.31, "interactions",
        ["id  PK", "visitor_id  FK", "event_type", "channel / platform",
         "campaign_id", "is_real (derived)", "occurred_at"], GREEN, GREEN_E)
    tbl(0.79, 0.60, 0.185, 0.30, "analytics_output",
        ["id  PK", "visitor_id  FK", "predicted_conversion",
         "drop_off_risk", "channel_credits", "recommendation"], AMBER, AMBER_E)
    tbl(0.79, 0.22, 0.185, 0.28, "content_assets",
        ["id  PK", "site_id  FK", "platform", "caption / hashtags / cta",
         "semantic · fit · score"], PURPLE, PURPLE_E)

    arrow(ax, (0.135, 0.60), (0.135, 0.50))
    arrow(ax, (0.235, 0.75), (0.285, 0.75))
    arrow(ax, (0.385, 0.60), (0.385, 0.50))
    arrow(ax, (0.485, 0.36), (0.535, 0.36))
    arrow(ax, (0.485, 0.42), (0.535, 0.70), rad=-0.2)
    arrow(ax, (0.74, 0.35), (0.79, 0.70), rad=-0.2)
    arrow(ax, (0.74, 0.30), (0.79, 0.34))
    ax.text(0.5, 0.055,
            "is_synthetic and is_real are derived at write time, never asserted by the caller, "
            "so demonstration traffic\ncan never be reported as measured behaviour. "
            "A regression test fails the build if it ever is.",
            ha="center", fontsize=8, color=MUTED, linespacing=1.5, style="italic")
    save(fig, "fig07_schema.png")


if __name__ == "__main__":
    fig1_loop()
    fig2_architecture()
    fig3_m1()
    fig4_m2()
    fig5_m3()
    fig6_m4()
    fig7_schema()
    print("done ->", OUT)
