"""Static configuration: model names, score weights, paths."""

from pathlib import Path

# Models
SUMMARIZATION_MODEL_NAME = "facebook/bart-large-cnn"
GENERATION_MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
SEMANTIC_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DATA_FINETUNE_MODEL_NAME = "facebook/bart-large-mnli"

# Backward compatibility
DATA_FINETUNE_MODAL = DATA_FINETUNE_MODEL_NAME

# Score weights
SEMANTIC_WEIGHT = 0.30
PLATFORM_WEIGHT = 0.25
ENGAGEMENT_WEIGHT = 0.45

# Default platforms
PLATFORMS = ["instagram", "linkedin", "shorts", "email"]

# Paths
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW_WEBSITES = DATA / "raw" / "websites"
RAW_DATASETS = DATA / "raw" / "datasets"
INTERMEDIATE = DATA / "intermediate"
PROCESSED = DATA / "processed"
OUTPUTS = DATA / "outputs"
MODELS = ROOT / "models"

def init_dirs() -> None:
    """Create all pipeline directories. Idempotent. Called explicitly from main.py
    so importing config has no filesystem side effect (better for tests)."""
    for d in (RAW_WEBSITES, RAW_DATASETS, INTERMEDIATE, PROCESSED, OUTPUTS, MODELS):
        d.mkdir(parents=True, exist_ok=True)



RAW_MARKETING_DATASET = (
    RAW_DATASETS
    / "RafaM97_marketing_social_media_raw.csv"
)

PREPROCESSED_MARKETING_DATASET = (
    INTERMEDIATE
    / "marketing_preprocessed.csv"
)

GOAL_LABELED_DATASET = (
    INTERMEDIATE
    / "campaign_goal_labeled.csv"
)

TONE_LABELED_DATASET = (
    INTERMEDIATE
    / "tone_labeled.csv"
)

GOAL_TONE_RESEARCH_DATASET = (
    PROCESSED
    / "goal_tone_dataset_research.csv"
)

GOAL_TONE_TRAINING_DATASET = (
    PROCESSED
    / "goal_tone_dataset_training.csv"
)

GOAL_TONE_LABEL_STATISTICS_JSON = (
    PROCESSED
    / "goal_tone_label_statistics.json"
)

LABELED_DATASET_CSV = GOAL_TONE_TRAINING_DATASET

LEGACY_LABELED_DATASET_CSV = RAW_DATASETS / "your_labeled_marketing_dataset.csv"

# Dataset filenames (drop your CSVs in data/raw/datasets/ with these names)
ENGAGEMENT_DATASET_CSV = (
    RAW_DATASETS
    / "your_engagement_dataset.csv"
)

HUMAN_DATASET_CSV = RAW_DATASETS / "human_content_dataset.csv"

# Pipeline output artifacts
CRAWL_JSON = RAW_WEBSITES / "crawled_website_data.json"
KB_JSON = PROCESSED / "marketing_knowledge_base.json"
SUMMARY_JSON = PROCESSED / "marketing_summary.json"
GENERATED_CSV = OUTPUTS / "generated_platform_assets.csv"
RANKED_CSV = OUTPUTS / "ranked_platform_assets.csv"
OPTIMIZED_CSV = OUTPUTS / "optimized_platform_assets.csv"
OPTIMIZED_RANKED_CSV = OUTPUTS / "optimized_ranked_platform_assets.csv"
COMPARISON_CSV = OUTPUTS / "before_after_optimization_comparison.csv"
SIGNIFICANCE_CSV = OUTPUTS / "optimization_significance_test.csv"
HUMAN_AI_CSV = OUTPUTS / "human_vs_ai_comparison.csv"
ENGAGEMENT_MODEL_PKL = MODELS / "best_engagement_model.pkl"
ENGAGEMENT_FEATURES_PKL = MODELS / "engagement_feature_columns.pkl"
GOAL_MODEL_PKL = MODELS / "best_goal_model.pkl"
GOAL_ENCODER_PKL = MODELS / "best_goal_encoder.pkl"
TONE_MODEL_PKL = MODELS / "best_tone_model.pkl"
TONE_ENCODER_PKL = MODELS / "best_tone_encoder.pkl"
GOAL_TONE_SELECTION_JSON = MODELS / "goal_tone_model_selection.json"
GOAL_TONE_METRICS_JSON = (
    MODELS
    / "goal_tone_training_metrics.json"
)
