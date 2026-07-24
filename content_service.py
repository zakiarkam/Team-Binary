"""Module 4 content service — the app-facing entry point for content generation.

Wraps Person 4's content pipeline so the unified app can turn a product brief
into scored, platform-ready marketing assets. Two engines, identical schema:

  engine="fast"  (default) — instant template generation, still model-backed:
      goal + tone inferred by the trained classifiers, engagement predicted by
      the trained regressor, ranked by the same composite score. Good for the
      interactive "enter product -> see posts" loop.

  engine="phi3"            — the real Phi-3 generator exactly as Person 4 built
      it (generator.run). Higher quality, slower (~30-90s/asset on CPU).

Every asset is scored with Person 4's evaluation:
    final_score = 0.30*semantic + 0.25*platform_suitability + 0.45*engagement
Then re-ranked, with platform order nudged by Module 3's analytics feedback.
"""

from __future__ import annotations

import re
from typing import Any, Callable

import pandas as pd

import config
import engagement
import evaluation
import goal_tone
from adapters.m3_to_m4 import apply_to_platforms

# CTA phrasing per inferred campaign goal.
_CTA_BY_GOAL = {
    "awareness": "Discover what makes {name} different.",
    "conversion": "Start with {name} today.",
    "lead_generation": "Sign up and see {name} in action.",
    "engagement": "Tell us what you'd build with {name}.",
    "retention": "Come back to {name} — there's more waiting.",
}

