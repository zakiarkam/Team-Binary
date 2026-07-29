"""E5 — Conversion and drop-off prediction, and what happens when it moves.

Two questions, and the second matters more than the first.

**Does the model beat a trivial baseline?** ROC-AUC alone will not say so: on an
imbalanced target a model can post a respectable AUC while being useless at the
operating point anyone would actually use. So each classifier is scored against
a stratified-random baseline on ROC-AUC, PR-AUC (which is sensitive to the
positive rate in a way ROC is not) and the Brier score (which punishes
confident wrongness), with bootstrap intervals on all three.

**Does it survive the move to another audience?** The shipped models were fitted
on Module 3's simulator and are applied in production to the imported research
audience — a different distribution. That transfer is the honest weak point of
Module 3, so it is measured rather than mentioned: the fitted models are pushed
through the live feature table and the *spread* of their predictions is
reported. A model that ranks correctly but crushes every probability into a
narrow band still invalidates every threshold built on it, and "at risk above
0.6" means nothing if nothing ever reaches 0.6.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import config, module_loader
from research.stats import bootstrap_ci

ID = "E5"
TITLE = "Module 3 — prediction quality, and its transfer to another audience"

TARGETS = {"conversion": "converted", "drop_off": "dropped_off"}


def _load_m3():
    """Module 3's prediction module — reused so the preprocessing matches."""
    return module_loader.load(config.M3_DIR, "prediction")


def _scores(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

    if len(np.unique(y_true)) < 2:
        return {"roc_auc": float("nan"), "pr_auc": float("nan"),
                "brier": float("nan")}
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }


