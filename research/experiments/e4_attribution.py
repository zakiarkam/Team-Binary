"""E4 — Four attribution models, and the fact that they disagree.

Attribution is the part of this project where the honest finding is a negative
one. First-touch, last-touch, linear and Markov are all run on the same
journeys, and they hand the credit to different channels. That is not a bug in
one of them: they encode different beliefs about what a touchpoint is worth,
and on real journeys those beliefs diverge. A company that reads only its
last-touch dashboard concludes email is everything and cuts the spend that
built the audience.

Two settings, and they answer different questions:

*   **Scored against ground truth.** Module 3's simulator knows each channel's
    true influence, so on that data the models can be *ranked* by mean absolute
    error, not merely compared. This is the only place in the project where
    "which attribution model is right" is answerable at all.

*   **On the live journeys.** The imported research audience produces real
    multi-touch paths — an acquisition channel plus email engagement. Here
    there is no ground truth, so what gets reported is the disagreement itself,
    with the diagnostics that say how much structure the models had to work
    with. Attribution models agree by arithmetic on single-touch journeys, and
    that agreement must never be mistaken for corroboration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import config, module_loader
from research.stats import bootstrap_ci

ID = "E4"
TITLE = "Module 3 — attribution model comparison and disagreement"

MODELS = ("first_touch", "last_touch", "linear", "markov")


def _load_m3():
    """Module 3's attribution implementations — the same code the API runs."""
    return module_loader.load(config.M3_DIR, "attribution")


def _credit_vector(rows, channels: list[str]) -> np.ndarray:
    """Model output as a dense vector over a fixed channel order."""
    lookup = {}
    if isinstance(rows, list):
        for r in rows:
            key = r.get("platform") or r.get("channel")
            if key is not None:
                lookup[str(key)] = float(r.get("credit", 0.0))
    return np.array([lookup.get(c, 0.0) for c in channels])


def _disagreement(vectors: dict[str, np.ndarray]) -> dict:
    """How far apart the models are.

    Total variation distance (half the L1 distance) between each pair of credit
    vectors: 0 means identical allocations, 1 means they share no credit at all.
    """
    names = list(vectors)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            tvd = float(np.abs(vectors[a] - vectors[b]).sum() / 2)
            pairs.append({"model_a": a, "model_b": b,
                          "total_variation_distance": round(tvd, 4)})
    values = [p["total_variation_distance"] for p in pairs]
    return {
        "pairs": pairs,
        "max": round(max(values), 4) if values else 0.0,
        "mean": round(float(np.mean(values)), 4) if values else 0.0,
    }


def _ground_truth_study(attribution) -> tuple[list[dict], dict, list[str]]:
    """Score the four models where the true influence is known."""
    notes: list[str] = []
    if not (config.M3_EVENTS.exists() and config.M3_GROUND_TRUTH.exists()):
        return [], {}, ["Module 3 simulated journeys not found — "
                        "ground-truth scoring skipped."]

    events = pd.read_csv(config.M3_EVENTS)
    events["timestamp"] = pd.to_datetime(events["timestamp"])
    truth = pd.read_csv(config.M3_GROUND_TRUTH)

    comparison = attribution.compare_to_ground_truth(events, truth, level="platform")
    mae = attribution.attribution_mae(comparison)

    # A CI on each MAE by resampling the channels the error is averaged over.
    # Few channels, so the interval is wide — which is the honest signal that
    # "model X has the lowest MAE" is a weaker claim than a point estimate
    # makes it look.
    rows = []
    for model, column in (("first_touch", "ae_first_touch"),
                          ("last_touch", "ae_last_touch"),
                          ("linear", "ae_multi_touch"),
                          ("markov", "ae_markov")):
        if column not in comparison:
            continue
        errors = comparison[column].to_numpy(dtype=float)
        interval = bootstrap_ci(errors, lambda e: float(np.mean(e)))
        rows.append({
            "model": model,
            "mae": round(float(np.mean(errors)), 4),
            "ci_low": round(interval.low, 4),
            "ci_high": round(interval.high, 4),
            "n_channels": int(len(errors)),
        })

    rows.sort(key=lambda r: r["mae"])
    if len(rows) >= 2 and rows[0]["ci_high"] > rows[1]["ci_low"]:
        notes.append(
            f"{rows[0]['model']} has the lowest error, but its interval overlaps "
            f"{rows[1]['model']}'s — with only {rows[0]['n_channels']} channels to "
            "average over, the ranking is suggestive rather than established.")

    return rows, mae, notes


