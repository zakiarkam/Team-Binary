# Project Architecture

This is the exact architecture for the current Team-Binary code path. It reflects the real repository layout, the stage order in `modules/m4_content/main.py`, and the artifacts each module reads or writes. Module 4's pipeline code lives in `modules/m4_content/`, alongside the other three modules.

## 1. Repository Structure

```text
Research/
│
├── input.json
├── orchestrator.py
├── modules/
│   ├── m1_segmentation/
│   ├── m2_automation/
│   ├── m3_analytics/
│   └── m4_content/
│       ├── config.py
│       ├── main.py
│       ├── models.py
│       ├── crawler.py
│       ├── knowledge_base.py
│       ├── dataset/
│       │   ├── preprocess_marketing.py
│       │   ├── label_campaign_goal.py
│       │   ├── label_tone.py
│       │   └── build_final_dataset.py
│       ├── dashboard/
│       │   ├── app.py
│       │   ├── artifacts.py
│       │   └── theme.py
│       ├── goal_tone.py
│       ├── summary.py
│       ├── generator.py
│       ├── engagement.py
│       ├── evaluation.py
│       ├── optimization.py
│       └── significance.py
├── tests/
│   └── test_pipeline.py
├── data/
│   ├── raw/
│   │   └── datasets/
│   │       ├── Social Media Engagement Dataset.csv
│   │       ├── your_engagement_dataset.csv
│   │       ├── your_labeled_marketing_dataset.csv
│   │       ├── socialmedia.csv
│   │       ├── Instagram-datasets.csv
│   │       ├── Facebook-datasets.csv
│   │       ├── TikTok-datasets.csv
│   │       └── Apr-01-2022_Jun-30-2022_244847167907999.csv
│   ├── processed/
│   │   ├── marketing_knowledge_base.json
│   │   └── marketing_summary.json
│   ├── outputs/
│   │   ├── generated_platform_assets.csv
│   │   ├── ranked_platform_assets.csv
│   │   ├── optimized_ranked_platform_assets.csv
│   │   ├── before_after_optimization_comparison.csv
│   │   └── optimization_significance_test.csv
│   └── raw/websites/
├── models/
│   ├── best_goal_model.pkl
│   ├── best_tone_model.pkl
│   ├── best_goal_encoder.pkl
│   ├── best_tone_encoder.pkl
│   ├── goal_tone_model_selection.json
│   ├── best_engagement_model.pkl
│   └── engagement_feature_columns.pkl
├── README.md
└── docs/
    ├── RESEARCH_PROJECT_README.md
    ├── RESEARCH_EVIDENCE_README.md
    ├── GOAL_TONE_REASONING_README.md
    └── GOAL_TONE_DATASET_FLOW_README.md
```

## 2. Logical Layers

The code is organized into five layers:

```text
Input layer
    -> data and product configuration
Preparation layer
    -> dataset labeling and knowledge-base construction
Modeling layer
    -> goal/tone classification and engagement regression
Generation layer
    -> content creation and scoring
Validation layer
    -> ranking, optimization, significance testing
```

## 3. Exact Pipeline Flow

The execution order is controlled by `modules/m4_content/main.py`:

```text
crawl
kb
preprocess-dataset
label-goal
label-tone
build-dataset
goal-tone-train
goal-tone-predict
summary
generate
engagement-train
engagement-score
evaluate
optimize
significance
```

### Flow Diagram

```text
input.json
   |
   v
[crawler.py]
   |
   v
raw website text
   |
   v
[knowledge_base.py]
   |
   v
marketing_knowledge_base.json
   |
   +--> [goal-tone-train] from labeled marketing dataset
   |
   +--> [goal-tone-predict] updates module_input with campaign_goal + tone
   |
   v
[summary.py]
   |
   v
marketing_summary.json
   |
   v
[generator.py]
   |
   v
generated_platform_assets.csv
   |
   +--> [engagement.py train] learns from your_engagement_dataset.csv
   |
   v
[engagement.py score]
   |
   v
predicted_engagement + engagement_score
   |
   v
[evaluation.py]
   |
   v
ranked_platform_assets.csv
   |
   v
[optimization.py]
   |
   v
optimized_ranked_platform_assets.csv
   |
   v
[significance.py]
   |
   v
optimization_significance_test.csv
```

## 4. Module Responsibilities

