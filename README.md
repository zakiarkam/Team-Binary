# AI-Powered Digital Marketing Orchestration

**Team Binary · University of Moratuwa · Level 4 Final Year Project (2026)**

A closed-loop marketing system that watches a real website, segments the people who
visit it, decides who to contact and when, measures what actually happened, and writes
the next round of content from that measurement — then feeds the result back to the top.

Four research modules, one production stack, and eleven reproducible experiments that
report what the evidence supports and what it does not.

---

## What it does

```
  Client website  ──mos.js──▶  FastAPI backend  ──▶  PostgreSQL
                                    │                    ▲
  Next.js dashboard ──REST──────────┤                    │
                                    ▼                    │
                        AI modules M1 · M2 · M3 · M4 ─────┘
```

A tracking snippet (`mos.js`) is pasted into any website. Visitors, clicks, scroll
depth and purchases flow into PostgreSQL through the FastAPI backend. The four modules
then run over that audience, and the Next.js dashboard shows the result — with every
figure labelled by where its data came from.

| Module | Role | Key idea |
|---|---|---|
| **M1 — Segmentation** | Turns an audience into five segments | Hybrid engine: rules + K-Means + hierarchical clustering vote, so segmentation still works on a brand-new product with almost no data |
| **M2 — Automation** | Decides who gets contacted, with what, and when | Three policies — `fixed`, `trigger`, `hybrid` — compared on efficiency *and* operational complexity (how many decision rules each needs) |
| **M3 — Analytics** | Funnels, attribution, per-visitor prediction | Four attribution models (first-touch, last-touch, linear, Markov removal-effect) plus conversion / drop-off classifiers and uplift modelling |
| **M4 — Content** | Reads the client's site and writes platform content | Crawl → knowledge base → inferred campaign goal & tone → per-platform assets → scored → optimised → significance-tested |

**The loop closes in both directions.** M3's attribution decides which platforms M4
writes for first; M4's best-scoring email asset becomes the opening message of M2's
next campaign. Neither direction is decorative — the send records which
`content_asset_id` it used.

The five shared segments are `High Intent · Loyal Customer · Price Sensitive ·
Low Engagement · New Cold User`.

---

## Tech stack

| Layer | What |
|---|---|
| Backend | FastAPI · SQLAlchemy · PostgreSQL 16 · psycopg 3 |
| Dashboard | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · Recharts |
| ML / NLP | scikit-learn · XGBoost · PyTorch · Transformers (BART, Phi-3 Mini) · Sentence-BERT |
| Data | pandas · NumPy · SciPy |
| Crawling | requests · BeautifulSoup · Playwright (JS-heavy sites) |
| Tracking | Vanilla-JS snippet, no third-party cookies, honours Do Not Track |

---

## Quick start

Requires Python 3.10+, Node 18+, and either Docker or a local PostgreSQL 16.

```bash
python3 -m venv .venv && source .venv/bin/activate
make setup        # Python + Node dependencies, Playwright browser, .env
make db           # PostgreSQL on port 5434 (Docker, or Homebrew if no Docker)
```

Then four terminals:

```bash
make api          # FastAPI      → http://localhost:8000/docs
make web          # Dashboard    → http://localhost:3000
make site         # Demo store   → http://localhost:4000
make demo         # Import the audience and run every module
```

`make help` lists every target. `make status` shows what is currently up.

**Everything runs locally.** No API keys are needed — the language models are
Hugging Face checkpoints downloaded on first use, and outbound email is **dry-run by
default** (leave `SMTP_HOST` empty in `.env` and messages are composed, tracked and
recorded but never sent).

Full operating guide: **[docs/RUNNING.md](docs/RUNNING.md)**.

---

## Try it without a database

The research pipeline and every experiment run standalone:

```bash
make research                      # all 11 experiments + figures (~3.5 min)
python -m research.run_all --only E1,E4
python orchestrator.py --full      # M1 → M2 → M3 → M4 as one pipeline
streamlit run app_unified/Home.py  # legacy Streamlit UI over the same modules
```

---

## The demo store

`demo-site/` is a small e-commerce site with the tracking snippet already installed —
a real second origin on port 4000, so tracking is genuinely cross-origin, exactly as a
customer's site would be. Browse it and watch events arrive:

| Do this | Event recorded |
|---|---|
| Land on a page | `page_view` (plus `utm_*` if present) |
| Scroll | `scroll` at 25 / 50 / 75 / 100 % |
| Click a link or button | `click` with its label |
| Submit the form | `form_submit` + `identify` |
| Add to basket → check out | `add_to_cart`, then `purchase` |

Turn on Do Not Track and reload: the footer badge flips off and nothing is collected.

**Never collected:** keystrokes, form field values (except one explicitly marked
`data-mos-email`), cross-site history, third-party cookies. Analytics consent and email
consent are separate — a visitor can be tracked and still not be contactable.

---

## Research results

Eleven experiments, all currently passing, seeded at 42 with 10,000 bootstrap
resamples. Results land in `research/results/` (one CSV per table plus
`results.json`); figures in `research/figures/` are drawn from those tables, and the
chapters in `docs/research/` interpolate their numbers from the same JSON — so a
chart, a chapter and the experiment behind it cannot disagree.

