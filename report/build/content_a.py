# -*- coding: utf-8 -*-
"""Front matter and Chapters 1-3 of the final report.

Numbers quoted here that come from an experiment are repeated from
`research/results/results.json`. Chapter 7 is generated directly from that
file; if a headline number in this file ever disagrees with Chapter 7,
Chapter 7 is correct and this file is stale.
"""

A = "/Users/arkamzakir/Documents/Research/Research/report/assets"

FRONT_BLOCKS = [
    ("h1", "ACKNOWLEDGMENT"),
    ("p", "We wish to record our sincere gratitude to our supervisors, "
          "Dr. A. L. A. Romesh R. Thanuja and Ms. M. A. N. Perera, whose "
          "guidance shaped this project from four loosely related marketing "
          "ideas into a single research system. Their insistence that every "
          "claim be tied to a measurement — and that a measurement we could "
          "not defend should not be quoted at all — is the reason this report "
          "is able to present its negative results as findings rather than "
          "hide them."),
    ("p", "We thank the academic and technical staff of the Faculty of "
          "Information Technology, University of Moratuwa, for the knowledge "
          "and facilities that made this work possible, and the evaluation "
          "panels at the proposal and interim stages, whose questions exposed "
          "weaknesses in our methodology early enough for us to correct them. "
          "Several of the experiments in Chapter 7 exist because of those "
          "questions."),
    ("p", "We acknowledge the maintainers of the open datasets on which this "
          "study depends: the Digital Marketing Campaign dataset that forms "
          "our study audience, Kevin Hillstrom's MineThatData e-mail analytics "
          "challenge dataset, whose randomised assignment is the only reason "
          "any causal claim in this report is possible, the UCI Machine "
          "Learning Repository, and the publishers of the social-media "
          "engagement corpora used in Module 4."),
    ("p", "Finally, we thank our families and our colleagues in the Level 4 "
          "batch for their encouragement over the course of this project, and "
          "the free education system of Sri Lanka, without which none of us "
          "would have reached this point."),

    ("h1", "ABSTRACT"),
    ("p", "Digital marketing is executed through fragmented tools: one system "
          "segments an audience, another automates campaigns, a third reports "
          "analytics and a fourth generates content. Because these systems do "
          "not exchange information, the outcome of one campaign rarely "
          "improves the next. The difficulty is sharpest for a newly launched "
          "product, where almost no behavioural history exists — the "
          "cold-start condition — and where conventional data-hungry marketing "
          "models are least effective."),
    ("p", "This project designs, implements and experimentally evaluates an "
          "integrated, closed-loop marketing orchestration framework built for "
          "that condition. Four modules act on one audience over one shared "
          "database: a hybrid segmentation engine combining rule-based logic "
          "with k-means and hierarchical clustering through an agreement vote; "
          "a campaign automation engine comparing fixed, trigger-based and "
          "hybrid policies; an analytics and decision-support module providing "
          "funnel analysis, attribution, prediction, uplift modelling and "
          "off-policy evaluation; and an AI content refinery that reads the "
          "client's own website, detects what that website is actually capable "
          "of, and produces platform-specific assets. The system runs behind a "
          "FastAPI service over PostgreSQL with a Next.js dashboard. The study "
          "audience is the 8,000-customer Digital Marketing Campaign dataset, "
          "imported as the customer base of a demonstration e-commerce store."),
    ("p", "Eleven experiments, each reproducible with a single command, "
          "support every claim made. The principal results are deliberately "
          "not all favourable. **The hybrid segmentation engine does not "
          "separate conversion better than its own rules** (0.3838 against "
          "0.3837); its value lies in calibrated confidence and an explicit "
          "cold-start segment, not in separation. A target leak in the "
          "confidence model was found to inflate certainty **by a factor of "
          "150** — 450 customers at confidence 1.00 against 3 — while moving "
          "accuracy by 0.0013, showing that accuracy is not what such a defect "
          "corrupts. The simulated and live builds **disagree about which "
          "automation policy wins**, so that ranking is reported as unstable. "
          "Four attribution models disagree over **68 % of all attributed "
          "credit** on the same 7,811 converting journeys. TF-IDF and "
          "Sentence-BERT are statistically indistinguishable on the goal and "
          "tone corpora (McNemar p = 1.000 and p = 0.727), so the simpler model "
          "is chosen on cost rather than accuracy. The engagement regressor's "
          "R² of 0.99 was leakage; corrected it is −0.168, and none of eight "
          "text features survives Holm–Bonferroni correction. Targeting by "
          "uplift and by predicted response are shown on randomised data to be "
          "genuinely different policies, agreeing on only 56 % of a 30 % "
          "budget. Finally, off-policy evaluation demonstrates that without "
          "deliberate exploration the estimate of a new policy is biased "
          "**upwards** while appearing more stable, which is why the system "
          "now logs every decision with the probability it was taken under."),
    ("p", "The contribution is not any single model but the demonstration that "
          "these four functions can be operated as one measurable feedback "
          "loop under cold-start conditions, together with a methodology — "
          "derived provenance, mandatory propensity logging, generated "
          "chapters and refusal thresholds — that makes overstating a result "
          "structurally difficult."),
    ("p", "**Index Terms** — digital marketing orchestration, cold start, "
          "hybrid segmentation, marketing automation, multi-touch attribution, "
          "uplift modelling, off-policy evaluation, AI content generation, "
          "reproducible research."),
]


