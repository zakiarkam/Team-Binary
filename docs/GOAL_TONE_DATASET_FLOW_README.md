# Goal/Tone Dataset Build Flow

This file explains the best way to create stronger raw data for:

```text
text,campaign_goal,tone
```

It also explains which real datasets can be used, which labels can be trusted, which labels must be generated, and why there is no fully automatic 100% accurate path without human ground truth.

## 1. Direct Answer

You are looking for a real dataset that already has:

```text
marketing text + campaign_goal + tone
```

That exact public dataset is difficult to find. The best practical research flow is:

```text
real marketing dataset
        |
        v
extract campaign_goal from explicit "Goals" text
        |
        v
generate tone using a controlled label rubric/model
        |
        v
keep confidence + method columns
        |
        v
train goal/tone classifier
        |
        v
predict goal/tone for new product website
```

For this project, `campaign_goal` can be made fairly strong because the base marketing dataset often contains a real `Goals:` field. `tone` is harder because most marketing datasets do not explicitly label writing tone. Tone must usually be annotated by a model, rules, or a small human audit.

## 2. Real Dataset Options

| Dataset | Link | Good for | Not good for |
|---|---|---|---|
| RafaM97 marketing_social_media | https://huggingface.co/datasets/RafaM97/marketing_social_media | Best base dataset for this project. It has marketing `instruction`, `input`, and `response`. The `input` often contains explicit `Goals:` text. | It does not directly provide final `campaign_goal` and `tone` columns. |
| AdParaphrase v2.0 | https://github.com/CyberAgentAILab/AdParaphrase-v2.0 | Advertising text preference and attractiveness research. Useful as evidence for ad text quality/style research. | It is not a campaign-goal/tone classification dataset. |
| GoEmotions | https://huggingface.co/datasets/google-research-datasets/go_emotions | Real human-labeled emotion dataset. Useful as supporting evidence for emotional language. | It is Reddit comments, not marketing campaign data. It does not contain campaign goals. |
| Local Social Media Engagement Dataset | `data/raw/datasets/Social Media Engagement Dataset.csv` | Engagement prediction: platform, text, likes, shares, comments, impressions. | It does not contain campaign goal or tone labels. |

Recommended choice:

```text
Use RafaM97/marketing_social_media for goal/tone dataset construction.
Use your Social Media Engagement Dataset for engagement prediction.
Do not use GoEmotions as the main marketing tone dataset.
```

## 3. Why RafaM97 Is the Best Base Dataset

The RafaM97 dataset has 689 rows and these fields:

```text
instruction
input
response
```

Example structure:

```text
instruction: Develop a social media campaign...
input: Company, Target Audience, Constraints, Goals, Workflow Stage
response: Generated campaign plan/copy
```

This is useful because:

1. `input` often contains an explicit `Goals:` phrase.
2. `response` is marketing content.
3. The data is already close to your project domain.
4. The final project needs marketing strategy, not general emotion detection.

## 4. What Should Become `text`

Use the marketing output as the training text:

```text
text = response
```

Reason:

The classifier will later predict goal/tone from crawled product/website marketing content. It should learn from actual marketing content, not only from short labels.

Keep summary/context too:

```text
summary = input
```

Reason:

The `input` includes company, audience, constraints, and goals. It gives extra context for labeling.

Final raw dataset should look like:

```csv
text,summary,campaign_goal,tone,campaign_goal_confidence,tone_confidence,labeling_method,needs_review
```

Your training code only requires:

```csv
text,campaign_goal,tone
```

But the extra columns are important for research explanation and quality control.

## 5. Best Flow for `campaign_goal`

For `campaign_goal`, do not guess from the whole response first. Use the explicit `Goals:` part in the source dataset whenever possible.

Recommended priority:

```text
1. Extract explicit Goals field from summary/input.
2. Match it to one campaign_goal label.
3. Use response text only when Goals field is missing or unclear.
```

Label mapping:

| Source signal | campaign_goal |
|---|---|
| `brand awareness`, `visibility`, `reach`, `followers`, `traffic`, `brand recall` | `awareness` |
| `sales`, `purchase`, `conversion`, `subscription`, `orders`, `revenue` | `conversion` |
| `engagement`, `likes`, `comments`, `shares`, `participation`, `contest`, `challenge` | `engagement` |
| `leads`, `lead generation`, `demo`, `inquiry`, `signup`, `newsletter`, `download`, `webinar` | `lead_generation` |
| `retention`, `loyalty`, `repeat purchase`, `inactive subscribers`, `reactivate`, `win back` | `retention` |

When a row has multiple goals, use a fixed priority rule so the dataset is consistent.

Recommended priority for single-label training:

```text
retention > lead_generation > conversion > engagement > awareness
```

Reason:

`awareness` often appears together with another business objective. If you always choose `awareness`, the dataset becomes too biased. More specific goals should win over broad goals.

Example:

```text
Goals: Increase brand awareness by 20% and drive sales by 15%.
```

Best single label:

```text
conversion
```

Why:

Both awareness and sales are present, but sales is a more concrete business outcome.

## 6. Best Flow for `tone`

Tone is less explicit than campaign goal. Most datasets do not say:

```text
tone = persuasive
```

So the best flow is controlled generation/annotation:

```text
1. Define tone labels and descriptions.
2. Use model/rules to assign tone.
3. Store confidence.
4. Keep low-confidence rows for review or exclude them from training.
```

Tone mapping:

