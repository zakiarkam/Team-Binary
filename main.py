"""CLI orchestrator.

Examples
--------
python main.py                       # run full pipeline, skip stages whose outputs exist
python main.py --force               # rerun everything
python main.py --step crawl          # run only the crawl stage
python main.py --step engagement-train optimize  # run specific stages
python main.py --list                # show stage names
"""

import argparse
import json
import sys

import config
import pipeline_cache
from datetime import datetime

STAGES = [
    "crawl",
    "kb",
    "preprocess-dataset",
    "label-goal",
    "label-tone",
    "build-dataset", # end
    "goal-tone-train",
    "goal-tone-predict",
    "summary",
    "generate",
    "engagement-train",
    "engagement-score",
    "evaluate",
    "optimize",
    "significance",
    "human-baseline",
]

# Opt-in stages for the adaptive engagement-learning subsystem (learning/).
# Deliberately NOT part of the default STAGES sequence: a plain `python main.py`
# never runs them, so the existing pipeline is unaffected. They are selectable
# only via `--step`.
LEARNING_STAGES = [
    "feedback-log",       # record generated/ranked assets + predictions into the store
    "feedback-import",    # ingest analytics CSV exports → observed engagement
    "engagement-retrain", # retrain the personalized predictor on base + feedback
    "generate-candidates",# best-of-N generation ranked by the personalized model
]

ALL_STAGES = STAGES + LEARNING_STAGES


def _load_input() -> dict:
    with open(config.ROOT / "input.json", encoding="utf-8") as f:
        return json.load(f)


config.init_dirs()


def _exists(path) -> bool:
    return path.exists()

def _calculate_pipeline_hash(module_input: dict) -> str:
    """
    Create SHA256 hash from important business inputs.
    """

    return pipeline_cache.calculate_hash(
        module_input,
        config.PIPELINE_HASH_FIELDS
    )


