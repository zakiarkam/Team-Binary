# Research Analysis

A grounded account of what this project actually is: the structure that exists in
the code, the decisions already taken, the evidence behind them, how accuracy is
computed, where the novelty defensibly sits, and which claims will not survive
review.

Everything here was checked against the code and the artifacts on disk. Where the
code and the older documents disagree, the code wins and the disagreement is
noted.

---

## 1. Current structure

Twelve top-level Python modules, one `dataset/` package of four weak-labeling
modules, one `dashboard/` package, and a file-mediated artifact tree.

```
Research/
├── input.json                  ← the entire user-supplied input
├── main.py                     CLI orchestrator, 16 named stages
├── config.py                   paths, model names, weights, thresholds, thread policy
├── models.py                   lazy BART / Phi-3 / MiniLM loaders + device & dtype policy
│
├── crawler.py                  website → structured raw text
├── knowledge_base.py           raw text → cleaned, deduped combined_text
├── summary.py                  combined_text → BART abstractive brief
├── generator.py                brief → per-platform JSON assets (Phi-3)
│
├── dataset/                    ── weak supervision, run once ──
│   ├── preprocess_marketing.py     RafaM97 raw → cleaned rows
│   ├── label_campaign_goal.py      rule + zero-shot + Phi-3 → campaign_goal
│   ├── label_tone.py               rule + BART-MNLI + Phi-3 → tone (4 checkpointed stages)
│   └── build_final_dataset.py      confidence gate → training + research splits
│
├── goal_tone.py                TF-IDF+LR vs SBERT+XGB, select by weighted F1
├── engagement.py               RF vs XGBoost on engagement_rate, select by R²
├── evaluation.py               semantic + platform-fit + composite score, rank
├── optimization.py             threshold-triggered re-prompt + re-score
├── significance.py             paired t-test on before/after
├── human_baseline.py           human captions through the identical scorer
│
├── dashboard/                  Streamlit research dashboard (read-only over artifacts)
├── tests/                      45 tests, no model downloads
├── data/{raw,intermediate,processed,outputs}/
└── models/                     trained classifiers + regressor + metrics JSON
```

### Structural facts worth knowing

- **Stages communicate only through files.** No stage holds a reference to
  another stage's objects. This is why `--step` works and why the dashboard can
  read everything without importing the pipeline.
- **A stage is skipped if its output file exists**, unless `--force`. Cheap
  iteration, but it also means a stale artifact silently survives a config change.
- **`models/` and `outputs/models/` are different things.** `models/` holds this
  project's artifacts. `outputs/models/` holds seven `.pkl` files
  (`conversion_*`, `drop_off_*`, `learned_recommender`) that no module in this
  repository reads or writes, alongside `data/raw/bank_marketing/`. These are
  leftovers from unrelated work — 41 MB of it. They should be deleted or moved
  out before submission; right now they make the repository look like two
  projects glued together.

---

## 2. The pipeline, and how the parts connect

### Is there only one pipeline?

**One pipeline, three flows.** The 16 stages form a single linear DAG, but they
decompose into three groups with very different lifecycles. This distinction is
the thing to put in the write-up, because "one pipeline" and "runs end-to-end
per product" are not the same claim.

| Flow | Stages | Runs | Depends on the product? |
|---|---|---|---|
| **A. Goal/tone supervision** | `preprocess-dataset → label-goal → label-tone → build-dataset → goal-tone-train` | Once | No |
| **B. Engagement supervision** | `engagement-train` | Once | No |
| **C. Per-product inference** | `crawl → kb → goal-tone-predict → summary → generate → engagement-score → evaluate → optimize → significance → human-baseline` | Every product | Yes |

Flows A and B produce three model artifacts. Flow C consumes them. A new product
only re-runs flow C — which is exactly the workflow the README's "test a new
product" recipe encodes.

### How the flows interconnect

