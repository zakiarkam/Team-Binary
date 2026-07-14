# Goal and Tone Reasoning README

This file explains the exact flow for `campaign_goal` and `tone`: what they mean, where they come from, why the project uses a dataset, why a model is trained, what would happen if a model predicted them directly, and what the correct research-safe flow is.

## 1. What Are `campaign_goal` and `tone`?

`campaign_goal` is the marketing objective. In this project it is one of:

```text
awareness
conversion
engagement
lead_generation
retention
```

Examples:

| Campaign goal | Meaning |
|---|---|
| `awareness` | Make people know the product/brand exists. |
| `conversion` | Push users to buy, subscribe, register, book, or order. |
| `engagement` | Increase likes, comments, shares, replies, participation, or community activity. |
| `lead_generation` | Collect leads through signup, demo request, inquiry, newsletter, download, or webinar. |
| `retention` | Bring existing/inactive customers back or increase loyalty/repeat purchase. |

`tone` is the writing style. In this project it is one of:

```text
friendly
professional
luxury
emotional
persuasive
humorous
```

Examples:

| Tone | Meaning |
|---|---|
| `friendly` | Casual, welcoming, community-oriented. |
| `professional` | Formal, business-like, informative. |
| `luxury` | Premium, exclusive, elegant. |
| `emotional` | Story-driven, empathetic, inspirational. |
| `persuasive` | Action-oriented, offer-driven, sales-focused. |
| `humorous` | Playful, witty, lighthearted. |

## 2. Why This Project Needs Goal and Tone

The generator uses `campaign_goal` and `tone` inside the prompt. That means the generated content changes depending on these two values.

Example:

| Input strategy | Expected content behavior |
|---|---|
| `campaign_goal = awareness`, `tone = friendly` | Shorter, welcoming, brand-introduction content. |
| `campaign_goal = conversion`, `tone = persuasive` | Stronger CTA, offer language, purchase-oriented copy. |
| `campaign_goal = lead_generation`, `tone = professional` | Demo/signup/download language, more business-focused. |
| `campaign_goal = retention`, `tone = emotional` | Win-back, loyalty, personalized reactivation language. |

So goal and tone are not decorative fields. They guide the final captions, hashtags, CTA, image prompt, and shorts prompt.

## 3. The Important Difference: Dataset, Model, Training, Fine-Tuning

These words are different:

| Term | Meaning in this project |
|---|---|
| Dataset | A CSV containing examples of marketing text and labels. |
| Label | The correct or assumed answer for one row, such as `conversion` or `friendly`. |
| Pseudo-label | An automatically created label when human labels are unavailable. |
| Model | A machine learning method that learns patterns from the dataset. |
| Training | Teaching a classifier to predict labels from text. |
| Fine-tuning | Updating the weights of a large neural model such as BERT/Phi-3. |
| Direct prompting | Asking Phi-3 or another LLM to answer `goal` and `tone` without training your own classifier. |

This project currently uses **training**, not full neural fine-tuning.

## 4. Current Project Flow

The current flow is:

```text
marketing text dataset
        |
        v
auto/pseudo-label campaign_goal and tone
        |
        v
train goal/tone classifiers
        |
        v
crawl new product website
        |
        v
predict goal/tone for the new product
        |
        v
generate platform-specific marketing assets
```

In code:

| Step | File | Purpose |
|---|---|---|
| Auto-label dataset | `auto_label_marketing_dataset.py` | Creates `campaign_goal` and `tone` labels when a perfect labeled dataset is unavailable. |
| Build dataset from Hugging Face | `dataset_builder.py` | Builds a pseudo-labeled marketing dataset from `RafaM97/marketing_social_media`. |
| Train classifiers | `goal_tone.py` | Trains TF-IDF + Logistic Regression and SentenceBERT + XGBoost. |
| Predict for product | `goal_tone.py` | Predicts campaign goal and tone for the crawled product/website knowledge base. |
| Generate content | `generator.py` | Uses predicted goal/tone in the content generation prompt. |

## 5. Why the Dataset Is Needed

The dataset is needed because the project must learn how different marketing language maps to different goals and tones.

For example:

```text
"Limited-time 20% discount. Shop now."
```

