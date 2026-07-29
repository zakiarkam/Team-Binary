# DISCUSSION


## 4.1 What the evidence supports

- **The closed loop runs.** One audience passes through segmentation, content generation, campaign planning and analytics, and the analytics output feeds back into which platforms get written for next. That is the architecture the report proposes, executing.
- **Cold start is handled explicitly, and it had to be defended.** The engine declines to cluster below thirty customers and says why; individual customers with thin histories are decided by rules and flagged. The vote-order defect showed how easily that contribution can be destroyed by a pipeline that looks correct.
- **Attribution model choice changes the conclusion.** On the same journeys the four models disagree over a third of attributed credit on average. Any single-model dashboard is a decision, not a measurement.
- **Simpler models won twice.** TF-IDF matched Sentence-BERT on goal and tone, and interpretable rules matched the full hybrid on conversion separation. Neither result was expected.
- **The recommender was answering the wrong question.** Ranking customers by predicted conversion and ranking them by the *incremental effect* of the action select materially different people — they share only about half their choices at a realistic budget. This is the clearest direction for future work the project produced.


## 4.2 What the evidence does not support

- **That the hybrid segmentation separates conversion better than rules alone.** It does not, on this dataset. Its value lies in calibrated confidence and explicit cold start.
- **That any one automation policy is best.** The simulator and the live build disagree, and the ranking depends on how response is modelled rather than on the policies themselves.
- **That engagement can be predicted from caption text.** Not on this corpus, where no text feature survives correction.
- **That the prediction thresholds transfer.** They were set on the distribution the models were fitted on and do not carry to another audience. The production recommender was changed to rank rather than threshold as a direct consequence.
- **That uplift modelling is straightforwardly better.** The best uplift learner beat the current policy, but the intervals overlap and the second uplift learner did worse. The framing is right; the evidence for any particular learner is not yet strong.


# THREATS TO VALIDITY


## 5.1 Construct validity

The reconstruction of event timing is the principal threat. Attribution operates on journeys whose *order* this project created, so the attribution results characterise the reconstruction as well as the data. The counts underlying those journeys are real; their sequence is not observed. A dataset with genuine timestamped events would settle what this study can only bound.

Conversion separation depends on segment definitions that a human wrote. The rules were not tuned against the conversion column — which is what keeps the metric from being circular — but they were written by someone who knows the domain, and that is a weaker guarantee than a preregistered rule set.


## 5.2 Internal validity

Two defects found in this work were both invisible to the metrics being watched at the time, and both made results look better. That is evidence that other such defects may remain. Every correction now carries a regression test, and the leakage guard in the engagement model raises an exception rather than a warning if an outcome column re-enters the feature set.

Campaign response in both the simulator and the live build is modelled, not observed. No claim about open or click rates in this report is a measurement of human behaviour.


## 5.3 External validity

One dataset, one product category, one language. The 87.6% conversion rate in the source data is far above any plausible e-commerce baseline, which suggests the dataset is either filtered or synthetic in origin; conclusions about absolute rates should not leave it. Comparisons *between* methods on the same data are the results that travel.

The goal corpus has 453 labelled rows and the tone corpus 174, with one tone class represented by a single example. Macro-F1 on a corpus that small carries wide uncertainty, and the per-class numbers for rare classes should be read as indicative.


# LIMITATIONS

- **Event timing and ordering are reconstructed**, so attribution path statistics are partly a property of the importer.
- **Campaign response is modelled**, in both the simulator and the live build. Nobody in this study opened a real email.
- **Conversion and drop-off models were fitted on a simulator** and transfer poorly in calibration, though the ranking survives.
- **The engagement dataset carries no usable text signal**, so that component of the content score is close to arbitrary and is weighted accordingly.
- **`humorous` tone has a single training example** and cannot be learned or evaluated.
- **Open-rate tracking under-reports** by design: most mail clients block the pixel, so click-through is the reliable engagement signal.
- **Three real platform datasets ship unused** — they are comment-level scrapes that pair no post text with post engagement.
- **No action was ever randomised on this project's own audience**, so the next-best-action recommendation cannot be validated on it at all. E8 borrows a dataset where treatment *was* randomised, and the actions there are not this project's actions.
