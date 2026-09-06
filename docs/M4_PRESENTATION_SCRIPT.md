# Module 4 — Presentation Script

**215001G · Aadhil M. H. M. · AI Content Refinery and Multi-Platform Distribution**

Eleven slides, ~9 minutes. Each page below has two blocks:

- **ON THE SLIDE** — copy this onto the slide verbatim. Fragments only. Never a sentence you intend to read aloud.
- **SCRIPT** — what you say. Written to be spoken, not read.

Plus **IF ASKED** — the follow-up the panel is most likely to raise on that slide.

---

> ### ⚠ Read this first — `M4_MEMBER_CONTRIBUTION_GUIDE.md` is out of date
>
> That guide predates the corrections in the final report. **Five of its numbers
> will be wrong if you quote them.** Use the values in this file.
>
> | The old guide says | The delivered system and final report say |
> |---|---|
> | "Engagement R² is around 0.99 … likely optimistic" | R² 0.99 was **leakage** (defect D4). Corrected: **−0.1676** [−0.4081, −0.0715] |
> | Weights `0.30 semantic / 0.20 format / 0.15 historical / 0.35 engagement` | **`0.40 semantic / 0.40 platform fit / 0.20 engagement`** — see `config.py:101-103` |
> | "Only 113 usable platform rows" | Defect D5 fixed: **527-row corpus**; 453 goal-labelled, 174 tone-labelled |
> | "Tone ~91%, goal ~65–70% accuracy" | **Tone 0.8182 acc / 0.7315 macro-F1. Goal 0.7719 acc / 0.4998 macro-F1** |
> | "weighted-F1 selection" | **Macro-F1, plus exact McNemar** — weighted F1 hid the rare classes |
> | *(capability detection absent)* | E10 and E11 are now part of Module 4 |

---

## Slide 1 — What Module 4 is `0:00`

**ON THE SLIDE**

> ### AI Content Refinery & Multi-Platform Distribution
> Reads the **client's own website** → platform-specific marketing assets
>
> - Crawl → knowledge base → goal & tone → generate → score → select
> - Instagram · TikTok · LinkedIn · Email
> - **Also: detects what the website can actually do**

**SCRIPT**

> "My module is the content refinery. It takes the client's own website as
> input — not a prompt someone typed — crawls it, builds a knowledge base of
> the business and its brand vocabulary, infers what the campaign is trying to
> achieve and in what tone, generates several candidate assets per platform,
> scores them, and returns the best one.
>
> Two things make it a research module rather than a wrapper around a language
> model. First, it doesn't return the first thing the generator produces — it
> generates candidates and *selects*, and I'll show you the evidence behind
> the scoring weights. Second, it reads the site to work out what that business
> can actually *do* — sell, take subscriptions, capture leads, accept donations
> — so the rest of the system can't recommend an action the client cannot
> perform. That last part is the piece I'd defend first, and it's slide nine."

**IF ASKED — "Which generator?"**
Phi-3-mini-4k-instruct, running locally. Chosen because it's reproducible and
instruction-tuned. It is not fine-tuned on our corpus, and deliberately so — I'll
come to why on slide eight.

---

## Slide 2 — The research question, and the gap `0:50`

**ON THE SLIDE**

> **RQ** — Can AI repurpose content into platform-specific assets while
> preserving quality, predicting engagement, and **without recommending what
> the site cannot do?**
>
> | Existing work | Gap |
> |---|---|
> | Caption / text generation | Rarely evaluates platform suitability, semantic consistency or engagement — and **never checks capability** |

**SCRIPT**

> "The research question at interim was: can AI repurpose content into
> platform-specific assets while preserving quality and predicting engagement?
>
> That question is still the spine of the module, but I added a clause to it
> during the project. Existing AI copy tools optimise for fluency. They'll
> happily write you a caption that says 'shop now, checkout today' for a
> newspaper that has no checkout. That isn't a weak recommendation — it's a
> category error, and no amount of better generation fixes it, because the
> problem isn't the wording.
>
> So the gap I'm addressing is two-part. Content tools rarely evaluate platform
> suitability, semantic consistency or engagement in any measured way — and
> none of them check whether the action they're recommending is one the client
> can actually perform."

---

## Slide 3 — The pipeline `1:40`

**ON THE SLIDE**

*(Figure: `report/assets/fig08_module4.png`)*

> **1** Crawl → **2** Knowledge base → **3** Goal & tone → **4** BART brief →
> **5** Phi-3 generation → **6** Score & select
>
> Also emitted: **site capabilities** → Module 3's action catalogue

**SCRIPT**

