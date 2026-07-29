# Module 3 — Marketing Analytics & Decision Support

Team Binary · AI-Powered Digital Marketing Orchestration · University of Moratuwa (Level 4 FYP)

This module is the **intelligence layer** of the orchestration framework. It consumes
campaign event logs (from Module 2) and turns them into funnels, attribution credit,
conversion / drop-off predictions, and **per-user recommendations** — the closed-loop
signal that feeds Module 4 (content).

---

## 1. What this module does

| Capability | Where | Output |
|---|---|---|
| **Funnel & drop-off analysis** | `src/funnel.py` | stage counts + drop-off rates, sliced by strategy / segment / channel |
| **Attribution (4 models)** | `src/attribution.py` | first-touch, last-touch, linear multi-touch, **Markov removal-effect**; MAE vs ground truth |
| **Conversion & drop-off prediction** | `src/prediction.py` | 3 classifiers (LogReg / RandomForest / XGBoost) × 2 targets, 5-fold CV + holdout |
| **Per-user decision support** | `src/recommender.py` | `analytics_output.json` — one record per user |
| **Learned recommender** | `src/learned_recommender.py` | XGBoost alternative to the hand-tuned rules |
| **Model explainability** | `src/shap_analysis.py` | SHAP feature importance per target |
| **Statistical rigour** | `src/bootstrap.py` | 95% bootstrap CIs + p-values for strategy lift & attribution MAE |
| **Real-data calibration** | `src/calibration.py` | simulator base rates fitted from UCI Bank-Marketing |
| **Dashboard** | `dashboard/app.py` | Streamlit: Funnel · Attribution · Per-user Predict · What-If |

---

## 2. Quick start — run ONLY Module 3

```bash
cd modules/m3_analytics

# Full run: install deps → simulate/train → tests
bash run_person3.sh

# If dependencies are already installed (e.g. the repo venv):
bash run_person3.sh --no-install

# Also open the dashboard afterwards:
bash run_person3.sh --no-install --dashboard
```

The script runs `python -m src.pipeline --full`, which executes every stage below and
**regenerates `outputs/models/*.pkl`** (trained models are intentionally *not* committed —
see [.gitignore](.gitignore)). A full run takes ~50 s on 10,000 users.

Manual equivalent:

```bash
python -m src.pipeline --full          # simulate → features → train → eval → recommend → bootstrap → SHAP
python -m pytest tests/ -q             # 36 tests (1 skips if bank-marketing data absent)
python -m streamlit run dashboard/app.py
```

---

## 3. Pipeline stages (`src/pipeline.py --full`)

1. **Simulate** — 10,000 users, 5 segments, 3 strategies, 5 platforms (`src/simulator.py`).
2. **Features** — one row per user (`src/features.py`). *Features are built from
   **pre-conversion events only** — see §6.*
3. **Train** — 3 classifiers × 2 targets, saved to `outputs/models/`.
4. **Evaluation studies** — attribution vs ground truth, ROC / confusion matrices, strategy comparison.
5. **Recommendations** — per-user `analytics_output.json` + system-level `insights.md`.
6. **Bootstrap** — 95% CIs for strategy lift and attribution MAE.
7. **Learned recommender** — XGBoost trained on a weakly-supervised proxy label.
8. **SHAP** — feature importance for the XGBoost models.

---

## 4. Key results (10,000-user simulation)

### Prediction (test-set AUC — honest, post-de-leak)
| Target | LogReg | RandomForest | XGBoost |
|---|---|---|---|
| Conversion | 0.968 | 0.971 | **0.976** |
| Drop-off   | 0.930 | 0.987 | **0.990** |

Validated against real **UCI Bank-Marketing** data (XGBoost AUC ≈ 0.95), so the simulated
scores are realistic, not inflated.

### Attribution (MAE vs ground-truth influence, lower = better)
| First-touch | Last-touch | Multi-touch | Markov |
|---|---|---|---|
| 0.0178 | 0.0260 | **0.0178** | 0.0525 |

Multi-touch and first-touch recover the true platform influence best; last-touch and
Markov are worse on these short cold-start journeys.

### Strategy comparison (bootstrap, 500 replicates)
| Strategy | Conversion rate | 95% CI |
|---|---|---|
| fixed | 10.1% | [9.1%, 11.1%] |
| trigger | 11.7% | [10.6%, 12.8%] |
| hybrid | **12.7%** | [11.6%, 13.9%] |

