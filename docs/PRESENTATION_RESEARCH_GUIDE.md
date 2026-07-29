# Presentation Research Guide — AI-Powered Digital Marketing Orchestration

## 1. One-sentence project definition

This project is a **closed-loop, platform-conditioned marketing-content decision system**: it segments users, simulates campaign automation, analyses funnel outcomes, predicts a platform-specific goal and tone, generates several content candidates, and selects the best candidate using relevance, platform compliance, predicted engagement, and historical platform-content fit.

It is a research prototype: it previews/exports content and does not post to live platforms.

## 2. Problem and research gap

Small businesses need different content for each platform, but commonly face three constraints:

1. Product context is unstructured (a website, a description, an audience), while content generation needs an explicit strategy.
2. A generic LLM can write copy, but it does not know which candidate best fits a brand's historical platform performance.
3. Raw likes are not comparable across accounts: follower count and exposure dominate them.

Existing social-media tools generally generate or rewrite text, while engagement prediction research generally predicts performance from existing posts. The project combines these into one inference-time loop:

```text
product context -> platform strategy -> generate candidates -> score/rank -> preview
                                                    ^
                                  historical platform engagement evidence
```

The novelty claim is **not** “we invented Phi-3, TF-IDF, or XGBoost.” The defensible novelty is the integration of: (a) platform-conditioned strategy prediction, (b) candidate selection using a supervised engagement signal plus historical content fit, and (c) a future cold-start-to-personalized feedback path that normalizes engagement within an account.

## 3. Final operational pipeline

```text
User product brief + selected platforms
  |
  +-- M1: audience segmentation
  |     hybrid rules + RandomForest -> five audience segments
  |
  +-- M2: automation simulation
  |     fixed / trigger / hybrid strategies -> event log
  |
  +-- M3: analytics and decision support
  |     funnel + conversion/drop-off + attribution study -> platform priorities
  |
  +-- M4: content refinery, once per selected platform
        platform-conditioned goal classifier
        platform-conditioned tone classifier
        -> 3 fast candidates (or Phi-3 candidate)
        -> semantic relevance + format fit + engagement + historical fit
        -> highest-scoring candidate returned for that platform
```

`orchestrator.py` is the final integrated entry point. `main.py` remains the detailed M4 research/CLI pipeline and its optional learning stages.

## 4. Models, algorithms, datasets, and why each is used

| Layer | Implemented method | Dataset/artifact | Why this choice | What it is **not** |
|---|---|---|---|---|
| M1 segmentation | Hybrid rules + RandomForest | `modules/m1_segmentation/ecommerce_user_segmentation.csv` | Combines interpretable business rules with non-linear segmentation. | A live customer-data model. |
| M2 automation | Fixed, trigger, hybrid campaign simulators; conversion model | `modules/m2_automation/data/raw/digital_marketing_conversion.csv` | Gives controlled strategy comparisons and event logs. | Evidence that a live campaign will perform identically. |
| M3 analytics | Funnel, attribution, conversion/drop-off predictors, recommender | M2 events + validated M3 artifacts | Turns events into targeting and platform-priority signals. | A causal claim from the simulated multi-platform data. |
| Product summary | BART-large-CNN | Crawled website/brief | Converts long product context into compact generation context. BART is a seq2seq denoising model effective for generation tasks. | Guaranteed factual summarization; website claims must still be checked. |
| Content generation | Phi-3-mini-4k-instruct, or fast deterministic candidates | Product summary + platform strategy | Phi-3 is a compact instruction model suitable for local, reproducible generation. The fast path keeps the demo responsive. | Fine-tuned marketing copy; it is not trained on this project's 113 labels. |
| Goal classifier | TF-IDF + Logistic Regression and SentenceBERT + XGBoost; selected by weighted F1 | 113 weakly labelled RafaM97-derived platform rows | Compares an interpretable sparse baseline with dense semantic embeddings. | A human-ground-truth 85%+ classifier. |
| Tone classifier | Same two candidate classifiers | Same | Tone labels are a separate target, so it is trained/evaluated separately. | A measure of caption quality. |
| Engagement ranker | RandomForest and XGBoost; selected by held-out R² | `your_engagement_dataset.csv`, 12,000 posts | Tree ensembles are strong tabular baselines and handle feature interactions. | A causal estimate of content effect or a raw-like predictor. |
| Historical content fit | TF-IDF centroid of the highest-engagement quartile per platform | Same 12,000 posts | Adds direct evidence of what successful text on the *same* platform looks like; it never copies a historical post. | A supervised quality label. |
| Candidate selection | Best-of-3, full composite score | Generated candidates + all scores | Reduces dependence on one generated wording. Small N limits proxy over-optimization. | Proof that the top candidate will win live engagement. |
| Future personalization | Relative engagement target, RF/XGBoost, best-of-N | Account analytics CSVs in `data/feedback/` | Corrects follower/exposure confounding by comparing a post with the account's own baseline. | Automatic posting or language-model fine-tuning. |

