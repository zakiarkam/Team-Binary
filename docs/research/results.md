# RESULTS


## 3.1 Segmentation — the hybrid against its components

**Table R3 — Each method scored on the same 8,000 customers, with 95% bootstrap intervals.**

| Method | Segments | Separation | 95% CI | Cold-start segment |
|---|---|---|---|---|
| rules only | 5 | 0.3837 | [0.309, 0.464] | yes |
| k-means only | 4 | 0.0693 | [0.049, 0.090] | no |
| hierarchical only | 4 | 0.0343 | [0.019, 0.059] | no |
| hybrid (vote) | 5 | 0.3838 | [0.307, 0.463] | yes |

![Figure R1 — Conversion separation by method. The hybrid and the rules are indistinguishable; clustering alone separates almost nothing.](../../research/figures/fig_e1_segmentation_ablation.png)

*Figure R1 — Conversion separation by method. The hybrid and the rules are indistinguishable; clustering alone separates almost nothing.*

The hybrid separates conversion by 0.3838, against 0.3837 for the rules alone. The difference is within noise. Clustering on its own reaches 0.0343.

> **This is a negative result, and it is reported as the headline rather than buried.** On the separation metric the clustering contributes nothing. The hybrid earns its place in the system on different grounds — it produces a calibrated confidence from the level of agreement between three independent methods, and the vote is what makes cold start explicit — but it does not separate conversion better than a handful of interpretable rules.

Silhouette is 0.0869. The clusters overlap heavily in feature space, and all three methods disagree for 35.3% of customers. The segments are commercially useful without being geometrically clean, and reporting only the separation would hide that.

![Figure R2 — Segment sizes and conversion rate per segment.](../../research/figures/fig_e1_segment_profile.png)

*Figure R2 — Segment sizes and conversion rate per segment.*


## 3.2 Two defects, reproduced and measured


### 3.2.1 A segment deleted by its own vote

The original agreement vote tested whether the two clusterings agreed *before* it tested whether the rules had identified a cold-start customer. Clustering cannot represent “there is not enough evidence about this person” — it must place everyone somewhere — so whenever the two clusterings happened to agree, they overruled the rules. Of 163 cold-start customers the rules detect, that ordering keeps 127; on the live audience the segment went to zero. Novel Contribution 1 was being erased from its own output.

Resolving cold start immediately after unanimity keeps all 163. Those customers convert at 53.4% against 88.4% for everyone else, so the segment the original code discarded is the one with the most distinctive behaviour in the dataset.

> The general principle, and the one worth defending in a viva: **a method that cannot represent a finding does not get a vote on it.**


### 3.2.2 Target leakage in the confidence model

The Random Forest was trained with the rule label among its input features while the target was the hybrid consensus — so it was largely reading off its own answer. Reproducing both versions on the same split shows accuracy barely moves (0.9213 against 0.9200), but certainty changes by a factor of 150: 450 customers emerge at confidence 1.00 with the rule label among the inputs, against 3 without it.

Accuracy is not what the defect corrupts. The confidence attached to every downstream decision is — and a model whose accuracy is honest while its confidence is not will be trusted in exactly the cases where it should not be. That is also why the defect survived review: nothing fails, no test goes red, and the only symptom is a confidence column that looks impressive.

![Figure R3 — Both defects reproduced against their fixes.](../../research/figures/fig_e2_defects.png)

*Figure R3 — Both defects reproduced against their fixes.*


## 3.3 Automation policies — outcome against cost

**Table R4 — Policy comparison over 30 paired seeds on the Module 2 simulator.**

| Policy | Conv. per 1,000 sends | 95% range | Messages/user | Decision rules |
|---|---|---|---|---|
| fixed | 7.15 | [6.75, 7.49] | 4.0 | 1 |
| trigger | 10.45 | [9.62, 11.17] | 1.32 | 4 |
| hybrid | 7.99 | [7.45, 8.41] | 3.05 | 9 |

**Table R5 — Head-to-head, paired by seed.**

| Comparison | Mean difference | 95% CI | Wilcoxon p | Cliff's δ | Extra rules |
|---|---|---|---|---|---|
| hybrid − fixed | 0.837 | [0.727, 0.944] | 1.86e-09 | 0.991 | 8 |
| hybrid − trigger | -2.462 | [-2.574, -2.347] | 1.86e-09 | -1.0 | 5 |
| trigger − fixed | 3.299 | [3.146, 3.447] | 1.86e-09 | 1.0 | 3 |

