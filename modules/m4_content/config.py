"""Static configuration: model names, score weights, paths."""

import os
import hashlib
# ---------------------------------------------------------------------------
# Native threading / OpenMP safety
# ---------------------------------------------------------------------------
# This block must run before numpy, torch or xgboost are imported. PyTorch and
# XGBoost each bundle their own OpenMP runtime (libomp); on macOS, *fitting* an
# XGBoost model in a process where torch is loaded segfaults the interpreter
# (exit code 139, no traceback).
#
# Measured on this project (torch 2.13, xgboost 3.2, macOS arm64):
#
#   KMP_DUPLICATE_LIB_OK=TRUE ............ does NOT prevent the crash
#   XGBoost estimator n_jobs/nthread=1 ... does NOT prevent the crash
#   torch on CPU instead of MPS .......... does NOT prevent the crash
#   OMP_NUM_THREADS=1 .................... prevents the crash
#
# So the two mitigations below are kept for defence in depth, but they are not
# sufficient on their own — an earlier version of this comment claimed they
# were, which is why `goal_tone.train()` died silently and the label encoders
# were never written.
#
# Only *fitting* is affected; inference and embedding are fine multi-threaded.
# Training is therefore run single-threaded through scripts/train_models.py,
# while everything else keeps the cores. Override per run with:
#
#     PIPELINE_NUM_THREADS=1 python <anything>

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

# ---------------------------------------------------------------------------
# Content score weights
# ---------------------------------------------------------------------------
# final_score = SEMANTIC·semantic + PLATFORM·platform_fit + ENGAGEMENT·engagement
#
# These were 0.30 / 0.25 / 0.45, leaning hardest on the engagement model. That
# weighting rested on a reported R² of 0.99 — which turned out to come entirely
# from label leakage: `likes`, `comments`, `shares` and `impressions` were left
# in the feature set while the target was (likes+comments+shares)/impressions.
#
# With the leak removed and only text-derived features remaining, the measured
# result on data/raw/datasets/your_engagement_dataset.csv is:
#
#     R²        -0.30   (worse than predicting the training mean)
#     Spearman   0.02   (no rank correlation)
#
# and no individual text feature correlates with engagement at any reasonable
# significance (all p > 0.16). The dataset appears to carry no relationship
# between wording and engagement at all, so this is a property of the data
# rather than a fixable modelling failure.
#
# The weights below therefore lean on the two components that *are* meaningful:
# platform fit is a deterministic check against each platform's own length,
# hashtag and emoji conventions, and semantic similarity keeps the copy on
# message. Engagement is kept as a small tie-breaker rather than removed, so the
# pathway stays wired for when a dataset with real signal is available — but it
# no longer decides the ranking on the strength of a model with no demonstrated
# skill.
SEMANTIC_WEIGHT = 0.40
PLATFORM_WEIGHT = 0.40
ENGAGEMENT_WEIGHT = 0.20

# Content-service selection policy. These affect generation/ranking only and
# deliberately never retrain or overwrite the goal/tone classifiers.
FAST_CANDIDATES_PER_PLATFORM = 3
LOW_CONTENT_SCORE_THRESHOLD = 0.75
LOW_SCORE_RETRY_CANDIDATES = 2

# Default platforms
# M4 product scope. Other platform specifications remain below only for
# backward-compatible reading of historical artifacts; the app never offers
# them as new campaign targets.
PLATFORMS = ["instagram", "tiktok", "linkedin", "email"]

