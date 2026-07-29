# AI-Powered Digital Marketing Orchestration

**Team Binary · Faculty of Information Technology · University of Moratuwa · 2026**

A closed-loop marketing platform for newly launched products, where there is
almost no data to work with. **A company creates an account, registers its
website, pastes one script tag into it — and that website's visitors become
the audience** the four research modules act on.

The system is an **advisor, not a sender.** It does not publish to Instagram
and it does not have to send your email. It works out what to do next, writes
the content, and hands you an **Action Plan** — *"send this email to these 15
High Intent contacts"*, *"post this on LinkedIn"* — which you execute in your
own tools. That is Module 3 of the report: **Decision Support**.

```
   client's website ──mos.js──▶  visitors become the audience
                                        │
   ① Audience Targeting  ──segments──▶  ② Campaign Automation
        (rules + ML, cold-start)            (fixed / trigger / hybrid)
              ▲                                     │
              │                              tracked email
        platform priorities                         ▼
              │                          ③ Analytics & Decision Support
   ④ AI Content Refinery  ◀──────────      (funnel · attribution · prediction)
     (reads their website)   ◀── analytics feedback closes the loop
```

---

## Quick start

```bash
make setup     # once — Python, Node, Chromium, .env
make db        # PostgreSQL in Docker

make api       # terminal 2
make web       # terminal 3
make site      # terminal 4 — the demo client website

make demo      # populate a full demonstration (~60s)
```

| | |
|---|---|
| Dashboard | <http://localhost:3000> — sign in as `demo@innov8smart.example` / `demo1234` |
| Client website (demo) | <http://localhost:4000> |
| API docs | <http://localhost:8000/docs> |

`make help` lists everything. **[docs/VIVA_DEMO.md](docs/VIVA_DEMO.md)** is a
10-minute walkthrough; **[docs/RUNNING.md](docs/RUNNING.md)** has the detail.

### Multi-tenant by design

The dashboard is a product, not a demo script. Any company can **Create your
company account → Add your website → install the snippet** and get its own
audience, campaigns, analytics and content — scoped to that account alone:

- **Isolation is enforced in the API**, in one middleware that covers every
  site-scoped route; a company probing another company's site gets **404**,
  which doesn't even confirm it exists. A test registers two companies and
  proves it.
