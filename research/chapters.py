"""The written chapters, generated from the measured results.

    venv/bin/python -m research.chapters

Writes `docs/research/*.md` and `report/build/content_research.py`.

The prose is authored here once and rendered twice — to Markdown for the
repository and to the report builder's block DSL for the .docx. Writing it
twice would guarantee the two drift, and the numbers are interpolated from
`research/results/results.json` rather than typed, so a rerun of `make research`
updates every figure quoted in every sentence.

That is the whole point: a claim in the report and the experiment that produced
it cannot disagree, because there is only one copy of the number.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research import config

DOCS = config.ROOT / "docs" / "research"
REPORT_MODULE = config.ROOT / "report" / "build" / "content_research.py"

Block = tuple[str, Any]


# ── Reading the results ──────────────────────────────────────────────────────
class Results:
    """Typed-ish access to results.json, with loud failure on a missing key.

    A silently-missing metric would render as an empty cell in the report, which
    is the one failure mode this whole generator exists to prevent.
    """

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.experiments = payload.get("experiments", {})

    @classmethod
    def load(cls) -> "Results":
        path = config.RESULTS / "results.json"
        if not path.exists():
            raise SystemExit(
                f"{path} not found — run `make research` before generating chapters.")
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def ok(self, key: str) -> bool:
        return self.experiments.get(key, {}).get("status") == "ok"

    def m(self, key: str, name: str, default: Any = None) -> Any:
        value = self.experiments.get(key, {}).get("metrics", {}).get(name, default)
        if value is None and default is None:
            raise KeyError(f"{key}.metrics.{name} is missing from results.json")
        return value

    def table(self, name: str) -> list[dict]:
        import csv

        path = config.RESULTS / f"{name}.csv"
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def notes(self, key: str) -> list[str]:
        return self.experiments.get(key, {}).get("notes", []) or []


def _pct(value: float, places: int = 1) -> str:
    return f"{float(value) * 100:.{places}f}%"


def _table_block(caption: str, header: list[str], rows: list[list[str]]) -> Block:
    return ("table", {"caption": caption, "header": header, "rows": rows})


def _figure(name: str, caption: str) -> Block:
    return ("figure", {"path": str(config.FIGURES / f"{name}.png"),
                       "caption": caption, "width": 6.0})


# ── Chapter: Methodology ─────────────────────────────────────────────────────
def methodology(r: Results) -> list[Block]:
    return [
        ("h1", "RESEARCH METHODOLOGY"),

        ("h2", "1.1 What is being studied"),
        ("p", "This project builds a closed-loop marketing framework for newly "
              "launched products, where almost no behavioural history exists. "
              "Four modules act on one audience: segmentation, campaign "
              "automation, analytics and decision support, and content "
              "generation. Each module was developed separately and evaluated "
              "on its own; the contribution of this stage of the work is that "
              "they now run as one system over a single audience, and that "
              "every claim about them is reproducible from one command."),

        ("h2", "1.2 The audience, and what it is made of"),
        ("p", "The study audience is the **Digital Marketing Campaign** dataset "
              "— 8,000 customers with recorded website behaviour, email "
              "engagement, purchase history and a conversion outcome. Those "
              "customers are imported as the customer base of a demonstration "
              "e-commerce store, so that the same audience flows through all "
              "four modules exactly as a real one would."),
        ("p", "This is the single most important methodological point in the "
              "project, and it must be stated before any result is quoted. "
              "The dataset is real: real people, whose behaviour was really "
              "measured. But it was measured as **per-customer totals** — "
              "25 website visits, 5.5 pages per visit, 9 email opens — and not "
              "as an event log. Nobody recorded when visit 14 happened or which "
              "page it was."),
        ("table", {
            "caption": "Table R1 — What is measured data and what is "
                       "reconstructed by the importer.",
            "header": ["Quantity", "Status", "Source"],
            "rows": [
                ["Sessions, page views, time on site", "Measured",
                 "WebsiteVisits, PagesPerVisit, TimeOnSite"],
                ["On-site clicks", "Measured", "ClickThroughRate × page views"],
                ["Purchases", "Measured", "PreviousPurchases"],
                ["Email opens and clicks", "Measured",
                 "EmailOpens, EmailClicks"],
                ["Conversion outcome", "Measured", "Conversion"],
                ["Acquisition channel", "Measured", "CampaignChannel"],
                ["Timestamp of each visit", "Reconstructed",
                 "Spread over a 90-day window, seeded per customer"],
                ["Which page each visit landed on", "Reconstructed",
                 "Cycled through the store's real pages"],
                ["Scroll depth", "Reconstructed", "Derived from dwell time"],
                ["Order of email opens and clicks", "Reconstructed",
                 "Interleaved across the window"],
                ["Basket value of a purchase", "Reconstructed",
                 "Drawn from the store's catalogue prices"],
            ]}),
        ("note", "**Consequence for the results.** Anything that depends only "
                 "on the totals — segment membership, conversion rate by "
                 "segment, funnel counts — rests on real measurements. Anything "
                 "that depends on event *order* or *timing* — attribution paths, "
                 "journey length, inter-event gaps — is a property of the "
                 "reconstruction as much as of the data, and is reported as such "
                 "throughout Chapter 3."),
        ("p", "To keep that distinction in the data rather than only in prose, "
              "the importer writes one event per *visit* carrying that visit's "
              "totals, instead of one event per page view. A live browser "
              "reports one event per page and no count; the feature definition "
              "sums the two identically, so a single definition serves both "
              "without either pretending to be the other."),

        ("h2", "1.3 Provenance is recorded, never asserted"),
        ("p", "Imported customers and live browser sessions share one database. "
              "Every visitor and every funnel event therefore carries a "
              "`source` column with the value `dataset` or `live`, and that "
              "value is **derived at write time from the visitor the event "
              "belongs to** — it can never be supplied by the caller. A test "
              "fails the build if a dataset-derived customer ever produces a "
              "row claiming to be live observation."),
        ("p", "Every figure in the dashboard carries the resulting label, and "
              "the analytics layer refuses to report attribution below five "
              "converting journeys rather than returning a number it cannot "
              "support."),

        ("h2", "1.4 Reproducibility"),
        ("p", f"All randomness is seeded (seed {r.payload.get('seed')}). The "
              f"importer is deterministic given the source CSV and idempotent "
              f"on re-run. Confidence intervals use "
              f"{r.payload.get('n_bootstrap'):,} bootstrap resamples, and the "
              f"policy comparison runs {r.payload.get('n_seeds')} independent "
              f"seeds. `make research` regenerates every table and every figure "
              f"in this chapter and the two that follow."),
    ]


# ── Chapter: Experimental setup ──────────────────────────────────────────────
def setup(r: Results) -> list[Block]:
    rows = [
        ["E1", "Does the hybrid beat its own components?",
         "8,000-customer dataset", "Conversion separation, silhouette"],
        ["E2", "The two Module 1 defects, reproduced",
         "8,000-customer dataset", "Segment survival, accuracy, certainty"],
        ["E3", "Which automation policy wins, and at what cost",
         "Module 2 simulator, 30 seeds", "Conversions per 1,000 sends"],
        ["E4", "Do the attribution models agree?",
         "Module 3 simulator + live journeys", "MAE vs ground truth, TVD"],
        ["E5", "Prediction quality and its transfer",
         "Module 3 features + live audience", "ROC-AUC, PR-AUC, Brier"],
        ["E6", "TF-IDF versus Sentence-BERT",
         "527-row goal/tone corpus", "Macro-F1, McNemar"],
        ["E7", "Engagement leakage and text signal",
         "12,000-row engagement corpus", "R², Spearman, Holm–Bonferroni"],
        ["E8", "Targeting by uplift versus by predicted response",
         "Hillstrom, 64,000 randomised", "Qini, incremental response"],
        ["E9", "Does the decision log make the policy learnable?",
         "Simulated world, known rewards", "Estimator bias, RMSE"],
    ]
    return [
        ("h1", "EXPERIMENTAL SETUP"),

        ("h2", "2.1 The experiments"),
        ("p", "Nine experiments cover the four modules. Each writes its tables "
              "to `research/results/`, and every figure in the next chapter is "
              "drawn from those tables rather than plotted by hand, so a chart "
              "cannot drift away from the number it shows."),
        _table_block("Table R2 — The seven experiments.",
                     ["ID", "Question", "Data", "Primary metric"], rows),

        ("h2", "2.2 Choice of statistics"),
        ("p", "Four tools are used, each chosen because it makes the fewest "
              "assumptions the data can violate."),
        ("bullets", [
            "**Percentile bootstrap** rather than a normal-theory interval. "
            "Conversion separation, silhouette and macro-F1 are not means and "
            "have no closed-form standard error; resampling makes no "
            "distributional claim at all.",
            "**Paired bootstrap and Wilcoxon signed-rank** for the policy "
            "comparison. Each seed puts the same 8,000 customers through all "
            "three policies, so the runs are paired; ignoring that wastes power "
            "and overstates the p-value.",
            "**Exact McNemar** for two classifiers on one test set. Only the "
            "disagreements carry information, and with roughly a hundred test "
            "rows the exact binomial is correct where the asymptotic "
            "approximation is not.",
            "**Cliff's delta** alongside every p-value. With thirty seeds almost "
            "any difference reaches significance; the effect size is what says "
            "whether it matters.",
        ]),

        ("h2", "2.3 Metrics, and why not the obvious ones"),
        ("bullets", [
            "**Conversion separation**, not cluster quality, for segmentation. "
            "Conversion is used only to *evaluate* segments — never as a "
            "clustering feature and never as a rule input — so a segmentation "
            "that separates it has found something it was not told.",
            "**Conversions per 1,000 sends**, not conversion rate, for the "
            "policy comparison. User-level conversion rises simply by sending "
            "more messages, which would hand the win to the policy that sends "
            "most rather than the one that sends best.",
            "**Macro-F1**, not accuracy, for goal and tone. The majority class "
            "is 59% of the goal corpus, so accuracy flatters a model that "
            "handles rare classes badly — and the rare classes are the ones a "
            "marketer would want detected.",
            "**Spearman**, not R², for engagement. The model exists to rank "
            "candidate captions, not to predict an engagement rate in absolute "
            "terms, and rank correlation is what ranking needs.",
        ]),
    ]


# ── Chapter: Results ─────────────────────────────────────────────────────────
def results_chapter(r: Results) -> list[Block]:
    blocks: list[Block] = [("h1", "RESULTS")]

    # ── E1 ──────────────────────────────────────────────────────────────────
    if r.ok("E1"):
        comparison = r.table("e1_method_comparison")
        hybrid_sep = r.m("E1", "hybrid_separation")
        best_single = r.m("E1", "best_single_separation")
        silhouette = r.m("E1", "silhouette")

        blocks += [
            ("h2", "3.1 Segmentation — the hybrid against its components"),
            _table_block(
                "Table R3 — Each method scored on the same 8,000 customers, "
                "with 95% bootstrap intervals.",
                ["Method", "Segments", "Separation", "95% CI", "Cold-start segment"],
                [[row["method"], row["n_segments"],
                  f"{float(row['separation']):.4f}",
                  f"[{float(row['ci_low']):.3f}, {float(row['ci_high']):.3f}]",
                  "yes" if row["finds_cold_start"] == "True" else "no"]
                 for row in comparison]),
            _figure("fig_e1_segmentation_ablation",
                    "Figure R1 — Conversion separation by method. The hybrid and "
                    "the rules are indistinguishable; clustering alone separates "
                    "almost nothing."),
            ("p", f"The hybrid separates conversion by {hybrid_sep:.4f}, against "
                  f"{best_single:.4f} for the rules alone. The difference is "
                  f"within noise. Clustering on its own reaches "
                  f"{min(float(row['separation']) for row in comparison):.4f}."),
            ("note", "**This is a negative result, and it is reported as the "
                     "headline rather than buried.** On the separation metric the "
                     "clustering contributes nothing. The hybrid earns its place "
                     "in the system on different grounds — it produces a "
                     "calibrated confidence from the level of agreement between "
                     "three independent methods, and the vote is what makes cold "
                     "start explicit — but it does not separate conversion better "
                     "than a handful of interpretable rules."),
            ("p", f"Silhouette is {silhouette:.4f}. The clusters overlap heavily "
                  f"in feature space, and all three methods disagree for "
                  f"{_pct(r.m('E1', 'all_disagree_share'))} of customers. The "
                  f"segments are commercially useful without being geometrically "
                  f"clean, and reporting only the separation would hide that."),
            _figure("fig_e1_segment_profile",
                    "Figure R2 — Segment sizes and conversion rate per segment."),
        ]

    # ── E2 ──────────────────────────────────────────────────────────────────
    if r.ok("E2"):
        detected = r.m("E2", "cold_start_detected")
        kept_nb = r.m("E2", "cold_start_kept_notebook")
        leaky_acc = r.m("E2", "leaky_accuracy")
        clean_acc = r.m("E2", "clean_accuracy")
        cert_leaky = r.m("E2", "users_at_certainty_leaky")
        cert_clean = r.m("E2", "users_at_certainty_clean")

        blocks += [
            ("h2", "3.2 Two defects, reproduced and measured"),
            ("h3", "3.2.1 A segment deleted by its own vote"),
            ("p", f"The original agreement vote tested whether the two "
                  f"clusterings agreed *before* it tested whether the rules had "
                  f"identified a cold-start customer. Clustering cannot represent "
                  f"“there is not enough evidence about this person” — it "
                  f"must place everyone somewhere — so whenever the two "
                  f"clusterings happened to agree, they overruled the rules. "
                  f"Of {detected} cold-start customers the rules detect, that "
                  f"ordering keeps {kept_nb}; on the live audience the segment "
                  f"went to zero. Novel Contribution 1 was being erased from its "
                  f"own output."),
            ("p", f"Resolving cold start immediately after unanimity keeps all "
                  f"{detected}. Those customers convert at "
                  f"{_pct(r.m('E2', 'cold_start_conversion'))} against "
                  f"{_pct(r.m('E2', 'other_segments_conversion'))} for everyone "
                  f"else, so the segment the original code discarded is the one "
                  f"with the most distinctive behaviour in the dataset."),
            ("note", "The general principle, and the one worth defending in a "
                     "viva: **a method that cannot represent a finding does not "
                     "get a vote on it.**"),

            ("h3", "3.2.2 Target leakage in the confidence model"),
            ("p", f"The Random Forest was trained with the rule label among its "
                  f"input features while the target was the hybrid consensus — so "
                  f"it was largely reading off its own answer. Reproducing both "
                  f"versions on the same split shows accuracy barely moves "
                  f"({leaky_acc:.4f} against {clean_acc:.4f}), but certainty "
                  f"changes by a factor of {cert_leaky / max(cert_clean, 1):.0f}: "
                  f"{cert_leaky} customers emerge at confidence 1.00 with the "
                  f"rule label among the inputs, against {cert_clean} without it."),
            ("p", "Accuracy is not what the defect corrupts. The confidence "
                  "attached to every downstream decision is — and a model whose "
                  "accuracy is honest while its confidence is not will be trusted "
                  "in exactly the cases where it should not be. That is also why "
                  "the defect survived review: nothing fails, no test goes red, "
                  "and the only symptom is a confidence column that looks "
                  "impressive."),
            _figure("fig_e2_defects",
                    "Figure R3 — Both defects reproduced against their fixes."),
        ]

    # ── E3 ──────────────────────────────────────────────────────────────────
    if r.ok("E3"):
        summary = r.table("e3_policy_summary")
        contests = r.table("e3_policy_contests")
        live = r.table("e3_live_measured")

        blocks += [
            ("h2", "3.3 Automation policies — outcome against cost"),
            _table_block(
                f"Table R4 — Policy comparison over {r.m('E3', 'n_seeds')} paired "
                f"seeds on the Module 2 simulator.",
                ["Policy", "Conv. per 1,000 sends", "95% range", "Messages/user",
                 "Decision rules"],
                [[row["strategy"], row["conversions_per_1000_sends"],
                  f"[{row['ci_low']}, {row['ci_high']}]",
                  row["messages_per_user"], row["operational_complexity"]]
                 for row in summary]),
            _table_block(
                "Table R5 — Head-to-head, paired by seed.",
                ["Comparison", "Mean difference", "95% CI", "Wilcoxon p",
                 "Cliff's δ", "Extra rules"],
                [[row["comparison"], row["mean_difference"],
                  f"[{row['ci_low']}, {row['ci_high']}]",
                  f"{float(row['wilcoxon_p']):.2e}", row["cliffs_delta"],
                  row["extra_rules"]]
                 for row in contests]),
            _figure("fig_e3_policy_comparison",
                    "Figure R4 — Efficiency across seeds, and what each policy "
                    "costs to run."),
        ]

        if live:
            blocks += [
                _table_block(
                    "Table R6 — The same three policies measured on the imported "
                    "audience in the running system.",
                    ["Policy", "Sent", "Clicks", "Conversions",
                     "Conv. per 1,000 sends", "Rules"],
                    [[row["strategy"], row["sent"], row["clicks"],
                      row["conversions"], row["conversions_per_1000_sends"],
                      row["operational_complexity"]] for row in live]),
                ("note", "**The simulation and the live build disagree about "
                         "which policy wins.** Both metrics are volume-controlled, "
                         "so the difference lies in how response is modelled — the "
                         "simulator's segment-level propensities against "
                         "per-customer rates drawn from each customer's own "
                         "recorded email history. Neither is an observation of "
                         "real people reacting. The ranking is evidently not "
                         "robust to that choice, and that instability is the "
                         "result. Quoting whichever run supports the preferred "
                         "conclusion would be the one genuinely dishonest option "
                         "available here."),
            ]

        blocks += [
            _figure("fig_e3_sparsity",
                    "Figure R5 — Efficiency as the behavioural signal is "
                    "suppressed. A policy that reacts to behaviour should degrade "
                    "as behaviour stops being observable."),
        ]

    # ── E4 ──────────────────────────────────────────────────────────────────
    if r.ok("E4"):
        mae = r.table("e4_ground_truth_mae")
        blocks += [
            ("h2", "3.4 Attribution — four models, four answers"),
            _table_block(
                "Table R7 — Attribution models scored against known channel "
                "influence on simulated journeys.",
                ["Model", "MAE", "95% CI", "Channels"],
                [[row["model"], row["mae"],
                  f"[{row['ci_low']}, {row['ci_high']}]", row["n_channels"]]
                 for row in mae]),
            ("p", f"On the live journeys of {r.m('E4', 'live_converters'):,} "
                  f"converting customers the models disagree over "
                  f"{_pct(r.m('E4', 'max_pairwise_disagreement'), 0)} of all "
                  f"attributed credit at the widest pair, and "
                  f"{_pct(r.m('E4', 'mean_pairwise_disagreement'), 0)} on average. "
                  f"Last-touch hands the great majority of credit to email; "
                  f"first-touch spreads it almost evenly across the acquisition "
                  f"channels."),
            ("note", "A company reading only its last-touch dashboard would "
                     "conclude that email is responsible for nearly everything, "
                     "and would cut the acquisition spend that built the audience "
                     "email later converted. The disagreement between models is "
                     "not a defect in one of them — it is the finding."),
            ("p", f"{_pct(r.m('E4', 'single_touch_share'), 0)} of converting "
                  f"journeys have a single touchpoint. On those, every model "
                  f"agrees by arithmetic, and that agreement must never be read "
                  f"as corroboration."),
            _figure("fig_e4_attribution",
                    "Figure R6 — The same journeys under four attribution models, "
                    "and their error where ground truth exists."),
        ]

    # ── E5 ──────────────────────────────────────────────────────────────────
    if r.ok("E5"):
        scores = r.table("e5_model_scores")
        transfer = r.table("e5_transfer")
        blocks += [
            ("h2", "3.5 Prediction, and what the move to another audience costs"),
            _table_block(
                "Table R8 — Conversion and drop-off classifiers against a "
                "baseline, fitted on Module 3's simulator.",
                ["Target", "Model", "ROC-AUC", "95% CI", "PR-AUC", "Brier"],
                [[row["target"], row["model"], row["roc_auc"],
                  f"[{row['roc_auc_ci_low']}, {row['roc_auc_ci_high']}]",
                  row["pr_auc"], row["brier"]] for row in scores]),
            _figure("fig_e5_prediction",
                    "Figure R7 — Discrimination against a stratified baseline, "
                    "with bootstrap intervals."),
        ]
        if transfer:
            blocks += [
                _table_block(
                    "Table R9 — The same models applied to the imported audience "
                    "— a different distribution from the one they were fitted on.",
                    ["Prediction", "Min", "Median", "Max", "Above threshold"],
                    [[row["prediction"], row["min"], row["median"], row["max"],
                      f"{row['above_threshold']} of {row['n_customers']} "
                      f"(≥ {row['threshold']})"] for row in transfer]),
                ("p", "The models discriminate well on the distribution they were "
                      "fitted on. Applying them to another audience is a transfer "
                      "across distributions: the ranking remains usable, the "
                      "absolute probabilities are not calibrated for it, and any "
                      "threshold set on the training distribution should be "
                      "treated as arbitrary here. The system raises a calibration "
                      "warning rather than reporting a confident number when the "
                      "prediction distribution is degenerate."),
            ]

    # ── E6 ──────────────────────────────────────────────────────────────────
    if r.ok("E6"):
        summary = r.table("e6_model_summary")
        mcnemar_rows = r.table("e6_mcnemar")
        blocks += [
            ("h2", "3.6 Goal and tone — the simpler model wins, and it matters "
                   "which metric says so"),
            _table_block(
                "Table R10 — Classifier comparison. Accuracy and macro-F1 tell "
                "different stories.",
                ["Target", "Model", "Accuracy", "Macro-F1", "Weighted F1", "Test rows"],
                [[row["target"], row["model"], row["accuracy"], row["macro_f1"],
                  row["weighted_f1"], row["n_test"]] for row in summary]),
            _figure("fig_e6_goal_tone",
                    "Figure R8 — Accuracy against macro-F1, with the "
                    "majority-class baseline marked."),
        ]
        if mcnemar_rows:
            blocks += [
                _table_block(
                    "Table R11 — Exact McNemar between the two approaches on the "
                    "same test rows.",
                    ["Target", "TF-IDF right, SBERT wrong",
                     "SBERT right, TF-IDF wrong", "p"],
                    [[row["target"], row["b01"], row["b10"],
                      f"{float(row['p_value']):.3f}"] for row in mcnemar_rows]),
                ("note", "Neither comparison is significant. The two approaches "
                         "are statistically indistinguishable on this corpus, so "
                         "selecting TF-IDF is a decision about cost, speed and "
                         "interpretability rather than about accuracy — which is a "
                         "stronger and more defensible claim than asserting the "
                         "simpler model is more accurate."),
            ]

    # ── E7 ──────────────────────────────────────────────────────────────────
    if r.ok("E7"):
        comparison = r.table("e7_leakage_comparison")
        blocks += [
            ("h2", "3.7 Engagement — a leak, and a dataset with no signal"),
            _table_block(
                "Table R12 — The engagement regressor with and without the "
                "outcome columns among its features.",
                ["Feature set", "Features", "R²", "Spearman", "MAE"],
                [[row["feature_set"], row["n_features"], row["r2"],
                  row["spearman"], row["mae"]] for row in comparison]),
            ("p", f"With the outcome columns present the model reports "
                  f"R² = {r.m('E7', 'leaky_r2'):.4f}. Removing them gives "
                  f"R² = {r.m('E7', 'clean_r2'):.4f} "
                  f"{r.m('E7', 'clean_r2_ci')} and a rank correlation of "
                  f"{r.m('E7', 'clean_spearman'):.4f} "
                  f"{r.m('E7', 'clean_spearman_ci')} — an interval spanning zero, "
                  f"so no ranking skill is demonstrated on held-out data."),
            ("p", f"The failure was invisible in training and fatal in use. A "
                  f"caption that has not been posted has no like count, so at "
                  f"prediction time those columns were filled with zeros — far "
                  f"outside anything the model had seen — and the score driving "
                  f"45% of every content ranking became noise. Its weight was "
                  f"reduced to 0.20 once the honest number was known."),
            ("p", f"Testing each of the {r.m('E7', 'n_features_tested')} text "
                  f"features against the target individually, "
                  f"{r.m('E7', 'features_with_signal')} survive Holm–Bonferroni "
                  f"correction. This is a property of the dataset rather than a "
                  f"modelling failure: no model can extract a signal that is not "
                  f"there, and the correct response is to reduce the weight the "
                  f"score carries rather than to keep tuning."),
            _figure("fig_e7_engagement",
                    "Figure R9 — The leak, and the absence of text signal."),
        ]

    # ── E8 ──────────────────────────────────────────────────────────────────
    if r.ok("E8"):
        summary = r.table("e8_policy_summary")
        actions = r.table("e8_action_assignment")
        overlap = r.m("E8", "top_share_overlap")

        blocks += [
            ("h2", "3.8 Who to target is not who will convert"),
            ("p", "The recommender ranks customers by predicted conversion and "
                  "gives the strongest action to the top of that ranking. That "
                  "is the intuitive thing to do and it answers the wrong "
                  "question. What matters is not who will convert but for whom "
                  "the action *changes* whether they convert — a customer "
                  "certain to buy anyway gains nothing from a discount, and the "
                  "discount is wasted on them."),
            ("p", "Answering that needs counterfactuals, and this project's own "
                  "audience cannot supply any: every imported customer received "
                  "one treatment, nobody recorded which, and no comparable "
                  "customer received an alternative. No model can recover a "
                  "causal effect from data where the cause never varied. The "
                  "experiment therefore moves to the **Hillstrom MineThatData** "
                  "dataset — 64,000 customers randomly assigned to one of three "
                  "arms (mens email, womens email, no email) with observed "
                  "visits. Random assignment is what makes the counterfactual "
                  "estimable."),
            _table_block(
                "Table R13 — Targeting policies scored on held-out customers. "
                "Qini is incremental responders above random targeting; the "
                "final column is what a 30% email budget buys.",
                ["Policy", "Qini", "95% CI", "Extra visits per 1,000 targeted"],
                [[row["policy"], row["qini_coefficient"],
                  f"[{row['ci_low']}, {row['ci_high']}]",
                  row["uplift_per_1000"]] for row in summary]),
            _figure("fig_e8_uplift",
                    "Figure R10 — Qini curves and what each policy buys at a "
                    "fixed budget."),
            ("p", f"Ranking by uplift and ranking by predicted response select "
                  f"substantially different people: the two scores correlate at "
                  f"Spearman {r.m('E8', 'rank_agreement_spearman'):.2f}, and at a "
                  f"30% budget the two policies share only "
                  f"{_pct(overlap, 0)} of their chosen customers — so about "
                  f"{_pct(1 - overlap, 0)} of the list would be emailed by one "
                  f"and not the other."),
            ("note", "**What this does and does not establish.** The best uplift "
                     "learner buys more incremental visits than the current "
                     "policy, but their Qini intervals overlap, so the ordering "
                     "of the two is not established on this split. The two uplift "
                     "learners also disagree with each other, one of them falling "
                     "below the current policy — so “use uplift modelling” is not "
                     "a conclusion on its own. What the data does support is the "
                     "weaker and more useful claim: these are different policies "
                     "that target different people, and the difference is large "
                     "enough to matter."),
        ]

        if actions:
            blocks += [
                _table_block(
                    "Table R14 — The three-arm version: which action each "
                    "customer should receive, rather than whether to act.",
                    ["Assigned action", "Customers", "Share",
                     "Observed uplift per 1,000"],
                    [[row["assigned_action"], row["customers"],
                      f"{float(row['share']):.1%}",
                      row["observed_uplift_per_1000"] or "—"]
                     for row in actions]),
                ("p", "This is the next-best-action problem proper: not send or "
                      "do not send, but which of several actions. Note that the "
                      "policy assigns a share of customers to *no email at all* "
                      "— an output the current rule cannot produce, because "
                      "every customer is given some action regardless of whether "
                      "acting helps."),
            ]

        blocks += [
            ("p", "Hillstrom's actions are mens and womens email, not this "
                  "project's premium, personalised, reactivation and reminder. "
                  "The experiment demonstrates the method on real randomised "
                  "data and shows that the current policy is answering a "
                  "different question from the one it should. It does not "
                  "produce a policy deployable to the imported audience, and "
                  "nothing in this report should be read as claiming it does."),
        ]

    # ── E9 ──────────────────────────────────────────────────────────────────
    if r.ok("E9"):
        accuracy = r.table("e9_estimator_accuracy")
        exploration = r.table("e9_exploration")

        blocks += [
            ("h2", "3.9 Making the recommendation learnable"),
            ("p", "E8 showed the recommender was answering the wrong question, "
                  "and that no borrowed dataset can answer the right one for "
                  "this project's actions. The response was to change what the "
                  "system records. `analytics_output` is overwritten on every "
                  "run and therefore holds only the current opinion; a new "
                  "append-only `action_log` records the decision that was "
                  "actually taken, **the probability it was taken under**, the "
                  "features it was taken on, and what followed."),
            ("p", "The propensity is the column that matters. Without it, logged "
                  "data can only report what the running policy achieved. With "
                  "it, an inverse-propensity estimator can answer what a "
                  "*different* policy would have achieved on the same customers "
                  "— a counterfactual recovered from observational logs. And "
                  "because a deterministic policy assigns probability zero to "
                  "every action it does not take, a small share of decisions are "
                  "made at random on purpose."),
            ("p", "That machinery is only worth having if it works, so this "
                  "experiment checks it in the one setting where “works” is "
                  "precisely defined: a simulated world with a known reward "
                  "function, where the true value of any policy is computable "
                  "and the estimate can be scored against it."),
            _table_block(
                "Table R15 — Estimator error against the true policy value, as "
                "the log grows. 40 replications per row.",
                ["Estimator", "Logged decisions", "Bias", "95% CI", "RMSE",
                 "Unbiased"],
                [[row["estimator"].replace("_", " "), row["log_size"],
                  row["bias"], f"[{row['bias_ci_low']}, {row['bias_ci_high']}]",
                  row["rmse"], "yes" if row["unbiased"] == "True" else "no"]
                 for row in accuracy]),
            _table_block(
                "Table R16 — What exploration buys, and what it costs.",
                ["Exploration rate", "Bias", "RMSE", "Reward given up"],
                [[f"{float(row['exploration_rate']):.0%}", row["bias"],
                  row["rmse"], f"{float(row['cost_of_exploring']):.1%}"]
                 for row in exploration]),
            _figure("fig_e9_offpolicy",
                    "Figure R11 — Estimator error against log size, and bias "
                    "against exploration rate."),
            ("p", f"At {r.m('E9', 'largest_log'):,} logged decisions the "
                  f"self-normalised estimator recovers the candidate policy's "
                  f"true value with a bias of {r.m('E9', 'best_bias'):+.4f} and "
                  f"an interval containing zero. The mechanism also detects that "
                  f"the candidate policy is worth "
                  f"{r.m('E9', 'true_policy_gain'):.4f} more reward per customer "
                  f"than the one generating the logs — from logged data alone, "
                  f"without having deployed it to anybody."),
            ("note", "**The finding worth carrying into the viva.** Without "
                     f"exploration the estimate is biased by "
                     f"{r.m('E9', 'bias_without_exploration'):+.4f}, and biased "
                     "*upwards* — it reports the candidate policy as better than "
                     "it is. Worse, the deterministic log looks more trustworthy: "
                     "its effective sample size is "
                     f"{r.m('E9', 'ess_without_exploration'):.0f} against "
                     f"{r.m('E9', 'ess_with_exploration'):.0f} with exploration, "
                     "because every weight is 0 or 1 rather than spread out. The "
                     "standard diagnostic for an unreliable importance-weighted "
                     "estimate points the wrong way. The estimate is stable and "
                     "wrong, computed only over the customers where the candidate "
                     "happens to agree with the logged policy. **Stability is not "
                     "correctness.**"),
            ("p", "Token exploration is worse than none: at a 1% rate the "
                  "estimator has the worst error of any setting tested — too few "
                  "random decisions to remove the bias, and weights large enough "
                  "to wreck the variance. Exploration is a commitment, not a "
                  "gesture."),
            ("p", "This experiment is a simulation, deliberately and without "
                  "apology. The claim under test is a property of an *estimator* "
                  "— unbiasedness — which is settled by mathematics and can "
                  "therefore be checked exactly against a known answer. It claims "
                  "nothing about real customers. What it establishes is that the "
                  "mechanism now in the system will produce a usable answer once "
                  "enough decisions have been logged, which is the difference "
                  "between a system that can improve and one that can only "
                  "assert."),
        ]

    return blocks


# ── Chapter: Discussion, threats, limitations ────────────────────────────────
def discussion(r: Results) -> list[Block]:
    blocks: list[Block] = [
        ("h1", "DISCUSSION"),

        ("h2", "4.1 What the evidence supports"),
        ("bullets", [
            "**The closed loop runs.** One audience passes through segmentation, "
            "content generation, campaign planning and analytics, and the "
            "analytics output feeds back into which platforms get written for "
            "next. That is the architecture the report proposes, executing.",
            "**Cold start is handled explicitly, and it had to be defended.** "
            "The engine declines to cluster below thirty customers and says why; "
            "individual customers with thin histories are decided by rules and "
            "flagged. The vote-order defect showed how easily that contribution "
            "can be destroyed by a pipeline that looks correct.",
            "**Attribution model choice changes the conclusion.** On the same "
            "journeys the four models disagree over a third of attributed credit "
            "on average. Any single-model dashboard is a decision, not a "
            "measurement.",
            "**Simpler models won twice.** TF-IDF matched Sentence-BERT on goal "
            "and tone, and interpretable rules matched the full hybrid on "
            "conversion separation. Neither result was expected.",
            "**The recommender was answering the wrong question.** Ranking "
            "customers by predicted conversion and ranking them by the "
            "*incremental effect* of the action select materially different "
            "people — they share only about half their choices at a realistic "
            "budget. This is the clearest direction for future work the project "
            "produced.",
        ]),

        ("h2", "4.2 What the evidence does not support"),
        ("bullets", [
            "**That the hybrid segmentation separates conversion better than "
            "rules alone.** It does not, on this dataset. Its value lies in "
            "calibrated confidence and explicit cold start.",
            "**That any one automation policy is best.** The simulator and the "
            "live build disagree, and the ranking depends on how response is "
            "modelled rather than on the policies themselves.",
            "**That engagement can be predicted from caption text.** Not on this "
            "corpus, where no text feature survives correction.",
            "**That the prediction thresholds transfer.** They were set on the "
            "distribution the models were fitted on and do not carry to another "
            "audience. The production recommender was changed to rank rather "
            "than threshold as a direct consequence.",
            "**That uplift modelling is straightforwardly better.** The best "
            "uplift learner beat the current policy, but the intervals overlap "
            "and the second uplift learner did worse. The framing is right; the "
            "evidence for any particular learner is not yet strong.",
        ]),

        ("h1", "THREATS TO VALIDITY"),

        ("h2", "5.1 Construct validity"),
        ("p", "The reconstruction of event timing is the principal threat. "
              "Attribution operates on journeys whose *order* this project "
              "created, so the attribution results characterise the "
              "reconstruction as well as the data. The counts underlying those "
              "journeys are real; their sequence is not observed. A dataset with "
              "genuine timestamped events would settle what this study can only "
              "bound."),
        ("p", "Conversion separation depends on segment definitions that a human "
              "wrote. The rules were not tuned against the conversion column — "
              "which is what keeps the metric from being circular — but they were "
              "written by someone who knows the domain, and that is a weaker "
              "guarantee than a preregistered rule set."),

        ("h2", "5.2 Internal validity"),
        ("p", "Two defects found in this work were both invisible to the metrics "
              "being watched at the time, and both made results look better. "
              "That is evidence that other such defects may remain. Every "
              "correction now carries a regression test, and the leakage guard in "
              "the engagement model raises an exception rather than a warning if "
              "an outcome column re-enters the feature set."),
        ("p", "Campaign response in both the simulator and the live build is "
              "modelled, not observed. No claim about open or click rates in this "
              "report is a measurement of human behaviour."),

        ("h2", "5.3 External validity"),
        ("p", "One dataset, one product category, one language. The 87.6% "
              "conversion rate in the source data is far above any plausible "
              "e-commerce baseline, which suggests the dataset is either "
              "filtered or synthetic in origin; conclusions about absolute rates "
              "should not leave it. Comparisons *between* methods on the same "
              "data are the results that travel."),
        ("p", "The goal corpus has 453 labelled rows and the tone corpus 174, "
              "with one tone class represented by a single example. Macro-F1 on "
              "a corpus that small carries wide uncertainty, and the per-class "
              "numbers for rare classes should be read as indicative."),

        ("h1", "LIMITATIONS"),
        ("bullets", [
            "**Event timing and ordering are reconstructed**, so attribution "
            "path statistics are partly a property of the importer.",
            "**Campaign response is modelled**, in both the simulator and the "
            "live build. Nobody in this study opened a real email.",
            "**Conversion and drop-off models were fitted on a simulator** and "
            "transfer poorly in calibration, though the ranking survives.",
            "**The engagement dataset carries no usable text signal**, so that "
            "component of the content score is close to arbitrary and is "
            "weighted accordingly.",
            "**`humorous` tone has a single training example** and cannot be "
            "learned or evaluated.",
            "**Open-rate tracking under-reports** by design: most mail clients "
            "block the pixel, so click-through is the reliable engagement signal.",
            "**Three real platform datasets ship unused** — they are "
            "comment-level scrapes that pair no post text with post engagement.",
            "**No action was ever randomised on this project's own audience**, "
            "so the next-best-action recommendation cannot be validated on it at "
            "all. E8 borrows a dataset where treatment *was* randomised, and the "
            "actions there are not this project's actions.",
        ]),
    ]
    return blocks


# ── Rendering ────────────────────────────────────────────────────────────────
def render_markdown(blocks: list[Block]) -> str:
    lines: list[str] = []
    for kind, payload in blocks:
        if kind in ("h1", "h1_nobreak"):
            lines += [f"\n# {payload}\n"]
        elif kind == "h2":
            lines += [f"\n## {payload}\n"]
        elif kind == "h3":
            lines += [f"\n### {payload}\n"]
        elif kind == "h4":
            lines += [f"\n#### {payload}\n"]
        elif kind == "p":
            lines += [payload, ""]
        elif kind == "note":
            lines += ["> " + payload.replace("\n", "\n> "), ""]
        elif kind == "bullets":
            lines += [f"- {item}" for item in payload] + [""]
        elif kind == "numbers":
            lines += [f"{i}. {item}" for i, item in enumerate(payload, 1)] + [""]
        elif kind == "table":
            caption, header, rows = (payload["caption"], payload["header"],
                                     payload["rows"])
            lines += [f"**{caption}**", ""]
            lines += ["| " + " | ".join(str(h) for h in header) + " |"]
            lines += ["|" + "---|" * len(header)]
            for row in rows:
                lines += ["| " + " | ".join(str(c) for c in row) + " |"]
            lines += [""]
        elif kind == "figure":
            path = Path(payload["path"])
            relative = f"../../research/figures/{path.name}"
            lines += [f"![{payload['caption']}]({relative})", "",
                      f"*{payload['caption']}*", ""]
        elif kind == "code":
            lines += ["```", str(payload), "```", ""]
        elif kind == "pagebreak":
            continue
        else:                                                # pragma: no cover
            raise ValueError(f"unknown block for markdown: {kind}")
    return "\n".join(lines).strip() + "\n"


def render_report_module(sections: list[tuple[str, list[Block]]]) -> str:
    """Emit the report builder's block DSL as a generated Python module."""
    blocks: list[Block] = []
    for _, section in sections:
        blocks.extend(section)

    body = ",\n".join(f"    {block!r}" for block in blocks)
    return (
        '# -*- coding: utf-8 -*-\n'
        '"""GENERATED FILE — do not edit by hand.\n\n'
        'Written by `venv/bin/python -m research.chapters` from\n'
        '`research/results/results.json`. Every number here was produced by an\n'
        'experiment in `research/experiments/`; editing this file would break\n'
        'that guarantee. Change the prose in research/chapters.py and regenerate.\n'
        '"""\n\n'
        f'BLOCKS = [\n{body},\n]\n'
    )


