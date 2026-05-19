# Marketing Content Pipeline

Generate, score, optimize, and benchmark platform-specific marketing assets from a product website using BART (summarization), Phi-3 (generation), Sentence-BERT (semantics), and TF-IDF/XGBoost/RandomForest (classification + engagement regression).

Same algorithm as the original Colab notebook, restructured as a local CLI with lazy model loading, stage-level caching, and a single configuration entry point.

---

## 1. Setup

```bash
cd /Users/arkamzakir/Documents/Aadhil

# Create + activate a virtual env
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Required model + system dependency
python -m spacy download en_core_web_sm
brew install ffmpeg          # macOS; Linux: apt-get install ffmpeg
```

> **Note on GPU**: BART and Phi-3 (~8 GB) load fastest on a CUDA GPU. On CPU/Mac everything still runs but Phi-3 generation will be slow (a minute+ per asset).
>
> `bitsandbytes` was dropped from `requirements.txt` because it's Linux/CUDA-only and the code does not use it.

---

## 2. Provide the input datasets

Drop these CSVs into `data/raw/datasets/` before running the pipeline:

| File | Required by stage | Required columns |
|---|---|---|
| `your_labeled_marketing_dataset.csv` | `goal-tone-train` | `text`, `campaign_goal`, `tone` |
| `your_engagement_dataset.csv` | `engagement-train` | `text`, `platform`, `likes`, `comments`, `shares`, `impressions` |
| `human_content_dataset.csv` | `human-baseline` | `platform`, `caption` |

If you don't have `your_labeled_marketing_dataset.csv`, the `label-dataset` stage will build one from the `RafaM97/marketing_social_media` Hugging Face dataset (slow — runs Phi-3 over every row).

---

## 3. Configure the product / website

Edit [`input.json`](input.json):

```json
{
    "product_name": "EcoSmart Bottle",
    "website_url": "https://www.shopify.com",
    "target_audience": "young professionals",
    "customer_segment": "eco-conscious buyers",
    "preferred_platforms": ["instagram", "linkedin", "facebook", "shorts", "email"]
}
```

`campaign_goal` and `tone` are **inferred** by the pipeline, not provided.

---

## 4. Run

```bash
# Run the full pipeline; stages whose outputs already exist are skipped.
python main.py

# Rerun everything from scratch
python main.py --force

# Run only specific stages
python main.py --step crawl kb summary

# List all stage names
python main.py --list
```

### Stages (in execution order)

| Stage | Reads | Writes |
|---|---|---|
| `crawl` | `input.json` | `data/raw/websites/crawled_website_data.json` |
| `kb` | crawl output | `data/processed/marketing_knowledge_base.json` |
| `label-dataset` | (HF dataset) | `data/raw/datasets/your_labeled_marketing_dataset.csv` |
| `goal-tone-train` | labeled dataset | `models/best_goal_model.pkl`, `models/best_tone_model.pkl`, selection JSON |
| `goal-tone-predict` | KB | updates KB with predicted goal + tone |
| `summary` | KB | `data/processed/marketing_summary.json` |
| `generate` | summary | `data/outputs/generated_platform_assets.csv` |
| `engagement-train` | engagement dataset | `models/best_engagement_model.pkl`, feature columns |
| `engagement-score` | generated assets | adds `predicted_engagement` + `engagement_score` columns |
| `evaluate` | generated + summary | `data/outputs/ranked_platform_assets.csv` |
| `optimize` | ranked + summary | `data/outputs/optimized_ranked_platform_assets.csv`, `before_after_optimization_comparison.csv` |
| `significance` | comparison | `data/outputs/optimization_significance_test.csv` |
| `human-baseline` | human CSV + summary + rankings | `data/outputs/human_vs_ai_comparison.csv` |

---

## 5. Project layout

```
Aadhil/
├── input.json                     # product/website input (edit this)
├── main.py                        # CLI orchestrator
├── config.py                      # paths, model names, score weights
├── models.py                      # lazy-loaded BART/Phi-3/MiniLM
├── crawler.py                     # STEP 6
├── knowledge_base.py              # STEP 7
├── dataset_builder.py             # builds labeled dataset from RafaM97
├── goal_tone.py                   # STEP 8: TF-IDF + SentenceBERT-XGB classifiers
├── summary.py                     # STEP 9
├── generator.py                   # STEP 10: Phi-3 platform assets
├── engagement.py                  # STEP 11/12: train + score
├── evaluation.py                  # STEP 13-15: semantic + platform + final score
├── optimization.py                # STEP 16-17: re-prompt + re-evaluate
├── significance.py                # STEP 18: paired t-test
├── human_baseline.py              # STEP 19: human vs AI
├── data/
│   ├── raw/
│   │   ├── datasets/              # ← drop your input CSVs here
│   │   └── websites/
│   ├── processed/
│   └── outputs/                   # all CSV results
└── models/                        # trained classifiers + engagement regressor
```

---

## 6. Common workflows

**First-time run (with all datasets in place):**
```bash
python main.py
```

**Already trained, want to test a new product:**
```bash
# Edit input.json, then:
python main.py --step crawl kb goal-tone-predict summary generate engagement-score evaluate optimize significance
```

**Retrain only the engagement model:**
```bash
python main.py --step engagement-train --force
```

**Generate fresh assets for a product without retraining anything:**
```bash
python main.py --step generate engagement-score evaluate optimize --force
```

---

## 7. Score formula

Final score per asset:

```
final_score = 0.30 * semantic_score
            + 0.25 * platform_suitability_score
            + 0.45 * engagement_score
```

Weights live in [`config.py`](config.py): `SEMANTIC_WEIGHT`, `PLATFORM_WEIGHT`, `ENGAGEMENT_WEIGHT`.

---

## 8. Notes

- Models are lazy-loaded — importing a module that uses Phi-3 won't actually download Phi-3 until `generate_with_phi3()` is called.
- Stages are independent and use disk artifacts for handoff. If a stage's output exists, it is reused unless `--force` is given.
- The original Colab `extract_json_from_text` was undefined — it is implemented in [`generator.py`](generator.py).
