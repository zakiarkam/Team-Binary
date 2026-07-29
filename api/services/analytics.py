"""Module 3 as a service — funnel, attribution and prediction over observed data.

Reuses Module 3's own implementations (`funnel.py`, `attribution.py`,
`features.py`, `recommender.py`) rather than reimplementing them, so the
production numbers and the research numbers come from the same code.

What changes is the *input*. In the research the events come from Module 3's
simulator; here they come from two real sources joined into one journey:

    events        website behaviour collected by mos.js  (acquisition touch)
    interactions  campaign sends, opens, clicks, conversions

That join is what makes multi-touch attribution meaningful. Email on its own is
a single platform, and every attribution model gives the same answer on a
single-platform journey — a degenerate result that would look like agreement but
mean nothing. Adding the acquisition channel (LinkedIn, Google, direct, …) gives
genuine multi-platform journeys to attribute across.

Honesty rules enforced here:

*   Every result carries `data_basis` — live, dataset or mixed — derived from
    `interactions.source`, never asserted.
*   Journey-length diagnostics are always returned, so a reader can see when
    attribution had only one touch to work with.
*   Predictions say which data their model was fitted on. The shipped models
    were fitted on Module 3's simulator; using them here is a transfer to a
    different distribution and is labelled as such.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from api import db

log = logging.getLogger("mos.analytics")

ROOT = Path(__file__).resolve().parents[2]
M3_DIR = ROOT / "modules" / "m3_analytics"
MODELS_DIR = ROOT / "outputs" / "models"

#: Below this many converting journeys, attribution is noise. Reported, not hidden.
MIN_CONVERSIONS_FOR_ATTRIBUTION = 5
#: Below this, a model fitted on real data would be worse than the transferred one.
MIN_USERS_FOR_LOCAL_TRAINING = 200


def _m3():
    """Import Module 3's package, which expects to be imported from its own root."""
    if str(M3_DIR) not in sys.path:
        sys.path.insert(0, str(M3_DIR))
    from src import attribution, features, funnel  # type: ignore
    return funnel, attribution, features


# ── Building the journey ─────────────────────────────────────────────────────
def journey_events(site_id: int) -> pd.DataFrame:
    """One long-format frame of every touchpoint, ready for Module 3.

    Columns: user_id, timestamp, channel, platform, campaign_id, strategy,
             event_type, source
    """
    # 1. Email campaign touchpoints — the funnel proper.
    email = db.fetch_all(
        """
        SELECT i.visitor_id            AS user_id,
               i.occurred_at           AS timestamp,
               i.channel, i.platform,
               COALESCE(i.campaign_id::text, 'none') AS campaign_id,
               -- The campaign owns the policy; interactions.strategy is a
               -- denormalised copy. Preferring the campaign means a stale copy
               -- can never split one campaign across two strategies in the
               -- comparison that the whole of Module 2 rests on.
               COALESCE(c.strategy, i.strategy, 'none') AS strategy,
               i.event_type, i.source
        FROM interactions i
        LEFT JOIN campaigns c ON c.id = i.campaign_id
        WHERE i.site_id = :s
          AND i.event_type IN ('sent', 'open', 'click', 'convert')
        """,
        s=site_id,
    )

    # 2. The acquisition touch — how each visitor first reached the site.
    #    Treated as a 'click' because arriving via a channel is an active
    #    engagement with it, which is what an attribution model credits.
    acquisition = db.fetch_all(
        """
        SELECT v.id                                   AS user_id,
               v.first_seen                           AS timestamp,
               'web'                                  AS channel,
               COALESCE(NULLIF(v.utm_source, ''), 'direct') AS platform,
               'none'                                 AS campaign_id,
               'none'                                 AS strategy,
               'click'                                AS event_type,
               v.source                               AS source
        FROM visitors v
        WHERE v.site_id = :s
        """,
        s=site_id,
    )

    # 3. On-site conversions that no campaign click preceded. They are real
    #    business outcomes and belong in the funnel even though no campaign
    #    may claim them.
    organic = db.fetch_all(
        """
        SELECT e.visitor_id AS user_id, e.occurred_at AS timestamp,
               'web' AS channel,
               COALESCE(NULLIF(v.utm_source, ''), 'direct') AS platform,
               'none' AS campaign_id, 'none' AS strategy,
               'convert' AS event_type,
               v.source AS source
        FROM events e
        JOIN visitors v ON v.id = e.visitor_id
        WHERE e.site_id = :s AND e.event_type IN ('purchase', 'convert')
          AND NOT EXISTS (
              SELECT 1 FROM interactions i
              WHERE i.visitor_id = e.visitor_id AND i.event_type = 'convert')
        """,
        s=site_id,
    )

    rows = email + acquisition + organic
    if not rows:
        return pd.DataFrame(columns=["user_id", "timestamp", "channel", "platform",
                                     "campaign_id", "strategy", "event_type", "source"])

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["user_id"] = df["user_id"].astype(str)
    return df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)