def run_pipeline(stages: list[str], force: bool = False):
    module_input = _load_input()

    current_hash = _calculate_pipeline_hash(
        module_input
    )

    previous_hash = pipeline_cache.load_hash(
        config.PIPELINE_METADATA_JSON
    )
    
    cache_changed = (
        previous_hash is None
        or previous_hash != current_hash
    )
    
    if cache_changed:

        print("[cache] input changed")

        # delete downstream cache files
        pipeline_cache.invalidate("crawl")

        # remove metadata
        pipeline_cache.clear_metadata(
            config.PIPELINE_METADATA_JSON
        )

        pipeline_cache.save_hash(
            config.PIPELINE_METADATA_JSON,
            current_hash
        )

    else:
        print(
            "[cache] input unchanged - "
            "using stage cache"
        )

    upstream_changed = cache_changed
    
    # Stage outputs we may reuse
    website_data = None
    kb = None
    marketing_summary = None
    generated_df = None
    ranked_df = None
    optimized_ranked = None
    comparison = None

    if "crawl" in stages:
        import crawler
        if force  or cache_changed or not _exists(config.CRAWL_JSON):
            website_data = crawler.run(module_input)
        else:
            # print(f"[skip] crawl ({config.CRAWL_JSON.name} exists)")
            print(
                f"[cache-hit] crawl "
                f"({config.CRAWL_JSON.name})"
            )
            website_data = crawler.load_cached()

    if "kb" in stages:
        import crawler, knowledge_base
        kb_reran = False
        if website_data is None:
            website_data = crawler.load_cached()
        if force or upstream_changed or not _exists(config.KB_JSON):
            kb = knowledge_base.run(
                website_data,
                module_input
            )
            kb_reran = True
        else:
            print("[cache-hit] kb")
            kb = knowledge_base.load_cached()

        upstream_changed = upstream_changed or kb_reran

    # These stages own argparse CLIs of their own. Called with no argument they
    # would parse main.py's argv and abort on --step/--force, so pass an empty
    # list and forward only the flags they understand.
    if "preprocess-dataset" in stages:
        from dataset import preprocess_marketing
        if force or not config.PREPROCESSED_DATASET_CSV.exists():
            preprocess_marketing.run([])
        else:
            print("[cache-hit] preprocess-dataset")

    if "label-goal" in stages:
        from dataset import label_campaign_goal
        label_campaign_goal.run(["--force"] if force else [])

    if "label-tone" in stages:
        from dataset import label_tone
        label_tone.run(["--force"] if force else [])

    if "build-dataset" in stages:
        from dataset import build_final_dataset
        if force or not config.LABELED_DATASET_CSV.exists():
            build_final_dataset.run([])
        else:
            print("[cache-hit] build-dataset")

    if "goal-tone-train" in stages:
        import goal_tone

        # Ensure the labeled dataset exists before training
        if not config.LABELED_DATASET_CSV.exists():
            raise FileNotFoundError(
                "Labeled dataset not found.\n"
                "Run the following stages first:\n"
                "  preprocess-dataset\n"
                "  label-goal\n"
                "  label-tone\n"
                "  build-dataset"
            )

        if force or not _exists(config.GOAL_TONE_SELECTION_JSON):
            goal_tone.train()
        else:
            print(f"[skip] goal-tone-train ({config.GOAL_TONE_SELECTION_JSON.name} exists)")

    if "goal-tone-predict" in stages:
        import knowledge_base, goal_tone

        if kb is None:
            kb = knowledge_base.load_cached()

        goal_predict_reran = False

        if force or upstream_changed:

            module_input, kb = goal_tone.predict(
                kb,
                module_input,
            )

            goal_predict_reran = True

            # Save updated KB
            with open(config.KB_JSON, "w", encoding="utf-8") as f:
                json.dump(
                    kb,
                    f,
                    indent=4,
                    ensure_ascii=False,
                )

            # Recalculate pipeline hash because prediction may update
            # campaign_goal and tone.
            new_hash = _calculate_pipeline_hash(module_input)

            if new_hash != current_hash:

                print("[cache] campaign goal or tone changed")

                pipeline_cache.invalidate("goal-tone-predict")

                current_hash = new_hash

                pipeline_cache.save_hash(
                    config.PIPELINE_METADATA_JSON,
                    current_hash,
                )

        else:
            print("[cache-hit] goal-tone-predict")

        upstream_changed = upstream_changed or goal_predict_reran

    if "summary" in stages:
        import knowledge_base, summary
        if kb is None:
            kb = knowledge_base.load_cached()
        summary_reran = False
        if force or upstream_changed or not _exists(config.SUMMARY_JSON):
            marketing_summary = summary.run(kb)
            summary_reran = True
        else:
            print("[cache-hit] summary")
            marketing_summary = summary.load_cached()

        upstream_changed = upstream_changed or summary_reran

    if "generate" in stages:
        import summary, generator
        if marketing_summary is None:
            marketing_summary = summary.load_cached()
        generate_reran = False

        if force or upstream_changed or not _exists(config.GENERATED_CSV):
            generated_df = generator.run(marketing_summary)
            generate_reran = True
        else:
            print("[cache-hit] generate")
            generated_df = generator.load_cached()

        upstream_changed = upstream_changed or generate_reran

    if "engagement-train" in stages:
        import engagement
        if force or not _exists(config.ENGAGEMENT_MODEL_PKL):
            engagement.train()
        else:
            print(f"[skip] engagement-train ({config.ENGAGEMENT_MODEL_PKL.name} exists)")

    if "engagement-score" in stages:
        import generator, engagement
        if generated_df is None:
            generated_df = generator.load_cached()
        generated_df = engagement.score(generated_df)

    if "evaluate" in stages:
        import generator, engagement, summary, evaluation
        if marketing_summary is None:
            marketing_summary = summary.load_cached()
        if generated_df is None:
            generated_df = generator.load_cached()
        if "engagement_score" not in generated_df.columns:
            generated_df = engagement.score(generated_df)
        evaluation_reran = False

        if force or upstream_changed or not _exists(config.RANKED_CSV):
            ranked_df = evaluation.run(
                generated_df,
                marketing_summary
            )
            evaluation_reran = True
        else:
            print("[cache-hit] evaluate")
            ranked_df = evaluation.load_cached()

        upstream_changed = upstream_changed or evaluation_reran

    if "optimize" in stages:
        import evaluation, summary, optimization
        if marketing_summary is None:
            marketing_summary = summary.load_cached()
        if ranked_df is None:
            ranked_df = evaluation.load_cached()
        optimization_reran = False

        if force or upstream_changed or not _exists(config.OPTIMIZED_RANKED_CSV):
            optimized_ranked, comparison = optimization.run(
                ranked_df,
                marketing_summary
            )
            optimization_reran = True
        else:
            print("[cache-hit] optimize")
            optimized_ranked, comparison = optimization.load_cached()

        upstream_changed = upstream_changed or optimization_reran

    if "significance" in stages:
        import optimization, significance
        if comparison is None:
            _, comparison = optimization.load_cached()
        significance.run(comparison)

    if "human-baseline" in stages:
        import summary, evaluation, optimization, human_baseline
        if marketing_summary is None:
            marketing_summary = summary.load_cached()
        if ranked_df is None:
            ranked_df = evaluation.load_cached()
        if optimized_ranked is None:
            optimized_ranked, _ = optimization.load_cached()
        try:
            human_baseline.run(marketing_summary, ranked_df, optimized_ranked)
        except human_baseline.MissingHumanDataset as exc:
            # This is the last stage and an optional benchmark. Aborting the run
            # here would discard everything the expensive generation stages just
            # produced, so report it and exit cleanly instead.
            print(f"\n[skip] human-baseline — {exc}")

    # -----------------------------------------------------------------------
    # Opt-in engagement-learning stages (learning/). Never in the default run.
    # -----------------------------------------------------------------------
    if "feedback-log" in stages:
        import pandas as pd
        from learning import feedback_store
        import evaluation, optimization
        account_id = module_input.get("account_id")
        logged = 0
        # Log whichever scored asset sets exist, tagging each with its source.
        for csv_path, source, loader in (
            (config.RANKED_CSV, "generated", evaluation.load_cached),
            (config.OPTIMIZED_RANKED_CSV, "optimized",
             lambda: optimization.load_cached()[0]),
            (config.BEST_CANDIDATES_CSV, "candidate",
             lambda: pd.read_csv(config.BEST_CANDIDATES_CSV)),
        ):
            if _exists(csv_path):
                logged += feedback_store.log_assets(
                    loader(), account_id=account_id, source=source
                )
        print(f"[feedback-log] recorded {logged} asset(s) → {config.FEEDBACK_DB.name}")
        print(f"[feedback-log] store summary: {feedback_store.summary()}")

    if "feedback-import" in stages:
        from learning import importer, feedback_store
        account_id = module_input.get("account_id")
        reports = importer.import_dir(account_id=account_id)
        if not reports:
            print(f"[feedback-import] no CSVs found in "
                  f"{config.ANALYTICS_IMPORT_DIR}. Drop platform Insights "
                  f"exports there and rerun.")
        for report in reports:
            print(f"[feedback-import] {report}")
        print(f"[feedback-import] store summary: {feedback_store.summary()}")

    if "engagement-retrain" in stages:
        from learning import personalize
        if force or not _exists(config.PERSONALIZED_ENGAGEMENT_MODEL_PKL):
            personalize.retrain()
        else:
            print(f"[skip] engagement-retrain "
                  f"({config.PERSONALIZED_ENGAGEMENT_MODEL_PKL.name} exists)")

    if "generate-candidates" in stages:
        import summary
        from learning import candidates
        if marketing_summary is None:
            marketing_summary = summary.load_cached()
        account_id = module_input.get("account_id")
        if force or not _exists(config.BEST_CANDIDATES_CSV):
            candidates.run(marketing_summary, account_id=account_id)
        else:
            print(f"[skip] generate-candidates "
                  f"({config.BEST_CANDIDATES_CSV.name} exists)")
    
    pipeline_cache.save_stage_metadata(
        config.PIPELINE_METADATA_JSON,
        {
            "hash": current_hash,
            "completed_stages": stages,
            "last_run": str(datetime.now())
        }
    )


def main():
    p = argparse.ArgumentParser(description="Marketing content pipeline.")
    p.add_argument("--step", nargs="+", choices=ALL_STAGES, metavar="STAGE",
                   help="Run only these stages (see --list for names).")
    p.add_argument("--force", action="store_true", help="Rerun stages even if outputs exist.")
    p.add_argument("--list", action="store_true", help="List stages and exit.")
    args = p.parse_args()

    if args.list:
        print("# core pipeline (default run)")
        for s in STAGES:
            print(s)
        print("\n# opt-in engagement-learning stages (run only via --step)")
        for s in LEARNING_STAGES:
            print(s)
        sys.exit(0)

    # No --step → the default sequence only. Learning stages must be requested.
    run_pipeline(args.step or STAGES, force=args.force)


if __name__ == "__main__":
    main()
