from .fixed import fixed_strategy
from .trigger import trigger_strategy

OPERATIONAL_COMPLEXITY = 19


def hybrid_strategy(user_row, event_history, rng) -> dict:
    """Routes each user to one of three behaviors based on segment_name and ml_score.

    1. Fallback path (fixed_strategy behavior):
       segment_name == 'New Cold User' OR ml_score < 0.30
       Cold-start / low-signal fallback — no behavioral signal to trigger on,
       so schedule messages instead.

    2. Full trigger path (trigger_strategy behavior):
       segment_name in ('High Intent', 'Loyal Customer')
       These segments have strong expected engagement signals, so behavioral
       triggers are used and the sequence terminates on silence.

    3. Blended path (hybrid-specific behavior):
       Everything else — includes Low Engagement, Price Sensitive, plus
       mid-ml_score users. Sends every step (schedule-driven, don't terminate
       on silence), but sets triggered=True if the previous message was
       opened or clicked. First message is triggered=False. This is the
       "schedule with opportunistic uplift" mode — trigger where possible,
       fixed where not.

    Requires user_row to have both 'segment_name' and 'ml_score'. Raises
    KeyError loudly if ml_score is missing rather than silently defaulting.
    """
    if 'ml_score' not in user_row:
        raise KeyError(
            "hybrid_strategy requires user_row to include 'ml_score', but it was not found."
        )

    segment_name = user_row['segment_name']
    ml_score = user_row['ml_score']

    if segment_name == 'New Cold User' or ml_score < 0.30:
        return fixed_strategy(user_row, event_history, rng)

    if segment_name in ('High Intent', 'Loyal Customer'):
        return trigger_strategy(user_row, event_history, rng)

    if not event_history:
        return {'send': True, 'triggered': False}
    last = event_history[-1]
    triggered = bool(last['opened'] or last['clicked'])
    return {'send': True, 'triggered': triggered}


if __name__ == "__main__":
    users = [
        {'segment_name': 'New Cold User', 'ml_score': 0.9},
        {'segment_name': 'High Intent', 'ml_score': 0.5},
        {'segment_name': 'Low Engagement', 'ml_score': 0.5},
    ]
    opened_history = [{'opened': True, 'clicked': False}]
    silent_history = [{'opened': False, 'clicked': False}]

    for user_row in users:
        empty_result = hybrid_strategy(user_row, [], None)
        opened_result = hybrid_strategy(user_row, opened_history, None)
        print(f"segment={user_row['segment_name']} ml_score={user_row['ml_score']}")
        print(f"  empty_history  -> {empty_result}")
        print(f"  after_open     -> {opened_result}")

    new_cold, high_intent, low_engagement = users

    # New Cold User -> fixed behavior: always send, never triggered.
    assert hybrid_strategy(new_cold, [], None) == {'send': True, 'triggered': False}
    assert hybrid_strategy(new_cold, opened_history, None) == {'send': True, 'triggered': False}
    assert hybrid_strategy(new_cold, silent_history, None) == {'send': True, 'triggered': False}

    # High Intent -> trigger behavior: triggered after open, stops after silence.
    assert hybrid_strategy(high_intent, [], None) == {'send': True, 'triggered': False}
    assert hybrid_strategy(high_intent, opened_history, None) == {'send': True, 'triggered': True}
    assert hybrid_strategy(high_intent, silent_history, None)['send'] is False

    # Low Engagement -> blended behavior: always sends, triggered after open.
    assert hybrid_strategy(low_engagement, [], None) == {'send': True, 'triggered': False}
    assert hybrid_strategy(low_engagement, opened_history, None) == {'send': True, 'triggered': True}
    assert hybrid_strategy(low_engagement, silent_history, None) == {'send': True, 'triggered': False}

    print("All smoke tests passed.")
