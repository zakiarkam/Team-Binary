# Research Evidence, Gap, Novelty, and Design Rationale

This file explains why the project topic is valid for research, what prior work supports it, where the research gap exists, what the novelty is, and why the selected models, datasets, and accuracy methods were chosen.

## 1. Research Area

The project belongs to AI-assisted digital marketing, natural language generation, social media analytics, and machine-learning-based engagement prediction.

The central problem is that businesses need marketing content that is not only fluent, but also platform-specific, aligned with product meaning, likely to engage users, and measurable after generation.

## 2. Proposed Research Title

AI-Driven Platform-Specific Marketing Content Generation Using Engagement Prediction and Adaptive Optimization

## 3. Main Research Problem

Most AI copywriting tools generate text from a prompt, but they usually do not provide a transparent research pipeline that:

1. Crawls real product or website context.
2. Infers campaign goal and tone instead of asking the user to manually provide them.
3. Generates content separately for Instagram, LinkedIn, Shorts, and Email.
4. Predicts engagement using historical social media metrics.
5. Scores semantic relevance, platform suitability, and predicted engagement together.
6. Optimizes weak outputs using score-triggered feedback.
7. Performs statistical before-vs-after validation.
8. Compares AI content against a human baseline.

This project addresses that gap with a reproducible local pipeline.

## 4. Research Gap

Existing generative AI marketing systems are useful for drafting content, but they are commonly closed commercial tools. They often hide model choices, training data, scoring logic, optimization criteria, and validation metrics.

Academic work shows that LLMs can generate marketing copy and can be optimized for engagement. For example, the GCOF copywriting framework studies self-iterative LLM-based copy optimization and reports improved click-through rate in online results. However, this project focuses on a different gap: a transparent, reproducible, modular pipeline that combines website crawling, strategy inference, platform-specific generation, engagement prediction, adaptive optimization, and statistical testing.

## 5. Novelty of This Project

The novelty is not simply "using AI to write captions." The novelty is the complete evaluation-and-optimization loop:

| Component | Common approach | This project |
|---|---|---|
| Campaign strategy | User manually enters campaign goal and tone | Goal and tone are inferred by trained classifiers. |
| Context | User writes a prompt manually | Website/product context is crawled and summarized. |
| Generation | One generic output | Separate outputs for each platform. |
| Evaluation | Human subjective judgment only | Semantic score, platform suitability score, predicted engagement score. |
| Optimization | Manual rewriting | Rule-triggered adaptive re-prompting based on weak scores. |
| Validation | No statistical test | Paired t-test compares before and after optimization. |
| Benchmark | Tool output only | Human baseline can be compared under the same scoring pipeline. |

## 6. Research Questions

Primary research question:

Can a modular AI pipeline generate platform-specific marketing content from website/product context and improve its quality through engagement-aware adaptive optimization?

Sub-questions:

1. How accurately can the system infer campaign goal and marketing tone from marketing text?
2. Can historical social media engagement data predict likely engagement for generated marketing captions?
3. Does adaptive optimization improve final content scores compared with the first generated version?
4. How do optimized AI-generated assets compare with human-written captions under the same evaluation framework?
5. Which platforms benefit most from adaptive optimization?

## 7. Hypotheses

| Hypothesis | Expected evidence |
|---|---|
| H1: Adaptive optimization improves generated content quality. | Mean `after_final_score` is higher than `before_final_score`. |
| H2: The improvement is statistically meaningful. | Paired t-test p-value is below 0.05. |
| H3: Engagement-aware scoring improves selection quality. | Top-ranked outputs have stronger predicted engagement than lower-ranked outputs. |
| H4: Optimized AI content can approach or exceed human baseline scores. | `human_vs_ai_comparison.csv` shows optimized AI mean score close to or higher than human mean score. |

## 8. Existing Research Evidence