> "Six stages. The crawler pulls page copy, headings and product descriptions.
> The knowledge base condenses them into a business summary and a brand
> vocabulary, which is what grounds every generated asset in the client's
> actual language rather than a generic voice.
>
> Stage three classifies campaign goal and tone. Stage four uses BART to
> compress the context into a generation brief. Stage five is Phi-3 producing
> the platform-native asset — caption, hashtags, call to action, image prompt,
> short-video brief. Stage six scores candidates and picks one.
>
> The branch at the bottom is the one that leaves my module: the capabilities
> I detect from the same crawl become the action catalogue Module 3 is allowed
> to choose from.
>
> One implementation detail worth a sentence, because it cost me a day: the
> crawler was silently corrupting text. The HTTP library defaults to
> ISO-8859-1 for `text/html` when the response header omits a charset, so every
> em-dash and accented character in a client's copy turned to mojibake before
> the generator ever saw it. Fixed, and it's the kind of fault that never raises
> an error — it just makes your output slightly wrong forever."

---

## Slide 4 — Goal & tone: a controlled comparison `2:40`

**ON THE SLIDE**

> **Two representations, same corpus, same split**
>
> - TF-IDF + logistic regression *(sparse, lexical)*
> - Sentence-BERT + XGBoost *(dense, semantic)*
>
> Corpus: **527 rows** — 453 goal-labelled (5 classes), 174 tone-labelled (6 classes)
>
> **Defect D5:** filter required *both* labels → corpus was **114 rows.** Fixed → **527**

**SCRIPT**

> "Goal and tone are the strategy layer — they decide what the generator is
> asked for. I built this as a controlled comparison rather than picking a
> model: sparse lexical features with logistic regression against dense
> Sentence-BERT embeddings with XGBoost, on the same corpus and the same split.
>
> Before I could run it I had to fix a defect in my own code. My corpus filter
> required a row to clear the confidence threshold for *both* goal and tone
> before keeping it — but the two classifiers train completely independently.
> A row with a confident goal label and an uncertain tone label is perfectly
> usable training data for the goal classifier. That filter had quartered my
> corpus, from 527 rows to 114. Per-target filtering restored it.
>
> That's defect five of the seven in Chapter 6.7, and it has the same signature
> as the others — nothing failed, no error, I just had far less data than I
> thought and every reported number was computed on a quarter of the corpus."

---

## Slide 5 ★ — Result: the simpler model wins, and macro-F1 is why we know `3:40`

**ON THE SLIDE**

*(Figure: `research/figures/fig_e6_goal_tone.png`)*

> | Target | Model | Acc | **Macro-F1** |
> |---|---|---:|---:|
> | goal | baseline | 0.5877 | 0.1481 |
> | goal | **TF-IDF** | 0.7719 | **0.4998** |
> | goal | SBERT | 0.7719 | 0.4042 |
> | tone | **TF-IDF** | 0.8182 | **0.7315** |
> | tone | SBERT | 0.7727 | 0.5912 |
>
> **Exact McNemar** — goal `8 vs 8, p = 1.000` · tone `5 vs 3, p = 0.727`

**SCRIPT**

> "Look at the goal rows. Accuracy is **identical** — 0.7719 for both models.
> If I'd reported accuracy, I'd have had nothing to say. Macro-F1 separates
> them: 0.50 against 0.40. The difference is entirely in the rare classes,
> which accuracy hides because the majority class is 59% of the corpus. A model
> can look respectable by predicting the majority class and never getting a
> minority class right at all — that's what the baseline row is doing at
> macro-F1 0.15.
>
> Then the test. I have about a hundred test rows and two classifiers evaluated
> on the *same* rows. Comparing two accuracy figures treats them as independent
> samples, which they aren't. The correct test is exact McNemar, because only
> the cases where the two models *disagree* carry any information — where both
> are right or both are wrong, you learn nothing.
>
> For goal, each model is right where the other is wrong exactly eight times.
> The disagreements cancel completely. p equals 1.000. For tone, five against
> three, p equals 0.73.
>
> So the two approaches are **statistically indistinguishable** on this corpus.
> And that means choosing TF-IDF is a decision about cost, speed and
> interpretability — not about accuracy. I want to be clear that this is a
> *stronger* claim than saying the simple model is better. Saying 'TF-IDF wins'
> on a difference this size, with this corpus, would be a claim my data cannot
> carry."