- **Sessions are database rows** — signing out deletes the row and the token
  dies instantly. Passwords are salted **scrypt**; the browser never sees the
  token (HttpOnly cookie on the dashboard's own origin).
- The public tracking routes (`/collect`, `/mos.js`, `/track/*`) need no
  login — a website's *visitors* aren't signed in to anything.

---

## Architecture

Matches Figure 5.1 of the interim report: a **Next.js + Recharts** dashboard
over a **FastAPI** backend over **PostgreSQL**, with the four Python modules
behind the API.

```
web/            Next.js dashboard — Overview · Audience · Campaigns ·
                Analytics · Content · Research
api/            FastAPI backend + schema.sql (the report's Figures 5.2–5.5)
  services/     each module as a service: segmentation, campaigns,
                email_sender, analytics, content, provenance
  static/mos.js the tracking snippet a client installs
modules/
  m1_segmentation/  segment.py — the hybrid engine
  m2_automation/    strategy simulator (research)
  m3_analytics/     funnel, attribution, prediction (research)
demo-site/      a realistic client website with the snippet installed
scripts/        setup, demo data, training, threshold tuning
```

The database uses the exact table names the report's figures name:
`user_segments`, `interactions`, `analytics_output`, `content_assets`.

> **Note on the report.** Chapter 3.6 says the backend is Node.js/NestJS, but
> Figure 5.1 shows FastAPI. FastAPI is what is built — every model is Python,
> and it is what the architecture chapter specifies. The Ch. 3.6 sentence should
> be corrected. Likewise the report mentions MongoDB *and* PostgreSQL; all five
> figures show PostgreSQL, and that is what is used.

---

## How the loop actually closes

| Step | What is real |
|---|---|
| **Audience** | One `<script>` tag on the client's site. Visitors, page views, scroll depth, clicks and conversions are collected first-party. Do Not Track is honoured. |
| **Segmentation** | Rules + K-Means + hierarchical clustering, combined by agreement. Below 30 visitors it declines to cluster and says why — the normal state for a launch. |
| **Action Plan** | Ready-to-send email drafts and ready-to-post captions, each with who it is for and why. Nothing leaves the platform. |
| **Analytics** | The funnel is measured, not simulated. A purchase is matched back to the click that earned it. |
| **Content** | The client's website is crawled; its own copy and headings drive the generated posts. Platform order comes from attribution. |
| **Back to the plan** | The highest-scoring email asset becomes the next plan's opening message. |

### How an advisory system still measures results

The tracked link lives in the **content**, not in the delivery — so it works no
matter who sends the message:

| The company publishes… | …and we still see |
|---|---|
| An email via Mailchimp or Gmail | **Clicks** — the body carries `/track/click/{token}/{i}` |
| An Instagram or LinkedIn post | **Clicks** — the caption carries `/l/{token}`, which redirects with `utm_source=instagram` so the visit is attributed |
| Either | **Conversions** — `mos.js` sees the purchase and ties it to the click |

The one thing lost is **guaranteed open tracking**: the pixel only fires if the
company pastes our HTML verbatim. Opens were always the weakest signal anyway —
Apple Mail Privacy Protection pre-fetches every pixel — which is why the
dashboard tells you to read *sent→click*, not *sent→open*.

**Sending is still available** as an opt-in: set `SMTP_HOST` and a company can
send from the platform (and then opens are guaranteed too). Advisory is the
default because it carries no deliverability or spam liability.

---

## Honesty, built into the system

The largest risk in a project like this is a reader assuming a number measured
real behaviour when it did not. Three mechanisms guard against that:

**1 · Real and simulated are separated in the data, not in a README.**
`visitors.is_synthetic` and `interactions.is_real` are *derived* when a row is
written, never asserted by the caller — demo traffic travels through the same
public endpoints as a real visitor. Every figure in the dashboard carries a
`real` / `simulated` / `mixed` badge, and a test fails the build if a synthetic
visitor ever produces a row marked real.

**2 · The Research page is generated, not written.**
Row counts are read from disk as the page loads, so it cannot drift. It reports
which dataset trained which model, whether that data is real, and for every
model both the headline number and what it actually means.

**3 · The system refuses to report what it cannot support.**
Attribution below five converting journeys returns no numbers, with the reason.
Degenerate predictions raise a calibration warning instead of a confident zero.
Journey diagnostics accompany every attribution result.

---

## Results, and what they mean

### Module 1 — segmentation (8,000-user research dataset)

| Segment | Users | Conversion |
|---|---:|---:|
| Low Engagement | 3,384 | 86.0% |
| Loyal Customer | 2,247 | 91.0% |
| Price Sensitive | 1,393 | 87.9% |
| High Intent | 813 | 91.8% |
| New Cold User | 163 | **53.4%** |

**38.4 points of conversion separation.** Conversion only ever *evaluates* the
segments — it is never a clustering feature — so the separation is not circular.

Reported honestly: **silhouette 0.087**. The clusters overlap heavily. The
segments are commercially useful without being geometrically clean, and 41% of
users have all three methods disagreeing.

### Module 3 — the attribution models disagree, and that is the finding

```
first_touch   newsletter 32% · direct 26% · instagram 21% · linkedin 11%
last_touch    email 88%      · linkedin 13%
linear        newsletter 24% · direct 21% · email 18% · instagram 18%
markov        email 34%      · newsletter 16% · instagram 15% · google 14%
```

Single-touch models point at opposite ends of the same journey. A company using
only last-touch would conclude email is everything and cut the spend that
created the audience.

### Module 4 — measured, including where it fails

| Model | Result |
|---|---|
| Campaign-goal classifier | accuracy 0.80, **macro-F1 0.54** (453 rows) |
| Tone classifier | accuracy 0.89, **macro-F1 0.72** (173 rows) |
| Engagement regressor | **R² −0.30, Spearman 0.02** |

Macro-F1 is the number to read: `awareness` is over half the goal corpus, so
accuracy flatters a model that handles rare classes badly. Both classifiers
selected **TF-IDF over Sentence-BERT + XGBoost** — the simpler model won.

---

## Corrections made to the original research

Six defects were found while turning the notebooks into a running system. Each
is fixed, and each has a regression test.

| # | Defect | Effect |
|---|---|---|
| 1 | **M1 Random Forest trained with its target as an input feature** | 6,248 of 8,000 users had confidence exactly 1.00. Honest held-out accuracy is **0.92**. |
| 2 | **The cold-start segment was silently deleted** | Clustering agreement overruled the rules, so `New Cold User` went 43 → **0** on live data. Novel Contribution 1 was being erased from its own output. |
| 3 | **Cluster names hardcoded to cluster indices** | Correct for one dataset and one seed; arbitrary on any new audience. Names are now derived from centroids. |
| 4 | **Engagement model trained on its own target** | `likes`, `comments`, `shares` and `impressions` were left in the features while the target was their ratio. R² 0.99 → **−0.30**. Its weight in content scoring fell from 0.45 to 0.20. |
| 5 | **Goal/tone corpus needlessly quartered** | A row had to clear the confidence bar for *both* targets although the classifiers train separately. **114 → 527 rows.** |
| 6 | **`shorts` never received a video brief** | It declared `visual: video` but had no `visual_options`, so the selector silently returned `image`. |

Two environment faults were also fixed: a macOS **OpenMP segfault** where
XGBoost and PyTorch each load their own `libomp` (it killed training, the test
suite and API workers with no traceback), and a **character-encoding bug** in
the crawler that turned every em-dash in a client's copy into mojibake.

---

## Known limitations

- The live funnel is currently driven by **simulated visitors**. The machinery
  is real; the audience is not, and the dashboard says so on every figure.
- **Conversion and drop-off models were fitted on a simulator.** They rank
  usefully on a live audience but their thresholds do not transfer.
- **Open rates under-report** — most mail clients block the tracking pixel.
  Click-through is the reliable signal.
- **The engagement dataset carries no text signal.** Not a modelling failure —
  no text feature correlates with engagement (every p > 0.16).
- **`humorous` tone has one training example** and cannot be learned.
- Three real platform datasets ship unused: they are comment-level scrapes and
  pair no post text with post engagement.

---

## Testing

```bash
make test          # Python suites + dashboard build
make test-fast     # Python only, skipping slow tests
```

**159 Python tests**, plus Module 3's own suite, plus a TypeScript build. The
API tests skip rather than fail when PostgreSQL is not running.

---

## Documentation

| | |
|---|---|
| **[docs/VIVA_DEMO.md](docs/VIVA_DEMO.md)** | 10-minute walkthrough and the questions it answers |
| **[docs/RUNNING.md](docs/RUNNING.md)** | Setup, ports, campaigns, analytics, email safety |
| **[modules/m1_segmentation/README.md](modules/m1_segmentation/README.md)** | The segmentation engine and its three corrections |
| **[INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)** | Original integration design and data contracts |
| `/research` on the dashboard | Live data and model provenance |
