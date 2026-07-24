# AI-Powered Digital Marketing Orchestration — Integration & Completion Plan

**Team Binary · University of Moratuwa · 2026**
Working branch: `unified` (created off `integrate`, non-destructive).

This document is the single source of truth for turning four separately-built
research modules into one integrated, closed-loop system with an operational UI.

---

## 1. Starting reality (what we actually had)

The four modules were **strong individually but never merged** — each lived on its
own branch. `integrate` was essentially only Module 4 (content), with Module 3's
`.pkl` files copied in but *not* its code (orphaned).

| Module | Owner branch | Nature | State |
|---|---|---|---|
| **M1 — Audience Segmentation** | `person1-segmentation` | Jupyter notebooks + `user_segments.csv` (8,000 users, hybrid rule+RandomForest) | Works; no reusable `.py` module yet |
| **M2 — Marketing Automation** | `person2-automation` | Python package: simulator, fixed/trigger/hybrid strategies, ML conversion model, multi-seed/sparsity/uplift robustness | Research-grade |
| **M3 — Analytics & Decision Support** | `person3-analytics` | Python package: funnel, 4 attribution models (incl. Markov removal-effect), conversion/drop-off models, SHAP, bootstrap CIs | Research-grade |
| **M4 — Content Refinery** | `integrate` (root) | crawl → goal/tone → Phi-3 generation → engagement scoring → evaluate → optimize + adaptive learning loop | Most developed |

**Decisions taken (2026-07-24):**
1. UI = **Unified Streamlit app** (operational + research dashboards).
2. Distribution = **Preview + export + schedule simulation** (no live auto-posting).
3. Content generation = **Module 4's own pipeline as built** (Phi-3 + goal/tone classifiers),
   with the **missing engagement-prediction stage re-wired** so the full flow runs.

---

## 2. Target architecture (unified, closed loop)

```
                        input.json  (product, website, audience, segment, platforms)
                             │
   ┌─────────────────────────┼───────────────────────────────────────────────┐
   │                    orchestrator.py                                        │
   │                                                                           │
   │  M1 Segmentation ──user_segments.csv──▶ M2 Automation ──event_logs──▶ M3 │
   │  (segment users)      (CustomerID,        (fixed/trigger/    (wide)   Analytics
   │                        segment_name)        hybrid sims)                  │
   │        ▲                                                        │         │
   │        │                                            analytics_output.json │
   │        │                                            + insights + strategy │
   │        │                                                        │         │
   │        └──────────── closed-loop feedback ◀─────────────────────┤         │
   │                                                                 ▼         │
   │                                              M4 Content Refinery          │
   │                                     (goal/tone → Phi-3 → engagement →      │
   │                                      evaluate → optimize → preview/export) │
   └───────────────────────────────────────────────────────────────────────────┘
```

**Repo layout on `unified`:**
```
Research/
  orchestrator.py              # NEW — runs the full closed loop
  adapters/                    # NEW — schema bridges between modules
  app_unified/                 # NEW — operational Streamlit app ("Run Campaign")
  config.py, main.py, ...      # M4 content pipeline (kept at root, untouched)
  learning/  dashboard/        # M4 adaptive loop + M4 research dashboard
  modules/
    m1_segmentation/           # M1 notebooks + user_segments.csv  (+ new segment.py)
    m2_automation/             # M2 package (src/, scripts/)
    m3_analytics/              # M3 package (src/)
```

M4 is deliberately left at the repo root (its `config.ROOT` and all data paths assume
this) so the working pipeline is not broken by the restructure.

---

## 3. The integration contracts (exact schemas)

### 3.1 M1 → M2 — ALREADY COMPATIBLE ✅
`modules/m1_segmentation/user_segments.csv`:
`user_id, CustomerID, segment_id, segment_name, segment_method, segment_confidence`
- 8,000 rows, same dataset as M2 (`digital_marketing_conversion.csv`).
- `segment_name` ∈ {`High Intent, Low Engagement, Price Sensitive, Loyal Customer, New Cold User`}
  — exactly the 5 labels M2 hardcodes. No adapter needed; just copy the file to
  `modules/m2_automation/data/processed/user_segments.csv`.

### 3.2 M2 → M3 — NEEDS AN ADAPTER ⚠
- **M2 writes WIDE** (`outputs/event_logs.csv`): one row per message —
  `user_id, message_index, sent, opened, clicked, converted, triggered, timestamp_day, segment_name, strategy`. Email-centric; **no platform concept**.