# The channels the orchestration product actually publishes to — what the API
# offers and the dashboard generates for. Kept separate from PLATFORMS above,
# which stays as the standalone module's own default so its existing generated
# artifacts still load unchanged.
#
# These two lists used to be declared independently (here and in
# api/services/content.py) and had drifted apart: `facebook` and `shorts` were
# offered by the API with no spec, no tone register and no register note, so
# they silently fell through to the generic defaults and read as the blandest
# assets on the page. Every name here must now appear in PLATFORM_SPECS,
# PLATFORM_TONE_REGISTER, PLATFORM_REGISTER_NOTE and PLATFORM_VISUAL_BRIEF —
# tests/test_content.py asserts exactly that, so adding a channel without
# writing its rules fails the suite instead of degrading quietly.
SERVICE_PLATFORMS = ["email", "instagram", "linkedin", "shorts", "facebook"]

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
        "hashtag_target": 8,       # discovery channel — tags are how posts are found
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
        "hashtag_target": 3,       # more than three reads as spam to a professional feed
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
        "hashtag_target": 4,
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
        "hashtag_target": 3,
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
    "facebook": {
        "visual_options": [
            "image",
            "video",
        ],
        "default_visual": "image",
        "hashtags": True,
        "caption_words": (10, 80),
        "hashtag_range": (1, 3),  # Facebook engagement drops past ~3 tags
        "hashtag_target": 2,
        "guidance": (
            "Conversational feed post for a mixed audience. Open with a "
            "relatable situation rather than a product claim, keep it "
            "plain-spoken, close by inviting a reply or a click."
        ),
    },
}


# ---------------------------------------------------------------------------
# Platform tone register
# ---------------------------------------------------------------------------
# The tone classifier predicts ONE tone for the business, from the business's
# own text. It cannot predict a per-platform tone: its training corpus
# (data/processed/goal_tone_dataset_training.csv) is text -> goal/tone with no
# platform column, so there is no platform signal in it to learn from.
#
# What varies per platform is therefore the *register* — how the same brand
# voice is spoken on that channel — not the brand voice itself. Keeping the
# brand voice constant across channels is deliberate: a company that reads as
# luxury on its own site should still read as luxury on TikTok, just at TikTok's
# energy. Swapping in a generic per-platform tone would discard the one thing
# the model actually measured.
#
# So: brand_tone (model, per business) x platform -> platform_tone (rule, per
# asset).
#
# PROVENANCE OF THE VALUES BELOW — read this before citing them.
#
# The *principle* is established: integrated marketing communications holds that
# a brand keeps one voice across touchpoints and varies only how it is expressed
# per channel. That is why this adapts the measured tone instead of replacing it.
#
# The *individual cells* are an editorial heuristic. They are not taken from a
# published table, not tuned, and not measured. They are declared operating
# points in the same sense as TONE_PHI3_TRIGGER_CONFIDENCE below.
#
# Learning them instead was tested and is not possible with the data here.
# scripts/probe_platform_tone_signal.py runs the trained tone classifier over
# the only corpus carrying both a platform label and post text
# (data/raw/datasets/Social Media Engagement Dataset.csv, 12k rows) and tests
# the platform x tone table for independence:
#
#     chi2 = 9.63, dof = 8, p = 0.292   ->  independent
#
# Predicted tone is within a few points of identical on all five platforms.
# The corpus is templated consumer chatter rather than brand copy, and its
# platforms barely overlap M4's, so there is no platform-voice signal in it to
# learn. As with the engagement model above, that is a property of the available
# data, not a modelling failure.
#
# To replace this heuristic with a learned mapping you need a corpus of real
# brand posts labelled by platform. Re-run the probe against it: if p < 0.05,
# derive the map from the measured distribution instead of this table.
#
# A platform absent from the map, or a brand tone absent from its inner map,
# falls through to the brand tone unchanged.

