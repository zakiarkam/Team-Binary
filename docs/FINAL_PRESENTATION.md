# Final Presentation — content and changes from the interim deck

**Team Binary · AI-Powered Digital Marketing Orchestration · Level 04 Final**

Everything below is drawn from the final report
(`report/Final_Report_TeamBinary_AI_Powered_Digital_Marketing_Orchestration.docx`)
and verified against `research/results/results.json`, which currently reports
**11 of 11 experiments `ok`, 0 skipped, 0 failed** (seed 42, 10,000 bootstrap
resamples, 30 seeds).

---

## Part 0 — What changes from the interim deck

### The one structural change

The interim deck was organised as **"here is our plan, here is our progress."**
Eleven of its twenty-one slides were problem framing, architecture, or
progress/next-steps tables. A final presentation cannot be organised that way.
The final deck is organised as **"here is the question, here is the number,
here is what the number does and does not license us to say."**

Concretely: **every `CURRENT PROGRESS / NEXT STEPS` slide is deleted.** Slides
10, 13, 16 and 19 of the interim deck have no equivalent in the final. Their
slots are taken by results slides carrying measured values with confidence
intervals.

### Slide-by-slide disposition of the interim deck

| Interim slide | Disposition | Why |
|---|---|---|
| 1 Title | **Keep**, retitle | "Level 04 Interim Presentation" → "Final Presentation". Add the report subtitle: *An Integrated, Closed-Loop Framework for Cold-Start Digital Marketing* |
| 2 Team members | **Keep**, add module ownership | Panel needs to know who answers which question. 215001G→M4, 215015D→M3, 215110N→M1, 215129F→M2 |
| 3 Introduction | **Compress to half a slide**, merge into new slide 4 | The panel has heard the motivation twice. Buy back 90 seconds for results |
| 4 Core research problem | **Rewrite** | Interim listed 5 generic challenges. Final has 6 specific problems from §1.3, including the one discovered *during* the project: *the system records no basis for its own improvement* |
| 5 Research focus | **Delete** | Fully absorbed by the new experimental-strategy slide (11 experiments, one command) |
| 6 Aim + 4 objectives | **Replace** | The report now carries **11 objectives** (§1.4.2). Group them into 5 lines on the slide; do not read all eleven |
| 7 Core system modules | **Keep**, redraw | Replace the 4-box grid with the closed-loop figure (`report/assets/fig01_closed_loop.png`). The loop is the contribution; four boxes are not |
| 8 Module 1 RQ/methods/gap | **Keep**, extend | Metrics change: separation + silhouette + cold-start survival, not CTR/conversion rate |
| 9 Module 1 architecture | **Replace image** | Use `report/assets/fig05_module1.png` (report Fig 5.2) |
| 10 Module 1 progress | **Delete → replace with results** | New: the ablation, the negative result, the two defects |
| 11 Module 2 RQ/strategies/gap | **Keep**, extend | Add *operational complexity* as a first-class metric and *volume control* as the metric decision |
| 12 Module 2 architecture | **Replace image** | Use `report/assets/fig06_module2.png` |
| 13 Module 2 progress | **Delete → replace with results** | New: 30 paired seeds, sim-vs-live instability |
| 14 Module 3 RQ/methods/gap | **Rewrite** | Interim listed funnel + 3 attribution + conversion prediction. Final adds **uplift modelling** and **off-policy evaluation** — both post-interim, both the module's strongest contributions |
| 15 Module 3 architecture | **Replace image** | Use `report/assets/fig07_module3.png` |
| 16 Module 3 progress | **Delete → replace with 4 results slides** | Attribution, prediction+transfer, uplift, off-policy |
| 17 Module 4 RQ/methods/gap | **Rewrite** | Add **capability detection** — not in the interim deck at all |
| 18 Module 4 architecture | **Replace image** | Use `report/assets/fig08_module4.png` |
| 19 Module 4 progress | **Delete → replace with results** | Goal/tone McNemar, engagement leak, capability detection |
| 20 Thank you / Q&A | **Keep**, move to the end | |
| 21 References | **Keep**, trim | The interim's 12 references are largely superseded; the report has 65+. Show the 10 the presentation actually cites |

### Claims from the interim deck that must not be repeated

These were stated at interim and are now either **wrong, superseded, or
abandoned**. If any appears in the final deck the panel will ask about it.

| Interim claim | Status | What to say instead |
|---|---|---|
| Module 2: *"ROC-AUC 0.7985"* for the conversion model | **Dropped** | Module 2 is no longer evaluated on ROC-AUC. Its metric is conversions per 1,000 sends, volume-controlled, over 30 paired seeds |
| Module 3 next step: *"Validate attribution on Criteo"* | **Abandoned** | Criteo was never used. Attribution is validated against **known channel influence in the Module 3 simulator** (MAE against ground truth), and disagreement is reported on the live journeys where no ground truth exists |
| Module 3 progress: *"Bank Marketing check"* | **Abandoned** | Not among the six data sources in report Table 11 |
| Module 1 metrics: *"CTR, conversion rate"* | **Superseded** | Conversion **separation** (between-segment spread), silhouette, and cold-start segment survival |
| Module 1 next step: *"Train Random Forest Model"* | **Done, and it had a leak** | The RF confidence model was trained with the rule label among its inputs (defect D1). Report the corrected model |
| Module 4: *"Semantic similarity, engagement prediction, virality"* as three co-equal metrics | **Reweighted** | Virality is not reported as a validated metric. Engagement prediction's weight was cut 0.45 → 0.20 after E7 showed the corpus has no text signal |
| Backend: Node.js / NestJS; MongoDB + PostgreSQL | **Changed** | FastAPI + PostgreSQL only. Report §3.7 documents both deviations with reasoning — put it on a slide rather than waiting to be caught |
| *"Upload a CSV of customers"* | **Changed** | The 8,000 customers are imported through the same tracking path a live browser uses. Report §3.7 explains why: a cold-start study is not credible if the audience arrives pre-formed |

### Six things in the final deck that were not in the interim deck at all

1. **Uplift modelling (E8)** — targeting by predicted response is the wrong question.
2. **Off-policy evaluation with a propensity-logged decision record (E9)** — how the system becomes able to improve itself.
3. **Capability detection (E10)** — the action set is a property of the website.
4. **Action-set cost (E11)** — what a larger action catalogue costs in data.
5. **Seven defects found in the team's own research code** — the methodological contribution.
6. **The measured/reconstructed distinction in the study audience** — the integrity slide.

---

## Part 1 — The final deck, slide by slide

**Target: 26 core slides, ~25 minutes.** Timings are cumulative suggestions.
Slides marked ★ are the ones that decide the grade — do not rush them.

