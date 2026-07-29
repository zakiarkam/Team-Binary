# -*- coding: utf-8 -*-
"""Chapters 4-6: Approach, Analysis and Design, Implementation.

Figure 1 is in content_a; this file uses Figures 2-29 and Tables 4-14.
Chapter 7 (generated) continues from Figure 30 and Table 15 — the builder
computes those offsets automatically, so inserting a figure here does not
require touching anything else.
"""

A = "/Users/arkamzakir/Documents/Research/Research/report/assets"
S = f"{A}/placeholders"

BLOCKS = [
    # ================================================== CHAPTER 4
    ("h1", "CHAPTER 4 — APPROACH"),

    ("h2", "4.1 Introduction"),
    ("p", "This chapter specifies what each module receives, what it does with "
          "it and what it produces. The four modules are described in the "
          "order in which data flows through them, followed by the integration "
          "strategy that joins them (Section 4.6) and the experimental "
          "strategy that governs how their results are measured and reported "
          "(Section 4.7)."),
    ("p", "The overall methodology is experimental rather than constructive. "
          "Each module implements at least two competing approaches — three "
          "segmentation methods, three automation policies, four attribution "
          "models, two text representations, two targeting paradigms, three "
          "off-policy estimators — so that a comparison, and not merely a "
          "demonstration, is possible. Where a comparison cannot be made "
          "honestly on the project's own audience, the approach is to find "
          "data on which it *can* be made and to state plainly what does and "
          "does not transfer."),

    ("h2", "4.2 Module 1 — Audience Targeting and Personalization"),

    ("h3", "4.2.1 Input"),
    ("p", "Module 1 operates over two feature domains using the same "
          "algorithm. Both are reduced to a common feature matrix before the "
          "engine sees them, which is what allows one implementation to serve "
          "the research audience and a live browser audience without either "
          "being treated as a special case."),
    ("table", {"caption": "Table 4 — The two feature domains of the "
                          "segmentation engine.",
               "header": ["", "Research domain", "Live web domain"],
               "rows": [
                   ["Source", "Digital Marketing Campaign dataset — 8,000 "
                              "customers imported into the demo store",
                    "Browser sessions collected by the mos.js snippet"],
                   ["Features", "email opens and clicks, website visits, pages "
                                "per visit, time on site, social shares, "
                                "previous purchases, loyalty points",
                    "page views, clicks, sessions, unique pages, scroll depth, "
                    "time on site, form submits, purchases"],
                   ["Row shape", "One event per visit, carrying that visit's "
                                 "counts",
                    "One event per page, carrying no count"],
                   ["Reconciled by", "VISITOR_FEATURES_SQL, which sums both "
                                     "identically (§6.2.3)",
                    "The same definition"],
               ]}),

    ("h3", "4.2.2 Process"),
    ("p", "Preprocessing handles missing values, encodes categorical "
          "attributes and standardises numeric features, since both k-means "
          "and Ward-linkage hierarchical clustering are distance-based. "
          "Derived behavioural features — engagement score, click ratio, "
          "recency — are then computed. Three methods run in parallel over "
          "that identical matrix:"),
    ("numbers", [
        "**Rule-based segmentation.** Marketing heuristics expressed as "
        "explicit thresholds. Fully interpretable, and the only one of the "
        "three that can test for the *absence* of history rather than for "
        "proximity to a centroid.",
        "**k-means clustering** with *k* = 4 on scaled features, capturing "
        "behavioural groupings no rule was written for.",
        "**Hierarchical (agglomerative) clustering** with Ward linkage, "
        "providing a second, differently biased partition against which "
        "k-means can be checked.",
    ]),
    ("p", "An **agreement vote** then combines the three labels, and the order "
          "of its branches is the design decision that matters:"),
    ("bullets", [
        "**① All three agree** — the label is taken with the highest "
        "confidence.",
        "**② The rules identify a cold-start customer** — resolved next, "
        "*before* any comparison between the two clusterings. A method that "
        "cannot represent a finding does not get a vote on it.",
        "**③ Two of three agree** — the majority label, medium confidence.",
        "**④ All three disagree** — the rule label is retained at the lowest "
        "confidence, and the confidence value is what tells a downstream "
        "module how much to trust it.",
    ]),
    ("p", "Cluster names are derived from cluster centroids rather than "
          "assigned to cluster indices, so the same code produces correct "
          "names on a new audience and a new random seed. Segments below a "
          "minimum size (30 customers) are reported but excluded from the "
          "separation statistic, and below a minimum audience size the engine "
          "declines to cluster at all and says why. For a launch-stage product "
          "that is the normal condition, not an error."),

    ("h3", "4.2.3 Output"),
    ("p", "For every customer: a segment label from a fixed five-value "
          "taxonomy, the method that produced it, and a calibrated confidence, "
          "written to the shared **user_segments** table."),
    ("table", {"caption": "Table 5 — The five shared audience segments.",
               "header": ["Segment", "Behavioural signature",
                          "Marketing implication"],
               "rows": [
                   ["High Intent", "High click and visit frequency, short "
                                   "recency, strong purchase signals",
                    "Prioritise; expect the fastest conversion"],
                   ["Loyal Customer", "Repeat purchases, high loyalty points, "
                                      "consistent engagement",
                    "Retain; premium and reactivation messaging"],
                   ["Price Sensitive", "High browsing, low conversion relative "
                                       "to visits",
                    "Discount-led messaging; the largest drop-off risk"],
                   ["Low Engagement", "Few opens, few clicks, long recency",
                    "Re-engagement, or suppression to protect deliverability"],
                   ["New Cold User", "Almost no interaction history",
                    "The cold-start case: onboarding, not prediction"],
               ]}),

    ("h2", "4.3 Module 2 — Marketing Automation and Campaign Management"),

    ("h3", "4.3.1 Input"),
    ("p", "Segment labels and confidences from Module 1, joined to each "
          "customer's behavioural profile, together with a library of campaign "
          "message templates (welcome, product information, social proof, "
          "discount offer, final reminder, reactivation)."),

    ("h3", "4.3.2 Process"),
    ("p", "A campaign policy engine selects the next action for each customer. "
          "Three policies are implemented and compared under identical "
          "conditions — the same customers, the same templates, the same "
          "response model — so that any difference in outcome is attributable "
          "to the policy alone. The policy engine is the only component that "
          "differs between the three arms."),
    ("table", {"caption": "Table 6 — The three automation policies compared.",
               "header": ["Policy", "Decision basis", "Expected trade-off"],
               "rows": [
                   ["Fixed workflow", "Predetermined schedule, identical for "
                                      "every customer",
                    "Simple and cheap to operate; no personalisation; sends "
                    "the most messages"],
                   ["Trigger-based", "The customer's most recent observed "
                                     "event selects the next action",
                    "Responsive and message-efficient; stops early; rule count "
                    "grows"],
                   ["Hybrid", "Schedule + triggers + segment label + predicted "
                              "response probability",
                    "Best personalisation; highest operational complexity"],
               ]}),
    ("p", "Response probability is supplied by a supervised model trained on "
          "the campaign dataset. Logistic regression and a random forest are "
          "both fitted, and a stratified dummy classifier is fitted alongside "
          "them as a floor, because the dataset is strongly imbalanced and "
          "accuracy alone would be misleading."),
    ("p", "A response simulation layer converts each campaign action into "
          "interaction events — sent, opened, clicked, ignored, converted — "
          "using segment-level propensities calibrated against the dataset's "
          "own conversion rates. The comparison is run over **30 independent "
          "seeds**, each putting the same 8,000 customers through all three "
          "policies, so the trials are paired and the statistics are paired "
          "accordingly. The same three policies are then run a second time "
          "against the imported audience in the live system, and both results "
          "are reported — including where they disagree."),

    ("h3", "4.3.3 Output"),
    ("p", "A customer-level interaction log written to **interactions**, a "
          "decision record written to **action_log**, and a policy comparison "
          "table reporting conversions per thousand sends, messages per "
          "customer and decision-rule count for each policy."),

    ("h2", "4.4 Module 3 — Marketing Analytics and Decision Support"),

    ("h3", "4.4.1 Input"),
    ("p", "The interaction log from Module 2, the segment labels from Module 1 "
          "and the propensity-logged decision record. For the controlled "
          "attribution experiment a simulator is used whose per-channel "
          "influence weights are known — the property that makes ground-truth "
          "scoring possible at all. For the targeting experiment the Hillstrom "
          "MineThatData dataset is used, because it is randomised and the "
          "project's own audience is not."),

    ("h3", "4.4.2 Process"),
    ("p", "Processing proceeds along five tracks over a common journey-level "
          "feature matrix."),
    ("p", "**Funnel construction and drop-off analysis.** Journeys are "
          "assembled into the canonical sequence sent → opened → clicked → "
          "converted, and transition rates are computed overall and "
          "disaggregated by segment, channel and policy, so a loss can be "
          "localised to a stage of a specific audience under a specific "
          "policy."),
    ("p", "**Attribution modelling.** Four models assign conversion credit "
          "across the touchpoints of each converting journey."),
    ("table", {"caption": "Table 7 — Attribution models implemented in "
                          "Module 3.",
               "header": ["Model", "Credit rule", "Known weakness"],
               "rows": [
                   ["First-touch", "All credit to the first touchpoint",
                    "Ignores everything that closed the sale"],
                   ["Last-touch", "All credit to the final touchpoint",
                    "Ignores everything that created the audience"],
                   ["Linear", "Credit divided equally across touchpoints",
                    "Assumes every touch contributed equally"],
                   ["Markov (removal effect)", "Credit from the drop in "
                    "conversion probability when a channel is removed",
                    "Needs substantial journey volume to be stable"],
               ]}),
    ("p", "Where journeys are simulated, the true credit distribution is known "
          "by construction and each model is scored by mean absolute error "
          "against it. Where they are not — on the imported audience — no such "
          "column exists, so the module reports **pairwise disagreement** "
          "instead of accuracy. Reporting accuracy there would require a "
          "ground truth that does not exist."),
    ("p", "**Predictive modelling.** A journey-level feature matrix (counts of "
          "sends, opens and clicks; recency; journey length; average "
          "inter-event time; first and last channel; segment; policy) is used "
          "to fit logistic regression, random forest and XGBoost models for "
          "conversion probability and drop-off risk, each compared against a "
          "stratified baseline with bootstrap intervals. Applying them to the "
          "imported audience is treated explicitly as a transfer across "
          "distributions: the ranking is usable, the absolute probabilities "
          "are not calibrated for it, and the report says so."),
    ("p", "**Uplift modelling.** Ranking customers by predicted conversion "
          "answers *who is most likely to convert*. A campaign needs to know "
          "*for whom does contacting them change the outcome*. S-learner and "
          "T-learner uplift models are fitted and compared against the "
          "predicted-response policy and a random baseline using Qini curves. "
          "This is done on Hillstrom's randomised data because uplift is "
          "identifiable only where assignment was randomised — and the report "
          "declines to compute it on the project's own audience, where no "
          "action was ever randomised."),
    ("p", "**Off-policy evaluation.** The system records every decision, the "
          "action taken, **the probability it was taken under**, and what "
          "followed. Inverse-propensity, self-normalised and doubly-robust "
          "estimators are validated against a known answer in simulation, "
          "including the effect of the exploration rate. Ten per cent of "
          "decisions are randomised on purpose, because a deterministic policy "
          "assigns probability zero to every action it does not take and "
          "nothing can be learned from a denominator of zero."),
    ("p", "A refusal guard sits across the module: attribution is not reported "
          "below five converting journeys, and degenerate prediction "
          "distributions raise a calibration warning rather than a confident "
          "answer."),

    ("h3", "4.4.3 Output"),
    ("p", "Per-customer predicted conversion probability, drop-off risk, "
          "channel and platform credit, a recommended action and platform, "
          "written to **analytics_output**; an append-only **action_log**; a "
          "set of funnel, attribution, prediction, uplift and estimator "
          "figures; and a system-level insight summary consumed by Module 2 "
          "for campaign optimisation and Module 4 for platform priority."),

    ("h2", "4.5 Module 4 — AI Content Refinery and Multi-Platform "
           "Distribution"),

    ("h3", "4.5.1 Input"),
    ("p", "The client's own website, crawled to extract page copy, headings "
          "and product descriptions into a business summary and brand "
          "vocabulary; a labelled corpus for campaign-goal and tone "
          "classification; and platform priority supplied by Module 3's "
          "attribution output."),

    ("h3", "4.5.2 Process"),
    ("p", "**Capability detection** runs first. The crawler reads the site and "
          "decides what the business can actually do, as independent flags "
          "rather than as a single category — a charity that sells merchandise "
          "has both donation and commerce; a publisher running a store has "
          "commerce as well as content."),
    ("table", {"caption": "Table 8 — Detected site capabilities and the "
                          "actions each unlocks.",
               "header": ["Capability", "Evidence sought",
                          "Actions it makes available"],
               "rows": [
                   ["commerce", "Basket, checkout and product paths, price "
                                "markup",
                    "Abandoned-basket recovery, product promotion, discount "
                    "offer"],
                   ["subscription", "Pricing tiers, plan or trial paths",
                    "Trial nudge, upgrade prompt, renewal reminder"],
                   ["lead_capture", "Contact, demo or quote forms",
                    "Lead-nurture sequence, demo invitation"],
                   ["donation", "Donate paths, appeal or campaign pages",
                    "Appeal message, recurring-gift prompt"],
               ]}),
    ("p", "This matters for two reasons. Recommending *drive to checkout* to a "
          "site with no checkout is an error the marketer sees immediately and "
          "which destroys trust in every other recommendation. And because the "
          "action set determines how thinly the exploration budget is spread, "
          "the catalogue must stay as small as honestly covers what the site "
          "can do — a cost Section 7.3.10 measures directly."),
    ("p", "The campaign goal (awareness, conversion, engagement, lead "
          "generation, retention) and tone (professional, persuasive, "
          "friendly, luxury, emotional) are then classified from the source "
          "text. Two representations are compared for both targets — TF-IDF "
          "with logistic regression, and Sentence-BERT embeddings with XGBoost "
          "— and the better model per target is selected on held-out "
          "performance using a test appropriate to two classifiers on one test "
          "set, rather than assumed."),
    ("p", "A platform-aware generation engine then produces, for each target "
          "platform, a caption, hashtags, a call to action, an image prompt "
          "and — where the platform supports it — a short-video brief, "
          "respecting that platform's length, formality and format "
          "conventions. Every asset is scored on three axes and ranked by a "
          "weighted composite."),
    ("table", {"caption": "Table 9 — Content scoring components and their "
                          "weights.",
               "header": ["Component", "Method", "Weight", "Rationale"],
               "rows": [
                   ["Semantic similarity", "Sentence-BERT cosine similarity "
                    "between source summary and generated asset", "0.40",
                    "Guards against the model inventing claims the business "
                    "does not make"],
                   ["Platform suitability", "Rule-based check of length, "
                    "hashtag count, emoji use and structure", "0.40",
                    "Deterministic, auditable and platform-specific"],
                   ["Predicted engagement", "XGBoost regressor over text "
                    "features", "0.20",
                    "Reduced from an originally intended 0.45 after the model "
                    "was shown to have no demonstrable skill (§7.3.7)"],
               ]}),
    ("p", "A human-baseline harness scores manually written marketing copy "
          "through the identical pipeline, so that AI-generated assets are "
          "compared with human assets on the same scale rather than against an "
          "assertion."),

    ("h3", "4.5.3 Output"),
    ("p", "Ranked, platform-ready marketing assets written to "
          "**content_assets**, ordered by platform according to Module 3's "
          "measured attribution credit, and restricted to actions the site is "
          "capable of performing."),

    ("h2", "4.6 Integration Strategy"),
    ("p", "Integration is achieved through a shared relational data layer "
          "rather than through direct calls between modules. Each module reads "
          "the tables it needs and writes the tables it owns, which keeps the "
          "modules independently testable and replaceable while still allowing "
          "the loop to close."),
    ("p", "The loop runs as follows. The imported audience and any live "
          "sessions populate **visitors** and raw events. Module 1 writes "
          "**user_segments**. Module 2 reads segments and writes "
          "**interactions** and **action_log**. Module 3 reads all three and "
          "writes **analytics_output**. Module 4 reads analytics output for "
          "platform priority, writes **content_assets**, and supplies the "
          "capability set that constrains what Module 3 may recommend. Module "
          "2's next cycle reads both analytics output and the highest-scoring "
          "content asset."),
    ("p", "Four integration properties were treated as requirements rather "
          "than conveniences."),
    ("bullets", [
        "**Isolation.** Every site-scoped route is filtered by ownership in "
        "one place, so one account can never read another's audience.",
        "**Provenance.** Every visitor and every event records whether it came "
        "from the dataset or from live observation, and that value is derived "
        "at write time rather than supplied by the caller.",
        "**Evaluability.** Every decision is written with the probability it "
        "was taken under. Without it the system's own history cannot be used "
        "to assess a change to the policy.",
        "**Degradation.** When a module has insufficient data it must decline "
        "and explain, not guess — the normal condition at launch.",
    ]),

    ("h2", "4.7 Experimental Strategy"),
    ("p", "Evaluation operates at two levels: module-level, where each "
          "module's competing approaches are compared on their own metrics; "
          "and system-level, where the integration itself is examined. Eleven "
          "experiments implement this, and the whole apparatus runs from one "
          "command."),
    ("figure", {"path": f"{A}/fig03_research_pipeline.png",
                "caption": "Figure 2 — The research pipeline. Experiments "
                           "write tables; the statistics layer computes "
                           "intervals; figures are drawn from the tables and "
                           "the chapter is generated from the results file, so "
                           "no number in Chapter 7 is copied by hand.",
                "width": 6.3}),
    ("p", "Five principles govern the experiments and are applied "
          "consistently in Chapter 7."),
    ("numbers", [
        "**Compare, do not merely demonstrate.** Every module reports at least "
        "two competing approaches under identical conditions, plus a naive "
        "baseline — a dummy classifier, a mean predictor, a majority-class "
        "floor or random targeting — so the reader can see the floor as well "
        "as the ceiling.",
        "**Report the interval, not just the point.** All uncertainty is "
        "quantified by percentile bootstrap with 10,000 resamples, because the "
        "quantities involved — separation, silhouette, macro-F1, Qini — are "
        "not means and have no closed-form standard error.",
        "**Pair what is paired.** The policy comparison puts the same 8,000 "
        "customers through all three policies on each of thirty seeds, so "
        "paired tests are used; treating the runs as independent would "
        "overstate the p-value and waste power.",
        "**Prefer the metric that survives the data's shape.** Conversions per "
        "thousand sends rather than conversion rate; macro-F1 rather than "
        "accuracy; Spearman rather than R² for a ranking model; effect size "
        "beside every p-value.",
        "**Report negative results as findings.** A model with no demonstrable "
        "skill, a hybrid that does not beat its own components, and a policy "
        "ranking that does not survive a change of simulator are all reported "
        "as headlines rather than removed.",
    ]),

    ("h2", "4.8 Summary"),
    ("p", "The approach specifies four modules exchanging data through a "
          "shared relational layer, each implementing competing methods so "
          "that comparison is possible, and an experimental strategy designed "
          "to resist the failure modes most likely to affect a project of this "
          "kind: leakage from features that encode the target, optimism from "
          "evaluating on the data that generated the model, and the temptation "
          "to quote whichever of two disagreeing runs is more flattering. "
          "Chapter 5 converts this approach into a concrete architecture."),

    # ================================================== CHAPTER 5
    ("h1", "CHAPTER 5 — ANALYSIS AND DESIGN"),

    ("h2", "5.1 Introduction"),
    ("p", "This chapter presents the architecture of the delivered system: the "
          "overall layered design (Section 5.2), the internal architecture of "
          "each module (Section 5.3), the shared database (Section 5.4), the "
          "design decisions taken specifically to protect research integrity "
          "(Section 5.5) and the multi-tenant design (Section 5.6)."),

    ("h2", "5.2 High-Level Architecture of the Overall System"),
    ("p", "The system is organised into four layers, shown in Figure 3. "
          "Separation is strict: the presentation layer holds no marketing "
          "logic, the research modules hold no HTTP concerns, and all "
          "cross-module communication passes through the data layer."),
    ("figure", {"path": f"{A}/fig02_architecture.png",
                "caption": "Figure 3 — High-level layered architecture of the "
                           "orchestration platform.", "width": 6.4}),
    ("p", "**Presentation layer.** A Next.js dashboard with seven pages "
          "(Overview, Plan, Audience, Campaigns, Analytics, Content and "
          "Research) plus authentication and site-onboarding flows. "
          "Separately, the demonstration e-commerce store carries the mos.js "
          "snippet; its visitors are part of the audience and never interact "
          "with the dashboard."),
    ("p", "**Application layer.** A FastAPI service exposing site-scoped "
          "routers for segments, campaigns, analytics, content, actions and "
          "decisions; public tracking endpoints requiring no authentication, "
          "because a website's visitors are not signed in to anything; an "
          "ownership middleware enforcing tenant isolation in a single place; "
          "a decision service that holds the action catalogue and writes every "
          "decision with its propensity; and a provenance service that reports "
          "at request time which data is dataset-derived and which is live."),
    ("p", "**Research module layer.** The four modules as importable Python "
          "packages. Because the API is itself Python, the module that "
          "produced a reported research number is the same object the API "
          "loads at run time; there is no re-implementation gap between the "
          "experiment and the running system."),
    ("p", "**Data layer.** A single PostgreSQL database whose principal tables "
          "carry the names specified in the interim report's architecture "
          "figures, with **action_log** added after the interim stage as a "
          "direct consequence of experiments E8 and E9."),

    ("h2", "5.3 High-Level Architectures of Individual Modules"),

    ("h3", "5.3.1 Module 1 — Audience Targeting and Personalization"),
    ("p", "Figure 4 shows the segmentation engine. The three methods are peers "
          "rather than a pipeline: each produces a complete labelling of the "
          "audience, and the agreement vote arbitrates. The confidence score "
          "is a first-class output, because a downstream module needs to know "
          "not only which segment a customer is in but how much to trust it."),
    ("figure", {"path": f"{A}/fig05_module1.png",
                "caption": "Figure 4 — Architecture of the hybrid segmentation "
                           "engine. The numbered branches of the agreement "
                           "vote are evaluated in that order, and the ordering "
                           "is the contribution.", "width": 6.1}),
    ("p", "Two design points are load-bearing. The cold-start branch is "
          "resolved before any clustering comparison, so a genuinely new "
          "customer cannot be absorbed into an established cluster. And the "
          "minimum-audience threshold causes the engine to decline clustering "
          "outright, returning interpretable rule-based labels with an "
          "explicit explanation rather than an unstable partition presented as "
          "a result."),

    ("h3", "5.3.2 Module 2 — Marketing Automation and Campaign Management"),
    ("p", "Figure 5 shows the campaign engine. The policy engine is the single "
          "point at which the three policies differ; profile builder, response "
          "model, templates, response simulation and evaluation are all "
          "shared. That is what makes the comparison in Section 7.3.3 a "
          "controlled one."),
    ("figure", {"path": f"{A}/fig06_module2.png",
                "caption": "Figure 5 — Architecture of the campaign automation "
                           "engine, annotated with the measured outcome and "
                           "cost of each policy.", "width": 6.1}),

    ("h3", "5.3.3 Module 3 — Marketing Analytics and Decision Support"),
    ("p", "Figure 6 shows the analytics module. Five analytical tracks feed "
          "two predictive models and a shared explainability and validation "
          "stage, which in turn feed the recommendation generator. The "
          "exploration component and the refusal guard sit between the "
          "generator and the published output."),
    ("figure", {"path": f"{A}/fig07_module3.png",
                "caption": "Figure 6 — Architecture of the analytics and "
                           "decision support module, including the uplift and "
                           "off-policy evaluation tracks added after the "
                           "interim stage.", "width": 6.4}),
    ("p", "The refusal guard is drawn as a distinct component because it is "
          "one: it can suppress a result entirely. Below five converting "
          "journeys attribution returns no numbers and states why, and a "
          "prediction distribution that has collapsed to a constant raises a "
          "calibration warning rather than being presented as a confident "
          "forecast. The exploration component is equally deliberate — it "
          "spends a measurable fraction of achievable reward in order to keep "
          "the decision record informative, and Section 7.3.9 quotes that "
          "price rather than presenting exploration as free."),

    ("h3", "5.3.4 Module 4 — AI Content Refinery and Multi-Platform "
           "Distribution"),
    ("p", "Figure 7 shows the content refinery. Two arrows into it are the "
          "integration points the literature review found missing: platform "
          "generation order is set by measured attribution credit rather than "
          "assumption, and the action catalogue is constrained by what the "
          "site is detected to be capable of."),
    ("figure", {"path": f"{A}/fig08_module4.png",
                "caption": "Figure 7 — Architecture of the AI content "
                           "refinery, including capability detection and the "
                           "scoring weights justified in Chapter 7.",
                "width": 6.1}),

    ("h2", "5.4 Database Design"),
    ("p", "Figure 8 shows the schema. The design follows the interim report's "
          "table naming so that the delivered system can be read directly "
          "against the architecture figures approved at that stage, with two "
          "additions: `visitors.source` replaces the pair of boolean flags "
          "used earlier, and `action_log` is new."),
    ("figure", {"path": f"{A}/fig09_schema.png",
                "caption": "Figure 8 — Shared database schema. Provenance is "
                           "derived at write time; the propensity column is "
                           "mandatory.", "width": 6.4}),
    ("table", {"caption": "Table 10 — Principal database tables and their "
                          "owning module.",
               "header": ["Table", "Written by", "Read by", "Key content"],
               "rows": [
                   ["users, sessions", "Auth service", "All routes",
                    "Accounts, scrypt password hashes, database-row sessions"],
                   ["sites", "Onboarding, Module 4",
                    "All site-scoped routes",
                    "Registered site, owner, write key, detected capabilities"],
                   ["visitors", "Importer, tracking endpoint", "Modules 1, 3",
                    "Anonymous identity, source ('dataset' | 'live')"],
                   ["user_segments", "Module 1", "Modules 2, 3, 4",
                    "Segment name, method, calibrated confidence"],
                   ["interactions", "Module 2, tracking", "Module 3",
                    "Event type, channel, platform, source (derived)"],
                   ["action_log", "Decision service", "Module 3",
                    "Action, propensity, exploration flag, reward"],
                   ["analytics_output", "Module 3",
                    "Modules 2, 4, dashboard",
                    "Conversion probability, drop-off risk, credits, "
                    "recommendation"],
                   ["content_assets", "Module 4", "Module 2, dashboard",
                    "Caption, hashtags, CTA, component and composite scores"],
               ]}),

    ("h2", "5.5 Design for Research Integrity"),
    ("p", "The largest risk to a project of this kind is not that a model "
          "performs poorly but that a reader — or the team itself — mistakes a "
          "reconstructed or simulated result for a measured one. Four "
          "mechanisms were designed into the system rather than documented as "
          "conventions."),
    ("p", "**Provenance is derived, not asserted.** Every visitor and every "
          "interaction carries a `source` column whose value is computed when "
          "the row is written, from the visitor the row belongs to. A caller "
          "cannot declare its own data live. An automated test fails the build "
          "if a dataset-derived customer ever produces a row claiming live "
          "observation."),
    ("p", "**Measured and reconstructed are separated at the point of "
          "import.** The importer preserves every total from the source "
          "dataset exactly and reconstructs only what the dataset never "
          "contained. Section 6.2.2 states which is which, and Chapter 7 "
          "repeats the distinction wherever a result depends on it."),
    ("p", "**The evaluation chapter is generated, not written.** Chapter 7's "
          "prose is authored once in `research/chapters.py` with the numbers "
          "interpolated from the results file, so a figure cannot drift away "
          "from the value it plots and a number cannot be quietly rounded in "
          "the report but not in the code."),
    ("p", "**The system declines to report what it cannot support.** The "
          "refusal thresholds are enforced in code, and every dashboard figure "
          "carries a provenance badge derived from the rows behind it."),

    ("h2", "5.6 Multi-Tenant Design"),
    ("p", "Although the study operates on one demonstration store, the "
          "platform is designed so that any organisation could register a "
          "website and receive its own segmentation, campaigns, analytics and "
          "content. This required the security design to be part of the "
          "architecture rather than an afterthought."),
    ("bullets", [
        "**One isolation point.** All site-scoped routes pass through a single "
        "ownership middleware. A request for a site owned by another account "
        "returns 404 rather than 403, so the response does not confirm that "
        "the site exists. A regression test registers two accounts and asserts "
        "the isolation.",
        "**Sessions are database rows.** Signing out deletes the row, so the "
        "token dies immediately rather than remaining valid until expiry. "
        "Passwords are hashed with salted scrypt.",
        "**The browser never holds the token.** The dashboard receives an "
        "HttpOnly cookie set on its own origin, so client-side script cannot "
        "read it.",
        "**Public routes stay public.** The tracking endpoints require no "
        "authentication, because a website's visitors are not signed in to the "
        "platform and must not be asked to be.",
    ]),

    ("h2", "5.7 Summary"),
    ("p", "The design is a four-layer architecture in which the research "
          "modules are ordinary Python packages behind an API, joined by a "
          "single relational store whose provenance column is derived rather "
          "than declared and whose decision log makes the system's own policy "
          "evaluable. The next chapter describes how this design was "
          "implemented, including the defects discovered in the process."),

    # ================================================== CHAPTER 6
    ("h1", "CHAPTER 6 — IMPLEMENTATION"),

    ("h2", "6.1 Introduction"),
    ("p", "This chapter describes the implementation of the framework: the "
          "data it is built on (Section 6.2), the site under study "
          "(Section 6.3), each module in turn (Section 6.4), the integrated "
          "platform (Section 6.5), the research infrastructure (Section 6.6), "
          "the defects found in the project's own research code (Section 6.7) "
          "and the testing arrangements (Section 6.8)."),

    ("h2", "6.2 Data Collection"),

    ("h3", "6.2.1 Datasets"),
    ("p", "Six data sources are used. Their provenance determines the strength "
          "of every claim built on them, so it is stated explicitly here and "
          "repeated in Chapter 7 wherever it matters."),
    ("table", {"caption": "Table 11 — Data sources, with size, nature and "
                          "role.",
               "header": ["Source", "Size", "Nature", "Used by"],
               "rows": [
                   ["Digital Marketing Campaign dataset",
                    "8,000 customers", "Real, per-customer totals",
                    "The study audience — Modules 1–4; E1, E2, E3"],
                   ["Hillstrom MineThatData",
                    "64,000 customers, 3 randomised arms",
                    "Real, randomised assignment",
                    "E8 — the only causal claim in the report"],
                   ["Social-media engagement corpus",
                    "12,000 posts", "Real (public)",
                    "Module 4 engagement regressor — E7"],
                   ["Campaign goal / tone corpus",
                    "527 labelled rows", "Real, semi-automatically labelled",
                    "Module 4 text classifiers — E6"],
                   ["Capability website sample",
                    "15 real websites, hand-labelled", "Real, fetched live",
                    "Module 4 capability detection — E10"],
                   ["Module 2 and Module 3 simulators",
                    "8,000 customers × 30 seeds; known-reward worlds",
                    "Simulated, calibrated",
                    "E3; E4 ground truth; E5, E9, E11"],
               ]}),
    ("note", "**Why simulation appears at all.** Three claims in this report "
             "are properties of an estimator rather than of customers — that "
             "attribution recovers known influence, that an off-policy "
             "estimator is unbiased, and how error scales with action-set "
             "size. Each is decided by mathematics and can therefore be "
             "checked exactly against a known answer, which no real dataset "
             "permits. Where a claim concerns people rather than estimators, "
             "real data is used."),

    ("h3", "6.2.2 The importer, and what it does not invent"),
    ("p", "The study audience is imported by "
          "`scripts/import_research_audience.py`, which turns 8,000 dataset "
          "rows into customers of the demonstration store. The dataset is "
          "real, but it was measured as **per-customer totals** — 25 website "
          "visits, 5.5 pages per visit, 9 email opens — and not as an event "
          "log. Nobody recorded when visit 14 happened or which page it was."),
    ("figure", {"path": f"{A}/fig04_importer.png",
                "caption": "Figure 9 — What the importer preserves and what it "
                           "reconstructs. The distinction is kept in the data, "
                           "not only in prose.", "width": 6.3}),
    ("p", "The importer therefore preserves every total exactly and "
          "reconstructs only what the dataset never contained: the timestamp "
          "of each visit, which page it landed on, scroll depth, the ordering "
          "of email events and basket value. Fidelity is asserted against the "
          "source CSV after every import — sessions, page views, time on site, "
          "clicks and purchases all match exactly, and a re-import is "
          "byte-identical — so a reconstruction error cannot pass silently."),
    ("figure", {"path": f"{S}/shot_code_importer.png",
                "caption": "Figure 10 — The fidelity check in the importer. "
                           "Totals are asserted against the source CSV after "
                           "import.", "width": 6.0}),
    ("note", "**Consequence for every result in Chapter 7.** Anything "
             "depending only on the totals — segment membership, conversion "
             "rate by segment, funnel counts — rests on real measurements. "
             "Anything depending on event *order* or *timing* — attribution "
             "paths, journey length, inter-event gaps — is a property of the "
             "reconstruction as much as of the data. Chapter 7 says which is "
             "which every time it matters."),

    ("h3", "6.2.3 One feature definition for two kinds of row"),
    ("p", "A live browser writes one event per page view and carries no count; "
          "the importer writes one event per *visit* carrying that visit's "
          "counts. Rather than maintain two feature paths — which would "
          "eventually diverge — a single SQL definition sums both identically, "
          "treating a missing count as one. Imported and live customers are "
          "therefore described by the same features without either pretending "
          "to be the other."),
    ("figure", {"path": f"{S}/shot_code_features.png",
                "caption": "Figure 11 — The shared feature definition. One "
                           "expression serves imported per-visit counts and "
                           "live per-page events.", "width": 6.0}),

    ("h2", "6.3 The Site Under Study"),
    ("p", "The demonstration store is a small e-commerce site with six product "
          "pages, a basket and a checkout path, served on port 4000 with the "
          "mos.js snippet installed. It is the site Module 4 crawls, the site "
          "whose capabilities are detected, and the site whose visitors form "
          "the live half of the audience."),
    ("figure", {"path": f"{S}/shot_store_home.png",
                "caption": "Figure 12 — The demonstration e-commerce store, "
                           "home page.", "width": 6.0}),
    ("figure", {"path": f"{S}/shot_store_product.png",
                "caption": "Figure 13 — A product page with the tracking "
                           "status indicator, confirming first-party event "
                           "collection.", "width": 6.0}),
    ("p", "Browsing the store during a demonstration changes the provenance "
          "badge throughout the dashboard from *research dataset* to "
          "*dataset + live*, which is the most direct way to show that the "
          "provenance mechanism is real rather than a label."),

    ("h2", "6.4 Implementation of Individual Modules"),

    ("h3", "6.4.1 Module 1 — Audience Targeting and Personalization"),
    ("p", "The engine is implemented in `modules/m1_segmentation/segment.py` "
          "as a feature-set-agnostic function with two callers, one for the "
          "research audience and one for live visitors. Preprocessing uses "
          "`StandardScaler`; clustering uses `KMeans` (k = 4, `n_init` = 10, "
          "fixed random state) and `AgglomerativeClustering` with Ward "
          "linkage. Cluster naming is derived at run time by ranking centroids "
          "on engagement and purchase dimensions."),
    ("figure", {"path": f"{S}/shot_code_vote.png",
                "caption": "Figure 14 — The agreement vote. Cold start is "
                           "resolved immediately after unanimity, before the "
                           "clustering comparison.", "width": 6.0}),
    ("p", "The confidence score is produced by a classifier trained on the "
          "vote outcome with the vote's own encoded label excluded from the "
          "feature set. Section 6.7 explains why that exclusion is not "
          "optional, and Section 7.3.2 measures what it changes."),

    ("h3", "6.4.2 Module 2 — Marketing Automation and Campaign Management"),
    ("p", "Module 2 is implemented under `modules/m2_automation/src/` with the "
          "three policies in a `strategies/` package behind a common "
          "interface, so that the simulator and evaluator are identical across "
          "policies. `ml_model.py` fits the response models; `simulator.py` "
          "generates events; `evaluation.py` computes the comparison metrics."),
    ("figure", {"path": f"{S}/shot_code_policy.png",
                "caption": "Figure 15 — The policy engine. The three policies "
                           "share every other component of the comparison.",
                "width": 6.0}),
    ("p", "A stratified dummy classifier is fitted alongside the real models "
          "and reported in the same table, because the dataset's base rate is "
          "high enough that a model can look accurate by predicting the "
          "majority class for every customer. Publishing the dummy result "
          "beside the real one makes that floor visible."),

    ("h3", "6.4.3 Module 3 — Marketing Analytics and Decision Support"),
    ("p", "Module 3 is implemented under `modules/m3_analytics/src/` as "
          "co-operating components run end to end by `pipeline.py`."),
    ("table", {"caption": "Table 12 — Components of the Module 3 analytics "
                          "pipeline.",
               "header": ["Component", "Responsibility"],
               "rows": [
                   ["simulator.py", "Generate journeys with known channel "
                                    "influence for ground-truth scoring"],
                   ["funnel.py", "Funnel construction and drop-off by stage, "
                                 "segment and policy"],
                   ["attribution.py", "First-, last-, linear and Markov credit "
                                      "assignment"],
                   ["features.py", "Journey-level feature matrix shared by "
                                   "both predictive models"],
                   ["prediction.py", "Conversion and drop-off models against a "
                                     "stratified baseline"],
                   ["calibration.py", "Probability calibration and "
                                      "degenerate-prediction warnings"],
                   ["bootstrap.py", "Percentile and paired bootstrap "
                                    "intervals"],
                   ["shap_analysis.py", "SHAP feature attribution for both "
                                        "models"],
                   ["recommender.py / learned_recommender.py",
                    "Rule-based and supervised recommendation generation"],
               ]}),
    ("figure", {"path": f"{S}/shot_code_attribution.png",
                "caption": "Figure 16 — The attribution engine. Four models "
                           "over the same journeys.", "width": 6.0}),
    ("p", "The decision service is the part of Module 3 that changed most "
          "after the interim stage. Every recommendation is now written to an "
          "append-only log together with the probability it was taken under, "
          "and ten per cent of decisions are drawn at random on purpose. "
          "Without that, the log records only what the current policy already "
          "believes, and no alternative policy can be evaluated from it."),
    ("figure", {"path": f"{S}/shot_code_propensity.png",
                "caption": "Figure 17 — Logging a decision with its "
                           "propensity, and the deliberate exploration branch.",
                "width": 6.0}),

    ("h3", "6.4.4 Module 4 — AI Content Refinery"),
    ("p", "The crawler (`crawler.py`) fetches and cleans the site; the "
          "capability detector reads whole path segments and host labels "
          "rather than substrings, for reasons Section 7.3.10 explains; "
          "`knowledge_base.py` builds the business summary; `goal_tone.py` "
          "trains and selects the classifiers; `generator.py` produces "
          "platform-specific assets; `evaluation.py` computes semantic "
          "similarity and platform suitability; `engagement.py` provides the "
          "engagement regressor; and `human_baseline.py` scores human-written "
          "copy through the same pipeline."),
    ("figure", {"path": f"{S}/shot_code_goal_tone.png",
                "caption": "Figure 18 — Model selection in goal_tone.py. Both "
                           "representations are trained on the same split and "
                           "compared, not assumed.", "width": 6.0}),
    ("p", "The engagement regressor is trained with an explicit leakage guard: "
          "the outcome components from which the target is derived are "
          "excluded from the feature set by name. The guard iterates a sorted "
          "sequence rather than a set, because an unordered iteration made "
          "column order depend on the process hash seed and the reported score "
          "wobble between runs — a reproducibility defect described in "
          "Section 6.7."),

    ("h2", "6.5 Integrated Platform Implementation"),
    ("p", "The FastAPI application exposes routers over the four modules, with "
          "module logic wrapped in a `services/` layer so that HTTP concerns "
          "never leak into research code. The database schema lives in "
          "`api/schema.sql`; the tracking snippet is served from "
          "`api/static/mos.js`. Tenant isolation is implemented as a single "
          "middleware covering every site-scoped route rather than a check "
          "repeated in each handler — an isolation check that must be "
          "remembered in twenty places will eventually be forgotten in one."),
    ("figure", {"path": f"{S}/shot_login.png",
                "caption": "Figure 19 — Account creation, website registration "
                           "and the snippet installation check.",
                "width": 6.0}),
    ("p", "The dashboard is a Next.js application with seven authenticated "
          "pages. Every figure it renders carries a provenance badge derived "
          "from the rows behind it, so a reader can never mistake a "
          "dataset-derived chart for measured live behaviour."),
    ("figure", {"path": f"{S}/shot_dash_overview.png",
                "caption": "Figure 20 — Dashboard, Overview page.",
                "width": 6.0}),
    ("figure", {"path": f"{S}/shot_dash_audience.png",
                "caption": "Figure 21 — Dashboard, Audience page: the five "
                           "segments with sizes, conversion rates and "
                           "calibrated confidence.", "width": 6.0}),
    ("figure", {"path": f"{S}/shot_dash_campaigns.png",
                "caption": "Figure 22 — Dashboard, Campaigns page: the three "
                           "policies and their measured efficiency.",
                "width": 6.0}),
    ("figure", {"path": f"{S}/shot_dash_analytics.png",
                "caption": "Figure 23 — Dashboard, Analytics page: funnel, "
                           "drop-off by segment and the four attribution "
                           "models side by side.", "width": 6.0}),
    ("figure", {"path": f"{S}/shot_dash_content.png",
                "caption": "Figure 24 — Dashboard, Content page: generated "
                           "assets with their component scores.",
                "width": 6.0}),
    ("figure", {"path": f"{S}/shot_dash_plan.png",
                "caption": "Figure 25 — Dashboard, Action Plan: who to "
                           "contact, with what, on which platform, and why.",
                "width": 6.0}),
    ("figure", {"path": f"{S}/shot_dash_research.png",
                "caption": "Figure 26 — Dashboard, Research page. Generated at "
                           "request time from disk and database, so it cannot "
                           "drift from the system it describes.",
                "width": 6.0}),
    ("p", "The whole system is reproducible from a clean checkout: `make "
          "setup` provisions dependencies, `make db` starts PostgreSQL, "
          "`make api`, `make web` and `make site` start the services, and "
          "`make demo` imports the audience and runs every module end to end."),

    ("h2", "6.6 Research Infrastructure"),
    ("p", "The experimental apparatus lives in `research/` and is the part of "
          "the implementation that makes Chapter 7 possible. Eleven "
          "experiments in `research/experiments/` each write their own CSV "
          "tables; `stats.py` provides the percentile bootstrap, the paired "
          "bootstrap with Wilcoxon signed-rank, exact McNemar, Wilson "
          "intervals and Cliff's delta; `figures.py` draws every figure from "
          "those tables; and `chapters.py` authors the prose once and renders "
          "it both to Markdown and into this report with the values "
          "interpolated."),
    ("figure", {"path": f"{S}/shot_code_experiment.png",
                "caption": "Figure 27 — An experiment. Each writes its own "
                           "tables; nothing is copied into the report by hand.",
                "width": 6.0}),
    ("p", "A single command runs the lot. All randomness is seeded, confidence "
          "intervals use 10,000 bootstrap resamples and the policy comparison "
          "runs 30 independent seeds."),
    ("figure", {"path": f"{S}/shot_make_research.png",
                "caption": "Figure 28 — `make research` completing all eleven "
                           "experiments and regenerating every table, figure "
                           "and chapter in Chapter 7.", "width": 6.0}),
    ("p", "One implementation detail is worth recording because it caused a "
          "real defect. Module 2 and Module 3 both ship a top-level package "
          "named `src`, so importing them in the same process is ambiguous; "
          "`module_loader.py` exists to load each by explicit path rather than "
          "letting import order decide which one wins."),

    ("h2", "6.7 Defects Identified and Corrected in the Research Code"),
    ("p", "Converting the interim-stage notebooks into a running system, and "
          "then subjecting that system to its own experiments, exposed a "
          "series of defects in the project's own code. Each had produced "
          "results that looked good and were not valid. They are reported here "
          "in full because the corrected figures are the ones used throughout "
          "Chapter 7, and because the pattern they form — every one of them "
          "inflated a result, and none produced an error — is itself a "
          "finding."),
    ("table", {"caption": "Table 13 — Defects found in the research code, "
                          "their effect and the correction applied.",
               "header": ["#", "Defect", "Effect on reported results",
                          "Correction"],
               "rows": [
                   ["D1", "Module 1's confidence classifier was trained with "
                          "the rule label among its inputs while the target "
                          "was the hybrid consensus.",
                    "Certainty inflated by a factor of 150 — 450 customers at "
                    "confidence 1.00 against 3 — while accuracy moved by "
                    "0.0013 (§7.3.2).",
                    "Rule label removed from the feature set; the honest "
                    "accuracy and its interval reported instead."],
                   ["D2", "In the agreement vote, the clustering comparison "
                          "was evaluated before the cold-start rule.",
                    "The cold-start segment lost 36 of 163 customers on the "
                    "dataset and went to zero on the live audience — the "
                    "module's novel contribution erased by its own pipeline.",
                    "Cold start resolved immediately after unanimity, with a "
                    "regression test."],
                   ["D3", "Cluster names were hardcoded to cluster indices.",
                    "Names were correct for one dataset and one random seed, "
                    "and arbitrary for any other audience.",
                    "Names derived from cluster centroids at run time."],
                   ["D4", "Module 4's engagement regressor retained the "
                          "outcome components from which its target was "
                          "derived.",
                    "R² of 0.9901 was entirely leakage; the corrected value is "
                    "−0.168 (§7.3.7).",
                    "Leakage guard by feature name; the model's weight in "
                    "content scoring reduced from 0.45 to 0.20."],
                   ["D5", "The goal/tone corpus required a row to clear the "
                          "confidence threshold for both targets, although the "
                          "two classifiers train independently.",
                    "The usable corpus was reduced from 527 rows to 114.",
                    "Per-target filtering, restoring the full corpus."],
                   ["D6", "The `shorts` platform declared a video visual type "
                          "but defined no visual options.",
                    "The selector silently returned a static image brief.",
                    "Visual options defined; the selector asserts the declared "
                    "type is satisfiable."],
                   ["D7", "The engagement leakage guard iterated a Python "
                          "`set`, so column order depended on the process hash "
                          "seed.",
                    "The reported R² wobbled between 0.9898 and 0.99 across "
                    "processes — a result that could not be reproduced "
                    "exactly.",
                    "Sorted iteration, with a subprocess test that varies "
                    "PYTHONHASHSEED."],
               ]}),
    ("p", "Two environment faults were also diagnosed and fixed. The first was "
          "a macOS **OpenMP conflict**: XGBoost and PyTorch each bundle their "
          "own `libomp`, and fitting or predicting with XGBoost while PyTorch "
          "was loaded terminated the process with exit code 139 and no "
          "traceback, killing training runs, the test suite and API workers. "
          "Only constraining OpenMP to a single thread resolved it, and a "
          "guard module is imported first in every entry point. The second was "
          "a **character-encoding fault** in the crawler: the HTTP library "
          "defaults to ISO-8859-1 for `text/html` when the response header "
          "omits a charset, which corrupted every non-ASCII character in a "
          "client's marketing copy before it reached the content generator."),
    ("note", "The defects share a signature: each made a result better than it "
             "truly was, and none produced an error message. D1 is the "
             "sharpest case — it barely moved accuracy while multiplying "
             "certainty by 150, so every test stayed green and the only "
             "symptom was a confidence column that looked impressive. That is "
             "why the integrity mechanisms of Section 5.5 were designed into "
             "the system rather than left as good intentions."),

    ("h2", "6.8 Testing and Reproducibility"),
    ("p", "The automated suite comprises **260 collected tests** across the "
          "platform, Module 3 and the research layer, covering data contracts, "
          "API behaviour, tracking, segmentation, campaign actions, the action "
          "catalogue, decision logging, content generation, authentication, "
          "tenant isolation, the research importer, the statistics functions "
          "and the experiments themselves."),
    ("figure", {"path": f"{S}/shot_make_test.png",
                "caption": "Figure 29 — The test suite passing.",
                "width": 6.0}),
    ("table", {"caption": "Table 14 — What the structural tests protect.",
               "header": ["Test", "Property protected"],
               "rows": [
                   ["Provenance guard",
                    "A dataset-derived customer can never produce a row "
                    "claiming live observation."],
                   ["Import fidelity",
                    "Every preserved total matches the source CSV, and a "
                    "re-import is byte-identical."],
                   ["Numeric serialisation walk",
                    "Every API response returns numbers as numbers; "
                    "PostgreSQL NUMERIC values reached the dashboard as JSON "
                    "strings twice before this test existed."],
                   ["Two-account isolation",
                    "One account probing another's site receives 404, not "
                    "403."],
                   ["Hash-seed reproducibility",
                    "A subprocess run under a different PYTHONHASHSEED "
                    "produces the same engagement result (defect D7)."],
                   ["One regression test per defect",
                    "Each row of Table 13 has a test that fails if the defect "
                    "returns."],
               ]}),

    ("h2", "6.9 Summary"),
    ("p", "All four modules are implemented, integrated behind a single API "
          "over a shared PostgreSQL database, exercised by 260 automated tests "
          "and reproducible from a clean checkout with a small number of "
          "commands. Seven defects in the research code were identified and "
          "corrected, each with a regression test, and the corrected figures "
          "are the ones evaluated in Chapter 7."),
]
