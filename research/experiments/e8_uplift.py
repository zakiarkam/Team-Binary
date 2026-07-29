"""E8 — Who to target is not the same question as who will convert.

The system's recommender ranks customers by **predicted conversion** and gives
the strongest action to the top of that ranking. That is the intuitive thing to
do and it is the wrong question. The right question is not "who will convert?"
but "**for whom does the action change whether they convert?**" — and the two
rankings are not the same list. A customer certain to buy anyway gains nothing
from a discount; the discount is wasted on them.

Answering it needs *counterfactuals*: what this customer would have done had
they received a different action. The project's own audience cannot supply
them. Every imported customer received one treatment, nobody recorded which,
and no comparable customer received an alternative. No model can recover a
causal effect from data where the cause never varied — which is why the
existing `learned_recommender.py` cannot solve this either: it trains on a
label synthesised from `(converted, segment)` while `segment` is one of its own
input features, so its 94% accuracy measures how well it reconstructs a rule.

So this experiment moves to data that *can* answer it: the **Hillstrom
MineThatData** email challenge — 64,000 customers randomly assigned to one of
three arms (Mens email, Womens email, no email) with observed visits and
conversions. Random assignment is what makes the counterfactual estimable, and
three arms make it a genuine next-best-*action* problem rather than a
send/don't-send one.

What is measured
----------------
*   **Two uplift learners.** An S-learner (one model, treatment as a feature)
    and a T-learner (one model per arm), scoring each customer by the estimated
    *increase* in response the email causes for them.
*   **The system's current policy, scored on the same data** — rank by predicted
    response, ignoring the treatment effect. This is the comparison that
    matters, because it is what the recommender does today.
*   **Qini curves**, the standard way to evaluate a targeting rule when only one
    arm is observed per customer. At every budget the curve reports incremental
    responders relative to targeting at random.
*   **Realised incremental response at a fixed budget**, which is the number a
    marketer can act on: "if you can only email 30% of your list, how many extra
    visits does each policy buy per thousand people targeted?"

What this does and does not license
-----------------------------------
Hillstrom's actions are *mens email* and *womens email*, not this project's
premium/personalised/reactivation/reminder. The experiment therefore
demonstrates the *method* on real randomised data and establishes that ranking
by response and ranking by uplift disagree. It does not produce a policy that
can be deployed to the imported audience, and the report must not imply that it
does.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research import config
from research.stats import bootstrap_ci

ID = "E8"
TITLE = "Module 3 — targeting by uplift versus targeting by predicted response"

DATASET = config.ROOT / "data" / "raw" / "datasets" / "hillstrom_email.csv"
DOWNLOAD = ("curl -sS -o data/raw/datasets/hillstrom_email.csv "
            "http://www.minethatdata.com/"
            "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv")

CONTROL_ARM = "No E-Mail"

#: `visit` rather than `conversion` as the primary outcome. Conversion is 0.9%
#: overall, so a held-out split contains only a few hundred converters and every
#: curve becomes noise. Visits are the standard choice on this dataset for that
#: reason; conversion is reported alongside as the secondary outcome.
OUTCOME = "visit"

NUMERIC = ["recency", "history", "mens", "womens", "newbie"]
CATEGORICAL = ["history_segment", "zip_code", "channel"]

#: The budget the policy comparison is evaluated at — a marketer emails some
#: share of the list, not all of it. Matches the tiering the recommender uses.
BUDGET = 0.30


def _model():
    from xgboost import XGBClassifier

    # n_jobs=1: XGBoost's OpenMP pool clashes with torch's on macOS.
    return XGBClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        random_state=config.SEED, n_jobs=1, eval_metric="logloss")


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """One-hot the categoricals once, so every learner sees identical inputs."""
    return pd.get_dummies(frame[NUMERIC + CATEGORICAL],
                          columns=CATEGORICAL, drop_first=False).astype(float)


# ── Qini ─────────────────────────────────────────────────────────────────────
def qini_curve(scores: np.ndarray, treated: np.ndarray,
               outcome: np.ndarray, points: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Incremental responders gained by targeting the top-scoring share.

    At a prefix of k customers, the treated responders in that prefix are
    compared with the control responders *scaled to the same number of people*:

        qini(k) = responders_treated(k) − responders_control(k) · n_t(k)/n_c(k)

    The scaling is what makes it a causal quantity: because assignment was
    random, the control group inside any score-defined prefix is a valid
    stand-in for what the treated group would have done untreated.
    """
    order = np.argsort(-scores, kind="stable")
    t = treated[order].astype(float)
    y = outcome[order].astype(float)

    n_t = np.cumsum(t)
    n_c = np.cumsum(1.0 - t)
    r_t = np.cumsum(y * t)
    r_c = np.cumsum(y * (1.0 - t))

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(n_c > 0, n_t / np.maximum(n_c, 1e-9), 0.0)
    gain = r_t - r_c * ratio

    n = len(scores)
    idx = np.unique(np.linspace(0, n - 1, points).astype(int))
    return (idx + 1) / n, gain[idx]