- **M3 wants LONG** (`data/simulated/event_logs.csv`): one row per event —
  `user_id, timestamp, channel, platform, campaign_id, strategy, event_type`
  with `event_type ∈ {sent,open,click,convert}`, `platform ∈ {email,facebook,instagram,linkedin,tiktok}`, `channel ∈ {email,social,ad,offer}`.
- Adapter (`adapters/m2_to_m3.py`) must: explode wide→long, synthesize ISO timestamps
  from `timestamp_day`, map segment labels Title-Case→snake_case, and **assign platforms**.
  → **See §5 design decision** for how platform assignment is handled honestly.

### 3.3 M3 → M4 — NEEDS AN ADAPTER ⚠
- M3 emits `analytics_output.json` (per user: `predicted_conversion, drop_off_risk,
  recommendation, best_platform, platform_credits, confidence`).
- M4's `learning/` loop expects platform *analytics exports* (likes/comments/shares/impressions).
- Adapter (`adapters/m3_to_m4.py`) translates M3's per-platform performance signal into
  M4's content-prioritisation feedback (which platforms/goals to favour). This closes the loop.

### 3.4 Segment label map (`adapters/segment_labels.py`)
`"High Intent"↔"high_intent"`, `"Low Engagement"↔"low_engagement"`,
`"Price Sensitive"↔"price_sensitive"`, `"Loyal Customer"↔"loyal_customer"`,
`"New Cold User"↔"new_cold_customer"`.

---

## 4. Model health — findings & hardening

| Model | Issue found | Fix |
|---|---|---|
| **M3 conversion / drop-off** | AUC ≈ 1.0 on simulated data = **label leakage** (target defined by the same events used as features). | De-leak feature set / clearly separate *simulated* vs *real* metrics; report the honest **Bank-Marketing real-data AUC ≈ 0.95**. |
| **M4 tone classifier** | accuracy **1.0 on 121 rows** = overfit. | Stratified k-fold CV, expand labeled set, report CV mean±std not single split. |
| **M4 goal classifier** | 0.75 acc, `engagement` class F1 = 0 (1 support). | More labeled data for rare classes; report per-class honestly; consider class weights. |
| **M2 conversion model** | Honest; near baseline due to class imbalance. | Keep; document. Optionally persist the fitted model as an artifact. |
| **M4 engagement regressor** | **Not trained / missing from outputs.** | Train it and wire `engagement-score` into the flow (Phase 2). |

A "best research project" reports these honestly rather than hiding the inflated numbers.

---

## 5. Key design decision for Phase 1 (M2 ↔ M3 platform gap)

M2 simulates **generic (email-centric) messages with no platform**; M3's attribution study
is fundamentally **multi-platform**. Three ways to reconcile:

- **(A)** Fabricate platforms on M2 messages → makes attribution "run" on invented journeys. *Rejected — dishonest.*
- **(B)** Extend M2's simulator to assign a platform per message (by segment/step) so multi-touch journeys are genuinely simulated. *More honest, modifies M2.*
- **(C, recommended)** Two honest data paths:
  - **Real M1→M2 pipeline** feeds M3's **funnel + conversion/drop-off + recommendations** (these only need sent/open/click/convert, which M2 truly produces).
  - **M3's own richer multi-platform simulator** remains the basis for the **attribution study** (which needs multi-platform journeys), clearly labelled as a controlled simulation.
  This keeps every number defensible and still demonstrates the full closed loop.

**Chosen: (C)**, with (B) as an optional future enhancement.

---

## 6. Phased delivery

- **Phase 0 — Unify repo** ✅ *(done)* — `unified` branch; all 4 modules co-located; M2/M3 import-verified.
- **Phase 1 — Adapters + orchestrator** — segment-label map, M2→M3 adapter, M3→M4 adapter, `orchestrator.py` running the full loop on the 8,000-user sample.
- **Phase 2 — Complete M4 content** — train the engagement regressor, wire generate → engagement-score → evaluate → optimize so the whole content flow runs end-to-end.
- **Phase 3 — Operational Streamlit app** — "Run Campaign" input page (product/audience) → runs the loop → shows segments, campaign-strategy results, analytics, and preview/export/schedule of platform posts; plus the M2/M3/M4 research dashboards.
- **Phase 4 — Model hardening** — fix leakage, cross-validate, honest metrics, cold-start evaluation.
- **Phase 5 — Integrated research evaluation + docs** — end-to-end metrics, comparisons, updated README/report artifacts.

---

## 7. How to run (target, once Phases 1–3 land)

```bash
# one-shot closed loop on sample data
venv/bin/python orchestrator.py --full

# operational app
venv/bin/streamlit run app_unified/Home.py
```
