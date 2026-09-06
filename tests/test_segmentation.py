"""Phase 2 tests — Module 1, the hybrid segmentation engine.

These lock in the three corrections made when the notebook was turned into
runnable code, so they cannot silently regress:

  · cluster names are derived from centroids, not from cluster index
  · the cold-start segment survives the agreement vote
  · the classifier never sees a segment label among its inputs

Most tests need no database. The service-level ones are skipped without one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from modules.m1_segmentation.segment import (
    HIGH_INTENT,
    LOW_ENGAGEMENT,
    LOYAL_CUSTOMER,
    NEW_COLD_USER,
    PRICE_SENSITIVE,
    SEGMENT_IDS,
    SEGMENTS,
    HybridSegmenter,
    WEB_FEATURES,
    research_rules,
    research_segmenter,
    web_rules,
    web_segmenter,
)

WEB_COLUMNS = WEB_FEATURES.columns


def make_web_audience(n: int = 200, seed: int = 7) -> pd.DataFrame:
    """A synthetic but deliberately messy audience — archetypes that overlap."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        kind = i % 5
        if kind == 0:      # bouncer
            r = dict(page_views=1, clicks=0, sessions=1, unique_pages=1,
                     max_scroll_depth=rng.integers(5, 40), time_on_site_seconds=rng.integers(1, 12),
                     form_submits=0, purchases=0)
        elif kind == 1:    # browser
            r = dict(page_views=rng.integers(2, 5), clicks=rng.integers(0, 2),
                     sessions=1, unique_pages=2, max_scroll_depth=rng.integers(40, 80),
                     time_on_site_seconds=rng.integers(20, 90), form_submits=0, purchases=0)
        elif kind == 2:    # researcher
            r = dict(page_views=rng.integers(3, 8), clicks=rng.integers(0, 2),
                     sessions=rng.integers(2, 5), unique_pages=3,
                     max_scroll_depth=rng.integers(50, 95),
                     time_on_site_seconds=rng.integers(60, 240), form_submits=0, purchases=0)
        elif kind == 3:    # engaged
            r = dict(page_views=rng.integers(3, 9), clicks=rng.integers(2, 7),
                     sessions=rng.integers(1, 4), unique_pages=3,
                     max_scroll_depth=rng.integers(75, 101),
                     time_on_site_seconds=rng.integers(90, 400), form_submits=1, purchases=0)
        else:              # customer
            r = dict(page_views=rng.integers(4, 11), clicks=rng.integers(3, 10),
                     sessions=rng.integers(2, 6), unique_pages=4,
                     max_scroll_depth=100, time_on_site_seconds=rng.integers(150, 600),
                     form_submits=1, purchases=1)
        r["visitor_id"] = i + 1
        rows.append(r)
    return pd.DataFrame(rows).astype({c: float for c in WEB_COLUMNS})


# ── Rules ────────────────────────────────────────────────────────────────────

def test_a_converter_is_never_low_engagement() -> None:
    """Conversion is the strongest signal available; a buyer labelled
    'Low Engagement' would be an obvious contradiction to an examiner."""
    df = make_web_audience(200)
    labels = web_rules(df)
    converters = labels[df["purchases"] > 0]
    assert set(converters).issubset({HIGH_INTENT, LOYAL_CUSTOMER})


def test_repeat_buyer_is_loyal_first_time_buyer_is_high_intent() -> None:
    df = pd.DataFrame([
        dict(page_views=5, clicks=3, sessions=3, unique_pages=3, max_scroll_depth=90,
             time_on_site_seconds=200, form_submits=1, purchases=1),   # repeat
        dict(page_views=5, clicks=3, sessions=1, unique_pages=3, max_scroll_depth=90,
             time_on_site_seconds=200, form_submits=1, purchases=1),   # first time
    ]).astype(float)
    labels = web_rules(df).tolist()
    assert labels == [LOYAL_CUSTOMER, HIGH_INTENT]


