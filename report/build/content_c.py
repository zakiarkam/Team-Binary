# -*- coding: utf-8 -*-
"""Chapters 7-9 and the appendices."""

F = "/Users/arkamzakir/Documents/Research/Research/modules/m3_analytics/outputs/figures"

BLOCKS = [
    # ================================================== CHAPTER 7
    ("h1", "CHAPTER 7 — EVALUATION"),

    ("h2", "7.1 Metrics Used"),
    ("p", "This section defines each metric used in the evaluation and "
          "states why it is appropriate for the quantity being measured. "
          "Several of the datasets in this project are strongly imbalanced, "
          "so the choice of metric is not a formality: on the campaign "
          "response dataset a model that predicts the majority class for "
          "every user achieves 87.6 % accuracy while being of no practical "
          "use whatsoever."),

    ("h3", "7.1.1 Accuracy"),
    ("p", "The proportion of correct predictions, "
          "(TP + TN) / (TP + TN + FP + FN). Reported throughout for "
          "comparability with the literature, but never used as the "
          "headline metric where the class distribution is skewed, for the "
          "reason given above."),

    ("h3", "7.1.2 Precision"),
    ("p", "TP / (TP + FP): of the cases predicted positive, the proportion "
          "that truly are. In this project precision governs cost — a "
          "high-intent user who is not high intent receives a premium offer "
          "that is wasted, and an over-eager drop-off classifier triggers "
          "unnecessary reactivation campaigns."),

    ("h3", "7.1.3 Recall"),
    ("p", "TP / (TP + FN): of the truly positive cases, the proportion "
          "identified. Recall governs opportunity: a converting user the "
          "model fails to identify is revenue not earned. Precision and "
          "recall trade against one another, which is why both are reported "
          "for every classifier in this chapter."),

    ("h3", "7.1.4 F1-Score"),
    ("p", "The harmonic mean of precision and recall, "
          "2PR / (P + R). Two variants are reported. **Weighted F1** "
          "averages per-class F1 weighted by support and is therefore "
          "dominated by the majority class. **Macro F1** averages per-class "
          "F1 without weighting and therefore exposes failure on rare "
          "classes. Where the two diverge sharply — as they do for the "
          "campaign-goal classifier in Section 7.5.1 — macro F1 is the "
          "number to read."),

    ("h3", "7.1.5 ROC-AUC and PR-AUC"),
    ("p", "ROC-AUC is the probability that a randomly chosen positive case "
          "is ranked above a randomly chosen negative one; 0.5 is chance. "
          "It is threshold-independent, which suits this project because the "
          "predictive models are used for *ranking* audiences rather than "
          "for hard classification. PR-AUC summarises the "
          "precision–recall curve and is more informative than ROC-AUC "
          "under heavy imbalance; its baseline is the positive base rate, "
          "not 0.5, and it is interpreted against that floor throughout."),

    ("h3", "7.1.6 MAE, R² and Spearman correlation"),
    ("p", "For the regression and attribution tasks, **mean absolute "
          "error (MAE)** measures average deviation in the units of the "
          "quantity itself — for attribution, credit share. **R²** measures "
          "the proportion of variance explained; a negative R² means the "
          "model performs worse than predicting the mean, which is a "
          "meaningful and reportable outcome. **Spearman rank correlation** "
          "is reported alongside R² for the engagement model because that "
          "model is used to rank content rather than to predict an absolute "
          "value."),

    ("h3", "7.1.7 Silhouette coefficient"),
    ("p", "For clustering, the silhouette coefficient [58] compares each "
          "point's mean intra-cluster distance with its mean distance to the "
          "nearest other cluster, on a scale from −1 to 1. It measures "
          "geometric separation only, and this project reports it alongside "
          "a downstream marketing measure precisely because the two can "
          "disagree."),

    ("h3", "7.1.8 Bootstrap confidence intervals and significance"),
    ("p", "Differences between automation strategies are small in absolute "
          "terms, so point estimates alone would not support a conclusion. "
          "Non-parametric bootstrap resampling [57] with 95 % percentile "
          "confidence intervals and associated p-values is used wherever a "
          "strategy or attribution comparison is claimed."),
    ("table", {"caption": "Table 13 — Evaluation metrics by module and task.",
               "header": ["Module", "Task", "Primary metric",
                          "Supporting metrics"],
               "rows": [
                   ["M1", "Segmentation", "Downstream conversion separation",
                    "Silhouette, method agreement, segment stability"],
                   ["M1", "Confidence model", "Held-out accuracy",
                    "Feature-leakage audit"],
                   ["M2", "Strategy comparison", "Conversions per 1,000 "
                    "messages", "Open rate, CTR, days-to-convert, complexity"],
                   ["M2", "Response model", "ROC-AUC and PR-AUC",
                    "Accuracy against dummy floor, feature importance"],
                   ["M3", "Funnel", "Stage drop-off rate",
                    "Overall conversion rate by segment and strategy"],
                   ["M3", "Attribution", "MAE against ground truth",
                    "Bootstrap CI, credit distribution"],
                   ["M3", "Prediction", "ROC-AUC (external validation)",
                    "CV AUC, precision, recall, F1, SHAP, calibration"],
                   ["M3", "Recommendation", "Accuracy vs rule baseline",
                    "Per-class precision, recall, F1, agreement"],
                   ["M4", "Goal / tone classification", "Macro F1",
                    "Accuracy, weighted F1, cross-validated F1"],
                   ["M4", "Engagement regression", "R² and Spearman",
                    "MAE against mean baseline"],
                   ["M4", "Content quality", "Composite score",
                    "Semantic similarity, platform fit, human baseline"],
               ]}),

    ("h2", "7.2 Module 1 — Audience Targeting and Personalization"),

    ("h3", "7.2.1 Segment distribution and downstream conversion"),
    ("p", "The hybrid engine was run over the 8,000-user Digital Marketing "
          "Campaign dataset. Conversion is used only to *evaluate* the "
          "resulting segments — it is never supplied as a clustering "
          "feature — so the separation reported below is not circular."),
    ("table", {"caption": "Table 14 — Hybrid segmentation output on the "
                          "8,000-user dataset, with downstream conversion.",
               "header": ["Segment", "Users", "Share", "Conversion rate"],
               "rows": [
                   ["High Intent", "813", "10.2 %", "**91.8 %**"],
                   ["Loyal Customer", "2,247", "28.1 %", "91.0 %"],
                   ["Price Sensitive", "1,393", "17.4 %", "87.9 %"],
                   ["Low Engagement", "3,384", "42.3 %", "86.0 %"],
                   ["New Cold User", "163", "2.0 %", "**53.4 %**"],
                   ["**Total / spread**", "**8,000**", "100 %",
                    "**38.4 pp separation**"],
               ]}),
    ("p", "The engine separates the highest- from the lowest-converting "
          "segment by **38.4 percentage points**. The commercially "
          "important result is the New Cold User segment: 163 users whose "
          "conversion rate of 53.4 % is roughly 33 points below every other "
          "segment. These are exactly the users a launch-stage marketing "
          "system must treat differently, and they are the users that pure "
          "clustering cannot isolate."),

    ("h3", "7.2.2 Geometric quality versus marketing usefulness"),
    ("p", "The same clustering achieves a **silhouette coefficient of "
          "0.087**. This is a low value: the clusters overlap heavily and "
          "are not geometrically clean. Additionally, **41 % of users "
          "receive three different labels** from the three methods, which "
          "is why the confidence score is exported alongside the label "
          "rather than discarded."),
    ("p", "The two results are reported together because they disagree, and "
          "the disagreement is the finding. Judged as a clustering problem "
          "the segmentation is mediocre; judged as a marketing instrument — "
          "does it group users who behave differently in the way that "
          "matters commercially? — it separates conversion by 38.4 points. "
          "A study that reported only the silhouette would have discarded a "
          "useful segmentation; a study that reported only the conversion "
          "separation would have overstated its geometric quality."),

    ("h3", "7.2.3 Comparison against the constituent methods"),
    ("p", "At the interim stage the rule-based and K-Means segmenters were "
          "evaluated separately on the same dataset under an earlier "
          "five-segment taxonomy. The rule-based method separated its "
          "highest- and lowest-converting segments by 25.5 percentage "
          "points (92.7 % against 67.2 %), whereas K-Means produced more "
          "evenly sized but far less differentiated clusters, separated by "
          "only 7.7 points (90.9 % against 83.2 %). Critically, K-Means "
          "**failed to isolate cold-start users at all**, because a user "
          "with almost no interaction history has no distinguishing "
          "distance signature and is absorbed into the nearest centroid."),
    ("p", "This comparison motivated the hybrid design and the cold-start "
          "precedence rule. It also predicted defect D2 in Section 6.6: "
          "when the agreement vote was implemented with the clustering "
          "comparison evaluated first, the cold-start segment collapsed from "
          "43 users to zero on live data — clustering overruling the only "
          "method capable of recognising a new user."),

    ("h3", "7.2.4 Confidence model"),
    ("p", "The classifier that produces the confidence score originally "
          "reported near-perfect confidence for 6,248 of 8,000 users. "
          "Auditing revealed that the encoded vote outcome — the target "
          "itself — was present among its input features (defect D1). With "
          "the leaked feature removed, held-out accuracy is **0.92**. This "
          "is the value used by the system and reported here."),

    ("h2", "7.3 Module 2 — Marketing Automation and Campaign Management"),

    ("h3", "7.3.1 Strategy comparison"),
    ("p", "The three strategies were executed over the same 8,000-user "
          "cohort with the same templates and the same response model."),
    ("table", {"caption": "Table 15 — Automation strategy comparison over "
                          "an identical 8,000-user cohort (Module 2 "
                          "simulator).",
               "header": ["Metric", "Fixed", "Trigger", "Hybrid"],
               "rows": [
                   ["Messages sent", "32,000", "**10,596**", "24,348"],
                   ["Open rate", "24.25 %", "**24.75 %**", "23.11 %"],
                   ["Click-through rate", "4.68 %", "**4.78 %**", "4.21 %"],
                   ["Conversion rate (per user)", "**2.70 %**", "1.35 %",
                    "2.34 %"],
                   ["Conversions per 1,000 messages", "6.75", "**10.19**",
                    "7.68"],
                   ["Average days to convert", "1.36", "**0.53**", "1.21"],
                   ["Operational complexity (rules)", "**7**", "15", "19"],
               ]}),
    ("p", "The result is more interesting than a simple ranking. The fixed "
          "workflow achieves the highest per-user conversion rate — but "
          "only by sending three times as many messages as the trigger "
          "strategy. Measured by **efficiency**, the ordering reverses "
          "completely: the trigger strategy converts **10.19 users per "
          "1,000 messages against the fixed workflow's 6.75**, a 51 % "
          "improvement, and it converts them in 0.53 days rather than 1.36."),
    ("p", "This exposes a trade-off that reporting conversion rate alone "
          "would conceal. A fixed workflow buys conversions with volume, at "
          "a cost in send expense, list fatigue and deliverability that the "
          "conversion rate does not show. The hybrid strategy sits between "
          "the two on every metric — and carries the highest operational "
          "complexity at 19 rules against the fixed workflow's 7. For a "
          "small organisation, that near-tripling of the rule surface is a "
          "real maintenance cost that the marketing literature rarely "
          "quantifies."),

    ("h3", "7.3.2 Campaign response model"),
    ("p", "The response model was fitted with a stratified dummy classifier "
          "reported alongside it, because the dataset's base rate is 0.876."),
    ("table", {"caption": "Table 16 — Campaign response model performance "
                          "against a dummy baseline (base rate 0.876).",
               "header": ["Model", "Accuracy", "ROC-AUC", "PR-AUC",
                          "Precision", "Recall", "F1"],
               "rows": [
                   ["Dummy (majority)", "0.8762", "0.5000", "0.8762",
                    "0.8762", "1.0000", "0.9340"],
                   ["Logistic regression", "0.8931", "0.7873", "0.9460",
                    "0.8953", "0.9943", "0.9422"],
                   ["Random forest", "**0.8950**", "**0.8055**", "**0.9491**",
                    "0.8955", "0.9964", "**0.9433**"],
               ]}),
    ("p", "Accuracy is almost uninformative here: the random forest's "
          "0.8950 exceeds the dummy's 0.8762 by less than two points. The "
          "meaningful signal is in the ranking metrics. ROC-AUC rises from "
          "0.5000 (chance) to **0.8055**, and PR-AUC rises from the base "
          "rate floor of 0.8762 to **0.9491**. The model discriminates; it "
          "simply cannot demonstrate that through accuracy on a dataset "
          "this imbalanced."),
    ("p", "The gap between random forest and logistic regression on ROC-AUC "
          "is only 0.018, which suggests the signal in these features is "
          "largely linear with limited interaction structure. The most "
          "important features are engagement score (0.117), click-through "
          "rate (0.078), conversion rate (0.077), advertising spend (0.076) "
          "and pages per visit (0.073) — behavioural rather than "
          "demographic, consistent with the segmentation design in "
          "Module 1."),

    ("h2", "7.4 Module 3 — Marketing Analytics and Decision Support"),

    ("h3", "7.4.1 Funnel construction and drop-off"),
    ("p", "The funnel was constructed over 2,000 simulated users and 10,000 "
          "campaign sends, with stage transition probabilities calibrated "
          "against the UCI Bank Marketing dataset [51] (41,188 real "
          "records), giving p(open | sent) = 0.899, p(click | open) = 0.557 "
          "and p(convert | click) = 0.198."),
    ("figure", {"path": f"{F}/funnel_overall.png",
                "caption": "Figure 8 — Overall marketing funnel: sent → "
                           "opened → clicked → converted.", "width": 5.3}),
    ("p", "The observed funnel is 10,000 sent → 7,524 opened (−24.8 %) → "
          "3,516 clicked (−53.3 %) → 1,149 converted (−67.3 %), an overall "
          "conversion rate of **11.49 %** against the 11.27 % implied by the "
          "calibration targets — confirming that the simulator reproduces "
          "the real-data transition structure it was fitted to. The largest "
          "single loss is at click → convert, which is where the drop-off "
          "model and the recommendation layer are directed."),
    ("figure", {"path": f"{F}/funnel_by_segment.png",
                "caption": "Figure 9 — Funnel performance disaggregated by "
                           "audience segment.", "width": 5.8}),
    ("p", "Disaggregating by segment localises the loss. Drop-off between "
          "click and conversion is highest for the **Price Sensitive** "
          "segment at **96.9 %** — these users engage readily and convert "
          "rarely, which is a pricing or offer problem rather than a "
          "targeting problem. **High Intent** is the strongest segment at "
          "**59.0 % end-to-end conversion**. This is the kind of "
          "prescriptive statement the analytics module exists to produce: "
          "it names the stage, the audience and the likely cause."),

    ("h3", "7.4.2 Automation strategy comparison with significance testing"),
    ("figure", {"path": f"{F}/funnel_by_strategy.png",
                "caption": "Figure 10 — Funnel progression by automation "
                           "strategy.", "width": 5.8}),
    ("table", {"caption": "Table 17 — Funnel and drop-off by automation "
                          "strategy (Module 3 calibrated simulator).",
               "header": ["Strategy", "Sent", "Opened", "Clicked",
                          "Converted", "Drop click→convert",
                          "Overall conversion"],
               "rows": [
                   ["Fixed", "3,320", "2,476", "1,158", "334", "71.16 %",
                    "10.06 %"],
                   ["Trigger", "3,339", "2,498", "1,168", "391", "66.52 %",
                    "11.71 %"],
                   ["Hybrid", "3,341", "2,550", "1,190", "424",
                    "**64.37 %**", "**12.69 %**"],
               ]}),
    ("figure", {"path": f"{F}/eval_strategy_comparison.png",
                "caption": "Figure 11 — Strategy comparison across funnel "
                           "stages and conversion.", "width": 5.9}),
    ("p", "Under the calibrated simulator the hybrid strategy converts best, "
          "and the improvement survives significance testing."),
    ("table", {"caption": "Table 18 — Bootstrap 95 % confidence intervals "
                          "for conversion rate and strategy lift.",
               "header": ["Quantity", "Point estimate", "95 % CI",
                          "p-value"],
               "rows": [
                   ["Conversion rate — fixed", "0.1006",
                    "[0.0909, 0.1108]", "—"],
                   ["Conversion rate — trigger", "0.1171",
                    "[0.1057, 0.1278]", "—"],
                   ["Conversion rate — hybrid", "0.1269",
                    "[0.1159, 0.1390]", "—"],
                   ["Lift: trigger vs fixed", "+16.4 %",
                    "[+2.3 %, +33.5 %]", "0.012"],
                   ["Lift: hybrid vs fixed", "**+26.2 %**",
                    "[+10.1 %, +44.6 %]", "**< 0.001**"],
               ]}),
    ("p", "Both lifts are statistically significant at the 5 % level and the "
          "hybrid lift is significant at the 0.1 % level. The confidence "
          "intervals are wide — the trigger interval reaches down to +2.3 % "
          "— which is honest information about the strength of the "
          "conclusion, and a reason to prefer the hybrid result."),
    ("note", "The two simulators disagree, and the disagreement is "
             "informative. Module 2's simulator (Table 15) ranks the fixed "
             "workflow highest on per-user conversion; Module 3's calibrated "
             "simulator (Table 17) ranks it lowest. The reconciliation is "
             "message volume: Module 2's trigger strategy sends only a third "
             "as many messages, which depresses per-user conversion while "
             "raising conversion per message. Module 3's simulator holds "
             "send volume approximately constant across strategies, which "
             "isolates policy quality from send volume. The consistent "
             "finding across both is that behaviour-aware strategies are "
             "more *efficient* per message; the per-user conversion ranking "
             "depends on how many messages a strategy is permitted to send."),

    ("h3", "7.4.3 Attribution modelling against ground truth"),
    ("p", "Because the simulator generates journeys from known per-channel "
          "influence weights, the true credit distribution is available and "
          "each attribution model can be scored against it — a comparison "
          "that observational marketing data cannot support."),
    ("figure", {"path": f"{F}/attribution_comparison.png",
                "caption": "Figure 12 — Platform-level attribution credit: "
                           "three models compared against known ground "
                           "truth.", "width": 6.0}),
    ("p", "The ground-truth credit distribution generated by the simulator "
          "is LinkedIn 37.2 %, email 29.8 %, Instagram 18.5 %, TikTok 8.9 % "
          "and Facebook 5.1 %. Figure 12 shows the three models deviating "
          "from it in systematically different directions rather than "
          "randomly."),
    ("bullets", [
        "**First-touch** over-credits email (31.9 % against 29.8 %) and "
        "under-credits LinkedIn (33.8 % against 37.2 %) — it rewards the "
        "channel that opens the journey.",
        "**Last-touch** over-credits Instagram by 6.3 percentage points "
        "(24.8 % against 18.5 %) while under-crediting email (26.6 %) and "
        "almost halving Facebook (2.9 % against 5.1 %) — it rewards "
        "whichever channel happens to be last.",
        "**Multi-touch** tracks ground truth most closely across the "
        "distribution, recovering email at 29.3 % against a true 29.8 % and "
        "LinkedIn at 33.3 % against 37.2 %.",
    ]),
    ("p", "The two single-touch models therefore disagree about the same "
          "journeys in opposite directions: first-touch says email creates "
          "the audience, last-touch says Instagram closes it, and each is "
          "blind to the other's evidence. An organisation relying on "
          "last-touch alone would over-invest in Instagram and cut the "
          "email spend that first-touch and ground truth both show to be "
          "responsible for roughly 30 % of conversion credit."),
    ("figure", {"path": f"{F}/attribution_mae.png",
                "caption": "Figure 13 — Mean absolute error of each "
                           "attribution model against known ground-truth "
                           "credit.", "width": 5.3}),
    ("table", {"caption": "Table 19 — Attribution accuracy against "
                          "ground truth, with bootstrap confidence "
                          "intervals (lower MAE is better).",
               "header": ["Attribution model", "MAE", "95 % CI"],
               "rows": [
                   ["Multi-touch (weighted)", "**0.0178**",
                    "[0.0102, 0.0250]"],
                   ["First-touch", "0.0178", "[0.0124, 0.0316]"],
                   ["Last-touch", "0.0260", "[0.0183, 0.0358]"],
                   ["Markov (removal effect)", "0.0525", "[0.0467, 0.0575]"],
               ]}),
    ("p", "Three findings follow. **Last-touch is measurably the worse of "
          "the two single-touch models**, with 46 % higher error than "
          "multi-touch — and it is the model most widely used in practice "
          "because it is the easiest to compute. **Multi-touch attribution "
          "is the most reliable**, matching first-touch on point estimate "
          "but with a tighter confidence interval. **Markov attribution is "
          "the worst performer here**, at nearly three times the error of "
          "multi-touch — not because the method is inferior in principle, "
          "but because removal-effect estimation requires far more "
          "converting journeys than a cold-start scenario provides. That is "
          "a direct, quantified demonstration of the cold-start constraint "
          "this project set out to study."),
    ("figure", {"path": f"{F}/attribution_channel.png",
                "caption": "Figure 14 — Channel-level attribution credit "
                           "(rolled up) under the three models.",
                "width": 5.6}),
    ("p", "Rolled up to the channel level (Figure 14) the three models "
          "agree far more closely — social carries 61–68 % of credit and "
          "email 24–29 % under all three. The disagreement is therefore "
          "concentrated *within* the social channel, at exactly the level "
          "of granularity at which a marketer must choose which platform to "
          "produce content for, which is why Module 4 consumes the "
          "platform-level rather than the channel-level distribution."),
    ("figure", {"path": f"{F}/eval_attribution_study.png",
                "caption": "Figure 15 — Attribution study: platform credit "
                           "for four models against ground truth (left) and "
                           "recovery error (right).", "width": 6.2}),
    ("p", "Figure 15 adds the Markov model to the comparison. It "
          "over-credits Instagram (23.1 %) and TikTok (13.9 % against a "
          "true 8.9 %) while under-crediting LinkedIn by more than ten "
          "points (26.9 % against 37.2 %) — the largest deviations of any "
          "model, and the reason for its error of 0.0525."),
    ("p", "The system-level insight generated from this analysis reads: "
          "*email leads first-touch (31.9 %) but loses credit in last-touch, "
          "while Instagram gains the most last-touch credit (24.8 %) — use "
          "email for acquisition and Instagram for closing.* This is passed "
          "to Module 4 as the platform generation priority."),

    ("h3", "7.4.4 Conversion and drop-off prediction"),
    ("p", "Three algorithms were fitted for each of the two targets, with "
          "five-fold cross-validation."),
    ("table", {"caption": "Table 20 — Conversion and drop-off model "
                          "performance on simulated data (five-fold CV).",
               "header": ["Target", "Model", "Accuracy", "Precision",
                          "Recall", "F1", "AUC", "CV AUC (mean ± sd)"],
               "rows": [
                   ["Conversion", "Logistic regression", "0.9035", "0.5491",
                    "0.9000", "0.6820", "0.9678", "0.9624 ± 0.0066"],
                   ["Conversion", "Random forest", "**0.9510**", "**0.9125**",
                    "0.6348", "**0.7487**", "0.9712", "0.9687 ± 0.0049"],
                   ["Conversion", "XGBoost", "0.9010", "0.5402", "**0.9348**",
                    "0.6847", "**0.9756**", "**0.9722 ± 0.0038**"],
                   ["Drop-off", "Logistic regression", "0.8865", "0.9433",
                    "0.8745", "0.9076", "0.9299", "0.9318 ± 0.0059"],
                   ["Drop-off", "Random forest", "**0.9510**", "0.9475",
                    "**0.9773**", "**0.9622**", "0.9867", "0.9840 ± 0.0027"],
                   ["Drop-off", "XGBoost", "0.9475", "**0.9563**", "0.9616",
                    "0.9589", "**0.9902**", "**0.9879 ± 0.0006**"],
               ]}),
    ("figure", {"path": f"{F}/eval_roc_conversion.png",
                "caption": "Figure 16 — ROC curves for the conversion "
                           "prediction models.", "width": 5.4}),
    ("figure", {"path": f"{F}/eval_roc_drop_off.png",
                "caption": "Figure 17 — ROC curves for the drop-off risk "
                           "models.", "width": 5.4}),
    ("figure", {"path": f"{F}/eval_cm_conversion.png",
                "caption": "Figure 18 — Confusion matrix, conversion model.",
                "width": 4.6}),
    ("figure", {"path": f"{F}/eval_cm_drop_off.png",
                "caption": "Figure 19 — Confusion matrix, drop-off model.",
                "width": 4.6}),
    ("p", "The precision–recall trade-off is visible and operationally "
          "meaningful. For conversion, the random forest achieves precision "
          "of 0.9125 at recall 0.6348, while XGBoost achieves recall 0.9348 "
          "at precision 0.5402. Which is preferable depends on the cost "
          "asymmetry: for an expensive premium offer, precision matters "
          "more; for a cheap reminder email, recall matters more. The "
          "system therefore exposes the probability and lets the "
          "recommendation layer choose the threshold, rather than fixing one."),

    ("h3", "7.4.5 External validation: quantifying simulator optimism"),
    ("p", "AUC values near 0.99 on simulated data should not be believed. In "
          "a simulator, the events used as features and the events that "
          "define the label are produced by the same generative process, so "
          "some degree of leakage is structural. Rather than argue about "
          "the magnitude of this effect, the models were re-fitted and "
          "re-evaluated on the real UCI Bank Marketing dataset [51]."),
    ("table", {"caption": "Table 21 — Model AUC on simulated data versus "
                          "the real UCI Bank Marketing dataset.",
               "header": ["Model", "Simulated AUC", "Real-data AUC",
                          "Optimism"],
               "rows": [
                   ["Logistic regression", "1.0000", "0.9438", "0.0562"],
                   ["Random forest", "0.9794", "0.9492", "0.0302"],
                   ["XGBoost", "0.9934", "**0.9535**", "0.0399"],
               ]}),
    ("figure", {"path": f"{F}/validation_auc_comparison.png",
                "caption": "Figure 20 — Model AUC on simulated data "
                           "compared with the real UCI Bank Marketing "
                           "dataset.", "width": 5.4}),
    ("p", "Simulator optimism is between 3.0 and 5.6 AUC points, and "
          "logistic regression — which reached a perfect 1.0 on simulated "
          "data — is the most inflated. **The honest headline figure for "
          "this module is therefore AUC 0.9535**, obtained by XGBoost on "
          "real behavioural data, and that is the figure reported in the "
          "abstract and conclusion. The simulated values remain in the "
          "report, clearly labelled, because the difference between them is "
          "itself a methodological result: a study reporting only the "
          "simulated AUC would have overstated its models by up to five "
          "points."),

    ("h3", "7.4.6 Model explainability"),
    ("figure", {"path": f"{F}/shap_importance_conversion.png",
                "caption": "Figure 21 — SHAP feature importance for the "
                           "conversion model.", "width": 5.6}),
    ("figure", {"path": f"{F}/shap_importance_drop_off.png",
                "caption": "Figure 22 — SHAP feature importance for the "
                           "drop-off risk model.", "width": 5.6}),
    ("table", {"caption": "Table 22 — Top SHAP features (mean absolute "
                          "SHAP value) for both predictive models.",
               "header": ["Rank", "Conversion model", "Value",
                          "Drop-off model", "Value"],
               "rows": [
                   ["1", "Number of clicks", "4.708", "Number of opens",
                    "3.601"],
                   ["2", "Recency (days)", "0.504", "Number of clicks",
                    "2.769"],
                   ["3", "Segment: High Intent", "0.486", "Recency (days)",
                    "0.370"],
                   ["4", "Number sent", "0.314", "Segment: High Intent",
                    "0.324"],
                   ["5", "Avg. time between events", "0.295",
                    "Segment: New Cold User", "0.259"],
                   ["6", "Segment: Loyal Customer", "0.180",
                    "Segment: Low Engagement", "0.214"],
               ]}),
    ("p", "Two observations. First, **click behaviour dominates conversion "
          "prediction** by an order of magnitude over every other feature — "
          "consistent with the measurement decision in Section 6.2.2 to "
          "treat sent → click as the reliable signal and to distrust open "
          "tracking. Second, **the segment labels produced by Module 1 "
          "appear among the top features of both models**, with High Intent "
          "third in the conversion model and New Cold User fifth in the "
          "drop-off model. This is direct quantitative evidence that "
          "Module 1's output carries predictive value into Module 3, which "
          "is the integration effect the literature review found to be "
          "asserted but rarely measured."),

    ("h3", "7.4.7 Recommendation generation"),
    ("p", "A supervised recommender was trained to reproduce and improve on "
          "the rule-based recommendation engine, and evaluated on a "
          "held-out set of 2,000 journeys."),
    ("table", {"caption": "Table 23 — Learned recommender against the "
                          "rule-based baseline (n = 2,000 held-out "
                          "journeys).",
               "header": ["Recommender", "Test accuracy",
                          "Agreement with rules"],
               "rows": [
                   ["Rule-based baseline", "0.8280", "—"],
                   ["Learned recommender", "**0.9440**", "0.8215"],
               ]}),
    ("table", {"caption": "Table 24 — Per-class performance of the learned "
                          "recommender.",
               "header": ["Recommended action", "Precision", "Recall", "F1",
                          "Support"],
               "rows": [
                   ["Send general reminder", "0.9562", "0.9796", "0.9678",
                    "1,716"],
                   ["Send reactivation campaign", "1.0000", "1.0000",
                    "**1.0000**", "54"],
                   ["Send premium offer", "0.8212", "0.7500", "0.7840",
                    "196"],
                   ["Send personalised offer", "0.6667", "0.1765",
                    "**0.2791**", "34"],
               ]}),
    ("p", "The learned recommender improves on the rule baseline by **11.6 "
          "percentage points** while agreeing with it on 82.2 % of cases — "
          "it has learned the rules and corrected them, rather than "
          "replacing them with something unrelated. Reactivation campaigns "
          "are identified perfectly, because dormancy is a clean signal."),
    ("p", "The honest weakness is the personalised-offer class: recall of "
          "**0.1765** on 34 support means the model finds fewer than one in "
          "five of the users who should receive a personalised offer. With "
          "34 examples in the test set this class is simply too rare to "
          "learn — an instance of the cold-start problem appearing inside "
          "the recommendation layer itself. In deployment the rule engine "
          "therefore retains authority over this class, and the report does "
          "not claim a capability the evidence does not support."),

    ("h2", "7.5 Module 4 — AI Content Refinery and Multi-Platform "
           "Distribution"),

    ("h3", "7.5.1 Campaign goal and tone classification"),
    ("p", "Two feature representations were compared for each target on the "
          "same corpus and the same held-out split."),
    ("table", {"caption": "Table 25 — Goal and tone classification: TF-IDF "
                          "with logistic regression against Sentence-BERT "
                          "with XGBoost.",
               "header": ["Target", "Representation", "Accuracy",
                          "Weighted F1", "Macro F1", "Test rows"],
               "rows": [
                   ["Campaign goal", "**TF-IDF + logistic regression**",
                    "**0.8022**", "**0.8001**", "**0.5391**", "91"],
                   ["Campaign goal", "Sentence-BERT + XGBoost", "0.7692",
                    "0.7291", "0.3793", "91"],
                   ["Tone", "**TF-IDF + logistic regression**", "**0.8857**",
                    "**0.8672**", "**0.7227**", "35"],
                   ["Tone", "Sentence-BERT + XGBoost", "0.8000", "0.7560",
                    "0.5136", "35"],
               ]}),
    ("p", "**The simpler representation won for both targets.** TF-IDF with "
          "logistic regression outperformed Sentence-BERT with XGBoost on "
          "every metric, and the margin is widest on macro F1 (0.539 against "
          "0.379 for goal; 0.723 against 0.514 for tone). With a corpus of "
          "453 and 173 labelled rows respectively, the high-dimensional "
          "embedding model has too little data to exploit its capacity — a "
          "result consistent with the cold-start theme of the project, and a "
          "useful counterweight to the assumption that a transformer "
          "embedding is always the stronger choice."),
    ("p", "The gap between weighted and macro F1 is the number to read. For "
          "campaign goal, weighted F1 of 0.800 sits beside macro F1 of "
          "0.539, because the *awareness* class accounts for more than half "
          "the corpus (54 of 91 test rows) and is classified well (F1 "
          "0.904), while *engagement* has two test examples and is never "
          "predicted correctly (F1 0.000) and *retention* has four (F1 "
          "0.400). Accuracy flatters a model that handles rare classes "
          "badly, and this report states that plainly."),
    ("p", "Cross-validated performance, which is more trustworthy on a "
          "corpus this small than any single split, is **weighted F1 0.763 "
          "± 0.091** for goal and **0.903 ± 0.073** for tone."),

    ("h3", "7.5.2 Engagement prediction — a negative result"),
    ("p", "The engagement regressor was trained on 12,000 social-media posts "
          "with 13 text and platform features, and with an explicit leakage "
          "guard excluding likes, comments, shares, impressions and "
          "engagement rate — the components from which the target is "
          "derived."),
    ("table", {"caption": "Table 26 — Engagement regression against a mean "
                          "baseline (12,000 posts, leakage-guarded).",
               "header": ["Model", "MAE", "R²", "Spearman ρ",
                          "Beats baseline?"],
               "rows": [
                   ["Baseline (predict mean)", "**0.3278**", "≈ 0.000",
                    "0.000", "—"],
                   ["Random forest", "0.3931", "−0.1676", "0.0120", "No"],
                   ["XGBoost", "0.3568", "−0.3011", "0.0199", "No"],
               ]}),
    ("p", "**Neither model beats predicting the mean.** Both R² values are "
          "negative and both Spearman correlations are within noise of zero, "
          "meaning the ranking the model produces over candidate content is "
          "close to arbitrary. Before the leakage guard was applied the same "
          "model reported R² ≈ 0.99 (defect D4, Section 6.6); the entire "
          "apparent performance was the model reading its own target."),
    ("p", "Investigation established that this is a property of the dataset "
          "rather than of the modelling: **no text feature in the corpus "
          "correlates significantly with engagement** — every feature "
          "returns p > 0.16. Engagement on social platforms is driven by "
          "factors absent from the post text, principally platform ranking "
          "algorithms, posting time, follower composition and trending "
          "topics."),
    ("p", "Three responses were taken rather than removing the model. The "
          "component's weight in content scoring was reduced from an "
          "originally intended **0.45 to 0.20**, with the freed weight "
          "moved to semantic similarity and platform suitability (0.40 "
          "each), both of which are deterministic and verifiable. The "
          "model's own metrics file records the verdict *“no demonstrated "
          "skill on this dataset”*. And the dashboard displays that verdict "
          "next to the score, so a marketer is not shown a number that "
          "implies more than it means."),

    ("h3", "7.5.3 Content quality and platform suitability"),
    ("p", "Generated assets are ranked by a composite of semantic similarity "
          "to the source business summary (weight 0.40), rule-based platform "
          "suitability (0.40) and predicted engagement (0.20). Semantic "
          "similarity is measured by Sentence-BERT cosine similarity [53] "
          "and guards against the generator introducing claims the business "
          "does not make — the principal safety risk in AI-generated "
          "marketing copy. Platform suitability is a deterministic, "
          "auditable check of length, hashtag count, emoji use and required "
          "structure per platform."),
    ("p", "A human-baseline harness scores manually written marketing copy "
          "through the identical pipeline, so that any comparison between "
          "AI-generated and human content is made on one scale. The "
          "platform generation order is supplied by Module 3's attribution "
          "output, which is the closing link of the loop: the platform that "
          "measurably earned conversion credit is the platform for which "
          "content is generated first."),

    ("h2", "7.6 Overall System Evaluation"),

    ("h3", "7.6.1 Integration"),
    ("p", "System-level evaluation asks a different question from module "
          "evaluation: not whether each part works, but whether joining them "
          "produces anything. Four pieces of evidence are offered."),
    ("table", {"caption": "Table 27 — Evidence that the loop closes.",
               "header": ["Integration link", "Evidence", "Where reported"],
               "rows": [
                   ["Module 1 → Module 3",
                    "Segment labels appear among the top SHAP features of "
                    "both predictive models (High Intent 3rd for conversion; "
                    "New Cold User 5th for drop-off).", "§7.4.6"],
                   ["Module 1 → Module 2",
                    "Segment-conditional response propensity is an input to "
                    "the hybrid policy, which achieves the highest measured "
                    "conversion (+26.2 %, p < 0.001).", "§7.4.2"],
                   ["Module 2 → Module 3",
                    "Strategy is a feature of the predictive models and a "
                    "dimension of the funnel; drop-off differs measurably by "
                    "strategy (64.4 % vs 71.2 % at click→convert).",
                    "§7.4.1–7.4.2"],
                   ["Module 3 → Module 4",
                    "Attribution credit sets platform generation order; the "
                    "generated insight (“email for acquisition, Instagram "
                    "for closing”) is consumed directly.", "§7.4.3"],
                   ["Module 4 → Module 2",
                    "The highest-scoring content asset becomes the opening "
                    "message of the next campaign plan.", "§4.6"],
               ]}),
    ("p", "The strongest of these is the first, because it is quantitative "
          "and was not designed to be flattering: SHAP was computed to "
          "explain the models, and the segment features earned their places "
          "in the ranking on their own. Integration in this framework is "
          "therefore not only architectural but measurable."),

    ("h3", "7.6.2 Results against the objectives"),
    ("table", {"caption": "Table 28 — Achievement of the nine objectives "
                          "stated in Section 1.4.2.",
               "header": ["#", "Objective", "Status", "Principal evidence"],
               "rows": [
                   ["1", "Hybrid segmentation engine, evaluated against its "
                         "constituents", "Achieved",
                    "38.4 pp conversion separation; silhouette 0.087 "
                    "reported alongside (§7.2)"],
                   ["2", "Three automation strategies compared under "
                         "identical conditions", "Achieved",
                    "Tables 15 and 17; efficiency reversal identified "
                    "(§7.3.1)"],
                   ["3", "Funnel and drop-off analysis by stage, segment and "
                         "strategy", "Achieved",
                    "Figures 8–11; Price Sensitive 96.9 % click→convert "
                    "drop-off (§7.4.1)"],
                   ["4", "Five attribution models compared against ground "
                         "truth", "Achieved",
                    "MAE 0.0178 multi-touch vs 0.0260 last-touch vs 0.0525 "
                    "Markov (§7.4.3)"],
                   ["5", "Calibrated predictive models validated on real "
                         "data", "Achieved",
                    "AUC 0.9535 on UCI Bank Marketing; optimism quantified "
                    "at 3.0–5.6 pts (§7.4.5)"],
                   ["6", "Ranked recommendations; learned vs rule baseline",
                    "Achieved with a stated limit",
                    "94.4 % vs 82.8 %; personalised-offer recall 0.177 "
                    "reported (§7.4.7)"],
                   ["7", "AI content refinery with scored assets",
                    "Achieved with a negative result",
                    "TF-IDF beats SBERT on both targets; engagement model "
                    "has no skill (§7.5)"],
                   ["8", "Integrated multi-tenant platform with live "
                         "audience", "Achieved",
                    "FastAPI + PostgreSQL + Next.js; 208 tests; isolation "
                    "test (§6.4–6.5)"],
                   ["9", "Mechanisms preventing simulated results being "
                         "reported as measured", "Achieved",
                    "Derived provenance flags, generated research page, "
                    "refusal thresholds (§5.5)"],
               ]}),

    ("h3", "7.6.3 Discussion"),
    ("p", "Three themes run through the results."),
    ("p", "**Integration produces measurable, if modest, gains.** The "
          "hybrid strategy — the only one that uses input from all of "
          "scheduling, behaviour, segmentation and prediction — converts "
          "26.2 % better than a fixed workflow with a p-value below 0.001, "
          "and segment labels earn top-five SHAP positions in both "
          "predictive models. The gains are real but not dramatic, and this "
          "report resists inflating them: the confidence intervals are "
          "wide, and the hybrid strategy costs nearly three times the "
          "operational complexity of the fixed workflow. Whether that "
          "trade is worth making is an organisational decision that the "
          "evidence informs rather than settles."),
    ("p", "**The cold-start constraint is visible everywhere once it is "
          "measured.** It appears as K-Means failing to isolate new users; "
          "as Markov attribution performing worst of five models because it "
          "lacks converting journeys; as the personalised-offer class being "
          "unlearnable at 34 examples; and as Sentence-BERT losing to "
          "TF-IDF on a 453-row corpus. These are four independent "
          "manifestations of one underlying condition, and together they "
          "constitute the project's clearest empirical finding: under "
          "cold-start conditions, the simpler and more constrained method "
          "usually wins."),
    ("p", "**Honest evaluation changes conclusions.** Every one of the six "
          "defects in Section 6.6 inflated a result, and none produced an "
          "error. Had they gone undetected, this report would have claimed "
          "a segmentation confidence of 1.00, an engagement model with R² "
          "0.99, and a cold-start contribution whose segment had silently "
          "become empty. The system-level lesson is that a research "
          "platform should be built so that self-deception is difficult — "
          "derived rather than asserted provenance, external validation "
          "against real data, and explicit refusal when evidence is "
          "insufficient."),

    ("h2", "7.7 Threats to Validity and Limitations"),
    ("table", {"caption": "Table 29 — Threats to validity and how they are "
                          "handled or bounded.",
               "header": ["Threat", "Impact", "Mitigation / current status"],
               "rows": [
                   ["The live funnel is driven by simulated visitors; the "
                    "machinery is real, the audience is not.",
                    "External validity of live-operation claims.",
                    "Every figure is badged real / simulated / mixed; "
                    "provenance is derived at write time and cannot be "
                    "asserted."],
                   ["Module 3's predictive models were fitted on simulated "
                    "journeys.",
                    "Absolute probabilities and thresholds do not transfer "
                    "to a live audience; ranking does.",
                    "External validation on UCI Bank Marketing; optimism "
                    "quantified at 3.0–5.6 AUC points; 0.9535 reported as "
                    "the headline."],
                   ["Open-rate tracking is unreliable because mail clients "
                    "block or pre-fetch the pixel.",
                    "sent → open is systematically under-reported.",
                    "sent → click is used as the reliable signal; SHAP "
                    "confirms clicks dominate conversion prediction."],
                   ["The engagement corpus contains no usable text signal "
                    "(all features p > 0.16).",
                    "Predicted engagement cannot rank content reliably.",
                    "Reported as a negative result; weight reduced 0.45 → "
                    "0.20; verdict shown in the interface."],
                   ["Small labelled corpora (453 goal, 173 tone rows); "
                    "the humorous tone class has one example.",
                    "Rare-class performance is poor and unstable.",
                    "Macro F1 and cross-validated F1 with standard "
                    "deviations reported; the humorous class is not claimed."],
                   ["Both automation comparisons rely on simulators, which "
                    "disagree on per-user conversion ranking.",
                    "Strategy ranking is conditional on send-volume policy.",
                    "Both results reported side by side with the "
                    "reconciliation stated explicitly (§7.4.2)."],
                   ["Three real platform datasets could not be used.",
                    "Reduced breadth of real-world content evidence.",
                    "They are comment-level scrapes that pair no post text "
                    "with post engagement; this is stated rather than "
                    "concealed."],
               ]}),

    ("h2", "7.8 Summary"),
    ("p", "All four modules were evaluated against competing methods and "
          "naive baselines. Hybrid segmentation separates conversion by "
          "38.4 points while retaining a cold-start segment that clustering "
          "destroys; the hybrid automation strategy improves conversion by "
          "26.2 % (p < 0.001) at nearly three times the operational "
          "complexity; multi-touch attribution matches ground truth 46 % "
          "more closely than last-touch; the predictive models reach AUC "
          "0.9535 on real data after simulator optimism is removed; the "
          "learned recommender improves on its rule baseline by 11.6 points; "
          "and in the content module the simpler text representation wins "
          "while the engagement regressor is reported as having no "
          "demonstrable skill. The integration itself is evidenced "
          "quantitatively through SHAP."),

    # ================================================== CHAPTER 8
    ("h1", "CHAPTER 8 — CONCLUSION"),

    ("h2", "8.1 Conclusion"),
    ("p", "This project set out to determine whether the four principal "
          "functions of digital marketing — audience targeting, campaign "
          "automation, analytics and content production — can be operated "
          "as a single measurable feedback loop, and whether such a loop "
          "remains useful for a newly launched product that has almost no "
          "data. Both questions are answered affirmatively, with "
          "qualifications that the evaluation makes explicit."),
    ("p", "A complete, running, multi-tenant platform was delivered: four "
          "research modules behind a FastAPI service over PostgreSQL, a "
          "Next.js dashboard, and a first-party tracking snippet through "
          "which any organisation can register its website and obtain its "
          "own segmentation, campaigns, analytics and content. The system "
          "is reproducible from a clean checkout and is covered by 208 "
          "automated tests."),
    ("p", "The nine objectives of Section 1.4.2 were met (Table 28). "
          "Substantively, the project establishes four things. The **hybrid "
          "segmentation engine** separates conversion by 38.4 percentage "
          "points while retaining a cold-start segment that pure clustering "
          "eliminates entirely. The **controlled comparison of automation "
          "strategies** shows a statistically significant 26.2 % conversion "
          "improvement for the hybrid policy, while also revealing an "
          "efficiency reversal that a conversion-rate-only analysis would "
          "have concealed. **Ground-truth attribution scoring** — made "
          "possible by a simulator with known channel influence — shows "
          "last-touch attribution to be 46 % less accurate than multi-touch, "
          "and Markov attribution to fail outright under cold-start data "
          "volumes. And the **integration itself is measurable**: Module 1's "
          "segment labels appear among the top five SHAP features of both "
          "of Module 3's predictive models."),
    ("p", "The project's methodological contribution is of comparable "
          "weight. Six defects were found in the team's own research code, "
          "every one of which had inflated a result without producing an "
          "error. Their correction changed the headline figures materially "
          "— a segmentation confidence of 1.00 became 0.92, an engagement "
          "R² of 0.99 became −0.30, and a cold-start segment that had "
          "silently emptied to zero was restored. This experience shaped "
          "the design: provenance flags derived at write time rather than "
          "asserted, a research page generated from disk rather than "
          "written by hand, refusal thresholds that suppress output the data "
          "cannot support, and external validation on real data for every "
          "model fitted on simulated data."),
    ("p", "The clearest empirical theme is that **under cold-start "
          "conditions the simpler, more constrained method usually wins**. "
          "Rule-based logic outperforms clustering at identifying new users; "
          "TF-IDF outperforms Sentence-BERT on small labelled corpora; "
          "multi-touch attribution outperforms Markov when converting "
          "journeys are scarce. This is not an argument against "
          "sophisticated methods but a statement about when they pay: "
          "capacity requires data to exploit it, and at launch that data "
          "does not exist."),
    ("p", "The limitations are stated plainly in Section 7.7 and are not "
          "minor. The live funnel is still driven by simulated visitors; "
          "the predictive models' thresholds do not transfer to a live "
          "audience even though their ranking does; open-rate tracking is "
          "unreliable by construction; and the engagement regressor has no "
          "demonstrable skill on the available corpus. These are reported "
          "as findings rather than concealed as gaps, because a framework "
          "whose purpose is to help marketers trust their measurements "
          "cannot be evaluated by a standard lower than the one it "
          "advocates."),

    ("h2", "8.2 Future Work"),
    ("numbers", [
        "**Live-audience validation.** The most valuable next step is a "
        "field deployment with a real launch-stage product, replacing "
        "simulated visitors with tracked ones and re-fitting the predictive "
        "models on measured journeys so that thresholds, and not only "
        "rankings, transfer.",
        "**Adaptive strategy selection.** The three automation strategies "
        "are currently compared offline. A contextual-bandit or "
        "reinforcement-learning layer could select the policy per segment "
        "online, using the conversion signal already collected, with the "
        "operational-complexity measure as an explicit cost term.",
        "**A content corpus with genuine engagement signal.** The negative "
        "engagement result is a data problem, not a modelling one. "
        "Collecting post-level text paired with post-level engagement from "
        "the platform's own campaigns — which the tracking layer already "
        "supports — would allow the model to be retrained and its weight "
        "restored if it earns it.",
        "**Growing the labelled goal and tone corpora.** Both classifiers "
        "are limited by corpus size rather than by method; active learning "
        "over the assets the platform already generates would expand the "
        "rare classes that currently fail.",
        "**Richer attribution under sparsity.** Shapley-value and Bayesian "
        "attribution should be evaluated against the same ground truth to "
        "establish whether any data-driven method is usable at cold-start "
        "journey volumes, given that Markov attribution is not.",
        "**Multimodal content generation.** The framework generates image "
        "prompts and video briefs but not the assets themselves; "
        "integrating generation and extending the platform-suitability "
        "scorer to visual assets is a natural extension.",
        "**Privacy and regulatory hardening.** The tracking layer is "
        "first-party and honours Do Not Track, but consent management, data "
        "retention policy and GDPR-style subject-access support would be "
        "required for commercial deployment.",
    ]),
    ("p", "The framework as delivered is a research instrument that happens "
          "to be a working product. Its value lies less in any single model "
          "than in demonstrating that the four marketing functions can be "
          "operated as one loop, that the effect of doing so can be "
          "measured rather than asserted, and that a system can be built to "
          "make its own results harder to overstate."),

    # ================================================== CHAPTER 9
    ("h1", "CHAPTER 9 — REFERENCES"),
    ("bullets", []),
    ("p", "[1] D. A. Aaker and C. Moorman, *Strategic Market Management*, "
          "11th ed. Hoboken, NJ, USA: Wiley, 2017."),
    ("p", "[2] C. C. Aggarwal, *Data Mining: The Textbook*. Cham, "
          "Switzerland: Springer, 2015."),
    ("p", "[3] M. Alves Gomes and T. Meisen, “A review on customer "
          "segmentation methods for personalized customer targeting in "
          "e-commerce use cases,” *Information Systems and e-Business "
          "Management*, vol. 21, no. 3, pp. 527–570, 2023."),
    ("p", "[4] A. Banks and E. Porcello, *Learning React: Modern Patterns "
          "for Developing React Apps*, 2nd ed. Sebastopol, CA, USA: "
          "O’Reilly Media, 2020."),
    ("p", "[5] J. Bobadilla, F. Ortega, A. Hernando, and A. Gutiérrez, "
          "“Recommender systems survey,” *Knowledge-Based Systems*, "
          "vol. 46, pp. 109–132, 2013."),
    ("p", "[6] T. B. Brown et al., “Language models are few-shot learners,” "
          "*Advances in Neural Information Processing Systems*, vol. 33, "
          "pp. 1877–1901, 2020."),
    ("p", "[7] S. Chacon and B. Straub, *Pro Git*, 2nd ed. Berkeley, CA, "
          "USA: Apress, 2014."),
    ("p", "[8] D. Chaffey and F. Ellis-Chadwick, *Digital Marketing: "
          "Strategy, Implementation and Practice*, 8th ed. Harlow, UK: "
          "Pearson, 2022."),
    ("p", "[9] D. Chaffey, T. Hemphill, and D. Edmundson-Bird, *Digital "
          "Business and E-Commerce Management*, 8th ed. Harlow, UK: "
          "Pearson, 2024."),
    ("p", "[10] D. Court, D. Elzinga, S. Mulder, and O. J. Vetvik, “The "
          "consumer decision journey,” *McKinsey Quarterly*, vol. 3, "
          "pp. 96–107, 2009."),
    ("p", "[11] B. Dalessandro, C. Perlich, O. Stitelman, and F. Provost, "
          "“Causally motivated attribution for online advertising,” in "
          "*Proc. 6th Int. Workshop on Data Mining for Online Advertising "
          "and Internet Economy (ADKDD)*, 2012, pp. 1–9."),
    ("p", "[12] T. H. Davenport, A. Guha, D. Grewal, and T. Bressgott, “How "
          "artificial intelligence will change the future of marketing,” "
          "*Journal of the Academy of Marketing Science*, vol. 48, no. 1, "
          "pp. 24–42, 2020."),
    ("p", "[13] Y. K. Dwivedi et al., “Artificial Intelligence (AI): "
          "Multidisciplinary perspectives on emerging challenges, "
          "opportunities, and agenda for research, practice and policy,” "
          "*International Journal of Information Management*, vol. 57, "
          "Art. no. 101994, 2021."),
    ("p", "[14] A. Géron, *Hands-On Machine Learning with Scikit-Learn, "
          "Keras, and TensorFlow*, 3rd ed. Sebastopol, CA, USA: O’Reilly "
          "Media, 2022."),
    ("p", "[15] I. Goodfellow, Y. Bengio, and A. Courville, *Deep "
          "Learning*. Cambridge, MA, USA: MIT Press, 2016."),
    ("p", "[16] J. Han, J. Pei, and H. Tong, *Data Mining: Concepts and "
          "Techniques*, 4th ed. Cambridge, MA, USA: Morgan Kaufmann, 2022."),
    ("p", "[17] T. Hastie, R. Tibshirani, and J. Friedman, *The Elements of "
          "Statistical Learning: Data Mining, Inference, and Prediction*, "
          "2nd ed. New York, NY, USA: Springer, 2009."),
    ("p", "[18] M. Haverbeke, *Eloquent JavaScript: A Modern Introduction "
          "to Programming*, 4th ed. San Francisco, CA, USA: No Starch "
          "Press, 2024."),
    ("p", "[19] D. Herron, *Node.js Web Development*, 5th ed. Birmingham, "
          "UK: Packt Publishing, 2020."),
    ("p", "[20] D. Hows, P. Membrey, and E. Plugge, *MongoDB Basics*. "
          "Berkeley, CA, USA: Apress, 2014."),
    ("p", "[21] M.-H. Huang and R. T. Rust, “Artificial intelligence in "
          "service,” *Journal of Service Research*, vol. 21, no. 2, "
          "pp. 155–172, 2018."),
    ("p", "[22] J. Järvinen and H. Karjaluoto, “The use of Web analytics "
          "for digital marketing performance measurement,” *Industrial "
          "Marketing Management*, vol. 50, pp. 117–127, 2015."),
    ("p", "[23] B. Johnson, *Visual Studio Code: End-to-End Editing and "
          "Debugging Tools for Web Developers*. Hoboken, NJ, USA: Wiley, "
          "2019."),
    ("p", "[24] P. Kotler, H. Kartajaya, and I. Setiawan, *Marketing 5.0: "
          "Technology for Humanity*. Hoboken, NJ, USA: Wiley, 2021."),
    ("p", "[25] P. Kotler, K. L. Keller, and A. Chernev, *Marketing "
          "Management*, 16th ed. Harlow, UK: Pearson, 2021."),
    ("p", "[26] V. Kumar, A. Dixit, R. G. Javalgi, and M. Dass, “Digital "
          "transformation of marketing: A synthesis and research agenda,” "
          "*Journal of Business Research*, vol. 122, pp. 779–792, 2021."),
    ("p", "[27] V. Kumar and W. Reinartz, *Customer Relationship "
          "Management: Concept, Strategy, and Tools*, 3rd ed. Berlin, "
          "Germany: Springer, 2018."),
    ("p", "[28] J. Li, D. Li, C. Xiong, and S. C. H. Hoi, “BLIP: "
          "Bootstrapping language-image pre-training for unified "
          "vision-language understanding and generation,” in *Proc. Int. "
          "Conf. Machine Learning (ICML)*, 2022, pp. 12888–12900."),
    ("p", "[29] S. M. Lundberg and S.-I. Lee, “A unified approach to "
          "interpreting model predictions,” *Advances in Neural Information "
          "Processing Systems*, vol. 30, pp. 4765–4774, 2017."),
    ("p", "[30] G. Magolan, P. Housley, A. de Peretti, J. Bell, and "
          "D. Guijarro, *Nest.js: A Progressive Node.js Framework*. "
          "Birmingham, UK: Packt Publishing, 2019."),
    ("p", "[31] B. Marr and M. Ward, *Artificial Intelligence in Practice: "
          "How 50 Successful Companies Used AI and Machine Learning to "
          "Solve Problems*. Hoboken, NJ, USA: Wiley, 2019."),
    ("p", "[32] W. McKinney, *Python for Data Analysis*, 3rd ed. "
          "Sebastopol, CA, USA: O’Reilly Media, 2022."),
    ("p", "[33] C. Molnar, *Interpretable Machine Learning*, 2nd ed., 2022."),
    ("p", "[34] S. Murray, *Interactive Data Visualization for the Web: An "
          "Introduction to Designing with D3*, 2nd ed. Sebastopol, CA, USA: "
          "O’Reilly Media, 2017."),
    ("p", "[35] R. O. Obe and L. S. Hsu, *PostgreSQL: Up and Running*, "
          "3rd ed. Sebastopol, CA, USA: O’Reilly Media, 2017."),
    ("p", "[36] F. Pedregosa et al., “Scikit-learn: Machine learning in "
          "Python,” *Journal of Machine Learning Research*, vol. 12, "
          "pp. 2825–2830, 2011."),
    ("p", "[37] F. Provost and T. Fawcett, *Data Science for Business*. "
          "Sebastopol, CA, USA: O’Reilly Media, 2013."),
    ("p", "[38] A. Radford et al., “Learning transferable visual models "
          "from natural language supervision,” in *Proc. Int. Conf. Machine "
          "Learning (ICML)*, 2021, pp. 8748–8763."),
    ("p", "[39] P. Resnick and H. R. Varian, “Recommender systems,” "
          "*Communications of the ACM*, vol. 40, no. 3, pp. 56–58, 1997."),
    ("p", "[40] F. Ricci, L. Rokach, and B. Shapira, Eds., *Recommender "
          "Systems Handbook*, 3rd ed. New York, NY, USA: Springer, 2022."),
    ("p", "[41] M. Riva, *Real-World Next.js: Build Scalable, "
          "High-Performance, and Modern Web Applications Using Next.js*. "
          "Birmingham, UK: Packt Publishing, 2022."),
    ("p", "[42] A. I. Schein, A. Popescul, L. H. Ungar, and D. M. Pennock, "
          "“Methods and metrics for cold-start recommendations,” in *Proc. "
          "25th Annu. Int. ACM SIGIR Conf. Research and Development in "
          "Information Retrieval*, 2002, pp. 253–260."),
    ("p", "[43] X. Shao and L. Li, “Data-driven multi-touch attribution "
          "models,” in *Proc. 17th ACM SIGKDD Int. Conf. Knowledge "
          "Discovery and Data Mining*, 2011, pp. 258–264."),
    ("p", "[44] R. S. Sutton and A. G. Barto, *Reinforcement Learning: An "
          "Introduction*, 2nd ed. Cambridge, MA, USA: MIT Press, 2018."),
    ("p", "[45] L. Tunstall, L. von Werra, and T. Wolf, *Natural Language "
          "Processing with Transformers*. Sebastopol, CA, USA: O’Reilly "
          "Media, 2022."),
    ("p", "[46] J. VanderPlas, *Python Data Science Handbook*, 2nd ed. "
          "Sebastopol, CA, USA: O’Reilly Media, 2022."),
    ("p", "[47] A. Vaswani et al., “Attention is all you need,” *Advances "
          "in Neural Information Processing Systems*, vol. 30, "
          "pp. 5998–6008, 2017."),
    ("p", "[48] S. Verma, R. Sharma, S. Deb, and D. Maitra, “Artificial "
          "intelligence in marketing: Systematic review and future research "
          "direction,” *International Journal of Information Management "
          "Data Insights*, vol. 1, no. 1, Art. no. 100002, 2021."),
    ("p", "[49] M. Wedel and P. K. Kannan, “Marketing analytics for "
          "data-rich environments,” *Journal of Marketing*, vol. 80, no. 6, "
          "pp. 97–121, 2016."),
    ("p", "[50] T. Zhang, V. Kishore, F. Wu, K. Q. Weinberger, and "
          "Y. Artzi, “BERTScore: Evaluating text generation with BERT,” in "
          "*Proc. Int. Conf. Learning Representations (ICLR)*, 2020."),
    ("p", "[51] S. Moro, P. Cortez, and P. Rita, “A data-driven approach to "
          "predict the success of bank telemarketing,” *Decision Support "
          "Systems*, vol. 62, pp. 22–31, 2014."),
    ("p", "[52] T. Chen and C. Guestrin, “XGBoost: A scalable tree boosting "
          "system,” in *Proc. 22nd ACM SIGKDD Int. Conf. Knowledge "
          "Discovery and Data Mining*, 2016, pp. 785–794."),
    ("p", "[53] N. Reimers and I. Gurevych, “Sentence-BERT: Sentence "
          "embeddings using Siamese BERT-networks,” in *Proc. Conf. "
          "Empirical Methods in Natural Language Processing (EMNLP-IJCNLP)*, "
          "2019, pp. 3982–3992."),
    ("p", "[54] S. Ramírez, “FastAPI documentation,” 2024. [Online]. "
          "Available: https://fastapi.tiangolo.com"),
    ("p", "[55] Vercel Inc., “Next.js documentation,” 2025. [Online]. "
          "Available: https://nextjs.org/docs"),
    ("p", "[56] The PostgreSQL Global Development Group, “PostgreSQL 16 "
          "documentation,” 2024. [Online]. Available: "
          "https://www.postgresql.org/docs/16/"),
    ("p", "[57] B. Efron and R. J. Tibshirani, *An Introduction to the "
          "Bootstrap*. New York, NY, USA: Chapman & Hall, 1993."),
    ("p", "[58] P. J. Rousseeuw, “Silhouettes: A graphical aid to the "
          "interpretation and validation of cluster analysis,” *Journal of "
          "Computational and Applied Mathematics*, vol. 20, pp. 53–65, "
          "1987."),

    # ================================================== APPENDIX A
    ("h1", "APPENDIX A — INDIVIDUAL CONTRIBUTION"),
    ("p", "The project was divided into four research modules, one per team "
          "member, with integration, evaluation and reporting shared. Each "
          "member owned the design, implementation, evaluation and "
          "documentation of their module, and contributed to the integrated "
          "platform."),

    ("h2", "A.1  215001G — Aadhil M. H. M."),
    ("h3", "Module 4 — AI Content Refinery and Multi-Platform Distribution"),
    ("p", "I was responsible for the design, implementation and evaluation "
          "of the AI content refinery. I built the website crawler that "
          "extracts a client's own page copy, headings and product "
          "descriptions, and the knowledge-base component that condenses "
          "them into a business summary and brand vocabulary used as the "
          "grounding for every generated asset. During this work I "
          "diagnosed and fixed a character-encoding fault in which the HTTP "
          "library defaulted to ISO-8859-1 for `text/html` responses whose "
          "headers omitted a charset, corrupting every non-ASCII character "
          "in a client's marketing copy before it reached the generator."),
    ("p", "I assembled and labelled the campaign-goal and tone corpus and "
          "implemented both classifiers as a controlled comparison — TF-IDF "
          "with logistic regression against Sentence-BERT embeddings with "
          "XGBoost — with per-target model selection on held-out "
          "performance. I found and corrected the corpus filtering defect "
          "(D5) in which a row was required to clear the confidence "
          "threshold for both targets although the classifiers train "
          "independently, which had reduced the usable corpus from 527 rows "
          "to 114. I reported macro F1 alongside accuracy because the "
          "*awareness* class dominates the corpus and accuracy alone "
          "flattered the model."),
    ("p", "I implemented the platform-aware generation engine producing "
          "captions, hashtags, calls to action, image prompts and "
          "short-video briefs per platform, and fixed the defect (D6) in "
          "which the `shorts` platform declared a video visual type but had "
          "no visual options defined, so the selector silently returned a "
          "static image brief."),
    ("p", "I built the three-component scoring framework — semantic "
          "similarity, rule-based platform suitability and predicted "
          "engagement — and the human-baseline harness that scores manually "
          "written copy through the identical pipeline. The most "
          "consequential piece of this work was negative: I discovered that "
          "the engagement regressor had been trained with likes, comments, "
          "shares and impressions among its features while predicting a "
          "ratio derived from them (D4). Adding an explicit leakage guard "
          "moved R² from 0.99 to −0.30. I then established that no text "
          "feature in the corpus correlates with engagement at all "
          "(every p > 0.16), reduced the component's weight in content "
          "scoring from 0.45 to 0.20, and made the model's own verdict "
          "visible in the interface rather than removing the result."),
    ("p", "I also diagnosed the macOS OpenMP conflict between XGBoost and "
          "PyTorch that terminated training runs and API workers with no "
          "traceback, and implemented the guard module now imported first in "
          "every entry point. I wrote the Module 4 sections of this report "
          "and contributed to the evaluation and demonstration."),

    ("h2", "A.2  215015D — Arqam Z. H."),
    ("h3", "Module 3 — Marketing Analytics and Decision Support"),
    ("p", "I was responsible for the analytics and decision-support module, "
          "which is the component through which the framework's feedback "
          "loop closes. I designed and implemented the nine-component "
          "pipeline described in Table 11 and the calibrated journey "
          "simulator on which the controlled experiments depend, "
          "calibrating its stage transition probabilities against the "
          "41,188-record UCI Bank Marketing dataset rather than choosing "
          "them by hand, and writing the PyTest suite that verifies schema "
          "correctness, event ordering, segment validity and attribution "
          "integrity of the generated data."),
    ("p", "I implemented funnel construction and drop-off analysis "
          "disaggregated by stage, segment, channel and automation "
          "strategy, which produced the finding that the Price Sensitive "
          "segment loses 96.9 % of its users between click and conversion — "
          "a pricing problem rather than a targeting problem, and the kind "
          "of prescriptive statement the module exists to produce."),
    ("p", "I implemented five attribution models and, more importantly, the "
          "evaluation method for them. Because my simulator generates each "
          "journey from known per-channel influence weights, the true "
          "credit distribution is available, so each model could be scored "
          "by mean absolute error against ground truth — a comparison "
          "observational marketing data cannot support. This produced the "
          "result that last-touch attribution, the model most widely used "
          "in practice, carries 46 % higher error than multi-touch, and "
          "that Markov attribution fails outright at cold-start journey "
          "volumes with nearly three times the error."),
    ("p", "I built the journey-level feature matrix and the conversion and "
          "drop-off models, comparing logistic regression, random forest "
          "and XGBoost with five-fold cross-validation, probability "
          "calibration, bootstrap confidence intervals and SHAP "
          "explanations. Recognising that AUC values near 0.99 on simulated "
          "data should not be believed, I added external validation on the "
          "real UCI Bank Marketing dataset, which quantified simulator "
          "optimism at 3.0 to 5.6 AUC points and established 0.9535 as the "
          "honest headline figure for the module. The SHAP analysis also "
          "produced the project's clearest evidence of integration: "
          "Module 1's segment labels appear among the top five features of "
          "both models."),
    ("p", "I implemented the rule-based recommendation engine and the "
          "supervised recommender trained to improve on it, measuring an "
          "11.6-point accuracy gain at 82.2 % agreement, and reported "
          "honestly that the personalised-offer class reaches only 0.177 "
          "recall on 34 examples and must remain under rule-engine "
          "authority. I designed the refusal guard that suppresses "
          "attribution below five converting journeys and raises "
          "calibration warnings on degenerate predictions, and the "
          "bootstrap significance testing used for every strategy claim in "
          "Chapter 7."),
    ("p", "Beyond my module I contributed to the integration architecture — "
          "the shared schema, the analytics API routes and the dashboard's "
          "analytics page — and to the research-integrity mechanisms, in "
          "particular the principle that provenance flags must be derived "
          "at write time rather than asserted by the caller. I compiled and "
          "wrote this final report."),

    ("h2", "A.3  215110N — Sarah M. M. F."),
    ("h3", "Module 1 — Audience Targeting and Personalization"),
    ("p", "I was responsible for the hybrid segmentation engine, the first "
          "module in the pipeline and the source of the segment taxonomy "
          "used by every other module. I prepared and preprocessed the "
          "8,000-user Digital Marketing Campaign dataset — missing-value "
          "handling, categorical encoding, feature scaling and the derived "
          "behavioural features (engagement score, click ratio, recency) — "
          "and established the five-segment taxonomy shared across the "
          "system."),
    ("p", "I implemented all three segmentation methods as peers over a "
          "common feature matrix: a rule-based segmenter encoding marketing "
          "heuristics, K-Means clustering and Ward-linkage agglomerative "
          "clustering. I then designed the agreement vote that combines "
          "them and produces a confidence score, and evaluated the hybrid "
          "engine against each constituent method."),
    ("p", "The evaluation produced two results I consider central to the "
          "project. First, the engine separates the highest- from the "
          "lowest-converting segment by 38.4 percentage points while "
          "retaining a New Cold User segment that K-Means cannot isolate at "
          "all — because a user with almost no interaction history has no "
          "distinguishing distance signature. Second, the same clustering "
          "achieves a silhouette coefficient of only 0.087, and 41 % of "
          "users receive three different labels from the three methods. I "
          "reported both, because the disagreement between geometric "
          "quality and marketing usefulness is itself the finding, and "
          "because it is the reason the confidence score is exported "
          "alongside the label rather than discarded."),
    ("p", "I found and corrected two defects in my own module. The first "
          "(D1) was that the confidence classifier had been trained with "
          "its own target present among its input features, which had "
          "produced confidence of exactly 1.00 for 6,248 of 8,000 users; "
          "with the leaked feature removed, honest held-out accuracy is "
          "0.92. The second (D2) was the more serious: the agreement vote "
          "evaluated the clustering comparison before the cold-start rule, "
          "so clustering overruled the only method capable of recognising a "
          "new user, and the New Cold User segment fell from 43 users to "
          "zero on live data — erasing the module's novel contribution from "
          "its own output. I reordered the vote so the cold-start rule takes "
          "precedence, and added a regression test. I also replaced the "
          "hardcoded cluster-index naming (D3) with names derived from "
          "cluster centroids at run time, so the engine remains correct on a "
          "new audience and a new random seed."),
    ("p", "I implemented the minimum-audience rule under which the engine "
          "declines to cluster below 30 visitors and states why, and the "
          "second feature domain (`web_segmenter`) that segments live "
          "tracked visitors on page views, scroll depth and session "
          "features rather than on email history, which a first-time "
          "visitor does not have. I wrote the Module 1 sections of this "
          "report."),

    ("h2", "A.4  215129F — Zanar M. H. M. R. A."),
    ("h3", "Module 2 — Marketing Automation and Campaign Management"),
    ("p", "I was responsible for the campaign automation and management "
          "module, which consumes segments from Module 1 and produces the "
          "interaction log that Module 3 analyses. I designed the module as "
          "a controlled experiment rather than a single implementation: the "
          "campaign policy engine is the only component that differs "
          "between the three strategies, while the profile builder, "
          "response model, message templates, event simulator and evaluator "
          "are shared, so that any measured difference is attributable to "
          "the policy alone."),
    ("p", "I implemented all three strategies — fixed workflow, "
          "trigger-based and hybrid — behind a common interface, together "
          "with the message template library and the event simulation layer "
          "that converts campaign actions into sent, opened, clicked, "
          "ignored and converted events with segment-conditional response "
          "propensities. During early integration I built the mock "
          "segmentation file with the agreed schema so that my module could "
          "be developed in parallel with Module 1 and later swapped to the "
          "real output without changing the automation logic."),
    ("p", "I implemented the campaign response model and made the "
          "deliberate decision to fit and report a stratified dummy "
          "classifier alongside it. The dataset's base rate is 0.876, so a "
          "model can reach 87.6 % accuracy by predicting the majority class "
          "for every user; publishing the dummy result in the same table "
          "makes that floor visible and prevents accuracy from being read "
          "as evidence of skill. The meaningful result is that ROC-AUC "
          "rises from 0.5000 at chance to 0.8055, and PR-AUC from the base "
          "rate floor of 0.8762 to 0.9491."),
    ("p", "I designed the operational complexity measure that counts the "
          "distinct decision rules and branch points each strategy "
          "requires, because effectiveness alone is not a sufficient basis "
          "for an engineering choice. This produced what I consider my "
          "module's most useful finding: the fixed workflow achieves the "
          "highest per-user conversion rate but only by sending three times "
          "as many messages as the trigger strategy, and measured by "
          "conversions per thousand messages the ordering reverses entirely "
          "— 10.19 for trigger against 6.75 for fixed, a 51 % improvement, "
          "at less than half the time to conversion. The hybrid strategy "
          "sits between them on every outcome metric while requiring nearly "
          "three times the rule surface of the fixed workflow, which is a "
          "real maintenance cost for a small organisation."),
    ("p", "I contributed the campaign execution and action-plan routes to "
          "the integrated API, the tracked-link mechanism that allows a "
          "conversion to be matched back to the click that earned it even "
          "when the company sends the message through its own tools, and "
          "the campaigns page of the dashboard. I wrote the Module 2 "
          "sections of this report."),

    # ================================================== APPENDIX B
    ("h1", "APPENDIX B — ADDITIONAL IMPLEMENTATION DETAILS"),

    ("h2", "B.1 Reproducing the System"),
    ("p", "The system is reproducible from a clean checkout. The following "
          "commands provision dependencies, start the database and "
          "services, serve a demonstration client website with the tracking "
          "snippet installed, and populate a complete end-to-end "
          "demonstration."),
    ("code", "make setup     # dependencies, browser, environment file\n"
             "make db        # PostgreSQL 16 in Docker\n"
             "make api       # FastAPI backend        (terminal 2)\n"
             "make web       # Next.js dashboard      (terminal 3)\n"
             "make site      # demo client website    (terminal 4)\n"
             "make demo      # populate a full demonstration (~60 s)\n"
             "make test      # Python suites + dashboard build"),
    ("table", {"caption": "Table 30 — Service endpoints in the running "
                          "system.",
               "header": ["Service", "Address", "Purpose"],
               "rows": [
                   ["Dashboard", "http://localhost:3000",
                    "Marketer interface (6 pages + auth)"],
                   ["Demo client website", "http://localhost:4000",
                    "Realistic tenant site with mos.js installed"],
                   ["API", "http://localhost:8000",
                    "FastAPI service"],
                   ["API documentation", "http://localhost:8000/docs",
                    "Interactive OpenAPI documentation"],
                   ["PostgreSQL", "localhost:5434",
                    "Database (non-default port to avoid collisions)"],
               ]}),

    ("h2", "B.2 Repository Structure"),
    ("code", "web/                 Next.js dashboard (6 pages + auth + onboarding)\n"
             "api/                 FastAPI backend\n"
             "  routers/           HTTP routes: sites, segments, campaigns,\n"
             "                     analytics, content, actions, tracking, auth\n"
             "  services/          module wrappers + provenance + email sender\n"
             "  static/mos.js      first-party tracking snippet\n"
             "  schema.sql         database schema\n"
             "modules/\n"
             "  m1_segmentation/   segment.py — hybrid segmentation engine\n"
             "  m2_automation/     strategy engine, simulator, evaluation\n"
             "  m3_analytics/      funnel, attribution, prediction, recommender\n"
             "demo-site/           demonstration client website\n"
             "scripts/             setup, demo data, training, threshold tuning\n"
             "tests/               platform test suite (171 test functions)\n"
             "report/assets/       architecture figures used in this report"),

    ("h2", "B.3 Test Suite Composition"),
    ("table", {"caption": "Table 31 — Automated test suite composition.",
               "header": ["Suite", "Test functions", "Coverage focus"],
               "rows": [
                   ["tests/ (platform)", "171",
                    "API foundation, tracking, segmentation, campaigns, "
                    "analytics, content, actions, auth, tenant isolation, "
                    "learning loop, pipeline"],
                   ["modules/m3_analytics/tests/", "37",
                    "Simulator schema and event ordering, funnel integrity, "
                    "attribution correctness, model pipeline"],
                   ["**Total**", "**208**",
                    "Plus a TypeScript build of the dashboard"],
               ]}),
    ("p", "Every defect listed in Table 12 has a dedicated regression test. "
          "Two structural tests guard the research-integrity properties: "
          "one fails the build if a synthetic visitor produces a row marked "
          "real, and one walks every API response asserting that numeric "
          "fields serialise as numbers rather than as strings."),

    ("h2", "B.4 Research Output Artefacts"),
    ("p", "The evaluation figures and tables in Chapter 7 are generated "
          "artefacts, not screenshots, and can be regenerated by re-running "
          "the module pipelines. They are written to:"),
    ("code", "modules/m3_analytics/outputs/figures/    funnel, attribution,\n"
             "                                         ROC, SHAP, validation\n"
             "modules/m3_analytics/outputs/reports/    model_metrics.csv,\n"
             "                                         attribution_mae.csv,\n"
             "                                         bootstrap_ci.csv,\n"
             "                                         funnel_summary.csv,\n"
             "                                         validation_comparison.csv,\n"
             "                                         insights.md\n"
             "modules/m2_automation/outputs/           strategy_comparison.csv,\n"
             "                                         ml_model_report.txt\n"
             "models/                                  goal_tone_training_metrics.json,\n"
             "                                         engagement_metrics.json\n"
             "data/integrated/model_health.json        cross-module honesty audit"),

    ("h2", "B.5 System-Generated Insight Output"),
    ("p", "The following is the verbatim system-level insight summary "
          "produced by Module 3 from the evaluation run reported in "
          "Chapter 7. It is generated, not written."),
    ("code", "Drop-off between click and convert is highest for segment\n"
             "'price_sensitive' (96.9%).\n\n"
             "Email leads first-touch (31.9%) but loses credit in last-touch,\n"
             "while Instagram gains the most last-touch credit (24.8%) —\n"
             "use Email for acquisition, Instagram for closing.\n\n"
             "Trigger strategy yields 16.4% higher conversion rate than fixed\n"
             "(11.7% vs 10.1%).\n\n"
             "'high_intent' is the highest-converting segment (59.0%\n"
             "end-to-end conversion rate)."),

    ("h2", "B.6 Cross-Module Model Health Audit"),
    ("p", "The system maintains a generated audit of every model's honest "
          "status, which the dashboard's Research page renders directly. "
          "Its findings are summarised below."),
    ("table", {"caption": "Table 32 — Generated model health audit.",
               "header": ["Model", "Level", "Finding and required "
                          "interpretation"],
               "rows": [
                   ["M2 campaign response model", "OK",
                    "Accuracy sits near the base rate due to class "
                    "imbalance; interpret with ROC-AUC and PR-AUC, not "
                    "accuracy."],
                   ["M4 campaign-goal classifier", "Caution",
                    "Small labelled set with almost no support for rare "
                    "classes; report cross-validated weighted F1 "
                    "0.763 ± 0.091, not a single split."],
                   ["M4 tone classifier", "Caution",
                    "A perfect single-split score on ~24 rows is an "
                    "overfitting signal; report CV weighted F1 "
                    "0.903 ± 0.073."],
                   ["M4 engagement regressor", "Caution",
                    "No demonstrated skill on this dataset; treat as a "
                    "relative ranker at most, and validate on real platform "
                    "exports."],
                   ["M3 conversion / drop-off models", "Caution",
                    "Simulated AUC near 1.0 is inflated; the honest figure "
                    "is the real-data validation AUC of 0.9535."],
               ]}),
]
