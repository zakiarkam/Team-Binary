"""Static configuration: model names, score weights, paths."""

import os
import hashlib
# ---------------------------------------------------------------------------
# Native threading / OpenMP safety
# ---------------------------------------------------------------------------
# This block must run before numpy, torch or xgboost are imported. PyTorch and
# XGBoost each bundle their own OpenMP runtime (libomp); on macOS, loading both
# and then fitting XGBoost while torch is active segfaults.
#
# The actual crash guard is two-part and neither part needs a single thread:
#   1. KMP_DUPLICATE_LIB_OK lets the duplicate runtimes coexist.
#   2. Every XGBoost estimator in this project is constructed with n_jobs=1,
#      so XGBoost never spawns the pool that clashes with torch's.
#
# Pinning OMP_NUM_THREADS=1 globally was the previous blunt fix. It also capped
# every torch CPU matmul and every BLAS call to a single core, which made CPU
# inference roughly as many times slower as the machine has cores. The default
# below leaves one core for the OS and uses the rest.
#
# Override per run, e.g.  PIPELINE_NUM_THREADS=1 python main.py
_DEFAULT_THREADS = str(max(1, (os.cpu_count() or 2) - 1))
_THREADS = os.environ.get("PIPELINE_NUM_THREADS", _DEFAULT_THREADS)

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
for _env_var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_env_var, _THREADS)

# Hard escape hatch: train only the TF-IDF + Logistic Regression classifier and
# skip the Sentence-BERT + XGBoost model entirely. For machines where the
# torch/XGBoost OpenMP clash still crashes despite the settings above (a
# segfault cannot be caught in Python, so opting out is the only recovery).
#   GOAL_TONE_SKIP_XGBOOST=1 python main.py
GOAL_TONE_SKIP_XGBOOST = (
    os.environ.get("GOAL_TONE_SKIP_XGBOOST", "").strip().lower()
    in {"1", "true", "yes"}
)

