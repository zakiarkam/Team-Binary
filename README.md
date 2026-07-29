# AI-Powered Digital Marketing Orchestration

**Team Binary · Faculty of Information Technology · University of Moratuwa · 2026**

A closed-loop marketing framework for newly launched products, where there is
almost no data to work with. Four research modules — segmentation, campaign
automation, analytics, content generation — run as one system over one
audience, and every claim made about them can be reproduced with one command.

```
   research dataset ──8,000 customers──▶  the demo store's audience
                                                │
   ① Audience Targeting  ──segments──▶  ② Campaign Automation
        (rules + ML, cold-start)            (fixed / trigger / hybrid)
              ▲                                     │
              │                              tracked messages
        platform priorities                         ▼
              │                          ③ Analytics & Decision Support
   ④ AI Content Refinery  ◀──────────      (funnel · attribution · prediction)
     (reads the store)      ◀── analytics feedback closes the loop
```

The system is an **advisor, not a sender.** It does not publish to Instagram
and it does not send email. It works out what to do next, writes the content,
and hands over an **Action Plan** — *"send this to these 15 High Intent
contacts"*, *"post this on LinkedIn"* — which a company would execute in its own
tools. That is Module 3 of the report: **Decision Support**.

---

## Quick start

```bash
make setup     # once — Python, Node, Chromium, .env
make db        # PostgreSQL in Docker

make api       # terminal 2
make web       # terminal 3
make site      # terminal 4 — the demo store

make demo      # import the 8,000 customers and run every module
make research  # reproduce every experiment and figure
```

| | |
|---|---|
| Dashboard | <http://localhost:3000> — sign in as `demo@innov8smart.example` / `demo1234` |
| Demo store | <http://localhost:4000> |
| API docs | <http://localhost:8000/docs> |

`make help` lists everything. **[docs/VIVA_DEMO.md](docs/VIVA_DEMO.md)** is a
10-minute walkthrough; **[docs/RUNNING.md](docs/RUNNING.md)** has the detail.

---

## The audience, and what it is made of

**Read this before quoting any number.**

The study audience is the **Digital Marketing Campaign** dataset — 8,000 real
customers with recorded website behaviour, email engagement, purchase history
and a conversion outcome. `scripts/import_research_audience.py` imports them as
the customers of a demonstration e-commerce store, so the same audience flows
through all four modules exactly as a real one would.

The dataset is real, but it was measured as **per-customer totals**, not as an
event log. Nobody recorded when visit 14 happened or which page it was. So the
importer preserves the totals exactly and reconstructs only what the dataset
never contained:

| Measured — taken straight from the dataset | Reconstructed by the importer |
|---|---|
| Sessions, page views, time on site | The timestamp of each visit |
| On-site clicks, purchases | Which page each visit landed on |
| Email opens and clicks | Scroll depth (derived from dwell time) |
| Conversion outcome, acquisition channel | The order of email opens and clicks |

**Consequence.** Anything depending only on the totals — segment membership,
conversion by segment, funnel counts — rests on real measurements. Anything
depending on event *order* or *timing* — attribution paths, journey length — is
a property of the reconstruction as much as of the data, and is reported that
way throughout.

Fidelity is verified against the source CSV: sessions, page views, time on site,
clicks and purchases all match exactly, and a re-import is byte-identical.

### Provenance is recorded, never asserted

Imported customers and live browser sessions share one database, so every
visitor and every funnel event carries `source` = `dataset` or `live`, **derived
at write time from the visitor the event belongs to** — never supplied by the
caller. A test fails the build if a dataset-derived customer ever produces a row
claiming to be live observation. Every dashboard figure carries the label.

Browse the demo store yourself and the badge changes from `research dataset` to
`dataset + live`.

---

## Architecture

Matches Figure 5.1 of the report: a **Next.js + Recharts** dashboard over a
**FastAPI** backend over **PostgreSQL**, with the four Python modules behind
the API.