---

### 1 — Title `0:00`

> **AI-Powered Digital Marketing Orchestration**
> An Integrated, Closed-Loop Framework for Cold-Start Digital Marketing
>
> **Level 04 Final Presentation** · Group 01: Team Binary
> Information Technology & Management, Faculty of IT, University of Moratuwa, 2026
>
> Supervisors: Dr. A. L. A. Romesh R. Thanuja · Ms. M. A. N. Perera

---

### 2 — Team and module ownership `0:20`

| | | |
|---|---|---|
| Aadhil M. H. M. | 215001G | Module 4 — AI Content Refinery |
| Arqam Z. H. | 215015D | Module 3 — Analytics & Decision Support |
| Sarah M. M. F. | 215110N | Module 1 — Audience Targeting |
| Zanar M. H. M. R. A. | 215129F | Module 2 — Marketing Automation |

*Speaker note:* one line — "shared work was the integration layer, the
experimental apparatus and the report."

---

### 3 ★ — What we said at interim, and what happened `0:40`

Open with this. It is the single most effective slide in a final presentation
and no other team will have it.

| At interim we said | What we delivered |
|---|---|
| Four modules, integrated | Four modules behind one FastAPI service over one PostgreSQL database, with a Next.js dashboard and a live demo store |
| We would compare methods | **11 experiments**, every table and figure regenerated by one command |
| Node.js/NestJS + MongoDB | FastAPI + PostgreSQL — §3.7 explains why |
| Validate attribution on Criteo | Validated against **known ground truth in simulation**; disagreement reported on real journeys |
| *(not planned)* | **Uplift modelling** and **off-policy evaluation** — added because an interim question exposed that our recommender answered the wrong question |
| *(not planned)* | **Capability detection** — the action set is a property of the client's website |

> **And: we found seven defects in our own research code. Every one of them
> made a result look better than it was. None produced an error message.**

---

### 4 — The problem, restated `1:40`

Digital marketing is executed as disconnected actions, not as a learning
process. Six concrete failures (report §1.3):

1. **Segmentation collapses under low data** — clustering cannot express *"there is not enough evidence about this person."* It must place everyone somewhere.
2. **Automation policies are asserted, not compared** — rarely on the same users, rarely with cost reported beside outcome.
3. **Attribution is simplistic or unusable at launch** — and models are compared only with each other, because observational data has no ground truth.
4. **Analytics describes; it does not prescribe** — and when it does prescribe, it prescribes the wrong thing.
5. **Generated content is disconnected from performance and from capability** — it will recommend "drive to checkout" to a site with no checkout.
6. **The system records no basis for its own improvement** — a deterministic policy assigns probability zero to every action it does not take, so its own logs cannot evaluate an alternative.

*Speaker note:* "Point 6 is not in our interim report. We discovered it while
running the experiments, and it changed the system."

---

### 5 — Aim and objectives `2:40`

**Aim.** To design, implement and experimentally evaluate an integrated,
closed-loop AI marketing orchestration framework that unifies segmentation,
automation, attribution-aware predictive analytics and AI content refinement;
that remains effective under cold-start conditions; and **whose every reported
claim is reproducible from the system itself.**

**Eleven objectives, grouped:**

- **Build and ablate** — hybrid segmentation against each of its own components.
- **Compare, don't assert** — three automation policies over paired trials, cost beside outcome; four attribution models against ground truth where one exists.
- **State what transfers** — prediction quality against a baseline, and what moving to another audience preserves.
- **Choose honestly** — TF-IDF against Sentence-BERT with the correct test; whether the engagement corpus contains any signal at all.
- **Make it improvable** — establish that uplift and response targeting differ; log every decision with its propensity; validate the estimator against a known answer; make the action set a property of the site.
- **Integrate, and make overstating structurally difficult.**

*Speaker note:* the last clause of the aim is the thesis. Say it out loud.

---

### 6 ★ — The system: one loop, closing twice `3:40`

**Figure:** `report/assets/fig01_closed_loop.png` (report Figure 1) — full bleed.

```
   8,000-customer audience ──▶ ① Audience Targeting ──segments──▶ ② Campaign Automation
             ▲                        (rules + ML, cold-start)      (fixed/trigger/hybrid)
             │                                                              │
     platform priorities                                          tracked interactions
             │                                                              ▼
   ④ AI Content Refinery ◀────── analytics feedback ────── ③ Analytics & Decision Support
     (reads the client site)                                (funnel · attribution · uplift · OPE)
```

Three sentences, and only three:

- **The loop is genuine, not decorative.** Module 3's attribution credit changes which platform Module 4 writes for first; the highest-scoring asset becomes the opening message of the next plan.
- **It closes twice.** Once through analytics feedback, and once through the propensity-logged decision record, which makes the policy itself evaluable.
- **The system is an advisor, not a sender.** It produces an Action Plan — *"send this to these 15 High Intent contacts"* — that a company executes in its own tools.

---

### 7 — Technology, and three deviations from the interim report `4:40`

| Layer | Technology |
|---|---|
| Presentation | Next.js 16, React, TypeScript, Recharts — 7 dashboard pages |
| Tracking | `mos.js` first-party snippet on the site under study |
| Application | FastAPI, Uvicorn, Pydantic — routers, tenant isolation, decision logging, provenance |
| Research | scikit-learn, XGBoost, SHAP, sentence-transformers, Phi-3-mini, BART |
| Data | PostgreSQL 16 |
| Quality | pytest, Make, Git — one-command reproduction |

**Declared deviations (report §3.7) — put these on the slide, don't be caught by them:**

| Interim said | Delivered | Reason |
|---|---|---|
| Node.js / NestJS backend | FastAPI | Interim Fig 5.1 already showed FastAPI — the interim report was internally inconsistent. Every model is Python; a Node backend adds a serialisation boundary for no research benefit |
| MongoDB **and** PostgreSQL | PostgreSQL only | All five interim architecture figures show PostgreSQL. Two stores would split the integrity constraints the provenance guarantees depend on |
| Audience uploaded as CSV | Imported as customers of a live demo store | A cold-start study is not credible if the audience arrives pre-formed. One code path, one feature definition, one provenance rule for both imported and live |

---

### 8 ★ — The audience: what is measured, and what is reconstructed `5:40`

**Figure:** `report/assets/fig04_importer.png` (report Figure 9).

The study audience is the **Digital Marketing Campaign dataset — 8,000 real
customers.** It is real, but it was measured as **per-customer totals, not as
an event log.**

| Measured — taken straight from the dataset | Reconstructed by the importer |
|---|---|
| Sessions, page views, time on site | The timestamp of each visit |
| On-site clicks, purchases | Which page each visit landed on |
| Email opens and clicks | Scroll depth |
| Conversion outcome, acquisition channel | The order of email events, basket value |