| Module | Role | Reads | Writes |
|---|---|---|---|
| `main.py` | CLI orchestrator | `input.json`, cached artifacts | None directly |
| `config.py` | Paths, constants, model names, weights | None | Creates folders |
| `crawler.py` | Crawls product website | `input.json` | `marketing_knowledge_base` input for later stages |
| `knowledge_base.py` | Cleans and structures website/product context | Crawl output + `input.json` | `data/processed/marketing_knowledge_base.json` |
| `dataset/preprocess_marketing.py` | Cleans the RafaM97 corpus into pipeline rows | `RafaM97_marketing_social_media_raw.csv` | `data/intermediate/marketing_preprocessed.csv` |
| `dataset/label_campaign_goal.py` | Weak-labels `campaign_goal` (rule + zero-shot + Phi-3) | preprocessed corpus | `data/intermediate/campaign_goal_labeled.csv` |
| `dataset/label_tone.py` | Weak-labels `tone` (rule + BART-MNLI + Phi-3, checkpointed) | goal-labeled corpus | `data/intermediate/tone_labeled.csv` |
| `dataset/build_final_dataset.py` | Applies the confidence gate and writes the splits | tone-labeled corpus | `goal_tone_dataset_training.csv`, `goal_tone_dataset_research.csv` |
| `modules/m4_content/dashboard/app.py` | Streamlit research dashboard over the written artifacts | all artifacts | nothing (read-only view) |
| `goal_tone.py` | Trains and predicts campaign goal/tone | Labeled dataset + KB | Saved classifiers + updated KB input |
| `summary.py` | Creates concise summary of KB | `marketing_knowledge_base.json` | `marketing_summary.json` |
| `generator.py` | Generates platform-specific marketing assets | `marketing_summary.json` | `generated_platform_assets.csv` |
| `engagement.py` | Trains and scores engagement | `your_engagement_dataset.csv` + generated assets | Engagement model + scores |
| `evaluation.py` | Computes semantic, platform, and final score | Generated assets + summary | `ranked_platform_assets.csv` |
| `optimization.py` | Re-prompts weak assets and re-scores | Ranked assets + summary | Optimized outputs + comparison CSV |
| `significance.py` | Statistical validation | Optimization comparison | `optimization_significance_test.csv` |

## 5. Data Flow by Stage

### Stage 1: Input

`input.json` provides:

```text
product_name
website_url
target_audience
customer_segment
preferred_platforms
```

### Stage 2: Crawl

`crawler.py` fetches website content from `website_url` and extracts raw marketing text.

### Stage 3: Knowledge Base

`knowledge_base.py` merges:

```text
website content + user input
```

into a structured marketing knowledge base.

### Stage 4: Goal/Tone Dataset Preparation

The four `dataset/` modules create training labels for:

```text
campaign_goal
tone
```

This is the only place where the project learns the label mapping.

### Stage 5: Goal/Tone Modeling

`goal_tone.py` trains:

```text
TF-IDF + Logistic Regression
SentenceBERT + XGBoost
```

The best model is chosen by weighted F1 and stored in `models/`.

### Stage 6: Summary

`summary.py` reduces the knowledge base into a marketing summary used by the generator.

### Stage 7: Generation

`generator.py` creates one row per selected platform with:

```text
caption
hashtags
cta
image_prompt
shorts_prompt
```

### Stage 8: Engagement Modeling

`engagement.py` trains a regressor from:

```text
platform
text
likes
shares
comments
impressions
```

It then scores generated captions.

### Stage 9: Evaluation

`evaluation.py` combines:

```text
semantic_score
platform_suitability_score
engagement_score
```

into:

```text
final_score
```

### Stage 10: Optimization

`optimization.py` re-prompts weaker outputs using rule-based feedback and re-evaluates them.

### Stage 11: Significance Testing

`significance.py` compares before-vs-after optimization using a paired t-test.

## 6. Artifact Flow

| Artifact | Produced by | Purpose |
|---|---|---|
| `marketing_knowledge_base.json` | `knowledge_base.py` | Structured source context |
| `marketing_summary.json` | `summary.py` | Compact generation context |
| `generated_platform_assets.csv` | `generator.py` | Initial output set |
| `ranked_platform_assets.csv` | `evaluation.py` | Initial ranking |
| `optimized_ranked_platform_assets.csv` | `optimization.py` | Improved ranking |
| `before_after_optimization_comparison.csv` | `optimization.py` | Improvement analysis |
| `optimization_significance_test.csv` | `significance.py` | Statistical validation |

## 7. Why This Architecture Fits the Code

This structure matches the current implementation because:

1. The pipeline is file-based and stage-driven.
2. Each stage reads the previous artifact and writes the next one.
3. Goal/tone are learned separately from engagement prediction.
4. Generation happens after strategy inference and summarization.
5. Optimization and statistical testing are separate validation stages.

## 8. Minimal Dependency View

```text
input.json -> crawler.py -> knowledge_base.py -> summary.py -> generator.py -> engagement.py -> evaluation.py -> optimization.py -> significance.py

data/raw/datasets/your_labeled_marketing_dataset.csv -> goal_tone.py

data/raw/datasets/your_engagement_dataset.csv -> engagement.py
```

## 9. Recommended Report Figure

For a thesis or paper, this is the best short architecture caption:

```text
The system follows a modular pipeline in which website content is crawled,
converted into a knowledge base, used to infer campaign goal and tone,
summarized, transformed into platform-specific assets, scored by engagement
and semantic relevance, optimized through feedback, and validated through
statistical significance testing.
```