def segment_frame(site_id: int) -> pd.DataFrame:
    """Segments in the schema Module 3 expects (user_id, segment, confidence)."""
    rows = db.fetch_all(
        """
        SELECT visitor_id AS user_id, segment_name, segment_confidence
        FROM user_segments WHERE site_id = :s
        """,
        s=site_id,
    )
    if not rows:
        return pd.DataFrame(columns=["user_id", "segment", "confidence"])

    # Route through the adapter rather than lower-casing here. Module 1 emits
    # "New Cold User"; Module 3 was trained on "new_cold_customer". A local
    # `.lower().replace(" ", "_")` produced "new_cold_user", which the model's
    # encoder does not recognise — and because it is configured with
    # handle_unknown="ignore", the segment silently became an all-zero vector.
    # Cold-start customers were reaching the model with no segment at all: the
    # same failure as the vote-order defect, one module boundary further on.
    from adapters.segment_labels import to_snake

    df = pd.DataFrame(rows)
    return pd.DataFrame({
        "user_id": df["user_id"].astype(str),
        "segment": df["segment_name"].map(to_snake),
        "confidence": pd.to_numeric(df["segment_confidence"], errors="coerce").fillna(0.5),
    })


def _data_basis(df: pd.DataFrame) -> str:
    """Which audience these numbers rest on — derived from the rows themselves."""
    if df.empty or "source" not in df:
        return "no data yet"
    live = bool((df["source"] == "live").any())
    dataset = bool((df["source"] == "dataset").any())
    return "mixed" if live and dataset else "live" if live else "dataset"


# ── Funnel ───────────────────────────────────────────────────────────────────
def build_funnel(site_id: int) -> dict[str, Any]:
    """Campaign funnel and drop-off, sliced by strategy and by segment."""
    funnel_mod, _, _ = _m3()
    events = journey_events(site_id)

    # The funnel is about the campaign, so acquisition touches are excluded —
    # otherwise every visitor would appear to have "clicked" a campaign.
    campaign = events[events["campaign_id"] != "none"]
    if campaign.empty:
        return {"funnel": {s: 0 for s in funnel_mod.STAGES}, "dropoffs": {},
                "by_strategy": [], "by_segment": [], "data_basis": "no data yet",
                "note": "No campaign has been sent yet."}

    counts = funnel_mod.compute_funnel(campaign)
    dropoffs = funnel_mod.compute_dropoffs(counts)

    by_strategy = funnel_mod.funnel_by(campaign, "strategy").reset_index().to_dict("records")

    segments = segment_frame(site_id)
    by_segment: list[dict] = []
    if not segments.empty:
        merged = campaign.merge(segments[["user_id", "segment"]], on="user_id", how="left")
        merged["segment"] = merged["segment"].fillna("unsegmented")
        by_segment = funnel_mod.funnel_by(merged, "segment").reset_index().to_dict("records")

    return {
        "funnel": counts,
        "dropoffs": dropoffs,
        "by_strategy": by_strategy,
        "by_segment": by_segment,
        "data_basis": _data_basis(campaign),
        "caveat": ("Open counts under-report — most mail clients block the "
                   "tracking pixel. Read sent→click rather than sent→open."),
    }