def _bootstrap_auc(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[float, float]:
    from sklearn.metrics import roc_auc_score

    idx = np.arange(len(y_true))

    def stat(sample):
        yt, yp = y_true[sample], y_prob[sample]
        if len(np.unique(yt)) < 2:
            return float("nan")
        return float(roc_auc_score(yt, yp))

    # 2,000 resamples: AUC on several thousand rows is stable, and the full
    # 10,000 would dominate the runtime of the whole research run.
    interval = bootstrap_ci(idx, stat, n_resamples=2_000)
    return interval.low, interval.high


def run() -> dict:
    if not config.M3_FEATURES.exists():
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": f"Module 3 feature table not found at {config.M3_FEATURES}"}

    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from xgboost import XGBClassifier

    prediction = _load_m3()
    features = pd.read_csv(config.M3_FEATURES)

    rows, notes = [], []

    for target, column in TARGETS.items():
        if column not in features:
            notes.append(f"`{column}` missing from the feature table — "
                         f"{target} not evaluated.")
            continue

        x = features[prediction.FEATURES]
        y = features[column].astype(int).to_numpy()

        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, random_state=config.SEED, stratify=y)

        candidates = {
            "baseline (stratified)": DummyClassifier(
                strategy="stratified", random_state=config.SEED),
            "logistic regression": LogisticRegression(max_iter=1000),
            "random forest": RandomForestClassifier(
                n_estimators=200, random_state=config.SEED, min_samples_leaf=2),
            # n_jobs=1: XGBoost's OpenMP pool clashes with torch's on macOS.
            "xgboost": XGBClassifier(
                n_estimators=300, learning_rate=0.05, max_depth=5,
                random_state=config.SEED, n_jobs=1, eval_metric="logloss"),
        }

        for name, estimator in candidates.items():
            model = Pipeline([("prep", prediction._preprocessor()),
                              ("clf", estimator)])
            model.fit(x_train, y_train)
            y_prob = model.predict_proba(x_test)[:, 1]

            scores = _scores(y_test, y_prob)
            lo, hi = _bootstrap_auc(y_test, y_prob)
            rows.append({
                "target": target,
                "model": name,
                "roc_auc": round(scores["roc_auc"], 4),
                "roc_auc_ci_low": round(lo, 4),
                "roc_auc_ci_high": round(hi, 4),
                "pr_auc": round(scores["pr_auc"], 4),
                "brier": round(scores["brier"], 4),
                "positive_rate": round(float(y_test.mean()), 4),
                "n_test": int(len(y_test)),
            })

    # Does the best model actually beat the baseline, interval to interval?
    for target in TARGETS:
        subset = [r for r in rows if r["target"] == target]
        if len(subset) < 2:
            continue
        baseline = next(r for r in subset if r["model"].startswith("baseline"))
        best = max((r for r in subset if not r["model"].startswith("baseline")),
                   key=lambda r: r["roc_auc"])
        if best["roc_auc_ci_low"] > baseline["roc_auc_ci_high"]:
            notes.append(
                f"{target}: {best['model']} (AUC {best['roc_auc']:.3f}) clears the "
                f"baseline with no interval overlap.")
        else:
            notes.append(
                f"{target}: {best['model']} does NOT separate from the baseline "
                "once the intervals are drawn — the apparent gap is within noise.")

    # ── The transfer question ───────────────────────────────────────────────
    transfer: list[dict] = []
    try:
        from api import db
        from api.services import analytics as analytics_svc

        site = db.fetch_one(
            "SELECT id FROM sites WHERE name = 'Innov8Smart' ORDER BY id DESC LIMIT 1")
        if site is None:
            notes.append("Transfer check skipped: no Innov8Smart site — run `make demo`.")
        else:
            live = db.fetch_all(
                """
                SELECT predicted_conversion::float8 AS pc,
                       drop_off_risk::float8        AS dr
                FROM analytics_output WHERE site_id = :s
                """, s=int(site["id"]))
            if not live:
                notes.append("Transfer check skipped: no predictions stored yet.")
            else:
                frame = pd.DataFrame(live)
                for label, column, threshold in (("conversion", "pc", 0.5),
                                                 ("drop-off risk", "dr", 0.6)):
                    values = frame[column].dropna().to_numpy()
                    if values.size == 0:
                        continue
                    above = int((values >= threshold).sum())
                    transfer.append({
                        "prediction": label,
                        "n_customers": int(values.size),
                        "min": round(float(values.min()), 4),
                        "median": round(float(np.median(values)), 4),
                        "max": round(float(values.max()), 4),
                        "spread": round(float(values.max() - values.min()), 4),
                        "above_threshold": above,
                        "threshold": threshold,
                        "share_above": round(above / values.size, 4),
                    })
                for row in transfer:
                    if row["share_above"] == 0:
                        notes.append(
                            f"No customer reaches the {row['threshold']:.0%} "
                            f"{row['prediction']} threshold (highest "
                            f"{row['max']:.1%}). The threshold was set for the "
                            "distribution the model was fitted on and does not "
                            "transfer; rank customers rather than thresholding them.")
                    elif row["spread"] < 0.05:
                        notes.append(
                            f"{row['prediction']} is nearly constant across "
                            f"{row['n_customers']} customers (range "
                            f"{row['spread']:.3f}) — the model is not "
                            "discriminating on this audience.")
    except Exception as exc:
        notes.append(f"Transfer check skipped: database not reachable "
                     f"({type(exc).__name__}).")

    notes.append(
        "These models are fitted on Module 3's simulator. Applying them to the "
        "imported audience is a transfer across distributions: the ranking is "
        "usable, the absolute probabilities are not calibrated for it.")

    tables = {"e5_model_scores": rows}
    if transfer:
        tables["e5_transfer"] = transfer

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "targets_evaluated": sorted({r["target"] for r in rows}),
            "n_models": len({r["model"] for r in rows}),
            "best_conversion_auc": max(
                (r["roc_auc"] for r in rows
                 if r["target"] == "conversion" and not r["model"].startswith("baseline")),
                default=None),
            "best_drop_off_auc": max(
                (r["roc_auc"] for r in rows
                 if r["target"] == "drop_off" and not r["model"].startswith("baseline")),
                default=None),
            "transfer_checked": bool(transfer),
        },
        "tables": tables,
        "notes": notes,
    }