> **Consequence, and we apply it throughout.** Segment membership, conversion
> by segment and funnel counts rest on real measurements. **Attribution paths
> and journey length are a property of the reconstruction as much as of the
> data**, and are reported that way every time.

Fidelity is asserted after every import — sessions, page views, time on site,
clicks and purchases match the source CSV exactly, and a re-import is
byte-identical. Every row carries `source = dataset | live`, **derived at write
time from the visitor**, never supplied by the caller. A test fails the build
if a dataset-derived customer ever produces a row claiming live observation.

*Speaker note:* this slide is why the panel should believe the rest of the deck.
Take your time on it.

---

### 9 — Experimental strategy: eleven experiments, one command `7:00`

| | Question | Data | Primary metric |
|---|---|---|---|
| E1 | Does the hybrid beat its own components? | 8,000 customers | Separation, silhouette |
| E2 | The two Module 1 defects, reproduced | 8,000 customers | Segment survival, certainty |
| E3 | Which automation policy wins, at what cost? | Simulator, 30 paired seeds + live build | Conversions / 1,000 sends |
| E4 | Do the attribution models agree? | Simulator + 7,811 live journeys | MAE vs ground truth; disagreement |
| E5 | Prediction quality, and its transfer | Module 3 features + imported audience | ROC-AUC vs stratified baseline |
| E6 | TF-IDF vs Sentence-BERT | 527-row goal/tone corpus | Macro-F1, exact McNemar |
| E7 | Engagement leakage and text signal | 12,000-post corpus | R², Spearman, Holm–Bonferroni |
| E8 | Uplift vs predicted-response targeting | Hillstrom, 64,000 randomised | Qini, incremental response |
| E9 | Does the decision log make the policy learnable? | Known-reward simulation | Estimator bias, RMSE, ESS |
| E10 | Can the system read what a website can do? | 15 real websites, hand-labelled | Agreement (Wilson) |
| E11 | What a per-website action set costs in data | Known-reward simulation | RMSE, decisions required |

> `make research` — **11/11 ok, 0 skipped, 0 failed.** Every figure is drawn
> from the tables the experiments just wrote, and Chapter 7 is rendered from
> `results.json`, so **no number in the report is typed by hand and no figure
> can disagree with the value it plots.**

**Statistics.** Percentile bootstrap (10,000 resamples) for separation,
silhouette, macro-F1, MAE and Qini; paired bootstrap and Wilcoxon signed-rank
for the 30-seed policy comparison; exact McNemar for two classifiers on one
test set; Cliff's δ for effect size; Wilson intervals near a proportion of 1.0;
Holm–Bonferroni across the eight engagement features.

---

## Module 1 — Audience Targeting and Personalization

### 10 — Question, methods, gap `8:20`

**RQ.** Does hybrid segmentation outperform static rules and pure ML clustering
under cold-start conditions?

**Compared as peers over one feature matrix:** rule-based segmenter · k-means ·
Ward-linkage hierarchical · hybrid agreement vote.

**Metrics:** conversion **separation** (not CTR), silhouette, three-way
disagreement, **cold-start segment survival.**

**Five shared segments:** High Intent · Loyal Customer · Price Sensitive ·
Low Engagement · New Cold User.

| Existing work | Gap |
|---|---|
| Rule-based, k-means, hierarchical clustering, each evaluated alone | Hybrid methods are rarely measured **against their own components**, and cold start is rarely treated as something a method must be able to *represent* |

*Architecture:* `report/assets/fig05_module1.png`

---

### 11 ★ — Result: the hybrid does not beat its own rules `9:20`

**Figure:** `research/figures/fig_e1_segmentation_ablation.png`

| Method | Segments | Separation | 95% CI | Cold-start segment |
|---|---|---:|---|---|
| rules only | 5 | 0.3837 | [0.309, 0.464] | yes |
| **hybrid (vote)** | 5 | **0.3838** | [0.307, 0.463] | yes |
| k-means only | 4 | 0.0693 | [0.049, 0.090] | no |
| hierarchical only | 4 | 0.0343 | [0.019, 0.059] | no |

> **This is a negative result and we report it as the headline.** On conversion
> separation the clustering contributes nothing — 0.3838 against 0.3837, well
> inside the interval.

Silhouette is **0.0869**; all three methods disagree for **35.3%** of
customers. The clusters overlap heavily, and quoting only the separation would
hide that.

**So why keep the hybrid?** On two grounds that are not separation: it produces
a **calibrated confidence** from the level of three-way agreement, and **the
vote is what makes cold start explicit.** That claim is defensible. "The hybrid
separates conversion better" is not, so we do not make it.

*Speaker note (Sarah):* "My first instinct was to look for a better metric. The
right response was to report the number and re-examine what the hybrid is for."

---

### 12 ★ — Two defects, reproduced and measured `10:40`

**Figure:** `research/figures/fig_e2_defects.png`

**D2 — a segment deleted by its own vote.** The agreement vote tested whether
the two clusterings agreed *before* it tested whether the rules had found a
cold-start customer. Clustering cannot represent "there is not enough evidence
about this person," so whenever the clusterings happened to agree, they
overruled the rules.

- 163 cold-start customers detected by the rules → **127 kept**.
- On the live audience the segment went to **zero**.
- Novel Contribution 1 was being erased from its own output.
- Those 163 convert at **53.4%** against **88.4%** for everyone else — the most distinctive behaviour in the dataset.

> **The principle:** a method that cannot represent a finding does not get a
> vote on it.

**D1 — target leakage in the confidence model.** The Random Forest was trained
with the rule label among its inputs while the target was the hybrid consensus.

| | With the leak | Corrected |
|---|---:|---:|
| Accuracy | 0.9213 | 0.9200 |
| Customers at confidence 1.00 | **450** | **3** |

Accuracy moved by **0.0013**. Certainty inflated **150×**. **Accuracy is not
what the leak corrupts** — the confidence attached to every downstream decision
is. That is exactly why it survived review with every test green.

---

## Module 2 — Marketing Automation and Campaign Management

### 13 — Question, design, gap `12:00`

**RQ.** Which automation strategy gives the best balance between engagement,
conversion efficiency and operational complexity?

**Designed as a controlled experiment, not three implementations.** The policy
engine is the *only* component that differs between arms; profile builder,
response model, templates, simulator and evaluator are shared, so any measured
difference is attributable to the policy alone.

**Two methodological decisions we defend:**

