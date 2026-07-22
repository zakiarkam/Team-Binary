"""Score human-written content against the same pipeline and compare with AI outputs."""

import pandas as pd

import config
import engagement
import evaluation


class MissingHumanDataset(FileNotFoundError):
    """The optional human baseline CSV is absent."""


def _score_human(marketing_summary: dict) -> pd.DataFrame:
    if not config.HUMAN_DATASET_CSV.exists():
        raise MissingHumanDataset(
            f"Human baseline dataset not found: {config.HUMAN_DATASET_CSV}\n"
            "This stage compares human-written captions against the generated "
            "ones. Create the CSV with two columns — 'platform' and 'caption' — "
            "one row per human-written asset, then rerun:\n"
            "  python main.py --step human-baseline"
        )

    raw = pd.read_csv(config.HUMAN_DATASET_CSV)

    missing_columns = {"platform", "caption"} - set(raw.columns)
    if missing_columns:
        raise ValueError(
            f"{config.HUMAN_DATASET_CSV} is missing required column(s): "
            f"{', '.join(sorted(missing_columns))}. Expected 'platform' and 'caption'."
        )

    df = pd.DataFrame()
    df["platform"] = raw["platform"].fillna("unknown").astype(str).str.lower()
    df["caption"] = raw["caption"].fillna("").astype(str)
    df["hashtags"] = ""
    df["cta"] = ""
    df["image_prompt"] = ""
    df["shorts_prompt"] = ""

    df = engagement.score(df)
    df["semantic_score"] = df["caption"].apply(
        lambda c: evaluation.semantic_score(marketing_summary["summary"], c)
    )
    df["platform_suitability_score"] = df.apply(evaluation.platform_suitability, axis=1)
    df["final_score"] = (
        config.SEMANTIC_WEIGHT * df["semantic_score"]
        + config.PLATFORM_WEIGHT * df["platform_suitability_score"]
        + config.ENGAGEMENT_WEIGHT * df["engagement_score"]
    )
    return df


def run(marketing_summary: dict, ranked_df: pd.DataFrame, optimized_ranked_df: pd.DataFrame) -> pd.DataFrame:
    human_df = _score_human(marketing_summary)

    def _mean_by_platform(df: pd.DataFrame, label: str) -> pd.DataFrame:
        m = df.groupby("platform")["final_score"].mean().reset_index()
        m["source"] = label
        return m

    comparison = pd.concat(
        [
            _mean_by_platform(human_df, "human"),
            _mean_by_platform(ranked_df, "phi3_initial"),
            _mean_by_platform(optimized_ranked_df, "phi3_optimized"),
        ],
        ignore_index=True,
    )
    comparison.to_csv(config.HUMAN_AI_CSV, index=False)
    print(f"Human vs AI comparison saved → {config.HUMAN_AI_CSV}")
    print(comparison.to_string())
    return comparison