# ── Attribution ──────────────────────────────────────────────────────────────
def build_attribution(site_id: int, level: str = "platform") -> dict[str, Any]:
    """Compare first-touch, last-touch, linear and Markov attribution."""
    _, attribution, _ = _m3()
    events = journey_events(site_id)

    converters = events.loc[events["event_type"] == "convert", "user_id"].nunique()
    diagnostics = _journey_diagnostics(events, level)

    if converters < MIN_CONVERSIONS_FOR_ATTRIBUTION:
        return {
            "models": {}, "converters": int(converters),
            "data_basis": _data_basis(events),
            "diagnostics": diagnostics,
            "note": (
                f"Only {converters} converting journeys — below the "
                f"{MIN_CONVERSIONS_FOR_ATTRIBUTION} needed for attribution to mean "
                "anything. Reported as unavailable rather than as a number."
            ),
        }

    models: dict[str, Any] = {}
    for name, fn in (
        ("first_touch", attribution.first_touch_attribution),
        ("last_touch", attribution.last_touch_attribution),
        ("linear", attribution.linear_multi_touch_attribution),
        ("markov", attribution.markov_chain_attribution),
    ):
        try:
            frame = fn(events, level=level)
            models[name] = frame.to_dict("records")
        except Exception as exc:                       # pragma: no cover
            log.warning("attribution model %s failed: %s", name, exc)
            models[name] = {"error": str(exc)[:200]}

    return {
        "models": models,
        "level": level,
        "converters": int(converters),
        "data_basis": _data_basis(events),
        "diagnostics": diagnostics,
    }


def _journey_diagnostics(events: pd.DataFrame, level: str) -> dict[str, Any]:
    """How much structure the attribution actually had to work with.

    A single-touch journey makes every attribution model agree by construction.
    Without this, that agreement reads as a robust finding instead of an artefact.
    """
    if events.empty:
        return {"single_touch_share": None}

    meaningful = events[events["event_type"].isin({"open", "click", "convert"})]
    converters = meaningful.loc[meaningful["event_type"] == "convert", "user_id"].unique()
    if len(converters) == 0:
        return {"single_touch_share": None, "n_converting_journeys": 0}

    journeys = meaningful[meaningful["user_id"].isin(converters)]
    touches = journeys[journeys["event_type"] != "convert"].groupby("user_id")[level].nunique()

    single = int((touches <= 1).sum())
    total = int(len(touches)) or 1
    return {
        "n_converting_journeys": total,
        "mean_distinct_touchpoints": round(float(touches.mean()), 2) if total else 0.0,
        "single_touch_journeys": single,
        "single_touch_share": round(single / total, 3),
        "note": (
            "Attribution models can only disagree where a journey has more than "
            "one touchpoint; agreement on single-touch journeys is arithmetic, "
            "not evidence."
        ) if single else None,
    }