![Figure R4 — Efficiency across seeds, and what each policy costs to run.](../../research/figures/fig_e3_policy_comparison.png)

*Figure R4 — Efficiency across seeds, and what each policy costs to run.*

**Table R6 — The same three policies measured on the imported audience in the running system.**

| Policy | Sent | Clicks | Conversions | Conv. per 1,000 sends | Rules |
|---|---|---|---|---|---|
| fixed | 500 | 144 | 36 | 72.0 | 1 |
| trigger | 400 | 111 | 44 | 110.0 | 4 |
| hybrid | 400 | 109 | 42 | 105.0 | 8 |

> **The simulation and the live build disagree about which policy wins.** Both metrics are volume-controlled, so the difference lies in how response is modelled — the simulator's segment-level propensities against per-customer rates drawn from each customer's own recorded email history. Neither is an observation of real people reacting. The ranking is evidently not robust to that choice, and that instability is the result. Quoting whichever run supports the preferred conclusion would be the one genuinely dishonest option available here.

![Figure R5 — Efficiency as the behavioural signal is suppressed. A policy that reacts to behaviour should degrade as behaviour stops being observable.](../../research/figures/fig_e3_sparsity.png)

*Figure R5 — Efficiency as the behavioural signal is suppressed. A policy that reacts to behaviour should degrade as behaviour stops being observable.*


## 3.4 Attribution — four models, four answers

**Table R7 — Attribution models scored against known channel influence on simulated journeys.**

| Model | MAE | 95% CI | Channels |
|---|---|---|---|
| first_touch | 0.0178 | [0.0112, 0.0268] | 5 |
| linear | 0.0178 | [0.0086, 0.0292] | 5 |
| last_touch | 0.026 | [0.0094, 0.0448] | 5 |
| markov | 0.0525 | [0.0345, 0.0791] | 5 |

On the live journeys of 7,811 converting customers the models disagree over 68% of all attributed credit at the widest pair, and 35% on average. Last-touch hands the great majority of credit to email; first-touch spreads it almost evenly across the acquisition channels.

> A company reading only its last-touch dashboard would conclude that email is responsible for nearly everything, and would cut the acquisition spend that built the audience email later converted. The disagreement between models is not a defect in one of them — it is the finding.

20% of converting journeys have a single touchpoint. On those, every model agrees by arithmetic, and that agreement must never be read as corroboration.

![Figure R6 — The same journeys under four attribution models, and their error where ground truth exists.](../../research/figures/fig_e4_attribution.png)

*Figure R6 — The same journeys under four attribution models, and their error where ground truth exists.*


## 3.5 Prediction, and what the move to another audience costs

**Table R8 — Conversion and drop-off classifiers against a baseline, fitted on Module 3's simulator.**

| Target | Model | ROC-AUC | 95% CI | PR-AUC | Brier |
|---|---|---|---|---|---|
| conversion | baseline (stratified) | 0.4983 | [0.4772, 0.5221] | 0.1147 | 0.205 |
| conversion | logistic regression | 0.9651 | [0.9541, 0.9743] | 0.8371 | 0.0409 |
| conversion | random forest | 0.9722 | [0.9642, 0.9793] | 0.8667 | 0.0375 |
| conversion | xgboost | 0.9725 | [0.9654, 0.9793] | 0.8624 | 0.038 |
| drop_off | baseline (stratified) | 0.4898 | [0.4687, 0.5107] | 0.6328 | 0.4715 |
| drop_off | logistic regression | 0.9306 | [0.9168, 0.9442] | 0.9377 | 0.0829 |
| drop_off | random forest | 0.9876 | [0.9829, 0.9915] | 0.9917 | 0.0362 |
| drop_off | xgboost | 0.99 | [0.9867, 0.9929] | 0.9941 | 0.0355 |

![Figure R7 — Discrimination against a stratified baseline, with bootstrap intervals.](../../research/figures/fig_e5_prediction.png)

*Figure R7 — Discrimination against a stratified baseline, with bootstrap intervals.*

**Table R9 — The same models applied to the imported audience — a different distribution from the one they were fitted on.**

| Prediction | Min | Median | Max | Above threshold |
|---|---|---|---|---|
| conversion | 0.0103 | 0.9126 | 0.9956 | 5606 of 8000 (≥ 0.5) |
| drop-off risk | 0.0006 | 0.0441 | 0.9911 | 911 of 8000 (≥ 0.6) |

The models discriminate well on the distribution they were fitted on. Applying them to another audience is a transfer across distributions: the ranking remains usable, the absolute probabilities are not calibrated for it, and any threshold set on the training distribution should be treated as arbitrary here. The system raises a calibration warning rather than reporting a confident number when the prediction distribution is degenerate.