def test_single_page_visitor_is_new_cold_user() -> None:
    df = pd.DataFrame([dict(page_views=1, clicks=0, sessions=1, unique_pages=1,
                            max_scroll_depth=20, time_on_site_seconds=4,
                            form_submits=0, purchases=0)]).astype(float)
    assert web_rules(df).iloc[0] == NEW_COLD_USER


def test_rules_only_ever_emit_known_segments() -> None:
    df = make_web_audience(200)
    assert set(web_rules(df)).issubset(set(SEGMENTS))


# ── The agreement vote ───────────────────────────────────────────────────────

def test_cold_start_beats_clustering_agreement() -> None:
    """The regression this locks in.

    Clustering cannot represent 'not enough evidence yet', so when the rules
    detect a cold-start user, two agreeing clusterings must not overrule them.
    In the notebook they did, which silently emptied the segment.
    """
    label, confidence = HybridSegmenter._vote(
        NEW_COLD_USER, LOW_ENGAGEMENT, LOW_ENGAGEMENT)
    assert label == NEW_COLD_USER
    assert confidence == pytest.approx(0.65)


def test_unanimous_agreement_scores_highest() -> None:
    label, confidence = HybridSegmenter._vote(HIGH_INTENT, HIGH_INTENT, HIGH_INTENT)
    assert (label, confidence) == (HIGH_INTENT, 0.95)


def test_total_disagreement_falls_back_to_the_interpretable_rule() -> None:
    label, confidence = HybridSegmenter._vote(
        HIGH_INTENT, LOW_ENGAGEMENT, PRICE_SENSITIVE)
    assert label == HIGH_INTENT
    assert confidence == pytest.approx(0.60)


def test_no_cold_start_user_is_lost_by_the_engine() -> None:
    df = make_web_audience(200)
    expected = int((web_rules(df) == NEW_COLD_USER).sum())
    assert expected > 0, "test data must contain cold-start users to be meaningful"

    result = web_segmenter().fit_predict(df)
    assert int((result.frame["segment_name"] == NEW_COLD_USER).sum()) == expected


# ── Cluster naming ───────────────────────────────────────────────────────────

def test_cluster_names_are_stable_under_row_shuffling() -> None:
    """Names come from centroids, so reordering the input must not rename
    anyone. The notebook's hardcoded cluster-index mapping fails this."""
    df = make_web_audience(200)
    a = web_segmenter().fit_predict(df)

    shuffled = df.sample(frac=1.0, random_state=99).reset_index(drop=True)
    b = web_segmenter().fit_predict(shuffled)

    left = a.frame.set_index("visitor_id")["segment_name"].sort_index()
    right = b.frame.set_index("visitor_id")["segment_name"].sort_index()
    agreement = (left == right).mean()
    assert agreement > 0.95, f"labels moved for {(1 - agreement):.1%} of visitors"


def test_named_clusters_are_behaviourally_ordered() -> None:
    """The cluster called High Intent must actually be more engaged than the
    one called Low Engagement — otherwise the names are decoration."""
    df = make_web_audience(300)
    result = web_segmenter().fit_predict(df)
    by_segment = result.frame.groupby("segment_name")["clicks"].mean()

    if HIGH_INTENT in by_segment and LOW_ENGAGEMENT in by_segment:
        assert by_segment[HIGH_INTENT] > by_segment[LOW_ENGAGEMENT]


# ── Cold start ───────────────────────────────────────────────────────────────

def test_tiny_audience_skips_clustering_and_says_so() -> None:
    """A newly launched product lives here. Clustering 5 visitors would invent
    structure that is not in the data, so the engine must decline to."""
    df = make_web_audience(200).head(5)
    result = web_segmenter().fit_predict(df)

    assert result.diagnostics["mode"] == "cold_start_rules"
    assert "fewer than" in result.diagnostics["reason"]
    assert result.frame["is_cold_start"].all()
    assert (result.frame["segment_confidence"] == 0.50).all()


def test_empty_audience_is_handled() -> None:
    empty = pd.DataFrame(columns=[*WEB_COLUMNS, "visitor_id"])
    result = web_segmenter().fit_predict(empty)
    assert result.diagnostics["n_users"] == 0


