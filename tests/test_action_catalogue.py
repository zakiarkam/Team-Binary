"""Per-website, per-customer action sets.

The recommender used to offer the same four actions to every client. It now
offers what the website can perform, narrowed to what the customer qualifies
for — which makes two things load-bearing:

*   **a site must never be offered an action it cannot perform**, because a
    discount recommended to a site with no checkout is not a recommendation;
*   **the propensity must be computed over the set that was actually
    available**, because a fixed denominator when the real set varies is a
    silent bias in every off-policy estimate downstream.
"""

from __future__ import annotations

import random

import pytest

from api.services import actions_catalogue as catalogue
from api.services import decisions as svc

SHOP = {"commerce": True, "lead_capture": True, "content": True}
SAAS = {"subscription": True, "lead_capture": True, "content": True}
CHARITY = {"donation": True, "content": True}
BLOG = {"content": True}


# ── What a site can do ───────────────────────────────────────────────────────

def test_a_site_is_never_offered_what_it_cannot_do() -> None:
    """The failure this whole design exists to prevent."""
    blog_actions = set(catalogue.site_actions(BLOG))
    assert "send_premium_offer" not in blog_actions
    assert "send_discount_offer" not in blog_actions
    assert "send_donation_appeal" not in blog_actions
    assert "send_upgrade_prompt" not in blog_actions

    charity_actions = set(catalogue.site_actions(CHARITY))
    assert "send_donation_appeal" in charity_actions
    assert "send_abandoned_cart_reminder" not in charity_actions

    saas_actions = set(catalogue.site_actions(SAAS))
    assert "send_upgrade_prompt" in saas_actions
    assert "send_replenishment_reminder" not in saas_actions


def test_different_site_types_get_different_sets() -> None:
    sets = {name: set(catalogue.site_actions(caps))
            for name, caps in (("shop", SHOP), ("saas", SAAS),
                               ("charity", CHARITY), ("blog", BLOG))}
    # Every pair differs — otherwise capability detection changes nothing.
    names = list(sets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert sets[a] != sets[b], f"{a} and {b} got identical action sets"


def test_a_site_with_no_detected_capabilities_keeps_the_legacy_set() -> None:
    """An unmigrated site must behave exactly as it did before detection,
    rather than silently losing every action."""
    assert catalogue.site_actions(None) == list(catalogue.LEGACY_ACTIONS)
    assert catalogue.site_actions({}) == list(catalogue.LEGACY_ACTIONS)


# ── What a customer qualifies for ────────────────────────────────────────────

def test_eligibility_narrows_the_set_per_customer() -> None:
    newcomer = {"purchases": 0, "sessions": 1, "page_views": 1,
                "days_since_last_seen": 0, "add_to_carts": 0}
    regular = {"purchases": 4, "sessions": 9, "page_views": 30,
               "days_since_last_seen": 40, "add_to_carts": 5}

    for_newcomer = set(catalogue.available(SHOP, newcomer))
    for_regular = set(catalogue.available(SHOP, regular))

    assert for_newcomer != for_regular
    # A premium offer needs a purchase history; a replenishment reminder needs
    # a repeat buyer; a reactivation needs someone who has actually lapsed.
    assert "send_premium_offer" not in for_newcomer
    assert "send_premium_offer" in for_regular
    assert "send_replenishment_reminder" in for_regular
    assert "send_reactivation_campaign" not in for_newcomer
    assert "send_reactivation_campaign" in for_regular


def test_an_abandoned_basket_needs_an_actual_abandoned_basket() -> None:
    bought_everything = {"purchases": 3, "add_to_carts": 3}
    left_one = {"purchases": 1, "add_to_carts": 3}

    assert "send_abandoned_cart_reminder" not in catalogue.available(
        SHOP, bought_everything)
    assert "send_abandoned_cart_reminder" in catalogue.available(SHOP, left_one)


def test_the_candidate_set_is_never_empty() -> None:
    """An empty set means no action, no propensity, and a division by zero."""
    for capabilities in (SHOP, SAAS, CHARITY, BLOG, {}, None):
        for context in ({}, {"purchases": 0, "sessions": 0, "page_views": 0,
                             "days_since_last_seen": 0}):
            assert catalogue.available(capabilities, context)


def test_withheld_actions_explain_themselves() -> None:
    reasons = catalogue.withheld(BLOG, {"purchases": 0})
    by_action = {r["action"]: r for r in reasons}

    assert "send_premium_offer" in by_action
    assert by_action["send_premium_offer"]["scope"] == "site"
    assert "commerce" in by_action["send_premium_offer"]["reason"]


# ── Propensity over a varying set ────────────────────────────────────────────

def test_propensity_uses_the_available_set_not_a_global_constant() -> None:
    """The bias that a fixed denominator would introduce, pinned.

    A customer of a blog has far fewer candidates than a customer of a shop, so
    the same exploration budget spreads differently. Using len(ACTIONS) for both
    would silently misweight every off-policy estimate.
    """
    rng = random.Random(0)
    small = ["send_digest", "send_general_reminder"]
    large = catalogue.site_actions(SHOP)
    assert len(large) > len(small)

    _, _, p_small = svc.epsilon_greedy("send_digest", rng, 0.10, candidates=small)
    _, _, p_large = svc.epsilon_greedy(large[0], rng, 0.10, candidates=large)

    # Greedy propensity is ε/|A| + (1−ε); a smaller set concentrates the
    # exploration mass, so the greedy action is *more* likely there.
    assert p_small == pytest.approx(0.10 / len(small) + 0.90)
    assert p_large == pytest.approx(0.10 / len(large) + 0.90)
    assert p_small > p_large


def test_propensities_sum_to_one_over_any_candidate_set() -> None:
    for candidates in (["a", "b"], ["a", "b", "c", "d"], list("abcdefghijkl")):
        epsilon, k, greedy = 0.10, len(candidates), candidates[0]
        total = sum(epsilon / k + (1 - epsilon) * (a == greedy)
                    for a in candidates)
        assert total == pytest.approx(1.0), candidates


def test_an_action_outside_the_candidate_set_is_never_chosen() -> None:
    """The greedy policy may name an action this customer cannot receive —
    it must be replaced, not sent."""
    rng = random.Random(1)
    candidates = ["send_digest", "send_general_reminder"]
    for _ in range(200):
        action, _, propensity = svc.epsilon_greedy(
            "send_premium_offer", rng, 0.10, candidates=candidates)
        assert action in candidates
        assert propensity > 0


def test_goal_ordering_reorders_without_removing() -> None:
    """Module 4's goal classifier orders the candidates; it must never filter.

    Its macro-F1 is near 0.50, so dropping an action a site genuinely supports
    on the strength of that would be a coin-flip deciding a capability.
    """
    actions = catalogue.site_actions(SHOP)
    ranked = catalogue.rank_for_goal(actions, "conversion")

    assert sorted(ranked) == sorted(actions), "ordering must not drop anything"
    assert ranked != actions or len(actions) < 2
    # Conversion-serving actions come first.
    first = catalogue.BY_KEY[ranked[0]]
    assert "conversion" in first.goals
