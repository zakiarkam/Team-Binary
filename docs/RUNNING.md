# Running the system

**Team Binary · University of Moratuwa · 2026**

The production stack follows Figure 5.1 of the report:

```
  Client website  ──mos.js──▶  FastAPI backend  ──▶  PostgreSQL
                                    │                    ▲
  Next.js dashboard ──REST──────────┤                    │
                                    ▼                    │
                        AI modules M1 · M2 · M3 · M4 ─────┘
```

---

## One-time setup

```bash
# 1. Python environment (already exists as venv/)
source venv/bin/activate
pip install -r requirements.txt          # research modules (M1–M4)
pip install -r api/requirements.txt      # FastAPI backend

# 2. Configuration
cp .env.example .env                     # edit if you need non-default ports

# 3. Dashboard dependencies
cd web && npm install && cd ..
```

## Every time you work

Four processes. Use four terminals.

```bash
# ── Terminal 1 — PostgreSQL ──────────────────────────────────────────────
docker-compose up -d          # note: this machine has compose v1 ("docker-compose")
docker-compose logs -f db     # optional

# ── Terminal 2 — FastAPI backend ─────────────────────────────────────────
venv/bin/uvicorn api.main:app --reload --port 8000
#   API docs:   http://localhost:8000/docs
#   Health:     http://localhost:8000/health

# ── Terminal 3 — Next.js dashboard ───────────────────────────────────────
cd web && npm run dev
#   Dashboard:  http://localhost:3000

# ── Terminal 4 — the demo client website ─────────────────────────────────
python3 -m http.server 4000 --directory demo-site
#   Demo site:  http://localhost:4000
```

Stop the database with `docker-compose down` (data is kept) or
`docker-compose down -v` (data is **deleted**).

---

### PostgreSQL: two supported paths

`make db` starts a Homebrew `postgresql@16` service if one is installed and
falls back to Docker otherwise. Both listen on **5434**, so nothing else in the
project changes.

```bash
# Homebrew (fewer moving parts — recommended before a demo)
brew install postgresql@16
# set `port = 5434` in /opt/homebrew/var/postgresql@16/postgresql.conf
make db          # starts the service
make db-create   # once: creates the `mos` role and `marketing_os` database

# Docker
make db-docker
```

Homebrew is the default because Docker adds a virtual machine and an image
store between you and the database. A corrupted Docker image store took this
project's database down once; the Homebrew path has one moving part and
rebuilds the whole demo in about a minute either way.

`make reset` drops and recreates the database on the Homebrew path, or removes
the volume on the Docker one.

---

## Ports

| Service | Port | Why |
|---|---|---|
| PostgreSQL | **5434** | 5432 and 5433 were already taken on this machine |
| FastAPI | 8000 | |
| Next.js dashboard | 3000 | |
| Demo client website | 4000 | A **separate origin**, so tracking is genuinely cross-origin — exactly as a real customer's site would be |

Change them in `.env` if they clash.

---

## Verifying it works

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"up","email_delivery":"dry_run","version":"0.2.0"}

venv/bin/pytest tests/test_api_foundation.py -v   # backend + schema tests
venv/bin/pytest tests/ -q                          # full M4 + integration suite
cd modules/m3_analytics && ../../venv/bin/pytest tests/ -q   # M3 research suite
```

The API tests **skip** rather than fail when PostgreSQL is not running, so the
research suite still passes on a machine without Docker.

---

## The audience

The study audience is the **Digital Marketing Campaign** dataset — 8,000
customers — imported as the customer base of the demo store. `make demo` does
the whole thing; the steps below are what it runs.

**What is measured and what is reconstructed** is set out in
[research/methodology.md](research/methodology.md) and in the importer's own
docstring. In short: every per-customer total in the dataset is preserved
exactly; the timing, page paths and ordering of events are reconstructed,
because the dataset contains no event log.

```bash
# Register the store and inject its site key into every page
venv/bin/python scripts/setup_demo_site.py

# Import the 8,000 customers (deterministic, idempotent)
venv/bin/python scripts/import_research_audience.py --site-id 1

# A quicker subset while developing
venv/bin/python scripts/import_research_audience.py --site-id 1 --limit 500