def test_missing_feature_columns_fail_loudly() -> None:
    df = make_web_audience(200).drop(columns=["clicks"])
    with pytest.raises(KeyError, match="clicks"):
        web_segmenter().fit_predict(df)


# ── The classifier ───────────────────────────────────────────────────────────

def test_classifier_inputs_contain_no_segment_labels() -> None:
    """The notebook trained the RF with `rule_encoded` as both a feature and the
    target, so it scored ~100% by reading the answer. Guard against that here:
    the feature matrix must be exactly the behavioural columns."""
    engine = web_segmenter()
    engine.fit_predict(make_web_audience(200))

    assert engine.classifier is not None
    assert engine.classifier.n_features_in_ == len(WEB_COLUMNS)
    assert engine.features.columns == WEB_COLUMNS
    assert not any("segment" in c or "encoded" in c for c in engine.features.columns)


def test_classifier_can_label_a_brand_new_visitor() -> None:
    """The point of the classifier: segment an arriving visitor immediately,
    without re-clustering the whole audience."""
    engine = web_segmenter()
    engine.fit_predict(make_web_audience(200))

    newcomer = pd.DataFrame([dict(
        page_views=6, clicks=5, sessions=3, unique_pages=4, max_scroll_depth=100,
        time_on_site_seconds=300, form_submits=1, purchases=1)]).astype(float)

    out = engine.predict(newcomer)
    assert out["segment_name"].iloc[0] in SEGMENTS
    assert 0.0 <= out["segment_confidence"].iloc[0] <= 1.0


def test_predict_before_fit_is_an_error() -> None:
    with pytest.raises(RuntimeError, match="fit_predict"):
        web_segmenter().predict(make_web_audience(200))


def test_near_perfect_accuracy_carries_a_caveat() -> None:
    """If accuracy comes out ~1.0 the engine must say why that is unremarkable,
    rather than letting it be quoted as a headline result."""
    engine = web_segmenter()
    result = engine.fit_predict(make_web_audience(400))
    if result.diagnostics.get("classifier_accuracy", 0) > 0.99:
        assert "generalisation" in result.diagnostics["classifier_caveat"]


# ── Output contract with Module 2 ────────────────────────────────────────────

def test_user_segments_export_matches_the_module_2_schema() -> None:
    result = web_segmenter().fit_predict(make_web_audience(200))
    out = result.to_user_segments("visitor_id")

    assert list(out.columns) == [
        "user_id", "CustomerID", "segment_id", "segment_name",
        "segment_method", "segment_confidence",
    ]
    assert out["segment_id"].notna().all()
    assert set(out["segment_name"]).issubset(set(SEGMENTS))
    assert set(out["segment_id"]) <= set(SEGMENT_IDS.values())


# ── Research reproduction ────────────────────────────────────────────────────

def test_research_rules_reproduce_the_studied_distribution() -> None:
    """Guards the research numbers: the rule stage on the 8,000-user campaign
    dataset must keep producing the five studied segments."""
    path = "modules/m1_segmentation/digital_marketing_campaign_dataset.csv"
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        pytest.skip("research dataset not available")

    labels = research_rules(df)
    assert set(labels).issubset(set(SEGMENTS))
    assert len(df) == 8000
    # Cold-start users are rare in this dataset but must not be zero — that is
    # the population the research is about.
    assert (labels == NEW_COLD_USER).sum() > 0


@pytest.mark.slow
def test_research_segmentation_separates_conversion() -> None:
    """The segments must be commercially meaningful, not just statistically
    distinct: conversion rate should differ sharply across them."""
    path = "modules/m1_segmentation/digital_marketing_campaign_dataset.csv"
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        pytest.skip("research dataset not available")

    result = research_segmenter().fit_predict(df)
    conv = result.frame.groupby("segment_name")["Conversion"].mean()

    assert conv[NEW_COLD_USER] < conv[HIGH_INTENT]
    assert (conv.max() - conv.min()) > 0.20, "segments barely differ commercially"