## 3.6 Goal and tone — the simpler model wins, and it matters which metric says so

**Table R10 — Classifier comparison. Accuracy and macro-F1 tell different stories.**

| Target | Model | Accuracy | Macro-F1 | Weighted F1 | Test rows |
|---|---|---|---|---|---|
| campaign_goal | majority baseline | 0.5877 | 0.1481 | 0.4351 | 114 |
| campaign_goal | tfidf + logistic | 0.7719 | 0.4998 | 0.7628 | 114 |
| campaign_goal | sbert + xgboost | 0.7719 | 0.4042 | 0.7391 | 114 |
| tone | majority baseline | 0.3864 | 0.1115 | 0.2154 | 44 |
| tone | tfidf + logistic | 0.8182 | 0.7315 | 0.8153 | 44 |
| tone | sbert + xgboost | 0.7727 | 0.5912 | 0.7482 | 44 |

![Figure R8 — Accuracy against macro-F1, with the majority-class baseline marked.](../../research/figures/fig_e6_goal_tone.png)

*Figure R8 — Accuracy against macro-F1, with the majority-class baseline marked.*

**Table R11 — Exact McNemar between the two approaches on the same test rows.**

| Target | TF-IDF right, SBERT wrong | SBERT right, TF-IDF wrong | p |
|---|---|---|---|
| campaign_goal | 8 | 8 | 1.000 |
| tone | 5 | 3 | 0.727 |

> Neither comparison is significant. The two approaches are statistically indistinguishable on this corpus, so selecting TF-IDF is a decision about cost, speed and interpretability rather than about accuracy — which is a stronger and more defensible claim than asserting the simpler model is more accurate.


## 3.7 Engagement — a leak, and a dataset with no signal

**Table R12 — The engagement regressor with and without the outcome columns among its features.**

| Feature set | Features | R² | Spearman | MAE |
|---|---|---|---|---|
| with outcome columns (original) | 17 | 0.9901 | 0.9977 | 0.01847 |
| text features only (corrected) | 13 | -0.1676 | 0.012 | 0.39307 |
| baseline (predict the mean) | 0 | -0.0 | 0.0 | 0.32783 |

With the outcome columns present the model reports R² = 0.9901. Removing them gives R² = -0.1676 [-0.4081, -0.0715] and a rank correlation of 0.0120 [-0.0276, 0.0539] — an interval spanning zero, so no ranking skill is demonstrated on held-out data.

The failure was invisible in training and fatal in use. A caption that has not been posted has no like count, so at prediction time those columns were filled with zeros — far outside anything the model had seen — and the score driving 45% of every content ranking became noise. Its weight was reduced to 0.20 once the honest number was known.

Testing each of the 8 text features against the target individually, 0 survive Holm–Bonferroni correction. This is a property of the dataset rather than a modelling failure: no model can extract a signal that is not there, and the correct response is to reduce the weight the score carries rather than to keep tuning.

![Figure R9 — The leak, and the absence of text signal.](../../research/figures/fig_e7_engagement.png)

*Figure R9 — The leak, and the absence of text signal.*


## 3.8 Who to target is not who will convert

The recommender ranks customers by predicted conversion and gives the strongest action to the top of that ranking. That is the intuitive thing to do and it answers the wrong question. What matters is not who will convert but for whom the action *changes* whether they convert — a customer certain to buy anyway gains nothing from a discount, and the discount is wasted on them.

Answering that needs counterfactuals, and this project's own audience cannot supply any: every imported customer received one treatment, nobody recorded which, and no comparable customer received an alternative. No model can recover a causal effect from data where the cause never varied. The experiment therefore moves to the **Hillstrom MineThatData** dataset — 64,000 customers randomly assigned to one of three arms (mens email, womens email, no email) with observed visits. Random assignment is what makes the counterfactual estimable.

**Table R13 — Targeting policies scored on held-out customers. Qini is incremental responders above random targeting; the final column is what a 30% email budget buys.**

| Policy | Qini | 95% CI | Extra visits per 1,000 targeted |
|---|---|---|---|
| uplift (S-learner) | 93.62 | [56.11, 129.76] | 103.45 |
| predicted response (current policy) | 75.91 | [38.8, 109.98] | 91.26 |
| uplift (T-learner) | 70.36 | [30.19, 112.29] | 92.0 |
| random targeting | -9.75 | [-48.65, 26.95] | 57.76 |

