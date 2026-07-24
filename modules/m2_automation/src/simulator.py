import numpy as np
import pandas as pd

INTENT_UPLIFT = 2.5           # multiplier on click_prob and convert_prob when
                              # a message is sent in response to a recent
                              # behavioral signal (open or click on the prior message)

BASE_OPEN_PROB = 0.25
BASE_CLICK_GIVEN_OPEN = 0.20
BASE_CONVERT_GIVEN_CLICK = 0.15

# Segment-level propensity anchors, in [0, 1]. These modulate the baseline
# probabilities so different segments show meaningfully different response rates.
# Values chosen from the segment-vs-Conversion table in users_merged.csv:
# New Cold User converts at ~53% vs ~87-92% for others; the anchor reflects that.
SEGMENT_PROPENSITY = {
    'High Intent':     1.15,
    'Loyal Customer':  1.10,
    'Price Sensitive': 0.95,
    'Low Engagement':  0.90,
    'New Cold User':   0.55,
}


def compute_user_propensities(user_row) -> dict:
    segment_anchor = SEGMENT_PROPENSITY[user_row['segment_name']]
    # engagement_score is [0,1] with mean ~0.5. Center it around 0 and scale gently.
    eng_modifier = 1.0 + 0.4 * (user_row['engagement_score'] - 0.5)
    # eng_modifier ranges roughly [0.82, 1.18] across the population
    combined = segment_anchor * eng_modifier
    open_prob = min(0.95, BASE_OPEN_PROB * combined)
    click_prob = min(0.90, BASE_CLICK_GIVEN_OPEN * combined)
    convert_prob = min(0.90, BASE_CONVERT_GIVEN_CLICK * combined)
    return {'open_prob': open_prob, 'click_prob': click_prob, 'convert_prob': convert_prob}


def simulate_message(user_row, message_index, triggered: bool, rng, signal_sparsity: float = 0.0) -> dict:
    """
    INTENT_UPLIFT is the end-to-end lift on conversion probability for triggered
    sends, calibrated against the empirical fact that behaviorally-triggered
    marketing messages convert at roughly 2-3x the rate of scheduled messages
    per send. It is applied to convert_prob only, not to earlier funnel stages,
    to avoid compounding along the sequential opened->clicked->converted chain.
    """
    propensities = compute_user_propensities(user_row)
    open_prob = propensities['open_prob']
    click_prob = propensities['click_prob']
    convert_prob = propensities['convert_prob']

    if triggered:
        convert_prob = min(0.95, convert_prob * INTENT_UPLIFT)

    opened = rng.random() < open_prob
    clicked = opened and (rng.random() < click_prob)
    converted = clicked and (rng.random() < convert_prob)

    if signal_sparsity > 0 and rng.random() < signal_sparsity:
        opened = False
        clicked = False

    return {
        'user_id': user_row['CustomerID'],
        'message_index': message_index,
        'sent': True,
        'opened': opened,
        'clicked': clicked,
        'converted': converted,
        'triggered': triggered,
        'timestamp_day': message_index,
        'segment_name': user_row['segment_name'],
    }


def simulate_campaign(users_df, strategy_fn, max_messages_per_user: int, seed: int, signal_sparsity: float = 0.0) -> pd.DataFrame:
    all_events = []

    for user_index, (_, user_row) in enumerate(users_df.iterrows()):
        rng = np.random.default_rng(seed + user_index)
        event_history = []

        for step in range(max_messages_per_user):
            decision = strategy_fn(user_row, event_history, rng)
            if decision['send'] is False:
                break
            event = simulate_message(user_row, step, decision['triggered'], rng, signal_sparsity)
            event_history.append(event)

        all_events.extend(event_history)

    return pd.DataFrame(all_events)


if __name__ == "__main__":
    users_df = pd.read_csv("data/processed/users_merged.csv")

    print("=== Self-test: triggered vs untriggered convert rates by segment ===")
    rows = []
    for segment in SEGMENT_PROPENSITY:
        user_row = users_df[users_df['segment_name'] == segment].iloc[0]

        rng = np.random.default_rng(0)
        untriggered_converts = [
            simulate_message(user_row, 0, False, rng)['converted'] for _ in range(20000)
        ]
        untriggered_rate = np.mean(untriggered_converts)

        rng = np.random.default_rng(1)
        triggered_converts = [
            simulate_message(user_row, 0, True, rng)['converted'] for _ in range(20000)
        ]
        triggered_rate = np.mean(triggered_converts)

        ratio = triggered_rate / untriggered_rate if untriggered_rate > 0 else float('nan')
        rows.append({
            'segment': segment,
            'untriggered_convert_rate': untriggered_rate,
            'triggered_convert_rate': triggered_rate,
            'ratio': ratio,
        })

    print(pd.DataFrame(rows).to_string(index=False))
