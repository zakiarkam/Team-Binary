# -*- coding: utf-8 -*-
"""Front matter and Chapters 1-3."""

A = "/Users/arkamzakir/Documents/Research/Research/report/assets"

FRONT_BLOCKS = [
    ("h1", "ACKNOWLEDGMENT"),
    ("p", "We wish to record our sincere gratitude to our supervisors, "
          "Dr. A. L. A. Romesh R. Thanuja and Ms. M. A. N. Perera, whose "
          "guidance shaped this project from a loose collection of four "
          "marketing ideas into a single coherent research system. Their "
          "insistence that every claim be supported by a measurement, and "
          "their patience through several changes of direction, are the "
          "reason this report is able to report failures as openly as it "
          "reports successes."),
    ("p", "We thank the academic and technical staff of the Faculty of "
          "Information Technology, University of Moratuwa, for the knowledge "
          "and the facilities that made this work possible, and the panel of "
          "evaluators whose questions at the proposal and interim stages "
          "exposed weaknesses in our methodology early enough for us to "
          "correct them."),
    ("p", "We acknowledge the maintainers of the open datasets on which this "
          "study depends — in particular the UCI Machine Learning Repository "
          "for the Bank Marketing dataset, which provided the only real "
          "behavioural benchmark available to us, and the publishers of the "
          "Digital Marketing Campaign and social-media engagement datasets "
          "used for segmentation and content modelling."),
    ("p", "Finally, we thank our families and our colleagues in the "
          "Level 4 batch for their encouragement over the course of this "
          "project, and the free education system of Sri Lanka, without "
          "which none of us would have reached this point."),

    ("h1", "ABSTRACT"),
    ("p", "Digital marketing is executed through fragmented tools: one system "
          "segments an audience, another automates campaigns, a third reports "
          "analytics and a fourth generates content. Because these systems do "
          "not exchange information, the outcome of a campaign rarely improves "
          "the next one. The difficulty is sharpest for a newly launched "
          "product, where almost no historical interaction data exists — the "
          "cold-start condition — and where conventional data-hungry marketing "
          "models are least effective."),
    ("p", "This project designs, implements and evaluates an integrated, "
          "closed-loop AI marketing orchestration framework built specifically "
          "for cold-start conditions. Four research modules are joined by a "
          "shared data layer so that the output of each becomes the input of "
          "the next: (1) a hybrid audience segmentation engine that combines "
          "rule-based logic with K-Means and hierarchical clustering through "
          "an agreement vote, preserving a cold-start segment that clustering "
          "alone destroys; (2) a campaign automation engine that compares "
          "fixed, trigger-based and hybrid strategies under identical "
          "conditions; (3) an analytics and decision-support module that "
          "constructs funnels, compares five attribution models, predicts "
          "conversion and drop-off risk, and generates ranked "
          "recommendations; and (4) an AI content refinery that crawls the "
          "client's own website and produces platform-specific marketing "
          "assets scored on semantic fidelity, platform suitability and "
          "predicted engagement. The modules run behind a FastAPI service "
          "over PostgreSQL, with a Next.js dashboard and a first-party "
          "website tracking snippet that supplies a live audience."),
    ("p", "Evaluation used a mixture of public datasets, a calibrated "
          "behavioural simulator and live tracked traffic. Hybrid "
          "segmentation separated the highest- from the lowest-converting "
          "segment by 38.4 percentage points while retaining a New Cold User "
          "segment that pure clustering eliminated. The hybrid automation "
          "strategy raised conversion by 26.2 % over a fixed workflow "
          "(bootstrap 95 % CI 10.1 %–44.6 %, p < 0.001). Conversion and "
          "drop-off models reached AUC 0.9756 and 0.9902 on simulated data, "
          "but the honest figure reported is the AUC of 0.9535 obtained on "
          "the real UCI Bank Marketing dataset. Multi-touch attribution "
          "matched ground-truth channel credit with a mean absolute error of "
          "0.0178 against 0.0260 for last-touch, and a learned recommender "
          "reached 94.4 % accuracy against 82.8 % for the rule baseline. In "
          "Module 4 both text classifiers selected TF-IDF over "
          "Sentence-BERT, while the engagement regressor is reported as "
          "having no demonstrable skill (R² −0.30) and its weight in content "
          "scoring was reduced accordingly."),
    ("p", "The principal contribution is not any single model but the "
          "demonstration that the four functions can be operated as one "
          "measurable feedback loop under cold-start conditions — together "
          "with a set of mechanisms that prevent simulated results from being "
          "reported as measured behaviour."),
    ("p", "**Index Terms** — digital marketing orchestration, cold-start, "
          "hybrid segmentation, marketing automation, funnel analytics, "
          "multi-touch attribution, conversion prediction, AI content "
          "generation, closed-loop optimisation."),
]