![Figure R10 — Qini curves and what each policy buys at a fixed budget.](../../research/figures/fig_e8_uplift.png)

*Figure R10 — Qini curves and what each policy buys at a fixed budget.*

Ranking by uplift and ranking by predicted response select substantially different people: the two scores correlate at Spearman 0.40, and at a 30% budget the two policies share only 56% of their chosen customers — so about 44% of the list would be emailed by one and not the other.

> **What this does and does not establish.** The best uplift learner buys more incremental visits than the current policy, but their Qini intervals overlap, so the ordering of the two is not established on this split. The two uplift learners also disagree with each other, one of them falling below the current policy — so “use uplift modelling” is not a conclusion on its own. What the data does support is the weaker and more useful claim: these are different policies that target different people, and the difference is large enough to matter.

**Table R14 — The three-arm version: which action each customer should receive, rather than whether to act.**

| Assigned action | Customers | Share | Observed uplift per 1,000 |
|---|---|---|---|
| Mens E-Mail | 13601 | 70.8% | 71.27 |
| Womens E-Mail | 5054 | 26.3% | 87.47 |
| No E-Mail | 545 | 2.8% | 0.0 |

This is the next-best-action problem proper: not send or do not send, but which of several actions. Note that the policy assigns a share of customers to *no email at all* — an output the current rule cannot produce, because every customer is given some action regardless of whether acting helps.

Hillstrom's actions are mens and womens email, not this project's premium, personalised, reactivation and reminder. The experiment demonstrates the method on real randomised data and shows that the current policy is answering a different question from the one it should. It does not produce a policy deployable to the imported audience, and nothing in this report should be read as claiming it does.


## 3.9 Making the recommendation learnable

E8 showed the recommender was answering the wrong question, and that no borrowed dataset can answer the right one for this project's actions. The response was to change what the system records. `analytics_output` is overwritten on every run and therefore holds only the current opinion; a new append-only `action_log` records the decision that was actually taken, **the probability it was taken under**, the features it was taken on, and what followed.

The propensity is the column that matters. Without it, logged data can only report what the running policy achieved. With it, an inverse-propensity estimator can answer what a *different* policy would have achieved on the same customers — a counterfactual recovered from observational logs. And because a deterministic policy assigns probability zero to every action it does not take, a small share of decisions are made at random on purpose.

That machinery is only worth having if it works, so this experiment checks it in the one setting where “works” is precisely defined: a simulated world with a known reward function, where the true value of any policy is computable and the estimate can be scored against it.

**Table R15 — Estimator error against the true policy value, as the log grows. 40 replications per row.**

| Estimator | Logged decisions | Bias | 95% CI | RMSE | Unbiased |
|---|---|---|---|---|---|
| ips | 500 | -0.0297 | [-0.0528, -0.0031] | 0.0853 | no |
| snips | 500 | -0.016 | [-0.0399, 0.0089] | 0.0783 | yes |
| doubly robust | 500 | -0.0159 | [-0.0401, 0.0094] | 0.0788 | yes |
| ips | 2000 | -0.007 | [-0.0207, 0.0072] | 0.0457 | yes |
| snips | 2000 | -0.0029 | [-0.0149, 0.0092] | 0.0389 | yes |
| doubly robust | 2000 | -0.0037 | [-0.0157, 0.0088] | 0.0399 | yes |
| ips | 10000 | -0.0006 | [-0.0071, 0.0057] | 0.0213 | yes |
| snips | 10000 | -0.0029 | [-0.008, 0.0019] | 0.0166 | yes |
| doubly robust | 10000 | -0.0031 | [-0.0084, 0.0018] | 0.017 | yes |

**Table R16 — What exploration buys, and what it costs.**

| Exploration rate | Bias | RMSE | Reward given up |
|---|---|---|---|
| 0% | 0.0391 | 0.0423 | 0.0% |
| 1% | 0.0105 | 0.1124 | 0.8% |
| 5% | 0.0142 | 0.0655 | 3.8% |
| 10% | -0.0015 | 0.0332 | 7.5% |
| 25% | -0.011 | 0.0242 | 18.8% |

![Figure R11 — Estimator error against log size, and bias against exploration rate.](../../research/figures/fig_e9_offpolicy.png)

*Figure R11 — Estimator error against log size, and bias against exploration rate.*

At 10,000 logged decisions the self-normalised estimator recovers the candidate policy's true value with a bias of -0.0029 and an interval containing zero. The mechanism also detects that the candidate policy is worth 0.0361 more reward per customer than the one generating the logs — from logged data alone, without having deployed it to anybody.