BODY_BLOCKS = [
    # ================================================== CHAPTER 1
    ("h1_nobreak", "CHAPTER 1 — INTRODUCTION"),

    ("h2", "1.1 Introduction"),
    ("p", "Digital marketing is the primary means by which organisations "
          "acquire, engage, convert and retain customers. A modern campaign "
          "spans email, social platforms, paid advertising, search and the "
          "organisation's own website, and every one of those channels "
          "produces behavioural data that could, in principle, improve the "
          "next campaign. In practice it rarely does. The tools that perform "
          "segmentation, automation, analytics and content production are "
          "separate products with separate data models, and the marketer is "
          "left to carry insight between them by hand."),
    ("p", "The consequence is that digital marketing is executed as a series "
          "of disconnected actions rather than as a learning process. "
          "Segmentation output does not inform the automation policy; "
          "analytics describe what already happened without prescribing what "
          "to do next; content is produced without reference to which platform "
          "actually earned the last conversion; and — the point this project "
          "arrives at only in its final stage — nothing in the pipeline records "
          "the information that would be needed to tell whether a change to "
          "the policy was an improvement. The marketing cycle does not close."),
    ("p", "This project addresses that gap directly. It designs, builds and "
          "evaluates an **AI-powered digital marketing orchestration "
          "framework** in which four research modules — audience targeting, "
          "campaign automation, analytics and decision support, and AI content "
          "refinement — operate over a single shared data layer, so that the "
          "measured outcome of one campaign becomes an input to the next. The "
          "framework targets the hardest case deliberately: a **newly launched "
          "product** for which almost no behavioural history exists."),
    ("p", "What distinguishes this report from a system description is the "
          "evidence behind it. Eleven experiments were designed and run "
          "against the delivered system; each writes its own tables, each "
          "figure in Chapter 7 is drawn from those tables rather than plotted "
          "by hand, and the chapter itself is generated from the results file. "
          "Several of those experiments returned answers the team did not "
          "want. They are reported as headlines."),

    ("h2", "1.2 Background and Motivation"),
    ("p", "Four observations motivated this work."),
    ("p", "**Fragmentation is the normal state of marketing technology.** "
          "Commercial platforms such as HubSpot, Mailchimp, Salesforce "
          "Marketing Cloud and Adobe Experience Platform each solve part of "
          "the problem well, but integration between customer intelligence, "
          "campaign execution and decision support is shallow. Academic work "
          "mirrors the division: studies address segmentation, or automation, "
          "or attribution, but seldom the interaction between them. Where "
          "integration is proposed it is usually described architecturally "
          "rather than evaluated experimentally, so the effect of joining the "
          "components is asserted rather than measured."),
    ("p", "**The cold-start condition is under-studied and commercially "
          "acute.** Most published marketing analytics assumes an established "
          "customer base with a rich interaction history. A start-up or a "
          "newly launched product has neither. Clustering algorithms need "
          "behavioural variance to form meaningful groups; predictive models "
          "need converted examples; attribution models need multi-touch "
          "journeys. At launch none of these exist in sufficient quantity, and "
          "precisely the organisations that most need marketing efficiency are "
          "the ones the literature serves least well."),
    ("p", "**Descriptive analytics is not decision support.** Existing tools "
          "report clicks, impressions and conversion counts. They say what "
          "happened; they do not say which audience to contact next, on which "
          "platform, with which message. Turning measurement into a prescribed "
          "action — and then measuring whether that action worked — is what "
          "closes the loop, and it is the part that is generally missing."),
    ("p", "**A recommendation cannot be improved unless the system records "
          "what it would take to evaluate it.** This motivation emerged during "
          "the project rather than before it. Ranking customers by predicted "
          "conversion answers the question *who is most likely to convert*, "
          "which is not the question a marketer is asking — that question is "
          "*for whom does contacting them change the outcome*. Establishing "
          "the difference required a dataset with randomised assignment, and "
          "acting on it required the system to begin logging every decision "
          "with the probability it was taken under. Both appear in Chapter 7 "
          "as experiments E8 and E9."),
    ("p", "A fifth motivation is methodological. While converting the "
          "interim-stage notebooks into a running system, the team found "
          "several defects in its own research code that had produced "
          "impressive but invalid results. Every one of them made a number "
          "look better than it was, and none produced an error message. That "
          "experience shaped the project's design as much as any requirement "
          "in the proposal, and it is documented in Section 6.7."),

    ("h2", "1.3 Problem in Brief"),
    ("p", "There is no integrated, empirically evaluated framework that "
          "unifies audience intelligence, campaign automation, "
          "attribution-aware predictive analytics and AI content generation "
          "into a single closed feedback loop that remains usable under "
          "cold-start, low-data conditions — and whose recommendations can be "
          "evaluated from the data the system itself records."),
    ("p", "This decomposes into six concrete problems:"),
    ("numbers", [
        "**Segmentation collapses under low data.** Clustering requires "
        "behavioural variance that a newly launched product does not have, "
        "and cannot represent the statement *there is not enough evidence "
        "about this person* at all — it must place everyone somewhere.",
        "**Automation policies are asserted rather than compared.** Fixed, "
        "trigger-based and hybrid campaign policies are advocated in the "
        "literature but rarely evaluated against one another on the same "
        "users under the same conditions, and rarely with operational cost "
        "reported beside outcome.",
        "**Attribution is either simplistic or unusable at launch.** "
        "Single-touch models oversimplify the journey; data-driven models "
        "such as Markov or Shapley require journey volumes a launch-stage "
        "product cannot supply. Worse, models are usually compared only with "
        "each other, because observational data has no ground truth.",
        "**Analytics does not prescribe, and prescribes the wrong thing when "
        "it does.** Funnel reports identify drop-off without recommending the "
        "correction; and a recommender that ranks by predicted response is "
        "answering a different question from the one a campaign asks.",
        "**Generated content is disconnected from performance, and from "
        "capability.** AI content tools optimise for fluency, not for the "
        "platform that produced conversions, and will happily recommend an "
        "action — *drive to checkout* — that the client's website cannot "
        "perform.",
        "**The system records no basis for its own improvement.** A "
        "deterministic policy assigns probability zero to every action it does "
        "not take, so its own logs cannot be used to estimate what a different "
        "policy would have achieved.",
    ]),

    ("h2", "1.4 Aim and Objectives"),

    ("h3", "1.4.1 Aim"),
    ("p", "To design, implement and experimentally evaluate an integrated, "
          "closed-loop, AI-powered digital marketing orchestration framework "
          "that unifies audience segmentation, campaign automation, "
          "attribution-aware predictive analytics and AI content refinement; "
          "that remains effective for newly launched products operating under "
          "cold-start and limited-data conditions; and whose every reported "
          "claim is reproducible from the system itself."),

    ("h3", "1.4.2 Objectives"),
    ("numbers", [
        "To design and implement a hybrid segmentation engine combining "
        "rule-based logic with unsupervised clustering, and to evaluate it "
        "**against each of its own components** on segment separation, "
        "geometric quality and cold-start survival.",
        "To reproduce and quantify the defects found in the project's own "
        "research code, establishing what each one actually corrupted.",
        "To implement fixed, trigger-based and hybrid campaign policies and "
        "compare them over repeated paired trials, reporting operational cost "
        "beside outcome, and to check whether the ranking is stable across "
        "how response is modelled.",
        "To implement and compare first-touch, last-touch, linear and Markov "
        "attribution against a known ground truth where one exists, and to "
        "quantify their disagreement where one does not.",
        "To build conversion and drop-off models, validate them against a "
        "baseline with intervals, and state explicitly what applying them to a "
        "different audience does and does not preserve.",
        "To determine whether the simpler text representation is genuinely "
        "competitive with a transformer embedding on the available corpora, "
        "using a test appropriate to two classifiers on one test set.",
        "To establish whether the engagement corpus contains any usable text "
        "signal, correcting for multiple comparisons, and to set the model's "
        "influence on content ranking according to the answer.",
        "To establish, on data with randomised assignment, whether targeting "
        "by uplift and targeting by predicted response are different policies "
        "— and to state carefully what that evidence does and does not "
        "support.",
        "To make the system's own recommendations evaluable by logging every "
        "decision with its propensity, and to validate the estimator against a "
        "known answer, including the cost of the exploration it requires.",
        "To detect what a client's website is actually capable of, so that the "
        "action set is a property of the site, and to measure what a larger "
        "action set costs in data.",
        "To integrate the four modules into one platform over a shared "
        "database with a dashboard, and to establish mechanisms that make "
        "presenting a reconstructed or simulated result as a measured one "
        "structurally difficult.",
    ]),

    ("h2", "1.5 Proposed Solution"),
    ("p", "The proposed solution is a four-module orchestration framework "
          "sharing one data layer. Each module is an independent research "
          "contribution that is separately evaluable, and each is also a "
          "producer and consumer of data for its neighbours. The modules are "
          "summarised below and specified in detail in Chapters 4 to 6."),

    ("h3", "1.5.1 Module 1 — Audience Targeting and Personalization"),
    ("p", "Module 1 converts raw behavioural data into labelled audience "
          "segments. Three methods run in parallel over the same feature "
          "matrix — a rule-based segmenter encoding marketing heuristics, "
          "k-means clustering and agglomerative hierarchical clustering — and "
          "their outputs are combined by an agreement vote that also yields a "
          "calibrated confidence. Five segments are shared across the system: "
          "High Intent, Loyal Customer, Price Sensitive, Low Engagement and "
          "New Cold User."),
    ("p", "The load-bearing element is the *order* of the vote. A customer "
          "with almost no history has no distinguishing behavioural signature, "
          "so clustering places them at the nearest centroid and the fact that "
          "they are new is lost. In the delivered engine the cold-start rule is "
          "resolved immediately after unanimity, **before** any clustering "
          "comparison. Section 7.3.2 shows what happens when it is not."),

    ("h3", "1.5.2 Module 2 — Marketing Automation and Campaign Management"),
    ("p", "Module 2 consumes segments and executes campaigns. Its research "
          "purpose is comparative: three policies operate on the same "
          "population under the same conditions, so that any difference is "
          "attributable to the policy alone."),
    ("bullets", [
        "**Fixed workflow** — an identical scheduled sequence for every "
        "customer; the baseline, and the cheapest to operate.",
        "**Trigger-based** — the next action is selected from the customer's "
        "most recent observed event.",
        "**Hybrid** — scheduling, behavioural triggers, segment labels and a "
        "learned response probability combined in one policy engine.",
    ]),
    ("p", "Execution produces interaction events which become the primary "
          "input to Module 3. Policies are compared on conversions per "
          "thousand messages rather than per-customer conversion rate, because "
          "the latter rewards a policy simply for sending more, and the "
          "operational cost of each policy is reported in the same table as "
          "its outcome."),

    ("h3", "1.5.3 Module 3 — Marketing Analytics and Decision Support"),
    ("p", "Module 3 is the intelligence layer. It converts the interaction log "
          "into a funnel with drop-off attributed by stage, segment and "
          "policy; a comparison of four attribution models; calibrated "
          "conversion and drop-off predictions; and ranked, actionable "
          "recommendations naming the audience, the action and the platform."),
    ("p", "Two capabilities were added after the interim stage in response to "
          "experimental findings, and they are the module's strongest "
          "contributions. **Uplift modelling** addresses the discovery that "
          "ranking by predicted response answers the wrong question. "
          "**Off-policy evaluation over a propensity-logged decision record** "
          "addresses the discovery that no borrowed dataset can answer the "
          "right question for this system's own actions — so the system must "
          "record what it needs to answer it itself, including a deliberate "
          "fraction of randomised decisions."),

    ("h3", "1.5.4 Module 4 — AI Content Refinery and Multi-Platform "
           "Distribution"),
    ("p", "Module 4 crawls the client's own website, extracts a business "
          "summary and brand vocabulary, classifies campaign goal and tone, "
          "and generates platform-specific assets — captions, hashtags, calls "
          "to action, image prompts and short-video briefs."),
    ("p", "It also performs **capability detection**: reading the site to "
          "establish what it can actually do — sell, take subscriptions, "
          "capture leads, accept donations — so that the action catalogue "
          "offered to Module 3 is a property of the website rather than a "
          "fixed list. Each generated asset is scored on semantic similarity "
          "to the source material, rule-based platform suitability and "
          "predicted engagement, with the weight of the last set by what "
          "Section 7.3.7 shows it is worth."),

    ("h3", "1.5.5 Flow of the Overall System"),
    ("p", "Figure 1 shows the end-to-end flow. The audience — 8,000 imported "
          "customers of a demonstration e-commerce store, plus any live "
          "browser sessions — is segmented by Module 1. Module 2 selects and "
          "executes a campaign action per segment. The resulting interaction "
          "events, and every decision taken with the probability it was taken "
          "under, are logged. Module 3 analyses those events and produces "
          "predictions and recommendations; Module 4 generates content for the "
          "next cycle using Module 3's platform priorities and the site's "
          "detected capabilities."),
    ("figure", {"path": f"{A}/fig01_closed_loop.png",
                "caption": "Figure 1 — Closed-loop flow of the overall "
                           "orchestration framework. The loop closes twice: "
                           "through analytics feedback, and through the "
                           "propensity-logged decision record that makes the "
                           "policy itself evaluable.", "width": 6.3}),
    ("p", "The loop is genuine rather than decorative. Module 3's attribution "
          "credit changes which platform Module 4 writes for first; the "
          "highest-scoring content asset becomes the opening message of the "
          "next campaign plan; and the decision log makes it possible to "
          "estimate what a candidate policy would have achieved without "
          "deploying it to anybody. Chapter 7 reports the measurement of each "
          "of these paths."),

    # ================================================== CHAPTER 2
    ("h1", "CHAPTER 2 — RELATED WORK"),

    ("h2", "2.1 Introduction"),
    ("p", "This chapter reviews the research this project builds on and "
          "positions the proposed framework against it. It is organised in "
          "four parts: work addressing the marketing pipeline as a whole "
          "(Section 2.2); work specific to each module (Section 2.3); work on "
          "causal targeting and off-policy evaluation, which the project "
          "reached only after its interim stage (Section 2.4); and the "
          "research gaps that follow (Section 2.5). Throughout, the review "
          "asks two questions that are decisive here — whether a technique "
          "remains usable when interaction data is scarce, and whether its "
          "output is connected to any downstream decision."),

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
          "marketing, and Chaffey and Ellis-Chadwick [8] give the operational "
          "treatment of channel-specific strategy that informs the "
          "platform-aware element of Module 4. Kumar et al. [26] review the "
          "digital transformation of marketing and note the persistent gap "
          "between the analytics an organisation collects and the decisions it "
          "actually takes — the gap Module 3 is designed to close."),
    ("p", "Verma et al. [48] conduct a systematic review of AI in marketing "
          "and report that the overwhelming majority of studies address a "
          "single function in isolation. Where a full pipeline is proposed it "
          "is generally presented as an architecture diagram rather than an "
          "implemented and measured system. Two consequences follow. First, "
          "the interaction effects between modules are unknown: whether better "
          "segmentation actually improves campaign outcomes is rarely "
          "measured, because the two are rarely measured together. Second, the "
          "cost of integration is invisible. This project responds by "
          "implementing the pipeline end to end and reporting the interaction "
          "effects it produces — including, in Section 7.3.1, one that is "
          "smaller than the team expected."),
    ("p", "Commercial systems do integrate these functions, but as closed "
          "products they publish neither their methods nor controlled "
          "comparisons, and their models are trained on the mature customer "
          "bases of established enterprises. Their cold-start behaviour is "
          "undocumented and their results are not reproducible."),

    ("h2", "2.3 Module-wise Related Work"),

    ("h3", "2.3.1 Audience Segmentation and Personalization"),
    ("p", "Customer segmentation moved from demographic rules to behavioural "
          "clustering as machine learning became routine. Han et al. [16] give "
          "the standard treatment of k-means and hierarchical clustering, and "
          "Aggarwal [2] and Hastie et al. [17] cover the assumptions each "
          "carries — in particular k-means's assumption of roughly spherical, "
          "similarly sized clusters and its requirement that *k* be fixed in "
          "advance. Alves Gomes and Meisen [3] review segmentation for "
          "e-commerce personalisation and find that cluster-quality metrics "
          "dominate the evaluation literature while downstream marketing "
          "outcomes are rarely reported."),
    ("p", "Hybrid approaches combining business rules with clustering are "
          "proposed to retain interpretability while gaining adaptability, and "
          "are reported to improve personalisation reliability relative to "
          "either alone. What that literature does not address is "
          "**arbitration**: when the rule and the cluster disagree, which "
          "wins? This project found the answer to be consequential in two "
          "separate ways. Resolving disagreement in favour of clustering "
          "silently destroys the cold-start segment (Section 7.3.2), and — "
          "measured directly against its own components — the hybrid does not "
          "separate conversion better than the rules at all (Section 7.3.1). "
          "Neither finding is available to a study that does not run the "
          "ablation."),
    ("p", "The cold-start problem itself is well characterised in recommender "
          "systems. Schein et al. [42] define the methods and metrics; "
          "Bobadilla et al. [5] and Ricci et al. [40] survey the mitigations. "
          "That work concerns recommending *items* to users with no history. "
          "The analogous marketing problem — *segmenting* users who have no "
          "history, for a product that has none either — receives markedly "
          "less attention, and is the specific gap Module 1 addresses."),

    ("h3", "2.3.2 Marketing Automation and Campaign Management"),
    ("p", "Chaffey and Ellis-Chadwick [8] document fixed-workflow campaign "
          "management and its limitations: identical sequences delivered "
          "regardless of behaviour produce low engagement and slow conversion. "
          "Davenport et al. [12] describe behaviour-triggered automation and "
          "report improved relevance at the cost of growing rule complexity. "
          "Kumar and Reinartz [27] propose a blended approach in which a "
          "stable base workflow is modulated by predicted engagement "
          "probability."),
    ("p", "Predictive campaign optimisation applies supervised learning to "
          "response prediction; Provost and Fawcett [37] set out the practical "
          "framing. Sutton and Barto [44] provide the foundation for "
          "reinforcement-learning approaches to sequential campaign decisions, "
          "attractive in principle but requiring extensive interaction "
          "histories and carefully designed rewards, which restricts them to "
          "warm-start settings."),
    ("p", "Two gaps persist. Controlled comparison is rare: the three policies "
          "are seldom run on the same users under the same conditions, so "
          "reported differences confound policy with population. And "
          "operational cost is almost never measured alongside effectiveness, "
          "although it is decisive in practice. Module 2 addresses both by "
          "running all three policies over an identical 8,000-customer cohort "
          "across thirty paired seeds, and reporting rule count and message "
          "volume beside conversion."),

    ("h3", "2.3.3 Marketing Analytics and Attribution"),
    ("p", "Funnel analysis is the established framework for locating loss in "
          "the customer journey. Court et al. [10] introduced the consumer "
          "decision journey, arguing that purchase paths are not linear, and "
          "Järvinen and Karjaluoto [22] show that stage-to-stage transition "
          "analysis is more actionable than any single aggregate metric. Its "
          "limitation is that funnel reporting is descriptive: it identifies "
          "the leak without prescribing the repair."),
    ("p", "Attribution modelling assigns conversion credit across touchpoints. "
          "First- and last-touch attribution are computationally trivial and, "
          "as Dalessandro et al. [11] argue, causally unsound — they assign all "
          "credit to one interaction on the basis of position alone. Shao and "
          "Li [43] present data-driven multi-touch attribution learning "
          "contribution weights from interaction sequences. Markov-chain and "
          "Shapley-value formulations extend this at the cost of requiring "
          "substantial journey volume."),
    ("p", "A methodological weakness runs through this literature: attribution "
          "models are usually compared with one another rather than against a "
          "known ground truth, because in observational data the true credit "
          "is unobservable. Module 3 addresses this on both sides. Where "
          "journeys are simulated the true channel influence is known by "
          "construction, so each model can be scored by mean absolute error. "
          "Where they are not, the module reports **disagreement** instead of "
          "accuracy, and Section 7.3.4 shows that disagreement to reach 68 % "
          "of all attributed credit."),

    ("h3", "2.3.4 AI Content Generation and Multi-Platform Optimisation"),
    ("p", "Transformer architectures [47] and large pre-trained language "
          "models [6] made fluent, controllable text generation practical, and "
          "Tunstall et al. [45] document the applied pipeline. Sentence "
          "embeddings [53] and BERTScore [50] provide the standard means of "
          "checking that generated text preserves source meaning, and Radford "
          "et al. [38] and Li et al. [28] extend the approach to multimodal "
          "content."),
    ("p", "Platform-aware optimisation is emphasised in the practitioner "
          "literature [8], [25]: platforms differ in length conventions, "
          "hashtag norms, formality and format expectation, so republishing "
          "one message everywhere underperforms. Rule-based platform-fit "
          "scoring is straightforward and is adopted in Module 4."),
    ("p", "Engagement prediction is the weakest link. Models are trained to "
          "predict likes, shares or engagement rate from post features, but "
          "outcomes are dominated by factors absent from the text — platform "
          "ranking algorithms, timing, follower composition, trending topics. "
          "Reported successes are frequently inflated by leakage when "
          "engagement components remain among the features. This project "
          "encountered exactly that defect in its own code and reports the "
          "corrected result — no demonstrable skill, and no text feature "
          "surviving multiple-comparison correction — as a finding rather than "
          "removing the model."),
    ("p", "Finally, the literature almost never connects content generation "
          "either to campaign analytics or to what the client can actually do. "
          "Generated content is evaluated on linguistic quality in isolation. "
          "Module 4 consumes Module 3's attribution output to order platform "
          "generation, and detects site capability so that the system does not "
          "recommend an action the website cannot perform."),

    ("h2", "2.4 Causal Targeting and Off-Policy Evaluation"),
    ("p", "This section covers the literature the project reached only after "
          "its interim evaluation, and it is where the strongest results in "
          "Chapter 7 come from."),
    ("p", "**Uplift modelling.** Radcliffe and Surry [39] and Gutierrez and "
          "Gérardy [51] formalise the distinction between predicting response "
          "and predicting the *incremental effect of an intervention*. A "
          "customer who would have converted anyway contributes to a response "
          "model's accuracy while contributing nothing to the campaign; a "
          "customer whose behaviour the message actually changes is what the "
          "campaign is for. The S-learner and T-learner formulations, and the "
          "Qini curve used to evaluate them, come from this literature. Its "
          "practical constraint is severe and is respected here: uplift is "
          "identifiable only where assignment was randomised, which is why "
          "Experiment E8 uses Hillstrom's randomised dataset [58] and why the "
          "report explicitly declines to compute uplift on its own audience."),
    ("p", "**Off-policy evaluation.** Horvitz and Thompson [59] give the "
          "inverse-propensity estimator; Dudík et al. [60] develop the "
          "doubly-robust variant; Swaminathan and Joachims [61] cover "
          "self-normalisation and its bias–variance behaviour. The core result "
          "this project depends on is that these estimators are unbiased only "
          "when every action had non-zero probability of being taken — which a "
          "deterministic policy violates by construction. Li et al. [62] "
          "demonstrate unbiased offline evaluation of news recommendation from "
          "logged data with recorded propensities. This is the literature that "
          "converts a vague intention to *learn from feedback* into a specific "
          "engineering requirement: log the propensity, and explore on "
          "purpose."),
    ("p", "What this body of work does not supply is a marketing system that "
          "actually records it. The gap Module 3 addresses is not the "
          "estimator — that is well established — but the finding, measured in "
          "Section 7.3.9, that a deterministic log looks *more* trustworthy by "
          "the usual diagnostic while being biased upwards, and the "
          "consequence that exploration has to be designed in rather than "
          "hoped for."),

    ("h2", "2.5 Research Gaps"),
    ("p", "The review identifies eight gaps that define this project's "
          "contribution."),
    ("table", {"caption": "Table 1 — Research gaps identified in the "
                          "literature and the response of this project.",
               "header": ["#", "Research gap", "How this project responds"],
               "rows": [
                   ["G1", "Segmentation, automation, analytics and content are "
                          "studied and built separately; integration is "
                          "asserted, not measured.",
                    "All four modules implemented over one shared data layer "
                    "with measured feedback paths (Ch. 5–7)."],
                   ["G2", "Cold-start marketing is under-researched; methods "
                          "assume mature customer data.",
                    "Hybrid segmentation with cold-start precedence in the "
                    "vote and a minimum-audience refusal rule (§4.2, §7.3.1)."],
                   ["G3", "Hybrid segmentation is proposed without arbitration "
                          "rules or an ablation against its own components.",
                    "Full ablation over the same customers; the negative "
                    "result reported as the headline (§7.3.1)."],
                   ["G4", "Automation policies are asserted, not compared "
                          "under controlled conditions.",
                    "Three policies, 8,000 customers, 30 paired seeds, cost "
                    "reported beside outcome (§7.3.3)."],
                   ["G5", "Attribution models are compared to each other, not "
                          "to a ground truth, and disagreement is not "
                          "quantified.",
                    "MAE against known influence where it exists; total "
                    "disagreement where it does not (§7.3.4)."],
                   ["G6", "Recommenders rank by predicted response, which is "
                          "not the question a campaign asks.",
                    "Uplift versus response compared on randomised data, with "
                    "the limits of that evidence stated (§7.3.8)."],
                   ["G7", "Marketing systems record no basis for evaluating "
                          "their own policy.",
                    "Propensity-logged decision record with deliberate "
                    "exploration; estimator validated against a known answer "
                    "(§7.3.9)."],
                   ["G8", "Content tools ignore both measured platform "
                          "performance and what the client's site can do.",
                    "Attribution-driven platform ordering and per-site "
                    "capability detection (§4.5, §7.3.10)."],
               ]}),

    ("h2", "2.6 Summary"),
    ("p", "The reviewed literature provides mature methods for each individual "
          "marketing function but leaves four things open: the behaviour of "
          "these methods when interaction data is scarce; the measured effect "
          "of connecting them into one loop; the honest evaluation of models "
          "whose reported performance is easily inflated by leakage or by "
          "evaluation on the data that generated them; and the gap between "
          "knowing that off-policy evaluation requires logged propensities and "
          "building a marketing system that records them. These four concerns "
          "shape the approach in Chapter 4, the design in Chapter 5 and the "
          "experimental programme in Chapter 7."),

    # ================================================== CHAPTER 3
    ("h1", "CHAPTER 3 — TECHNOLOGY ADAPTED"),

    ("h2", "3.1 Introduction"),
    ("p", "This chapter describes the technologies selected to implement the "
          "framework and the reasoning behind each choice. Selection was "
          "governed by four criteria: suitability for machine-learning "
          "research; the ability to run all four modules behind a single "
          "service; reproducibility, so that any reported result can be "
          "regenerated by an examiner; and modest resource requirements, since "
          "the framework targets small organisations. Section 3.7 records "
          "where the delivered stack differs from the interim report and why."),

    ("h2", "3.2 Programming Languages"),

    ("h3", "3.2.1 Python"),
    ("p", "Python 3.11 is the primary language. All four research modules, the "
          "data importer, the model training scripts, the eleven experiments, "
          "the statistics layer and the backend service are written in Python. "
          "It was selected for the maturity of its scientific stack, its "
          "dominance in machine-learning research, and because a single "
          "language across modelling and serving removes an entire class of "
          "training/serving-skew defects: the model object that produced a "
          "reported number is the same object the API loads."),

    ("h3", "3.2.2 JavaScript and TypeScript"),
    ("p", "The marketer-facing dashboard is written in TypeScript. Static "
          "typing was valuable because the dashboard consumes a wide API "
          "surface across seven pages; type errors that would otherwise appear "
          "as blank charts are caught at build time. JavaScript is also used "
          "for **mos.js**, the first-party tracking snippet installed on the "
          "site under study, which is deliberately dependency-free and small "
          "so that it does not slow the host page."),

    ("h3", "3.2.3 SQL"),
    ("p", "SQL is treated as a first-class part of the system rather than an "
          "implementation detail, because one SQL definition — "
          "`VISITOR_FEATURES_SQL` — carries a load-bearing research property. "
          "It sums imported per-visit counts and live per-page events "
          "identically, so a single feature definition serves both data "
          "sources without either having to pretend to be the other. This is "
          "explained in Section 6.2.3."),

    ("h2", "3.3 Machine Learning and Data Science Libraries"),
    ("bullets", [
        "**scikit-learn** [36] — k-means, agglomerative clustering, logistic "
        "regression, random forests, TF-IDF vectorisation, pipelines, "
        "cross-validation and the metric suite. It is the backbone of Modules "
        "1, 2 and 3 and of the text classifiers in Module 4.",
        "**XGBoost** [57] — gradient-boosted trees for conversion and drop-off "
        "prediction in Module 3, for engagement regression in Module 4, and as "
        "the base learner in the uplift S- and T-learners.",
        "**pandas and NumPy** [32], [46] — tabular handling, feature "
        "engineering and numerical computation throughout.",
        "**SciPy and statsmodels** — the Wilcoxon signed-rank test, exact "
        "binomial tests and correlation analysis underlying "
        "`research/stats.py`.",
        "**SHAP** [29] — model-agnostic explanation of the conversion and "
        "drop-off models, so predictions can be defended rather than merely "
        "reported.",
        "**sentence-transformers** [53] — Sentence-BERT embeddings for "
        "semantic similarity scoring in Module 4 and as one of the two "
        "candidate representations for the goal and tone classifiers.",
        "**Matplotlib and Seaborn** — every figure in Chapter 7, drawn by "
        "`research/figures.py` directly from the experiment tables.",
    ]),

    ("h2", "3.4 Web Application and API Frameworks"),
    ("bullets", [
        "**FastAPI** [54] — the backend service. Chosen because it is Python "
        "native, so the research modules are imported directly rather than "
        "invoked across a language boundary; because request and response "
        "schemas are validated automatically; and because it generates "
        "interactive API documentation used during evaluation and "
        "demonstration.",
        "**Next.js 16 with React** [55], [41] — the marketer dashboard: "
        "Overview, Plan, Audience, Campaigns, Analytics, Content and Research "
        "pages, plus authentication and site-onboarding flows.",
        "**Recharts** — funnel, attribution and prediction charts in the "
        "dashboard, matching the visualisation design specified at the interim "
        "stage.",
        "**Streamlit** — retained only for the standalone research dashboards "
        "used during module development; superseded in the integrated system "
        "by the Next.js dashboard.",
    ]),

    ("h2", "3.5 Data Storage and Infrastructure"),
    ("bullets", [
        "**PostgreSQL 16** [56], [35] — the single shared data layer. "
        "Relational storage was appropriate because the modules exchange "
        "well-structured entities with strict referential relationships, and "
        "because the integrity constraints described in Section 5.5 are "
        "enforced as database-level derivations rather than application "
        "conventions. It runs on port 5434 as a Homebrew service where one is "
        "available and in Docker otherwise.",
        "**Docker and Docker Compose** — the containerised database path, so "
        "the system can be reproduced on a machine with no local PostgreSQL "
        "installation.",
    ]),

    ("h2", "3.6 Development, Testing and Reproducibility Tools"),
    ("bullets", [
        "**pytest** — the automated suite: 260 collected tests covering data "
        "contracts, API behaviour, tracking, segmentation, campaign actions, "
        "content generation, authentication, tenant isolation, the decision "
        "log, the research importer, the statistics layer and the experiments "
        "themselves.",
        "**Make** — the reproduction interface. `make setup`, `make db`, "
        "`make api`, `make web`, `make site`, `make demo`, `make research` and "
        "`make test` are the whole operating surface of the project, which is "
        "what allows Chapter 7 to claim reproducibility in one command.",
        "**Git and GitHub** [7] — version control, with a branch per module "
        "during independent development and integration branches for the "
        "unified system.",
        "**Visual Studio Code, PyCharm and Jupyter** [23] — development and "
        "exploratory analysis; the original module notebooks are retained for "
        "traceability.",
    ]),

    ("h2", "3.7 Deviations from the Interim Report"),
    ("p", "Three decisions differ from the interim report and are recorded "
          "here for transparency."),
    ("table", {"caption": "Table 2 — Decisions that differ from the interim "
                          "report, and the reasoning.",
               "header": ["Interim report", "Delivered system", "Reason"],
               "rows": [
                   ["Section 3.6 states a Node.js / NestJS backend service "
                    "layer.",
                    "FastAPI (Python).",
                    "Figure 5.1 of the interim report already specified "
                    "FastAPI, so the report was internally inconsistent. Every "
                    "model is Python; a Node backend would have required a "
                    "second service and a serialisation boundary between the "
                    "API and the models, adding failure modes for no research "
                    "benefit."],
                   ["MongoDB and PostgreSQL are both named as data stores.",
                    "PostgreSQL only.",
                    "All five architecture figures in the interim report show "
                    "PostgreSQL. The data exchanged between modules is "
                    "strongly relational, and running two stores would have "
                    "split the integrity constraints that the provenance "
                    "guarantees depend on."],
                   ["The audience is supplied by uploading a CSV of "
                    "customers.",
                    "The 8,000-customer dataset is imported as the customer "
                    "base of a demonstration e-commerce store, which can also "
                    "be browsed live.",
                    "A cold-start study is not credible if the audience "
                    "arrives pre-formed. Importing the dataset through the "
                    "same tracking path a live visitor uses means one code "
                    "path, one feature definition and one provenance rule "
                    "govern both — which is what makes the live comparison in "
                    "Section 7.3.3 possible at all."],
               ]}),

    ("h2", "3.8 Summary"),
    ("table", {"caption": "Table 3 — Summary of the adopted technology stack "
                          "by layer.",
               "header": ["Layer", "Technology", "Role in the framework"],
               "rows": [
                   ["Presentation", "Next.js 16, React, TypeScript, Recharts",
                    "Marketer dashboard (7 pages), authentication, onboarding"],
                   ["Tracking", "JavaScript (mos.js)",
                    "First-party event collection on the site under study"],
                   ["Application", "FastAPI, Uvicorn, Pydantic",
                    "Routers, services, tenant isolation, decision logging, "
                    "provenance"],
                   ["Research modules",
                    "scikit-learn, XGBoost, SHAP, sentence-transformers, "
                    "pandas, NumPy",
                    "Segmentation, automation, analytics, uplift, OPE, content"],
                   ["Experiments", "Python, SciPy, statsmodels, Matplotlib",
                    "Eleven experiments, the statistics layer, every figure "
                    "in Chapter 7"],
                   ["Data", "PostgreSQL 16, Docker",
                    "user_segments, interactions, analytics_output, "
                    "action_log, content_assets"],
                   ["Quality", "pytest, Git, Make",
                    "260 tests, regression tests per defect, one-command "
                    "reproduction"],
               ]}),
    ("p", "The stack is deliberately conventional. The research contribution "
          "of this project lies in the integration and in the evaluation "
          "methodology, not in the novelty of the tools, and using "
          "well-understood components makes the results easier to reproduce "
          "and to challenge."),
]