def qini_coefficient(x: np.ndarray, gain: np.ndarray) -> float:
    """Area between the Qini curve and random targeting, per customer.

    Positive means the ranking finds persuadable customers earlier than chance.
    Zero means the ranking is no better than shuffling the list.
    """
    if len(x) < 2:
        return float("nan")
    area = float(np.trapezoid(gain, x))
    random_area = float(gain[-1]) / 2.0     # straight line to the same endpoint
    return area - random_area


def incremental_at_budget(scores: np.ndarray, treated: np.ndarray,
                          outcome: np.ndarray, budget: float = BUDGET) -> dict:
    """Extra responders per 1,000 targeted, if only `budget` of the list is emailed.

    Unbiased because assignment was randomised: within the targeted subgroup the
    treated and control halves remain comparable, so their difference in
    response rate is the causal effect of the email on the people this policy
    chose.
    """
    k = max(1, int(round(len(scores) * budget)))
    order = np.argsort(-scores, kind="stable")[:k]
    t, y = treated[order].astype(bool), outcome[order].astype(float)

    n_t, n_c = int(t.sum()), int((~t).sum())
    if n_t == 0 or n_c == 0:
        return {"uplift_per_1000": float("nan"), "n_targeted": k}

    lift = y[t].mean() - y[~t].mean()
    return {
        "n_targeted": k,
        "treated_response": round(float(y[t].mean()), 4),
        "control_response": round(float(y[~t].mean()), 4),
        "uplift_per_1000": round(float(lift) * 1000, 2),
    }