> **The finding worth carrying into the viva.** Without exploration the estimate is biased by +0.0391, and biased *upwards* — it reports the candidate policy as better than it is. Worse, the deterministic log looks more trustworthy: its effective sample size is 1094 against 107 with exploration, because every weight is 0 or 1 rather than spread out. The standard diagnostic for an unreliable importance-weighted estimate points the wrong way. The estimate is stable and wrong, computed only over the customers where the candidate happens to agree with the logged policy. **Stability is not correctness.**

Token exploration is worse than none: at a 1% rate the estimator has the worst error of any setting tested — too few random decisions to remove the bias, and weights large enough to wreck the variance. Exploration is a commitment, not a gesture.

This experiment is a simulation, deliberately and without apology. The claim under test is a property of an *estimator* — unbiasedness — which is settled by mathematics and can therefore be checked exactly against a known answer. It claims nothing about real customers. What it establishes is that the mechanism now in the system will produce a usable answer once enough decisions have been logged, which is the difference between a system that can improve and one that can only assert.


## 3.10 The action set is a property of the website

Every result so far assumed a fixed vocabulary of four actions. That assumption does not survive contact with a second client. A news site has no checkout, so recommending a discount there is not a poor recommendation but a category error; a charity has no upgrade path; a subscription product has no basket to abandon. The action set is therefore not a constant but the intersection of two things — what the website can perform, and what the customer qualifies for.

It is tempting to learn this. There is no dataset of websites labelled with marketing actions, so the labels would have to be synthesised from a rule and the model would learn that rule back — the same circularity as the two defects in 3.2 and 3.7. What a site can do is *evidence on its pages*, so it is detected; which of the available actions is best is genuinely unknown, so that is left to the decision log.


### 3.10.1 Detecting what a website can do

**Table R17 — Capability detection against hand labels on real websites.**

| Capability | Judgements | Agreement | 95% CI | False positives | False negatives |
|---|---|---|---|---|---|
| commerce | 8 | 1.0 | [0.676, 1.0] | 0 | 0 |
| subscription | 4 | 1.0 | [0.51, 1.0] | 0 | 0 |
| lead capture | 1 | 1.0 | [0.207, 1.0] | 0 | 0 |
| donation | 8 | 1.0 | [0.676, 1.0] | 0 | 0 |

![Figure R12 — Agreement per capability, with Wilson intervals. The width of the bars is the honest content.](../../research/figures/fig_e10_capability_detection.png)

*Figure R12 — Agreement per capability, with Wilson intervals. The width of the bars is the honest content.*

> **This is a development set and the figure is fitted.** The first run disagreed on four judgements. Two were detector faults, both caused by matching URLs as free text: `/product` fired on a magazine's `/categories/product-strategy`, and a retailer's `support.` subdomain was read as a donation page. Matching now works on whole path segments and host labels. The other two were faults in the *labels* — a charity with a shop and a publisher with a store had both been marked as having no commerce, and the detector was right. Code and labels both changed after seeing results, so a fresh sample would be needed to claim generalisation, and none is claimed here.

The finding that matters is not the percentage but what the disagreements taught: capability is not a site *type*. A charity that sells merchandise has donation and commerce both; a publisher running a store has commerce as well as content. Modelling capabilities as independent flags rather than as a category is what allowed the detector to be right where the human label was wrong.


### 3.10.2 What a larger action set costs

Letting each site use its own actions is not free. Exploration is a fixed budget, so the more actions on offer the less evidence each accumulates, and the longer before a logged policy comparison means anything.

**Table R18 — Logged decisions needed to reach an RMSE of 0.02 against the true policy value.**

| Actions on offer | Decisions needed | Per action |
|---|---|---|
| 2 | 5,000 | 2500 |
| 4 | 5,000 | 1250 |
| 8 | 20,000 | 2500 |
| 16 | 80,000 | 5000 |

![Figure R13 — Estimator error against action-set size, and the data each size requires.](../../research/figures/fig_e11_action_set_size.png)

*Figure R13 — Estimator error against action-set size, and the data each size requires.*

Reaching a usable estimate takes 5,000 decisions with 2 actions and 80,000 with 16. Raising the exploration rate helps but does not substitute for volume, and every explored decision is one deliberately not taken greedily.

> **The design guidance this yields.** The catalogue should stay as small as honestly covers what a site can do. Adding an action nobody will choose is not free — it takes evidence away from every other action. A site offering twelve actions should not expect conclusions on the same timescale as one offering four, and the system should say so rather than present an early estimate as settled.