- **The metric is conversions per 1,000 sends**, not per-customer conversion rate. A per-user rate rises simply by sending more, which would hand the win to the fixed workflow for sending *most* rather than for sending *best*. Volumes differ sharply: 4.00 messages/customer for fixed against 1.32 for trigger. We report both, so the choice of metric is visible rather than decisive in the background.
- **30 independent seeds**, each putting the same 8,000 customers through all three policies — so the comparison is paired, and paired tests are the correct analysis.

**Operational complexity** = the count of distinct decision rules and branch
points a policy requires. Effectiveness alone is not a sufficient basis for an
engineering choice.

| Existing work | Gap |
|---|---|
| Fixed workflows and behavioural triggers, advocated separately | No controlled comparison on the same users, and cost almost never reported beside outcome |

*Architecture:* `report/assets/fig06_module2.png`

---

### 14 ★ — Result: outcome against cost, and a ranking that is not stable `13:00`

**Figure:** `research/figures/fig_e3_policy_comparison.png`

**Simulator, 30 paired seeds:**

| Policy | Conv. / 1,000 sends | 95% range | Messages/user | Decision rules |
|---|---:|---|---:|---:|
| fixed | 7.15 | [6.75, 7.49] | 4.00 | 1 |
| **trigger** | **10.45** | [9.62, 11.17] | 1.32 | 4 |
| hybrid | 7.99 | [7.45, 8.41] | 3.05 | 9 |

Paired: trigger − fixed = **+3.299** [3.146, 3.447], Wilcoxon p = 1.86e-09,
Cliff's δ = **1.0**, for **three extra rules.** That is the trade, argued
explicitly rather than assumed.

**The same three policies on the imported audience in the running system:**

| Policy | Sent | Clicks | Conversions | Conv. / 1,000 | Rules |
|---|---:|---:|---:|---:|---:|
| fixed | 500 | 144 | 36 | 72.0 | 1 |
| trigger | 400 | 111 | 44 | 110.0 | 4 |
| **hybrid** | 400 | 109 | 42 | **105.0** | 8 |

> **The simulation and the live build disagree about which policy wins.** Both
> metrics are volume-controlled, so the difference lies in how response is
> modelled — segment-level propensities against per-customer rates drawn from
> each customer's own recorded email history. Neither is an observation of real
> people reacting. **The ranking is not robust to that choice, and that
> instability is the result.** Quoting whichever run supported our preferred
> conclusion would have been the one genuinely dishonest option available to us.

---

## Module 3 — Marketing Analytics and Decision Support

### 15 — Question, methods, gap `14:20`

**RQ.** How can funnel analytics, multi-touch attribution and predictive
modelling generate actionable recommendations under data scarcity — and how can
those recommendations be *evaluated*?

**Methods:** funnel construction with drop-off by stage/segment/policy ·
first-touch, last-touch, linear and Markov attribution · conversion and
drop-off classifiers with bootstrap intervals and SHAP · **uplift modelling
(new)** · **off-policy evaluation over a propensity-logged decision record
(new)** · recommendation generator.

| Existing work | Gap |
|---|---|
| Funnel reports; attribution models compared only against each other | Analytics is descriptive and weak in attribution-aware prediction — **and prescribes by ranking predicted response, which is not the question a campaign asks** |

*Architecture:* `report/assets/fig07_module3.png`

---

### 16 ★ — Attribution: four models, four answers `15:00`

**Figure:** `research/figures/fig_e4_attribution.png`

**Against known channel influence in simulation** (where ground truth exists):

| Model | MAE | 95% CI |
|---|---:|---|
| first_touch | 0.0178 | [0.0112, 0.0268] |
| linear | 0.0178 | [0.0086, 0.0292] |
| last_touch | 0.0260 | [0.0094, 0.0448] |
| markov | 0.0525 | [0.0345, 0.0791] |

**On 7,811 real converting journeys** (where it does not):

```
first_touch   referral 21% · email 21% · ppc 20% · seo 19% · social 19%
last_touch    email 89%    · referral  3% · ppc  3% · seo  3% · social  3%
linear        email 56%    · referral 12% · ppc 11% · seo 11% · social 10%
markov        email 53%    · referral 12% · ppc 12% · seo 11% · social 11%
```

The widest pair disagrees over **68% of all attributed credit**; **35% on
average.**

> A company reading only its last-touch dashboard would conclude email is
> responsible for nearly everything, and would cut the acquisition spend that
> built the audience email later converted. **The disagreement is not a defect
> in one of the models — it is the finding.**

**20% of converting journeys have a single touchpoint.** On those every model
agrees by arithmetic, and that agreement must never be read as corroboration.

---

### 17 — Prediction, and what moving to another audience costs `16:00`

**Figure:** `research/figures/fig_e5_prediction.png`

| Target | Model | ROC-AUC | 95% CI |
|---|---|---:|---|
| conversion | stratified baseline | 0.4983 | [0.4772, 0.5221] |
| conversion | XGBoost | **0.9725** | [0.9654, 0.9793] |
| drop-off | stratified baseline | 0.4898 | [0.4687, 0.5107] |
| drop-off | XGBoost | **0.9900** | [0.9867, 0.9929] |

*A stratified dummy is published in the same table, because the base rate is
high enough that a model can look accurate by predicting the majority class.*

**Applied to the imported audience — a different distribution:** conversion
probabilities run 0.0103 → 0.9956, median **0.9126**, with **5,606 of 8,000**
above 0.5.

> The **ranking** transfers. The **absolute probabilities** do not, and any
> threshold set on the training distribution is arbitrary here. **The
> production recommender was changed to rank rather than threshold as a direct
> consequence**, and the system raises a calibration warning instead of
> reporting a confident number when the distribution is degenerate.

---

### 18 ★ — Who to target is not who will convert `17:00`

**Figure:** `research/figures/fig_e8_uplift.png`

The recommender ranked customers by **predicted conversion**. That is the
intuitive thing to do and it answers the wrong question. What matters is not
who will convert but **for whom the action *changes* whether they convert.** A
customer certain to buy anyway gains nothing from a discount.

**Our own audience cannot answer this.** Every imported customer received one
treatment, nobody recorded which, and no comparable customer received an
alternative. No model recovers a causal effect from data where the cause never
varied. So the experiment moves to **Hillstrom MineThatData — 64,000 customers
randomly assigned** to mens email / womens email / no email.

| Policy | Qini | 95% CI | Extra visits per 1,000 targeted |
|---|---:|---|---:|
| uplift (S-learner) | 93.62 | [56.11, 129.76] | **103.45** |
| predicted response *(what we were doing)* | 75.91 | [38.80, 109.98] | 91.26 |
| uplift (T-learner) | 70.36 | [30.19, 112.29] | 92.00 |
| random targeting | −9.75 | [−48.65, 26.95] | 57.76 |