# Opening hook per tone.
_HOOK_BY_TONE = {
    "persuasive": "Here's why {aud} are switching to {name}.",
    "professional": "{name}: a smarter way for {aud} to get results.",
    "luxury": "Elevate your workflow with {name}.",
    "friendly": "Meet {name} — made for {aud}.",
    "informative": "What {aud} should know about {name}.",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _aud_short(aud: str) -> str:
    """A short, readable audience noun (first item of a list, else first few words)."""
    aud = _clean(aud)
    first = re.split(r",| and ", aud)[0].strip()
    return first if first else "you"


def _benefit(summary: dict) -> str:
    """A single concise benefit sentence from the description."""
    desc = _clean(summary.get("summary", ""))
    sent = re.split(r"(?<=[.!?])\s", desc)[0] if desc else ""
    return sent or f"{summary['product_name']} makes your work easier."


def _keywords(product_input: dict) -> list[str]:
    """Derive hashtag-friendly keywords from the brief."""
    raw = " ".join(str(product_input.get(k, "")) for k in
                    ("product_name", "target_audience", "customer_segment"))
    stop = {"and", "the", "for", "with", "small", "new", "our", "your", "you",
            "who", "that", "this", "are", "not", "all", "any", "app", "tool"}
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", raw)
    seen, out = set(), []
    for w in words:
        wl = w.lower()
        if wl not in seen and wl not in stop and len(w) > 2:
            seen.add(wl)
            out.append(w.capitalize())
    return out or ["Marketing", "AI", "Launch"]


def infer_goal_tone(text: str) -> tuple[str, str]:
    """Infer campaign_goal + tone with Person 4's trained classifiers."""
    sel = {}
    try:
        import json
        sel = json.loads(config.GOAL_TONE_SELECTION_JSON.read_text())
    except Exception:
        sel = {"best_goal_model_type": "tfidf_logistic",
               "best_tone_model_type": "tfidf_logistic"}
    goal = goal_tone.predict_one(text, config.GOAL_MODEL_PKL,
                                 sel.get("best_goal_model_type", "tfidf_logistic"),
                                 config.GOAL_ENCODER_PKL)
    tone = goal_tone.predict_one(text, config.TONE_MODEL_PKL,
                                 sel.get("best_tone_model_type", "tfidf_logistic"),
                                 config.TONE_ENCODER_PKL)
    return goal, tone


def build_summary(product_input: dict, priorities: dict | None = None) -> dict:
    """Assemble a marketing_summary and infer goal + tone."""
    name = _clean(product_input.get("product_name", "the product"))
    aud = _clean(product_input.get("target_audience", "modern teams"))
    seg = _clean(product_input.get("customer_segment", ""))
    desc = _clean(product_input.get("product_description",
                  f"{name} helps {aud} work better. {seg}"))
    goal, tone = infer_goal_tone(f"{name}. {desc}. For {aud}. {seg}")
    return {
        "product_name": name,
        "website_url": _clean(product_input.get("website_url", "")),
        "target_audience": aud,
        "customer_segment": seg,
        "campaign_goal": goal,
        "tone": tone,
        "summary": desc,
        "preferred_platforms": product_input.get("preferred_platforms", config.PLATFORMS),
    }


# --------------------------------------------------------------------------- #
# Fast, model-backed template generation
# --------------------------------------------------------------------------- #

def _fit_words(text: str, lo: int, hi: int, filler: str) -> str:
    """Pad/trim a caption to sit inside [lo, hi] words, keeping formatting when in-range."""
    n = len(text.split())
    if (n >= lo) and (hi == 0 or n <= hi):
        return text  # already compliant — preserve line breaks
    words = text.split()
    if hi and len(words) > hi:
        words = words[:hi]
    while len(words) < lo:
        words += filler.split()
    return " ".join(words)


def _hashtags(keywords: list[str], lo: int, hi: int, goal: str) -> list[str]:
    if hi == 0:
        return []
    pool = [f"#{k}" for k in keywords] + [
        f"#{goal.title().replace('_', '')}", "#Marketing", "#Launch",
        "#Growth", "#Brand", "#Digital",
    ]
    seen, out = set(), []
    for t in pool:
        if t.lower() not in seen:
            seen.add(t.lower()); out.append(t)
    target = max(lo, min(hi, max(lo, 5)))
    return out[:target]


def _template_asset(platform: str, summary: dict, keywords: list[str]) -> dict:
    spec = config.platform_spec(platform)
    visual = config.select_visual(platform, summary)
    name = summary["product_name"]; aud = _aud_short(summary["target_audience"])
    goal = summary["campaign_goal"]; tone = summary["tone"]
    lo, hi = spec["caption_words"]

    hook = _HOOK_BY_TONE.get(tone, _HOOK_BY_TONE["professional"]).format(name=name, aud=aud)
    cta = _CTA_BY_GOAL.get(goal, _CTA_BY_GOAL["awareness"]).format(name=name)
    benefit = _benefit(summary)

    if platform == "email":
        caption = (f"Subject: {hook}\n\n"
                   f"Hi {aud} — {benefit} That's why {name} is built for the way you work. "
                   f"{cta}")
    elif platform == "linkedin":
        caption = (f"{hook}\n\n{benefit} For teams that value momentum over busywork, "
                   f"{name} turns hours of effort into minutes.\n\n{cta}")
    else:  # instagram / shorts / tiktok — punchy
        caption = f"{hook} {benefit} {cta}"

    # Light normalisation that preserves paragraph breaks.
    caption = re.sub(r"[ \t]+", " ", caption).replace(" .", ".").strip()
    caption = re.sub(r"\n{3,}", "\n\n", caption)
    caption = _fit_words(caption, lo, hi, f"{benefit} {cta}")

    least, most = spec["hashtag_range"]
    tags = _hashtags(keywords, least, most, goal) if spec.get("hashtags") else []

    row = {c: "" for c in ("platform", "caption", "hashtags", "cta",
                           "image_prompt", "shorts_prompt")}
    row["platform"] = platform
    row["caption"] = caption
    row["hashtags"] = tags
    row["cta"] = cta
    if visual == "video":
        row["shorts_prompt"] = (f"Open on a scene that shows {aud} using {name}; "
                                f"quick cuts of the key benefit, end on the logo and CTA.")
    else:
        row["image_prompt"] = (f"A clean, bright product image of {name} in use by "
                               f"{aud}, modern lifestyle setting, high detail, on-brand.")
    return row


def _template_assets(summary: dict, platforms: list[str]) -> pd.DataFrame:
    keywords = _keywords({"product_name": summary["product_name"],
                          "target_audience": summary["target_audience"],
                          "customer_segment": summary["customer_segment"]})
    rows = [_template_asset(p, summary, keywords) for p in platforms]
    return pd.DataFrame(rows, columns=["platform", "caption", "hashtags", "cta",
                                       "image_prompt", "shorts_prompt"])


# --------------------------------------------------------------------------- #
# Scoring (Person 4's evaluation) + public entry point
# --------------------------------------------------------------------------- #

def _tfidf_semantic(src: str, texts: list[str]) -> list[float]:
    """Sklearn-only semantic similarity (no torch) — stable proxy for SBERT.

    Cosine similarity between the product summary and each caption over a shared
    TF-IDF space. Used for the fast engine to avoid the flaky torch/MPS↔sklearn
    native clash on macOS.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    corpus = [src or ""] + [t or "" for t in texts]
    try:
        m = TfidfVectorizer(stop_words="english").fit_transform(corpus)
        sims = cosine_similarity(m[0:1], m[1:]).ravel()
        return [float(s) for s in sims]
    except Exception:
        return [0.5] * len(texts)


def score_assets(assets: pd.DataFrame, summary: dict,
                 semantic_method: str = "tfidf") -> pd.DataFrame:
    """Add engagement + semantic + platform_suitability + final_score.

    semantic_method: 'tfidf' (sklearn, stable), 'sbert' (Sentence-BERT, torch),
    or 'none' (neutral placeholder).
    """
    df = engagement.score(assets)  # predicted_engagement + engagement_score
    df["platform_suitability_score"] = df.apply(evaluation.platform_suitability, axis=1)
    src = summary.get("summary", "")
    if semantic_method == "sbert":
        df["semantic_score"] = df["caption"].apply(lambda t: evaluation.semantic_score(src, t))
    elif semantic_method == "tfidf":
        df["semantic_score"] = _tfidf_semantic(src, df["caption"].tolist())
    else:
        df["semantic_score"] = 0.6
    df["final_score"] = (config.SEMANTIC_WEIGHT * df["semantic_score"]
                         + config.PLATFORM_WEIGHT * df["platform_suitability_score"]
                         + config.ENGAGEMENT_WEIGHT * df["engagement_score"])
    return df.sort_values("final_score", ascending=False).reset_index(drop=True)


def generate(product_input: dict, priorities: dict | None = None,
             engine: str = "fast", with_semantic: bool = True,
             semantic_method: str | None = None,
             log: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Turn a product brief into ranked, platform-ready, scored marketing assets."""
    def _l(m):
        print(m, flush=True)
        if log:
            log(m)

    summary = build_summary(product_input, priorities)
    _l(f"[M4] inferred goal='{summary['campaign_goal']}', tone='{summary['tone']}'")

    platforms = list(summary["preferred_platforms"])
    if priorities:
        platforms = apply_to_platforms(platforms, priorities)

    if engine == "phi3":
        _l(f"[M4] generating {len(platforms)} assets with Phi-3 (slow)…")
        import generator
        summary_for_gen = {**summary, "preferred_platforms": platforms}
        assets = generator.run(summary_for_gen)
    else:
        _l(f"[M4] generating {len(platforms)} assets (fast template engine)…")
        assets = _template_assets(summary, platforms)

    # Fast engine -> sklearn TF-IDF semantic (stable). Phi-3 -> Sentence-BERT.
    if semantic_method is None:
        semantic_method = "sbert" if engine == "phi3" else "tfidf"
    _l(f"[M4] scoring assets (engagement + {semantic_method}-semantic + platform-fit)…")
    ranked = score_assets(assets, summary, semantic_method=semantic_method)

    # Serialise hashtags as list for JSON friendliness.
    records = ranked.to_dict(orient="records")
    _l(f"[M4] done — top platform: {records[0]['platform']} "
       f"(score {records[0]['final_score']:.3f})")
    return {
        "assets": records,
        "summary": summary,
        "engine": engine,
        "priorities": priorities or {},
        "platform_order": platforms,
    }


if __name__ == "__main__":
    import json
    demo = json.loads((config.ROOT / "input.json").read_text())
    out = generate(demo, engine="fast")
    for a in out["assets"]:
        print(f"\n=== {a['platform'].upper()}  (final {a['final_score']:.3f}) ===")
        print(a["caption"])
        if a["hashtags"]:
            print(" ".join(a["hashtags"]))