Key sources: BART is a general seq2seq denoising architecture [Lewis et al.](https://aclanthology.org/2020.acl-main.703/); Phi-3-mini is a 3.8B instruction model intended for compact local deployment [Abdin et al.](https://arxiv.org/abs/2404.14219); Sentence-BERT supports efficient sentence similarity/embeddings [Reimers & Gurevych](https://aclanthology.org/D19-1410/); weak supervision is an established remedy for missing labels [Bach et al.](https://proceedings.mlr.press/v70/bach17a.html).

## 5. Dataset inventory and correct use

| Local dataset | Rows | Useful columns | Correct use | Do not use it for |
|---|---:|---|---|---|
| `RafaM97_marketing_social_media_raw.csv` | 689 | marketing instruction, context, text | Source corpus for weakly supervised goal/tone training. | Claiming it originally has goal/tone labels. |
| `your_labeled_marketing_dataset.csv` | 689 | `text, campaign_goal, tone, ...` | Audit artifact after weak labelling. | Independent extra training data—it derives from RafaM97. |
| `goal_tone_dataset_training.csv` | 114 before duplicate filtering / 113 training rows | `text, platform, campaign_goal, tone` | Actual goal/tone classifier training. Platform exists only when explicitly mentioned in source text. | Strong per-platform ground truth. |
| `Social Media Engagement Dataset.csv` | 12,000 | platform, text content, interactions, impressions, account fields | Engagement-rate model and historical platform-content profiles. | Direct goal/tone training; it has no such labels. |
| `your_engagement_dataset.csv` | 12,000 | `platform, text, likes, shares, comments, impressions` | Simplified engagement model input. | Follower-normalized personalized learning; it lacks account history. |
| `Instagram-datasets.csv`, `Facebook-datasets.csv`, `TikTok-datasets.csv` | 1,000 each | comments/replies | Optional audience-response analysis. | Caption generation training: they are comments, not brand posts. |
| Facebook Insights export | 9 | reach, impressions, engagements | Demo of real analytics schema. | Training a robust model: too few records. |
| `socialmedia.csv` | 39 | platform, post text, interactions | Smoke test only. | Reliable training/evaluation. |

The historical corpus covers Instagram, Facebook, YouTube, Twitter and Reddit. Shorts use YouTube evidence; LinkedIn, TikTok and Email receive a neutral historical-fit score until real matching data arrives. This is an explicit coverage limitation, not an error.

## 6. File-by-file responsibility

### Top-level operational files

| File | Main function/responsibility | Input -> output |
|---|---|---|
| `config.py` | Paths, platform specifications, model names, weights, safety switches. | Shared configuration. |
| `orchestrator.py` | `run_full()` executes M1 -> M2 -> M3 -> M4. | Product brief -> `data/integrated/run_bundle.json`. |
| `content_service.py` | `generate()`, `_platform_strategy()`, `score_assets()`; app-facing M4 path. | Brief -> selected asset per platform. |
| `goal_tone.py` | `train()`, `predict_one()`, `predict()`; platform-conditioned classification. | Labelled data/context -> goal/tone model or predictions. |
| `engagement.py` | `train()`, `score()`, `platform_content_fit()` and `platform_content_guidance()`. | Historical posts -> engagement model/profile -> candidate scores. |
| `generator.py` | `build_prompt()`, `run()`, `standardize()`. | Summary/strategy -> Phi-3 JSON assets. |
| `evaluation.py` | semantic similarity and platform format checks. | Assets -> component scores. |
| `optimization.py` | Re-prompts weak legacy-M4 assets. | Ranked assets -> optimized assets. |
| `summary.py` | BART summary creation. | KB -> marketing summary. |
| `crawler.py`, `knowledge_base.py` | Extract and clean website context. | URL/brief -> KB. |
| `model_health.py` | Produces honest warnings/metrics for dashboard/report. | Artifacts -> health JSON. |

### Dataset and learning files

| File | Function | Reason |
|---|---|---|
| `dataset/preprocess_marketing.py` | Cleans RafaM97 data and extracts context. | Reproducible source transformation. |
| `dataset/label_campaign_goal.py` | Rules + zero-shot + Phi-3 weak labels. | No native goal labels exist. |
| `dataset/label_tone.py` | Rules + BART-MNLI + Phi-3 weak labels. | No native tone labels exist. |
| `dataset/build_final_dataset.py` | Confidence gate and explicit-platform extraction. | Keeps uncertain labels separate from training. |
| `learning/targets.py` | Relative/within-account target. | Avoids follower-count bias. |
| `learning/feedback_store.py` | SQLite predictions plus later actuals. | Links generated content to real analytics. |
| `learning/importer.py` | Normalizes future platform export CSVs. | Platform-specific data can enter without changing the pipeline. |
| `learning/personalize.py` | Retrains account-aware engagement predictor. | Cold-start -> personalized adaptation. |
| `learning/candidates.py` | Phi-3 best-of-N candidate selection. | Optional higher-quality, slower selection flow. |

## 7. Choice comparisons and justification

### 7.1 Why weak supervision rather than no goal/tone model?

There is no local dataset with human-labelled marketing `goal` and `tone`. The alternatives were:

| Option | Decision | Reason |
|---|---|---|
| Ask the user to select every goal/tone | Not the core research path | Removes automatic strategy inference. Can be a future override, but not the primary study. |
| Direct Phi-3 label at inference | Not primary | Harder to reproduce/evaluate and can vary across prompts/runs. |
| Rules only | Not primary | Transparent but brittle to paraphrase. |
| Ensemble weak labels -> supervised classifier | Chosen | Retains reproducibility and gives measurable classifier metrics. |

The rules, zero-shot NLI and LLM are separate noisy label sources. Zero-shot classification can formulate labels as textual entailment, including non-topic aspects such as emotion [Yin, Hay & Roth](https://aclanthology.org/D19-1404/). The limitation is fundamental: labels remain weak until a human-reviewed hold-out set is collected.

### 7.2 Why TF-IDF + Logistic Regression versus SentenceBERT + XGBoost?

TF-IDF + LR is fast, interpretable, stable for small data, and a meaningful lexical baseline. SentenceBERT + XGBoost can capture semantic similarity/non-linear decision boundaries but requires additional embedding-model availability and is more fragile on a very small dataset. Both are trained; weighted F1 selects the model because class frequencies are imbalanced. Accuracy alone would hide failure on minority goals.

### 7.3 Why not fine-tune Phi-3?

The project has 113 weakly labelled goal/tone examples, not hundreds/thousands of verified input-output marketing examples. Fine-tuning would risk memorizing label noise and would not produce a defensible quality gain. The safer choice is a frozen pretrained generator plus separate ranking and future feedback adaptation.

### 7.4 Why engagement rate and relative targets instead of likes?

Raw likes measure exposure and account size as much as copy quality. Base training therefore uses interactions/impressions. When future per-account exports arrive, `learning/targets.py` uses a within-account percentile/z-score, so a post is compared with the account's own normal performance. This is the project’s answer to the follower-count confound.

### 7.5 Why best-of-3 rather than one candidate or many candidates?

One candidate makes the result sensitive to one wording. Ranking a small set gives the engagement model a practical decision role. A much larger set risks optimizing model error rather than real quality; this proxy-reward failure is documented for best-of-N selection [Gao, Schulman & Hilton](https://arxiv.org/abs/2210.10760). Therefore the fast path uses three candidates and the full composite score, not engagement alone.

### 7.6 Why historical content-fit, not copying successful captions?

`engagement.py` builds a TF-IDF centroid of the highest-engagement quartile per platform and compares a new candidate to it. It provides a platform-specific structural signal without retrieving/copying a historical post. It is a ranking feature, not a claim that lexical similarity causes engagement.

## 8. Scoring logic

For the integrated app path:

```text
final score = 0.30 * semantic relevance
            + 0.20 * platform formatting fit
            + 0.15 * historical platform-content fit
            + 0.35 * predicted engagement score
```

- Semantic relevance: caption remains related to the product summary.
- Formatting fit: platform word range, hashtag rules, CTA and visual/video-prompt requirements.
- Historical fit: similarity to high-engagement posts from the same available platform.
- Engagement: RandomForest/XGBoost estimate of normalized engagement rate.

The weights are design choices, not learned truths. State that a sensitivity analysis should be run before making strong ranking claims. Do not imply that the four scores are independent or causal.

## 9. Current evidence and honest limitations

Current stored classifier results should be read from `models/goal_tone_training_metrics.json` at presentation time. The latest local run reports approximately:

| Measure | Current value | Correct interpretation |
|---|---:|---|
| Goal classifier | about 65–70% held-out accuracy | Insufficient for an 85% goal-accuracy claim. |
| Tone classifier | about 91% held-out accuracy | Promising, but still only a small weakly labelled test split. |
| Engagement R² | about 0.99 on local data | Use as a ranking proxy; the dataset is synthetic/semi-simulated and likely optimistic. |
| Platform-content fit | no accuracy | It is an unsupervised ranking feature. |
| Generated caption/prompt | no “accuracy” | Needs human quality evaluation and/or real analytics. |

Essential limitations to say proactively:

1. Goal/tone labels are weakly supervised; they are not manual ground truth.
2. Per-platform support is uneven; no historical LinkedIn, TikTok or Email post corpus is available.
3. The M2/M3 multi-platform attribution study includes controlled simulation; label it as simulation.
4. A generated caption cannot be judged by classifier accuracy alone.
5. The app’s candidate ranking predicts a proxy, so it needs future real-world validation.

## 10. Evaluation plan for the final presentation

Use four separate evaluations, never one misleading “overall accuracy.”

| Research question | Metric | Required evidence |
|---|---|---|
| Does goal/tone inference work? | Accuracy, weighted F1, macro F1; confusion matrix | Human-reviewed stratified hold-out set. |
| Is generated copy platform appropriate? | Blind human rubric: goal alignment, tone, platform fit, clarity, prompt usability | 2–3 raters; report agreement and mean score. |
| Does candidate selection help? | Compare selected candidate vs random candidate on the same rubric/real engagement | Paired comparison, not unpaired averages. |
| Does personalization help later? | Within-account engagement percentile / rate uplift | Historical exports with account id and impressions. |

To make an honest >85% claim for goal prediction, collect a balanced, manually verified test set. A reasonable near-term target is 300–500 reviewed examples with all goal classes represented; reserve 20% before model selection. Do not repeatedly tune on that test set.

## 11. What to say in the presentation

### Contribution statement

> We propose a platform-conditioned marketing-content pipeline that converts product context into per-platform strategy and multiple content candidates, then selects candidates using both learned engagement signals and platform-specific historical content evidence. The system is designed for cold start and later adapts from imported account analytics using relative engagement targets to reduce follower-count bias.

### Do not say

- “Our generated captions are 99% accurate.”
- “The 12,000-row engagement dataset proves live engagement.”
- “All platforms have equal historical support.”
- “Fine-tuning Phi-3 improved content quality” (it was not fine-tuned).

### Say instead

- “Goal and tone are separate supervised tasks; their metrics are reported separately.”
- “The engagement model is used as a ranker, not a causal performance guarantee.”
- “Historical-fit evidence is platform-specific where data exists and neutral otherwise.”
- “Future account exports activate a personalized relative-engagement model.”

## 12. Commands to demonstrate

```bash
# Rebuild the goal/tone training data and classifiers.
python3 main.py --step build-dataset goal-tone-train --force

# Train/rebuild base engagement model and historical platform profiles.
python3 main.py --step engagement-train --force

# Run the final integrated pipeline.
python3 orchestrator.py --full --engine fast

# Open the operational presentation UI.
streamlit run app_unified/Home.py
```

For network-limited demonstration machines, ensure the selected local models are already cached. The TF-IDF goal/tone fallback is fully local; SentenceBERT/Phi-3 paths require their pretrained weights to be present.
