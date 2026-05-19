"""Static configuration: model names, score weights, paths."""

from pathlib import Path

# Models
SUMMARIZATION_MODEL_NAME = "facebook/bart-large-cnn"
GENERATION_MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
SEMANTIC_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Score weights
SEMANTIC_WEIGHT = 0.30
PLATFORM_WEIGHT = 0.25
ENGAGEMENT_WEIGHT = 0.45

# Default platforms
PLATFORMS = ["instagram", "linkedin", "facebook", "shorts", "email"]

# Paths
ROOT = Path(__file__).parent
DATA = ROOT / "data"
RAW_WEBSITES = DATA / "raw" / "websites"
RAW_DATASETS = DATA / "raw" / "datasets"
PROCESSED = DATA / "processed"
OUTPUTS = DATA / "outputs"
MODELS = ROOT / "models"

def init_dirs() -> None:
    """Create all pipeline directories. Idempotent. Called explicitly from main.py
    so importing config has no filesystem side effect (better for tests)."""
    for d in (RAW_WEBSITES, RAW_DATASETS, PROCESSED, OUTPUTS, MODELS):
        d.mkdir(parents=True, exist_ok=True)

# Dataset filenames (drop your CSVs in data/raw/datasets/ with these names)
LABELED_DATASET_CSV = RAW_DATASETS / "your_labeled_marketing_dataset.csv"
ENGAGEMENT_DATASET_CSV = RAW_DATASETS / "your_engagement_dataset.csv"
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