| # | Experiment | Headline |
|---|---|---|
| E1 | Hybrid segmentation vs each component alone | 8,000 users; mean confidence 0.71, but only 5.8% unanimous across the three methods |
| E2 | Leakage and the deleted cold-start segment | 163 cold-start users detected; a leaky feature inflated accuracy to 0.92 |
| E3 | Fixed vs trigger vs hybrid, 30 paired seeds | `trigger` best at 10.45 conversions/1k vs `fixed` at 7.15 — but `fixed` needs one rule |
| E4 | Attribution model comparison | Linear multi-touch closest to ground truth (MAE 0.018); models disagree by up to 68 pp |
| E5 | Prediction quality and transfer | Conversion AUC 0.97, drop-off 0.99 — thresholds do **not** transfer across audiences |
| E6 | Goal & tone classification | Tone macro-F1 0.73; campaign goal only 0.50 |
| E7 | Engagement prediction | Leaky R² 0.99 → **clean R² −0.17**: with leakage removed, the signal is not there |
| E8 | Uplift vs predicted-response targeting | Hillstrom, 64,000 customers: uplift (S-learner) wins at a 30% budget |
| E9 | Off-policy evaluation | SNIPS near-unbiased (−0.003); without exploration, bias rises to 0.039 |
| E10 | Capability detection on real websites | 21 judgements over 15 sites, 100% agreement (95% CI 0.85–1.0), 0 false positives |
| E11 | Cost of a larger action set | 2 actions need ~5,000 decisions; 16 actions need ~80,000 for the same error |

### What the project reports honestly

E7 is the clearest example of the standard this repo holds itself to. An engagement
model that looks near-perfect (R² 0.99) turns out to be reading its own answer; with
the leakage removed, R² is negative and Spearman correlation is indistinguishable from
zero. That negative result is kept, published and explained rather than quietly
dropped. The same discipline runs through the system:

- **Every figure carries a data-basis badge** — `research dataset`, `live traffic` or
  `dataset + live` — because imported customers use the same write paths as a real
  browser and a screenshot would otherwise be indistinguishable.
- **Attribution below 5 converting journeys returns no numbers**, with the reason
  stated. Attribution over two journeys is noise dressed as a finding.
- **Degenerate predictions raise a calibration warning** instead of a number, and the
  service says so in plain language.
- The `/research` dashboard page is generated from the repo and database at load time,
  so it cannot drift out of date — and it lists the shipped datasets that **no code
  reads**, rather than quietly omitting them.
- Open rates are always shown with the caveat that mail clients block tracking pixels.

---

## Repository layout

```
modules/
  m1_segmentation/    hybrid segmentation engine + notebooks
  m2_automation/      campaign policies, simulator, evaluation
  m3_analytics/       funnel, attribution, prediction, SHAP, bootstrap CIs
  m4_content/         crawler → KB → goal/tone → generate → score → optimise
adapters/             typed hand-offs between modules (M2→M3, M3→M4)
orchestrator.py       runs all four modules as one closed-loop pipeline
api/                  FastAPI backend: routers, services, schema.sql, mos.js
web/                  Next.js dashboard (Overview · Audience · Campaigns ·
                      Analytics · Content · Research)
app_unified/          legacy Streamlit UI over the same modules
demo-site/            the tracked demo e-commerce store
research/             11 experiments, figures, statistics, generated chapters
scripts/              audience import, demo build, training, tuning
tests/                backend, tracking, campaigns, analytics, content, research
docs/                 architecture, methodology, running guide, research chapters
```

---

## Tests

```bash
make test        # Python suites + M3 research suite + web build
make test-fast   # Python only, skipping slow tests
```

API tests **skip** rather than fail when PostgreSQL is not running, so the research
suite still passes on a machine without a database.

---

## Documentation

| Document | What it covers |
|---|---|
| [docs/RUNNING.md](docs/RUNNING.md) | Full operating guide — setup, ports, campaigns, email safety, the demo store |
| [docs/PROJECT_ARCHITECTURE.md](docs/PROJECT_ARCHITECTURE.md) | Layout, stage order, and every artifact each module reads or writes |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Research methodology |
| [docs/research/](docs/research/) | Generated chapters: methodology · experimental setup · results · discussion |
| [docs/EXTERNAL_DATA_AND_MODEL_AUDIT.md](docs/EXTERNAL_DATA_AND_MODEL_AUDIT.md) | Which dataset trained which model, and whether it is real or simulated |
| Module READMEs | [M1](modules/m1_segmentation/README.md) · [M2](modules/m2_automation/MODULE2_README.md) · [M3](modules/m3_analytics/README.md) |

---

## Data

The study audience is the Digital Marketing Campaign dataset (8,000 customers,
Kaggle), imported as the customer base of the demo store. Every per-customer total is
preserved exactly; event *timing, page paths and ordering* are reconstructed, because
the dataset holds no event log — this is stated wherever the numbers appear. Other
sources: UCI Bank Marketing (simulator calibration), Hillstrom MineThatData (uplift),
and public social-media engagement datasets.

Imported customers get addresses in the reserved `.invalid` TLD, so even with SMTP
configured they are unreachable by construction.

---

## Status and scope

This is an academic final-year research project, not a commercial product. It runs
locally, is designed for reproducibility and for a viva demonstration, and is
published so the experiments behind the report can be re-run and checked.

Team Binary · University of Moratuwa · 2026
