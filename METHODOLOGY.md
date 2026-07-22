# Methodology

A dataset-guided framework for platform-specific marketing content generation, engagement prediction, and adaptive optimization.

## 1. Problem statement

Businesses with a product or website struggle to produce platform-appropriate marketing assets across Instagram, LinkedIn, Shorts/TikTok, and Email — each demands a distinct caption style, hashtag policy, length, and CTA form. This system asks:

> Can a single AI framework, given only product/website context, automatically infer the campaign strategy, generate platform-tailored assets, predict their likely engagement, and iteratively optimize them?

## 2. Input contract

The user provides only:

```json
{
  "product_name": "...",
  "website_url": "...",
  "target_audience": "...",
  "customer_segment": "...",
  "preferred_platforms": ["instagram", "linkedin", "shorts", "email"]
}
```

`campaign_goal` and `tone` are **inferred** by trained classifiers — not provided.

## 3. Model selection rationale

| Role | Model | Why |
|---|---|---|
| Long-form summarization | `facebook/bart-large-cnn` | State-of-the-art abstractive summarizer; small enough to run locally; trained on CNN/DailyMail which matches marketing-paragraph length distribution. |
| Generative reasoning | `microsoft/Phi-3-mini-4k-instruct` | Strong instruction-following for a 3.8B-param model; fits on consumer GPU; 4k context handles full marketing summary + per-platform constraints. |
| Semantic similarity | `sentence-transformers/all-MiniLM-L6-v2` | Fast, well-calibrated cosine-similarity; established baseline for content-preservation evaluation. |
| Classification (goal/tone) | TF-IDF + LogReg **and** SentenceBERT + XGBoost | Two complementary methods — sparse lexical vs dense semantic. Best of the two by weighted F1 is selected. |
| Engagement regression | RandomForest **and** XGBoost | Two non-linear regressors compared by R²; selected best handles feature interactions without explicit engineering. |

## 4. Data preparation

### 4.1 Goal/tone labeled dataset

Source: `RafaM97/marketing_social_media` (HuggingFace).

The raw dataset has `instruction`, `input`, `response`. The transformation:

| Raw column | Pipeline use |
|---|---|
| `instruction` | Used by Phi-3 to infer `campaign_goal` |
| `input` | BART-summarized into a `summary` field |
| `response` | Used as `text` and to infer `tone` via Phi-3 |

Output schema: `text, campaign_goal, tone, summary`.

**Label collapse incident**: an early implementation called an undefined `generator` symbol, causing the exception handler to return fallback labels for every row. This produced single-class data and broke downstream classifier training (`ValueError: This solver needs samples of at least 2 classes`). The fix was to introduce a lazy-loaded model accessor (`get_phi3_generator()`) that guarantees pipeline initialization before inference. Validation now requires `value_counts()` to show ≥ 2 classes before training proceeds.

### 4.2 Engagement dataset

Schema: `platform, text, likes, comments, shares, impressions`.

Target variable: `engagement_rate = (likes + comments + shares) / impressions`.

### 4.3 Human baseline dataset

Schema: `platform, caption`. Used only for evaluation — never for training.

## 5. Pipeline architecture

```
input.json
    │
    ▼
[crawl]                   →  raw HTML → visible text artefacts
    │
    ▼
[knowledge_base]          →  cleaned, deduped, concatenated marketing context
    │
    ▼
[preprocess-dataset]      →  RafaM97 raw → cleaned rows
    │
    ▼
[label-goal]              →  rule + zero-shot + Phi-3 → campaign_goal
    │
    ▼
[label-tone]              →  rule + BART-MNLI + Phi-3 → tone
    │
    ▼
[build-dataset]           →  confidence gate → training + research splits
    │
    ▼
[goal-tone-train]         →  TF-IDF+LR vs SentenceBERT+XGB ; best by weighted F1
    │
    ▼
[goal-tone-predict]       →  attaches inferred campaign_goal + tone to module_input
    │
    ▼
[summary]                 →  BART abstractive summary
    │
    ▼
[generate]                →  Phi-3 → per-platform JSON: caption, hashtags, cta,
                                                          image_prompt, shorts_prompt
    │
    ▼
[engagement-train]        →  RF vs XGBoost on engagement_rate ; best by R²
    │
    ▼
[engagement-score]        →  predicted_engagement + min-max normalized engagement_score
    │
    ▼
[evaluate]                →  semantic_score, platform_suitability_score, final_score
    │
    ▼
[optimize]                →  rule-triggered Phi-3 re-prompt + full re-evaluation
    │
    ▼
[significance]            →  paired t-test on before vs after final_score
    │
    ▼
[human-baseline]          →  scores human-written captions through the same pipeline
```

