# Viva demonstration — a 10-minute walkthrough

**Team Binary · University of Moratuwa · 2026**

A script for demonstrating the system live, and the questions it is built to
survive.

---

## Before the room

Four terminals, then two commands.

```bash
make db                                    # terminal 1 — PostgreSQL
venv/bin/uvicorn api.main:app --port 8000  # terminal 2 — API
cd web && npm run dev                      # terminal 3 — dashboard
make site                                  # terminal 4 — the demo store

make demo                                  # import 8,000 customers, run every module
make status                                # confirm all four are up
```

Run **`make research`** once before the viva as well (~3.5 minutes). It
regenerates every table and figure in `docs/research/`, so if anyone asks
"where does that number come from?" the answer is one command away.

Open **<http://localhost:3000>** (dashboard) and **<http://localhost:4000>**
(the store) in two tabs.

`make demo` prints the login: **demo@innov8smart.example / demo1234**

> **The system never sends or publishes.** It writes the content and says what
> to do with it.

---

## The walkthrough

### 0 · What you are looking at (1 minute)

> "This is a research build. The audience is the Digital Marketing Campaign
> dataset — 8,000 real customers with recorded behaviour — imported as the
> customer base of this demo store, so that all four modules operate on one
> audience the way they would in production."

Say the honesty point **before** anyone asks, because it is the strongest card
in the demonstration:

> "The dataset is real, but it records per-customer *totals* — 25 visits, 5.5
> pages per visit, 9 email opens — not an event log. So the importer keeps every
> total exactly and reconstructs only what the data never contained: when each
> visit happened and which page it was. Segment membership and conversion rates
> rest on measurements. Attribution path statistics depend partly on my
> reconstruction, and I report them that way."

### 1 · The problem (30 seconds)

> "Marketing tools are fragmented: one for segmentation, one for email, one for
> analytics, one for content. Nothing connects them, and a newly launched
> product has almost no data to work with. This is the four joined into one
> loop, built for exactly that low-data case."

### 2 · A live visitor joins the audience (2 minutes)

Open the store at :4000. Point at the footer badge: `tracking: on · a1b2c3d4`.

Do this while narrating:

| Action | What is recorded |
|---|---|
| Scroll to the bottom | `scroll` at 25 / 50 / 75 / 100% |
| Open a product page | `page_view` with the path |
| **Add to basket** | `add_to_cart` with the SKU and value |
| Enter an email, **tick the consent box**, submit | `form_submit` + `identify` — now a *contactable* customer |
| Basket → **Complete order** | `purchase` — the conversion |

Refresh the dashboard's **Audience** page. The count has gone up by one, and the
badge on the funnel has flipped from `research dataset` to `dataset + live`.

> "That badge is not decoration. Provenance is a column on every visitor and
> every funnel event, and it is derived at write time from the visitor the
> event belongs to — a caller cannot assert it. There is a test that fails the
> build if a dataset-derived customer ever produces a row claiming to be live
> observation."

**Then turn on Do Not Track and reload.** The badge reads
`tracking: off (Do Not Track)` and nothing is collected.

### 3 · The audience is segmented (1 minute)

**Audience** page.

> "8,000 customers, segmented by the hybrid engine — rules, K-Means and
> hierarchical clustering combined by an agreement vote. The confidence column
> is the *agreement level*, not a probability: all three agreeing gives 0.95;
> only the rules deciding gives 0.60."

Point at **New Cold User**:

> "That is the cold-start group. Clustering cannot express 'insufficient
> evidence' — it has to put everyone somewhere — so the rules decide for them
> and they are flagged. That segment converts at 53% against 88% for everyone
> else, so it is the most distinctive group in the data."

### 4 · The Action Plan — what the system produces (2 minutes)

**Action Plan** page.

> "Not a report — a list of jobs. 'Send this email to these 168 High Intent
> contacts.' Subject and body already written. 'Post this on LinkedIn' —
> caption, hashtags and a visual brief, ready to paste."

Point at the reason line under each action, then pick up the **Link to use**:

> "We never send this email and never publish this post. So how is it still
> measured? The tracked link is in the *content*, not the delivery. Whoever puts
> it in the envelope — Mailchimp, Gmail, your own Instagram account — the link
> is ours. Clicking it records the click and forwards the visitor tagged
> `utm_source=instagram`, which the attribution model already understands."

### 5 · Three automation policies, measured (2 minutes)

**Campaigns** page. Point at **conversions per 1,000 sends**, not raw
conversions:

> "Fixed wins on raw conversions because it sends five times as many messages.
> Per-send efficiency is the fair comparison, and the rules column is the
> operational cost — hybrid needs eight decision rules, fixed needs one."

Then the honest part, which is worth volunteering:

> "In the running system hybrid wins at 87.5 conversions per thousand. But in
> the thirty-seed simulation study, *trigger* wins. The two disagree, and the
> reason is that response is modelled differently in each. Neither is an
> observation of people reacting. The ranking is not robust to how you model
> response, and that instability is a result in itself — it is in the report."