def run() -> dict:
    if not DATASET.exists():
        return {"id": ID, "title": TITLE, "status": "skipped",
                "reason": (f"Hillstrom dataset not found at "
                           f"{DATASET.relative_to(config.ROOT)} — download it with:\n"
                           f"    {DOWNLOAD}")}

    from sklearn.model_selection import train_test_split

    frame = pd.read_csv(DATASET)
    frame["treated"] = (frame["segment"] != CONTROL_ARM).astype(int)

    x = _prepare(frame)
    treated = frame["treated"].to_numpy()
    y = frame[OUTCOME].to_numpy()

    idx_train, idx_test = train_test_split(
        np.arange(len(frame)), test_size=0.3, random_state=config.SEED,
        stratify=frame["segment"])

    x_train, x_test = x.iloc[idx_train], x.iloc[idx_test]
    t_train, t_test = treated[idx_train], treated[idx_test]
    y_train, y_test = y[idx_train], y[idx_test]

    scores: dict[str, np.ndarray] = {}

    # ── S-learner: one model, treatment as an input feature ─────────────────
    s_train = x_train.copy(); s_train["treated"] = t_train
    s_model = _model().fit(s_train, y_train)

    as_treated = x_test.copy(); as_treated["treated"] = 1
    as_control = x_test.copy(); as_control["treated"] = 0
    scores["uplift (S-learner)"] = (
        s_model.predict_proba(as_treated)[:, 1]
        - s_model.predict_proba(as_control)[:, 1])

    # ── T-learner: one model per arm ────────────────────────────────────────
    treated_model = _model().fit(x_train[t_train == 1], y_train[t_train == 1])
    control_model = _model().fit(x_train[t_train == 0], y_train[t_train == 0])
    scores["uplift (T-learner)"] = (
        treated_model.predict_proba(x_test)[:, 1]
        - control_model.predict_proba(x_test)[:, 1])

    # ── The policy the system uses today: rank by predicted response ────────
    # Fitted on the treated arm only, which is what "who is most likely to
    # respond to our campaign" means in practice.
    response_model = _model().fit(x_train[t_train == 1], y_train[t_train == 1])
    scores["predicted response (current policy)"] = (
        response_model.predict_proba(x_test)[:, 1])

    # ── Random targeting, as the floor ──────────────────────────────────────
    rng = np.random.default_rng(config.SEED)
    scores["random targeting"] = rng.random(len(idx_test))

    # ── Score every policy ──────────────────────────────────────────────────
    curves, summary = [], []
    for name, score in scores.items():
        x_axis, gain = qini_curve(score, t_test, y_test)
        coefficient = qini_coefficient(x_axis, gain)

        # A CI on the Qini coefficient by resampling the held-out customers.
        # 400 resamples: each one re-sorts 19,200 rows, so the full 10,000
        # would dominate the whole research run.
        order_idx = np.arange(len(score))

        def stat(sample, sc=score):
            xs, gs = qini_curve(sc[sample], t_test[sample], y_test[sample])
            return qini_coefficient(xs, gs)

        interval = bootstrap_ci(order_idx, stat, n_resamples=400)

        at_budget = incremental_at_budget(score, t_test, y_test)
        summary.append({
            "policy": name,
            "qini_coefficient": round(coefficient, 2),
            "ci_low": round(interval.low, 2),
            "ci_high": round(interval.high, 2),
            **at_budget,
        })
        curves.extend({"policy": name, "share_targeted": round(float(a), 4),
                       "incremental_responders": round(float(g), 2)}
                      for a, g in zip(x_axis, gain))

    summary.sort(key=lambda r: -r["qini_coefficient"])

    # ── Three arms: which action, not whether to act ────────────────────────
    # The next-best-action question proper. One model per arm, then the arm with
    # the highest predicted response for each customer.
    arm_models = {}
    for arm in frame["segment"].unique():
        mask = frame["segment"].iloc[idx_train] == arm
        arm_models[arm] = _model().fit(x_train[mask.to_numpy()],
                                       y_train[mask.to_numpy()])

    arm_scores = pd.DataFrame(
        {arm: model.predict_proba(x_test)[:, 1] for arm, model in arm_models.items()})
    best_arm = arm_scores.idxmax(axis=1)

    action_rows = []
    for arm, count in best_arm.value_counts().items():
        # Among customers this policy would assign to `arm`, what actually
        # happened to the ones who really received it, against the control?
        chosen = (best_arm == arm).to_numpy()
        got_arm = (frame["segment"].iloc[idx_test].to_numpy() == arm) & chosen
        got_control = (frame["segment"].iloc[idx_test].to_numpy() == CONTROL_ARM) & chosen
        lift = (y_test[got_arm].mean() - y_test[got_control].mean()
                if got_arm.sum() and got_control.sum() else float("nan"))
        action_rows.append({
            "assigned_action": arm,
            "customers": int(count),
            "share": round(float(count) / len(best_arm), 4),
            "observed_uplift_per_1000": round(float(lift) * 1000, 2)
            if lift == lift else None,
        })

    # ── How much do the two rankings actually disagree? ──────────────────────
    from scipy.stats import spearmanr

    uplift_rank = scores["uplift (T-learner)"]
    response_rank = scores["predicted response (current policy)"]
    agreement = float(spearmanr(uplift_rank, response_rank).statistic)

    k = int(len(uplift_rank) * BUDGET)
    top_uplift = set(np.argsort(-uplift_rank)[:k])
    top_response = set(np.argsort(-response_rank)[:k])
    overlap = len(top_uplift & top_response) / k

    best = summary[0]
    current = next(r for r in summary
                   if r["policy"] == "predicted response (current policy)")

    notes = [
        "Assignment was randomised, which is the only reason any of these "
        "numbers are causal. The same computation on observational data would "
        "measure who was targeted, not what targeting achieved.",
        f"The two rankings agree only moderately (Spearman {agreement:.2f}). At a "
        f"{BUDGET:.0%} budget they share {overlap:.0%} of their chosen "
        f"customers — so roughly {1 - overlap:.0%} of the list would be emailed "
        f"by one policy and not the other.",
        "Hillstrom's actions are mens and womens email, not this project's four. "
        "The experiment establishes that ranking by response and ranking by "
        "uplift are different policies with different returns; it does not "
        "produce a policy deployable to the imported audience.",
    ]

    if best["policy"].startswith("uplift"):
        notes.insert(0,
            f"{best['policy']} targets best: {best['uplift_per_1000']} extra "
            f"{OUTCOME}s per 1,000 customers emailed at a {BUDGET:.0%} budget, "
            f"against {current['uplift_per_1000']} for ranking by predicted "
            f"response — the policy this system currently uses.")
    else:
        notes.insert(0,
            f"On this dataset the uplift learners did NOT beat "
            f"{best['policy']}. Reported as measured.")

    # The ordering of the policies is the weakest claim here, and saying so is
    # the difference between a result and an overclaim.
    if best["ci_low"] < current["ci_high"]:
        notes.insert(1,
            f"Their Qini intervals overlap ([{best['ci_low']}, {best['ci_high']}] "
            f"against [{current['ci_low']}, {current['ci_high']}]), so the "
            "ordering of the two policies is NOT established on this split. What "
            "the data does support is that they are different policies, not that "
            "one is reliably better.")

    learners = [r for r in summary if r["policy"].startswith("uplift")]
    if len(learners) == 2 and learners[1]["qini_coefficient"] < current["qini_coefficient"]:
        notes.insert(2,
            f"The two uplift learners disagree with each other — "
            f"{learners[0]['policy']} scores {learners[0]['qini_coefficient']} and "
            f"{learners[1]['policy']} {learners[1]['qini_coefficient']}, the latter "
            "below the current policy. 'Use uplift modelling' is therefore not a "
            "conclusion on its own: on this data the choice of learner matters as "
            "much as the choice of paradigm.")

    return {
        "id": ID,
        "title": TITLE,
        "status": "ok",
        "metrics": {
            "dataset": "Hillstrom MineThatData (64,000 customers, 3 randomised arms)",
            "outcome": OUTCOME,
            "n_train": int(len(idx_train)),
            "n_test": int(len(idx_test)),
            "budget": BUDGET,
            "best_policy": best["policy"],
            "best_uplift_per_1000": best["uplift_per_1000"],
            "current_policy_uplift_per_1000": current["uplift_per_1000"],
            "rank_agreement_spearman": round(agreement, 4),
            "top_share_overlap": round(overlap, 4),
        },
        "tables": {
            "e8_policy_summary": summary,
            "e8_qini_curves": curves,
            "e8_action_assignment": action_rows,
        },
        "notes": notes,
    }