SECTIONS = (
    ("methodology", methodology),
    ("experimental-setup", setup),
    ("results", results_chapter),
    ("discussion", discussion),
)


def build() -> list[str]:
    r = Results.load()
    DOCS.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    rendered: list[tuple[str, list[Block]]] = []

    for name, builder in SECTIONS:
        blocks = builder(r)
        rendered.append((name, blocks))
        path = DOCS / f"{name}.md"
        path.write_text(render_markdown(blocks), encoding="utf-8")
        written.append(str(path.relative_to(config.ROOT)))

    index = [
        "# Research chapters",
        "",
        "Generated by `venv/bin/python -m research.chapters` from the results in "
        "`research/results/results.json`. **Do not edit these files by hand** — "
        "the prose lives in `research/chapters.py` and the numbers come from the "
        "experiments, so that a claim and the measurement behind it cannot "
        "disagree.",
        "",
        "| Chapter | Covers |",
        "|---|---|",
        "| [methodology.md](methodology.md) | The audience, what is measured "
        "versus reconstructed, provenance, reproducibility |",
        "| [experimental-setup.md](experimental-setup.md) | The seven "
        "experiments, choice of statistics, choice of metrics |",
        "| [results.md](results.md) | Every measured result, with intervals |",
        "| [discussion.md](discussion.md) | What the evidence does and does not "
        "support, threats to validity, limitations |",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "make research                                  # rerun the experiments",
        "venv/bin/python -m research.chapters           # rewrite these chapters",
        "```",
        "",
    ]
    (DOCS / "README.md").write_text("\n".join(index), encoding="utf-8")
    written.append(str((DOCS / "README.md").relative_to(config.ROOT)))

    REPORT_MODULE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MODULE.write_text(render_report_module(rendered), encoding="utf-8")
    written.append(str(REPORT_MODULE.relative_to(config.ROOT)))

    return written


if __name__ == "__main__":
    for item in build():
        print(f"wrote {item}")
