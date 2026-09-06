"""pipeline.py — Orchestrate the full analytics run (Phase 7)."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd


def run_full(
    simulated_dir: Path = Path("data/simulated/"),
    processed_dir: Path = Path("data/processed/"),
    models_dir:    Path = Path("outputs/models/"),
    reports_dir:   Path = Path("outputs/reports/"),
    figures_dir:   Path = Path("outputs/figures/"),
    n_users: int = 10000,
    regenerate: bool = False,
) -> None:
    t0 = time.time()

    # Step 1: Simulate (skip if files exist and regenerate=False)
    events_path = simulated_dir / "event_logs.csv"
    if regenerate or not events_path.exists():
        print("Step 1: Generating simulated data...")
        from src.simulator import simulate
        frames = simulate(n_users=n_users, seed=42)
        simulated_dir.mkdir(parents=True, exist_ok=True)
        frames["event_logs"].to_csv(simulated_dir / "event_logs.csv", index=False)
        frames["user_segments"].to_csv(simulated_dir / "user_segments.csv", index=False)
        frames["ground_truth_influence"].to_csv(
            simulated_dir / "ground_truth_influence.csv", index=False
        )
        print(f"  Simulated {n_users} users.")
    else:
        print("Step 1: Simulated data already exists — skipping (use --regenerate to force).")

    # Step 2: Build features
    print("Step 2: Building feature table...")
    from src.features import build_features
    events   = pd.read_csv(simulated_dir / "event_logs.csv",   parse_dates=["timestamp"])
    segments = pd.read_csv(simulated_dir / "user_segments.csv")
    features = build_features(events, segments)
    processed_dir.mkdir(parents=True, exist_ok=True)
    features.to_csv(processed_dir / "features.csv", index=False)
    print(f"  Features: {features.shape}")

    # Step 3: Train all models
    print("Step 3: Training classifiers...")
    from src.prediction import run as train_run
    train_run(
        target="all",
        features_path=processed_dir / "features.csv",
        models_dir=models_dir,
        reports_dir=reports_dir,
    )

    # Step 4: Evaluation studies
    print("Step 4: Running evaluation studies...")
    from src.evaluation import attribution_comparison_study, model_comparison_study, strategy_comparison_study
    gt = pd.read_csv(simulated_dir / "ground_truth_influence.csv")
    figures_dir.mkdir(parents=True, exist_ok=True)
    attribution_comparison_study(events, gt, figures_dir)
    model_comparison_study(features, models_dir, figures_dir)
    strat_df = strategy_comparison_study(events, features, models_dir, figures_dir)
    strat_df.to_csv(reports_dir / "strategy_comparison.csv", index=False)

    # Step 5: Recommendations
    print("Step 5: Generating recommendations...")
    from src.recommender import build_recommendations, build_insights, validate_output
    import json
    records  = build_recommendations(events, segments, models_dir)
    validate_output(records)
    out_json = reports_dir / "analytics_output.json"
    with open(out_json, "w") as f:
        json.dump(records, f, indent=2)
    insights = build_insights(events, segments)
    with open(reports_dir / "insights.md", "w") as f:
        f.write("# System-Level Marketing Insights\n\n")
        for ins in insights:
            f.write(f"- {ins}\n")
    print(f"  {len(records)} recommendations + {len(insights)} insights written.")

    # Step 6: Bootstrap CIs
    print("Step 6: Bootstrapping 95% CIs for headline metrics...")
    from src.bootstrap import bootstrap_strategy, bootstrap_attribution
    s_df = bootstrap_strategy(events, n_boot=500)
    a_df = bootstrap_attribution(events, gt, n_boot=30)
    pd.concat([s_df, a_df], ignore_index=True).to_csv(
        reports_dir / "bootstrap_ci.csv", index=False
    )
    print(f"  Saved: {reports_dir / 'bootstrap_ci.csv'}")

    # Step 7: Learned recommender
    print("Step 7: Training learned recommender...")
    from src.learned_recommender import train as train_learned
    train_learned(processed_dir / "features.csv", models_dir, reports_dir)

    # Step 8: SHAP feature importance
    print("Step 8: Computing SHAP feature importance...")
    try:
        from src.shap_analysis import analyze_one
        for tgt in ("conversion", "drop_off"):
            analyze_one(tgt, features, models_dir, figures_dir, reports_dir)
    except Exception as e:
        print(f"  (SHAP step skipped: {e})")

    elapsed = time.time() - t0
    print(f"\nFull pipeline completed in {elapsed:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full analytics pipeline.")
    parser.add_argument("--full",       action="store_true", help="Run all steps end-to-end")
    parser.add_argument("--regenerate", action="store_true", help="Re-simulate even if data exists")
    parser.add_argument("--users",      type=int, default=10000)
    args = parser.parse_args()

    if args.full:
        run_full(n_users=args.users, regenerate=args.regenerate)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
