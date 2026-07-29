# EXPERIMENTAL SETUP


## 2.1 The experiments

Nine experiments cover the four modules. Each writes its tables to `research/results/`, and every figure in the next chapter is drawn from those tables rather than plotted by hand, so a chart cannot drift away from the number it shows.

**Table R2 — The seven experiments.**

| ID | Question | Data | Primary metric |
|---|---|---|---|
| E1 | Does the hybrid beat its own components? | 8,000-customer dataset | Conversion separation, silhouette |
| E2 | The two Module 1 defects, reproduced | 8,000-customer dataset | Segment survival, accuracy, certainty |
| E3 | Which automation policy wins, and at what cost | Module 2 simulator, 30 seeds | Conversions per 1,000 sends |
| E4 | Do the attribution models agree? | Module 3 simulator + live journeys | MAE vs ground truth, TVD |
| E5 | Prediction quality and its transfer | Module 3 features + live audience | ROC-AUC, PR-AUC, Brier |
| E6 | TF-IDF versus Sentence-BERT | 527-row goal/tone corpus | Macro-F1, McNemar |
| E7 | Engagement leakage and text signal | 12,000-row engagement corpus | R², Spearman, Holm–Bonferroni |
| E8 | Targeting by uplift versus by predicted response | Hillstrom, 64,000 randomised | Qini, incremental response |
| E9 | Does the decision log make the policy learnable? | Simulated world, known rewards | Estimator bias, RMSE |


## 2.2 Choice of statistics

Four tools are used, each chosen because it makes the fewest assumptions the data can violate.

- **Percentile bootstrap** rather than a normal-theory interval. Conversion separation, silhouette and macro-F1 are not means and have no closed-form standard error; resampling makes no distributional claim at all.
- **Paired bootstrap and Wilcoxon signed-rank** for the policy comparison. Each seed puts the same 8,000 customers through all three policies, so the runs are paired; ignoring that wastes power and overstates the p-value.
- **Exact McNemar** for two classifiers on one test set. Only the disagreements carry information, and with roughly a hundred test rows the exact binomial is correct where the asymptotic approximation is not.
- **Cliff's delta** alongside every p-value. With thirty seeds almost any difference reaches significance; the effect size is what says whether it matters.


## 2.3 Metrics, and why not the obvious ones

- **Conversion separation**, not cluster quality, for segmentation. Conversion is used only to *evaluate* segments — never as a clustering feature and never as a rule input — so a segmentation that separates it has found something it was not told.
- **Conversions per 1,000 sends**, not conversion rate, for the policy comparison. User-level conversion rises simply by sending more messages, which would hand the win to the policy that sends most rather than the one that sends best.
- **Macro-F1**, not accuracy, for goal and tone. The majority class is 59% of the goal corpus, so accuracy flatters a model that handles rare classes badly — and the rare classes are the ones a marketer would want detected.
- **Spearman**, not R², for engagement. The model exists to rank candidate captions, not to predict an engagement rate in absolute terms, and rank correlation is what ranking needs.