```
      ── FLOW A (once) ─────────────────────────────────┐
  RafaM97 corpus                                        │
      │  preprocess-dataset                             │
      ▼                                                 │
  689 cleaned rows                                      │
      │  label-goal    rule ⊕ zero-shot ⊕ Phi-3         │
      │  label-tone    rule ⊕ BART-MNLI ⊕ Phi-3         │
      ▼                                                 │
  689 weak-labeled rows ── build-dataset ──▶ 121 gated  │
      │                                                 │
      │  goal-tone-train  (TF-IDF+LR vs SBERT+XGB)      │
      ▼                                                 │
  best_goal_model.pkl, best_tone_model.pkl ─────────────┤
                                                        │
      ── FLOW B (once) ────────────────────────────┐    │
  12,000-row engagement corpus                     │    │
      │  engagement-train  (RF vs XGBoost by R²)   │    │
      ▼                                            │    │
  best_engagement_model.pkl ──────────────────┐    │    │
                                              │    │    │
      ── FLOW C (per product) ────────────────┼────┼────┼──
  input.json                                  │    │    │
      │  crawl                                │    │    │
      ▼                                       │    │    │
  crawled_website_data.json                   │    │    │
      │  kb                                   │    │    │
      ▼                                       │    │    │
  marketing_knowledge_base.json ──────────────┼────┼────┤
      │                                       │    │    │
      │  goal-tone-predict ◀───────────────────────┴────┘
      ▼        (classifies combined_text → campaign_goal, tone)
  KB + inferred goal & tone
      │  summary  (BART-large-cnn)
      ▼
  marketing_summary.json ─────────────────┐
      │  generate  (Phi-3, one batch)     │  (also the semantic reference
      ▼                                   │   and the re-prompt context)
  generated_platform_assets.csv           │
      │  engagement-score ◀───────────────┼──── best_engagement_model.pkl
      ▼                                   │
  + predicted_engagement, engagement_score│
      │  evaluate ◀────────────────────────┘
      ▼        (semantic vs summary, platform checklist, weighted sum)
  ranked_platform_assets.csv
      │  optimize   (rule chosen by which score fell short → Phi-3 re-prompt
      ▼              → identical re-scoring)
  optimized_ranked_platform_assets.csv + before_after_comparison.csv
      │  significance  (paired t-test)
      ▼
  optimization_significance_test.csv
      │  human-baseline  (human captions through the identical scorer)
      ▼
  human_vs_ai_comparison.csv
```

**The three couplings that matter:**

1. `marketing_summary.json` is used **three times** — as generation context, as
   the semantic-similarity reference, and as re-prompt context. A bad summary
   corrupts generation *and* the metric that is supposed to catch bad generation.
   The metric cannot detect its own reference being wrong.
2. `optimize` re-uses `engagement.score`, `evaluation.semantic_score` and
   `evaluation.platform_suitability` directly — not copies. Before and after are
   therefore genuinely commensurable. This is done correctly.
3. `human-baseline` runs human text through the same three scorers. Also correct
   as an implementation — but see §6 for why the *comparison* is still unfair.

### Input and output of the entire pipeline

**Input — everything the user supplies:**

```json
{
  "product_name": "EcoSmart Bottle",
  "website_url": "https://www.shopify.com",
  "target_audience": "young professionals",
  "customer_segment": "eco-conscious buyers",
  "preferred_platforms": ["instagram", "linkedin", "shorts", "email"]
}
```

Plus three corpora that are inputs to the system but not to a run: the RafaM97
marketing corpus, a 12,000-row engagement corpus, and a human caption CSV.

`campaign_goal` and `tone` are deliberately **absent**. They are predicted. That
absence is the research contribution's entry point.

**Output — one row per platform:**

| Column | Source |
|---|---|
| `platform` | input |
| `caption`, `hashtags`, `cta` | Phi-3 |
| `image_prompt` *or* `shorts_prompt` | Phi-3, whichever the platform uses |
| `predicted_engagement` | engagement regressor |
| `engagement_score` | min-max normalized within the batch |
| `semantic_score` | cosine(MiniLM(summary), MiniLM(caption)) |
| `platform_suitability_score` | rule checklist pass rate |
| `final_score` | 0.30·semantic + 0.25·platform + 0.45·engagement |
| `optimization_rule` | which rule fired (optimized set only) |

Plus three evidence artifacts: the before/after comparison, the significance
test, and the human comparison.

---

## 3. Model choices — what was actually compared

This is the distinction that will decide how the methodology chapter reads. Two
of the six choices are empirical selections. Four are declared design choices.
Presenting all six as "model comparison" is the single easiest thing for an
examiner to attack.

| Role | Chosen | Alternatives | Basis | Honest label |
|---|---|---|---|---|
| Summarization | `bart-large-cnn` | Pegasus, T5, extractive | argument + fit | **Declared** |
| Generation | `Phi-3-mini-4k-instruct` | Mistral-7B, Llama-3-8B, API models | argument + fits 16 GB at fp16 | **Declared** |
| Semantic similarity | `all-MiniLM-L6-v2` | MPNet, larger SBERT | argument | **Declared** |
| Zero-shot labeling | `bart-large-mnli` | — | used *within* an ensemble, not selected against anything | **Declared** |
| Goal/tone classifier | TF-IDF + LogReg | SBERT + XGBoost | **highest weighted F1 on held-out split** | **Empirical** |
| Engagement regressor | best of RF / XGBoost | each other | **highest R² on held-out split** | **Empirical** |