**IF ASKED — "Isn't macro-F1 0.50 quite poor for goal?"**
Yes, and I say so. Goal is the weaker of the two classifiers and the bottleneck
is corpus size, not method — five classes, 339 training rows, and the labels are
weak supervision rather than ground truth. That's why the goal classifier is used
to **order** the action candidates and never to filter them. Filtering a site's
genuine capabilities on a model near 0.50 would be a correctness claim it can't
support.

---

## Slide 6 ★ — The engagement model: R² 0.99 was a leak `4:50`

**ON THE SLIDE**

*(Figure: `research/figures/fig_e7_engagement.png`)*

> | Feature set | Feats | R² | Spearman |
> |---|---:|---:|---:|
> | with outcome columns *(original)* | 17 | **0.9901** | 0.9977 |
> | text features only *(corrected)* | 13 | **−0.1676** | 0.0120 |
> | predict the mean | 0 | −0.0 | 0.0 |
>
> Target = `(likes + comments + shares) / impressions`
> Features included… **likes, comments, shares, impressions**
>
> **Invisible in training. Fatal in use.**

**SCRIPT**

> "This is the finding I'm least proud of and most glad we published.
>
> My engagement regressor reported an R² of 0.99. That number survived review
> because a 0.99 doesn't look like a bug — it looks like success. It was
> leakage. The target is engagement rate, computed as likes plus comments plus
> shares over impressions. Those four columns were still sitting in the feature
> set. The model was reading its own answer.
>
> Now the part that matters. **Why was it invisible in training and fatal in
> use?** In training, every row has a like count, so the model learns to divide.
> At prediction time I'm scoring a caption that has *not been posted*. It has no
> likes, no comments, no impressions. Those columns get filled with zeros —
> values the model has never seen in its life — and the output is noise. And
> that noise was carrying **45% of the weight** in every content ranking
> decision the system made.
>
> With the leak removed and only text-derived features left, R² is minus 0.17,
> with a confidence interval of minus 0.41 to minus 0.07 — *worse than
> predicting the training mean*. Spearman rank correlation is 0.012, interval
> spanning zero. There is no demonstrated ranking skill on held-out data."

---

## Slide 7 ★ — And the dataset has no text signal at all `6:00`

**ON THE SLIDE**

> **All 8 text features vs engagement, Holm–Bonferroni corrected**
>
> `emoji_count · hashtag_count · sentiment · word_count · cta_present · char_length · question_hook · readability`
>
> **0 of 8 survive.** Smallest p = 0.199
>
> → Weight cut **0.45 → 0.20.** Not deleted. **Not tuned harder.**

**SCRIPT**

> "The obvious next move after a bad R² is to go and find a better model. I
> tested whether that was even worth doing.
>
> I took all eight text features — emoji count, hashtag count, sentiment, word
> count, whether there's a call to action, length, question hook, readability —
> and correlated each individually against engagement, with Holm–Bonferroni
> correction, because testing eight features without correction will manufacture
> a significant one by chance roughly one time in three.
>
> **Zero of eight survive.** The smallest p-value of any of them is 0.199 —
> that's not marginal, it's nowhere near.
>
> So this is a property of the **dataset**, not a failure of my model. No model
> extracts a signal that is not present in the data, and continuing to tune
> would have been me fitting noise until the number looked better.
>
> The correct response was to change what the score is *worth*. Its weight in
> content ranking went from 0.45 to 0.20. I deliberately did not remove it —
> the pathway stays wired for a dataset that does have signal — but it no longer
> decides a ranking on the strength of a model with no demonstrated skill. And
> the model's own verdict is shown in the interface, rather than the result
> being quietly deleted."

**IF ASKED — "So why keep it at 0.20 at all?"**
Two reasons. It breaks ties between candidates that are equal on the components
that *are* measured, and keeping the pathway live means that when we collect
post-level text paired with post-level engagement from the platform's own
campaigns — which the tracking layer already supports — the model can be
retrained and its weight restored **if it earns it.** Removing the component
would mean rebuilding it later; weighting it honestly costs nothing.

---

## Slide 8 — Scoring and selection, with honest weights `7:00`

**ON THE SLIDE**

> ```
> score = 0.40 · semantic similarity   (MiniLM + cosine)
>       + 0.40 · platform fit          (deterministic rule check)
>       + 0.20 · predicted engagement  (weight set by E7)
> ```
> Was `0.30 / 0.25 / 0.45`
>
> - Best-of-N, not first-output
> - Generator stays **frozen** — learning lives in strategy + ranking

**SCRIPT**