def _live_study(attribution) -> tuple[dict, list[str]]:
    """Run the four models on the imported audience's real journeys."""
    try:
        from api import db
        from api.services import analytics as analytics_svc
    except Exception as exc:                                   # pragma: no cover
        return {}, [f"API package unavailable ({type(exc).__name__})"]

    try:
        site = db.fetch_one(
            "SELECT id FROM sites WHERE name = 'Innov8Smart' ORDER BY id DESC LIMIT 1")
        if site is None:
            return {}, ["no Innov8Smart site — run `make demo` first"]
        result = analytics_svc.build_attribution(int(site["id"]), level="platform")
    except Exception as exc:
        return {}, [f"database not reachable ({type(exc).__name__})"]

    models = result.get("models") or {}
    if not models:
        return {}, [result.get("note") or "attribution unavailable on the live build"]

    channels = sorted({
        str(r.get("platform"))
        for rows in models.values() if isinstance(rows, list)
        for r in rows if r.get("platform")})

    vectors = {name: _credit_vector(rows, channels)
               for name, rows in models.items() if isinstance(rows, list)}

    table = []
    for name, vector in vectors.items():
        for channel, credit in zip(channels, vector):
            table.append({"model": name, "channel": channel,
                          "credit": round(float(credit), 4)})

    diagnostics = result.get("diagnostics") or {}
    notes = []
    share = diagnostics.get("single_touch_share")
    if share is not None:
        notes.append(
            f"{share:.0%} of converting journeys had a single touchpoint "
            f"(mean {diagnostics.get('mean_distinct_touchpoints')} distinct "
            "channels). On those, every model agrees by arithmetic — the "
            "agreement is not evidence.")

    return {
        "channels": channels,
        "credits": table,
        "disagreement": _disagreement(vectors),
        "converters": result.get("converters"),
        "data_basis": result.get("data_basis"),
        "diagnostics": diagnostics,
    }, notes


def run() -> dict:
    attribution = _load_m3()

    truth_rows, mae, truth_notes = _ground_truth_study(attribution)
    live, live_notes = _live_study(attribution)

    if not truth_rows and not live:
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": "; ".join(truth_notes + live_notes) or "no inputs available"}

    tables: dict[str, list[dict]] = {}
    if truth_rows:
        tables["e4_ground_truth_mae"] = truth_rows
    if live:
        tables["e4_live_credits"] = live["credits"]
        tables["e4_live_disagreement"] = live["disagreement"]["pairs"]

    metrics: dict = {}
    if truth_rows:
        metrics["best_model_vs_ground_truth"] = truth_rows[0]["model"]
        metrics["best_model_mae"] = truth_rows[0]["mae"]
        metrics["worst_model_mae"] = truth_rows[-1]["mae"]
    if live:
        metrics["live_converters"] = live["converters"]
        metrics["live_data_basis"] = live["data_basis"]
        metrics["max_pairwise_disagreement"] = live["disagreement"]["max"]
        metrics["mean_pairwise_disagreement"] = live["disagreement"]["mean"]
        metrics["single_touch_share"] = live["diagnostics"].get("single_touch_share")

        worst = max(live["disagreement"]["pairs"],
                    key=lambda p: p["total_variation_distance"])
        live_notes.append(
            f"{worst['model_a']} and {worst['model_b']} disagree over "
            f"{worst['total_variation_distance']:.0%} of all attributed credit on "
            "the same journeys — the single clearest argument in this project "
            "against trusting one attribution model.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": metrics,
        "tables": tables,
        "notes": truth_notes + live_notes + [
            "Ground-truth scoring is only possible on simulated journeys, where "
            "the true channel influence is known by construction. No such column "
            "exists for a real audience, which is why the live half reports "
            "disagreement rather than accuracy.",
        ],
    }