# ── Prediction + recommendations ─────────────────────────────────────────────
def build_predictions(site_id: int) -> dict[str, Any]:
    """Per-visitor conversion probability, drop-off risk and next-best action.

    Persists to `analytics_output` (Figure 5.4), which is what Modules 2 and 4
    read to close the loop.
    """
    _, _, features_mod = _m3()
    events = journey_events(site_id)
    segments = segment_frame(site_id)

    if events.empty or segments.empty:
        return {"n_users": 0, "note": "Need tracked visitors and segments first.",
                "data_basis": "no data yet"}

    feature_df = features_mod.build_features(events, segments)

    model_note = (
        "Conversion and drop-off models were fitted on Module 3's simulator, not "
        "on this audience. Applying them here is a transfer across distributions: "
        "the ranking is usable, the absolute probabilities are not calibrated for "
        "this site."
    )
    if len(feature_df) >= MIN_USERS_FOR_LOCAL_TRAINING:
        model_note = (
            f"{len(feature_df)} users available — enough to refit on this site's own "
            "data. Retraining is not automatic; run the Module 3 pipeline to do it."
        )

    records, source = _score(site_id, feature_df, events)

    if records:
        db.execute_many(
            """
            INSERT INTO analytics_output (site_id, visitor_id, predicted_conversion,
                                          drop_off_risk, recommendation,
                                          recommended_platform, attribution_model,
                                          confidence, model_version, computed_at)
            VALUES (:site_id, :visitor_id, :pc, :dr, :rec, :plat, :attr,
                    :conf, :ver, now())
            ON CONFLICT (visitor_id) DO UPDATE SET
                predicted_conversion = EXCLUDED.predicted_conversion,
                drop_off_risk        = EXCLUDED.drop_off_risk,
                recommendation       = EXCLUDED.recommendation,
                recommended_platform = EXCLUDED.recommended_platform,
                attribution_model    = EXCLUDED.attribution_model,
                confidence           = EXCLUDED.confidence,
                model_version        = EXCLUDED.model_version,
                computed_at          = now()
            """,
            records,
        )

    # Record what was decided, with the probability it was decided under. The
    # recommendation in `analytics_output` is overwritten on every run and so
    # cannot serve as evidence about anything; this log is append-only and is
    # what makes the policy improvable later. See api/services/decisions.py.
    from api.services import decisions as decision_log

    segment_of = dict(zip(feature_df["user_id"].astype(str),
                          feature_df.get("segment", pd.Series(dtype=str))))

    logged = decision_log.log_decisions(site_id, [
        {"visitor_id": r["visitor_id"], "greedy": r["rec"],
         # The features as they were at the moment of the decision, so a model
         # refitted later trains on what was known then, not on what is known
         # now — the difference between learning a policy and reading the future.
         "context": {"predicted_conversion": r["pc"], "drop_off_risk": r["dr"],
                     "segment": segment_of.get(str(r["visitor_id"]))}}
        for r in records
    ])
    rewards = decision_log.attach_rewards(site_id)

    mix: dict[str, int] = {}
    for r in records:
        mix[r["rec"]] = mix.get(r["rec"], 0) + 1

    n = len(records) or 1
    return {
        "n_users": len(records),
        "source": source,
        "model_note": model_note,
        "data_basis": _data_basis(events),
        "recommendation_mix": mix,
        "avg_predicted_conversion": round(sum(r["pc"] for r in records) / n, 4),
        "avg_drop_off_risk": round(sum(r["dr"] for r in records) / n, 4),
        "high_intent_users": sum(1 for r in records if r["pc"] >= 0.5),
        "at_risk_users": sum(1 for r in records if r["dr"] >= 0.6),
        "calibration_warnings": _calibration_warnings(records),
        "decision_log": {**logged, **rewards},
    }


def _calibration_warnings(records: list[dict]) -> list[str]:
    """Flag prediction distributions that are degenerate on this audience.

    A model transferred from one distribution to another often still *ranks*
    correctly while producing probabilities that are all crushed towards one
    end. That is easy to miss when only the mean is reported, and it silently
    invalidates any threshold — "at risk above 0.6" means nothing if nothing
    ever reaches 0.6. Better to say so than to publish a confident-looking zero.
    """
    if len(records) < 10:
        return []

    warnings: list[str] = []
    for field, label, threshold in (("pc", "conversion probability", 0.5),
                                    ("dr", "drop-off risk", 0.6)):
        values = [r[field] for r in records]
        spread = max(values) - min(values)
        above = sum(1 for v in values if v >= threshold)

        if spread < 0.05:
            warnings.append(
                f"Predicted {label} is nearly constant across all "
                f"{len(records)} visitors (range {spread:.3f}) — the model is not "
                "discriminating on this data."
            )
        elif above == 0:
            warnings.append(
                f"No visitor reaches the {threshold:.0%} {label} threshold "
                f"(highest is {max(values):.1%}). The threshold was set for the "
                "distribution the model was fitted on and does not transfer; "
                "rank visitors instead of thresholding them."
            )
    return warnings