### 6 · Attribution disagreeing is the finding (2 minutes)

**Analytics** page, attribution chart.

> "Four models over the same 7,811 converting journeys. First-touch spreads
> credit almost evenly across the acquisition channels — around 20% each.
> Last-touch gives email 89%. The widest pair disagrees over 68% of all
> attributed credit. A company using only last-touch would conclude email is
> everything and cut the spend that created the audience."

Then the diagnostic underneath:

> "It also says 20% of these journeys had a single touchpoint. On those, all
> four models agree by arithmetic, not because they found anything. Reporting
> agreement without that caveat would be misleading."

### 7 · Content written from the store's own pages (1 minute)

**Content** page.

> "The hashtags are lifted from the store's own headings; the copy comes from
> its meta description. We crawled the URL — nothing here was typed by hand."

Point at the platform priority panel:

> "The order comes from the attribution we just looked at. And it says plainly
> that 44% of the attributed credit sits with channels we cannot publish to —
> referral, PPC, SEO. Only the rest can influence what gets written."

### 8 · The Research page and `make research` (2 minutes) — spend real time here

> "This page is generated from the repository and the database as it loads, so
> it cannot drift away from what is actually there."

Then show the terminal:

```bash
make research
```

> "Seven experiments, every headline number with a confidence interval, and the
> figures are redrawn from the results the run just wrote — so a chart cannot
> disagree with the number it plots. The chapters in `docs/research/` are
> generated from the same file. There is one copy of every number in this
> project."

---

## Questions this is built to answer

**"Is this real data or simulated?"**
The customers are real people from a published dataset; their per-customer
totals are real measurements. The *timing and ordering* of their events is a
reconstruction, because the dataset has no event log. Campaign response is
modelled — nobody in this study opened a real email. Every figure carries a
provenance badge, and `source` is derived at write time, never asserted.

**"Does the hybrid segmentation actually beat just using rules?"**
**No — and that is in the report as the headline, not a footnote.** Rules alone
separate conversion by 0.3837; the full hybrid by 0.3838. Clustering alone
reaches 0.069. The hybrid earns its place on different grounds — it produces a
calibrated confidence from three-way agreement, and the vote is what makes cold
start explicit — but it does not separate conversion better than a handful of
interpretable rules. Experiment E1 measures exactly that.

**"Your segmentation confidence is 0.71. What does that mean?"**
Agreement between the three methods, not a probability. All three agreeing gives
0.95; only the rules deciding gives 0.60. All three disagree for 35% of
customers — they disagree more often than they fully agree, and the engine says
so.

**"Why is the silhouette only 0.087?"**
Because the clusters genuinely overlap. The segments are commercially meaningful
— conversion differs by 38 points across them — without being geometrically
tidy. Both facts are reported.

**"Your engagement model has a negative R². Why ship it?"**
It previously reported 0.99, which came entirely from leakage: the target's own
components were left in the feature set. Removed, the honest figure is −0.168
[−0.408, −0.072] and Spearman 0.012 with an interval spanning zero. Then I
tested every text feature against the target — **none** survives Holm–Bonferroni
correction. That is a property of the dataset, not a modelling failure, so the
score's weight was cut from 0.45 to 0.20 and the pathway stays wired for a
dataset that has signal. Finding it is the contribution; hiding it would have
been the failure.

**"You found bugs in your own research. Doesn't that undermine it?"**
The opposite. Both defects made the results look *better*, which is why they
survived review — no test failed, nothing went red. The leak barely moved
accuracy (0.9213 → 0.9200) but inflated certainty 150-fold. The vote-order bug
deleted the cold-start segment, which is Novel Contribution 1, from its own
output. Each fix now has a regression test, and E2 reproduces both with numbers
rather than asserting they were fixed.

**"Why FastAPI when Chapter 3.6 says NestJS?"**
Figure 5.1 specifies FastAPI and every model in the project is Python. The
Ch. 3.6 sentence is an error and should be corrected. The same applies to
MongoDB — all five figures show PostgreSQL, and PostgreSQL is what is used.

**"What would you do next?"**
Three things, in order: run it on a real launch so the funnel measures people
rather than a model; find an engagement dataset that actually has text signal;
and grow the goal/tone corpus, where `humorous` still has one example and cannot
be learned.

---

## If something breaks

| Symptom | Fix |
|---|---|
| Dashboard shows "Cannot reach the API" | `make api` in terminal 2 |
| API exits with no traceback | An OpenMP segfault — check `import openmp_guard` is first in the entry point |
| Content generation fails | Is the store served? `make site` |
| Everything looks empty | `make demo` |
| `/sites` returns `[]` from curl | Correct — the site is owned; sign in, or query the database directly |
| Total reset | `make reset && make db && make demo` |