| Evidence | Link | How it supports this project |
|---|---|---|
| BART: Denoising Sequence-to-Sequence Pre-training | https://arxiv.org/abs/1910.13461 | Supports the use of BART for abstractive summarization of website/product context. |
| Phi-3 Technical Report | https://arxiv.org/abs/2404.14219 | Supports use of a smaller instruction-tuned language model for local or lower-resource generation. |
| Sentence-BERT | https://arxiv.org/abs/1908.10084 | Supports cosine-similarity evaluation using sentence embeddings. |
| XGBoost | https://arxiv.org/abs/1603.02754 | Supports gradient-boosted trees for tabular ML and engagement prediction. |
| GCOF: Self-iterative Text Generation for Copywriting | https://arxiv.org/abs/2402.13667 | Shows that iterative LLM-based copy optimization is an active research direction. |
| Commercialized Generative AI and Native Advertising | https://arxiv.org/abs/2310.04892 | Shows the relevance and ethical importance of generated advertising content. |
| LLM-generated ads and persuasion | https://arxiv.org/abs/2512.03373 | Shows that LLM-generated ads are being studied against human-created persuasive content. |

## 9. Existing Systems Compared

| System | Link | What it does | Gap this project addresses |
|---|---|---|---|
| Hootsuite Wisdom AI | https://www.hootsuite.com/wisdom-ai | Uses social data to generate content, surface trends, draft posts, and recommend actions. | Closed commercial system; research pipeline, model internals, and scoring formula are not fully reproducible. |
| Buffer AI Assistant | https://buffer.com/ai-assistant | Generates post ideas, repurposes social posts, summarizes long content, and adjusts tone. | Useful tool, but not an academic pipeline with engagement model training, statistical tests, and transparent artifacts. |
| HubSpot Breeze AI | https://www.hubspot.com/products/artificial-intelligence | AI support for marketing, sales, service, and CRM workflows. | Strong business platform, but not designed as a transparent experimental framework for comparing model stages. |

## 10. Why These Models Were Selected

| Project role | Selected model/method | Reason |
|---|---|---|
| Website/product summarization | `facebook/bart-large-cnn` | BART is designed for sequence-to-sequence generation and this checkpoint is fine-tuned for summarization. |
| Marketing generation | `microsoft/Phi-3-mini-4k-instruct` | Instruction-tuned model with manageable size for local research experiments. |
| Semantic similarity | `sentence-transformers/all-MiniLM-L6-v2` | Fast 384-dimensional sentence embeddings suitable for cosine similarity. |
| Goal/tone classification | TF-IDF + Logistic Regression and SentenceBERT + XGBoost | Compares sparse lexical features against dense semantic features; best model is selected by weighted F1. |
| Engagement prediction | RandomForest and XGBoost regressors | Both handle nonlinear feature interactions in tabular data; best model is selected by R2. |
| Statistical validation | Paired t-test | Appropriate because the same platform asset is scored before and after optimization. |

## 11. Why These Datasets Were Selected

### Labeled Marketing Dataset

`RafaM97/marketing_social_media` is selected because it contains marketing-style text suitable for creating training examples for goal and tone classification. The project transforms it into:

```csv
text,campaign_goal,tone,summary
```

Reason: the project needs strategy labels, but the user should not manually provide campaign goal and tone for every new product.

Because a public dataset with exact `text`, `campaign_goal`, and `tone` columns was not available, this project uses transparent pseudo-labeling. The pseudo-labeler assigns campaign goal and tone from marketing keywords, writes confidence columns, removes labels with very low class support, and validates that the final dataset has more than one class. This is not claimed as 100% ground-truth accuracy; it is a reproducible weak-supervision method suitable for a research prototype.

### Engagement Dataset

The engagement dataset is selected because it contains real social media signals:

```csv
platform,text,likes,shares,comments,impressions
```

Reason: engagement prediction must be trained from observed audience interaction data, not only from subjective rules.

### Human Baseline Dataset

The human baseline dataset is selected to compare generated content against human-written content using the same scoring function.

Reason: without a human baseline, the project can show before-vs-after improvement but cannot discuss AI-vs-human performance.

## 12. What Was Done for Accuracy

The project uses several accuracy and validity controls:

| Control | Why it improves research quality |
|---|---|
| Train/test split for classifiers and regressors | Measures performance on unseen data instead of only training data. |
| Weighted F1 for goal/tone classification | Handles class imbalance better than accuracy alone. |
| MAE, RMSE, and R2 for engagement regression | Reports both error size and explained variance. |
| RandomForest vs XGBoost comparison | Avoids relying on one model without benchmark comparison. |
| TF-IDF vs SentenceBERT+XGBoost comparison | Tests lexical and semantic classification strategies. |
| Semantic similarity score | Prevents generated captions from drifting away from product meaning. |
| Platform suitability score | Ensures generated content follows platform-specific format expectations. |
| Engagement score | Adds data-driven ranking based on historical interactions. |
| Paired t-test | Tests whether optimization improvement is statistically meaningful. |
| Human baseline | Gives an external comparison point beyond AI self-improvement. |
| Stage caching and saved CSV/JSON artifacts | Makes outputs auditable and reproducible. |