# Same escape hatch for the personalized engagement regressor in learning/.
# The stage runs standalone (no torch in-process) so the clash does not arise in
# normal use; this exists for the test suite, where sibling modules import
# transformers first, and for any environment where the clash persists.
LEARNING_SKIP_XGBOOST = (
    os.environ.get("LEARNING_SKIP_XGBOOST", "").strip().lower()
    in {"1", "true", "yes"}
)

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
        "visual_options": [
            "image",
            "video",
        ],
        "default_visual": "image",
        "hashtags": True,
        "caption_words": (0, 40),
        "hashtag_range": (3, 30),  # 30 = Instagram's per-post hashtag cap
        "guidance": (
            "Short, visual-first feed caption. Lead with a hook in the "
            "first line, keep the body scannable, close with a soft CTA."
        ),
    },
    "linkedin": {
        "visual_options": [
            "image",
            "video",
        ],
        "default_visual": "image",
        "hashtags": True,
        "caption_words": (20, 180),
        "hashtag_range": (0, 5),
        "guidance": (
            "Professional post. Open with a business insight, support it "
            "with concrete value for the reader, close with a formal CTA."
        ),
    },
    "tiktok": {

        "visual_options": [
            "image",
            "video",
        ],
        "default_visual": "video",
        "hashtags": True,
        "caption_words": (0,30),
        "hashtag_range": (3,5),
        "guidance": (
            "Create short-form vertical video content. "
            "The first seconds must capture attention. "
            "Use simple CTA."
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


# def platform_spec(platform: str) -> dict:
#     """Return the capability spec for a platform, falling back to the default."""
#     return PLATFORM_SPECS.get(
#         str(platform).strip().lower(),
#         DEFAULT_PLATFORM_SPEC,
#     )

def platform_spec(platform: str) -> dict:

    platform = str(platform).strip().lower()

    spec = PLATFORM_SPECS.get(
        platform,
        DEFAULT_PLATFORM_SPEC,
    )

    spec = spec.copy()

    if "visual" not in spec:

        spec["visual"] = spec.get(
            "default_visual",
            "image"
        )

    return spec

def select_visual(platform, marketing_summary):

    spec = platform_spec(platform)

    options = spec.get(
        "visual_options",
        ["image"]
    )

    text = (
        marketing_summary.get("summary","")
        +
        marketing_summary.get("campaign_goal","")
    ).lower()


    video_keywords = [
        "launch",
        "demo",
        "tutorial",
        "automation",
        "ai",
        "app",
        "productivity",
        "show",
    ]


    if "video" in options:

        score = sum(
            1
            for word in video_keywords
            if word in text
        )

        if score >= 2:
            return "video"


    return spec.get(
        "default_visual",
        "image"
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

FEEDBACK = DATA / "feedback"
CACHE = DATA / "cache"

def init_dirs() -> None:
    """Create all pipeline directories. Idempotent. Called explicitly from main.py
    so importing config has no filesystem side effect (better for tests)."""
    for d in (RAW_WEBSITES, RAW_DATASETS, INTERMEDIATE, PROCESSED, OUTPUTS,
              MODELS, FEEDBACK, CACHE,):
        d.mkdir(parents=True, exist_ok=True)



RAW_MARKETING_DATASET = (
    RAW_DATASETS
    / "RafaM97_marketing_social_media_raw.csv"
)

PREPROCESSED_MARKETING_DATASET = (
    INTERMEDIATE
    / "marketing_preprocessed.csv"
)

PREPROCESSED_DATASET_CSV = PREPROCESSED_MARKETING_DATASET

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

# ---------------------------------------------------------------------------
# Engagement learning loop (opt-in — nothing here runs on a default `main.py`)
# ---------------------------------------------------------------------------
# These artifacts belong to the adaptive learning subsystem in learning/. The
# personalized model is written to its OWN file and never overwrites
# ENGAGEMENT_MODEL_PKL, so the default generate→evaluate→optimize path keeps
# using exactly the model it used before.

# A richer public corpus than ENGAGEMENT_DATASET_CSV: it carries a per-account
# id (user_id) and a timestamp, which is what makes within-account relative
# targets and personalization possible. Used as the base corpus when present.
RICH_ENGAGEMENT_DATASET_CSV = RAW_DATASETS / "Social Media Engagement Dataset.csv"

# SQLite store of generated assets + their predictions, with (nullable) actual
# analytics filled in later from an Insights CSV import.
FEEDBACK_DB = FEEDBACK / "feedback.db"

# Drop platform Insights CSV exports here for `feedback-import` to ingest.
ANALYTICS_IMPORT_DIR = FEEDBACK / "analytics_import"

# Personalized engagement predictor + its feature columns (separate from the
# base model on purpose).
PERSONALIZED_ENGAGEMENT_MODEL_PKL = MODELS / "personalized_engagement_model.pkl"
PERSONALIZED_ENGAGEMENT_FEATURES_PKL = MODELS / "personalized_engagement_features.pkl"
PERSONALIZED_ENGAGEMENT_METRICS_JSON = MODELS / "personalized_engagement_metrics.json"

# Best-of-N candidate generation output.
CANDIDATES_CSV = OUTPUTS / "candidate_platform_assets.csv"
BEST_CANDIDATES_CSV = OUTPUTS / "best_candidate_platform_assets.csv"
PIPELINE_METADATA_JSON = CACHE / "pipeline_metadata.json"

# How many caption candidates to generate per platform before ranking.
CANDIDATES_PER_PLATFORM = 5

# Minimum posts an account needs before its own history is trusted enough to
# normalize against (below this the base/raw rate is used instead).
RELATIVE_TARGET_MIN_ACCOUNT_POSTS = 5

PIPELINE_STAGE_OUTPUTS = {
    "crawl": CRAWL_JSON,
    "kb": KB_JSON,
    "goal-tone-predict": KB_JSON,
    "summary": SUMMARY_JSON,
    "generate": GENERATED_CSV,
    "evaluate": RANKED_CSV,
    "optimize": OPTIMIZED_RANKED_CSV,
}

PIPELINE_HASH_FIELDS = [
    "product_name",
    "website_url",
]


CONTENT_HASH_FIELDS = [
    "product_name",
    "website_url",
]


GENERATION_HASH_FIELDS = [
    "target_audience",
    "customer_segment",
    "preferred_platforms",
    "campaign_goal",
    "tone",
]

USER_INPUT_HASH_FIELDS = [
    "product_name",
    "website_url",
    "target_audience",
    "customer_segment",
    "preferred_platforms",
]

STAGE_HASHES = {
    "crawl": DATA / "crawl.hash",
    "summary": DATA / "summary.hash",
    "generate": DATA / "generate.hash",
}