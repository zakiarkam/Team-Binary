# 🧭 AI-Powered Digital Marketing Orchestration

**Team Binary · University of Moratuwa · Level 4 FYP · 2026**

An integrated, **closed-loop** marketing system for launch-stage products with
limited data. Four research modules run as one pipeline behind one app:

```
  ①  Audience Segmentation      →  ②  Campaign Automation
  (hybrid rule + ML, 8k users)      (fixed / trigger / hybrid strategies)
              ▲                                    │
              │                              event logs
        content priorities                        ▼
              │                     ③  Analytics & Decision Support
  ④  AI Content Refinery   ◀────────  (funnel · attribution · prediction ·
     (goal/tone → posts →              recommendations)
      scored & ranked)      ◀──── analytics feedback closes the loop
```

---

## Quick start

```bash
# 1. activate the environment
source venv/bin/activate            # Python 3.11

# 2a. run the whole closed loop from the command line (~10s)
python orchestrator.py --full --engine fast

# 2b. or launch the app and drive it from the browser
streamlit run app_unified/Home.py
```

Open **🚀 Run Campaign**, enter a product (name, website, audience, platforms),
and the system segments the audience, picks the best automation strategy,
analyses the funnel, and generates **platform-native, scored posts** you can
preview, export, and schedule.

> This is a research prototype: it runs on public / simulated data and
> **previews** content — it never auto-posts to live platforms.

---

## What each module does

| # | Module | Lives in | Produces |
|---|--------|----------|----------|
| ① | **Segmentation** | `modules/m1_segmentation/` | `user_segments.csv` — 8,000 users in 5 segments (hybrid rule + RandomForest) |
| ② | **Automation** | `modules/m2_automation/` | strategy comparison + campaign event logs (fixed / trigger / hybrid) |
| ③ | **Analytics** | `modules/m3_analytics/` | funnel, 4 attribution models, conversion / drop-off predictions, recommendations |
| ④ | **Content** | repo root (`content_service.py`, `generator.py`, `engagement.py`, …) | goal/tone-aware, platform-native posts scored `0.30·semantic + 0.25·platform-fit + 0.45·engagement` |

The **`unified` git branch** merges all four. See **[INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)**
for the exact data contracts between modules and the design decisions.

---

## The integration layer (what was built to unify them)

```
orchestrator.py        # runs M1 → M2 → M3 → (feedback) → M4, writes data/integrated/run_bundle.json
content_service.py     # M4 content: fast (template) + phi3 engines, both model-scored
model_health.py        # honest cross-validated metrics for every model
adapters/
  segment_labels.py    # Title-Case (M1/M2) ↔ snake_case (M3) segment names
  m2_to_m3.py          # M2 wide event logs → M3 long event logs + funnel
  m3_to_m4.py          # M3 analytics → M4 content platform priorities
app_unified/           # the Streamlit app (Home + Run Campaign + Research dashboards)
```

---

## Honest model health

A research project reports its weaknesses. Run `python model_health.py`; the
findings also appear on the app's **Research → Model health** tab.

| Model | Headline | Honest number |
|---|---|---|
| M4 tone classifier | 1.0 accuracy (24-row test) | **CV weighted-F1 0.90 ± 0.07** — low-data, not perfect |
| M4 goal classifier | 0.75 single-split | **CV weighted-F1 0.76 ± 0.09** |
| M4 engagement regressor | R² 0.99 | optimistic on synthetic data — use as a **ranker** |
| M3 conversion / drop-off | AUC ≈ 1.0 (simulated) | **real-data AUC 0.95** (leakage in sim) |
| M2 conversion | ~base-rate accuracy | honest; read via ROC/PR-AUC |

---

## Documentation

- **[INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)** — architecture, data contracts, phases, model-health plan
- **[docs/](docs/)** — per-module deep dives: methodology, content-engine reasoning, engagement-learning loop, research analysis
- Module notes: `modules/m2_automation/MODULE2_README.md`, `modules/m3_analytics/README.md`

---

## Repo layout

```
Research/                        (branch: unified)
├── orchestrator.py              # closed-loop runner
├── content_service.py           # M4 content service (app-facing)
├── model_health.py              # honest metrics report
├── adapters/                    # cross-module schema bridges
├── app_unified/                 # Streamlit app  (Home.py + pages/)
├── modules/
│   ├── m1_segmentation/         # Module 1
│   ├── m2_automation/           # Module 2
│   └── m3_analytics/            # Module 3
├── config.py, generator.py, engagement.py, evaluation.py, goal_tone.py, …  # Module 4
├── models/  outputs/  data/     # trained models, artifacts, datasets
├── docs/                        # deep-dive documentation
└── INTEGRATION_PLAN.md, README.md
```
