"""Best-of-N generation: generate several captions per platform, rank, keep best.

This is the inference-time half of the adaptive loop. The generator (Phi-3) is
never retrained — instead it is sampled several times per platform, and the
*updated* engagement predictor decides which candidate survives. As the
predictor improves from feedback, the selection improves, so the system produces
more engaging content without any change to the language model's weights.

⚠ Ranking N candidates by a model-predicted score is an over-optimization
regime: pushed hard, best-of-N selects for the predictor's error rather than
real engagement (Gao et al. 2023). Two guards are built in: N is small by
default, and candidates are ranked by the full composite score (semantic +
platform fit + engagement), not by predicted engagement alone. Whether best-of-N
actually beats a random pick is an empirical question the feedback data can
answer once enough actuals are collected — that comparison is the honest
validation of this stage.

Everything the ranking needs already exists in generator.py and evaluation.py;
this module only orchestrates them, so those modules are unchanged.
"""

from __future__ import annotations

import pandas as pd

import config
from generator import build_prompt, standardize, ASSET_COLUMNS
from learning import personalize


def _composite(semantic: float, platform_fit: float, engagement: float) -> float:
    """The same weighted sum evaluation.py uses, factored out for reuse/testing."""
    return (
        config.SEMANTIC_WEIGHT * semantic
        + config.PLATFORM_WEIGHT * platform_fit
        + config.ENGAGEMENT_WEIGHT * engagement
    )


def generate_candidates(
    marketing_summary: dict,
    platform: str,
    n: int,
) -> pd.DataFrame:
    """Sample `n` distinct assets for one platform."""
    from models import generate_with_phi3  # deferred: pulls in torch

    prompt = build_prompt(marketing_summary, platform)
    rows = []
    for i in range(n):
        # Sampling (deterministic=False) is what makes the candidates differ.
        raw = generate_with_phi3(prompt, max_new_tokens=500, deterministic=False)
        item = standardize(platform, raw, marketing_summary)
        item["candidate_index"] = i
        rows.append(item)
    return pd.DataFrame(rows, columns=[*ASSET_COLUMNS, "candidate_index"])


def score_candidates(
    candidates: pd.DataFrame,
    marketing_summary: dict,
    account_id: str | None = None,
) -> pd.DataFrame:
    """Attach semantic, platform-fit, engagement and composite scores + rank."""
    import evaluation  # deferred: pulls in the semantic model

    scored = personalize.score(candidates, account_id=account_id)

    source = marketing_summary["summary"]
    scored["semantic_score"] = scored["caption"].apply(
        lambda c: evaluation.semantic_score(source, c)
    )
    scored["platform_suitability_score"] = scored.apply(
        evaluation.platform_suitability, axis=1
    )
    scored["final_score"] = scored.apply(
        lambda r: _composite(
            r["semantic_score"], r["platform_suitability_score"],
            r["engagement_score"],
        ),
        axis=1,
    )
    scored = scored.sort_values(
        ["platform", "final_score"], ascending=[True, False]
    ).reset_index(drop=True)
    scored["rank_in_platform"] = scored.groupby("platform").cumcount() + 1
    return scored


def run(
    marketing_summary: dict,
    n: int | None = None,
    account_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate, score and rank candidates for every preferred platform.

    Returns (all_candidates, best_per_platform) and writes both to disk.
    """
    n = n or config.CANDIDATES_PER_PLATFORM
    platforms = list(marketing_summary.get("preferred_platforms", config.PLATFORMS))

    all_scored = []
    for platform in platforms:
        print(f"\n=== {str(platform).upper()}: generating {n} candidates ===")
        candidates = generate_candidates(marketing_summary, platform, n)
        all_scored.append(score_candidates(candidates, marketing_summary, account_id))

    everything = pd.concat(all_scored, ignore_index=True)
    everything.to_csv(config.CANDIDATES_CSV, index=False)

    best = (
        everything[everything["rank_in_platform"] == 1]
        .reset_index(drop=True)
    )
    best.to_csv(config.BEST_CANDIDATES_CSV, index=False)

    print(f"\nAll candidates → {config.CANDIDATES_CSV}")
    print(f"Best per platform → {config.BEST_CANDIDATES_CSV}")
    print(best[["platform", "final_score", "semantic_score",
                "platform_suitability_score", "engagement_score"]].to_string())
    return everything, best


def load_cached() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(config.CANDIDATES_CSV), pd.read_csv(config.BEST_CANDIDATES_CSV)