BODY_BLOCKS = [
    # ================================================== CHAPTER 1
    ("h1_nobreak", "CHAPTER 1 — INTRODUCTION"),

    ("h2", "1.1 Introduction"),
    ("p", "Digital marketing has become the primary means by which "
          "organisations acquire, engage, convert and retain customers. A "
          "modern campaign spans email, social platforms, paid advertising, "
          "search and the organisation's own website, and each of those "
          "channels generates behavioural data that could, in principle, be "
          "used to improve the next campaign. In practice this rarely "
          "happens. The tools that perform segmentation, automation, "
          "analytics and content production are separate products with "
          "separate data models, and the marketer is left to carry insight "
          "between them manually."),
    ("p", "The consequence is that digital marketing is executed as a series "
          "of disconnected actions rather than as a learning process. "
          "Segmentation output does not inform the automation strategy; "
          "analytics describe what has already happened without prescribing "
          "what to do next; and content is produced without reference to "
          "which platform actually earned the last conversion. The marketing "
          "cycle does not close."),
    ("p", "This project addresses that gap directly. It designs, builds and "
          "evaluates an **AI-powered digital marketing orchestration "
          "framework** in which four research modules — audience targeting, "
          "campaign automation, analytics and decision support, and AI "
          "content refinement — operate over a single shared data layer, so "
          "that the measured outcome of one campaign becomes an input to the "
          "next. The framework is targeted deliberately at the hardest case: "
          "a **newly launched product** for which almost no historical "
          "customer data exists."),
    ("p", "The system produced is both a working software platform and a "
          "research instrument. A company creates an account, registers its "
          "website and installs a single tracking snippet; the visitors to "
          "that website become the audience on which the four modules "
          "operate. Every figure the platform reports is accompanied by a "
          "statement of whether the underlying data was measured or "
          "simulated — a design decision that runs through the whole of this "
          "report."),

    ("h2", "1.2 Background and Motivation"),
    ("p", "Three observations motivated this work."),
    ("p", "**Fragmentation is the normal state of marketing technology.** "
          "Commercial platforms such as HubSpot, Mailchimp, Salesforce "
          "Marketing Cloud and Marketo each solve part of the problem well, "
          "but integration between customer intelligence, campaign execution "
          "and decision support is shallow. Academic work mirrors this "
          "division: studies address segmentation, or automation, or "
          "attribution, but seldom the interaction between them. Where "
          "integration is discussed it is usually described architecturally "
          "rather than evaluated experimentally."),
    ("p", "**The cold-start condition is under-studied and commercially "
          "acute.** Most published marketing analytics assumes an "
          "established customer base with a rich interaction history. A "
          "start-up or a newly launched product has neither. Clustering "
          "algorithms need behavioural variance to form meaningful groups; "
          "predictive models need converted examples to learn from; "
          "attribution models need multi-touch journeys. At launch, none of "
          "these are available in sufficient quantity, and precisely the "
          "organisations that most need marketing efficiency are the ones "
          "the literature serves least well."),
    ("p", "**Descriptive analytics is not decision support.** Existing "
          "analytics tools report clicks, impressions and conversion counts. "
          "They tell a marketer what happened; they do not say which "
          "audience to contact next, on which platform, with which message. "
          "Turning measurement into a prescribed action — and then measuring "
          "whether that action worked — is what closes the loop, and it is "
          "the part that is generally missing."),
    ("p", "A fourth motivation emerged during the project itself. While "
          "converting the interim-stage notebooks into a running system, the "
          "team discovered several defects in its own research code that had "
          "produced impressively good but invalid results. These are "
          "documented openly in Section 6.6 and Chapter 7, because the "
          "experience shaped the project's methodology: a research system "
          "should be constructed so that it is difficult to fool oneself."),

    ("h2", "1.3 Problem in Brief"),
    ("p", "There is no integrated, empirically evaluated framework that "
          "unifies audience intelligence, campaign automation, "
          "attribution-aware predictive analytics and AI content generation "
          "into a single closed feedback loop that remains usable under "
          "cold-start, low-data conditions."),
    ("p", "This decomposes into five concrete problems:"),
    ("numbers", [
        "**Segmentation collapses under low data.** Clustering requires "
        "behavioural variance that a newly launched product does not have, "
        "and rule-based segmentation alone cannot adapt.",
        "**Automation strategies are asserted rather than compared.** Fixed, "
        "trigger-based and hybrid campaign strategies are advocated in the "
        "literature, but rarely evaluated against one another on the same "
        "users under the same conditions, and rarely with operational cost "
        "considered alongside conversion.",
        "**Attribution is either simplistic or unusable at launch.** "
        "Single-touch models oversimplify the journey; data-driven models "
        "such as Markov or Shapley require volumes of journey data that a "
        "launch-stage product cannot supply.",
        "**Analytics does not prescribe.** Funnel reports identify drop-off "
        "but stop short of recommending the corrective action, and are not "
        "connected back to the automation engine.",
        "**Generated content is disconnected from performance.** AI content "
        "tools optimise for fluency, not for the platform that actually "
        "produced conversions, and typically have no feedback path from "
        "campaign analytics.",
    ]),

    ("h2", "1.4 Aim and Objectives"),

    ("h3", "1.4.1 Aim"),
    ("p", "To design, implement and experimentally evaluate an integrated, "
          "closed-loop, AI-powered digital marketing orchestration framework "
          "that unifies audience segmentation, campaign automation, "
          "attribution-aware predictive analytics and AI content refinement, "
          "and that remains effective for newly launched products operating "
          "under cold-start and limited-data conditions."),

    ("h3", "1.4.2 Objectives"),
    ("numbers", [
        "To design and implement a hybrid segmentation engine that combines "
        "rule-based logic with unsupervised clustering, and to evaluate it "
        "against each constituent method on segment separation, stability "
        "and downstream conversion.",
        "To implement fixed-workflow, trigger-based and hybrid campaign "
        "automation strategies and compare them experimentally on identical "
        "user cohorts using engagement, conversion, time-to-convert and "
        "operational complexity.",
        "To construct a marketing funnel and drop-off analysis capable of "
        "isolating loss by stage, segment and automation strategy.",
        "To implement and compare first-touch, last-touch, linear, "
        "multi-touch and Markov attribution against a known ground truth, "
        "and to quantify the error of each.",
        "To build calibrated conversion-probability and drop-off-risk models, "
        "validate them on a real-world dataset rather than only on simulated "
        "data, and explain their behaviour using SHAP.",
        "To generate ranked, actionable marketing recommendations from "
        "analytics output, and to compare a learned recommender against a "
        "rule-based baseline.",
        "To build an AI content refinery that converts a client's own website "
        "copy into platform-specific marketing assets, and to evaluate those "
        "assets on semantic fidelity, platform suitability and predicted "
        "engagement.",
        "To integrate the four modules into a single multi-tenant platform "
        "with a shared database, a tracking-based live audience and a "
        "dashboard, and to demonstrate that analytics output measurably "
        "re-enters segmentation, automation and content generation.",
        "To establish mechanisms that prevent simulated results from being "
        "presented as measured behaviour, and to report the framework's "
        "limitations and negative results explicitly.",
    ]),

    ("h2", "1.5 Proposed Solution"),
    ("p", "The proposed solution is a four-module orchestration framework "
          "sharing one data layer. Each module is an independent research "
          "contribution that is separately evaluable, and each is also a "
          "producer and consumer of data for its neighbours. The modules "
          "are summarised below and specified in detail in Chapters 4 to 6."),

    ("h3", "1.5.1 Module 1 — Audience Targeting and Personalization Engine"),
    ("p", "Module 1 converts raw behavioural data into labelled audience "
          "segments. Three segmentation methods run in parallel over the same "
          "feature matrix — a rule-based segmenter encoding marketing "
          "heuristics, K-Means clustering and agglomerative hierarchical "
          "clustering — and their outputs are combined through an agreement "
          "vote that also yields a confidence score. Five segments are shared "
          "across the whole system: High Intent, Loyal Customer, Price "
          "Sensitive, Low Engagement and New Cold User."),
    ("p", "The novel element is the treatment of the cold-start case. A "
          "visitor with almost no history has no distinguishing behavioural "
          "variance, so clustering assigns them to whichever centroid is "
          "nearest and the fact that they are new is lost. In the proposed "
          "engine the cold-start rule takes precedence over the clustering "
          "vote, and below a minimum audience size the engine declines to "
          "cluster at all and reports why. Segment labels and confidences "
          "are written to the shared **user_segments** table for Modules 2 "
          "and 3."),

    ("h3", "1.5.2 Module 2 — Marketing Automation and Campaign Management"),
    ("p", "Module 2 consumes segments and executes campaigns. Its research "
          "purpose is comparative: three automation strategies operate on the "
          "same user population under the same conditions so that the "
          "difference between them can be attributed to the strategy alone."),
    ("bullets", [
        "**Fixed workflow** — an identical scheduled sequence for every user; "
        "the baseline.",
        "**Trigger-based** — the next action is selected from the user's most "
        "recent observed event.",
        "**Hybrid** — scheduling, behavioural triggers, segment labels from "
        "Module 1 and a machine-learned response probability are combined in "
        "one policy engine.",
    ]),
    ("p", "Execution produces interaction events (sent, opened, clicked, "
          "ignored, converted) which are written to the shared "
          "**interactions** table and become the primary input to Module 3. "
          "Strategies are compared not only on conversion but on operational "
          "complexity, because a strategy that converts slightly better while "
          "trebling the number of rules to maintain may not be the correct "
          "engineering choice."),

    ("h3", "1.5.3 Module 3 — Marketing Analytics and Decision Support"),
    ("p", "Module 3 is the intelligence layer. It converts the interaction "
          "log into four kinds of output: a funnel with drop-off attribution "
          "by stage, segment and strategy; a comparison of five attribution "
          "models against ground truth; calibrated conversion-probability and "
          "drop-off-risk predictions with SHAP explanations; and ranked, "
          "actionable recommendations naming the audience, the action and the "
          "platform."),
    ("p", "Two design decisions distinguish it from conventional analytics. "
          "First, attribution models are not merely reported but "
          "**benchmarked against a known ground truth**, so the report can "
          "state which model is wrong and by how much. Second, the module "
          "**refuses to report what the data cannot support**: below five "
          "converting journeys attribution returns no numbers, and "
          "degenerate predictions raise a calibration warning rather than a "
          "confident answer. Its output is written to **analytics_output** "
          "and flows back to Modules 2 and 4, which is what closes the loop."),

    ("h3", "1.5.4 Module 4 — AI-Powered Content Refinery and Multi-Platform "
           "Distribution"),
    ("p", "Module 4 crawls the client's own website, extracts a business "
          "summary and brand vocabulary, classifies the campaign goal and "
          "tone, and generates platform-specific assets — captions, "
          "hashtags, calls to action, image prompts and short-video briefs — "
          "for Instagram, Facebook, LinkedIn, YouTube and email."),
    ("p", "Each asset is scored on three axes: semantic similarity to the "
          "source material, rule-based platform suitability, and predicted "
          "engagement. The composite score ranks the assets, and the "
          "platform ordering is supplied by Module 3's attribution output, "
          "so content production is driven by which platform actually earns "
          "conversions rather than by assumption. A human-baseline harness "
          "scores manually written content through the identical pipeline so "
          "that the AI output can be compared fairly."),

    ("h3", "1.5.5 Flow of the Overall System"),
    ("p", "Figure 1 shows the end-to-end flow. A visitor arrives at the "
          "client's website, where the tracking snippet records first-party "
          "behaviour. Module 1 segments that audience; Module 2 selects and "
          "executes a campaign action per segment; the resulting interaction "
          "events are logged; Module 3 analyses those events and produces "
          "predictions and recommendations; Module 4 generates the content "
          "for the next cycle using Module 3's platform priorities. Module "
          "3's recommendations simultaneously re-enter Module 2 as campaign "
          "optimisation and Module 1 as re-targeting priorities."),
    ("figure", {"path": f"{A}/fig01_closed_loop.png",
                "caption": "Figure 1 — Closed-loop flow of the overall "
                           "orchestration framework.", "width": 6.3}),
    ("p", "The loop is genuine rather than decorative: the highest-scoring "
          "content asset from Module 4 becomes the opening message of the "
          "next campaign plan, and the attribution credit computed by Module "
          "3 changes which platform Module 4 writes for first. Chapter 7 "
          "reports the measurement of this behaviour."),

    # ================================================== CHAPTER 2
    ("h1", "CHAPTER 2 — RELATED WORK"),

    ("h2", "2.1 Introduction"),
    ("p", "This chapter reviews the research that this project builds on and "
          "positions the proposed framework against it. It is organised in "
          "three parts: work addressing the marketing pipeline as a whole "
          "(Section 2.2); work specific to each of the four modules "
          "(Section 2.3); and the research gaps that follow from that "
          "review (Section 2.4). Throughout, the review pays particular "
          "attention to two questions that are decisive for this project — "
          "whether a technique remains usable when interaction data is "
          "scarce, and whether its output is connected to any downstream "
          "marketing decision."),

    ("h2", "2.2 Overall Related Work"),
    ("p", "Wedel and Kannan [49] survey marketing analytics for data-rich "
          "environments and establish the analytical vocabulary — "
          "segmentation, response modelling, attribution — that most "
          "subsequent work adopts. Their framing is explicit about its "
          "premise: the methods assume abundant historical data. Davenport "
          "et al. [12] and Huang and Rust [21] examine how artificial "
          "intelligence changes marketing practice, and both identify "
          "integration across the marketing function as the principal "
          "unrealised opportunity, while stopping short of specifying or "
          "evaluating an integrated architecture."),
    ("p", "Kotler et al. [24] describe the strategic case for technology-led "
          "marketing, and Chaffey and Ellis-Chadwick [8] provide the "
          "operational treatment of channel-specific strategy that informs "
          "the platform-aware element of Module 4. Kumar et al. [26] "
          "review the digital transformation of marketing and note the "
          "persistent gap between the analytics an organisation collects and "
          "the decisions it actually takes — the same gap this project's "
          "Module 3 is designed to close."),
    ("p", "Verma et al. [48] conduct a systematic review of AI in marketing "
          "and report that the overwhelming majority of studies address a "
          "single function in isolation. Where a full pipeline is proposed, "
          "it is generally presented as an architecture diagram rather than "
          "an implemented and measured system. Two consequences follow. "
          "First, the interaction effects between modules are unknown: it is "
          "not established whether better segmentation actually improves "
          "campaign outcomes, because the two are rarely measured together. "
          "Second, the cost of integration is invisible. This project "
          "responds by implementing the pipeline end to end and reporting "
          "the interaction effects it produces, including where they are "
          "smaller than expected."),
    ("p", "Commercial systems — IBM Watson Marketing, Salesforce Einstein, "
          "HubSpot and Adobe Experience Platform — do integrate these "
          "functions, but as closed products they publish neither their "
          "methods nor controlled comparisons, and their models are trained "
          "on the mature customer bases of established enterprises. The "
          "cold-start behaviour of these systems is not documented, and it "
          "is not possible to reproduce their results."),

    ("h2", "2.3 Module-wise Related Work"),

    ("h3", "2.3.1 Audience Segmentation and Personalization"),
    ("p", "Customer segmentation moved from demographic rules to behavioural "
          "clustering as machine learning became routine. Han et al. [16] "
          "give the standard treatment of K-Means and hierarchical "
          "clustering, and Aggarwal [2] and Hastie et al. [17] cover the "
          "assumptions each method carries — in particular K-Means's "
          "assumption of roughly spherical, similarly sized clusters and its "
          "requirement that *k* be fixed in advance. Alves Gomes and Meisen "
          "[3] review segmentation for e-commerce personalisation "
          "specifically and find that clustering quality metrics dominate "
          "the evaluation literature while downstream marketing outcomes are "
          "rarely reported."),
    ("p", "Hybrid approaches that combine business rules with clustering "
          "have been proposed to retain interpretability while gaining "
          "adaptability, and are reported to improve personalisation "
          "reliability relative to either method alone. What is not "
          "addressed is arbitration: when the rule and the cluster disagree, "
          "which wins? This project found that the answer is consequential. "
          "In an early implementation, resolving disagreement in favour of "
          "the clustering result silently destroyed the cold-start segment "
          "entirely (Section 6.6), because a new visitor has no behavioural "
          "signature and is therefore absorbed into whichever cluster is "
          "nearest."),
    ("p", "The cold-start problem itself is well characterised in "
          "recommender systems. Schein et al. [42] define the methods and "
          "metrics for cold-start recommendation; Bobadilla et al. [5] and "
          "Ricci et al. [40] survey the mitigations — content-based "
          "fallbacks, transfer learning, hybrid recommenders. That work "
          "concerns recommending *items* to users with no history. The "
          "analogous marketing problem — *segmenting* users who have no "
          "history, at the launch of a product that has no history either — "
          "receives markedly less attention, and it is the specific gap "
          "Module 1 addresses."),

    ("h3", "2.3.2 Marketing Automation and Campaign Management"),
    ("p", "Chaffey and Ellis-Chadwick [8] document fixed-workflow campaign "
          "management and its limitations: identical sequences delivered "
          "regardless of behaviour produce low engagement and slow "
          "conversion. Davenport et al. [12] describe behaviour-triggered "
          "automation, in which campaign actions respond to opens, clicks "
          "and abandonment, and report improved relevance at the cost of "
          "growing rule complexity. Kumar and Reinartz [27] propose a "
          "blended approach in which a stable base workflow is modulated by "
          "predicted engagement probability, and report improvements in open "
          "and click-through rates."),
    ("p", "Predictive campaign optimisation applies supervised learning — "
          "logistic regression, random forests, gradient boosting — to "
          "response prediction; Provost and Fawcett [37] set out the "
          "practical framing. Sutton and Barto [44] provide the foundation "
          "for reinforcement-learning approaches to sequential campaign "
          "decisions, which are attractive in principle but require "
          "extensive interaction histories and carefully designed reward "
          "functions, restricting them to warm-start settings."),
    ("p", "Two gaps persist. First, controlled comparison is rare: the three "
          "strategies are seldom run on the same users under the same "
          "conditions, so reported differences confound strategy with "
          "population. Second, operational cost is almost never measured "
          "alongside effectiveness, although it is decisive in practice. "
          "Module 2 addresses both by running all three strategies over an "
          "identical 8,000-user cohort and reporting rule count and workflow "
          "complexity beside conversion."),

    ("h3", "2.3.3 Marketing Analytics, Attribution and Decision Support"),
    ("p", "Funnel analysis is the established framework for locating loss in "
          "the customer journey. Court et al. [10] introduced the consumer "
          "decision journey, arguing that purchase paths are not linear, and "
          "Järvinen and Karjaluoto [22] show that stage-to-stage transition "
          "analysis is more actionable than any single aggregate engagement "
          "metric. The limitation they share with commercial analytics is "
          "that funnel reporting is descriptive: it identifies the leak "
          "without prescribing the repair."),
    ("p", "Attribution modelling assigns conversion credit across "
          "touchpoints. First-touch and last-touch attribution are "
          "computationally trivial and, as Dalessandro et al. [11] argue, "
          "causally unsound — they assign all credit to one interaction on "
          "the basis of position alone. Shao and Li [43] present data-driven "
          "multi-touch attribution that learns contribution weights from "
          "interaction sequences and demonstrate more realistic conversion "
          "analysis. Markov-chain and Shapley-value formulations extend "
          "this, at the cost of requiring substantial journey volume."),
    ("p", "A methodological weakness runs through this literature: "
          "attribution models are usually compared with one another rather "
          "than against a known ground truth, because in observational data "
          "the true credit is unobservable. Module 3 exploits its simulator "
          "to address this directly. Because the simulator generates each "
          "journey from known per-channel influence weights, the true credit "
          "*is* known, and each attribution model can be scored by mean "
          "absolute error against it (Section 7.4.3)."),
    ("p", "Predictive analytics for conversion and churn is well established "
          "[5], [37], with deep sequence models applied to behavioural "
          "prediction [15]. Interpretability is addressed by Lundberg and "
          "Lee [29] through SHAP and by Molnar [33] more broadly; these "
          "methods are used in Module 3 to explain what drives each "
          "prediction. The remaining gap is connective rather than "
          "algorithmic: analytics outputs are seldom wired back into "
          "campaign execution, so the loop stays open. Providing that wiring, "
          "and measuring it, is a central objective of this project."),

    ("h3", "2.3.4 AI Content Generation and Multi-Platform Optimisation"),
    ("p", "Transformer architectures [47] and large pre-trained language "
          "models [6] made fluent, controllable text generation practical, "
          "and Tunstall et al. [45] document the applied pipeline. In "
          "marketing this supports caption generation, product copywriting, "
          "tone adaptation and summarisation. Sentence embeddings and "
          "BERTScore [50] provide the standard means of checking that "
          "generated text preserves source meaning, and Radford et al. [38] "
          "and Li et al. [28] extend the approach to multimodal content."),
    ("p", "Platform-aware optimisation is emphasised in the practitioner "
          "literature [8], [25]: platforms differ in length conventions, "
          "hashtag norms, formality and format expectation, so republishing "
          "one message everywhere underperforms. Rule-based platform-fit "
          "scoring is straightforward and is adopted in Module 4."),
    ("p", "Engagement prediction is the weakest link. Models are trained to "
          "predict likes, shares or engagement rate from post features, but "
          "outcomes are dominated by factors absent from the text — platform "
          "ranking algorithms, timing, follower composition, trending "
          "topics. Reported successes are frequently inflated by leakage "
          "when engagement components are left among the features. This "
          "project encountered exactly that defect in its own code "
          "(Section 6.6) and reports the corrected result — no demonstrable "
          "skill — as a negative finding rather than removing the model."),
    ("p", "Finally, the literature almost never connects content generation "
          "to campaign analytics. Generated content is evaluated on "
          "linguistic quality in isolation, not on whether it was produced "
          "for the platform that earns conversions. Module 4 consumes "
          "Module 3's attribution output to order platform generation, "
          "which is the specific integration this review found missing."),

    ("h2", "2.4 Research Gaps"),
    ("p", "The review identifies six gaps that define this project's "
          "contribution."),
    ("table", {"caption": "Table 1 — Research gaps identified in the "
                          "literature and the response of this project.",
               "header": ["#", "Research gap", "How this project responds"],
               "rows": [
                   ["G1", "Lack of integrated marketing intelligence: "
                          "segmentation, automation, analytics and content "
                          "are studied and built separately.",
                    "All four modules implemented over one shared data layer "
                    "with measured feedback paths (Ch. 5–7)."],
                   ["G2", "Cold-start marketing is under-researched; methods "
                          "assume mature customer data.",
                    "Hybrid segmentation with cold-start precedence and a "
                    "minimum-audience refusal rule (§4.2, §7.2)."],
                   ["G3", "Automation strategies are asserted, not compared "
                          "under controlled conditions.",
                    "Fixed, trigger and hybrid run on an identical "
                    "8,000-user cohort; complexity reported with conversion "
                    "(§7.3)."],
                   ["G4", "Attribution models are compared to each other, "
                          "not to a ground truth.",
                    "Simulator with known channel influence enables MAE "
                    "scoring of five attribution models (§7.4.3)."],
                   ["G5", "Analytics describes but does not prescribe, and "
                          "is not wired back to execution.",
                    "Recommendation generator plus learned recommender; "
                    "output re-enters Modules 2 and 4 (§4.4, §7.4.5)."],
                   ["G6", "Generated content is disconnected from campaign "
                          "performance, and engagement models are often "
                          "leakage-inflated.",
                    "Attribution-driven platform ordering; leakage-guarded "
                    "engagement model reported honestly (§4.5, §7.5)."],
               ]}),

    ("h2", "2.5 Summary"),
    ("p", "The reviewed literature provides mature methods for each "
          "individual marketing function but leaves three things open: the "
          "behaviour of these methods when interaction data is scarce, the "
          "effect of connecting them into one loop, and the honest "
          "evaluation of models whose reported performance is easily "
          "inflated by leakage or by evaluation on the data that generated "
          "them. These three concerns shape the approach set out in "
          "Chapter 4, the design in Chapter 5 and the evaluation strategy "
          "in Chapter 7."),

    # ================================================== CHAPTER 3
    ("h1", "CHAPTER 3 — TECHNOLOGY ADAPTED"),

    ("h2", "3.1 Introduction"),
    ("p", "This chapter describes the technologies selected to implement the "
          "framework and the reasoning behind each choice. Selection was "
          "governed by four criteria: suitability for machine-learning "
          "research; the ability to run the four modules behind a single "
          "service; reproducibility, so that any reported result can be "
          "regenerated; and modest resource requirements, since the system "
          "targets small organisations. Section 3.7 records where the "
          "delivered stack differs from the interim report and why."),

    ("h2", "3.2 Programming Languages"),

    ("h3", "3.2.1 Python"),
    ("p", "Python 3.11 is the primary language. All four research modules, "
          "the data pipelines, the model training scripts, the simulator and "
          "the backend service are written in Python. It was selected for "
          "the maturity of its scientific stack, its dominance in machine "
          "learning research and the fact that a single language across "
          "modelling and serving removes an entire class of "
          "training/serving-skew defects: the model that produced a reported "
          "number is the same object the API loads."),

    ("h3", "3.2.2 JavaScript and TypeScript"),
    ("p", "The marketer-facing dashboard is written in TypeScript. Static "
          "typing was valuable because the dashboard consumes a wide API "
          "surface across six pages; type errors that would otherwise appear "
          "as blank charts are caught at build time. JavaScript is also used "
          "for **mos.js**, the first-party tracking snippet installed on a "
          "client's website, which is deliberately dependency-free and small "
          "so that it does not slow the host page."),

    ("h2", "3.3 Machine Learning and Data Science Libraries"),
    ("bullets", [
        "**scikit-learn** — K-Means, agglomerative clustering, logistic "
        "regression, random forests, TF-IDF vectorisation, pipelines, "
        "cross-validation and the metric suite. It is the backbone of "
        "Modules 1, 2 and 3, and of the text classifiers in Module 4.",
        "**XGBoost** — gradient-boosted trees for conversion and drop-off "
        "prediction in Module 3 and for engagement regression in Module 4; "
        "used as the strong learner against which simpler models are "
        "compared.",
        "**pandas and NumPy** — tabular data handling, feature engineering "
        "and numerical computation throughout.",
        "**SHAP** [29] — model-agnostic explanation of the conversion and "
        "drop-off models, so that predictions can be defended rather than "
        "merely reported.",
        "**sentence-transformers** — Sentence-BERT embeddings for semantic "
        "similarity scoring in Module 4 and as one of the two candidate "
        "feature representations for the goal and tone classifiers.",
        "**SciPy and statsmodels** — bootstrap confidence intervals, "
        "significance testing and correlation analysis used in Chapter 7.",
        "**Matplotlib and Seaborn** — figure generation for the research "
        "outputs reproduced in Chapter 7.",
    ]),

    ("h2", "3.4 Web Application and API Frameworks"),
    ("bullets", [
        "**FastAPI** — the backend service. Chosen because it is Python "
        "native (so the research modules are imported directly rather than "
        "invoked across a language boundary), because request and response "
        "schemas are validated automatically, and because it generates "
        "interactive API documentation used during evaluation and "
        "demonstration.",
        "**Next.js 16 with React** — the marketer dashboard: Overview, "
        "Audience, Campaigns, Analytics, Content and Research pages, plus "
        "authentication and site-onboarding flows.",
        "**Recharts** — funnel, attribution and prediction charts in the "
        "dashboard, matching the visualisation design specified at the "
        "interim stage.",
        "**Streamlit** — retained only for the standalone research "
        "dashboards used during module development; superseded in the "
        "integrated system by the Next.js dashboard.",
    ]),

    ("h2", "3.5 Data Storage and Infrastructure"),
    ("bullets", [
        "**PostgreSQL 16** — the single shared data layer. Relational "
        "storage was appropriate because the four modules exchange "
        "well-structured entities with strict referential relationships "
        "(a segment belongs to a visitor, an interaction belongs to a "
        "campaign), and because the honesty constraints described in "
        "Section 5.5 are enforced as database-level derivations rather than "
        "application conventions.",
        "**Docker and Docker Compose** — the database runs in a container so "
        "that the entire system can be reproduced on any machine with a "
        "single command, which matters for a research artefact that must be "
        "re-runnable by an examiner.",
    ]),

    ("h2", "3.6 Development, Testing and Version Control Tools"),
    ("bullets", [
        "**pytest** — the automated test suite (208 test functions across "
        "the platform and Module 3 suites) covering data contracts, API "
        "behaviour, tenant isolation and regression tests for each defect "
        "described in Section 6.6.",
        "**Git and GitHub** — version control, with a branch per module "
        "during independent development and integration branches for the "
        "unified system.",
        "**Make** — a task interface (`make setup`, `make db`, `make api`, "
        "`make web`, `make demo`, `make test`) that makes the reproduction "
        "path explicit.",
        "**Visual Studio Code, PyCharm and Jupyter** — development and "
        "exploratory analysis; the original module notebooks are retained "
        "for traceability.",
    ]),

    ("h2", "3.7 Deviations from the Interim Report"),
    ("p", "Two technology decisions differ from the interim report and are "
          "recorded here for transparency."),
    ("table", {"caption": "Table 2 — Technology decisions that differ from "
                          "the interim report.",
               "header": ["Interim report", "Delivered system", "Reason"],
               "rows": [
                   ["Section 3.6 states a Node.js / NestJS backend service "
                    "layer.",
                    "FastAPI (Python).",
                    "Figure 5.1 of the interim report already specified "
                    "FastAPI, so the report was internally inconsistent. "
                    "Every model is Python; a Node backend would have "
                    "required a second service and a serialisation boundary "
                    "between the API and the models, adding failure modes "
                    "for no research benefit."],
                   ["MongoDB and PostgreSQL are both named as data stores.",
                    "PostgreSQL only.",
                    "All five architecture figures in the interim report "
                    "show PostgreSQL. The data exchanged between modules is "
                    "strongly relational, and running two stores would have "
                    "split the integrity constraints that the honesty "
                    "mechanisms depend on."],
               ]}),
    ("p", "A third change is one of scope rather than technology. At the "
          "interim stage the audience was to be supplied by uploading a CSV "
          "of customers. In the delivered system the audience is collected "
          "from the client's own website through a tracking snippet. This "
          "was necessary for the research question: a cold-start study is "
          "not credible if the audience arrives pre-formed with a complete "
          "behavioural history."),

    ("h2", "3.8 Summary"),
    ("table", {"caption": "Table 3 — Summary of the adopted technology "
                          "stack by layer.",
               "header": ["Layer", "Technology", "Role in the framework"],
               "rows": [
                   ["Presentation", "Next.js 16, React, TypeScript, Recharts",
                    "Marketer dashboard, authentication, site onboarding"],
                   ["Tracking", "JavaScript (mos.js)",
                    "First-party visitor collection on the client website"],
                   ["Application", "FastAPI, Uvicorn, Pydantic",
                    "Routers, services, tenant isolation, provenance"],
                   ["Research modules", "scikit-learn, XGBoost, SHAP, "
                    "sentence-transformers, pandas, NumPy",
                    "Segmentation, automation, analytics, content"],
                   ["Data", "PostgreSQL 16, Docker",
                    "Shared tables: user_segments, interactions, "
                    "analytics_output, content_assets"],
                   ["Quality", "pytest, Git, Make",
                    "Regression tests, reproducibility, evaluation reruns"],
               ]}),
    ("p", "The stack is deliberately conventional. The research contribution "
          "of this project lies in the integration and the evaluation "
          "methodology, not in the novelty of the tools, and using "
          "well-understood components makes the results easier to "
          "reproduce and to challenge."),
]