The two rankings correlate at **Spearman 0.40**, and at a 30% budget the
policies share only **56%** of their chosen customers — about **44% of the list
differs.**

> **Stated carefully.** The Qini intervals overlap, and the *second* uplift
> learner does worse than the current policy — so **"use uplift modelling" is
> not a conclusion on its own.** What the data supports is the weaker and more
> useful claim: these are **different policies choosing different people, by a
> margin large enough to matter.**
>
> Hillstrom's actions are not our actions. This does not produce a policy
> deployable to our audience, and nothing in the report claims it does.

---

### 19 ★ — Making the recommendation learnable `18:20`

**Figure:** `research/figures/fig_e9_offpolicy.png`

E8 showed the recommender asks the wrong question **and that no borrowed
dataset can answer the right one for our actions.** So we changed what the
system records.

`analytics_output` is overwritten every run and holds only the current opinion.
A new **append-only `action_log`** records every decision, **the probability it
was taken under**, the features it was taken on, and what followed — plus
**10% of decisions made at random on purpose**, because a deterministic policy
assigns probability zero to every action it doesn't take, and you cannot learn
from a denominator of zero.

**Validated against a known answer** (simulated world, true policy value
computable, 40 replications per row):

| Logged decisions | SNIPS bias | 95% CI | RMSE |
|---:|---:|---|---:|
| 500 | −0.0160 | [−0.0399, 0.0089] | 0.0783 |
| 2,000 | −0.0029 | [−0.0149, 0.0092] | 0.0389 |
| **10,000** | **−0.0029** | **[−0.0080, 0.0019]** | **0.0166** |

It also detects that a candidate policy is worth **0.0361 more reward per
customer** than the one generating the logs — from logged data alone, without
deploying it to anybody.

> **The finding worth carrying into the viva.** Without exploration the
> estimate is biased by **+0.0391 — biased *upwards*.** It reports the
> candidate as better than it is. Worse, **the deterministic log looks *more*
> trustworthy**: effective sample size **1,094** against **107**, because every
> weight is 0 or 1 rather than spread out. **The standard diagnostic points the
> wrong way. Stability is not correctness.**

| Exploration rate | Bias | RMSE | Reward given up |
|---:|---:|---:|---:|
| 0% | 0.0391 | 0.0423 | 0.0% |
| 1% | 0.0105 | **0.1124** | 0.8% |
| 5% | 0.0142 | 0.0655 | 3.8% |
| **10%** | **−0.0015** | **0.0332** | 7.5% |
| 25% | −0.0110 | 0.0242 | 18.8% |

**Token exploration is worse than none** — at 1% the estimator has the worst
error of any setting tested. **Exploration is a commitment, not a gesture**,
and it costs about **7.5% of achievable reward** at a 10% rate.

---

## Module 4 — AI Content Refinery and Multi-Platform Distribution

### 20 — Question, methods, gap `19:40`

**RQ.** Can AI repurpose a client's own content into platform-specific
marketing assets while preserving quality, predicting engagement — **and
without recommending actions the client's website cannot perform?**

**Pipeline:** crawl the client site → knowledge base (business summary + brand
vocabulary) → BART summarisation → goal/tone classification → **Phi-3-mini**
platform-aware generation → three-component scoring → optimisation →
Instagram / LinkedIn / Facebook / Shorts / email assets.

**Scoring:** semantic similarity (MiniLM + cosine) · rule-based platform
suitability · predicted engagement — **weighted by what E7 shows each is
worth.**

**Plus capability detection** — reading the site to establish what it can
actually do: sell, take subscriptions, capture leads, accept donations.

| Existing work | Gap |
|---|---|
| Caption and text generation | AI content tools rarely evaluate platform suitability, semantic consistency or engagement prediction — **and none check whether the recommended action is one the site can perform** |

*Architecture:* `report/assets/fig08_module4.png`

---

### 21 ★ — Goal and tone: the simpler model wins, and macro-F1 is why we know `20:20`

**Figure:** `research/figures/fig_e6_goal_tone.png`

| Target | Model | Accuracy | Macro-F1 | Test rows |
|---|---|---:|---:|---:|
| campaign goal | majority baseline | 0.5877 | 0.1481 | 114 |
| campaign goal | **TF-IDF + logistic** | 0.7719 | **0.4998** | 114 |
| campaign goal | SBERT + XGBoost | 0.7719 | 0.4042 | 114 |
| tone | majority baseline | 0.3864 | 0.1115 | 44 |
| tone | **TF-IDF + logistic** | 0.8182 | **0.7315** | 44 |
| tone | SBERT + XGBoost | 0.7727 | 0.5912 | 44 |

**Accuracy is identical for goal (0.7719 both). Macro-F1 is not.** With an
imbalanced corpus, accuracy hides what happens to the rare classes.

**Exact McNemar** — with ~100 test rows and two classifiers on one test set,
only the disagreements carry information:

| Target | TF-IDF right / SBERT wrong | SBERT right / TF-IDF wrong | p |
|---|---:|---:|---:|
| campaign goal | 8 | 8 | **1.000** |
| tone | 5 | 3 | **0.727** |

> Statistically **indistinguishable**. So choosing TF-IDF is a decision about
> **cost, speed and interpretability — not accuracy.** That is a stronger and
> more defensible claim than asserting the simpler model is better.

*Also fixed here:* defect **D5** — the corpus filter required a row to clear the
confidence bar for *both* targets although the classifiers train independently.
**114 → 527 usable rows.**

---

### 22 ★ — Engagement: a leak, and a dataset with no signal `21:20`

**Figure:** `research/figures/fig_e7_engagement.png`

| Feature set | Features | R² | Spearman | MAE |
|---|---:|---:|---:|---:|
| with outcome columns *(original)* | 17 | **0.9901** | 0.9977 | 0.0185 |
| text features only *(corrected)* | 13 | **−0.1676** | 0.0120 | 0.3931 |
| baseline (predict the mean) | 0 | −0.0 | 0.0 | 0.3278 |

Corrected R² is −0.1676 [−0.4081, −0.0715]; Spearman 0.0120 [−0.0276, 0.0539]
— **an interval spanning zero, so no ranking skill on held-out data.**

**Why it was fatal in use, and invisible in training:** a caption that has not
been posted has no like count, so at prediction time those columns were filled
with zeros — far outside anything the model had seen — and **the score driving
45% of every content ranking became noise.**

Testing all 8 text features individually under **Holm–Bonferroni**, **0
survive.**

> This is a property of the **dataset**, not a modelling failure. No model
> extracts a signal that is not there. The correct response is to reduce the
> weight the score carries, not to keep tuning. **Weight cut 0.45 → 0.20**, and
> the model's own verdict is made visible in the interface rather than the
> result being deleted.