> "Three components. Semantic similarity, using MiniLM embeddings and cosine,
> checks the generated asset still says what the source material says.
> Platform fit is a deterministic rule check — word range, hashtag policy,
> whether the call to action is present, whether the visual brief is the right
> type for that platform. And predicted engagement.
>
> The weights were 0.30, 0.25 and 0.45, leaning hardest on engagement. They are
> now 0.40, 0.40 and 0.20. **That change is not a design preference — it's the
> direct output of the previous slide.** The two components I lean on are the
> two that are actually measurable: platform fit is deterministic, so it cannot
> be wrong about itself, and semantic similarity keeps the copy on message.
>
> I should be honest about what these weights are. They are **declared design
> weights** — a multi-criteria decision rule. They are not learned causal
> weights, and I don't claim they're optimal. What I do claim is that the one
> weight I changed, I changed for a measured reason.
>
> Last point: the generator is deliberately **not fine-tuned** on our corpus.
> With 527 weakly labelled rows, fine-tuning a 3.8-billion parameter model would
> teach it our labelling rule, not marketing. So Phi-3 stays frozen and all the
> learning happens in the strategy layer and the ranking layer, where I can
> actually measure it."

---

## Slide 9 ★ — The action set is a property of the website `8:00`

**ON THE SLIDE**

*(Figure: `research/figures/fig_e10_capability_detection.png`)*

> | Capability | Evidence | Unlocks |
> |---|---|---|
> | commerce | cart / checkout paths, "add to cart" | basket recovery, discount, promotion |
> | subscription | pricing, plans, "free trial" | trial nudge, upgrade prompt |
> | lead_capture | contact / demo forms, `input[type=email]` | nurture, demo invite |
> | donation | donate paths, "give now" | appeal, impact update |
> | **content** | *always true* | digest, article rec — **the floor** |
>
> **E10:** 15 real sites · agreement 1.0 · **development set, fitted**

**SCRIPT**

> "Every result the team reported before this assumed a fixed vocabulary of four
> actions for every client. That assumption does not survive a second client. A
> news site has no checkout. A charity has no upgrade path. A subscription
> product has no basket to abandon.
>
> So the action set isn't a constant — it's the intersection of what the *site*
> can do and what the *customer* qualifies for. I detect the site half from the
> same crawl, using two independent channels: visible text — call-to-action
> phrases and headings — and link structure, matched against **whole path
> segments**, not substrings. Plus one structural override: an email input field
> sets lead capture regardless of wording, because a form field is stronger
> evidence than a phrase.
>
> Now, why detect rather than train a classifier? There is no dataset of
> websites labelled with marketing actions. I'd have to synthesise the labels
> from a rule, and the model would learn my rule back. This project has already
> found two defects of exactly that shape — a Random Forest given its own target,
> and my own engagement model. A third would not be a contribution. So: what a
> site can do is **evidence on the page**, so it's detected. Which action is
> *best* is genuinely unknown, so that's left to the decision log.
>
> Fifteen real websites, hand-labelled, agreement of 1.0 across all four
> capabilities. **And I want to state plainly that this is a development set and
> that figure is fitted** — both the detector and two of my labels changed after
> I saw the results, so a fresh sample is needed before I'd call it accuracy.
>
> Which is fine, because the number isn't what I learned. Of four initial
> disagreements, two were detector faults — `/product` was firing on a
> magazine's `/categories/product-strategy`, and a retailer's `support.`
> subdomain was being read as a donation page, which is why URL matching is now
> whole-segment. **But the other two were faults in my labels.** A charity that
> sells merchandise has donation *and* commerce. A publisher running a store has
> commerce as well as content. I had marked both as having no commerce, and the
> detector was right.
>
> The lesson is that **capability is not a site type.** Modelling capabilities as
> independent flags, rather than as a category, is what let the detector be right
> where the human label was wrong."

**IF ASKED — "What if detection is wrong on a real client?"**
The two errors aren't symmetric, and the detector is tuned for that. A false
negative just gives the client a smaller action set. A false positive invents an
action they cannot perform and the system recommends it — much worse. And a site
where nothing is detected doesn't get an empty list; it falls back to the four
legacy actions, so nothing breaks.

---

## Slide 10 — What a larger action set costs `9:10`

**ON THE SLIDE**

*(Figure: `research/figures/fig_e11_action_set_size.png`)*

> **Decisions needed to reach RMSE 0.02**
>
> | Actions | Decisions |
> |---:|---:|
> | 2 | 5,000 |
> | 4 | 5,000 |
> | 8 | 20,000 |
> | 16 | **80,000** |
>
> `P(a|x) = ε/|A(x)| + (1−ε)·1[a = greedy(x)]` — **`|A(x)|` must be logged**

**SCRIPT**

