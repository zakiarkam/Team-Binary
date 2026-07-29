# Member 4 Contribution Guide — AI Content Refinery

> **Implementation status (important):** the current saved goal/tone models are
> trained on 527 weakly labelled rows with no platform column. They therefore
> infer one campaign goal/tone from product context; platform rules adapt the
> resulting asset format. The platform-conditioned strategy path in this guide
> is the next research extension and must be retrained/evaluated on
> platform-labelled examples before it is claimed as a measured capability.

## 1. My module in one sentence

Member 4 delivers the **AI Content Refinery (M4)**: it converts a product brief or website context into platform-specific captions and creative prompts, predicts a goal and tone for every platform, generates multiple candidate posts, and returns the best candidate using relevance, compliance, engagement, and historical content-fit signals.

```text
website/product brief
  -> knowledge base -> strategy prediction per platform
  -> generate candidates -> score/rank -> platform-ready asset
  -> later real analytics -> personalized ranking model
```

## 2. Scope: what belongs to M4 and what does not

| Belongs to my M4 contribution | Input from other modules |
|---|---|
| Website/product-context processing | M1 audience segment is optional contextual input. |
| Goal/tone weak labelling and classifiers | M2/M3 may provide campaign/platform priority, but they do not generate copy. |
| BART summary, Phi-3/fast generation, platform rules | M3 priority only reorders requested platforms. |
| Engagement prediction, historical content fit, candidate selection | M4 owns the caption-level score and final selected assets. |
| Optimization, significance testing, human comparison, feedback learning | M1–M3 own segmentation, automation and funnel analytics. |

## 3. M4 final pipeline

```text
INPUT
product_name, website_url, target_audience, customer_segment, selected platforms
     |
     v
1. crawler.py + knowledge_base.py
   website text -> clean product knowledge base
     |
     v
2. goal_tone.py, separately for each selected platform
   [Platform: Instagram + product context] -> goal classifier -> campaign_goal
   [Platform: Instagram + product context] -> tone classifier -> tone
     |
     v
3. summary.py / content_service.py
   context -> concise marketing brief -> strategy-aware generation context
     |
     v
4. content_service.py
   fast engine: 3 candidates/platform
   Phi-3 engine: platform-native JSON caption + CTA + image/video prompt
     |
     v
5. engagement.py + evaluation.py
   predicted engagement + historical platform fit + semantic relevance + format fit
     |
     v
6. content_service.py
   highest composite-scoring candidate is returned per platform
     |
     v
OUTPUT
caption, hashtags, CTA, image/video prompt, goal, tone, component scores
```

## 4. Files, functions, inputs, and outputs

| File | Main functions | Role in my module | Output/artifact |
|---|---|---|---|
| `config.py` | `platform_spec()`, `select_visual()` | Single source of platform length, hashtag, visual and score rules. | Shared constants and paths. |
| `crawler.py` | `run()` | Retrieves website text when a URL is supplied. | Crawl JSON. |
| `knowledge_base.py` | `build()`, `run()` | Cleans and deduplicates website/product text. | `marketing_knowledge_base.json`. |
| `dataset/preprocess_marketing.py` | preprocessing functions | Converts RafaM97 source records into clean marketing text. | `marketing_preprocessed.csv`. |
| `dataset/label_campaign_goal.py` | `run()` | Weak-labels goal using rules, zero-shot and Phi-3 signals. | `campaign_goal_labeled.csv`. |
| `dataset/label_tone.py` | `run()` | Weak-labels tone using rules, BART-MNLI and Phi-3 arbitration. | `tone_labeled.csv`. |
| `dataset/build_final_dataset.py` | `build()`, `extract_platforms()` | Confidence-gates labels; retains source-explicit platforms. | Goal/tone training and research CSVs. |
| `goal_tone.py` | `train()`, `predict_one()`, `predict()` | Trains/selects goal and tone classifiers; predicts separately per platform. | `best_goal_model.pkl`, `best_tone_model.pkl`, metrics JSON. |
| `summary.py` | `build()`, `run()` | Uses BART to make a concise generation brief. | `marketing_summary.json`. |
| `generator.py` | `build_prompt()`, `standardize()`, `run()` | Phi-3 platform-specific generation and JSON standardization. | Generated asset CSV. |
| `content_service.py` | `generate()`, `_platform_strategy()`, `score_assets()` | Final app-facing M4 service: creates candidates and selects the best per platform. | Asset records for app/export. |
| `engagement.py` | `train()`, `score()`, `platform_content_fit()` | Engagement-rate regressor and high-engagement platform-content profiles. | Engagement model + historical profiles. |
| `evaluation.py` | `semantic_score()`, `platform_suitability()` | Relevance and platform-format scoring. | Component scores/ranked CSV. |
| `optimization.py` | `run()` | Re-prompts legacy weak assets and re-scores them. | Optimized assets/comparison. |
| `significance.py` | `run()` | Paired before/after statistical test. | Significance CSV. |
| `human_baseline.py` | `run()` | Sends human and AI text through the same scorer. | Human-vs-AI CSV. |
| `learning/` | importer, targets, personalize, candidates | Future account-specific adaptation from analytics exports. | SQLite feedback store + personalized model. |

