"""The decision log — the mechanism that makes next-best-action learnable.

Three properties carry everything downstream, and each is easy to break in a
way nothing else would notice:

*   **Propensities must be a probability distribution.** Every off-policy
    estimate divides by them. Get them wrong and the numbers are still
    plausible-looking, just wrong.
*   **The log must be append-only.** `analytics_output` is overwritten on every
    run, which is exactly why it cannot serve as evidence. If this table ever
    acquires the same behaviour the mechanism is silently pointless.
*   **A reward must be caused by the decision.** Only events that came after it,
    and only events belonging to an action the system actually took.
"""

from __future__ import annotations

import random

import pytest

pytest.importorskip("fastapi")

from api import db  # noqa: E402
from api.services import decisions as svc  # noqa: E402

try:
    db.ping()
    DB_UP = True
except Exception:
    DB_UP = False


# ── Propensities: pure, no database needed ───────────────────────────────────

def test_propensities_sum_to_one_over_the_action_set() -> None:
    """Every estimator divides by these, so they must be a real distribution."""
    epsilon, k = 0.10, len(svc.ACTIONS)
    greedy = svc.ACTIONS[0]

    total = 0.0
    for action in svc.ACTIONS:
        p = epsilon / k + (1 - epsilon) * (1.0 if action == greedy else 0.0)
        total += p
    assert total == pytest.approx(1.0)


def test_every_action_keeps_a_positive_chance_of_being_taken() -> None:
    """A zero propensity is the formal statement of 'unlearnable'.

    An action never taken has no evidence about it and an infinite importance
    weight, so the estimator can say nothing about any policy that would choose
    it. Exploration exists to keep every denominator non-zero.
    """
    rng = random.Random(0)
    seen = {a: 0 for a in svc.ACTIONS}
    for _ in range(4_000):
        action, _, propensity = svc.epsilon_greedy(svc.ACTIONS[0], rng)
        seen[action] += 1
        assert propensity > 0

    assert all(count > 0 for count in seen.values()), (
        f"an action was never taken in 4,000 draws: {seen}")


def test_exploration_rate_is_honoured() -> None:
    rng = random.Random(1)
    explored = sum(svc.epsilon_greedy(svc.ACTIONS[0], rng, epsilon=0.10)[1] == "explore"
                   for _ in range(10_000))
    assert 0.085 <= explored / 10_000 <= 0.115


def test_no_exploration_means_a_deterministic_log() -> None:
    """With epsilon 0 the greedy action has propensity 1 and no other is taken.

    This is the state E9 shows to be dangerous: the log looks clean and supports
    no conclusion about any policy but the one that produced it.
    """
    rng = random.Random(2)
    for _ in range(200):
        action, policy, propensity = svc.epsilon_greedy(
            svc.ACTIONS[1], rng, epsilon=0.0)
        assert action == svc.ACTIONS[1]
        assert policy == "exploit"
        assert propensity == pytest.approx(1.0)


# ── Off-policy estimation, against a known answer ────────────────────────────

def test_ips_recovers_a_known_policy_value() -> None:
    """The estimator's whole job: score a policy that was never run.

    A world is built where the reward of each action is known exactly, logs are
    generated under a *different* policy, and the estimate must land on the
    target policy's true value.
    """
    rng = random.Random(3)
    true_reward = {svc.ACTIONS[0]: 0.8, svc.ACTIONS[1]: 0.2,
                   svc.ACTIONS[2]: 0.2, svc.ACTIONS[3]: 0.2}
    epsilon, k = 0.5, len(svc.ACTIONS)          # heavy exploration → low variance

    rows, target = [], {}
    for visitor in range(20_000):
        greedy = svc.ACTIONS[3]                 # the logging policy is poor
        action, policy, propensity = svc.epsilon_greedy(greedy, rng, epsilon)
        rows.append({
            "visitor_id": visitor, "action": action, "policy": policy,
            "propensity": propensity,
            "reward": 1.0 if rng.random() < true_reward[action] else 0.0,
            "context": {}, "source": "live",
        })
        target[visitor] = svc.ACTIONS[0]        # the candidate: always the best

    result = svc.evaluate_policy(site_id=0, target=target, rows=rows)

    assert result["snips"] == pytest.approx(0.8, abs=0.03), result
    assert result["ips"] == pytest.approx(0.8, abs=0.03), result
    assert result["doubly_robust"] == pytest.approx(0.8, abs=0.03), result
    # And it must beat what the logging policy actually achieved.
    assert result["observed_reward"] < result["snips"]


def test_evaluation_reports_nothing_rather_than_guessing() -> None:
    result = svc.evaluate_policy(site_id=0, rows=[])
    assert result["n"] == 0
    assert "cannot invent" in result["note"]


def test_evaluation_warns_when_the_log_has_no_exploration() -> None:
    rows = [{"visitor_id": i, "action": svc.ACTIONS[0], "policy": "exploit",
             "propensity": 1.0, "reward": 1.0, "context": {}, "source": "live"}
            for i in range(50)]
    result = svc.evaluate_policy(site_id=0, rows=rows)
    assert any("No exploration" in n for n in result["notes"])


# ── Database behaviour ───────────────────────────────────────────────────────

pytestmark = pytest.mark.skipif(not DB_UP, reason="PostgreSQL is not running")