```
web/            Next.js dashboard — Overview · Plan · Audience · Campaigns ·
                Analytics · Content · Research
api/            FastAPI backend + schema.sql (the report's Figures 5.2–5.5)
  services/     each module as a service
  static/mos.js the tracking snippet
modules/
  m1_segmentation/  segment.py — the hybrid engine
  m2_automation/    strategy simulator
  m3_analytics/     funnel, attribution, prediction
research/       the experiments, statistics, figures and chapters
demo-site/      the e-commerce store under study
scripts/        setup, dataset import, training
```

> **Note on the report.** Chapter 3.6 says the backend is Node.js/NestJS, but
> Figure 5.1 shows FastAPI. FastAPI is what is built — every model is Python.
> The Ch. 3.6 sentence should be corrected. Likewise the report mentions MongoDB
> *and* PostgreSQL; all five figures show PostgreSQL, and that is what is used.

---

## Results

`make research` runs nine experiments and regenerates every figure from the
results it just wrote, so a chart cannot disagree with the number it plots.
Full write-up in **[docs/research/](docs/research/)**.

### Module 1 — the hybrid does not beat its own rules

| Method | Separation | 95% CI |
|---|---:|---|
| rules only | 0.3837 | [0.309, 0.464] |
| **hybrid (vote)** | **0.3838** | [0.307, 0.463] |
| k-means only | 0.0693 | [0.049, 0.090] |
| hierarchical only | 0.0343 | [0.019, 0.059] |

**This is a negative result and it is reported as the headline.** On conversion
separation the clustering contributes nothing. The hybrid earns its place on
different grounds — a calibrated confidence from three-way agreement, and a vote
that makes cold start explicit — but not by separating conversion better than a
handful of interpretable rules. Silhouette is 0.087; all three methods disagree
for 35% of customers.

### Module 3 — the attribution models disagree, and that is the finding

```
first_touch   referral 21% · email 21% · ppc 20% · seo 19% · social 19%
last_touch    email 89%    · referral 3% · ppc 3% · seo 3% · social 3%
linear        email 56%    · referral 12% · ppc 11% · seo 11% · social 10%
markov        email 53%    · referral 12% · ppc 12% · seo 11% · social 11%
```

Across 7,811 converting journeys the widest pair disagrees over **68% of all
attributed credit**. A company reading only last-touch would conclude email is
everything and cut the acquisition spend that built the audience.

### Module 3 — the recommender was answering the wrong question

Ranking customers by **predicted conversion** is not the same as ranking them by
whether the action *changes* what they do. On the Hillstrom dataset — 64,000
customers randomly assigned to mens email / womens email / no email, so the
counterfactual is estimable — the two policies share only **56%** of their
choices at a 30% budget (Spearman 0.40):

| Policy | Qini | 95% CI | Extra visits per 1,000 targeted |
|---|---:|---|---:|
| uplift (S-learner) | 93.6 | [56.1, 129.8] | **103** |
| uplift (T-learner) | 70.4 | [30.2, 112.3] | 92 |
| predicted response *(what the recommender did)* | 75.9 | [38.8, 110.0] | 91 |
| random targeting | −9.8 | [−48.7, 27.0] | 58 |

**Stated carefully:** the intervals overlap, and the second uplift learner does
*worse* than the current policy — so "use uplift modelling" is not a conclusion
on its own. What the data supports is that these are different policies choosing
different people, by a margin large enough to matter.

This cannot be validated on the project's own audience at all: no action was
ever randomised there, so no counterfactual exists.

### Module 3 — and the mechanism that makes it fixable

E8 showed the recommender asks the wrong question and that no borrowed dataset
can answer the right one for *your* actions. So the system now records what it
needs to answer it itself: an append-only `action_log` holding every decision,
**the probability it was taken under**, and what followed — plus 10% of
decisions made at random on purpose, because a deterministic policy assigns
probability zero to every action it doesn't take, and you cannot learn from a
denominator of zero.

Validated against a known answer (E9): at 10,000 logged decisions the
self-normalised estimator recovers a candidate policy's true value with a bias
of −0.003, interval containing zero.

**The finding worth remembering:** without exploration the estimate is biased
**upwards** — it reports a candidate policy as better than it is — and the
deterministic log looks *more* trustworthy, not less. Its effective sample size
is 1,094 against 107, because every weight is 0 or 1 rather than spread out. The
standard diagnostic points the wrong way. **Stability is not correctness.**