## 5. Models and algorithms: comparison and choice reason

| Task | Alternatives considered | Chosen implementation | Why it is reasonable | Honest limitation |
|---|---|---|---|---|
| Summarization | Extractive, T5/Pegasus, BART | `facebook/bart-large-cnn` | BART is an established seq2seq denoising model for generation/summarization. | CNN/DailyMail is news-domain, not marketing-domain; summary may hallucinate. |
| Content generation | Templates, smaller local LLM, larger/API LLM | Phi-3-mini-4k-instruct; fast templates for responsive UI | Phi-3 is local, reproducible and instruction tuned; fast path permits immediate demo results. | Phi-3 is not fine-tuned on verified marketing examples. |
| Goal/tone labels | Manual labels, rules only, direct LLM, weak supervision | Rules + zero-shot NLI + Phi-3 -> confidence-gated training set | Allows transparent labels where no public exact labels exist. | Labels are weak supervision, not ground truth. |
| Goal/tone prediction | Rules only, TF-IDF+LR, SBERT+XGBoost, direct LLM | TF-IDF+LR vs SBERT+XGBoost; weighted-F1 selection | Compares sparse lexical and dense semantic features; weighted F1 handles imbalance. | Only 113 usable platform rows; goal accuracy is not yet 85%+. |
| Engagement ranking | Likes, linear model, neural regressor, RF, XGBoost | RF vs XGBoost on engagement rate | Tree models are effective tabular baselines and capture non-linear interactions. | Very high R² on public/synthetic data is optimistic; use as a ranker. |
| Platform relevance | Hard-coded rules only, nearest-post copying, TF-IDF profile | TF-IDF centroid from top engagement quartile | Uses historical platform evidence without copying a post. | It is similarity, not a causal performance measurement. |
| Candidate choice | One output, best-of-N by engagement only, best-of-N composite | Best-of-3 composite selection | Gives generation variation while limiting proxy over-optimization. | Must later validate against human ratings/real analytics. |

### Research support for the choices

