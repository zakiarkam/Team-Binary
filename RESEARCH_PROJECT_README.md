# Research Project Execution README

This file is the end-to-end operating guide for completing the AI marketing research project in this repository. It explains the exact project flow, required external tools, manual updates, datasets, commands, outputs, and the reason each step exists.

## 1. Project Title

AI-Driven Marketing Content Generation, Engagement Prediction, and Adaptive Optimization for Platform-Specific Digital Campaigns

## 2. What This Project Does

The project takes a product or website as input and produces platform-specific marketing assets for Instagram, LinkedIn, Shorts, and Email. It does not only generate captions. It also predicts campaign goal and tone, summarizes website context, generates platform-specific assets, predicts engagement, ranks outputs, optimizes weak outputs, tests whether optimization improved results, and compares AI outputs against a human baseline.

The main pipeline is controlled by:

```bash
python main.py
```

The stage order is defined in `main.py`:

```text
crawl
kb
label-dataset
goal-tone-train
goal-tone-predict
summary
generate
engagement-train
engagement-score
evaluate
optimize
significance
human-baseline
```

## 3. External Requirements

| Requirement | Link | Why it is needed |
|---|---|---|
| Python 3.10 or newer | https://www.python.org/downloads/ | Runs the full local pipeline and all ML libraries. |
| PyTorch | https://pytorch.org/get-started/locally/ | Required by Transformers, BART, Phi-3, and Sentence-BERT models. |
| Hugging Face Transformers | https://huggingface.co/docs/transformers | Loads BART and Phi-3 models. |
| Hugging Face Datasets | https://huggingface.co/docs/datasets | Used when building the labeled goal/tone dataset from Hugging Face. |
| BART model | https://huggingface.co/facebook/bart-large-cnn | Summarizes website/product context. |
| Phi-3 Mini Instruct | https://huggingface.co/microsoft/Phi-3-mini-4k-instruct | Generates marketing assets and helps create labels. |
| Sentence-BERT MiniLM | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 | Converts text to embeddings for semantic similarity. |
| RafaM97 marketing dataset | https://huggingface.co/datasets/RafaM97/marketing_social_media | Optional source for generating the labeled campaign goal/tone dataset. |
| spaCy English model | https://spacy.io/models/en | Required by the project dependency stack for NLP support. |
| FFmpeg | https://ffmpeg.org/download.html | Required by some ML/media stacks; install once to avoid runtime dependency issues. |

Use a GPU if available. Phi-3 can run on CPU, but generation will be slow.

## 4. Setup Steps

From the project root:

```bash
cd /Users/aadhil/Documents/Sem/research/Marketing/ai_marketing_research/Team-Binary
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

For macOS, install FFmpeg:

```bash
brew install ffmpeg
```

For Ubuntu/Linux:

```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

Verify the CLI stages:

```bash
python main.py --list
```

## 5. Manual Update 1: Product Input

Edit `input.json`. The correct schema is:

```json
{
  "product_name": "Shopify",
  "website_url": "https://www.shopify.com",
  "target_audience": "entrepreneurs and small business owners",
  "customer_segment": "online retailers and ecommerce startups",
  "preferred_platforms": ["instagram", "linkedin", "shorts", "email"]
}
```

Do not manually add `campaign_goal` or `tone`. The research contribution is that those are inferred by the trained model.

For Shopify, avoid `customer_segment: "eco-conscious buyers"` unless your experiment is specifically about sustainable ecommerce customers. Shopify is a commerce platform, so a stronger segment is `online retailers and ecommerce startups`.

## 6. Manual Update 2: Required Datasets

The code expects these files inside `data/raw/datasets/`.

| File | Required columns | Used for |
|---|---|---|
| `your_labeled_marketing_dataset.csv` | `text`, `campaign_goal`, `tone`, optional `summary` | Training goal and tone classifiers. |
| `your_engagement_dataset.csv` | `platform`, `text`, `likes`, `shares`, `comments`, `impressions` | Training engagement prediction model. |
| `human_content_dataset.csv` | `platform`, `caption` | Optional human-vs-AI comparison. |

### If Goal/Tone Labels Are Missing

There is no 100% accurate automatic replacement for human labels. For this project, the practical research-safe option is rule-based pseudo-labeling with confidence columns and class-balance checks.

Run:

```bash
python3 auto_label_marketing_dataset.py
```

This updates `your_labeled_marketing_dataset.csv`, keeps a backup named `your_labeled_marketing_dataset.csv.before_auto_label`, and adds:

```text
campaign_goal_confidence
campaign_goal_matched_groups
tone_confidence
tone_matched_groups
labeling_method
```

Report these as pseudo-labels in the methodology, not as perfect human annotations.

### Best Engagement Dataset Choice

Your rich file `data/raw/datasets/Social Media Engagement Dataset.csv` is a good source because it already contains social platform, text, and engagement metrics. The project code needs a normalized file named `your_engagement_dataset.csv`.

Map it like this:

| Source column | Project column |
|---|---|
| `platform` | `platform` |
| `text_content` | `text` |
| `likes_count` | `likes` |
| `shares_count` | `shares` |
| `comments_count` | `comments` |
| `impressions` | `impressions` |

After mapping, save the normalized file as:

```text
data/raw/datasets/your_engagement_dataset.csv
```

The final engagement CSV header must be exactly:

```csv
platform,text,likes,shares,comments,impressions
```

## 7. Manual Update 3: Human Baseline