# Remove them again, leaving live visitors untouched
venv/bin/python scripts/import_research_audience.py --site-id 1 --clear
```

Imported customers get an address in the reserved `.invalid` TLD, so even with
SMTP configured they are unreachable by construction.

### Registering a different website

The system is not tied to the demo store — any site can be registered and its
visitors become the audience.

```bash
curl -X POST http://localhost:8000/sites \
  -H 'Content-Type: application/json' \
  -d '{"name":"Innov8Smart","url":"https://innov8smart.com",
       "product_name":"Innov8Smart",
       "description":"Digital innovation and smart technology solutions",
       "target_audience":"SMEs adopting smart technology"}'
```

The response contains the snippet to paste into the site's `<head>`:

```html
<script defer src="http://localhost:8000/mos.js" data-site="mos_XXXXXXXX"></script>
```

- `site_key` (in the snippet) is **public** — it only permits writing events.
- `ingest_secret` is **private**, returned once, and is for server-to-server use.

### The demo store (for the viva)

`demo-site/` is a small e-commerce store with the snippet installed — an
online shop, because the dataset's customers have purchases and loyalty points
and a subscription product could not honestly own that behaviour. One command
registers it and injects the right site key into every page:

```bash
venv/bin/python scripts/setup_demo_site.py
python3 -m http.server 4000 --directory demo-site
```

Then open <http://localhost:4000> and behave like a visitor:

| Do this | Event recorded |
|---|---|
| Land on the page | `page_view` (plus `utm_*` if the URL has them) |
| Scroll down | `scroll` at 25 / 50 / 75 / 100 % |
| Click any link or button | `click` with its label |
| Submit the form | `form_submit` + `identify` |
| Tick the consent box first | the visitor also becomes **contactable** |
| Add a device to the basket | `add_to_cart` with SKU and value |
| Complete the order on `/cart.html` | `purchase` — the conversion goal |
| Leave the page | `page_exit` with seconds on page |

The footer badge shows the live tracking state. Turn on **Do Not Track** in your
browser and reload: the badge flips to *off* and nothing is collected — the
tracker honours DNT by design.

Watch the data arrive:

```bash
curl -s http://localhost:8000/sites/1/audience/summary | python3 -m json.tool
```

### What the tracker does and does not collect

| Collected | Never collected |
|---|---|
| Page paths, referrer, UTM parameters | Keystrokes |
| Clicks (element label / href) | Form field values — except a field explicitly marked `data-mos-email` |
| Scroll depth, seconds on page | Cross-site browsing history |
| Device class, language, screen size | Third-party cookies (none are set) |

Email consent is separate from analytics: a visitor can be tracked and still not
be contactable. Only ticking the `data-mos-consent` box sets `email_consent`.

---

## Running campaigns

```bash
# 1. Segment the audience (Module 1)
curl -X POST http://localhost:8000/sites/1/segment

# 2. See who may lawfully be emailed
curl -s http://localhost:8000/sites/1/audience/reachable | python3 -m json.tool

# 3. Compare all three automation policies on that audience (Module 2)
venv/bin/python scripts/run_strategy_comparison.py --site-id 1 --reset \
    --respond --limit 400
```

Typical output — note how few visitors are actually contactable:

```
Audience: 122 visitors · 15 contactable
  100 anonymous · 6 known but not opted in · 1 unsubscribed