- **BART:** Its denoising seq2seq pretraining supports generation and summarization tasks [Lewis et al., 2020](https://aclanthology.org/2020.acl-main.703/).
- **Phi-3:** Phi-3-mini is a 3.8B compact language model designed for capable local deployment [Abdin et al., 2024](https://arxiv.org/abs/2404.14219).
- **Sentence embeddings:** Sentence-BERT provides efficient semantic embeddings and similarity retrieval [Reimers & Gurevych, 2019](https://aclanthology.org/D19-1410/).
- **Zero-shot weak labels:** Textual-entailment formulations can classify labels for previously unseen tasks/aspects [Yin, Hay & Roth, 2019](https://aclanthology.org/D19-1404/).
- **Weak supervision:** Combining imperfect labeling sources is a recognized solution when manually labelled data is scarce [Bach et al., 2017](https://proceedings.mlr.press/v70/bach17a.html).
- **Small best-of-N:** Optimizing too aggressively against a learned proxy can harm true quality, so candidate count remains small and selection uses a composite score [Gao, Schulman & Hilton](https://arxiv.org/abs/2210.10760).

## 6. Exact datasets and correct claims

| Dataset | My use | Correct claim | Do not claim |
|---|---|---|---|
| RafaM97 raw, 689 rows | Source text for weak goal/tone labelling. | “We derive a transparent weakly supervised strategy dataset.” | “RafaM97 contains original human goal/tone labels.” |
| Final goal/tone training rows, 113 | Classifier training with platform-conditioned input. | “We evaluate two classifier families on a small weakly labelled corpus.” | “It proves high per-platform accuracy.” |
| Engagement datasets, 12,000 rows | Engagement-rate prediction and historical platform profiles. | “We use platform and text features to rank candidates.” | “It directly labels goal, tone, or generated-caption quality.” |
| Comment datasets | Not used for copy training. | “They can be future audience-response data.” | “They are marketing captions.” |
| Future platform analytics CSVs | Personalized engagement learning. | “They activate account-normalized, real-data adaptation.” | “They are already in the current evaluation.” |

## 7. My scoring and selection logic

For the unified app, each candidate receives:

```text
final score = 0.30 * semantic relevance
            + 0.20 * platform-format fit
            + 0.15 * historical platform-content fit
            + 0.35 * predicted engagement
```

1. **Semantic relevance** checks whether the caption remains related to the product brief.
2. **Platform-format fit** checks word range, hashtag policy, CTA and the correct image/video prompt type.
3. **Historical content fit** compares a caption with the top-engagement text profile for the same historical platform. Instagram/Facebook have direct profiles; Shorts use YouTube; unavailable platforms receive a neutral score rather than unrelated evidence.
4. **Predicted engagement** estimates normalized engagement rate from text features and platform.
5. The highest full-score candidate is selected per platform. It is not selected by engagement alone.

The weights are declared design weights. They should be called a multi-criteria decision rule, not learned causal weights.

## 8. M4 research gap and novelty

### Gap

There is a gap between generic AI-copy generation and engagement analytics:

- LLMs can create captions but usually return one unvalidated answer.
- Engagement datasets describe existing post performance but do not directly create product-specific copy.
- Raw engagement is confounded by follower count and reach.
- Small businesses often lack enough labelled goal/tone data to train platform-specific strategy models.

### My defensible novelty

> A platform-conditioned content-refinery pipeline that predicts strategy separately for each target platform, generates multiple candidates, and chooses the final asset using product relevance, platform compliance, predicted engagement and historical high-engagement content evidence. The design supports later account-level adaptation through relative engagement targets without fine-tuning the generator or auto-posting content.

This is an **integration and inference-time decision contribution**. Do not claim a new foundation model, a new classifier algorithm, or proven live engagement uplift.

## 9. Current results and what to say honestly

| Result | Presentation wording |
|---|---|
| Tone held-out accuracy is around 91% in the current artifact. | “Tone is the stronger classifier, but the test set is small and weakly labelled.” |
| Goal held-out accuracy is around 65–70%. | “Goal prediction is the current bottleneck; we do not claim an 85% goal accuracy.” |
| Engagement R² is around 0.99. | “The public corpus result is used as a ranking proxy; it is likely optimistic and requires real-export validation.” |
| Historical content fit has no accuracy. | “It is an evidence feature for ranking, not a classifier.” |
| Generated captions/prompts have no class accuracy. | “We evaluate them using platform rules, blind human ratings and future real analytics.” |

## 10. Evaluation and future work

### What I can evaluate now

1. Goal/tone classifier accuracy, weighted F1 and macro F1.
2. Platform-format compliance rate.
3. Before/after optimization score comparison and paired test.
4. Human-versus-AI comparison using the same scoring pipeline.
5. Candidate-selection comparison: best candidate versus a random candidate.

### What makes the project stronger after presentation

When platform CSV exports arrive, store:

```text
platform, account_id, post_id, caption, publish_time, followers_at_post_time,
impressions/reach, likes, comments, shares, clicks, conversions
```

Then apply the existing `learning/` path:

```text
feedback-import -> engagement-retrain -> generate-candidates
```

The target should be engagement rate and, with enough history, an account-relative percentile/z-score. This prevents a large account from looking better merely because it has more followers.

## 11. Short presentation script

> “My module is the AI Content Refinery. It takes a product context and selected social platforms, predicts a goal and tone separately for each platform, then creates several caption and creative-prompt candidates. Rather than returning the first LLM output, it ranks candidates using semantic relevance, platform rules, predicted engagement and similarity to successful historical content from the same platform. The model is deliberately not fine-tuned on our small weakly labelled corpus. Instead, the pretrained generator is kept frozen and learning happens in the strategy and ranking layers. When real platform analytics become available, the module retrains a personalized engagement ranker using within-account relative engagement, addressing the follower-count bias.”