Token exploration is worse than none: at 1% the estimator has the worst error of
any setting tested. Exploration is a commitment, not a gesture — and it costs
about 7.5% of achievable reward at a 10% rate.

### Module 4 — the simpler model wins, and macro-F1 is why we know

| Target | TF-IDF macro-F1 | SBERT+XGB macro-F1 | McNemar p |
|---|---:|---:|---:|
| campaign goal | **0.500** | 0.404 | 1.000 |
| tone | **0.732** | 0.591 | 0.727 |

Statistically indistinguishable — so choosing TF-IDF is a decision about cost
and interpretability, not accuracy. That is a stronger claim than asserting the
simpler model is better.

---

## Corrections made to the original research

Six defects were found while turning the notebooks into a running system. Each
is fixed, each has a regression test, and E2/E7 reproduce two of them with
numbers rather than asserting the fix happened.

| # | Defect | Measured effect |
|---|---|---|
| 1 | **Random Forest trained with its target as an input feature** | Accuracy barely moves (0.9213 → 0.9200) but certainty inflates **150×**: 450 customers at confidence 1.00 against 3. Accuracy was never what the leak corrupted. |
| 2 | **The cold-start segment deleted by its own vote** | `ml == hier` was tested before `rule == New Cold User`, so clustering overruled the rules. 163 detected → 127 kept; on live data it reached **0**. Novel Contribution 1 erased from its own output. |
| 3 | **Cluster names hardcoded to cluster indices** | Correct for one dataset and one seed; arbitrary on any new audience. Now derived from centroids. |
| 4 | **Engagement model trained on its own target** | R² 0.99 → **−0.168** [−0.408, −0.072]; Spearman 0.012, interval spanning zero. Its weight in content scoring fell 0.45 → 0.20. |
| 5 | **Goal/tone corpus needlessly quartered** | A row had to clear the confidence bar for *both* targets although the classifiers train separately. **114 → 527 rows.** |
| 6 | **`shorts` never received a video brief** | Declared `visual: video` but had no `visual_options`, so the selector silently returned `image`. |

Two environment faults were also fixed: a macOS **OpenMP segfault** where
XGBoost and PyTorch each load their own `libomp` (it killed training, the test
suite and API workers with no traceback), and a **character-encoding bug** in
the crawler that turned every em-dash in the store's copy into mojibake.

---

## Known limitations

- **Event timing and ordering are reconstructed**, so attribution path
  statistics are partly a property of the importer.
- **Campaign response is modelled**, in both the simulator and the live build.
  Nobody in this study opened a real email.
- **Conversion and drop-off models were fitted on a simulator** and transfer
  poorly in calibration, though the ranking survives.
- **The engagement dataset carries no usable text signal** — 0 of 8 text
  features survive Holm–Bonferroni correction. Not a modelling failure.
- **`humorous` tone has one training example** and cannot be learned.
- **No action was ever randomised on this audience**, so the next-best-action
  recommendation cannot be validated on it. E8 borrows a dataset where treatment
  *was* randomised; those actions are not this project's actions.
- **Open rates under-report** — most mail clients block the pixel. Click-through
  is the reliable signal.
- Three real platform datasets ship unused: comment-level scrapes that pair no
  post text with post engagement.

---

## Testing

```bash
make test          # Python suites + dashboard build
make test-fast     # Python only, skipping slow tests
make research      # every experiment, ~3.5 minutes
```

**177 Python tests**, plus Module 3's own suite, plus a TypeScript build. The
API tests skip rather than fail when PostgreSQL is not running.

---

## Documentation

| | |
|---|---|
| **[docs/research/](docs/research/)** | Methodology, experimental setup, results, discussion — generated from the measured numbers |
| **[docs/VIVA_DEMO.md](docs/VIVA_DEMO.md)** | 10-minute walkthrough and the questions it answers |
| **[docs/RUNNING.md](docs/RUNNING.md)** | Setup, ports, campaigns, analytics |
| **[modules/m1_segmentation/README.md](modules/m1_segmentation/README.md)** | The segmentation engine and its corrections |
| `/research` on the dashboard | Live data and model provenance |