PLATFORM_TONE_REGISTER = {
    "linkedin": {
        "friendly": "professional",
        "persuasive": "professional",
        "informative": "professional",
        "luxury": "luxury",          # already the right register for LinkedIn
        "professional": "professional",
        "emotional": "professional",
    },
    "instagram": {
        "professional": "friendly",
        "informative": "friendly",
        "persuasive": "persuasive",
        "luxury": "luxury",
        "friendly": "friendly",
        "emotional": "emotional",
    },
    "tiktok": {
        "professional": "friendly",
        "informative": "friendly",
        "luxury": "persuasive",      # luxury restraint does not survive TikTok
        "persuasive": "persuasive",
        "friendly": "friendly",
        "emotional": "emotional",
    },
    "email": {
        "friendly": "persuasive",    # a mailing list is opted-in: ask for the click
        "informative": "informative",
        "professional": "professional",
        "luxury": "luxury",
        "persuasive": "persuasive",
        "emotional": "persuasive",
    },
    # Short-form vertical video. Same reasoning as TikTok — the medium is the
    # same and only the host differs — so the register follows TikTok's.
    "shorts": {
        "professional": "friendly",
        "informative": "friendly",
        "luxury": "persuasive",
        "persuasive": "persuasive",
        "friendly": "friendly",
        "emotional": "emotional",
    },
    # Facebook's feed sits between LinkedIn's formality and Instagram's warmth:
    # a mixed, non-professional audience that still reads full sentences.
    "facebook": {
        "professional": "friendly",
        "informative": "informative",
        "luxury": "friendly",
        "persuasive": "friendly",
        "friendly": "friendly",
        "emotional": "emotional",
    },
}

# How each platform's register is described in a Phi-3 prompt, so the slow
# engine adapts the same way the fast engine does instead of relying on the
# free-text `guidance` string alone.
PLATFORM_REGISTER_NOTE = {
    "linkedin": "Speak to a professional peer audience: measured, credible, "
                "no slang and no hype.",
    "instagram": "Speak warmly and visually, in the first person, as if to one "
                 "person scrolling.",
    "tiktok": "Speak fast and casually, high energy, plain spoken words only.",
    "shorts": "Speak fast and casually, high energy, plain spoken words only — "
              "the hook has to land before anyone decides to scroll on.",
    "email": "Speak directly to a subscriber who already opted in: personal, "
             "specific, and to the point.",
    "facebook": "Speak plainly to a mixed, non-professional audience: "
                "conversational, no jargon, open with a situation they "
                "recognise rather than a product claim.",
}

# ---------------------------------------------------------------------------
# Per-platform creative briefs
# ---------------------------------------------------------------------------
# The fast engine previously emitted ONE image brief and ONE video brief for
# every channel, so a LinkedIn post and an Instagram post were handed a
# byte-identical brief and the dashboard showed five copies of the same text.
# A creative brief is platform-specific in the parts that matter most — aspect
# ratio, framing, whether it has to read with the sound off, how much room the
# caption needs — so those are the parts that vary here.
#
# Same status as PLATFORM_TONE_REGISTER: the *principle* (creative is cut to
# the placement) is standard practice; the individual values are declared
# editorial operating points, not measured optima.
#
# Templates take {name} (product) and {aud} (short audience noun).

DEFAULT_VISUAL_BRIEF = {
    "image": (
        "A clean, bright product image of {name} in use by {aud}, modern "
        "setting, high detail, on-brand."
    ),
    "video": (
        "Open on {aud} using {name}, quick cuts of the key benefit, close on "
        "the logo and the call to action."
    ),
}

