# Engagement Learning Loop

How the system learns to produce more engaging content **without ever posting**,
and how it is wired into the existing pipeline without changing it.

This is the adaptive half of the project. Everything here lives in `modules/m4_content/learning/`
and runs only through opt-in stages — a plain `python modules/m4_content/main.py` does not touch any
of it.

---

## 1. The core idea

The system cannot auto-post, so it cannot observe engagement on its own outputs.
The resolution is to **not depend on posting**: learn from performance data that
already exists (a business's own past posts, exported from platform analytics),
and use that to predict and rank future content.

Two subsystems, only one of which ever needs a post to exist:

```
SYSTEM 1 — generate (unchanged)                SYSTEM 2 — learn (new, opt-in)
  website → KB → goal/tone → summary             historical posts + analytics
        → Phi-3 → caption/hashtags/CTA/prompt          → relative target
                                                        → engagement predictor
                                                        → rank future candidates
```

System 2 never posts. It reads analytics the business already has.

---

## 2. The one decision that makes or breaks it: relative targets

**Do not predict absolute likes.** A caption's like count is dominated by
follower count — a 1M-follower account beats a 500-follower account on an
identical caption. Train on absolute counts and the model learns _the account_,
not _the content_. This is the account-size confound, and it is the documented
reason text-only engagement prediction is weak.

The fix, in `learning/targets.py`, is a target relative to the account's own
baseline, in two tiers:

| Tier                  | Target                                           | When                   |
| --------------------- | ------------------------------------------------ | ---------------------- |
| **Cold-start (base)** | `engagement_rate = interactions / impressions`   | no per-account history |
| **Personalized**      | within-account percentile / z-score of that rate | account has ≥ N posts  |

`relative_target()` returns the personalized target where an account has enough
history and falls back to the rate otherwise, so one call handles a corpus mixing
brand-new and data-rich accounts. The personalized target removes account size
entirely, so **one pooled model is comparable across accounts** — that is what
lets a brand-new business get a useful model on day one while an established one
gets a model tuned to its own audience.

### What the data actually supports today

Measured on the corpora in this repo:

- `Social Media Engagement Dataset.csv` (the rich base corpus) has `user_id` and
  a precomputed `engagement_rate`, **but exactly one post per user** — 12,000
  users, 12,000 posts. So the _relative_ target cannot engage on the base corpus;
  it correctly degrades to the raw rate, and the base model is a generic
  cold-start predictor. (Also note `engagement_rate` there ranges up to 32.2, so
  impressions are not always ≥ interactions — a data-quality caveat; a log
  transform or upper clip is worth considering for the base model.)
- The **personalized tier activates from feedback data**, where a single business
  accumulates many of its own posts over time. That is exactly the account with
  repeat history the relative target needs.

This is the honest story to tell: _general model now, personalized model as each
business's own history accumulates._ It is also the cold-start contribution.

---

## 3. How the model "learns new patterns" without retraining Phi-3

The generator stays frozen. Three cheap things adapt:

1. **The predictor** (`learning/personalize.py`) — retrain RF/XGBoost on
   `base corpus + collected feedback` with the relative target. Minutes.
2. **The selection** (`learning/candidates.py`) — generate N candidates per
   platform, rank by the _updated_ predictor inside the full composite score,
   keep the best (best-of-N).
3. **The prompt guidance** (future work, sketched below) — mine the feedback for
   what correlates with high engagement _for this account_ and inject it as a
   dynamic rule into the generate/optimize prompts.

So content gets more engaging as the predictor improves, with no weight update to
the 3.8B language model.

> ⚠ **Reward-hacking caveat.** Ranking N candidates by a model-predicted score is
> an over-optimization regime (Gao et al., _Scaling Laws for Reward Model
> Overoptimization_, ICML 2023): pushed hard, best-of-N selects for the
> predictor's error, not real engagement. Guards built in: N is small (default 5)
> and ranking uses the full composite (semantic + platform + engagement), not
> predicted engagement alone. **Whether best-of-N actually beats a random pick is
> an empirical question the feedback data answers** once enough actuals exist —
> that comparison is the honest validation of this stage, and it is a
> contribution in its own right.

---

## 4. Where the data comes from

Reading analytics needs none of the app-review bureaucracy that _posting_ does,
and the two permissions are separate — the business can keep posting by hand.

Preferred order (the store interface is identical, so later paths drop in behind
the same seam):

1. **CSV import of Insights exports — built now** (`learning/importer.py`).
   Instagram, LinkedIn and Meta all export a post-level analytics CSV. Drop it in
   `data/feedback/analytics_import/` and run `feedback-import`. The importer maps
   each platform's column names onto the store's canonical metrics; unknown
   layouts are reported, never silently dropped.
2. **Platform Analytics APIs** — future. Instagram Graph / LinkedIn / YouTube.
   Most automated, but needs a Business account and Meta app review (weeks).
3. **OCR from Insights screenshots** — future, demo-grade fallback.
4. **Manual entry** — last resort.

---

## 5. How it connects to the existing pipeline (without changing it)

The pipeline hands off through files and named stages, so this is purely
additive. Guarantees:

- The default `python modules/m4_content/main.py` runs the **same 15 stages as before**. The four
  learning stages are in `LEARNING_STAGES`, not `STAGES`, so they run **only**
  when named with `--step`.
- The personalized model is written to
  `models/personalized_engagement_model.pkl` and **never overwrites**
  `best_engagement_model.pkl`. The base evaluate/optimize path is byte-for-byte
  unchanged.
- New artifacts only (a SQLite store, a personalized model, candidate CSVs). No
  existing column, file, or function signature changed.

```
modules/m4_content/learning/
├── targets.py         relative-engagement target            ← the core idea
├── feedback_store.py  SQLite: predictions now, actuals later (nullable)
├── importer.py        Insights CSV → store
├── personalize.py     retrain predictor on base + feedback
└── candidates.py      best-of-N generation, ranked

new opt-in stages (modules/m4_content/main.py):
  feedback-log · feedback-import · engagement-retrain · generate-candidates
```

### The feedback store

`data/feedback/feedback.db` (SQLite). Each row is a generated asset plus the
score the model predicted for it, and a set of **nullable** actual-analytics
columns filled in later. An asset acquires its actuals by matching on the
platform's `external_post_id`, or — since the caption you posted is the caption
we generated — by normalized caption text. Analytics rows that match no generated
post but carry their own caption are inserted as standalone history, so a
business's back-catalogue becomes training data too.

---

## 6. Running it

```bash
# 1. Record what was generated (predictions), tagged by source.
python modules/m4_content/main.py --step feedback-log

# 2. Later: drop platform Insights CSVs in data/feedback/analytics_import/,
#    then ingest the observed engagement.
python modules/m4_content/main.py --step feedback-import

# 3. Retrain the personalized predictor on base corpus + feedback.
python modules/m4_content/main.py --step engagement-retrain --force

# 4. Best-of-N: generate several candidates per platform, rank, keep the best.
python modules/m4_content/main.py --step generate-candidates
```

To attribute feedback to a business, add an `account_id` to `input.json`; it is
threaded through logging, import, and personalization. Without it, everything
still works as a single pooled account.

Recommended cadence: `feedback-import` + `engagement-retrain` weekly as new
analytics arrive; `generate-candidates` per product.

---

## 7. What this does for the research

It converts the strongest novelty claim from "plausible" to "demonstrated." Last
analysis ranked the defensible contribution as _substituting a supervised
engagement regressor for the LLM judge in an inference-time refinement loop, with
no RL and no production traffic._ This subsystem is that loop, made concrete, and
it adds two things reviewers ask for:

- a principled answer to the account-size confound (relative targets), which is
  the standard objection to text-only engagement prediction;
- a clean cold-start → personalized story that does not retrain the LLM.

### Honest limitations to state in the write-up

- The public base corpus is singleton-per-account, so the personalized tier is
  only demonstrated on collected feedback — report base and personalized results
  separately.
- Best-of-N against a proxy is over-optimization-prone; report the random-pick
  control.
- Caption-text matching for actuals is heuristic; `external_post_id` is exact and
  preferred when the business records it.

---

## 8. Next increments (designed, not yet built)

- **Learned prompt guidance**: SHAP/feature-importance over the account's
  feedback → a short "what works for this account" rule injected into the
  generate/optimize prompts. The prompt adapts though the weights do not.
- **Multi-target prediction**: separate heads for likes / comments / shares /
  reach rather than one composite rate, each content-relative.
- **API sync** behind the same store interface, once app review is cleared.