### ⚠ The goal/tone comparison currently has one arm

`models/goal_tone_training_metrics.json` contains **two** result entries — one
per target, both `tfidf_logistic`. The Sentence-BERT + XGBoost arm produced no
metrics, which means it was skipped (`GOAL_TONE_SKIP_XGBOOST`, the macOS
OpenMP escape hatch in `config.py`). **The "best of two by weighted F1" selection
therefore compared exactly one candidate.** Re-run `goal-tone-train` with both
arms before reporting this as a comparison. The dashboard raises this warning
automatically on the Models page.

### Citations for each decision

**Summarization — `bart-large-cnn`**
- Lewis et al., *BART*, ACL 2020 — [arXiv:1910.13461](https://arxiv.org/abs/1910.13461). The model paper; `bart-large-cnn` is BART-large fine-tuned on CNN/DailyMail.
- Maynez et al., *On Faithfulness and Factuality in Abstractive Summarization*, ACL 2020 — [arXiv:2005.00661](https://arxiv.org/abs/2005.00661). **Against you**: all neural abstractive summarizers hallucinate substantially. A hallucinated brief propagates fabricated brand claims into every downstream asset.
- **Domain caveat to declare, not hide**: CNN/DailyMail is news wire. Crawled marketing copy — nav text, CTAs, product bullets — is out of domain.

**Generation — `Phi-3-mini-4k-instruct`**
- Abdin et al., *Phi-3 Technical Report*, 2024 — [arXiv:2404.14219](https://arxiv.org/abs/2404.14219). 3.8B params rivalling Mixtral-8x7B / GPT-3.5 while running locally. This is the justification for local open weights over an API: cost, reproducibility, data control.
- Wei et al., *FLAN*, ICLR 2022 — [arXiv:2109.01652](https://arxiv.org/abs/2109.01652). Why the `-instruct` suffix makes zero-shot per-platform generation reasonable to expect.
- Tam et al., *Let Me Speak Freely?*, EMNLP 2024 Industry — [arXiv:2408.02442](https://arxiv.org/abs/2408.02442). **Against you**: forcing JSON output measurably degrades LLM performance, worse with stricter schemas. Your prompt demands caption + hashtags + CTA + creative prompt in one JSON object. This is both a threat to validity and a cheap ablation.

**Semantic similarity — `all-MiniLM-L6-v2` + cosine**
- Reimers & Gurevych, *Sentence-BERT*, EMNLP 2019 — [arXiv:1908.10084](https://arxiv.org/abs/1908.10084). Why cosine over these embeddings is meaningful at all.
- Wang et al., *MiniLM*, NeurIPS 2020 — [arXiv:2002.10957](https://arxiv.org/abs/2002.10957). The distilled backbone; the latency argument.
- Steck, Ekanadham & Kallus, *Is Cosine-Similarity of Embeddings Really About Similarity?*, WWW '24 — [arXiv:2403.05440](https://arxiv.org/abs/2403.05440). **Against you**: cosine on learned embeddings can be arbitrary and non-unique depending on regularization. Directly challenges giving a raw cosine a fixed 0.30 weight and calling it "content preservation."
- **Structural criticism**: a 20-word caption compared against a 200-word brief is length- and register-confounded. A low score may mean *good copywriting*, not information loss.

**Zero-shot tone labeling — `bart-large-mnli` + Phi-3 arbitration + rules**
- Yin, Hay & Roth, *Benchmarking Zero-shot Text Classification*, EMNLP 2019 — [ACL D19-1404](https://aclanthology.org/D19-1404/). **The originating method paper** for the entire entailment-as-zero-shot approach. It explicitly covers emotion-aspect labels — the closest published analogue to zero-shot tone. Mandatory citation.
- Williams et al., *MultiNLI*, NAACL 2018 — [ACL N18-1101](https://aclanthology.org/N18-1101/). The corpus behind the `-mnli` checkpoint.
- Ratner et al., *Snorkel*, VLDB 2017 — [arXiv:1711.10160](https://arxiv.org/abs/1711.10160); *Data Programming*, NeurIPS 2016 — [arXiv:1605.07723](https://arxiv.org/abs/1605.07723). **Your three-method ensemble is a hand-rolled Snorkel.** Cite it and state plainly that you use heuristic confidence and agreement rather than Snorkel's learned generative label model.
- Zhang et al., *PromptedWS*, 2024 — [arXiv:2402.01867](https://arxiv.org/abs/2402.01867). Closest prior art to "LLM as one labeling function among several."

**Goal/tone classification — TF-IDF+LR vs SBERT+XGB**
- Spärck Jones 1972 ([DOI](https://www.emerald.com/insight/content/doi/10.1108/eb026526/full/html)) and Salton & Buckley 1988 — the IDF and term-weighting origins.
- Joulin et al., *fastText*, EACL 2017 — [arXiv:1607.01759](https://arxiv.org/abs/1607.01759). **The strongest citation for why TF-IDF+LR is a serious contender, not a strawman**: linear bag-of-features classifiers are often on par with deep ones and orders of magnitude faster.
- Reimers & Gurevych 2019; Chen & Guestrin 2016 — the embedding arm.
- **Gap**: there is no canonical head-to-head benchmark paper for this exact pairing. Frame yours as an empirical *model-selection procedure*, not a finding.

**Engagement regression — RF vs XGBoost**
- Breiman, *Random Forests*, 2001 — [DOI](https://link.springer.com/article/10.1023/A:1010933404324).
- Chen & Guestrin, *XGBoost*, KDD 2016 — [arXiv:1603.02754](https://arxiv.org/abs/1603.02754).
- Grinsztajn et al., *Why do tree-based models still outperform deep learning on typical tabular data?*, NeurIPS 2022 — [arXiv:2207.08815](https://arxiv.org/abs/2207.08815). **The justification for not trying a neural regressor.** Use it; it closes an obvious question.
- Kim & Hwang, 2025 — [arXiv:2508.21650](https://arxiv.org/abs/2508.21650). Closest task analogue. Two lessons: log-transform the skewed target, and beware that a very high R² on likes usually signals exposure-count leakage — a direct warning about your `impressions` denominator.

**Composite scoring — the 0.30/0.25/0.45 weights**
- Nardo, Saisana, Saltelli et al., *Handbook on Constructing Composite Indicators*, OECD/JRC 2008 — [PDF](https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf). **This is the reference a reviewer will use against you.** It mandates uncertainty and sensitivity analysis over weights and documents that min-max normalization is highly outlier-sensitive and that normalization choice materially changes rankings. There is no NLP paper that justifies these weights — this is a composite-indicator construction problem, and unjustified weights are a liability rather than a contribution.

**Adaptive optimization — threshold-triggered re-prompting**
- Madaan et al., *Self-Refine*, NeurIPS 2023 — [arXiv:2303.17651](https://arxiv.org/abs/2303.17651). The canonical generate→feedback→refine loop and your direct methodological ancestor. Differentiate: your feedback is **external and quantitative**, theirs is self-generated and verbal.
- Shinn et al., *Reflexion*, NeurIPS 2023 — [arXiv:2303.11366](https://arxiv.org/abs/2303.11366). Structurally the closest published analogue: scalar signal → verbal feedback → retry. Your `final_score` plays the role of the environment reward.
- Bai et al., *Constitutional AI*, 2022 — [arXiv:2212.08073](https://arxiv.org/abs/2212.08073). Your rule injection is a non-RL, single-step constitutional revision.
- Huang et al., *LLMs Cannot Self-Correct Reasoning Yet*, ICLR 2024 — [arXiv:2310.01798](https://arxiv.org/abs/2310.01798). **This one supports you** — LLMs fail to self-correct *without external feedback*. Your loop has external feedback. Use it that way.
- Stechly et al., 2023 — [arXiv:2310.12397](https://arxiv.org/abs/2310.12397). **Motivates the essential ablation**: apparent iterative gains can be lucky resampling. Without a random-resample control you cannot claim the *rule* did the work.

---

## 4. Research areas covered

Seven, which is unusually broad for one project — and that breadth is itself a
risk, because each area gets shallow treatment.

| # | Area | Where | Depth |
|---|---|---|---|
| 1 | **Web information extraction** | `crawler.py`, `knowledge_base.py` | Shallow — BeautifulSoup, single page, no JS rendering |
| 2 | **Abstractive summarization** | `summary.py` | Applied — off-the-shelf, no fine-tuning, no summarization eval |
| 3 | **Weak supervision / programmatic labeling** | `dataset/label_*.py` | **Deepest original work** — 3-method ensemble, calibration, confidence gating, checkpointing |
| 4 | **Text classification / model selection** | `goal_tone.py` | Standard — two representations, held-out split, weighted-F1 selection |
| 5 | **Social-media engagement prediction** | `engagement.py` | Standard — 8 handcrafted features + platform one-hot, tree ensembles |
| 6 | **Controlled NLG** | `generator.py`, `config.PLATFORM_SPECS` | Applied — schema + constraint prompting, capability table as single source of truth |
| 7 | **Feedback-driven optimization + statistical validation** | `optimization.py`, `significance.py`, `human_baseline.py` | Applied — the closed loop, currently under-powered |

Areas 3, 6 and 7 carry the contribution. Areas 1, 2, 4 and 5 are competent
plumbing that should be presented as such.

---

## 5. Research question and novelty

### The question the system actually answers

> Given only a product website and an audience description, can a fully
> open-weight, offline-evaluable pipeline infer campaign strategy, generate
> platform-appropriate marketing assets, and improve them against a supervised
> engagement signal — without production traffic, reinforcement learning, or a
> proprietary API?

That framing is defensible because every clause corresponds to something the
code does, and the constraints ("open-weight", "offline", "no traffic", "no RL")
are what separate it from the closest prior work.

### Sub-questions

1. Can `campaign_goal` and `tone` be recovered from website text by classifiers
   trained on weakly-labeled marketing copy, well enough to condition generation?
2. Does an engagement regressor trained on observed interaction data provide a
   usable optimization signal at inference time, standing in for the LLM judge
   that prior work uses?
3. Does threshold-triggered, rule-conditioned re-prompting improve assets more
   than resampling alone?
4. How do the resulting assets score relative to human-written captions under an
   identical metric?

Sub-question 3 is currently **not answered** — the random-resampling control does
not exist. It is the cheapest high-value experiment available.

### What is NOT novel — do not claim these

Each of these is already claimed in the literature, with better evidence:

| Claim | Already owned by |
|---|---|
| LLMs can adapt marketing content per platform | *Understanding User Engagement with Cross-Platform Social Media Content…*, ACM TWEB — [DOI 10.1145/3756014](https://dl.acm.org/doi/10.1145/3756014). GPT-4 across Facebook/Instagram/X, **892 human evaluators**. |
| LLM marketing copy generation with automated evaluation | Liu et al., *MarketingFM + AutoEval*, KDD 2025 — [arXiv:2506.17863](https://arxiv.org/abs/2506.17863). Rule metrics *and* LLM-judge, 89.6% human agreement, **online A/B: +9% CTR**. |
| Feedback-driven regeneration of generated text | Self-Refine, Reflexion, and Azov et al. *SCRABLE* — [arXiv:2405.03845](https://arxiv.org/abs/2405.03845). |
| Optimizing ad text against an engagement/CTR signal | Chen et al. — [arXiv:2507.20227](https://arxiv.org/abs/2507.20227); *RELATE* — [arXiv:2602.11780](https://arxiv.org/abs/2602.11780); Zeng et al. *Let AI Entertain You* — [arXiv:2312.12457](https://arxiv.org/abs/2312.12457). |
| Weak supervision by ensembling noisy labelers | Snorkel / Data Programming. |
| Zero-shot NLI for tone labels | Yin et al. 2019 — it literally includes emotion-aspect zero-shot classification. |

**MarketingFM ([arXiv:2506.17863](https://arxiv.org/abs/2506.17863)) is your closest
competitor and it has online A/B evidence you cannot obtain.** Read it before
writing the related-work chapter; do not let an examiner introduce it to you.

### The defensible novelty, ranked

**1 (strongest). Substituting a supervised engagement regressor for the LLM judge
in an inference-time refinement loop, with no RL and no production traffic.**
Every prior system that optimizes for engagement/CTR needs either live A/B
traffic (arXiv:2507.20227, arXiv:2312.12457) or RL training (RELATE). Every
system that refines without traffic (Self-Refine, Reflexion, SCRABLE) uses
self-generated or LLM-judge feedback. Substituting a model **trained on observed
engagement data** for the judge, at inference time, in an open-weight stack,
appears unclaimed. Frame it as an *architectural contribution under resource
constraints* — not a scientific breakthrough.

**2 (moderate). The source→brief→multi-platform-bundle chain with an explicit,
weighted semantic-fidelity term tying output back to source.**
MarketingFM uses RAG over product data, not summarization of a crawled site; the
TWEB study has no ingestion stage. The novelty is the *scored fidelity
constraint*, not the pipeline shape. Expect "this is RAG with extra steps."

**3 (weak). Confidence-gated LLM arbitration at τ=0.67 for marketing tone.**
Snorkel-shaped, so not novel as a method. The application to marketing tone and
the specific arbitration trigger have no direct precedent, but a reviewer who
knows Snorkel will see a hand-rolled label model *without* the generative
denoising — a simplification, not an advance. Do not oversell.

**4 (none). The model comparisons.** Standard model selection. Present as
engineering diligence.

**5 (liability, not contribution). The 0.30/0.25/0.45 weights.** Remove any
claim attached to these until a sensitivity sweep exists.

**Bottom line**: every individual component has prior art. The *composition* does
not appear to — but composition-novelty is the weakest kind, and it only holds up
if supported by ablations: does the corrective rule beat random resampling? does
the engagement term beat a constant? what happens at other weightings?

---

## 6. How accuracy is actually calculated

Three different quantities in this project get called a "score." Only the first
is accuracy in the classification sense, and conflating them is the fastest way
to lose credibility.

### 6.1 Classifier accuracy — goal and tone

`goal_tone.py:calculate_metrics`, on a stratified 20% held-out split of the
**gated** 121-row training set (24 test rows):

- `accuracy_score` — plain fraction correct
- `f1_score(average="weighted")` — **the selection criterion**
- `f1_score(average="macro")` — reported, not used for selection
- full `classification_report` — per-class precision/recall/F1/support

Current results, from `models/goal_tone_training_metrics.json`:

| Target | Model | Accuracy | Weighted F1 | Macro F1 |
|---|---|---|---|---|
| `campaign_goal` | tfidf_logistic | 0.750 | 0.741 | **0.554** |
| `tone` | tfidf_logistic | **1.000** | 1.000 | 1.000 |

**Both numbers need heavy qualification.**

*Campaign goal.* The 0.554 macro F1 against 0.741 weighted F1 is the whole story:
weighted F1 is hiding class collapse. Per class —

| Class | F1 | Test support |
|---|---|---|
| awareness | 0.917 | 12 |
| conversion | 0.615 | 7 |
| lead_generation | 0.667 | 2 |
| retention | 0.571 | 2 |
| **engagement** | **0.000** | **1** |

`engagement` is never predicted correctly because it has exactly one test
example. Three of five classes have support ≤ 2, where a single prediction moves
F1 by 0.5 or more. **Report macro F1 and per-class support, not the headline
accuracy.**

*Tone.* 1.000 across the board on 24 test rows spanning three classes — 18
`persuasive`, 5 `professional`, 1 `luxury`. A perfect score on a 24-row test set
with that imbalance is not evidence of a good classifier; it is evidence that the
gated dataset is nearly linearly separable because **the confidence gate kept
only the rows the weak labeler found easy**. The gate and the test set are not
independent.

**The framing caveat that governs both.** The labels being scored against were
produced by the weak supervision ensemble. So this measures *agreement with the
weak labeller*, not correctness. **There is no human-annotated gold set in this
repository.** Every accuracy number in this project is conditional on the weak
labels being right, and that has never been checked.

Relevant criticism to engage with rather than ignore:
- Ma et al., *Issues with Entailment-based Zero-shot Text Classification*, ACL 2021 — [ACL 2021.acl-short.99](https://aclanthology.org/2021.acl-short.99/). Entailment ZSC leans on **spurious lexical patterns** rather than inference. Your keyword rule scorer and your NLI classifier may therefore fire on the *same* surface cues — inflating apparent inter-method agreement, which is precisely the quantity your confidence gate trusts.
- Desai & Durrett, *Calibration of Pre-trained Transformers*, EMNLP 2020 — [arXiv:2003.07892](https://arxiv.org/abs/2003.07892). NLI models are calibrated in-domain, **miscalibrated out-of-domain**. τ=0.67 is an out-of-domain decision boundary with no calibration set behind it.
- Gilardi et al., PNAS 2023 — [DOI](https://www.pnas.org/doi/10.1073/pnas.2305016120). Supports LLM-as-labeler — but validates against human gold labels, which you lack.
- **A further structural flaw to disclose**: Phi-3 arbitration is *triggered by* the NLI confidence, so the two labelers are correlated by construction. Agreement between them is not independent evidence.

### 6.2 Engagement regression quality — not accuracy

`engagement.py:train`, 20% held-out split of the 12,000-row corpus. MAE, RMSE,
and R²; **selection is by R²**. Target is
`engagement_rate = (likes + comments + shares) / impressions`.

Features: `char_length`, `word_count`, `hashtag_count`, `emoji_count`,
`cta_present`, `question_hook`, `sentiment_score` (VADER),
`readability_score` (Flesch), plus platform one-hots.

This is a regression fit, not an accuracy. Two known problems:
- The target is a raw ratio and almost certainly heavy-tailed. Kim & Hwang
  ([arXiv:2508.21650](https://arxiv.org/abs/2508.21650)) log-transform theirs, and
  warn that a suspiciously high R² usually indicates exposure-count leakage.
- The RecSys 2021 challenge ([arXiv:2109.08245](https://arxiv.org/abs/2109.08245),
  ~1B interactions) established that **engagement prediction from text alone is
  weak** — user, social and graph features dominate. That is the strongest
  published challenge to giving a text-only regressor the **largest** weight
  (0.45) in your composite.

### 6.3 Composite asset score — not measured against anything

```
final_score = 0.30·semantic + 0.25·platform_suitability + 0.45·engagement
```

There is **no ground truth**. It is a weighted sum of an embedding cosine, a rule
checklist pass rate, and a model prediction. It is a **ranking heuristic**.
Calling it accuracy would be wrong.

Three specific defects:

**⚠ `engagement_score` is min-max normalized within the batch.**
`engagement.py:score` computes `(pred - min) / (max - min + 1e-8)` over the
current asset set. With four assets, **the best always scores exactly 1.0 and the
worst exactly 0.0**, whatever the underlying predicted rates are. It measures
rank within the batch, not absolute engagement — and it carries the largest
weight. Scores are also not comparable across runs, because min and max are each
a single observation. The OECD/JRC handbook treats this as a first-order
methodological error.

**⚠ Optimizing against a model-predicted score is textbook reward hacking.**
Gao, Schulman & Hilton, *Scaling Laws for Reward Model Overoptimization*, ICML
2023 — [arXiv:2210.10760](https://arxiv.org/abs/2210.10760). Optimizing against a
proxy reward degrades ground-truth performance past a point; **for best-of-n the
relationship is quadratic**. Your loop is threshold-triggered best-of-n against a
proxy regressor — exactly the studied regime. A rising `final_score` after
re-prompting is *weak* evidence of improved real engagement. Manheim & Garrabrant
([arXiv:1803.04585](https://arxiv.org/abs/1803.04585)) classify your case as
**Regressional** (selection selects regressor error) and **Extremal**
(re-prompting pushes into the tail where the regressor was never trained).

**⚠ The paired t-test runs on n=4.**
`significance.py` calls `ttest_rel` on one pair per platform. At n=4, normality of
the paired differences is untestable and power is near zero.
- de Winter, 2013 — [PARE PDF](https://files.eric.ed.gov/fulltext/EJ1015748.pdf). The most useful citation for defending small n *honestly*: no principled objection at N=2–5 and Type I error stays near nominal, **but** 80% power needs a very large effect, and paired designs at N≈3 need within-pair correlation r > 0.8. Report the within-pair correlation, the effect size, and the achieved power.
- Button et al., *Nature Reviews Neuroscience* 2013 — [DOI](https://www.nature.com/articles/nrn3475). Low power inflates effect sizes (winner's curse); a significant p at n=4 is more likely an overestimate than a discovery.
- Dror et al., ACL 2018 — [ACL P18-1128](https://aclanthology.org/P18-1128/). Points toward a **nonparametric paired test** (Wilcoxon signed-rank, or paired bootstrap) at this size.

**This is the cheapest serious fix available**: run flow C over many products
and pair at the *product* level. That turns n=4 into n=hundreds.

### 6.4 The human baseline is not a fair comparison

`human_baseline.py` sets `cta`, `image_prompt` and `shorts_prompt` to `""` for
every human row, then scores them with `platform_suitability`, which awards
points for a non-empty CTA and a sufficiently long creative prompt. **Human
captions are structurally penalised on criteria they were never given the chance
to satisfy.** They are also scored by the same composite the AI branch is
optimized against.

Report this as "how human captions score under our metric," never as "AI beats
humans."

---

## 7. The two-hour runtime — diagnosed and fixed

Four compounding causes, all in the model-loading layer. Machine: MacBook Air
M2, 8 cores, 16 GB unified memory.

| # | Cause | Effect |
|---|---|---|
| 1 | `models.py` computed `DEVICE = "mps"` but `_load_phi3` only checked `torch.cuda.is_available()`. **The MPS GPU was never used.** | All generation on CPU |
| 2 | Same check picked `float32` off-CUDA. **Phi-3-mini in fp32 needs ~15.2 GB of weights on a 16 GB machine.** | Continuous swapping — the dominant cost |
| 3 | `config.py` pinned `OMP_NUM_THREADS=1` globally to dodge a macOS OpenMP segfault. | Every torch and BLAS op on **1 of 8 cores** |
| 4 | 8 sequential 500-token generations (4 generate + 4 optimize), each running the full token budget past the JSON it was asked for. | Wasted tokens ×8 |

### ⚠ Do not batch the platform prompts

An earlier version of this fix batched the four platform prompts into one
`generate` call, on the reasoning that they are independent and batching
amortises the fixed per-step cost. **This is wrong on memory-constrained
hardware and it is wrong badly.** Measured on a 16 GB M2, fp16 on MPS,
~390-token prompts:

| Configuration | Throughput |
|---|---|
| batch = 1 | **5.5 tok/s** |
| batch = 4 | did not finish 40 tokens in 9 minutes, **16.3 GB of swap in use** |

Phi-3-mini in fp16 is ~7.6 GB of weights. Four concurrent sequences add four KV
caches and four sets of activations on top, which pushes a 16 GB unified-memory
machine into swap; once it swaps, every decode step pays disk latency and the
per-step saving is worth nothing. The failure mode is a **~50× slowdown, not an
OOM error**, so it does not announce itself.

Generation is therefore deliberately sequential. The reasoning is recorded in
the `generate_batch_with_phi3` docstring so it is not "optimized" back later.

### What changed

- **`models.py`** — Phi-3, BART and MiniLM now load on the selected accelerator
  in a dtype that fits. fp16 on MPS/CUDA halves the footprint to ~7.6 GB, which
  is the difference between fitting in unified memory and swapping.
  `device_map="auto"` is used **only** on CUDA — elsewhere it silently parks the
  model on CPU regardless of `DEVICE`. `low_cpu_mem_usage=True` avoids a second
  full copy during load. Overrides: `PIPELINE_DEVICE`, `PIPELINE_DTYPE`.
- **`config.py`** — the OpenMP guard is now `KMP_DUPLICATE_LIB_OK` plus the
  `n_jobs=1` that every XGBoost estimator already carried. Those are the actual
  crash guards; pinning one thread was collateral damage. Threads now default to
  `cpu_count() - 1`, overridable via `PIPELINE_NUM_THREADS`.
- **JSON stop criterion** — generation halts as soon as the first top-level
  `{...}` closes, incrementally decoding only new tokens so the check stays
  linear. Every caller wants one JSON object and discards the rest.
- **`human_baseline.py`** now raises a typed `MissingHumanDataset` with
  instructions when `human_content_dataset.csv` is absent, and `main.py` reports
  and skips rather than aborting. Previously a missing optional file threw an
  unhandled `FileNotFoundError` at the *last* stage, discarding a run that had
  just spent an hour in generation.
- Removed dead code (`_phi_generator`) and leftover `print("A"/"B"/…)` debug
  statements in `get_semantic_model`.

**Measured end-to-end on a 16 GB M2** (`device=mps dtype=float16 threads=7`),
full `generate` stage, four platforms:

```
[models] 214 new tokens in 79.1s (2.7 tok/s)   ← first call, includes MPS warmup
[models] 301 new tokens in 41.6s (7.2 tok/s)
[models] 249 new tokens in 37.0s (6.7 tok/s)
[models] 164 new tokens in 24.7s (6.6 tok/s)
GENERATE_STAGE_TOTAL = 182.7s
```

**~3 minutes for the generate stage**, and `optimize` does the same work again,
so the Phi-3 portion of a per-product run is roughly **6 minutes** — against
52 minutes for the batched `optimize` stage alone before this fix. 45/45 tests
pass.

### What is still slow, and is not a bug

The weak-labeling stages (`label-goal`, `label-tone`) run BART-MNLI over 689 rows
and Phi-3 over the low-confidence subset. That is inherently expensive. It is
already checkpointed every 20 rows across four stages, so an interrupted run
resumes. **It also only ever needs to run once** — it is flow A. If the 2-hour
figure was measured on a full `python main.py`, most of it was flow A, and the
fix is to not re-run it: `python main.py --step crawl kb goal-tone-predict
summary generate engagement-score evaluate optimize significance`.

---

## 8. What to fix next, in priority order

1. **Re-run `goal-tone-train` with both arms.** The headline "model comparison"
   currently has one candidate. `python main.py --step goal-tone-train --force`
   with `GOAL_TONE_SKIP_XGBOOST` unset.
2. **Replace n=4 with n=products.** Run flow C over many products; pair at the
   product level; use Wilcoxon signed-rank or a paired bootstrap. Biggest
   credibility gain for the least work.
3. **Add the random-resampling ablation.** Without it, §5 sub-question 3 is
   unanswered and the optimization claim is unsupported (Stechly et al.).
4. **Fix `engagement_score` normalization.** Min-max within a 4-row batch makes
   the largest-weighted term a rank, not a measurement. Normalize against the
   training corpus distribution instead.
5. **Hand-label ~100 rows for a gold set.** Every accuracy number in the project
   is currently conditional on the weak labels being correct, unverified. 100
   rows converts the whole evaluation from "agreement with ourselves" to
   "agreement with ground truth."
6. **Run a weight sensitivity sweep** over 0.30/0.25/0.45, per the OECD/JRC
   handbook, or drop any claim that depends on the specific values.
7. **Fix the human baseline** — give human rows their real CTAs, or score them
   only on criteria they could satisfy.
8. **Delete `outputs/models/` and `data/raw/bank_marketing/`** (41 MB of
   unrelated artifacts) so the repository reads as one project.
