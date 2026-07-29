# -*- coding: utf-8 -*-
"""Chapters 4-6: Approach, Analysis and Design, Implementation."""

A = "/Users/arkamzakir/Documents/Research/Research/report/assets"

BLOCKS = [
    # ================================================== CHAPTER 4
    ("h1", "CHAPTER 4 — APPROACH"),

    ("h2", "4.1 Introduction"),
    ("p", "This chapter specifies what each module receives, what it does "
          "with it and what it produces. The four modules are described in "
          "the order in which data flows through them, followed by the "
          "integration strategy that joins them (Section 4.6) and the "
          "evaluation strategy that governs how their results are measured "
          "and reported (Section 4.7)."),
    ("p", "The overall methodology is experimental rather than purely "
          "constructive. Each module implements at least two competing "
          "approaches — for example three segmentation methods, three "
          "automation strategies, five attribution models, two text "
          "representations — so that a comparison, and not merely a "
          "demonstration, is possible."),

    ("h2", "4.2 Module 1 — Audience Targeting and Personalization"),

    ("h3", "4.2.1 Input"),
    ("p", "Module 1 operates over two distinct feature domains, using the "
          "same algorithm in both."),
    ("table", {"caption": "Table 4 — The two feature domains of the "
                          "segmentation engine.",
               "header": ["", "Research domain", "Live web domain"],
               "rows": [
                   ["Source", "Digital Marketing Campaign dataset "
                              "(8,000 users, 20 columns)",
                    "Visitors collected by the mos.js tracking snippet"],
                   ["Features", "email opens, email clicks, website visits, "
                                "pages per visit, time on site, social "
                                "shares, previous purchases, loyalty points",
                    "page views, clicks, sessions, unique pages, scroll "
                    "depth, time on site, form submits, purchases"],
                   ["Purpose", "Reproduce and evaluate the study",
                    "Operate the product on a real audience"],
               ]}),
    ("p", "The two domains are kept separate deliberately. A first-time "
          "visitor to a newly launched product has no email history at all, "
          "so forcing web visitors into the research schema would require "
          "inventing values for columns that do not yet exist — which is "
          "precisely the cold-start distortion this project sets out to "
          "study."),

    ("h3", "4.2.2 Process"),
    ("p", "Preprocessing handles missing values, encodes categorical "
          "attributes and standardises numeric features, since both K-Means "
          "and Ward-linkage hierarchical clustering are distance-based. "
          "Derived behavioural features — engagement score, click ratio, "
          "recency — are then computed."),
    ("p", "Three segmentation methods run in parallel over the identical "
          "feature matrix:"),
    ("numbers", [
        "**Rule-based segmentation.** Marketing heuristics expressed as "
        "explicit thresholds. Fully interpretable, and the only method that "
        "can identify a genuinely new user, because it can test for the "
        "*absence* of history rather than for proximity to a centroid.",
        "**K-Means clustering** with *k* = 4 on scaled features, capturing "
        "behavioural groupings that no rule was written for.",
        "**Hierarchical (agglomerative) clustering** with Ward linkage, "
        "providing a second, differently biased partition against which "
        "K-Means can be checked.",
    ]),
    ("p", "An **agreement vote** then combines the three labels. Where all "
          "three agree, confidence is highest; where two agree, the majority "
          "label is taken with reduced confidence; where all three disagree, "
          "the rule-based label is retained and confidence is lowest. One "
          "rule overrides the vote entirely: if the rule-based method "
          "identifies a **New Cold User**, that label stands regardless of "
          "what the clustering methods report. Section 6.6 explains why this "
          "precedence is not optional."),
    ("p", "Cluster names are derived from cluster centroids rather than "
          "assigned to cluster indices, so that the same code produces "
          "correct names on a new audience and a new random seed. Below a "
          "minimum audience size (30 visitors) the engine does not cluster "
          "at all; it returns rule-based labels and states the reason. For "
          "a launch-stage product this is the normal condition, not an "
          "error."),

    ("h3", "4.2.3 Output"),
    ("p", "For every user, a segment label drawn from a fixed five-value "
          "taxonomy, the method that produced it and a confidence score, "
          "written to the shared **user_segments** table."),
    ("table", {"caption": "Table 5 — The five shared audience segments.",
               "header": ["Segment", "Behavioural signature",
                          "Marketing implication"],
               "rows": [
                   ["High Intent", "High click and visit frequency, short "
                                   "recency, strong purchase signals",
                    "Prioritise; send offers, expect fastest conversion"],
                   ["Loyal Customer", "Repeat purchases, high loyalty "
                                      "points, consistent engagement",
                    "Retain; premium and reactivation messaging"],
                   ["Price Sensitive", "High browsing, low conversion rate "
                                       "relative to visits",
                    "Discount-led messaging; the largest drop-off risk"],
                   ["Low Engagement", "Few opens, few clicks, long recency",
                    "Re-engagement or suppression to protect deliverability"],
                   ["New Cold User", "Almost no interaction history",
                    "The cold-start case: onboarding, not prediction"],
               ]}),

    ("h2", "4.3 Module 2 — Marketing Automation and Campaign Management"),

    ("h3", "4.3.1 Input"),
    ("p", "Segment labels and confidences from Module 1, joined to each "
          "user's behavioural profile, together with a library of campaign "
          "message templates (welcome, product information, social proof, "
          "discount offer, final reminder, reactivation)."),

    ("h3", "4.3.2 Process"),
    ("p", "A campaign policy engine selects the next action for each user. "
          "Three policies are implemented and compared under identical "
          "conditions — the same users, the same templates, the same "
          "response model — so that any difference in outcome is "
          "attributable to the policy alone."),
    ("table", {"caption": "Table 6 — The three automation strategies "
                          "compared.",
               "header": ["Strategy", "Decision basis", "Expected trade-off"],
               "rows": [
                   ["Fixed workflow", "Predetermined schedule, identical for "
                                      "every user",
                    "Simple and cheap to operate; no personalisation"],
                   ["Trigger-based", "The user's most recent observed event "
                                     "selects the next action",
                    "Responsive and message-efficient; rule count grows"],
                   ["Hybrid", "Schedule + triggers + segment label + "
                              "predicted response probability",
                    "Best personalisation; highest operational complexity"],
               ]}),
    ("p", "Response probability is supplied by a supervised model trained on "
          "the campaign dataset. Logistic regression and a random forest are "
          "both fitted, and a stratified dummy classifier is fitted "
          "alongside them as a floor, because the dataset is strongly "
          "imbalanced (base rate 0.876) and accuracy alone would be "
          "misleading."),
    ("p", "An event simulation layer converts each campaign action into "
          "realistic interaction events — sent, opened, clicked, ignored, "
          "converted — with per-segment response propensities, and an "
          "evaluation layer computes open rate, click-through rate, "
          "conversion rate, conversions per thousand messages, average "
          "days-to-convert and an operational complexity score derived from "
          "the number of distinct rules and branches each strategy requires."),

    ("h3", "4.3.3 Output"),
    ("p", "A user-level campaign interaction log written to the shared "
          "**interactions** table — the principal input to Module 3 — and a "
          "strategy comparison table reporting the six metrics above for "
          "each strategy."),

    ("h2", "4.4 Module 3 — Marketing Analytics and Decision Support"),

    ("h3", "4.4.1 Input"),
    ("p", "The campaign interaction log from Module 2 and the segment labels "
          "from Module 1. For the controlled experiments a calibrated "
          "behavioural simulator is used, whose per-channel influence "
          "weights are known — the property that makes ground-truth "
          "attribution scoring possible."),

    ("h3", "4.4.2 Process"),
    ("p", "Processing proceeds along four tracks that share a common feature "
          "matrix."),
    ("p", "**Funnel construction and drop-off analysis.** Journeys are "
          "assembled into the canonical sequence sent → opened → clicked → "
          "converted, and transition and drop-off rates are computed overall "
          "and disaggregated by segment, by channel and by automation "
          "strategy, so that a loss can be localised to a specific stage of "
          "a specific audience under a specific policy."),
    ("p", "**Attribution modelling.** Five models assign conversion credit "
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
                   ["Multi-touch (weighted)", "Position- and "
                    "sequence-weighted credit across touchpoints",
                    "Weighting scheme must be chosen"],
                   ["Markov (removal effect)", "Credit from the drop in "
                    "conversion probability when a channel is removed",
                    "Needs substantial journey volume to be stable"],
               ]}),
    ("p", "Because the simulator generates each journey from known "
          "per-channel influence weights, the true credit distribution is "
          "available, and each model is scored by mean absolute error "
          "against it — a comparison that observational marketing data "
          "cannot support."),
    ("p", "**Predictive modelling.** A journey-level feature matrix "
          "(counts of sends, opens and clicks; recency; journey length; "
          "average inter-event time; first and last channel; segment; "
          "strategy) is used to fit logistic regression, random forest and "
          "XGBoost models for two targets: conversion probability and "
          "drop-off risk. Models are compared by AUC with five-fold "
          "cross-validation, calibrated, explained with SHAP, and — "
          "critically — validated a second time on a real-world dataset "
          "(UCI Bank Marketing) so that simulator optimism can be "
          "quantified rather than assumed away."),
    ("p", "**Recommendation generation.** Predictions are converted into "
          "actions: retarget high-intent users, reactivate dormant "
          "segments, escalate to a premium offer, or send a general "
          "reminder — each naming the audience, the action and the "
          "recommended platform. Two recommenders are implemented: an "
          "explicit rule engine and a supervised recommender trained to "
          "reproduce and improve on it, so that the value added by learning "
          "can be measured."),
    ("p", "A refusal guard sits across the module. Attribution is not "
          "reported below five converting journeys; degenerate predictions "
          "raise calibration warnings instead of confident output; and every "
          "attribution result is accompanied by journey diagnostics."),

    ("h3", "4.4.3 Output"),
    ("p", "Per-user predicted conversion probability, drop-off risk, channel "
          "and platform credit distributions, a recommended action and a "
          "recommended platform, written to **analytics_output**; a set of "
          "funnel, attribution and model-evaluation figures; and a "
          "system-level insight summary. This output is consumed by Module 2 "
          "for campaign optimisation and by Module 4 for platform "
          "prioritisation."),

    ("h2", "4.5 Module 4 — AI Content Refinery and Multi-Platform "
           "Distribution"),

    ("h3", "4.5.1 Input"),
    ("p", "The client's own website, crawled to extract page copy, headings "
          "and product descriptions into a business summary and brand "
          "vocabulary; a labelled corpus for campaign-goal and tone "
          "classification; and platform priority supplied by Module 3's "
          "attribution output."),

    ("h3", "4.5.2 Process"),
    ("p", "The campaign goal (awareness, conversion, engagement, lead "
          "generation, retention) and the tone (professional, persuasive, "
          "friendly, luxury, emotional) are classified from the source text. "
          "Two representations are compared for both targets: TF-IDF with "
          "logistic regression, and Sentence-BERT embeddings with XGBoost. "
          "The better model per target is selected on held-out performance "
          "rather than assumed."),
    ("p", "A platform-aware generation engine then produces, for each target "
          "platform, a caption, hashtags, a call to action, an image prompt "
          "and — where the platform supports it — a short-video brief, "
          "respecting that platform's length, formality and format "
          "conventions."),
    ("p", "Every generated asset is scored on three axes and ranked by a "
          "weighted composite."),
    ("table", {"caption": "Table 8 — Content scoring components and their "
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
                    "Reduced from an originally intended 0.45 after the "
                    "model was shown to have no demonstrable skill (§6.6)"],
               ]}),
    ("p", "A human-baseline harness scores manually written marketing copy "
          "through the identical pipeline, so that AI-generated assets are "
          "compared with human assets on the same scale rather than "
          "against an assertion."),

    ("h3", "4.5.3 Output"),
    ("p", "Ranked, platform-ready marketing assets written to "
          "**content_assets**, ordered by platform according to Module 3's "
          "measured attribution credit, and surfaced to the marketer as part "
          "of an action plan."),

    ("h2", "4.6 Integration Strategy"),
    ("p", "Integration is achieved through a shared relational data layer "
          "rather than through direct calls between modules. Each module "
          "reads the tables it needs and writes the tables it owns, which "
          "keeps the modules independently testable and independently "
          "replaceable while still allowing the loop to close."),
    ("p", "The loop runs as follows. Visitor behaviour collected by the "
          "tracking snippet populates **visitors** and raw events. Module 1 "
          "writes **user_segments**. Module 2 reads segments and writes "
          "**interactions**. Module 3 reads interactions and segments, and "
          "writes **analytics_output**. Module 4 reads analytics output for "
          "platform priority and writes **content_assets**. Module 2's next "
          "cycle reads both analytics output and the highest-scoring content "
          "asset. The cycle then repeats with the outcome of the previous "
          "campaign as an input."),
    ("p", "Three integration properties were treated as requirements rather "
          "than conveniences. **Isolation**: because the platform is "
          "multi-tenant, every site-scoped route is filtered by ownership in "
          "one place, so one company can never read another's audience. "
          "**Provenance**: every row records whether it originated from real "
          "or synthetic traffic, and that flag is derived at write time "
          "rather than asserted by the caller. **Degradation**: when a "
          "module has insufficient data it must decline and explain, not "
          "guess — the normal condition at launch."),

    ("h2", "4.7 Evaluation Strategy"),
    ("p", "Evaluation operates at two levels: module-level, where each "
          "module's competing approaches are compared on their own metrics; "
          "and system-level, where the integration itself is examined."),
    ("p", "Four principles govern the evaluation and are applied "
          "consistently in Chapter 7."),
    ("numbers", [
        "**Compare, do not merely demonstrate.** Every module reports at "
        "least two competing approaches under identical conditions, plus a "
        "naive baseline (a dummy classifier, a mean predictor, or a "
        "rule-based recommender) so that the reader can see the floor.",
        "**Prefer the metric that survives class imbalance.** Where base "
        "rates are extreme, accuracy is reported but ROC-AUC, PR-AUC, "
        "macro-F1 and per-class scores are the metrics interpreted.",
        "**Quantify simulator optimism instead of ignoring it.** Any model "
        "fitted on simulated data is re-validated on a real dataset, and the "
        "real number is the one reported as the headline.",
        "**Report negative results.** A model with no demonstrable skill is "
        "reported as such, with its influence on the system reduced "
        "accordingly, rather than removed from the report.",
    ]),
    ("p", "Statistical claims about strategy differences are supported by "
          "bootstrap confidence intervals and p-values rather than by point "
          "estimates alone, because the differences involved are small "
          "enough that a point estimate would not be persuasive."),

    ("h2", "4.8 Summary"),
    ("p", "The approach specifies four modules that exchange data through a "
          "shared relational layer, each implementing competing methods so "
          "that comparison is possible, and an evaluation strategy designed "
          "to resist the two failure modes most likely to affect a project "
          "of this kind: optimism from evaluating on simulated data, and "
          "leakage from features that encode the target. Chapter 5 converts "
          "this approach into a concrete architecture."),

    # ================================================== CHAPTER 5
    ("h1", "CHAPTER 5 — ANALYSIS AND DESIGN"),

    ("h2", "5.1 Introduction"),
    ("p", "This chapter presents the architecture of the delivered system: "
          "the overall layered design (Section 5.2), the internal "
          "architecture of each module (Section 5.3), the shared database "
          "(Section 5.4), the design decisions taken specifically to protect "
          "research integrity (Section 5.5) and the multi-tenant design that "
          "allows any organisation to use the platform on its own website "
          "(Section 5.6)."),

    ("h2", "5.2 High-Level Architecture of the Overall System"),
    ("p", "The system is organised into four layers, shown in Figure 2. "
          "Separation is strict: the presentation layer holds no marketing "
          "logic, the research modules hold no HTTP concerns, and all "
          "cross-module communication passes through the data layer."),
    ("figure", {"path": f"{A}/fig02_architecture.png",
                "caption": "Figure 2 — High-level layered architecture of "
                           "the orchestration platform.", "width": 6.4}),
    ("p", "**Presentation layer.** A Next.js dashboard with six pages "
          "(Overview, Audience, Campaigns, Analytics, Content, Research) "
          "plus authentication and website-onboarding flows. Separately, the "
          "client's own website carries the mos.js snippet; its visitors are "
          "the audience, and they never interact with the dashboard."),
    ("p", "**Application layer.** A FastAPI service exposing site-scoped "
          "routers for segments, campaigns, analytics, content and actions; "
          "public tracking endpoints that require no authentication because "
          "a website's visitors are not signed in to anything; an ownership "
          "middleware enforcing tenant isolation in a single place; an "
          "authentication service; and a provenance service that reports, at "
          "request time, which data is real and which is simulated."),
    ("p", "**Research module layer.** The four modules as importable Python "
          "packages. Because the API is itself Python, the module that "
          "produced a reported research number is the same object the API "
          "loads at run time; there is no re-implementation gap between the "
          "experiment and the product."),
    ("p", "**Data layer.** A single PostgreSQL database whose principal "
          "tables carry the names specified in the interim report's "
          "architecture figures: user_segments, interactions, "
          "analytics_output and content_assets."),

    ("h2", "5.3 High-Level Architectures of Individual Modules"),

    ("h3", "5.3.1 Module 1 — Audience Targeting and Personalization"),
    ("p", "Figure 3 shows the segmentation engine. The three methods are "
          "peers rather than a pipeline: each produces a complete labelling "
          "of the audience, and the agreement vote arbitrates. The "
          "confidence score is a first-class output, because a downstream "
          "module needs to know not only which segment a user is in but how "
          "much to trust it."),
    ("figure", {"path": f"{A}/fig03_module1.png",
                "caption": "Figure 3 — Architecture of the hybrid "
                           "segmentation engine (Module 1).", "width": 6.1}),
    ("p", "Two design points are load-bearing. The cold-start rule takes "
          "precedence over the clustering vote, so a genuinely new visitor "
          "cannot be absorbed into an established cluster. And the minimum "
          "audience threshold causes the engine to decline clustering "
          "outright below 30 visitors, returning interpretable rule-based "
          "labels with an explicit explanation rather than an unstable "
          "partition presented as a result."),

    ("h3", "5.3.2 Module 2 — Marketing Automation and Campaign Management"),
    ("p", "Figure 4 shows the campaign engine. The policy engine is the "
          "single point at which the three strategies differ; every other "
          "component — profile builder, response model, templates, event "
          "simulation, evaluation — is shared. This is what makes the "
          "comparison in Section 7.3 a controlled one."),
    ("figure", {"path": f"{A}/fig04_module2.png",
                "caption": "Figure 4 — Architecture of the campaign "
                           "automation engine (Module 2).", "width": 6.1}),

    ("h3", "5.3.3 Module 3 — Marketing Analytics and Decision Support"),
    ("p", "Figure 5 shows the analytics module. Four analytical tracks — "
          "feature construction, funnel analysis, drop-off analysis and "
          "attribution — feed two predictive models and a shared "
          "explainability and validation stage, which in turn feed the "
          "recommendation generator."),
    ("figure", {"path": f"{A}/fig05_module3.png",
                "caption": "Figure 5 — Architecture of the analytics and "
                           "decision support module (Module 3).",
                "width": 6.4}),
    ("p", "The refusal guard is drawn as a distinct component because it is "
          "one. It sits between the recommendation generator and the "
          "published output and can suppress a result entirely: below five "
          "converting journeys attribution returns no numbers and states "
          "why, and a prediction distribution that has collapsed to a "
          "constant raises a calibration warning rather than being "
          "presented as a confident forecast."),

    ("h3", "5.3.4 Module 4 — AI Content Refinery and Multi-Platform "
           "Distribution"),
    ("p", "Figure 6 shows the content refinery. The feedback arrow from "
          "Module 3 is the integration point that the literature review "
          "found missing: platform generation order is set by measured "
          "attribution credit, not by assumption."),
    ("figure", {"path": f"{A}/fig06_module4.png",
                "caption": "Figure 6 — Architecture of the AI content "
                           "refinery (Module 4).", "width": 6.1}),

    ("h2", "5.4 Database Design"),
    ("p", "Figure 7 shows the schema. The design follows the interim "
          "report's table naming so that the delivered system can be read "
          "directly against the architecture figures approved at that "
          "stage."),
    ("figure", {"path": f"{A}/fig07_schema.png",
                "caption": "Figure 7 — Shared database schema. Provenance "
                           "flags are derived at write time.", "width": 6.4}),
    ("table", {"caption": "Table 9 — Principal database tables and their "
                          "owning module.",
               "header": ["Table", "Written by", "Read by", "Key content"],
               "rows": [
                   ["users, sessions", "Auth service", "All routes",
                    "Accounts, scrypt password hashes, database-row sessions"],
                   ["sites", "Onboarding", "All site-scoped routes",
                    "Registered client website, owner, write key"],
                   ["visitors", "Tracking endpoint", "Modules 1, 3",
                    "Anonymous visitor identity, is_synthetic (derived)"],
                   ["user_segments", "Module 1", "Modules 2, 3",
                    "Segment name, method, confidence"],
                   ["interactions", "Module 2, tracking", "Module 3",
                    "Event type, channel, platform, is_real (derived)"],
                   ["analytics_output", "Module 3", "Modules 2, 4, dashboard",
                    "Conversion probability, drop-off risk, credits, "
                    "recommendation"],
                   ["content_assets", "Module 4", "Module 2, dashboard",
                    "Caption, hashtags, CTA, component and composite scores"],
               ]}),

    ("h2", "5.5 Design for Research Integrity"),
    ("p", "The largest risk to a project of this kind is not that a model "
          "performs poorly but that a reader — or the team itself — mistakes "
          "a simulated result for a measured one. Three mechanisms were "
          "designed into the system rather than documented as conventions."),
    ("p", "**Provenance is derived, not asserted.** The columns "
          "`visitors.is_synthetic` and `interactions.is_real` are computed "
          "when a row is written, from the path the data actually travelled; "
          "a caller cannot declare its own data real. Demonstration traffic "
          "passes through the same public endpoints as genuine visitor "
          "traffic, so the flag is decided by the same code in both cases. "
          "An automated test fails the build if a synthetic visitor ever "
          "produces a row marked real."),
    ("p", "**The provenance report is generated, not written.** The "
          "dashboard's Research page reads dataset row counts from disk and "
          "from the database as the page loads, and reports which dataset "
          "trained which model, whether that data is real, and for each "
          "model both the headline number and its correct interpretation. "
          "Because it is generated it cannot drift away from the system it "
          "describes."),
    ("p", "**The system declines to report what it cannot support.** The "
          "refusal thresholds described in Section 5.3.3 are enforced in "
          "code, and every dashboard figure carries a real / simulated / "
          "mixed badge derived from the provenance of the rows behind it."),

    ("h2", "5.6 Multi-Tenant Design"),
    ("p", "The platform is designed so that any organisation can create an "
          "account, register its website, install the snippet and receive "
          "its own segmentation, campaigns, analytics and content. This "
          "required the security design to be part of the architecture "
          "rather than an afterthought."),
    ("bullets", [
        "**One isolation point.** All site-scoped routes pass through a "
        "single ownership middleware. A request for a site owned by another "
        "account returns 404 rather than 403, so the response does not even "
        "confirm that the site exists. A regression test registers two "
        "companies and asserts the isolation.",
        "**Sessions are database rows.** Signing out deletes the row, so the "
        "token dies immediately rather than remaining valid until expiry. "
        "Passwords are hashed with salted scrypt.",
        "**The browser never holds the token.** The dashboard receives an "
        "HttpOnly cookie set on its own origin, so client-side script cannot "
        "read it.",
        "**Public routes stay public.** The tracking endpoints require no "
        "authentication, because a website's visitors are not signed in to "
        "the platform and must not be asked to be.",
    ]),

    ("h2", "5.7 Summary"),
    ("p", "The design is a four-layer architecture in which the research "
          "modules are ordinary Python packages behind an API, joined by a "
          "single relational store whose provenance columns are derived "
          "rather than declared. The next chapter describes how this design "
          "was implemented, including the defects discovered in the process."),

    # ================================================== CHAPTER 6
    ("h1", "CHAPTER 6 — IMPLEMENTATION"),

    ("h2", "6.1 Introduction"),
    ("p", "This chapter describes the implementation of the framework: the "
          "data it was built on (Section 6.2), each module in turn "
          "(Section 6.3), the integrated platform (Section 6.4), the "
          "reproducibility and testing arrangements (Section 6.5), and the "
          "defects found in the project's own research code together with "
          "their corrections (Section 6.6)."),

    ("h2", "6.2 Data Collection"),

    ("h3", "6.2.1 Datasets"),
    ("p", "Four categories of data were used. Their provenance matters for "
          "the interpretation of every result in Chapter 7, so they are "
          "stated explicitly."),
    ("table", {"caption": "Table 10 — Datasets used, with size and role.",
               "header": ["Dataset", "Size", "Real / simulated", "Used by"],
               "rows": [
                   ["Digital Marketing Campaign dataset", "8,000 users × "
                    "20 columns", "Real (public)",
                    "Module 1 segmentation; Module 2 response model"],
                   ["UCI Bank Marketing (bank-additional-full)",
                    "41,188 records", "Real (public)",
                    "Module 3 simulator calibration and external model "
                    "validation"],
                   ["Social media engagement corpus", "12,000 posts",
                    "Real (public)", "Module 4 engagement regressor"],
                   ["Campaign goal / tone corpus", "527 labelled rows "
                    "(453 goal, 173 tone)", "Real, semi-automatically "
                    "labelled", "Module 4 text classifiers"],
                   ["Calibrated journey simulator", "2,000 users, 10,000 "
                    "campaign sends", "Simulated (calibrated on UCI)",
                    "Module 3 funnel, attribution and prediction "
                    "experiments"],
                   ["Live tracked traffic", "Variable", "Real, first-party",
                    "Live operation of all four modules"],
               ]}),

    ("h3", "6.2.2 Live audience collection"),
    ("p", "The audience for live operation is collected by **mos.js**, a "
          "small dependency-free script that a client installs on its "
          "website. It records page views, scroll depth, clicks, form "
          "submissions and purchases as first-party data, honours the Do Not "
          "Track header, and posts to the public `/collect` endpoint. "
          "Tracked links embedded in campaign content — `/track/click/{token}` "
          "for email and `/l/{token}` for social posts — allow a conversion "
          "to be matched back to the click that earned it even when the "
          "company sends the message through its own tools."),
    ("p", "One measurement limitation follows from this design and is "
          "reported wherever it is relevant: open tracking depends on a "
          "pixel that most mail clients now block or pre-fetch, so "
          "**sent → click** is treated as the reliable signal and "
          "sent → open is not relied upon."),

    ("h3", "6.2.3 The journey simulator"),
    ("p", "A simulator was required because a launch-stage product has, by "
          "definition, no journey history, and because ground-truth "
          "attribution scoring is impossible with observational data. The "
          "simulator generates users with segment-conditional response "
          "propensities, assigns each a channel exposure sequence drawn from "
          "known per-channel influence weights, and emits sent, open, click "
          "and convert events."),
    ("p", "Its stage transition probabilities are calibrated against the UCI "
          "Bank Marketing dataset (41,188 records) rather than chosen by "
          "hand, giving p(open | sent) = 0.899, p(click | open) = 0.557 and "
          "p(convert | click) = 0.198 for an overall conversion rate of "
          "11.3 %. Automated tests verify schema correctness, event "
          "ordering, segment validity and attribution integrity of the "
          "generated data."),

    ("h2", "6.3 Implementation of Individual Modules"),

    ("h3", "6.3.1 Module 1 — Audience Targeting and Personalization"),
    ("p", "The engine is implemented in `modules/m1_segmentation/segment.py` "
          "as a feature-set-agnostic function with two callers: "
          "`research_segmenter()` for the 8,000-user dataset and "
          "`web_segmenter()` for live tracked visitors. Preprocessing uses "
          "`StandardScaler`; clustering uses `KMeans` (k = 4, "
          "`n_init` = 10, fixed random state) and `AgglomerativeClustering` "
          "with Ward linkage."),
    ("p", "Cluster naming is derived at run time by ranking cluster "
          "centroids on engagement and purchase dimensions, so that names "
          "remain correct on a new audience. The agreement vote is "
          "implemented with the cold-start rule evaluated **first**, before "
          "the clustering comparison, which is the ordering the defect "
          "described in Section 6.6 required. The confidence score is "
          "produced by a classifier trained on the vote outcome with the "
          "vote's own encoded label excluded from the feature set."),

    ("h3", "6.3.2 Module 2 — Marketing Automation and Campaign Management"),
    ("p", "Module 2 is implemented under `modules/m2_automation/src/` with "
          "the three strategies in a `strategies/` package behind a common "
          "interface, so that the simulator and evaluator are identical "
          "across strategies. `ml_model.py` fits the response models; "
          "`simulator.py` generates events; `evaluation.py` computes the "
          "comparison metrics."),
    ("p", "A stratified dummy classifier is fitted alongside the real models "
          "and reported in the same table. This is deliberate: the dataset's "
          "base rate is 0.876, so a model can reach 87.6 % accuracy by "
          "predicting the majority class for every user. Publishing the "
          "dummy result in the same table makes that floor visible and "
          "prevents accuracy from being read as evidence of skill."),
    ("p", "Operational complexity is computed as the number of distinct "
          "decision rules and branch points a strategy requires. It is a "
          "simple measure, but it makes explicit a trade-off the literature "
          "usually leaves implicit: the hybrid strategy requires roughly "
          "three times the rule surface of the fixed workflow."),

    ("h3", "6.3.3 Module 3 — Marketing Analytics and Decision Support"),
    ("p", "Module 3 is implemented under `modules/m3_analytics/src/` as nine "
          "co-operating components, run end to end by `pipeline.py`."),
    ("table", {"caption": "Table 11 — Components of the Module 3 analytics "
                          "pipeline.",
               "header": ["Component", "Responsibility"],
               "rows": [
                   ["simulator.py", "Generate calibrated journeys with known "
                                    "channel influence"],
                   ["funnel.py", "Funnel construction and drop-off analysis "
                                 "overall, by segment and by strategy"],
                   ["attribution.py", "First-, last-, linear, multi-touch "
                                      "and Markov attribution"],
                   ["features.py", "Journey-level feature matrix shared by "
                                   "both predictive models"],
                   ["prediction.py", "Conversion and drop-off models with "
                                     "five-fold cross-validation"],
                   ["calibration.py", "Probability calibration and "
                                      "degenerate-prediction warnings"],
                   ["bootstrap.py", "Bootstrap confidence intervals and "
                                    "significance tests"],
                   ["shap_analysis.py", "SHAP feature attribution for both "
                                        "models"],
                   ["recommender.py / learned_recommender.py",
                    "Rule-based and supervised recommendation generation"],
               ]}),
    ("p", "Two implementation decisions are worth recording. First, the "
          "feature matrix deliberately excludes any variable that is defined "
          "in terms of the target; the elevated AUC values obtained on "
          "simulated data (Section 7.4.4) are nonetheless treated as "
          "optimistic, because in a simulator the events used as features "
          "and the events that define the label are generated by the same "
          "process. Second, the external validation against UCI Bank "
          "Marketing was added specifically so that this optimism could be "
          "quantified rather than argued about."),

    ("h3", "6.3.4 Module 4 — AI Content Refinery and Multi-Platform "
           "Distribution"),
    ("p", "The crawler (`crawler.py`) fetches and cleans the client's site; "
          "`knowledge_base.py` builds the business summary; `goal_tone.py` "
          "trains and selects the goal and tone classifiers; `generator.py` "
          "produces platform-specific assets; `evaluation.py` computes "
          "semantic similarity and platform suitability; `engagement.py` "
          "provides the engagement regressor; and `human_baseline.py` scores "
          "human-written copy through the same pipeline."),
    ("p", "Both classifiers are trained twice — once on TF-IDF features with "
          "logistic regression and once on Sentence-BERT embeddings with "
          "XGBoost — and the better model per target is selected on held-out "
          "performance. On this corpus the simpler representation won for "
          "both targets, which is reported in Section 7.5.1."),
    ("p", "The engagement regressor is trained with an explicit leakage "
          "guard: `likes`, `comments`, `shares`, `impressions` and "
          "`engagement_rate` are excluded from the feature set by name, "
          "because the target is derived from them. The consequence of "
          "adding that guard is reported honestly in Section 7.5.2."),

    ("h2", "6.4 Integrated Platform Implementation"),
    ("p", "The FastAPI application (`api/`) exposes eleven routers over the "
          "four modules, with the module logic wrapped in a `services/` "
          "layer so that HTTP concerns never leak into research code. The "
          "database schema lives in `api/schema.sql`; the tracking snippet "
          "is served from `api/static/mos.js`."),
    ("p", "Tenant isolation is implemented as a single middleware in "
          "`api/main.py` covering every site-scoped route, rather than as a "
          "check repeated in each handler — a deliberate choice, since an "
          "isolation check that must be remembered in twenty places will "
          "eventually be forgotten in one. Sites created by scripts and "
          "tests have no owner and remain open, so the command-line "
          "reproduction path needs no login."),
    ("p", "The dashboard (`web/`) is a Next.js application with six "
          "authenticated pages plus login, signup and site onboarding. "
          "Authentication cookies are set through Next route handlers on the "
          "dashboard's own origin, and `middleware.ts` redirects "
          "unauthenticated requests. A site switcher in the application "
          "shell reads the current site from a cookie and redirects to "
          "onboarding when an account has no sites yet."),
    ("p", "The entire system is reproducible from a clean checkout: "
          "`make setup` provisions dependencies, `make db` starts PostgreSQL "
          "in Docker, `make api` and `make web` start the services, "
          "`make site` serves a realistic demonstration client website with "
          "the snippet installed, and `make demo` populates a complete "
          "end-to-end demonstration in approximately sixty seconds."),

    ("h2", "6.5 Testing and Reproducibility"),
    ("p", "The automated suite comprises **208 test functions** — 171 in the "
          "platform suite and 37 in Module 3's own suite — covering data "
          "contracts, API behaviour, tracking, segmentation, campaign "
          "actions, content generation, authentication and tenant isolation, "
          "in addition to a TypeScript build of the dashboard. API tests "
          "skip rather than fail when PostgreSQL is not running, so the "
          "suite remains usable on a machine without Docker."),
    ("p", "Each defect described in the next section has a dedicated "
          "regression test, so that a corrected error cannot silently "
          "return. Two tests are structural rather than functional: one "
          "fails the build if a synthetic visitor produces a row marked "
          "real, and one walks every API response to assert that numeric "
          "fields are serialised as numbers — a guard added after PostgreSQL "
          "`NUMERIC` values twice reached the dashboard as JSON strings and "
          "silently broke chart rendering."),

    ("h2", "6.6 Defects Identified and Corrected in the Research Code"),
    ("p", "Converting the interim-stage notebooks into a running system "
          "exposed six defects in the project's own research code. Each had "
          "produced results that looked good and were not valid. They are "
          "reported here in full because the corrected figures are the ones "
          "used throughout Chapter 7, and because the pattern they form — "
          "every one of them inflated a result — is itself a finding."),
    ("table", {"caption": "Table 12 — Defects found in the research code, "
                          "their effect and the correction applied.",
               "header": ["#", "Defect", "Effect on reported results",
                          "Correction"],
               "rows": [
                   ["D1", "Module 1's confidence classifier was trained with "
                          "its own target (the encoded vote outcome) present "
                          "as an input feature.",
                    "6,248 of 8,000 users received confidence of exactly "
                    "1.00.",
                    "Target removed from the feature set; honest held-out "
                    "accuracy is 0.92."],
                   ["D2", "In the agreement vote, the clustering comparison "
                          "was evaluated before the cold-start rule.",
                    "The New Cold User segment fell from 43 users to 0 on "
                    "live data — the project's first novel contribution was "
                    "being erased from its own output.",
                    "Cold-start rule evaluated first, with precedence over "
                    "the clustering vote."],
                   ["D3", "Cluster names were hardcoded to cluster indices.",
                    "Names were correct for one dataset and one random seed "
                    "and arbitrary for any other audience.",
                    "Names derived from cluster centroids at run time."],
                   ["D4", "Module 4's engagement regressor retained likes, "
                          "comments, shares and impressions as features "
                          "while predicting a ratio derived from them.",
                    "R² of 0.99 was entirely leakage; the honest value is "
                    "−0.30.",
                    "Leakage guard by feature name; the model's weight in "
                    "content scoring reduced from 0.45 to 0.20."],
                   ["D5", "The goal/tone corpus required a row to clear the "
                          "confidence threshold for both targets, although "
                          "the two classifiers train independently.",
                    "The usable corpus was reduced from 527 rows to 114.",
                    "Per-target filtering: 453 rows for goal, 173 for tone."],
                   ["D6", "The `shorts` platform declared a video visual "
                          "type but defined no visual options.",
                    "The selector silently returned a static image brief "
                    "instead of a video brief.",
                    "Visual options defined; selector asserts the declared "
                    "type is satisfiable."],
               ]}),
    ("p", "Two environment faults were also diagnosed and fixed. The first "
          "was a macOS **OpenMP conflict**: XGBoost and PyTorch each bundle "
          "their own `libomp`, and fitting or predicting with XGBoost while "
          "PyTorch was loaded terminated the process with exit code 139 and "
          "no traceback, killing training runs, the test suite and API "
          "workers. Only constraining OpenMP to a single thread resolved it; "
          "a guard module is imported first in every entry point. The "
          "second was a **character-encoding fault** in the crawler: the "
          "HTTP library defaults to ISO-8859-1 for `text/html` when the "
          "response header omits a charset, which corrupted every non-ASCII "
          "character in a client's marketing copy before it reached the "
          "content generator."),
    ("note", "The defects share a signature: each one made a result better "
             "than it truly was, and none produced an error message. This is "
             "the reason the integrity mechanisms of Section 5.5 were "
             "designed into the system rather than left as good intentions."),

    ("h2", "6.7 Summary"),
    ("p", "All four modules are implemented, integrated behind a single API "
          "over a shared PostgreSQL database, exercised by 208 automated "
          "tests and reproducible from a clean checkout with a small number "
          "of commands. Six defects in the research code were identified and "
          "corrected, and the corrected figures are the ones evaluated in "
          "Chapter 7."),
]