strategy   recip  sent  open  click  conv     CTR  conv/1k  rules  basis
fixed         15    75    44     16     6   21.3%     80.0      1  simulated
trigger       15    15     8      6     3   40.0%    200.0      4  simulated
hybrid        15    15    11      4     1   26.7%     66.7      8  simulated
```

`rules` is the operational-complexity metric: how many distinct decision rules
each policy needs. `basis` says whether the numbers came from real people or
from simulated traffic.

### `--respond` and what it means

Imported customers are records, not people, and cannot be made to open an email
on cue. With `--respond` each recipient's reaction is drawn from **their own
recorded behaviour** — the EmailOpens, EmailClicks and ConversionRate the
dataset holds for that specific person — rather than one rate applied to
everybody. Those events travel through the *real* tracking endpoints, so:

- `interactions.source` is **derived** from the visitor it belongs to, never
  asserted by the caller;
- every report labels such a campaign `basis: dataset`;
- a test (`test_dataset_visitors_never_produce_live_funnel_events`) fails the
  build if a dataset-derived customer ever produces a row marked live.

This makes the comparison *between* policies meaningful, because the same
audience with the same per-person propensities goes through all three. It does
not make the absolute open and click rates measurements — the base levels are
parameters of the response model. Without the flag, the funnel only ever fills
from genuine interaction with the live store.

---

## The dashboard

<http://localhost:3000> — Next.js + React + Recharts, the stack named in
Chapter 3 of the report.

| Page | Shows |
|---|---|
| **Overview** | Health, audience, funnel, best strategy, latest content |
| **Audience** | Visitors, segments, cold-start share, and *why* most visitors cannot be emailed |
| **Campaigns** | Fixed vs trigger vs hybrid — efficiency against operational complexity |
| **Analytics** | Funnel, drop-off, four attribution models side by side, next-best action per visitor |
| **Content** | Generated assets with their four scores, and which platforms to write for |
| **Research** | Auto-generated data/model provenance and the honest limitations |

### Two things the UI does on purpose

**Every figure carries a data-basis badge** — `research dataset`,
`live traffic` or `dataset + live`. Imported customers go through the same write
paths as a live browser, so a screenshot would otherwise be indistinguishable
from one taken over live traffic. The badge is driven by `interactions.source`,
which is derived from the visitor the event belongs to at write time rather than
asserted by the caller.

**Numbers that need a caveat carry one, next to the number.** Open rate is shown
beside the note that mail clients block tracking pixels; strategy comparison is
ranked by conversions per 1,000 sends rather than raw conversions, with the
decision-rule count beside it; attribution shows what share of journeys had only
a single touchpoint.

### The Research page

`/research` is generated from the repository and the database as you load it —
row counts are read from disk, so it cannot drift out of date the way a
hand-written table in a report can. It reports which dataset trained which
model, whether that data is real or simulated, and for every model both the
headline number and what it actually means.

It also lists the three real platform datasets that ship with the project and
which **no code reads** — visible rather than quietly omitted.

---

## Content (Module 4)

```bash
# Read the client's website
curl -X POST "http://localhost:8000/sites/1/crawl?force=true" | python3 -m json.tool

# Generate, score and store platform content from what it says
curl -X POST http://localhost:8000/sites/1/content/generate \
     -H 'Content-Type: application/json' -d '{"engine":"fast"}'
```

The URL used to be collected and never opened — copy was written from the typed
brief alone. Now the flow is:

```
crawl the site → meta description + headings become the brief
               → per-platform assets (Module 4)
               → scored: engagement · semantic · platform fit
               → stored in content_assets   (report Figure 5.5)
               → the best email asset becomes the campaign's copy
