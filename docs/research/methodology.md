# RESEARCH METHODOLOGY


## 1.1 What is being studied

This project builds a closed-loop marketing framework for newly launched products, where almost no behavioural history exists. Four modules act on one audience: segmentation, campaign automation, analytics and decision support, and content generation. Each module was developed separately and evaluated on its own; the contribution of this stage of the work is that they now run as one system over a single audience, and that every claim about them is reproducible from one command.


## 1.2 The audience, and what it is made of

The study audience is the **Digital Marketing Campaign** dataset — 8,000 customers with recorded website behaviour, email engagement, purchase history and a conversion outcome. Those customers are imported as the customer base of a demonstration e-commerce store, so that the same audience flows through all four modules exactly as a real one would.

This is the single most important methodological point in the project, and it must be stated before any result is quoted. The dataset is real: real people, whose behaviour was really measured. But it was measured as **per-customer totals** — 25 website visits, 5.5 pages per visit, 9 email opens — and not as an event log. Nobody recorded when visit 14 happened or which page it was.

**Table R1 — What is measured data and what is reconstructed by the importer.**

| Quantity | Status | Source |
|---|---|---|
| Sessions, page views, time on site | Measured | WebsiteVisits, PagesPerVisit, TimeOnSite |
| On-site clicks | Measured | ClickThroughRate × page views |
| Purchases | Measured | PreviousPurchases |
| Email opens and clicks | Measured | EmailOpens, EmailClicks |
| Conversion outcome | Measured | Conversion |
| Acquisition channel | Measured | CampaignChannel |
| Timestamp of each visit | Reconstructed | Spread over a 90-day window, seeded per customer |
| Which page each visit landed on | Reconstructed | Cycled through the store's real pages |
| Scroll depth | Reconstructed | Derived from dwell time |
| Order of email opens and clicks | Reconstructed | Interleaved across the window |
| Basket value of a purchase | Reconstructed | Drawn from the store's catalogue prices |

> **Consequence for the results.** Anything that depends only on the totals — segment membership, conversion rate by segment, funnel counts — rests on real measurements. Anything that depends on event *order* or *timing* — attribution paths, journey length, inter-event gaps — is a property of the reconstruction as much as of the data, and is reported as such throughout Chapter 3.

To keep that distinction in the data rather than only in prose, the importer writes one event per *visit* carrying that visit's totals, instead of one event per page view. A live browser reports one event per page and no count; the feature definition sums the two identically, so a single definition serves both without either pretending to be the other.


## 1.3 Provenance is recorded, never asserted

Imported customers and live browser sessions share one database. Every visitor and every funnel event therefore carries a `source` column with the value `dataset` or `live`, and that value is **derived at write time from the visitor the event belongs to** — it can never be supplied by the caller. A test fails the build if a dataset-derived customer ever produces a row claiming to be live observation.

Every figure in the dashboard carries the resulting label, and the analytics layer refuses to report attribution below five converting journeys rather than returning a number it cannot support.


## 1.4 Reproducibility

All randomness is seeded (seed 42). The importer is deterministic given the source CSV and idempotent on re-run. Confidence intervals use 10,000 bootstrap resamples, and the policy comparison runs 30 independent seeds. `make research` regenerates every table and every figure in this chapter and the two that follow.