@pytest.fixture
def site():
    db.init_schema()
    row = db.fetch_one(
        """INSERT INTO sites (site_key, ingest_secret, name, url)
           VALUES ('mos_decisions', 's', 'Decisions Test', 'http://x')
           RETURNING id""")
    yield int(row["id"])
    db.execute("DELETE FROM sites WHERE id = :i", i=int(row["id"]))


def _visitor(site_id: int, uid: str, source: str = "live") -> int:
    return int(db.fetch_one(
        """INSERT INTO visitors (site_id, visitor_uid, source)
           VALUES (:s, :u, :src) RETURNING id""",
        s=site_id, u=uid, src=source)["id"])


def test_the_log_is_append_only(site) -> None:
    """The reason this table exists rather than reusing analytics_output.

    analytics_output is UNIQUE (visitor_id) and overwritten every run, so it can
    only ever hold the current opinion. A decision history that overwrites
    itself is not a history.
    """
    visitor = _visitor(site, "append-1")
    decision = [{"visitor_id": visitor, "greedy": svc.ACTIONS[0], "context": {}}]

    svc.log_decisions(site, decision, seed=1)
    svc.log_decisions(site, decision, seed=2)
    svc.log_decisions(site, decision, seed=3)

    n = db.fetch_one("SELECT count(*) AS n FROM action_log WHERE site_id = :s",
                     s=site)["n"]
    assert n == 3, "each decision must be kept, not replaced"


def test_logged_decisions_inherit_the_visitor_provenance(site) -> None:
    live = _visitor(site, "prov-live", source="live")
    dataset = _visitor(site, "prov-dataset", source="dataset")

    svc.log_decisions(site, [
        {"visitor_id": live, "greedy": svc.ACTIONS[0], "context": {}},
        {"visitor_id": dataset, "greedy": svc.ACTIONS[0], "context": {}},
    ], seed=0)

    rows = {r["visitor_id"]: r["source"] for r in db.fetch_all(
        "SELECT visitor_id, source FROM action_log WHERE site_id = :s", s=site)}
    assert rows[live] == "live"
    assert rows[dataset] == "dataset"


def test_reward_only_counts_events_caused_by_an_action_we_took(site) -> None:
    """Regression: reconstructed history was being credited as a reward.

    The importer spreads each customer's prior email history over a 90-day
    window from their first visit, so some of it carries a timestamp later than
    now. Those rows passed an 'occurred after the decision' test while being a
    reconstruction of someone else's campaign. Only events belonging to a
    campaign this system planned may count.
    """
    visitor = _visitor(site, "reward-1")
    svc.log_decisions(site, [{"visitor_id": visitor, "greedy": svc.ACTIONS[0],
                              "context": {}}], seed=0)

    # Reconstructed history, dated in the future, belonging to no campaign.
    db.execute(
        """INSERT INTO interactions (site_id, visitor_id, campaign_id, channel,
                                     platform, event_type, source, occurred_at)
           VALUES (:s, :v, NULL, 'email', 'email', 'convert', 'dataset',
                   now() + interval '2 days')""",
        s=site, v=visitor)

    assert svc.attach_rewards(site)["rewarded"] == 0
    assert db.fetch_one(
        "SELECT count(*) AS n FROM action_log WHERE site_id=:s AND reward IS NOT NULL",
        s=site)["n"] == 0

    # Now an event that IS downstream of a campaign the system planned.
    campaign = db.fetch_one(
        """INSERT INTO campaigns (site_id, name, strategy, status)
           VALUES (:s, 'T', 'hybrid', 'running') RETURNING id""", s=site)["id"]
    db.execute(
        """INSERT INTO interactions (site_id, visitor_id, campaign_id, channel,
                                     platform, event_type, source, occurred_at)
           VALUES (:s, :v, :c, 'email', 'email', 'convert', 'live',
                   now() + interval '1 hour')""",
        s=site, v=visitor, c=campaign)

    assert svc.attach_rewards(site)["rewarded"] == 1
    row = db.fetch_one(
        """SELECT reward::float8 AS reward, reward_kind FROM action_log
           WHERE site_id = :s""", s=site)
    assert row["reward"] == pytest.approx(svc.REWARD_VALUES["convert"])
    assert row["reward_kind"] == "convert"


def test_a_reward_cannot_precede_the_decision_that_earned_it(site) -> None:
    """A conversion that already happened cannot have been caused by an action
    taken afterwards, and counting it would manufacture evidence."""
    visitor = _visitor(site, "reward-2")
    campaign = db.fetch_one(
        """INSERT INTO campaigns (site_id, name, strategy, status)
           VALUES (:s, 'T', 'hybrid', 'running') RETURNING id""", s=site)["id"]

    db.execute(
        """INSERT INTO interactions (site_id, visitor_id, campaign_id, channel,
                                     platform, event_type, source, occurred_at)
           VALUES (:s, :v, :c, 'email', 'email', 'convert', 'live',
                   now() - interval '1 day')""",
        s=site, v=visitor, c=campaign)

    svc.log_decisions(site, [{"visitor_id": visitor, "greedy": svc.ACTIONS[0],
                              "context": {}}], seed=0)

    assert svc.attach_rewards(site)["rewarded"] == 0
