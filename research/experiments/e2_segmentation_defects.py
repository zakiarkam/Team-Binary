"""E2 — The two Module 1 defects, reproduced and measured.

Both were found while turning the notebook into a running engine. Neither
announced itself: the broken versions produced *better-looking* numbers than
the fixed ones, which is exactly why they survived review. This experiment runs
the broken and the corrected code side by side so the report can quantify the
damage instead of asserting it.

Defect 1 — target leakage in the Random Forest
    The notebook trained the classifier with `rule_encoded` among its input
    features while the target was the hybrid consensus. Since the rule label is
    a deterministic function of the same features and a major component of the
    consensus, the model was largely reading off its own answer. It scored near
    100% and 6,248 of 8,000 users came out with confidence exactly 1.00.

Defect 2 — the cold-start segment deleted by its own vote
    The notebook's agreement vote tested `ml == hier` *before* it tested
    `rule == New Cold User`. Clustering cannot represent "there is not enough
    evidence about this person" — it must place everyone somewhere — so
    whenever the two clusterings happened to agree, they overruled the rules and
    the cold-start segment was silently emptied. That segment is Novel
    Contribution 1: the system was erasing its own contribution from its output.

The corrected vote resolves cold start second, immediately after unanimity. The
principle is general and worth stating in the report: **a method that cannot
represent a finding does not get a vote on it.**
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from research import config
from research.stats import proportion_ci

ID = "E2"
TITLE = "Module 1 — leakage and the deleted cold-start segment"

NEW_COLD_USER = "New Cold User"


def _vote_notebook(rule: str, ml: str, hier: str) -> tuple[str, float]:
    """The original ordering: clustering agreement is tested first."""
    if rule == ml == hier:
        return rule, 0.95
    if ml == hier:                      # ← before the cold-start test
        return ml, 0.70
    if rule == ml:
        return rule, 0.80
    if rule == hier:
        return rule, 0.75
    return rule, 0.60


def _vote_corrected(rule: str, ml: str, hier: str) -> tuple[str, float]:
    """The shipped ordering: cold start is resolved before clustering agreement."""
    if rule == ml == hier:
        return rule, 0.95
    if rule == NEW_COLD_USER:
        return NEW_COLD_USER, 0.65
    if rule == ml:
        return rule, 0.80
    if rule == hier:
        return rule, 0.75
    if ml == hier:
        return ml, 0.70
    return rule, 0.60


def _fit(x_train, y_train, x_test, y_test, seed: int):
    clf = RandomForestClassifier(
        n_estimators=200, random_state=seed,
        min_samples_leaf=2, class_weight="balanced_subsample")
    clf.fit(x_train, y_train)
    accuracy = float(clf.score(x_test, y_test))
    confidence = clf.predict_proba(x_test).max(axis=1)
    return accuracy, confidence


def run() -> dict:
    if not config.M1_DATASET.exists():
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": f"dataset not found at {config.M1_DATASET}"}

    from modules.m1_segmentation.segment import RESEARCH_FEATURES, research_segmenter

    df = pd.read_csv(config.M1_DATASET)
    result = research_segmenter().fit_predict(df)
    frame = result.frame

    rule = frame["rule_segment"].to_numpy()
    ml = frame["ml_segment"].to_numpy()
    hier = frame["hierarchical_segment"].to_numpy()

    # ── Defect 2: what each vote ordering does to the cold-start segment ─────
    notebook = np.array([_vote_notebook(r, m, h)[0] for r, m, h in zip(rule, ml, hier)])
    corrected = np.array([_vote_corrected(r, m, h)[0] for r, m, h in zip(rule, ml, hier)])

    detected = int((rule == NEW_COLD_USER).sum())
    kept_notebook = int((notebook == NEW_COLD_USER).sum())
    kept_corrected = int((corrected == NEW_COLD_USER).sum())

    conversion = frame["Conversion"].astype(float).to_numpy()
    cold_conversion = (float(conversion[corrected == NEW_COLD_USER].mean())
                       if kept_corrected else float("nan"))
    rest_conversion = (float(conversion[corrected != NEW_COLD_USER].mean())
                       if kept_corrected < len(frame) else float("nan"))

    vote_table = [{
        "vote_order": "notebook (ml == hier tested first)",
        "cold_start_detected_by_rules": detected,
        "cold_start_surviving": kept_notebook,
        "share_lost": round(1 - kept_notebook / detected, 4) if detected else None,
    }, {
        "vote_order": "corrected (cold start resolved second)",
        "cold_start_detected_by_rules": detected,
        "cold_start_surviving": kept_corrected,
        "share_lost": round(1 - kept_corrected / detected, 4) if detected else None,
    }]

    # ── Defect 1: leakage in the inductive classifier ────────────────────────
    features = df[RESEARCH_FEATURES.columns].astype(float).fillna(0.0).to_numpy()
    target = corrected                                    # the hybrid consensus
    rule_encoded = LabelEncoder().fit_transform(rule).reshape(-1, 1)
    leaky_features = np.hstack([features, rule_encoded])

    idx_train, idx_test = train_test_split(
        np.arange(len(df)), test_size=0.2, random_state=config.SEED, stratify=target)

    clean_acc, clean_conf = _fit(features[idx_train], target[idx_train],
                                 features[idx_test], target[idx_test], config.SEED)
    leaky_acc, leaky_conf = _fit(leaky_features[idx_train], target[idx_train],
                                 leaky_features[idx_test], target[idx_test], config.SEED)

    # The notebook's headline symptom was the confidence distribution, not the
    # accuracy — so that is what gets measured, on the full audience.
    _, full_clean_conf = _fit(features[idx_train], target[idx_train],
                              features, target, config.SEED)
    _, full_leaky_conf = _fit(leaky_features[idx_train], target[idx_train],
                              leaky_features, target, config.SEED)

    certain_leaky = int((full_leaky_conf >= 0.9999).sum())
    certain_clean = int((full_clean_conf >= 0.9999).sum())

    leakage_table = [{
        "feature_set": "with rule_encoded (notebook)",
        "held_out_accuracy": round(leaky_acc, 4),
        "users_at_confidence_1.00": certain_leaky,
        "share_at_confidence_1.00": round(certain_leaky / len(df), 4),
        "mean_confidence": round(float(full_leaky_conf.mean()), 4),
    }, {
        "feature_set": "behavioural features only (corrected)",
        "held_out_accuracy": round(clean_acc, 4),
        "users_at_confidence_1.00": certain_clean,
        "share_at_confidence_1.00": round(certain_clean / len(df), 4),
        "mean_confidence": round(float(full_clean_conf.mean()), 4),
    }]

    clean_ci = proportion_ci(int(round(clean_acc * len(idx_test))), len(idx_test))

    # What the leak actually damages, measured rather than assumed. On this
    # reproduction accuracy barely moves — the interesting distortion is in the
    # *certainty*, and that is the more dangerous failure of the two: a model
    # whose accuracy is honest but whose confidence is not will be trusted
    # exactly where it should not be.
    ratio = (certain_leaky / certain_clean) if certain_clean else float("inf")
    notes = [
        f"Leakage barely moves accuracy ({leaky_acc:.4f} against {clean_acc:.4f}) "
        f"but inflates certainty by a factor of {ratio:.0f}: {certain_leaky} users "
        f"come out at confidence 1.00 with the rule label among the inputs, "
        f"against {certain_clean} without it. Accuracy is not what the defect "
        "corrupts — the confidence attached to every downstream decision is.",
        "That is also why it survived review. Nothing fails, no test goes red, "
        "and the only symptom is a confidence column that looks impressive.",
        "Even the corrected accuracy should not be quoted as generalisation to a "
        "new audience. The rule component of the target is a deterministic "
        "function of these same features, so this measures internal consistency; "
        "the engine reports that caveat in its own diagnostics.",
    ]
    if kept_notebook < detected:
        notes.append(
            f"Under the notebook's vote order the cold-start segment loses "
            f"{detected - kept_notebook} of {detected} users on this dataset. On "
            "the live audience it went to zero — a contribution deleted by its "
            "own pipeline.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "cold_start_detected": detected,
            "cold_start_kept_notebook": kept_notebook,
            "cold_start_kept_corrected": kept_corrected,
            "cold_start_conversion": round(cold_conversion, 4),
            "other_segments_conversion": round(rest_conversion, 4),
            "leaky_accuracy": round(leaky_acc, 4),
            "clean_accuracy": round(clean_acc, 4),
            "clean_accuracy_ci": [round(clean_ci.low, 4), round(clean_ci.high, 4)],
            "users_at_certainty_leaky": certain_leaky,
            "users_at_certainty_clean": certain_clean,
        },
        "tables": {
            "e2_vote_order": vote_table,
            "e2_leakage": leakage_table,
        },
        "notes": notes,
    }
