"""Artifact discovery.

The pipeline hands off between stages entirely through files on disk, so the
dashboard reads exactly what the pipeline wrote — it never recomputes a score.
Anything missing is reported as missing rather than faked, because a stage that
has not run is a fact the user needs to see.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


@dataclass(frozen=True)
class Stage:
    """One pipeline stage and the artifact whose existence proves it ran."""

    name: str
    label: str
    layer: str
    reads: str
    writes: str
    artifact: Path

    @property
    def done(self) -> bool:
        return self.artifact.exists()

    @property
    def finished_at(self) -> datetime | None:
        if not self.done:
            return None
        return datetime.fromtimestamp(self.artifact.stat().st_mtime)


STAGES: list[Stage] = [
    Stage("crawl", "Crawl website", "Input",
          "input.json", "crawled_website_data.json", config.CRAWL_JSON),
    Stage("kb", "Build knowledge base", "Input",
          "crawl output", "marketing_knowledge_base.json", config.KB_JSON),
    Stage("preprocess-dataset", "Preprocess corpus", "Preparation",
          "RafaM97 raw CSV", "marketing_preprocessed.csv",
          config.PREPROCESSED_MARKETING_DATASET),
    Stage("label-goal", "Weak-label campaign goal", "Preparation",
          "preprocessed corpus", "campaign_goal_labeled.csv",
          config.GOAL_LABELED_DATASET),
    Stage("label-tone", "Weak-label tone", "Preparation",
          "goal-labeled corpus", "tone_labeled.csv", config.TONE_LABELED_DATASET),
    Stage("build-dataset", "Gate + split dataset", "Preparation",
          "tone-labeled corpus", "goal_tone_dataset_training.csv",
          config.GOAL_TONE_TRAINING_DATASET),
    Stage("goal-tone-train", "Train goal/tone classifiers", "Modeling",
          "training dataset", "best_goal_model.pkl / best_tone_model.pkl",
          config.GOAL_TONE_SELECTION_JSON),
    Stage("goal-tone-predict", "Infer goal + tone", "Modeling",
          "knowledge base", "updated knowledge base", config.KB_JSON),
    Stage("summary", "Summarize (BART)", "Generation",
          "knowledge base", "marketing_summary.json", config.SUMMARY_JSON),
    Stage("generate", "Generate assets (Phi-3)", "Generation",
          "marketing summary", "generated_platform_assets.csv",
          config.GENERATED_CSV),
    Stage("engagement-train", "Train engagement regressor", "Modeling",
          "engagement dataset", "best_engagement_model.pkl",
          config.ENGAGEMENT_MODEL_PKL),
    Stage("engagement-score", "Score engagement", "Evaluation",
          "generated assets", "engagement_score column", config.GENERATED_CSV),
    Stage("evaluate", "Rank by composite score", "Evaluation",
          "scored assets", "ranked_platform_assets.csv", config.RANKED_CSV),
    Stage("optimize", "Re-prompt + re-score", "Evaluation",
          "ranked assets", "optimized_ranked_platform_assets.csv",
          config.OPTIMIZED_RANKED_CSV),
    Stage("significance", "Paired t-test", "Validation",
          "before/after comparison", "optimization_significance_test.csv",
          config.SIGNIFICANCE_CSV),
]


def read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def training_metrics() -> dict | None:
    return read_json(config.GOAL_TONE_METRICS_JSON)


def engagement_comparison() -> pd.DataFrame | None:
    return read_csv(config.OUTPUTS / "engagement_model_comparison.csv")


def research_dataset() -> pd.DataFrame | None:
    return read_csv(config.GOAL_TONE_RESEARCH_DATASET)


def training_dataset() -> pd.DataFrame | None:
    return read_csv(config.GOAL_TONE_TRAINING_DATASET)