def _score(site_id: int, feature_df: pd.DataFrame,
           events: pd.DataFrame) -> tuple[list[dict], str]:
    """Run Module 3's trained models, falling back to its rule logic."""
    import joblib

    from api.services import _recommend_rules as rules   # local import, see below

    try:
        from src.prediction import FEATURES  # type: ignore
        conv = joblib.load(MODELS_DIR / "conversion_xgboost.pkl")
        drop = joblib.load(MODELS_DIR / "drop_off_xgboost.pkl")
        p_conv = conv.predict_proba(feature_df[FEATURES])[:, 1]
        p_drop = drop.predict_proba(feature_df[FEATURES])[:, 1]
        source = "Module 3 XGBoost models (fitted on simulated data)"
    except Exception as exc:
        log.warning("trained models unavailable (%s) — using rule fallback", exc)
        p_conv, p_drop = rules.heuristic_scores(feature_df)
        source = f"rule-based fallback ({type(exc).__name__})"

    best_platform = _best_platform_per_user(events)

    frame = feature_df.reset_index(drop=True)

    # Decided by rank across this audience, not by the absolute cut-offs Module
    # 3's rule uses. Those cut-offs belong to the distribution the models were
    # fitted on; see rank_based_actions() and experiment E5.
    actions = rules.rank_based_actions(
        p_conv, p_drop, frame.get("segment", pd.Series([""] * len(frame))))

    records = []
    for i, row in frame.iterrows():
        pc, dr = float(p_conv[i]), float(p_drop[i])
        records.append({
            "site_id": site_id,
            "visitor_id": int(row["user_id"]),
            "pc": round(pc, 4),
            "dr": round(dr, 4),
            "rec": actions[i],
            "plat": best_platform.get(str(row["user_id"]), "email"),
            "attr": "last_touch",
            "conf": round(rules.confidence(pc, dr), 4),
            "ver": "m3-analytics-1.0",
        })
    return records, source


def _best_platform_per_user(events: pd.DataFrame) -> dict[str, str]:
    """The platform each visitor engaged with most — used to target follow-ups."""
    engaged = events[events["event_type"].isin({"open", "click"})]
    if engaged.empty:
        return {}
    counts = engaged.groupby(["user_id", "platform"]).size().reset_index(name="n")
    best = counts.sort_values("n", ascending=False).drop_duplicates("user_id")
    return dict(zip(best["user_id"].astype(str), best["platform"]))


# ── Full run ─────────────────────────────────────────────────────────────────
def run_analytics(site_id: int) -> dict[str, Any]:
    """Funnel + attribution + predictions in one pass."""
    funnel = build_funnel(site_id)
    attribution = build_attribution(site_id)
    predictions = build_predictions(site_id)
    insights = _insights(funnel, attribution, predictions)

    db.execute(
        """INSERT INTO pipeline_runs (site_id, stage, status, detail, finished_at)
           VALUES (:s, 'analytics', 'ok', CAST(:d AS jsonb), now())""",
        s=site_id,
        d=json.dumps({"funnel": funnel["funnel"], "n_users": predictions.get("n_users")}),
    )

    return {"funnel": funnel, "attribution": attribution,
            "predictions": predictions, "insights": insights}


def _insights(funnel: dict, attribution: dict, predictions: dict) -> list[str]:
    """Plain-language findings, each tied to a number a reader can check."""
    out: list[str] = []
    counts, drops = funnel.get("funnel", {}), funnel.get("dropoffs", {})

    if counts.get("sent"):
        biggest = max(drops.items(), key=lambda kv: kv[1], default=None)
        if biggest:
            out.append(
                f"The largest drop-off is {biggest[0]} at {biggest[1]:.0%} — "
                "that is where the campaign loses most people."
            )
        if counts.get("click"):
            rate = counts.get("convert", 0) / counts["click"]
            out.append(
                f"{rate:.0%} of visitors who clicked went on to convert "
                f"({counts.get('convert', 0)} of {counts['click']})."
            )

    diag = attribution.get("diagnostics") or {}
    if diag.get("single_touch_share") is not None:
        out.append(
            f"{diag['single_touch_share']:.0%} of converting journeys had a single "
            f"touchpoint (mean {diag.get('mean_distinct_touchpoints')} distinct "
            "platforms), so attribution models agree largely by construction."
        )

    if predictions.get("n_users"):
        out.append(
            f"{predictions['high_intent_users']} visitors are scored above 50% "
            f"conversion likelihood and {predictions['at_risk_users']} above 60% "
            "drop-off risk."
        )
    out.extend(predictions.get("calibration_warnings", []))

    basis = funnel.get("data_basis")
    if basis in ("simulated", "mixed"):
        out.append(
            f"These figures rest on {basis} data — simulated visitors are included, "
            "so they demonstrate the pipeline rather than measure an audience."
        )
    return out
