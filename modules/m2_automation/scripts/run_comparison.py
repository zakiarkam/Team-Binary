import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.evaluation import compare_strategies, evaluate_events
from src.simulator import simulate_campaign
from src.strategies.fixed import OPERATIONAL_COMPLEXITY as FIXED_COMPLEXITY
from src.strategies.fixed import fixed_strategy
from src.strategies.hybrid import OPERATIONAL_COMPLEXITY as HYBRID_COMPLEXITY
from src.strategies.hybrid import hybrid_strategy
from src.strategies.trigger import OPERATIONAL_COMPLEXITY as TRIGGER_COMPLEXITY
from src.strategies.trigger import trigger_strategy

USERS_PATH = "data/processed/users_with_ml_scores.csv"
EVENT_LOGS_PATH = "outputs/event_logs.csv"
MAX_MESSAGES_PER_USER = 4
SEED = 42
SIGNAL_SPARSITY = 0.0


def print_message_breakdown(strategy_name, events_df):
    messages_per_user = events_df.groupby('user_id').size()
    mean_msgs = messages_per_user.mean()
    median_msgs = messages_per_user.median()
    full_pct = (messages_per_user == MAX_MESSAGES_PER_USER).mean() * 100
    fewer_pct = 100 - full_pct
    print(
        f"{strategy_name}: mean={mean_msgs:.2f}, median={median_msgs:.1f}, "
        f"full ({MAX_MESSAGES_PER_USER} msgs)={full_pct:.1f}%, early termination={fewer_pct:.1f}%"
    )


def main():
    users_df = pd.read_csv(USERS_PATH)

    assert 'ml_score' in users_df.columns, (
        f"'ml_score' column not found in {USERS_PATH} — run src/ml_model.py first "
        f"to generate data/processed/users_with_ml_scores.csv."
    )

    fixed_events = simulate_campaign(
        users_df, fixed_strategy,
        max_messages_per_user=MAX_MESSAGES_PER_USER, seed=SEED, signal_sparsity=SIGNAL_SPARSITY,
    )
    trigger_events = simulate_campaign(
        users_df, trigger_strategy,
        max_messages_per_user=MAX_MESSAGES_PER_USER, seed=SEED, signal_sparsity=SIGNAL_SPARSITY,
    )
    hybrid_events = simulate_campaign(
        users_df, hybrid_strategy,
        max_messages_per_user=MAX_MESSAGES_PER_USER, seed=SEED, signal_sparsity=SIGNAL_SPARSITY,
    )

    fixed_result = evaluate_events(fixed_events, strategy_name='fixed', complexity=FIXED_COMPLEXITY)
    trigger_result = evaluate_events(trigger_events, strategy_name='trigger', complexity=TRIGGER_COMPLEXITY)
    hybrid_result = evaluate_events(hybrid_events, strategy_name='hybrid', complexity=HYBRID_COMPLEXITY)

    comparison_df = compare_strategies([fixed_result, trigger_result, hybrid_result])

    event_logs = pd.concat([
        fixed_events.assign(strategy='fixed'),
        trigger_events.assign(strategy='trigger'),
        hybrid_events.assign(strategy='hybrid'),
    ], ignore_index=True)
    os.makedirs(os.path.dirname(EVENT_LOGS_PATH), exist_ok=True)
    event_logs.to_csv(EVENT_LOGS_PATH, index=False)

    print(comparison_df.to_string(index=False))

    trigger_vs_fixed = trigger_result['conversions_per_1000_sends'] / fixed_result['conversions_per_1000_sends']
    hybrid_vs_fixed = hybrid_result['conversions_per_1000_sends'] / fixed_result['conversions_per_1000_sends']
    hybrid_vs_trigger = hybrid_result['conversions_per_1000_sends'] / trigger_result['conversions_per_1000_sends']

    print()
    print(f"Trigger conv/1k vs Fixed conv/1k:  {trigger_vs_fixed:.2f}x")
    print(f"Hybrid  conv/1k vs Fixed conv/1k:  {hybrid_vs_fixed:.2f}x")
    print(f"Hybrid  conv/1k vs Trigger conv/1k: {hybrid_vs_trigger:.3f}x")

    untriggered_pct = (hybrid_events['triggered'] == False).mean() * 100
    triggered_pct = (hybrid_events['triggered'] == True).mean() * 100

    print()
    print("=== Hybrid routing behavior audit ===")
    print(f"Untriggered sends: {untriggered_pct:.1f}%")
    print(f"Triggered sends:   {triggered_pct:.1f}%")

    print()
    print("=== Messages-per-user breakdown ===")
    print_message_breakdown('fixed', fixed_events)
    print_message_breakdown('trigger', trigger_events)
    print_message_breakdown('hybrid', hybrid_events)


if __name__ == "__main__":
    main()
