import os

import pandas as pd

OUTPUT_PATH = "outputs/strategy_comparison.csv"

COMPARISON_COLUMNS = [
    'strategy',
    'n_users',
    'messages_sent',
    'open_rate',
    'ctr',
    'conversion_rate',
    'conversions_per_1000_sends',
    'avg_days_to_convert',
    'operational_complexity',
]


def evaluate_events(events_df, strategy_name: str, complexity: int) -> dict:
    """
    conversion_rate is user-level and inflates with message volume
    (more sends per user = more chances to convert).
    conversions_per_1000_sends is the volume-controlled efficiency metric.
    Report both; interpret differences using conversions_per_1000_sends.
    """
    n_users = events_df['user_id'].nunique()
    messages_sent = len(events_df)

    converted_per_user = events_df.groupby('user_id')['converted'].any()
    total_conversions = converted_per_user.sum()

    converting_events = events_df[events_df['converted']]
    if converting_events.empty:
        avg_days_to_convert = float('nan')
    else:
        first_convert_day = converting_events.groupby('user_id')['timestamp_day'].min()
        avg_days_to_convert = first_convert_day.mean()

    return {
        'strategy': strategy_name,
        'n_users': n_users,
        'messages_sent': messages_sent,
        'total_opens': events_df['opened'].sum(),
        'total_clicks': events_df['clicked'].sum(),
        'total_conversions': total_conversions,
        'open_rate': events_df['opened'].mean(),
        'ctr': events_df['clicked'].mean(),
        'conversion_rate': total_conversions / n_users,
        'conversions_per_1000_sends': (total_conversions / messages_sent) * 1000,
        'avg_days_to_convert': avg_days_to_convert,
        'operational_complexity': complexity,
    }


def compare_strategies(list_of_result_dicts) -> pd.DataFrame:
    comparison_df = pd.DataFrame(list_of_result_dicts)[COMPARISON_COLUMNS]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    comparison_df.to_csv(OUTPUT_PATH, index=False)

    return comparison_df


if __name__ == "__main__":
    rows = []
    for user_id in range(10):
        converts = user_id < 5
        convert_at = user_id % 3
        for message_index in range(3):
            if converts:
                opened = message_index <= convert_at
                clicked = opened and (message_index == convert_at)
                converted = message_index == convert_at
            else:
                opened = message_index % 2 == 0
                clicked = False
                converted = False
            rows.append({
                'user_id': user_id,
                'message_index': message_index,
                'sent': True,
                'opened': opened,
                'clicked': clicked,
                'converted': converted,
                'triggered': False,
                'timestamp_day': message_index,
                'segment_name': 'Test',
            })
    events_df = pd.DataFrame(rows)

    result = evaluate_events(events_df, strategy_name='test', complexity=5)
    print(result)

    expected_messages_sent = len(events_df)
    expected_total_conversions = events_df.groupby('user_id')['converted'].any().sum()
    expected_conversions_per_1000 = (expected_total_conversions / expected_messages_sent) * 1000

    checks = [
        ('messages_sent', result['messages_sent'] == expected_messages_sent),
        ('total_conversions', result['total_conversions'] == expected_total_conversions),
        ('conversions_per_1000_sends',
         abs(result['conversions_per_1000_sends'] - expected_conversions_per_1000) < 1e-9),
    ]

    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"FAILED checks: {failed}")
        raise AssertionError(f"Assertion(s) failed: {failed}")

    print("All assertions passed.")