This should usually map to:

```text
campaign_goal = conversion
tone = persuasive
```

Another example:

```text
"Download our free guide and book a demo."
```

This should usually map to:

```text
campaign_goal = lead_generation
tone = professional
```

Without a labeled or pseudo-labeled dataset, the project has no measurable training signal for goal/tone classification.

## 6. Why the Old Dataset Was Wrong

The earlier dataset had:

```text
campaign_goal = awareness for every row
tone = professional for every row
```

That is not useful because a classifier trained on one class only learns one answer.

Bad result:

```text
Every product -> awareness/professional
```

That would make the project look like it predicts strategy, but actually it would be repeating the only labels it saw.

## 7. Why Pseudo-Labeling Was Added

A public dataset with exact columns:

```text
text,campaign_goal,tone
```

is difficult to find. So the practical research-safe solution is:

```text
marketing text dataset + transparent pseudo-labeling + validation
```

The pseudo-labeler checks words and phrases in the marketing text.

Examples:

| Keywords/signals | Assigned goal |
|---|---|
| `sales`, `buy`, `purchase`, `discount`, `offer` | `conversion` |
| `leads`, `signup`, `demo`, `newsletter`, `download` | `lead_generation` |
| `comments`, `shares`, `challenge`, `contest`, `community` | `engagement` |
| `loyalty`, `inactive`, `win back`, `we miss you` | `retention` |
| `awareness`, `reach`, `visibility`, `launch`, `showcase` | `awareness` |

Examples:

| Keywords/signals | Assigned tone |
|---|---|
| `premium`, `exclusive`, `elegant` | `luxury` |
| `discount`, `offer`, `shop`, `book`, `register` | `persuasive` |
| `community`, `welcome`, `join us`, `tips` | `friendly` |
| `business`, `industry`, `guide`, `webinar`, `report` | `professional` |
| `story`, `inspire`, `we miss you`, `journey` | `emotional` |
| `funny`, `witty`, `meme`, `playful` | `humorous` |

This is not 100% ground truth. It is weak supervision. The strength is that the method is transparent, reproducible, and explainable in the research report.

## 8. Why Train a Classifier After Pseudo-Labeling?

This is the key point.

Pseudo-labeling labels the training examples. The classifier then learns a reusable prediction model from those examples.

Reason to train:

1. The final product website will not always contain exact keywords.
2. The classifier can learn broader text patterns.
3. Training gives measurable metrics such as accuracy and weighted F1.
4. The project can compare two classifier types and choose the better one.
5. The prediction step becomes fast after training.

Current classifiers:

| Classifier | What it learns from |
|---|---|
| TF-IDF + Logistic Regression | Word and phrase patterns. |
| SentenceBERT + XGBoost | Semantic embedding patterns. |

The project selects the better classifier by weighted F1.

## 9. Why Not Predict Goal and Tone Directly With Phi-3?

You can ask Phi-3 directly:

```text
Given this website text, classify campaign_goal and tone.
```

That is possible, but it has research disadvantages.

| Direct LLM prediction | Trained classifier approach |
|---|---|
| Easier to implement. | More measurable and reproducible. |
| Can change answers across runs. | More stable after training. |
| Harder to evaluate without ground truth. | Can report accuracy and weighted F1 on a test split. |
| Depends heavily on prompt wording. | Learns from a fixed dataset and saved artifacts. |
| More expensive/slower at scale. | Fast once trained. |
| Less transparent decision boundary. | TF-IDF and class distributions are easier to explain. |

Direct LLM prediction is good for a prototype. For a research project, training a classifier is easier to justify because you can report metrics.

## 10. Is Fine-Tuning Better?

Fine-tuning can be better, but only when you have enough high-quality labeled data and enough compute.

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Direct Phi-3 prompt | Simple, no training dataset needed | Less stable, less measurable | Good for demo only. |
| Rule-based pseudo-labeling only | Transparent and fast | Too keyword-dependent | Good for bootstrapping labels. |
| Current classifier training | Measurable, reproducible, lightweight | Depends on pseudo-label quality | Best practical choice for this project. |
| Fine-tuning BERT/DistilBERT | Stronger if labels are good | More compute, more complexity, can overfit pseudo-labels | Future work or extension. |
| Fine-tuning Phi-3 | Powerful | Heavy compute, not needed for this research scope | Not recommended now. |