Create this file only if you want to compare AI outputs against human-written marketing content:

```text
data/raw/datasets/human_content_dataset.csv
```

Required format:

```csv
platform,caption
instagram,"Your human Instagram caption here"
linkedin,"Your human LinkedIn caption here"
shorts,"Your human Shorts caption here"
email,"Subject: Your human email subject and body here"
```

Use the same product and same platforms as `input.json`. Otherwise the comparison is not fair.

## 8. Exact Run Flow

### First Full Research Run

Use this when datasets are ready:

```bash
python main.py --force
```

This rebuilds all artifacts from scratch.

### Faster Repeat Run After Models Already Exist

Use this after changing only `input.json`:

```bash
python main.py --step crawl kb goal-tone-predict summary generate engagement-score evaluate optimize significance
```

### Train Only Goal/Tone Models

```bash
python main.py --step goal-tone-train --force
```

### Train Only Engagement Model

```bash
python main.py --step engagement-train --force
```

### Generate and Evaluate New Marketing Assets

```bash
python main.py --step generate engagement-score evaluate optimize significance --force
```

### Run Human Baseline Only

```bash
python main.py --step human-baseline
```

## 9. Output Files to Use in the Research Report

| Output file | What to report |
|---|---|
| `data/processed/marketing_knowledge_base.json` | Crawled and cleaned website/product knowledge. |
| `data/processed/marketing_summary.json` | Product summary, inferred campaign goal, inferred tone, preferred platforms. |
| `data/outputs/generated_platform_assets.csv` | Initial AI-generated captions, hashtags, CTAs, image prompts, video prompts. |
| `data/outputs/engagement_model_comparison.csv` | RandomForest vs XGBoost engagement model results. |
| `data/outputs/ranked_platform_assets.csv` | Initial semantic, platform suitability, engagement, and final scores. |
| `data/outputs/optimized_ranked_platform_assets.csv` | Optimized final outputs after adaptive re-prompting. |
| `data/outputs/before_after_optimization_comparison.csv` | Before-vs-after score changes. |
| `data/outputs/optimization_significance_test.csv` | Paired t-test result. |
| `data/outputs/human_vs_ai_comparison.csv` | Human, initial AI, and optimized AI comparison. |

## 10. Score Formula

The final score is:

```text
final_score = 0.30 * semantic_score
            + 0.25 * platform_suitability_score
            + 0.45 * engagement_score
```

Reason:

| Score | Weight | Why |
|---|---:|---|
| Semantic similarity | 0.30 | Checks whether the generated content stays close to the product meaning. |
| Platform suitability | 0.25 | Checks whether content fits each platform's communication style. |
| Engagement prediction | 0.45 | Highest weight because it is learned from real social engagement metrics. |

## 11. Accuracy and Validation Checklist

Before writing final results, check these items:

1. `your_labeled_marketing_dataset.csv` has more than one `campaign_goal` class and more than one `tone` class.
2. `your_engagement_dataset.csv` has non-empty text and positive impressions.
3. Engagement model report includes MAE, RMSE, and R2.
4. Goal/tone model report includes accuracy and weighted F1.
5. Generated outputs are valid JSON-converted rows in `generated_platform_assets.csv`.
6. Every generated row has `platform`, `caption`, `hashtags`, `cta`, `image_prompt`, and `shorts_prompt`.
7. `before_after_optimization_comparison.csv` shows whether optimization improved final score.
8. `optimization_significance_test.csv` reports p-value from the paired t-test.
9. Human baseline captions are for the same product and platforms.
10. Report limitations honestly if R2 is low, class balance is poor, or the sample size is small.

## 12. Final Research Workflow

Use this as the exact order for completing the full research project:

1. Finalize research topic, research gap, and research questions using `RESEARCH_EVIDENCE_README.md`.
2. Prepare `input.json` with the selected product and audience.
3. Normalize the engagement dataset into `your_engagement_dataset.csv`.
4. Prepare or generate `your_labeled_marketing_dataset.csv`.
5. Add `human_content_dataset.csv` if human comparison is required.
6. Install dependencies and external tools.
7. Run `python main.py --force`.
8. Inspect all output CSVs.
9. Record model metrics: weighted F1, MAE, RMSE, R2.
10. Record ranking metrics: semantic score, platform suitability score, engagement score, final score.
11. Record optimization improvement and paired t-test p-value.
12. Compare optimized AI against human baseline.
13. Write the final report with method, results, discussion, limitations, and future work.

## 13. Common Problems

| Problem | Cause | Fix |
|---|---|---|
| Missing column error in engagement training | Dataset column names do not match code | Rename to `platform,text,likes,shares,comments,impressions`. |
| Classifier fails with one-class error | All labels became the same class | Check `campaign_goal` and `tone` value counts before training. |
| Phi-3 is very slow | CPU inference | Use GPU or run fewer platforms during testing. |
| Cached output does not change | Existing artifact is reused | Add `--force` or delete only the specific output artifact. |
| Human comparison is unfair | Human captions are for another product | Use same product, audience, and platforms as `input.json`. |

## 14. Final Submission Artifacts

For a clean research submission, include:

```text
README.md
RESEARCH_PROJECT_README.md
RESEARCH_EVIDENCE_README.md
METHODOLOGY.md
input.json
requirements.txt
main.py and source modules
data/outputs/*.csv
models/* selection files or screenshots of metrics
```

Do not submit downloaded model cache folders unless your institution specifically asks for them.