PLATFORM_VISUAL_BRIEF = {
    "instagram": {
        "image": (
            "4:5 portrait lifestyle frame: a single {aud} mid-task with {name} "
            "visible but off-centre, bright natural window light, shallow depth "
            "of field, warm authentic colour. Leave clear space in the upper "
            "third for the caption hook. No stock-photo poses, no text baked in."
        ),
        "video": (
            "9:16 vertical Reel, 15-20s: hook frame in the first second showing "
            "the problem {aud} recognise, then three fast cuts to {name} solving "
            "it, end on the logo. Handheld feel, trending-audio pacing, large "
            "on-screen text since most viewers watch muted."
        ),
    },
    "linkedin": {
        "image": (
            "1.91:1 landscape frame in a credible workplace context: {aud} at "
            "real work with {name} on screen, muted professional palette, even "
            "diffuse lighting, documentary rather than staged. Uncluttered "
            "enough to stay legible as a small feed thumbnail."
        ),
        "video": (
            "16:9 landscape, 30-60s: a named person explains one concrete "
            "result {aud} get from {name}, intercut with screen capture of the "
            "product. Subtitled throughout, measured pacing, no music bed."
        ),
    },
    "email": {
        "image": (
            "Wide header banner, roughly 600x200, one clear focal point: {name} "
            "shown in use, generous margins, high contrast so it still reads in "
            "a cramped inbox preview pane. Must make sense as the single image "
            "in the message and survive being displayed at half width on mobile."
        ),
        "video": (
            "Short animated header loop for {aud}, under 5s, no sound: one "
            "simple motion showing what {name} does, exported as a fallback "
            "still frame as well since most mail clients block animation."
        ),
    },
    "facebook": {
        "image": (
            "1.91:1 landscape scene of an everyday moment {aud} recognise, with "
            "{name} present but incidental rather than the hero. Faces visible, "
            "warm natural tones, candid framing — it should look like something "
            "a person posted, not an advert."
        ),
        "video": (
            "1:1 square, 20-30s, built for sound-off autoplay: burned-in "
            "captions from the first frame, one clear idea about how {name} "
            "helps {aud}, closing card with the call to action."
        ),
    },
    "shorts": {
        "image": (
            "9:16 vertical still used as the end card: {name} large and legible, "
            "one short line of text for {aud}, high contrast for small screens."
        ),
        "video": (
            "9:16 vertical Short, under 30s: the hook must land in the first "
            "three seconds — lead with the outcome {aud} want, not the setup. "
            "Fast jump cuts, bold on-screen text tracking the spoken words, "
            "spoken-word simple CTA on the final frame."
        ),
    },
    "tiktok": {
        "image": (
            "9:16 vertical still for a photo carousel: native and unpolished, "
            "{name} shown the way {aud} would actually photograph it, chunky "
            "on-screen text in the platform's own style."
        ),
        "video": (
            "9:16 vertical, 15-25s, shot handheld and deliberately unpolished: "
            "front-load the payoff for {aud}, keep cuts under two seconds, "
            "on-screen captions throughout, {name} revealed rather than "
            "announced. Native creator energy, not an advert."
        ),
    },
}


def visual_brief(platform: str, kind: str, name: str, aud: str) -> str:
    """The creative brief for this platform and medium, filled in.

    Unknown platform or medium falls back to the generic brief rather than
    raising — a new channel should degrade to plain copy, not break generation.
    """
    briefs = PLATFORM_VISUAL_BRIEF.get(
        str(platform).strip().lower(),
        DEFAULT_VISUAL_BRIEF,
    )
    kind = "video" if str(kind).strip().lower() == "video" else "image"
    template = briefs.get(kind) or DEFAULT_VISUAL_BRIEF[kind]
    return template.format(name=name, aud=aud)


def platform_tone(platform: str, brand_tone: str) -> str:
    """Adapt the model-predicted brand tone into this platform's register.

    The brand voice is what the classifier measured, so it is the input and the
    fallback; only its register shifts. Unknown platform or unknown tone returns
    the brand tone unchanged rather than guessing.
    """
    register = PLATFORM_TONE_REGISTER.get(
        str(platform).strip().lower(),
        {},
    )
    brand_tone = str(brand_tone or "").strip().lower()
    return register.get(brand_tone, brand_tone)


def register_note(platform: str) -> str:
    """One-line description of how this platform is spoken, for the LLM prompt."""
    return PLATFORM_REGISTER_NOTE.get(
        str(platform).strip().lower(),
        "",
    )


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

    # Platforms that do not offer "visual_options" are not adaptive — their
    # "visual" is a fixed property of the medium and must be honoured.
    # (Without this, "shorts" fell through to the ["image"] default and never
    # received a shorts_prompt, so the video platform got an image brief.)
    if "visual_options" not in spec:
        return spec["visual"]

    options = spec["visual_options"]

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
# This file lives in modules/m4_content/; shared artifact directories (data/,
# models/, input.json) stay at the repository root, so ROOT points there.
ROOT = Path(__file__).resolve().parents[2]
M4_DIR = Path(__file__).resolve().parent
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

DATASET_HASH_FIELDS = [
    "dataset_path",
    "label_threshold",
]