---

### 23 — The action set is a property of the website `22:20`

**Figures:** `research/figures/fig_e10_capability_detection.png`,
`research/figures/fig_e11_action_set_size.png`

Every result so far assumed a fixed vocabulary of four actions. **That
assumption does not survive contact with a second client.** A news site has no
checkout, so recommending a discount there is a *category error*, not a poor
recommendation. A charity has no upgrade path.

**E10 — detection against hand labels, 15 real websites.** Agreement 1.0 for
commerce, subscription, lead capture and donation, with Wilson intervals
[0.676, 1.0], [0.51, 1.0], [0.207, 1.0], [0.676, 1.0].

> **This is a development set and the figure is fitted, and we say so.** Of
> four initial disagreements, two were detector faults (URL matched as free
> text: `/product` fired on `/categories/product-strategy`) and **two were
> faults in our labels** — a charity with a shop and a publisher with a store
> had both been marked as having no commerce, and the detector was right.
> **Capability is not a site *type*.** Modelling capabilities as independent
> flags is what let the detector be right where the human label was wrong.

**E11 — what a larger action set costs.** Logged decisions needed to reach
RMSE 0.02:

| Actions on offer | Decisions needed |
|---:|---:|
| 2 | 5,000 |
| 4 | 5,000 |
| 8 | 20,000 |
| 16 | **80,000** |

> Adding an action nobody will choose is **not free** — it takes evidence away
> from every other action. A site offering twelve actions should not expect
> conclusions on the same timescale as one offering four, and the system should
> say so rather than present an early estimate as settled.

---

### 24 ★ — Seven defects, and what they have in common `23:20`

| | Defect | What it actually corrupted |
|---|---|---|
| D1 | Confidence model trained with the rule label among its inputs | Certainty inflated **150×** (450 → 3 at confidence 1.00); accuracy moved 0.0013 |
| D2 | Clustering comparison evaluated before the cold-start rule | Cold-start segment 163 → 127; **zero on the live audience** |
| D3 | Cluster names hardcoded to cluster indices | Correct for one dataset and one seed; arbitrary on any other audience |
| D4 | Engagement regressor kept the outcome components its target was derived from | R² 0.9901 → **−0.168**; weight in content scoring 0.45 → 0.20 |
| D5 | Goal/tone corpus filtered on both targets at once | Usable corpus **527 → 114 rows** |
| D6 | `shorts` declared a video visual type but defined no visual options | Selector silently returned a static image brief |
| D7 | Leakage guard iterated a Python `set` | Reported R² depended on the process hash seed — not exactly reproducible |

> **They share a signature: every one made a result better than it was, and
> none produced an error message.**

**That is why the integrity mechanisms are built in, not promised.** Provenance
derived at write time · the importer declares what it reconstructs · propensity
is a mandatory column · refusal thresholds suppress output the data can't
support · Chapter 7 generated from the results file · **one regression test per
defect.**