> "Letting every site have its own action set isn't free, and this experiment
> prices it.
>
> Exploration is a fixed budget. The more actions on offer, the less evidence
> each one accumulates, and the longer before any comparison between policies
> means anything. Reaching a usable estimate takes five thousand logged
> decisions with two actions and **eighty thousand with sixteen.**
>
> There's also a mathematical consequence I have to hand to Module 3 correctly.
> A varying action set changes the propensity — exploration has to be uniform
> over the actions available to *that* customer at *that* moment. Which means
> the size of the candidate set has to be recorded **with** the decision,
> because an estimator run six months later cannot reconstruct which actions
> were on offer. Getting that denominator wrong isn't an error message, it's a
> silent bias.
>
> The design guidance this gives is concrete: keep the catalogue as small as
> honestly covers what a site can do. **Adding an action nobody will choose is
> not free — it takes evidence away from every other action.** A site offering
> twelve actions should not expect conclusions on the same timescale as one
> offering four, and the system should say so rather than present an early
> estimate as settled."

---

## Slide 11 — What I contributed, and what I won't claim `10:00`

**ON THE SLIDE**

> **Contributed**
> Crawler + knowledge base · goal/tone corpus and both classifiers · Phi-3
> generation · three-component scoring · **capability detection** ·
> defects D4, D5, D6 + the encoding and OpenMP faults
>
> **Will not claim**
> A new model · proven live engagement uplift · held-out capability accuracy ·
> that captions predict engagement
>
> **Would defend first:** *capability is not a site type*

**SCRIPT**

> "To close — what I'd defend, and what I won't claim.
>
> My contribution is an integration and inference-time decision contribution.
> I built the crawler and knowledge base, assembled the goal and tone corpus and
> both classifiers as a controlled comparison, built the platform-aware
> generation and the three-component scoring, and built capability detection.
> I found and fixed three of the seven defects — the engagement leak, the corpus
> filter, and a case where the shorts platform declared it wanted video but had
> no video options defined, so the selector was silently returning a static
> image. I also diagnosed the crawler's encoding fault and a macOS OpenMP
> conflict where XGBoost and PyTorch each load their own libomp and kill the
> process with no traceback.
>
> What I will not claim: I have not built a new model. I have no evidence of
> live engagement uplift, because nothing in this study was posted to a real
> platform. My capability accuracy is fitted on a development set. And I cannot
> predict engagement from caption text — not on this corpus, and I've shown that
> it's the corpus, not the model.
>
> What I'd defend first is the thing the capability experiment taught me:
> **capability is not a site type.** A charity that sells merchandise is both a
> charity and a shop. Modelling that as independent flags rather than as a
> category is what let my detector be right in the two cases where my own hand
> label was wrong — and that's a more useful result than the agreement figure
> above it."

---

## Timing

| Slides | Content | Cumulative |
|---|---|---|
| 1–3 | Framing and pipeline | 2:40 |
| 4–5 ★ | Goal & tone, McNemar | 4:50 |
| 6–7 ★ | The leak, and no signal | 7:00 |
| 8 | Scoring with honest weights | 8:00 |
| 9–10 ★ | Capability detection and its cost | 9:10 |
| 11 | Contribution and limits | 10:00 |

**If cut to 6 minutes:** drop slides 3 and 10, compress 4 into 5. Never drop
6, 7 or 9 — those are the three slides carrying original findings.

---

## Delivery notes

**The three sentences to land.** If the panel remembers nothing else:

1. *"R² 0.99 was leakage. Corrected it is minus 0.17, and zero of eight text features survive correction — so I changed the weight, not the model."*
2. *"The two classifiers are statistically indistinguishable, so choosing the simpler one is a decision about cost, not accuracy — which is a stronger claim than saying it's better."*
3. *"Capability is not a site type — and that's why my detector was right where my own label was wrong."*

**Do not say "unfortunately" about a negative result.** E7 is not a
disappointment; it is a measurement that changed the system. Deliver it as a
finding, in the same tone as any other.

**Don't read the tables.** Read one number off each and say what it means. The
panel can see the rest.

**Two known drifts, in case someone opens the code while you talk:**

- **Platform list.** `config.py:115` sets the product scope to `instagram, tiktok, linkedin, email`. Some documents say *Facebook* and *Shorts*. Read the config before you present and use what it says.
- **Engagement figures.** The comment block at `config.py:78-92` records R² −0.30 and Spearman 0.02 from a development run. The experiment of record, E7, gives **−0.1676** and **0.0120**. Quote E7 — those are the values in the report, in `results.json`, and in the figure.