## 6. Scoring formula

```
final_score = 0.30 · semantic_score
            + 0.25 · platform_suitability_score
            + 0.45 · engagement_score
```

**Weight derivation**: engagement is weighted highest because it is the only data-driven signal trained on real interaction data; semantic similarity guards against drift from the source meaning; platform suitability is a rule-based sanity check. Weights sum to 1.0 (verified in `tests/test_pipeline.py`).

### 6.1 Semantic score

Cosine similarity between MiniLM embeddings of the source business summary and the generated caption. Range: [-1, 1], typically [0, 1] for related content.

### 6.2 Platform suitability score

A 5-point heuristic checklist per platform — word count, hashtag count, CTA presence, image/video prompt completeness — normalized to [0, 1].

### 6.3 Engagement score

Min-max normalized prediction from the best regressor across the asset set, scaled to [0, 1].

## 7. Adaptive optimization

After initial scoring, each asset is examined against three thresholds:

| Trigger | Rule emitted to Phi-3 |
|---|---|
| `semantic_score < 0.65` | "Keep content closer to original product meaning." |
| `platform_suitability_score < 0.75` | Platform-specific rule (Instagram brevity, LinkedIn formality, etc.) |
| `engagement_score < 0.50` | "Use clearer benefits, stronger emotional wording, more action-oriented CTA." |

The asset is regenerated with the rule appended to the prompt and re-scored.

## 8. Statistical validation

A paired t-test compares `before_final_score` vs `after_final_score` across all platforms. p < 0.05 indicates the optimization round produced a statistically significant uplift.

## 9. Human baseline

Human-written captions for the same platforms are scored through the exact same pipeline (engagement model, semantic similarity, platform rules, final score). Mean final score per platform is compared against `phi3_initial` and `phi3_optimized` to characterise where AI under- or over-performs humans.

## 10. Engineering decisions

- **Lazy model loading** — BART, Phi-3, and MiniLM load only when first used. Importing a module that doesn't need them stays cheap. Critical for unit tests, which avoid model downloads entirely.
- **Disk-mediated stage handoff** — each stage writes a CSV/JSON; the next stage reads it. Stages are individually re-runnable via `python main.py --step <name>`.
- **Output existence caching** — by default a stage is skipped if its output already exists; `--force` overrides. Saves expensive Phi-3 calls during iteration.
- **No `manual_input` for campaign_goal/tone** — these are inferred outputs of the pipeline, not user-provided. Manual override would defeat the research contribution.

## 11. Limitations

- **Cold-start sensitivity**: engagement model accuracy depends heavily on training-set size and platform balance. Reported R² on a held-out 20% split.
- **Phi-3 hallucination**: generation is constrained by JSON-only prompt rules; the parser falls back to wrapping the raw text as a caption if JSON extraction fails.
- **Platform suitability is heuristic, not learned**: rules encode common-sense norms; a learned suitability classifier would be a natural future-work extension.
- **No DistilBERT fine-tuning in current implementation**: the original design considered DistilBERT as a third classifier method. The two-method comparison (TF-IDF+LR vs SentenceBERT+XGB) is sufficient for selecting a goal/tone model under the available compute; DistilBERT is a stretch goal.

## 12. Contribution

A reproducible, modular framework that:

1. Removes manual specification of campaign strategy by learning `campaign_goal` and `tone` from a public marketing dataset.
2. Combines abstractive summarization, instruction-tuned generation, dense semantic evaluation, supervised classification, and supervised regression into a single auditable pipeline.
3. Closes the loop with rule-triggered, data-grounded adaptive optimization, validated by a paired statistical test against a human baseline.