```

Crawls are cached in `site_crawls` for 24 hours — marketing copy changes far
more slowly than campaigns are generated, and re-fetching every time would be
rude to the client's server.

**If the site cannot be read**, generation falls back to the typed brief and
says so (`content_source: "brief"`). An unreachable website must not take the
campaign down with it.

### The closed loop, both directions

| Direction | Mechanism |
|---|---|
| analytics → content | Platform *order* comes from Module 3's linear multi-touch attribution, so channels that actually earn conversions are written for first |
| content → campaigns | The highest-scoring email asset becomes the opening message of the next campaign, and the send records which `content_asset_id` it used |

`/sites/{id}/content/priorities` splits the ranking into **actionable** and
**unactionable** channels. Attribution credits `direct`, `google` and
`newsletter` — but this system cannot publish to an acquisition channel, so only
part of the attributed credit can influence what gets written. Reporting a
ranking that quietly drops the rest would overstate how much feedback actually
reaches content.

---

## Analytics (Module 3)

```bash
curl -X POST http://localhost:8000/sites/1/analytics/run | python3 -m json.tool
```

One pass produces the funnel, all four attribution models, per-visitor
predictions, and plain-language insights. Predictions are written to
`analytics_output` (report Figure 5.4), which is what Modules 2 and 4 read to
close the loop.

### Why the journey joins two data sources

Attribution needs multi-platform journeys. Email on its own is a *single*
platform, and every attribution model gives an identical answer on a
single-platform journey — an agreement that looks like robustness but is pure
arithmetic. So each journey is assembled from:

| Source | Contributes |
|---|---|
| `visitors` (from `mos.js`) | the **acquisition touch** — LinkedIn, Google, newsletter, direct … |
| `interactions` (from email tracking) | sends, opens, clicks, conversions |
| `events` | on-site purchases with no preceding campaign click |

The four models then disagree in a way that is actually informative:

```
first_touch  newsletter 32% · direct 26% · instagram 21% · linkedin 11%
last_touch   email 88%      · linkedin 13%
linear       newsletter 24% · direct 21% · email 18% · instagram 18%
markov       email 34%      · newsletter 16% · instagram 15% · google 14%
```

Single-touch models point at opposite ends of the same journey — that
disagreement *is* the finding your report argues for.

### What the service refuses to do

- **Attribution below 5 converting journeys** returns no numbers, with the
  reason stated. Attribution over two journeys is noise dressed as a finding.
- **Journey diagnostics are always returned** (`single_touch_share`,
  `mean_distinct_touchpoints`), so a reader can see how much structure the
  models actually had.
- **Degenerate predictions raise a calibration warning.** The shipped
  conversion/drop-off models were fitted on Module 3's *simulator*; applying
  them to a live audience is a transfer across distributions. They still rank
  usefully, but the thresholds do not carry over — and the service says so:

  > No visitor reaches the 60% drop-off risk threshold (highest is 50.1%). The
  > threshold was set for the distribution the model was fitted on and does not
  > transfer; rank visitors instead of thresholding them.

- **Every result declares `data_basis`** — `real`, `simulated` or `mixed`.

---

## Email safety

Outbound email is **dry-run by default**: with `SMTP_HOST` empty in `.env`,
messages are composed, tracked and recorded exactly as normal but never handed
to a mail server. Fill in the SMTP settings to go live.

| Protection | Where it is enforced |
|---|---|
| Nobody is emailable without explicit opt-in | `visitors.email_consent NOT NULL DEFAULT FALSE`, and the consent filter lives inside `eligible_recipients()`'s SQL so no caller can skip it |
| Consent re-checked at send time | `deliver_due_sends()` — someone may unsubscribe between scheduling and delivery |
| Unsubscribing cancels queued mail | `/unsubscribe/{token}` sets every remaining `scheduled` send to `skipped` |
| One-click unsubscribe in every message | `compose()` builds it into the HTML *and* the plain-text part, plus `List-Unsubscribe` headers (RFC 8058) |
| No open redirect | Tracked links are `/track/click/{token}/{index}`; the destination is looked up server-side from the message's own link list, never taken from the URL |
| Repeat opens not double counted | Mail clients re-fetch the pixel on preview; only the first is recorded |

### How the funnel becomes real data

```
deliver_due_sends()      → interactions: sent
/track/open/{t}.gif      → interactions: open      (pixel fetched by mail client)
/track/click/{t}/{i}     → interactions: click     (then 302 to the real page)
purchase event on site   → interactions: convert   (last-touch, 7-day window)
/unsubscribe/{t}         → interactions: unsubscribe + consent revoked
```

The conversion step is what closes the loop: a `purchase` arriving from `mos.js`
is matched back to that visitor's most recent tracked click, so the campaign is
credited only when it actually caused the sale. A purchase with no preceding
click is left unattributed — it is real, but it is not the campaign's to claim.

**Open rates under-report.** Most mail clients block remote images by default,
so a missing `open` does not mean the message went unread. Click-through is the
reliable engagement signal, and every metrics response carries that caveat.

---

## Reproducing the research

```bash
make research                          # all seven experiments, ~3.5 minutes
venv/bin/python -m research.run_all --only E1,E4
venv/bin/python -m research.run_all --no-figures
venv/bin/python -m research.chapters   # regenerate docs/research/*.md
```

Results land in `research/results/` (one CSV per table plus `results.json`) and
figures in `research/figures/`. The figures are drawn from those tables rather
than plotted by hand, and the chapters interpolate their numbers from the same
JSON — so a chart, a chapter and the experiment behind them cannot disagree.

A partial run (`--only`) merges into the existing `results.json` rather than
replacing it, so it cannot silently delete the experiments it did not rerun.

---

## The legacy Streamlit app

`app_unified/` (Streamlit) still works and remains the fastest way to run the
research pipeline end-to-end:

```bash
venv/bin/streamlit run app_unified/Home.py
```

It is being superseded by the Next.js dashboard, which is the architecture the
report specifies. Both read the same modules.