## 13. Why the Selected Scoring Formula Is Reasonable

The final score is:

```text
final_score = 0.30 * semantic_score
            + 0.25 * platform_suitability_score
            + 0.45 * engagement_score
```

Reasoning:

1. Engagement score has the highest weight because marketing content is ultimately evaluated by audience response.
2. Semantic score prevents high-engagement but irrelevant captions from being ranked too highly.
3. Platform suitability score ensures that each caption fits the selected channel.
4. The formula is transparent and can be changed in `config.py` for ablation experiments.

## 14. Existing System Limitations That Motivate the Project

Commercial AI marketing tools are strong in usability but weak for academic reproducibility. They often do not reveal:

1. Which models are used.
2. How campaign strategy is inferred.
3. Whether engagement prediction is trained on historical metrics.
4. How content is scored.
5. Whether optimization is statistically validated.
6. Whether AI content is compared against human content under the same scoring rules.

This project is designed as a research pipeline, not only a productivity tool.

## 15. Expected Contribution

The expected contribution is a transparent and reproducible framework for AI marketing content generation that:

1. Converts product/website context into a structured marketing knowledge base.
2. Infers campaign goal and tone automatically.
3. Generates platform-specific marketing assets.
4. Predicts engagement from historical social media data.
5. Ranks generated assets using a combined quality score.
6. Optimizes weak outputs using score-triggered rules.
7. Validates improvement with a paired t-test.
8. Benchmarks AI output against human-written content.

## 16. Limitations to Report Honestly

Include these limitations in the final research report:

1. Engagement prediction quality depends on dataset size, platform balance, and data cleanliness.
2. Likes, comments, and shares are imperfect proxies for real business value such as sales or retention.
3. Platform suitability rules are heuristic and may not capture all platform algorithm changes.
4. Phi-3 generation can still hallucinate or produce generic marketing language.
5. The system predicts likely engagement; it does not replace live A/B testing.
6. If the human baseline sample is small, human-vs-AI conclusions must be reported cautiously.

## 17. Suggested Final Report Structure

Use this structure for the thesis/report:

1. Introduction
2. Problem statement
3. Research gap
4. Research questions and hypotheses
5. Literature review
6. Existing systems comparison
7. Methodology
8. Dataset preparation
9. System architecture
10. Model selection rationale
11. Evaluation metrics
12. Results
13. Statistical analysis
14. Human baseline comparison
15. Discussion
16. Limitations
17. Future work
18. Conclusion
19. References

## 18. Suggested Future Work

1. Add live A/B testing with real campaign outcomes.
2. Fine-tune a domain-specific marketing generator.
3. Replace platform suitability heuristics with a learned classifier.
4. Add image generation and image quality evaluation.
5. Add cost, latency, and carbon-efficiency comparison between small and large models.
6. Add explainable AI methods for engagement prediction.
7. Evaluate more platforms such as Facebook, TikTok, X, Pinterest, and YouTube.

## 19. References

- Lewis et al., BART: https://arxiv.org/abs/1910.13461
- Abdin et al., Phi-3 Technical Report: https://arxiv.org/abs/2404.14219
- Reimers and Gurevych, Sentence-BERT: https://arxiv.org/abs/1908.10084
- Chen and Guestrin, XGBoost: https://arxiv.org/abs/1603.02754
- Zhou et al., GCOF copywriting optimization: https://arxiv.org/abs/2402.13667
- Zelch et al., Generative AI/native advertising: https://arxiv.org/abs/2310.04892
- Meguellati et al., LLM-generated ads: https://arxiv.org/abs/2512.03373
- BART model card: https://huggingface.co/facebook/bart-large-cnn
- Phi-3 model card: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct
- MiniLM model card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- RafaM97 dataset: https://huggingface.co/datasets/RafaM97/marketing_social_media
- Hootsuite Wisdom AI: https://www.hootsuite.com/wisdom-ai
- Buffer AI Assistant: https://buffer.com/ai-assistant
- HubSpot AI: https://www.hubspot.com/products/artificial-intelligence