Lift vs fixed: **hybrid +26.2%** (p < 0.001), **trigger +16.4%** (p = 0.012).

### Learned vs rule-based recommender
Learned XGBoost recommender: **94.4%** accuracy on the proxy label; **82%** agreement with
the interpretable rule engine.

---

## 5. Per-user output schema (`outputs/reports/analytics_output.json`)

One record per user (10,000 total):

```json
{
  "user_id": "U00000",
  "modality": "analytics",
  "predicted_conversion": 0.20,
  "drop_off_risk": 0.71,
  "attribution_model": "multi_touch",
  "channel_credits":  {"email": 0.2, "social": 0.6, "ad": 0.2},
  "platform_credits": {"instagram": 0.4, "email": 0.2, "...": 0.0},
  "best_platform": "instagram",
  "recommendation": "send_general_reminder",
  "recommended_platform": "instagram",
  "confidence": 0.85
}
```

Recommendation mix on the current run: general-reminder 71.3%, premium-offer 13.9%,
personalized-offer 12.2%, reactivation 2.7%.

---

## 6. Research note — label-leakage fix (important)

Conversion is defined by a user's `convert` event. Earlier, the feature table counted the
`convert` event inside `journey_length` and the timing features, so the **target leaked into
the features** and the classifiers scored a fake **AUC ≈ 1.0**.

The fix (in `src/features.py`): **all features are computed from pre-conversion events
only** — the `convert` row (and any later touches) are dropped before aggregation, while the
`open`/`click` counts that legitimately precede the decision are kept. After the fix,
conversion AUC is an honest **≈ 0.96–0.98**, and SHAP shows `n_clicks` (a real funnel signal)
as the top driver instead of the leaky `journey_length`.

---

## 7. Directory layout

```
modules/m3_analytics/
├── run_person3.sh              # one-command run of THIS module only
├── src/
│   ├── simulator.py            # generates the 3 input CSVs (+ ground truth)
│   ├── features.py             # per-user feature table (pre-conversion only)
│   ├── prediction.py           # train/evaluate 3 classifiers × 2 targets
│   ├── attribution.py          # first / last / multi-touch / Markov
│   ├── funnel.py               # funnel counts, drop-offs, plots
│   ├── recommender.py          # per-user analytics_output.json + insights
│   ├── learned_recommender.py  # XGBoost recommender
│   ├── evaluation.py           # 3 comparison studies + figures
│   ├── bootstrap.py            # 95% CIs
│   ├── shap_analysis.py        # SHAP importance
│   ├── calibration.py          # base rates from UCI Bank-Marketing
│   └── pipeline.py             # orchestrates all of the above
├── dashboard/app.py            # Streamlit dashboard
├── notebooks/                  # 01 funnel · 02 attribution · 03 prediction · 04 final
├── data/simulated/             # event_logs, user_segments, ground_truth (committed)
├── data/processed/features.csv # regenerated by the pipeline
├── outputs/reports/            # metrics, analytics_output.json, insights, CIs
├── outputs/figures/            # all evaluation charts
├── outputs/models/             # trained .pkl — regenerated, NOT committed
└── tests/test_smoke.py         # 37 tests
```

---

## 8. Limitations (honest)

- **Simulated data.** The study targets a cold-start / low-data launch scenario, so a
  controlled simulator is used. Base rates are calibrated to real UCI Bank-Marketing data,
  and models are cross-checked against it, but this is not a live campaign.
- **Attribution study is multi-platform by design.** Module 2's real campaign is
  single-platform (email); the multi-platform attribution comparison therefore runs on this
  module's own validated simulator (see `INTEGRATION_PLAN.md` §5).
- **Markov attribution underperforms** the simpler models on these short journeys — reported
  honestly rather than hidden.
- The What-If simulator in the dashboard is a planning projection, not a causal counterfactual.

> **Data-size note:** this module simulates **10,000 users** (pipeline default and committed
> data). The interim report text mentions ~2,000 — reconcile the report to 10,000, or
> regenerate with `--users 2000`, so the two agree.

---

## 9. How it fits the unified system

`M1 segments → M2 campaign event logs → **M3 analytics** → M4 content`. The unified repo wires
this module in through `adapters/m2_to_m3.py` (event-log format) and `adapters/m3_to_m4.py`
(analytics → content priorities), driven by `orchestrator.py` at the repo root.
