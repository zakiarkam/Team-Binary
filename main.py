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


def _load_input() -> dict:
    with open(config.ROOT / "input.json", encoding="utf-8") as f:
        return json.load(f)


config.init_dirs()


def _exists(path) -> bool:
    return path.exists()


def run_pipeline(stages: list[str], force: bool = False):
    module_input = _load_input()

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
        if force or not _exists(config.CRAWL_JSON):
            website_data = crawler.run(module_input)
        else:
            print(f"[skip] crawl ({config.CRAWL_JSON.name} exists)")
            website_data = crawler.load_cached()

    if "kb" in stages:
        import crawler, knowledge_base
        if website_data is None:
            website_data = crawler.load_cached()
        if force or not _exists(config.KB_JSON):
            kb = knowledge_base.run(website_data, module_input)
        else:
            print(f"[skip] kb ({config.KB_JSON.name} exists)")
            kb = knowledge_base.load_cached()

    # These stages own argparse CLIs of their own. Called with no argument they
    # would parse main.py's argv and abort on --step/--force, so pass an empty
    # list and forward only the flags they understand.
    if "preprocess-dataset" in stages:
        from dataset import preprocess_marketing
        preprocess_marketing.run([])

    if "label-goal" in stages:
        from dataset import label_campaign_goal
        label_campaign_goal.run(["--force"] if force else [])

    if "label-tone" in stages:
        from dataset import label_tone
        label_tone.run(["--force"] if force else [])

    if "build-dataset" in stages:
        from dataset import build_final_dataset
        build_final_dataset.run([])

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
        module_input, kb = goal_tone.predict(kb, module_input)
        # Persist updated KB
        with open(config.KB_JSON, "w", encoding="utf-8") as f:
            json.dump(kb, f, indent=4, ensure_ascii=False)

    if "summary" in stages:
        import knowledge_base, summary
        if kb is None:
            kb = knowledge_base.load_cached()
        if force or not _exists(config.SUMMARY_JSON):
            marketing_summary = summary.run(kb)
        else:
            print(f"[skip] summary ({config.SUMMARY_JSON.name} exists)")
            marketing_summary = summary.load_cached()

    if "generate" in stages:
        import summary, generator
        if marketing_summary is None:
            marketing_summary = summary.load_cached()
        if force or not _exists(config.GENERATED_CSV):
            generated_df = generator.run(marketing_summary)
        else:
            print(f"[skip] generate ({config.GENERATED_CSV.name} exists)")
            generated_df = generator.load_cached()

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
        if force or not _exists(config.RANKED_CSV):
            ranked_df = evaluation.run(generated_df, marketing_summary)
        else:
            print(f"[skip] evaluate ({config.RANKED_CSV.name} exists)")
            ranked_df = evaluation.load_cached()

    if "optimize" in stages:
        import evaluation, summary, optimization
        if marketing_summary is None:
            marketing_summary = summary.load_cached()
        if ranked_df is None:
            ranked_df = evaluation.load_cached()
        if force or not _exists(config.OPTIMIZED_RANKED_CSV):
            optimized_ranked, comparison = optimization.run(ranked_df, marketing_summary)
        else:
            print(f"[skip] optimize ({config.OPTIMIZED_RANKED_CSV.name} exists)")
            optimized_ranked, comparison = optimization.load_cached()

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
        human_baseline.run(marketing_summary, ranked_df, optimized_ranked)


def main():
    p = argparse.ArgumentParser(description="Marketing content pipeline.")
    p.add_argument("--step", nargs="+", choices=STAGES, help="Run only these stages.")
    p.add_argument("--force", action="store_true", help="Rerun stages even if outputs exist.")
    p.add_argument("--list", action="store_true", help="List stages and exit.")
    args = p.parse_args()

    if args.list:
        for s in STAGES:
            print(s)
        sys.exit(0)

    run_pipeline(args.step or STAGES, force=args.force)


if __name__ == "__main__":
    main()