Fine-tuning on weak pseudo-labels is risky. It can make the model confidently learn noisy labels. For this project, the safer path is:

```text
pseudo-label -> train lightweight classifiers -> evaluate -> report limitations
```

## 11. Correct Research-Safe Flow

Use this exact flow:

### Step 1: Prepare the base marketing text dataset

Use:

```text
data/raw/datasets/your_labeled_marketing_dataset.csv
```

Required minimum columns:

```text
text
summary
```

The file can also already contain `campaign_goal` and `tone`, but they will be replaced if you run auto-labeling.

### Step 2: Auto-label goal and tone

Run:

```bash
python3 auto_label_marketing_dataset.py
```

This creates:

```text
campaign_goal
campaign_goal_confidence
campaign_goal_matched_groups
tone
tone_confidence
tone_matched_groups
labeling_method
```

It also keeps a backup:

```text
data/raw/datasets/your_labeled_marketing_dataset.csv.before_auto_label
```

### Step 3: Check class distribution

Run:

```bash
python3 -c "import pandas as pd; df=pd.read_csv('data/raw/datasets/your_labeled_marketing_dataset.csv'); print(df['campaign_goal'].value_counts()); print(df['tone'].value_counts())"
```

Good condition:

```text
At least 2 classes for campaign_goal
At least 2 classes for tone
Preferably 20+ rows per class
```

Current usable distribution:

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

### Step 4: Train goal/tone classifiers

Run:

```bash
python3 main.py --step goal-tone-train --force
```

This trains:

```text
TF-IDF + Logistic Regression
SentenceBERT + XGBoost
```

It saves the best model artifacts in:

```text
models/best_goal_model.pkl
models/best_tone_model.pkl
models/goal_tone_model_selection.json
```

### Step 5: Predict goal and tone for the selected product

Run:

```bash
python3 main.py --step crawl kb goal-tone-predict summary --force
```

This reads `input.json`, crawls the product website, builds the knowledge base, and predicts:

```text
campaign_goal
tone
```

These values are written into the processed marketing summary.

### Step 6: Generate content using predicted goal and tone

Run:

```bash
python3 main.py --step generate engagement-score evaluate optimize significance --force
```

The generated output includes:

```text
platform
caption
hashtags
cta
image_prompt
shorts_prompt
predicted_engagement
engagement_score
semantic_score
platform_suitability_score
final_score
```

## 12. What to Write in the Research Report

Use wording like this:

```text
Because a public dataset with explicit campaign_goal and tone labels was not available,
the study used transparent rule-based pseudo-labeling to construct weak labels from
marketing text. The pseudo-labeled dataset was then used to train and compare
TF-IDF + Logistic Regression and SentenceBERT + XGBoost classifiers. The best model
was selected using weighted F1 and used to infer campaign strategy for new product
contexts.
```

Do not write:

```text
The labels are 100% accurate.
```

Correct wording:

```text
The labels are automatically generated pseudo-labels. Accuracy is controlled through
class-balance checks, confidence columns, train/test evaluation, and transparent
labeling rules.
```

## 13. Final Answer to the Main Doubt

Question:

```text
Is goal/tone from dataset or model?
```

Answer:

```text
Both.
```

Explanation:

1. The dataset provides examples.
2. Pseudo-labeling creates labels when human labels are unavailable.
3. Training uses those labeled examples to create a classifier.
4. The classifier predicts goal and tone for a new product.
5. The generator uses predicted goal and tone to create content.

Question:

```text
Why not direct model prediction?
```

Answer:

```text
Direct model prediction is possible, but it is harder to evaluate, less stable,
and weaker for a research methodology. The trained classifier path gives metrics,
saved artifacts, reproducibility, and clearer justification.
```

Question:

```text
Is fine-tuning better?
```

Answer:

```text
Fine-tuning may be better only with strong human-labeled data and enough compute.
Fine-tuning on noisy pseudo-labels can overfit label noise. For this project,
lightweight classifier training is the best practical and explainable choice.
```