Two environment faults were also diagnosed: a macOS **OpenMP conflict** (XGBoost
and PyTorch each bundling `libomp`, killing training runs and API workers with
exit 139 and no traceback) and a **character-encoding fault** in the crawler
(ISO-8859-1 default for `text/html` with no charset, corrupting every non-ASCII
character in a client's copy).

---

### 25 — What the evidence supports, and what it does not `24:20`

Two columns. Say both.

| Supported | **Not** supported |
|---|---|
| The closed loop runs — one audience through all four modules, with feedback | That hybrid segmentation separates conversion better than rules alone |
| Cold start is handled explicitly, and had to be defended against the pipeline | That any one automation policy is best — sim and live disagree |
| Attribution model choice changes the conclusion, by 68% of credit | That engagement is predictable from caption text on this corpus |
| Simpler models won twice, and we can say *why we know* | That the prediction thresholds transfer to another audience |
| The recommender was answering the wrong question — the clearest direction the project produced | That uplift modelling is straightforwardly better — the intervals overlap |

**Threats to validity.** Reconstructed event ordering is the principal one —
attribution characterises the reconstruction as well as the data. Campaign
response is **modelled**, in both the simulator and the live build: **nobody in
this study opened a real email.** One dataset, one product category, one
language — and its 87.6% conversion rate is far above any plausible e-commerce
baseline, so conclusions about *absolute* rates should not leave it.
**Comparisons between methods on the same data are the results that travel.**

---

### 26 — Conclusion and future work `25:20`

**Delivered:** four research modules behind a FastAPI service over PostgreSQL,
a 7-page Next.js dashboard, a demonstration store with first-party tracking, an
8,000-customer audience imported through the live path, **11 experiments
reproducible with one command**, and a full automated test suite with one
regression test per defect.

**Four findings that stand on their own:**

1. **A hybrid method must be measured against its own components** — 0.3838 against 0.3837, and the finding only exists because the ablation was run.
2. **Accuracy is not what a leak corrupts** — 0.0013 of accuracy, 150× of certainty, every test green.
3. **Attribution models disagree enough to reverse a spending decision** — 68% of credit across 7,811 journeys.
4. **A recommender ranking by predicted response answers a different question, and a system that does not log propensities cannot discover that for itself** — so ours now does, and explores on purpose. **Stability is not correctness.**

**Future work.** Run the loop long enough to close it with real decisions — the
mechanism is built and validated; what remains is volume, not design. A
**held-out** capability sample. Live-audience re-fitting so thresholds and not
only orderings become usable. A content corpus with genuine engagement signal.
Growing the goal/tone corpora by active learning. A contextual-bandit layer
selecting the automation policy per segment online, using the exploration
budget we already spend. Consent management and retention policy for commercial
deployment.

> The framework is a research instrument that happens to run as a product. Its
> value lies less in any single model than in demonstrating that the four
> marketing functions can be operated as one loop, that the effect can be
> **measured rather than asserted**, and that a system can be built to make its
> own results **harder to overstate.**

---

### 27 — References (trim to what you cite)

Keep from the interim deck: Schein et al. (cold start), Shao & Li (multi-touch
attribution), Wedel & Kannan (marketing analytics), Davenport et al. (AI in
marketing). **Add the post-interim work the new experiments rest on:** Hillstrom
MineThatData, uplift/Qini evaluation, inverse-propensity and doubly-robust
off-policy evaluation, Holm–Bonferroni, Wilson intervals, Cliff's delta,
exact McNemar. Full list is Chapter 9 of the report.

---

### 28 — Thank you / Q&A

---

## Backup slides (do not present; have them ready)

| # | Content | Anticipates |
|---|---|---|
| B1 | Database schema — `report/assets/fig09_schema.png` | "Show us the data model" |
| B2 | Dashboard screenshots — `report/assets/placeholders/shot_dash_*.png` | "Is it actually built?" |
| B3 | The three-arm uplift assignment: Mens 13,601 (70.8%), Womens 5,054 (26.3%), **No E-Mail 545 (2.8%)** | "What does next-best-action actually output?" — the point being that the policy can say *contact nobody*, which the current rule cannot |
| B4 | Full E5 table: LR / RF / XGBoost × conversion / drop-off with PR-AUC and Brier | "Why XGBoost?" |
| B5 | Sparsity curve — `research/figures/fig_e3_sparsity.png` | "Does the trigger policy degrade as behaviour becomes unobservable?" |
| B6 | Statistical methods table (report Table 35) | "Why bootstrap and not a t-test?" |
| B7 | Individual contribution summary (Appendix A) | "What did each member do?" |

---

## Part 2 — Assets, and where they are

| Slide | Asset |
|---|---|
| 6 | `report/assets/fig01_closed_loop.png` |
| 7 | `report/assets/fig02_architecture.png` (optional inset) |
| 8 | `report/assets/fig04_importer.png` |
| 9 | `report/assets/fig03_research_pipeline.png` |
| 10 | `report/assets/fig05_module1.png` |
| 11 | `research/figures/fig_e1_segmentation_ablation.png` (+ `fig_e1_segment_profile.png`) |
| 12 | `research/figures/fig_e2_defects.png` |
| 13 | `report/assets/fig06_module2.png` |
| 14 | `research/figures/fig_e3_policy_comparison.png` |
| 15 | `report/assets/fig07_module3.png` |
| 16 | `research/figures/fig_e4_attribution.png` |
| 17 | `research/figures/fig_e5_prediction.png` |
| 18 | `research/figures/fig_e8_uplift.png` |
| 19 | `research/figures/fig_e9_offpolicy.png` |
| 20 | `report/assets/fig08_module4.png` |
| 21 | `research/figures/fig_e6_goal_tone.png` |
| 22 | `research/figures/fig_e7_engagement.png` |
| 23 | `research/figures/fig_e10_capability_detection.png`, `fig_e11_action_set_size.png` |
| B1 | `report/assets/fig09_schema.png` |

Every figure also exists as `.pdf` in `research/figures/` — use the PDF if the
slide tool rasterises badly.

---

## Part 3 — Fix these before you present

Three numbers currently disagree across the report, the README and the code.
Pick one value for each and use it everywhere; a panel that spots a
contradiction in a deck whose thesis is *measurement integrity* will press on it.

1. **Test count.** Report §3.6, §6.8 and §6.9 say **260 collected tests**.
   `README.md` says **177 Python tests**. The current tree collects **277 in
   `tests/`** plus **37 in `modules/m3_analytics/tests/`**. Run `make test` the
   morning of the presentation and quote what it prints.

2. **Experiment count in the README.** `README.md` line 133 says
   *"`make research` runs nine experiments."* There are **eleven**
   (`research/experiments/e1…e11`), and the report says eleven throughout. Fix
   the README.

3. **The README's architecture note is now stale.** `README.md` lines 124–127
   flag the Ch. 3.6 NestJS/MongoDB inconsistency as something "the report should
   correct." **The report already corrects it** — §3.7 documents both
   deviations in a table. Delete the note so the README does not accuse the
   report of an error it no longer contains.

Optional but worth it: the interim deck's Module 3 metrics list spells it
*"Coversion rate."* Do not carry that slide forward as-is.

---

## Part 4 — Questions the panel will ask, and the answer

**"Your hybrid doesn't beat your rules. Isn't Module 1 a failure?"**
No — it is a result, and it is only available because we ran the ablation.
Separation is 0.3838 against 0.3837, inside the interval. The hybrid keeps its
place on two grounds that are not separation: a calibrated confidence from
three-way agreement, and a vote that makes cold start explicit. Defect D2 showed
how easily that second contribution is destroyed by a pipeline that looks
correct. We report what the number supports and no more.

**"Why should we trust results built on a reconstructed event log?"**
We separate them. Segment membership, conversion by segment and funnel counts
rest on totals taken straight from the dataset and asserted against the source
CSV after every import. Attribution paths and journey length depend on ordering
we created, and are reported as a property of the reconstruction every time
they appear. Slide 8 is that distinction, and it is enforced in the data, not
only in the prose.

**"Isn't E8 borrowed data? What does it prove about your system?"**
It proves the framing, not the policy. Uplift is identifiable only where
assignment was randomised, and nothing in our audience was. Hillstrom's actions
are not our actions, and we say so in the report. What E8 establishes is that
ranking by predicted response and ranking by uplift choose materially different
people — 56% overlap at a 30% budget. E9 is the response: our system now logs
the propensity so the question can eventually be answered on *our* actions.

**"You simulate a lot. Why should we accept that?"**
Three claims in the report are properties of an *estimator*, not of customers:
that attribution recovers known influence, that an off-policy estimator is
unbiased, and how error scales with action-set size. Each is settled by
mathematics and can be checked exactly against a known answer, which no real
dataset permits. Where a claim concerns people rather than estimators, we use
real data.

**"Which automation policy do you recommend?"**
We do not recommend one, and that is deliberate. The simulator favours trigger;
the live build favours hybrid. Both metrics are volume-controlled, so the
difference is in how response is modelled, and neither is an observation of
real people. Reporting the instability is the honest result. What we *can*
recommend is the trade the numbers do support: trigger leads fixed by 3.3
conversions per thousand sends for three extra decision rules.

**"You found seven bugs in your own code. Why should we trust the rest?"**
Because of what the pattern taught us. Every defect inflated a result and none
raised an error, which is evidence that more may remain — we say that in §7.5.2.
The response was structural: each defect has a regression test, the leakage
guard raises rather than warns, provenance is derived at write time instead of
asserted, propensity is mandatory, and Chapter 7 is generated from the results
file so a figure cannot drift from its number. The alternative — finding no
bugs because we never looked — is not better.

**"What is genuinely novel here?"**
Four things. That a hybrid must be ablated against its own components, shown by
a negative result we report as the headline. That a leak can leave accuracy
intact while inflating certainty 150-fold. That attribution disagreement is
large enough to reverse a spending decision. And the one we would defend first:
that a marketing system which does not log the probability its own decisions
were taken under **cannot ever learn whether a different policy would have been
better** — and that without deliberate exploration, the estimate is biased
upwards while its standard diagnostic looks *better*, not worse.

---

## Part 5 — Presenting report Table 9 (capabilities → actions)

*For 215001G, Aadhil — Module 4. This is the table the panel is most likely to
stop on, because it is the one place where Module 4 changes what Module 3 is
allowed to do.*

### The one sentence

> "Table 9 is the contract between the website and the recommender. The left
> column is what we read off the client's own pages; the right column is the
> set of actions that reading unlocks. Nothing outside that set can be
> recommended to that client."

### Why the table exists at all — lead with the failure

Every result in Chapters 7.3.1 to 7.3.9 assumed a **fixed vocabulary of four
actions** for every client. That assumption breaks on the second client:

- A news site has no checkout — "send a discount offer" there is a **category error**, not a weak recommendation.
- A charity has no upgrade path.
- A subscription product has no basket to abandon.

So the action set is not a constant. **It is the intersection of two things:**
what the *site* can perform, and what the *customer* qualifies for. Table 9 is
the site half.

### How to read the three columns

| Column | What it really is |
|---|---|
| **Capability** | A boolean flag on the site, detected per crawl — not a category the site belongs to |
| **Evidence sought** | Two independent channels, OR-ed together — visible text and link structure |
| **Actions it makes available** | The `requires` field on each action in the catalogue. An action is offerable if the site has **any one** of its required capabilities |

**The evidence column is two channels, not one** — this is the detail that makes
the answer credible (`modules/m4_content/crawler.py:149`):

1. **Visible text** — call-to-action text and headings, matched against phrase
   signals: `add to cart`, `start free trial`, `book a demo`, `give now`.
2. **Link structure** — `href` targets and form actions, tokenised into **whole
   path segments and host labels**, matched against `cart`, `pricing`,
   `newsletter`, `donate`.
3. Plus one structural override: **an `<input type="email">` sets
   `lead_capture` regardless of wording**, because a form field is stronger
   evidence than a phrase.

### The four points worth defending

**1 — Why this is detected, not predicted.** There is no dataset of websites
labelled with marketing actions. To train a classifier we would have to
synthesise the labels from a rule, and the model would then learn that rule
back. **This project has already found two defects of exactly that shape** — a
Random Forest given its own target as a feature (D1) and an engagement
regressor keeping the components its target was derived from (D4). A third
would not be a contribution. So: *what a site can do is evidence on the page,
so it is detected. Which of the available actions is best is genuinely unknown,
so that is left to the decision log.*

**2 — Why flags and not a site type.** This is what E10 actually taught us, and
it matters more than the agreement figure. Of four initial disagreements, **two
were faults in my labels, not in the detector**: a charity that sells
merchandise has *donation and commerce*; a publisher running a store has
*commerce as well as content*. Had I modelled capability as a category —
"this is a charity site" — the detector could not have been right where my
label was wrong. Independent flags is what made that possible.

**3 — Why the detector is deliberately conservative.** The two errors are not
symmetric. A **false negative** just gives the client a smaller action set. A
**false positive invents an action the client cannot perform**, and the system
recommends it. So each signal needs a real match. Concretely, after E10 I
changed URL matching from substring to whole-segment, because `/product` had
fired on a magazine's `/categories/product-strategy` and a retailer's
`support.` subdomain had been read as a donation page. **`support` is now
deliberately absent from the donation URL list** — as a URL it means customer
service far more often than it means donating, and it survives only as the
phrase *"support us"* in the text channel.

**4 — What it costs downstream.** A varying action set changes the propensity.
Exploration must be uniform over the actions available to *that* customer at
*that* moment:

```
P(a | x) = ε/|A(x)| + (1 − ε)·1[a = greedy(x)]
```

and **`|A(x)|` must be logged with the decision**, because an estimator run
months later cannot reconstruct which actions were on offer. Getting that
denominator wrong is a *silent bias*, not an error. And E11 measures the price:
reaching RMSE 0.02 takes **5,000** logged decisions with 2 actions and
**80,000** with 16. Adding an action nobody chooses is not free — it takes
evidence away from every other action.

### The honest limit — say it before you are asked

The E10 sample is **fifteen websites, and it is a development set.** Both the
detector and two of my labels changed after seeing the results, so the reported
agreement of 1.0 is **fitted, not held out**. The Wilson intervals are wide for
exactly that reason — commerce is [0.676, 1.0] on eight judgements, lead
capture is [0.207, 1.0] on one. A fresh sample of sites never inspected during
development is what would turn this into a generalisation claim, and it is
listed in future work.

Also: **the action vocabulary is authored, not discovered.** Detection decides
which families a site can support; it does not invent new ones. A client
needing an action outside the catalogue must have it added by hand.

### Two things to check in Table 9 before you present it

1. **The table lists four capabilities; the system has five.** `content` is
   missing (`api/services/actions_catalogue.py:54`). It is not cosmetic —
   `content` is set to `True` for every site, and it is the **floor that
   guarantees the candidate set is never empty.** An empty candidate set means
   no action, no propensity, and a division by zero in the estimator. Either
   add the row, or be ready to explain the omission.

2. **The third column's action names are prose, not the implemented keys.**
   Table 9 says *"renewal reminder"*, *"lead-nurture sequence"*, *"demo
   invitation"*, *"recurring-gift prompt"* — none of these is a key in
   `CATALOGUE`. The implemented catalogue has **17 actions**: 5 commerce
   (Premium offer, Discount offer, Abandoned basket reminder, Replenishment
   reminder, New arrivals), 4 subscription (Upgrade prompt, Trial extension,
   Onboarding nudge, Feature announcement), 2 lead capture (Personalised offer,
   Case study), 2 donation (Donation appeal, Impact update), 2 content (Content
   digest, Article recommendation) and 2 cross-cutting (Reactivation campaign,
   General reminder). If a panellist opens the file while you are reading the
   table aloud, the names will not match. Either say **"these are families —
   the implemented catalogue is seventeen actions"**, or align the table to the
   keys.

### Likely follow-ups

**"What if the detector is wrong about a client?"**
The failure is asymmetric by design, so the common case is a smaller action set
than the site deserves. And a site with *no* capabilities detected does not get
an empty list — it falls back to the four legacy actions, so a site that
predates detection behaves exactly as it did before.

**"Does Module 4's goal classifier decide which action is chosen?"**
No, and deliberately not. It **orders** the candidates; it never filters them.
Its macro-F1 is around 0.50 (E6). Filtering a site's genuine capabilities on a
model that close to a coin flip would remove actions the site really supports.
Ordering is a presentation choice; filtering would be a correctness claim the
model cannot support.

**"Is the customer side rule-based too?"**
Yes, and it is the same argument. You cannot send a replenishment reminder to
someone who has never bought, or a trial extension to someone with no trial.
Those are facts about the record, not predictions. `available()` returns
`site_actions ∩ eligible`, and it is deterministic given the same inputs —
which it has to be, because the estimator reading the log months later must be
able to reproduce exactly which actions were on offer.