| Source signal | tone |
|---|---|
| `discount`, `offer`, `buy`, `shop`, `book`, `register`, strong CTA | `persuasive` |
| `business`, `industry`, `webinar`, `guide`, `report`, `case study`, B2B language | `professional` |
| `community`, `welcome`, `join`, `tips`, conversational phrasing | `friendly` |
| `premium`, `luxury`, `exclusive`, `elegant`, `prestige`, high-end lifestyle | `luxury` |
| `story`, `journey`, `inspire`, `we miss you`, empathy/wellness language | `emotional` |
| `funny`, `witty`, `meme`, `playful`, jokes/puns | `humorous` |

Important:

If one tone class has very few rows, do not force it into training. For example, if `humorous` has only 1 row, remove it or collect more examples. A class with 1 row cannot train a reliable classifier.

## 7. Best Model-Based Labeling Option

If you want stronger labels than keyword rules, use zero-shot classification with `facebook/bart-large-mnli` or a strong LLM.

Zero-shot candidate labels:

```text
campaign_goal labels:
awareness, conversion, engagement, lead_generation, retention

tone labels:
friendly, professional, luxury, emotional, persuasive, humorous
```

Best zero-shot process:

```text
1. Run zero-shot model for campaign_goal.
2. Run zero-shot model for tone.
3. Store top label, confidence, and second-best label.
4. Accept only if confidence >= 0.60 and margin >= 0.15.
5. Send low-confidence rows to review/exclusion.
```

Reason:

The confidence margin matters. A row with:

```text
professional = 0.42
persuasive = 0.40
```

is not a strong tone label even though `professional` is top.

## 8. Best Hybrid Flow

This is the recommended flow for your research:

```text
campaign_goal:
    extract from explicit Goals field with deterministic rules

tone:
    generate using controlled zero-shot/model labeling
    fallback to transparent keyword rules
    filter low-confidence rows

training:
    train goal/tone classifiers
    report weighted F1

prediction:
    use trained classifier for new product website
```

Why this is best:

1. Campaign goal is usually stated in the source data, so deterministic extraction is stronger than guessing.
2. Tone is usually not stated, so model-assisted annotation is acceptable.
3. Confidence columns make the dataset auditable.
4. Filtering weak rows improves training quality.
5. The final trained classifier gives measurable results.

## 9. Why Not Use Only Direct Model Prediction?

Direct model prediction means:

```text
Ask Phi-3/BART-MNLI to classify goal and tone for the product website directly.
```

This is possible, but weaker for research because:

1. There is no training/test metric.
2. Output can change when prompt changes.
3. It is harder to justify accuracy.
4. It does not create a reusable dataset.
5. It gives less evidence for your methodology chapter.

Use direct model prediction only as an annotation assistant, not as the final research method.

## 10. Why Not Fine-Tune Immediately?

Fine-tuning sounds better, but it is only better when the labels are strong.

If labels are pseudo-generated and noisy, fine-tuning can make the model learn wrong patterns confidently.

Recommended order:

```text
1. Build better labels.
2. Train lightweight classifiers.
3. Evaluate weighted F1.
4. Only then consider fine-tuning as future work.
```

For this project, the current classifier approach is more defensible than fine-tuning on noisy labels.

## 11. Exact Quality Checks

Before training, check:

```text
1. campaign_goal has at least 3 useful classes.
2. tone has at least 3 useful classes.
3. each class has preferably 20+ rows.
4. low-confidence rows are removed or marked.
5. label distribution is reported in the methodology.
```

Good example:

```text
campaign_goal:
conversion         288
awareness          247
engagement          83
lead_generation     71

tone:
persuasive      320
professional    152
friendly        142
emotional        44
luxury           31
```

Weak example:

```text
campaign_goal:
awareness 689

tone:
professional 689
```

The weak example must not be used for training.

## 12. Most Correct Research Statement

Use this wording in the report:

```text
No public dataset was found with complete campaign_goal and tone labels matching
the project schema. Therefore, the study used a real marketing campaign dataset
as the base source. Campaign goals were derived from explicit goal statements
where available, and tone labels were produced through controlled pseudo-labeling
with confidence tracking. The resulting labels were used to train supervised
classifiers, and model performance was evaluated using weighted F1.
```

Do not write:

```text
The generated goal/tone labels are 100% correct.
```

Write:

```text
The labels are research-grade pseudo-labels generated using a transparent,
auditable flow and validated through class-balance checks and classifier
performance metrics.
```

## 13. Final Recommendation

Use this final plan:

```text
1. Keep RafaM97/marketing_social_media as the real base dataset.
2. Improve campaign_goal labels by extracting from explicit Goals text.
3. Improve tone labels using zero-shot/model labeling plus rules.
4. Keep confidence and review flags.
5. Remove classes with too few rows.
6. Train the goal/tone classifier.
7. Report weighted F1 and limitations.
8. Use the trained classifier to predict goal/tone for Shopify or any new website.
```

This is the closest correct flow without doing full manual labeling.

## 14. Sources

- RafaM97 marketing_social_media: https://huggingface.co/datasets/RafaM97/marketing_social_media
- AdParaphrase v2.0: https://github.com/CyberAgentAILab/AdParaphrase-v2.0
- AdParaphrase v2.0 paper: https://arxiv.org/abs/2505.20826
- GoEmotions dataset: https://huggingface.co/datasets/google-research-datasets/go_emotions
- GoEmotions paper: https://arxiv.org/abs/2005.00547
- BART-MNLI zero-shot model: https://huggingface.co/facebook/bart-large-mnli
- Hugging Face zero-shot classification task: https://huggingface.co/tasks/zero-shot-classification
