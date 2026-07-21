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

# ---------------------------------------------------------------------------
# Platform capabilities
# ---------------------------------------------------------------------------
# Single source of truth for what each platform actually needs, so generation
# (generator.py), scoring (evaluation.py) and re-prompting (optimization.py)
# cannot drift apart.
#
# "visual" decides which creative prompt is requested for a platform:
#   "image" -> ask for image_prompt only
#   "video" -> ask for shorts_prompt only
#   None    -> ask for neither
#
# Provenance of the numbers below:
#   hashtag_range upper bounds are the platforms' own published per-post caps.
#   caption_words ranges are the conventions already used by this project's
#   scoring rules. They are editorial heuristics, not measured optima.

DEFAULT_PLATFORM_SPEC = {
    "visual": "image",
    "hashtags": True,
    "caption_words": (0, 80),
    "hashtag_range": (0, 5),
    "guidance": (
        "Write a clear caption with one concrete benefit and a direct "
        "call to action."
    ),
}

PLATFORM_SPECS = {
    "instagram": {
        "visual": "image",
        "hashtags": True,
        "caption_words": (0, 40),
        "hashtag_range": (3, 30),  # 30 = Instagram's per-post hashtag cap
        "guidance": (
            "Short, visual-first feed caption. Lead with a hook in the "
            "first line, keep the body scannable, close with a soft CTA."
        ),
    },
    "linkedin": {
        "visual": "image",
        "hashtags": True,
        "caption_words": (20, 180),
        "hashtag_range": (0, 5),
        "guidance": (
            "Professional post. Open with a business insight, support it "
            "with concrete value for the reader, close with a formal CTA."
        ),
    },
    "shorts": {
        "visual": "video",
        "hashtags": True,
        "caption_words": (0, 30),
        "hashtag_range": (0, 5),
        "guidance": (
            "Very short vertical-video caption. The hook must land in the "
            "first three seconds and the CTA must be spoken-word simple."
        ),
    },
    "email": {
        "visual": "image",
        "hashtags": False,
        "caption_words": (20, 200),
        "hashtag_range": (0, 0),
        "guidance": (
            "Write a subject line followed by a concise body. State the "
            "value proposition early, end with one clear CTA. No hashtags."
        ),
    },
}


def platform_spec(platform: str) -> dict:
    """Return the capability spec for a platform, falling back to the default."""
    return PLATFORM_SPECS.get(
        str(platform).strip().lower(),
        DEFAULT_PLATFORM_SPEC,
    )

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

# ---------------------------------------------------------------------------
# Tone labeling: per-stage checkpoints
# ---------------------------------------------------------------------------
# The tone labeler runs four stages and writes one checkpoint per stage, so an
# interrupted run resumes from the last completed stage instead of re-running
# BART-MNLI or Phi-3 from scratch. DATA is ROOT / "data".

TONE_RULE_CHECKPOINT = (
    DATA / "tone_rule_checkpoint.csv"
)

TONE_BART_CHECKPOINT = (
    DATA / "tone_bart_checkpoint.csv"
)

TONE_PHI3_CHECKPOINT = (
    DATA / "tone_phi3_checkpoint.csv"
)

TONE_FINAL_CHECKPOINT = (
    DATA / "tone_final_checkpoint.csv"
)

# Stages in execution order, paired with the checkpoint each one writes.
# Used to resume from the furthest completed stage.
TONE_STAGE_CHECKPOINTS = [
    ("rule", TONE_RULE_CHECKPOINT),
    ("bart", TONE_BART_CHECKPOINT),
    ("phi3", TONE_PHI3_CHECKPOINT),
    ("final", TONE_FINAL_CHECKPOINT),
]

# Rows between incremental saves inside the long BART and Phi-3 stages.
LABEL_CHECKPOINT_INTERVAL = 20

# ---------------------------------------------------------------------------
# Tone labeling: ensemble tuning
# ---------------------------------------------------------------------------
# These are declared operating points, not measured optima. There is no
# human-annotated tone sample in this repository to tune them against, so they
# are surfaced here to be reported and re-tuned once a gold sample exists.

# BART confidence below which Phi-3 is asked to arbitrate.
TONE_PHI3_TRIGGER_CONFIDENCE = 0.67

# Confidence at which a single method is trusted without corroboration.
TONE_ZERO_SHOT_ACCEPT_CONFIDENCE = 0.72
TONE_RULE_ACCEPT_CONFIDENCE = 0.82

# Below this final confidence, or this level of inter-method agreement,
# a row is flagged for human review.
TONE_MIN_CONFIDENCE = 0.62
TONE_MIN_AGREEMENT = 0.5

# Rule scorer: total keyword weight treated as full evidence, and the split
# between "how much evidence" and "how clearly it beats the runner-up".
TONE_RULE_SATURATION_WEIGHT = 6.0
TONE_RULE_EVIDENCE_WEIGHT = 0.55
TONE_RULE_MARGIN_WEIGHT = 0.45

# BART-large-mnli truncates at 1024 tokens; this char cap is a cheap guard
# applied before tokenization.
TONE_ZERO_SHOT_MAX_CHARS = 4000

# Marginal (prior) calibration strength for zero-shot scores.
# 0.0 = raw BART output, 1.0 = fully divide out each label's corpus-mean score.
# Counteracts the single-label collapse that softmax over overlapping candidate
# descriptions produces on homogeneous marketing copy.
TONE_PRIOR_CALIBRATION_STRENGTH = 1.0

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
