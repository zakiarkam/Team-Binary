"""Research dashboard for the marketing content pipeline.

Run with:
    streamlit run dashboard/app.py

Every number shown here is read from an artifact the pipeline wrote. The
dashboard never recomputes a score, so what it displays is what the pipeline
actually produced — including the gaps.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import artifacts
import theme
import config

st.set_page_config(
    page_title="Marketing Content Pipeline — Research Dashboard",
    page_icon="📊",
    layout="wide",
)

theme.register()

st.markdown(
    f"""
    <style>
      .stApp {{ background: #f9f9f7; }}
      div[data-testid="stMetricValue"] {{ font-size: 1.9rem; }}
      .pill {{ display:inline-block; padding:2px 10px; border-radius:999px;
               font-size:12px; font-weight:600; }}
      .pill-done {{ background:#e6f4e6; color:#0b5c0b; }}
      .pill-todo {{ background:#f0efec; color:{theme.INK_MUTED}; }}
      .caption-note {{ color:{theme.INK_MUTED}; font-size:13px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def missing(what: str, stage: str) -> None:
    st.info(
        f"**{what}** has not been produced yet. "
        f"Run `python main.py --step {stage}` (or use **Run pipeline** in the "
        f"sidebar), then reload this page."
    )


def bar(data: pd.DataFrame, x: str, y: str, x_title: str, y_title: str,
        color: str | None = None, domain: list[str] | None = None,
        tooltip: list[str] | None = None, sort=None) -> alt.Chart:
    """Horizontal bar. One series gets one colour and no legend."""
    encode = {
        "x": alt.X(x, title=x_title, axis=alt.Axis(grid=True)),
        "y": alt.Y(y, title=y_title, sort=sort, axis=alt.Axis(grid=False)),
        "tooltip": tooltip or [y, x],
    }
    if color and domain:
        encode["color"] = alt.Color(color, title=None,
                                    scale=theme.color_scale(domain))
    chart = alt.Chart(data).mark_bar(
        height=18, cornerRadiusEnd=4,
    ).encode(**encode)
    if not color:
        chart = chart.mark_bar(height=18, cornerRadiusEnd=4,
                               color=theme.CATEGORICAL[0])
    return chart


def value_labels(data: pd.DataFrame, x: str, y: str, fmt: str = ".2f",
                 sort=None) -> alt.Chart:
    return alt.Chart(data).mark_text(
        align="left", dx=6, color=theme.INK_SECONDARY, fontSize=12,
    ).encode(
        x=alt.X(x), y=alt.Y(y, sort=sort), text=alt.Text(x, format=fmt),
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

PAGES = [
    "Overview",
    "Pipeline",
    "Dataset & labeling",
    "Models & accuracy",
    "Generated assets",
    "Optimization",
]

with st.sidebar:
    st.markdown("### Marketing Content Pipeline")
    st.caption("Research dashboard")
    page = st.radio("Section", PAGES, label_visibility="collapsed")

    st.divider()
    st.markdown("**Run pipeline**")
    stage_names = [s.name for s in artifacts.STAGES]
    chosen = st.multiselect("Stages", stage_names, default=[],
                            label_visibility="collapsed",
                            placeholder="Pick stages…")
    force = st.checkbox("Force rerun (`--force`)", value=False)
    if st.button("Run", type="primary", width="stretch",
                 disabled=not chosen):
        cmd = [sys.executable, "main.py", "--step", *chosen]
        if force:
            cmd.append("--force")
        with st.status(f"Running: {' '.join(cmd[1:])}", expanded=True) as status:
            log = st.empty()
            lines: list[str] = []
            process = subprocess.Popen(
                cmd, cwd=str(artifacts.ROOT), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            for line in process.stdout:  # type: ignore[union-attr]
                lines.append(line.rstrip())
                log.code("\n".join(lines[-40:]))
            code = process.wait()
            status.update(
                label=f"Finished with exit code {code}",
                state="complete" if code == 0 else "error",
            )


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def page_overview() -> None:
    st.title("Overview")
    st.caption(
        "One product URL in, ranked platform-specific marketing assets out — "
        "with the campaign strategy inferred rather than supplied."
    )

    done = sum(1 for s in artifacts.STAGES if s.done)
    metrics = artifacts.training_metrics()
    ranked = artifacts.read_csv(config.RANKED_CSV)
    training = artifacts.training_dataset()
    research = artifacts.research_dataset()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stages complete", f"{done} / {len(artifacts.STAGES)}")

    if research is not None and training is not None:
        c2.metric("Labeled rows", f"{len(research):,}",
                  help="Rows weak-labeled by the rule + BART-MNLI + Phi-3 ensemble")
        c3.metric("Rows past confidence gate", f"{len(training):,}",
                  delta=f"-{len(research) - len(training):,} filtered out",
                  delta_color="off")
    else:
        c2.metric("Labeled rows", "—")
        c3.metric("Rows past confidence gate", "—")

    if metrics:
        goal = next((r for r in metrics["results"]
                     if r["target"] == "campaign_goal"), None)
        c4.metric("Goal classifier accuracy",
                  f"{goal['accuracy']:.0%}" if goal else "—",
                  help="Held-out 20% split; see Models & accuracy")
    else:
        c4.metric("Goal classifier accuracy", "—")

    st.divider()

    left, right = st.columns([3, 2])

    with left:
        st.subheader("Pipeline input and output")
        st.markdown(
            """
| | |
|---|---|
| **Input** | `input.json` — product name, website URL, target audience, customer segment, preferred platforms |
| **Learned from** | RafaM97 marketing corpus (goal/tone supervision) and a 12,000-row engagement corpus |
| **Output** | `ranked_platform_assets.csv` and `optimized_ranked_platform_assets.csv` — one row per platform with caption, hashtags, CTA, creative prompt, three component scores and a composite score |
| **Evidence** | `before_after_optimization_comparison.csv`, `optimization_significance_test.csv` |

`campaign_goal` and `tone` are **never supplied by the user** — they are
predicted from the crawled site by classifiers trained on the labeled corpus.
That is the point of the system.
            """
        )

    with right:
        st.subheader("Composite score")
        st.markdown(
            f"""
```
final_score = {config.SEMANTIC_WEIGHT} × semantic_score
            + {config.PLATFORM_WEIGHT} × platform_suitability_score
            + {config.ENGAGEMENT_WEIGHT} × engagement_score
```
"""
        )
        weights = pd.DataFrame({
            "component": ["Engagement (learned)", "Semantic (embedding)",
                          "Platform fit (rules)"],
            "weight": [config.ENGAGEMENT_WEIGHT, config.SEMANTIC_WEIGHT,
                       config.PLATFORM_WEIGHT],
        })
        order = weights["component"].tolist()
        st.altair_chart(
            (bar(weights, "weight:Q", "component:N", "Weight", None,
                 sort=order, tooltip=["component", "weight"])
             + value_labels(weights, "weight:Q", "component:N", ".2f", sort=order)
             ).properties(height=140),
            width="stretch",
        )
        st.markdown(
            "<span class='caption-note'>The weights are a declared design "
            "choice, not a fitted result — see the caveat on the Models "
            "page.</span>", unsafe_allow_html=True,
        )

    if ranked is not None:
        st.divider()
        st.subheader("Current ranking")
        st.dataframe(
            ranked[["platform", "caption", "final_score"]]
            .style.format({"final_score": "{:.3f}"}),
            width="stretch", hide_index=True,
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def page_pipeline() -> None:
    st.title("Pipeline")
    st.caption(
        "A single linear pipeline of 16 stages. Stages hand off through files, "
        "so any stage can be rerun on its own."
    )

    rows = []
    for stage in artifacts.STAGES:
        finished = stage.finished_at
        rows.append({
            "Layer": stage.layer,
            "Stage": stage.name,
            "Does": stage.label,
            "Reads": stage.reads,
            "Writes": stage.writes,
            "Status": "complete" if stage.done else "not run",
            "Last written": finished.strftime("%Y-%m-%d %H:%M") if finished else "—",
        })
    table = pd.DataFrame(rows)

    for layer in ["Input", "Preparation", "Modeling", "Generation",
                  "Evaluation", "Validation"]:
        section = table[table["Layer"] == layer]
        if section.empty:
            continue
        complete = (section["Status"] == "complete").sum()
        st.markdown(f"#### {layer} · {complete}/{len(section)} complete")
        st.dataframe(
            section.drop(columns=["Layer"]), width="stretch",
            hide_index=True,
        )

    st.divider()
    st.subheader("Is there only one pipeline?")
    st.markdown(
        """
Yes — one pipeline, but it contains **three independently trained models** whose
training runs are separate sub-flows that converge on the generation path:

1. **Goal/tone supervision flow** — `preprocess-dataset → label-goal → label-tone
   → build-dataset → goal-tone-train`. Runs against the RafaM97 corpus. Produces
   two classifiers. Independent of any particular product.
2. **Engagement supervision flow** — `engagement-train`. Runs against the
   12,000-row engagement corpus. Produces one regressor. Also product-independent.
3. **Per-product inference flow** — `crawl → kb → goal-tone-predict → summary →
   generate → engagement-score → evaluate → optimize → significance`.
   This is the flow that runs for each new product.

Flows 1 and 2 are trained once and reused. Only flow 3 runs per product, which is
why `--step` exists: after the first full run you rerun flow 3 alone.
        """
    )


# ---------------------------------------------------------------------------
# Dataset & labeling
# ---------------------------------------------------------------------------

def page_dataset() -> None:
    st.title("Dataset & labeling")
    research = artifacts.research_dataset()
    training = artifacts.training_dataset()

    if research is None:
        missing("The labeled research corpus", "label-goal label-tone build-dataset")
        return

    st.caption(
        "Labels are produced by weak supervision: a keyword rule scorer, "
        "BART-MNLI zero-shot classification, and Phi-3 arbitration on "
        "low-confidence rows. No human-annotated gold set exists in this "
        "repository."
    )

    total = len(research)
    valid = int(research["valid_label_pair"].sum()) if "valid_label_pair" in research else total
    kept = len(training) if training is not None else 0

    funnel = pd.DataFrame({
        "stage": ["Weak-labeled", "Valid goal+tone pair", "Passed confidence gate"],
        "rows": [total, valid, kept],
    })
    order = funnel["stage"].tolist()

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("From corpus to training set")
        st.altair_chart(
            (alt.Chart(funnel).mark_bar(height=26, cornerRadiusEnd=4).encode(
                x=alt.X("rows:Q", title="Rows"),
                y=alt.Y("stage:N", title=None, sort=order, axis=alt.Axis(grid=False)),
                color=alt.Color("stage:N", sort=order, legend=None,
                                scale=alt.Scale(domain=order,
                                                range=["#86b6ef", "#3987e5", "#1c5cab"])),
                tooltip=["stage", "rows"],
            ) + value_labels(funnel, "rows:Q", "stage:N", ",.0f", sort=order)
            ).properties(height=170),
            width="stretch",
        )
    with c2:
        st.subheader("Retention")
        st.metric("Kept for training", f"{kept:,} of {total:,}",
                  delta=f"{kept / total - 1:.0%}", delta_color="off")
        st.markdown(
            "<span class='caption-note'>The confidence gate is the largest "
            "single reduction in the pipeline. It buys label precision at the "
            "cost of training-set size and class coverage — which is exactly "
            "what the per-class scores on the next page reflect.</span>",
            unsafe_allow_html=True,
        )

    st.divider()

    c1, c2 = st.columns(2)
    for column, target, container in (("campaign_goal", "Campaign goal", c1),
                                      ("tone", "Tone", c2)):
        with container:
            st.subheader(f"{target} distribution")
            frames = []
            if column in research:
                counts = research[column].value_counts().reset_index()
                counts.columns = ["label", "rows"]
                counts["set"] = "Weak-labeled corpus"
                frames.append(counts)
            if training is not None and column in training:
                counts = training[column].value_counts().reset_index()
                counts.columns = ["label", "rows"]
                counts["set"] = "Training set"
                frames.append(counts)
            if not frames:
                continue
            data = pd.concat(frames, ignore_index=True)
            domain = ["Weak-labeled corpus", "Training set"]
            st.altair_chart(
                alt.Chart(data).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X("rows:Q", title="Rows"),
                    y=alt.Y("label:N", title=None, axis=alt.Axis(grid=False),
                            sort="-x"),
                    yOffset=alt.YOffset("set:N", sort=domain),
                    color=alt.Color("set:N", title=None,
                                    scale=theme.color_scale(domain)),
                    tooltip=["label", "set", "rows"],
                ).properties(height=240),
                width="stretch",
            )

    st.divider()
    st.subheader("Which method decided the label")
    c1, c2 = st.columns(2)
    for column, target, container in (("campaign_goal_source", "Campaign goal", c1),
                                      ("tone_source", "Tone", c2)):
        if column not in research:
            continue
        with container:
            counts = research[column].value_counts().reset_index()
            counts.columns = ["source", "rows"]
            order = counts["source"].tolist()
            st.altair_chart(
                (bar(counts, "rows:Q", "source:N", "Rows", target, sort="-x",
                     tooltip=["source", "rows"])
                 + value_labels(counts, "rows:Q", "source:N", ",.0f", sort="-x")
                 ).properties(height=max(140, 34 * len(counts))),
                width="stretch",
            )

    st.divider()
    st.subheader("Joint label confidence")
    if "joint_label_confidence" in research:
        st.altair_chart(
            alt.Chart(research).mark_bar(color=theme.CATEGORICAL[0]).encode(
                x=alt.X("joint_label_confidence:Q", bin=alt.Bin(maxbins=40),
                        title="Joint label confidence"),
                y=alt.Y("count()", title="Rows"),
                tooltip=[alt.Tooltip("count()", title="Rows")],
            ).properties(height=220),
            width="stretch",
        )
        flagged = int(research["needs_review"].sum()) if "needs_review" in research else 0
        st.markdown(
            f"<span class='caption-note'>{flagged:,} rows are flagged "
            f"<code>needs_review</code> — below the confidence or inter-method "
            f"agreement floor. Those thresholds "
            f"(<code>TONE_MIN_CONFIDENCE={config.TONE_MIN_CONFIDENCE}</code>, "
            f"<code>TONE_MIN_AGREEMENT={config.TONE_MIN_AGREEMENT}</code>) are "
            f"declared operating points, not values tuned against a gold "
            f"sample.</span>", unsafe_allow_html=True,
        )

    with st.expander("Inspect labeled rows"):
        cols = [c for c in ["row_id", "text", "campaign_goal", "tone",
                            "campaign_goal_source", "tone_source",
                            "joint_label_confidence", "needs_review"]
                if c in research]
        st.dataframe(research[cols], width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Models & accuracy
# ---------------------------------------------------------------------------

def page_models() -> None:
    st.title("Models & accuracy")
    metrics = artifacts.training_metrics()

    st.subheader("How accuracy is actually calculated")
    st.markdown(
        """
Three different things in this project are called a "score". Only the first is
accuracy in the classification sense.

**1. Classifier accuracy (goal + tone).** A stratified 20% held-out split of the
gated training set. `accuracy_score`, plus weighted and macro F1 and a full
per-class report. Model selection is by **weighted F1**, not accuracy. The
critical caveat: the labels being scored against were produced by the weak
supervision ensemble, so this measures *agreement with the weak labeller*, not
correctness. There is no human-annotated gold set in this repository.

**2. Engagement regression quality.** A 20% held-out split of the engagement
corpus, scored by MAE, RMSE and R². Selection is by **R²**. This is a
regression fit, not an accuracy.

**3. Composite asset score.** Not measured against any ground truth at all — it
is a weighted sum of an embedding cosine similarity, a rule checklist pass rate,
and a model-predicted engagement rate. It is a ranking heuristic. Calling it
"accuracy" would be wrong.
        """
    )

    if metrics is None:
        missing("Training metrics", "goal-tone-train")
    else:
        st.divider()
        st.subheader("Goal / tone classifier selection")
        st.caption(
            f"Trained on {metrics['dataset_rows']} rows. "
            f"Selected: goal → `{metrics['selection']['best_goal_model_type']}`, "
            f"tone → `{metrics['selection']['best_tone_model_type']}`."
        )

        summary = pd.DataFrame([
            {"Target": r["target"], "Model": r["model"],
             "Accuracy": r["accuracy"], "Weighted F1": r["weighted_f1"],
             "Macro F1": r["macro_f1"]}
            for r in metrics["results"]
        ])
        st.dataframe(
            summary.style.format({"Accuracy": "{:.3f}", "Weighted F1": "{:.3f}",
                                  "Macro F1": "{:.3f}"}),
            width="stretch", hide_index=True,
        )

        if len(summary) < 4:
            st.warning(
                "Only one model type appears in the results. The "
                "Sentence-BERT + XGBoost arm was skipped "
                "(`GOAL_TONE_SKIP_XGBOOST`), so the reported \"best of two\" "
                "selection compared one candidate. Rerun with both arms before "
                "reporting this as a model comparison."
            )

        st.divider()
        st.subheader("Per-class performance")
        st.caption(
            "Weighted F1 hides class collapse. The per-class view is the one to "
            "report."
        )
        for result in metrics["results"]:
            report = result["classification_report"]
            rows = [
                {"class": name, "F1": vals["f1-score"],
                 "precision": vals["precision"], "recall": vals["recall"],
                 "support": vals["support"]}
                for name, vals in report.items()
                if isinstance(vals, dict) and name not in
                {"macro avg", "weighted avg"}
            ]
            if not rows:
                continue
            data = pd.DataFrame(rows).sort_values("support", ascending=False)
            order = data["class"].tolist()

            st.markdown(f"**{result['target']}** · {result['model']}")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.altair_chart(
                    (alt.Chart(data).mark_bar(
                        height=18, cornerRadiusEnd=4,
                        color=theme.CATEGORICAL[0],
                    ).encode(
                        x=alt.X("F1:Q", title="F1", scale=alt.Scale(domain=[0, 1])),
                        y=alt.Y("class:N", title=None, sort=order,
                                axis=alt.Axis(grid=False)),
                        tooltip=["class", alt.Tooltip("F1", format=".3f"),
                                 alt.Tooltip("precision", format=".3f"),
                                 alt.Tooltip("recall", format=".3f"), "support"],
                    ) + value_labels(data, "F1:Q", "class:N", ".2f", sort=order)
                    ).properties(height=max(120, 34 * len(data))),
                    width="stretch",
                )
            with c2:
                st.dataframe(
                    data.style.format({"F1": "{:.3f}", "precision": "{:.3f}",
                                       "recall": "{:.3f}", "support": "{:.0f}"}),
                    width="stretch", hide_index=True,
                )

            thin = data[data["support"] <= 2]
            if not thin.empty:
                names = ", ".join(f"`{c}` (n={int(s)})" for c, s in
                                  zip(thin["class"], thin["support"]))
                st.markdown(
                    f"<span class='caption-note'>⚠ Classes with a test support "
                    f"of 2 or fewer: {names}. A single prediction moves these "
                    f"F1 values by 0.5 or more — they carry no statistical "
                    f"weight and should be reported as such.</span>",
                    unsafe_allow_html=True,
                )
            st.write("")

    st.divider()
    st.subheader("Engagement regressor selection")
    comparison = artifacts.engagement_comparison()
    if comparison is None:
        missing("The engagement model comparison", "engagement-train")
    else:
        st.dataframe(
            comparison.style.format({"MAE": "{:.5f}", "RMSE": "{:.5f}",
                                     "R2": "{:.4f}"}),
            width="stretch", hide_index=True,
        )
        melted = comparison.melt(id_vars="model", value_vars=["MAE", "RMSE"],
                                 var_name="metric", value_name="value")
        domain = comparison["model"].tolist()
        c1, c2 = st.columns(2)
        with c1:
            st.altair_chart(
                alt.Chart(melted).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X("value:Q", title="Error (lower is better)"),
                    y=alt.Y("metric:N", title=None, axis=alt.Axis(grid=False)),
                    yOffset=alt.YOffset("model:N", sort=domain),
                    color=alt.Color("model:N", title=None,
                                    scale=theme.color_scale(domain)),
                    tooltip=["model", "metric", alt.Tooltip("value", format=".5f")],
                ).properties(height=180),
                width="stretch",
            )
        with c2:
            st.altair_chart(
                (alt.Chart(comparison).mark_bar(
                    height=22, cornerRadiusEnd=4).encode(
                    x=alt.X("R2:Q", title="R² (higher is better)"),
                    y=alt.Y("model:N", title=None, sort=domain,
                            axis=alt.Axis(grid=False)),
                    color=alt.Color("model:N", title=None, legend=None,
                                    scale=theme.color_scale(domain)),
                    tooltip=["model", alt.Tooltip("R2", format=".4f")],
                ) + value_labels(comparison, "R2:Q", "model:N", ".3f", sort=domain)
                ).properties(height=180),
                width="stretch",
            )

    st.divider()
    st.subheader("Model choices")
    st.dataframe(pd.DataFrame([
        {"Role": "Summarization", "Chosen": config.SUMMARIZATION_MODEL_NAME,
         "Compared against": "Pegasus, T5, extractive baseline",
         "Selection basis": "Declared design choice — not benchmarked in this repo"},
        {"Role": "Generation", "Chosen": config.GENERATION_MODEL_NAME,
         "Compared against": "Mistral-7B, Llama-3-8B, GPT-class APIs",
         "Selection basis": "Declared — fits 16 GB unified memory at fp16"},
        {"Role": "Semantic similarity", "Chosen": config.SEMANTIC_MODEL_NAME,
         "Compared against": "MPNet, larger SBERT variants",
         "Selection basis": "Declared — speed/quality tradeoff"},
        {"Role": "Zero-shot labeling", "Chosen": config.DATA_FINETUNE_MODEL_NAME,
         "Compared against": "keyword rules, Phi-3 direct",
         "Selection basis": "Used together as an ensemble, not selected between"},
        {"Role": "Goal/tone classifier", "Chosen": "TF-IDF + Logistic Regression",
         "Compared against": "Sentence-BERT + XGBoost",
         "Selection basis": "Empirical — highest weighted F1 on held-out split"},
        {"Role": "Engagement regressor", "Chosen": "best of RF / XGBoost",
         "Compared against": "each other",
         "Selection basis": "Empirical — highest R² on held-out split"},
    ]), width="stretch", hide_index=True)
    st.markdown(
        "<span class='caption-note'>Only the last two rows are empirical "
        "selections. The four transformer choices are justified by argument and "
        "hardware fit, not by an ablation run inside this project — state them "
        "that way in the write-up.</span>", unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Generated assets
# ---------------------------------------------------------------------------

def page_assets() -> None:
    st.title("Generated assets")
    ranked = artifacts.read_csv(config.RANKED_CSV)
    if ranked is None:
        missing("Ranked assets", "generate engagement-score evaluate")
        return

    summary = artifacts.read_json(config.SUMMARY_JSON) or {}
    if summary:
        c1, c2, c3 = st.columns(3)
        c1.metric("Product", summary.get("product_name", "—"))
        c2.metric("Inferred campaign goal", summary.get("campaign_goal", "—"))
        c3.metric("Inferred tone", summary.get("tone", "—"))
        with st.expander("Business summary given to the generator"):
            st.write(summary.get("summary", ""))

    st.divider()
    st.subheader("Composite score by platform")
    st.caption("Segments are each component's weighted contribution — they sum "
               "to the final score.")

    parts = []
    for _, row in ranked.iterrows():
        parts += [
            {"platform": row["platform"], "component": "Semantic",
             "contribution": config.SEMANTIC_WEIGHT * row["semantic_score"],
             "raw": row["semantic_score"]},
            {"platform": row["platform"], "component": "Platform fit",
             "contribution": config.PLATFORM_WEIGHT * row["platform_suitability_score"],
             "raw": row["platform_suitability_score"]},
            {"platform": row["platform"], "component": "Engagement",
             "contribution": config.ENGAGEMENT_WEIGHT * row["engagement_score"],
             "raw": row["engagement_score"]},
        ]
    stacked = pd.DataFrame(parts)
    domain = ["Semantic", "Platform fit", "Engagement"]
    order = ranked.sort_values("final_score", ascending=False)["platform"].tolist()

    st.altair_chart(
        alt.Chart(stacked).mark_bar(height=26, cornerRadiusEnd=4,
                                    stroke=theme.SURFACE, strokeWidth=2).encode(
            x=alt.X("contribution:Q", title="Weighted contribution to final score",
                    stack="zero"),
            y=alt.Y("platform:N", title=None, sort=order, axis=alt.Axis(grid=False)),
            color=alt.Color("component:N", title=None, sort=domain,
                            scale=theme.color_scale(domain)),
            tooltip=["platform", "component",
                     alt.Tooltip("raw", format=".3f", title="Raw score"),
                     alt.Tooltip("contribution", format=".3f", title="Weighted")],
        ).properties(height=max(160, 46 * len(order))),
        width="stretch",
    )

    st.markdown(
        "<span class='caption-note'>⚠ <code>engagement_score</code> is min-max "
        "normalized <em>across this asset set only</em>. With four assets the "
        "best always scores 1.0 and the worst always 0.0, whatever the "
        "underlying predicted rates are. It measures rank within the batch, not "
        "absolute engagement — and it carries the largest weight.</span>",
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("Assets")
    for _, row in ranked.iterrows():
        with st.expander(
            f"{str(row['platform']).upper()} · final score "
            f"{row['final_score']:.3f}"
        ):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown("**Caption**")
                st.write(row.get("caption", ""))
                st.markdown("**CTA**")
                st.write(row.get("cta", ""))
                st.markdown("**Hashtags**")
                st.write(row.get("hashtags", ""))
                creative = row.get("image_prompt") or row.get("shorts_prompt")
                if isinstance(creative, str) and creative.strip():
                    st.markdown("**Creative prompt**")
                    st.write(creative)
            with c2:
                st.metric("Semantic", f"{row['semantic_score']:.3f}")
                st.metric("Platform fit", f"{row['platform_suitability_score']:.3f}")
                st.metric("Engagement", f"{row['engagement_score']:.3f}")

    with st.expander("Raw table"):
        st.dataframe(ranked, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------

def page_optimization() -> None:
    st.title("Optimization")
    comparison = artifacts.read_csv(config.COMPARISON_CSV)
    if comparison is None:
        missing("The before/after comparison", "optimize")
        return

    st.caption(
        "Each asset is re-prompted with one corrective rule chosen by whichever "
        "component score fell below its threshold, then re-scored through the "
        "identical pipeline."
    )

    mean_delta = comparison["final_score_change"].mean()
    improved = int((comparison["final_score_change"] > 0).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Mean change in final score", f"{mean_delta:+.4f}")
    c2.metric("Assets improved", f"{improved} / {len(comparison)}")

    significance = artifacts.read_csv(config.SIGNIFICANCE_CSV)
    if significance is not None and not significance.empty:
        p = float(significance.iloc[0]["p_value"])
        c3.metric("Paired t-test p-value", f"{p:.4f}",
                  delta="significant" if p < 0.05 else "not significant",
                  delta_color="normal" if p < 0.05 else "off")

    st.divider()
    st.subheader("Before vs after")

    melted = comparison.melt(
        id_vars="platform",
        value_vars=["before_final_score", "after_final_score"],
        var_name="phase", value_name="score",
    )
    melted["phase"] = melted["phase"].map({
        "before_final_score": "Before", "after_final_score": "After"})
    domain = ["Before", "After"]
    order = comparison.sort_values("after_final_score",
                                   ascending=False)["platform"].tolist()

    st.altair_chart(
        alt.Chart(melted).mark_bar(cornerRadiusEnd=4, stroke=theme.SURFACE,
                                   strokeWidth=2).encode(
            x=alt.X("score:Q", title="Final score"),
            y=alt.Y("platform:N", title=None, sort=order, axis=alt.Axis(grid=False)),
            yOffset=alt.YOffset("phase:N", sort=domain),
            color=alt.Color("phase:N", title=None, sort=domain,
                            scale=theme.color_scale(domain)),
            tooltip=["platform", "phase", alt.Tooltip("score", format=".3f")],
        ).properties(height=max(180, 60 * len(order))),
        width="stretch",
    )

    st.subheader("Change by component")
    changes = comparison.melt(
        id_vars="platform",
        value_vars=["semantic_change", "platform_change", "engagement_change"],
        var_name="component", value_name="change",
    )
    changes["component"] = changes["component"].map({
        "semantic_change": "Semantic", "platform_change": "Platform fit",
        "engagement_change": "Engagement"})
    st.altair_chart(
        alt.Chart(changes).mark_bar(cornerRadiusEnd=4, stroke=theme.SURFACE,
                                    strokeWidth=2).encode(
            x=alt.X("change:Q", title="Change after optimization"),
            y=alt.Y("platform:N", title=None, sort=order, axis=alt.Axis(grid=False)),
            yOffset=alt.YOffset("component:N"),
            color=alt.Color("component:N", title=None,
                            scale=theme.color_scale(
                                ["Semantic", "Platform fit", "Engagement"])),
            tooltip=["platform", "component", alt.Tooltip("change", format=".3f")],
        ).properties(height=max(200, 74 * len(order))),
        width="stretch",
    )

    if significance is not None and not significance.empty:
        st.divider()
        st.subheader("Statistical validation")
        st.dataframe(significance, width="stretch", hide_index=True)
        st.markdown(
            f"<span class='caption-note'>⚠ The paired t-test runs on "
            f"n={len(comparison)} pairs — one per platform. At that sample size "
            f"the test has almost no power, the normality assumption is "
            f"untestable, and a p-value either way is not evidence. To make this "
            f"a real result, repeat the whole per-product flow over many products "
            f"and pair at the product level.</span>",
            unsafe_allow_html=True,
        )

    with st.expander("Comparison table"):
        st.dataframe(comparison, width="stretch", hide_index=True)

    optimized = artifacts.read_csv(config.OPTIMIZED_RANKED_CSV)
    if optimized is not None and "optimization_rule" in optimized:
        with st.expander("Rules that fired"):
            st.dataframe(optimized[["platform", "optimization_rule", "caption"]],
                         width="stretch", hide_index=True)


PAGE_FUNCTIONS = {
    "Overview": page_overview,
    "Pipeline": page_pipeline,
    "Dataset & labeling": page_dataset,
    "Models & accuracy": page_models,
    "Generated assets": page_assets,
    "Optimization": page_optimization,
}

PAGE_FUNCTIONS[page]()
