"""E7 — The engagement regressor, including the part where it fails.

Module 4 scores generated captions partly on predicted engagement. The original
model reported R² ≈ 0.99, which would be extraordinary for predicting social
engagement from wording alone. It was extraordinary: `likes`, `comments`,
`shares` and `impressions` were left among the features while the target was
their ratio, so the model was handed its own answer.

The failure was invisible in training and fatal in use. A caption that has not
been posted yet has no like count, so at prediction time those four columns were
filled with zeros — far outside anything the model had seen — and the score
driving 45% of every content ranking became noise.

This experiment does three things:

1.  **Reproduces the leak.** Trains with and without the outcome columns on the
    same split, so the report can show 0.99 → the real number rather than assert
    the correction happened.

2.  **Scores the honest model against a mean baseline**, on R², Spearman and
    MAE with bootstrap intervals. Spearman is the metric that matters: the model
    exists to *rank* candidate captions, not to predict an engagement rate, and
    rank correlation is what ranking needs.

3.  **Tests whether the dataset carries any text signal at all.** Each feature
    is correlated with the target and the p-values are corrected for testing
    eight of them (Holm–Bonferroni — with eight tests at α=0.05 there is a ~34%
    chance of at least one spurious "significant" result). If nothing survives,
    the conclusion is about the data rather than the model, and the right
    response is to cut the model's weight in the score — which is what was done.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import config
from research.stats import bootstrap_ci

ID = "E7"
TITLE = "Module 4 — engagement prediction, leakage and the absence of signal"


def _fit_and_score(x_train, y_train, x_test, y_test, seed: int) -> dict:
    from scipy.stats import spearmanr
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score

    model = RandomForestRegressor(n_estimators=200, random_state=seed)
    model.fit(x_train, y_train)
    pred = model.predict(x_test)

    rho = spearmanr(y_test, pred).statistic
    return {
        "r2": float(r2_score(y_test, pred)),
        "spearman": float(rho) if rho == rho else 0.0,
        "mae": float(mean_absolute_error(y_test, pred)),
        "predictions": pred,
    }


def run() -> dict:
    import config as project_config

    dataset = project_config.ENGAGEMENT_DATASET_CSV
    if not dataset.exists():
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": f"engagement dataset not found at {dataset}"}

    import engagement
    from scipy.stats import pearsonr
    from sklearn.model_selection import train_test_split

    raw = engagement._load_engagement_csv()
    features = engagement.extract_features(raw).fillna(0)
    target = features["engagement_rate"].to_numpy()

    clean_columns = engagement.model_feature_columns(features)
    # The notebook's selection: everything except the text and the target — which
    # silently kept the four outcome columns.
    #
    # `sorted` is load-bearing, not tidiness. LEAKY_COLUMNS is a set, and set
    # iteration order over strings varies between processes because Python
    # randomises string hashing per interpreter. That reordered the feature
    # matrix on every run, changed how the forest broke ties between equally
    # good splits, and moved the reported R² in the fourth decimal — a
    # reproducibility bug in the experiment whose entire subject is a
    # reproducibility bug.
    leaky_columns = clean_columns + sorted(
        c for c in engagement.LEAKY_COLUMNS
        if c != "engagement_rate" and c in features.columns)

    idx_train, idx_test = train_test_split(
        np.arange(len(features)), test_size=0.2, random_state=config.SEED)

    x_clean = features[clean_columns].to_numpy(dtype=float)
    x_leaky = features[leaky_columns].to_numpy(dtype=float)

    clean = _fit_and_score(x_clean[idx_train], target[idx_train],
                           x_clean[idx_test], target[idx_test], config.SEED)
    leaky = _fit_and_score(x_leaky[idx_train], target[idx_train],
                           x_leaky[idx_test], target[idx_test], config.SEED)

    # A model that always predicts the training mean.
    from sklearn.metrics import mean_absolute_error, r2_score
    baseline_pred = np.full(len(idx_test), float(target[idx_train].mean()))
    baseline = {
        "r2": float(r2_score(target[idx_test], baseline_pred)),
        "spearman": 0.0,
        "mae": float(mean_absolute_error(target[idx_test], baseline_pred)),
    }

    y_test = target[idx_test]
    idx = np.arange(len(y_test))

    def spearman_of(sample, pred):
        from scipy.stats import spearmanr
        rho = spearmanr(y_test[sample], pred[sample]).statistic
        return float(rho) if rho == rho else 0.0

    clean_rho = bootstrap_ci(idx, lambda s: spearman_of(s, clean["predictions"]),
                             n_resamples=2_000)
    clean_r2 = bootstrap_ci(
        idx, lambda s: float(r2_score(y_test[s], clean["predictions"][s])),
        n_resamples=2_000)

    comparison = [{
        "feature_set": "with outcome columns (original)",
        "n_features": len(leaky_columns),
        "r2": round(leaky["r2"], 4),
        "spearman": round(leaky["spearman"], 4),
        "mae": round(leaky["mae"], 5),
    }, {
        "feature_set": "text features only (corrected)",
        "n_features": len(clean_columns),
        "r2": round(clean["r2"], 4),
        "spearman": round(clean["spearman"], 4),
        "spearman_ci_low": round(clean_rho.low, 4),
        "spearman_ci_high": round(clean_rho.high, 4),
        "r2_ci_low": round(clean_r2.low, 4),
        "r2_ci_high": round(clean_r2.high, 4),
        "mae": round(clean["mae"], 5),
    }, {
        "feature_set": "baseline (predict the mean)",
        "n_features": 0,
        "r2": round(baseline["r2"], 4),
        "spearman": 0.0,
        "mae": round(baseline["mae"], 5),
    }]

    # ── Is there any text signal in this dataset at all? ─────────────────────
    tests = []
    for column in engagement.TEXT_FEATURES:
        if column not in features:
            continue
        values = features[column].to_numpy(dtype=float)
        if np.std(values) == 0:
            tests.append({"feature": column, "pearson_r": 0.0, "p_value": 1.0,
                          "note": "constant"})
            continue
        r, p = pearsonr(values, target)
        tests.append({"feature": column, "pearson_r": round(float(r), 4),
                      "p_value": float(p)})

    # Holm–Bonferroni: sort ascending, compare p(i) against alpha/(m − i).
    m = len(tests)
    for rank, row in enumerate(sorted(tests, key=lambda t: t["p_value"])):
        row["holm_threshold"] = round(0.05 / (m - rank), 5)
        row["significant_after_correction"] = bool(
            row["p_value"] < row["holm_threshold"])
    tests.sort(key=lambda t: t["p_value"])
    for row in tests:
        row["p_value"] = round(row["p_value"], 4)

    any_signal = any(t["significant_after_correction"] for t in tests)

    notes = [
        "The leaky model scores far better on every metric. That is the point: "
        "nothing about the training run flags the defect, and the corrected "
        "number looks like a regression to anyone reading only the headline.",
        "Spearman is the metric to read. The model ranks candidate captions; it "
        "is not required to predict an engagement rate in absolute terms.",
    ]
    if not any_signal:
        notes.append(
            f"None of the {m} text features correlates with engagement after "
            "Holm–Bonferroni correction. This is a property of the dataset, not "
            "a modelling failure — no model can extract a signal that is not "
            "there, and the honest response is to reduce the weight this score "
            "carries in content ranking rather than to keep tuning.")
    if clean_rho.low <= 0 <= clean_rho.high:
        notes.append(
            f"The corrected model's rank correlation is {clean['spearman']:.3f} "
            f"[{clean_rho.low:.3f}, {clean_rho.high:.3f}] — the interval spans "
            "zero, so no ranking skill is demonstrated on held-out data.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "n_rows": int(len(features)),
            "leaky_r2": round(leaky["r2"], 4),
            "clean_r2": round(clean["r2"], 4),
            "clean_r2_ci": [round(clean_r2.low, 4), round(clean_r2.high, 4)],
            "clean_spearman": round(clean["spearman"], 4),
            "clean_spearman_ci": [round(clean_rho.low, 4), round(clean_rho.high, 4)],
            "baseline_r2": round(baseline["r2"], 4),
            "features_with_signal": sum(
                1 for t in tests if t["significant_after_correction"]),
            "n_features_tested": m,
        },
        "tables": {
            "e7_leakage_comparison": comparison,
            "e7_feature_signal": tests,
        },
        "notes": notes,
    }
