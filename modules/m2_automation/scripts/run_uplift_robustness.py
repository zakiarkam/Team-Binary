import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import src.simulator as sim
from src.evaluation import evaluate_events
from src.strategies.fixed import OPERATIONAL_COMPLEXITY as FIXED_COMPLEXITY
from src.strategies.fixed import fixed_strategy
from src.strategies.hybrid import OPERATIONAL_COMPLEXITY as HYBRID_COMPLEXITY
from src.strategies.hybrid import hybrid_strategy
from src.strategies.trigger import OPERATIONAL_COMPLEXITY as TRIGGER_COMPLEXITY
from src.strategies.trigger import trigger_strategy

USERS_PATH = "data/processed/users_with_ml_scores.csv"
RAW_OUTPUT_PATH = "outputs/uplift_robustness_raw.csv"
SUMMARY_OUTPUT_PATH = "outputs/uplift_robustness_summary.csv"

MAX_MESSAGES_PER_USER = 4
SIGNAL_SPARSITY = 0.0
UPLIFT_LEVELS = [1.5, 2.0, 2.5, 3.0]
SEEDS = range(1, 6)  # seeds_per_level = 5

STRATEGIES = [
    ('fixed', fixed_strategy, FIXED_COMPLEXITY),
    ('trigger', trigger_strategy, TRIGGER_COMPLEXITY),
    ('hybrid', hybrid_strategy, HYBRID_COMPLEXITY),
]

REFERENCE_ORDER = ['trigger', 'hybrid', 'fixed']

ORIGINAL_UPLIFT = sim.INTENT_UPLIFT


def build_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    summary_rows = []
    for uplift in UPLIFT_LEVELS:
        for name, _, _ in STRATEGIES:
            subset = raw_df[(raw_df['uplift'] == uplift) & (raw_df['strategy'] == name)]
            summary_rows.append({
                'uplift': uplift,
                'strategy': name,
                'conv_per_1k_mean': subset['conv_per_1k'].mean(),
                'conv_per_1k_std': subset['conv_per_1k'].std(),
                'conv_rate_mean': subset['conv_rate'].mean(),
                'conv_rate_std': subset['conv_rate'].std(),
                'messages_sent_mean': subset['messages_sent'].mean(),
            })
    return pd.DataFrame(summary_rows)


def main():
    users_df = pd.read_csv(USERS_PATH)

    rows = []
    try:
        for uplift in UPLIFT_LEVELS:
            sim.INTENT_UPLIFT = uplift
            for seed in SEEDS:
                for name, strategy_fn, complexity in STRATEGIES:
                    events_df = sim.simulate_campaign(
                        users_df, strategy_fn,
                        max_messages_per_user=MAX_MESSAGES_PER_USER, seed=seed, signal_sparsity=SIGNAL_SPARSITY,
                    )
                    result = evaluate_events(events_df, strategy_name=name, complexity=complexity)
                    rows.append({
                        'uplift': uplift,
                        'seed': seed,
                        'strategy': name,
                        'conv_rate': result['conversion_rate'],
                        'conv_per_1k': result['conversions_per_1000_sends'],
                        'messages_sent': result['messages_sent'],
                    })
    finally:
        sim.INTENT_UPLIFT = ORIGINAL_UPLIFT

    raw_df = pd.DataFrame(rows)
    os.makedirs('outputs', exist_ok=True)
    raw_df.to_csv(RAW_OUTPUT_PATH, index=False)

    summary_df = build_summary(raw_df)
    summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)
    print(summary_df.to_string(index=False))

    print()
    print("=== Ordering by conv_per_1k_mean (descending), per uplift ===")
    for uplift in UPLIFT_LEVELS:
        subset = summary_df[summary_df['uplift'] == uplift].sort_values('conv_per_1k_mean', ascending=False)
        order = subset['strategy'].tolist()
        verdict = "STABLE" if order == REFERENCE_ORDER else "CHANGED"
        print(f"uplift={uplift}: {' > '.join(order)}  [{verdict}]")

    print()
    print("=== Hybrid vs Trigger: gap-vs-noise on conv_per_1k, across uplift ===")
    gap_rows = []
    for uplift in UPLIFT_LEVELS:
        hybrid_row = summary_df[(summary_df['uplift'] == uplift) & (summary_df['strategy'] == 'hybrid')].iloc[0]
        trigger_row = summary_df[(summary_df['uplift'] == uplift) & (summary_df['strategy'] == 'trigger')].iloc[0]

        gap = hybrid_row['conv_per_1k_mean'] - trigger_row['conv_per_1k_mean']
        combined_std = np.sqrt(hybrid_row['conv_per_1k_std'] ** 2 + trigger_row['conv_per_1k_std'] ** 2)
        ratio = abs(gap) / combined_std if combined_std > 0 else float('inf')

        if ratio <= 1.0:
            verdict = 'tied'
        elif gap > 0:
            verdict = 'hybrid_wins'
        else:
            verdict = 'hybrid_loses'

        gap_rows.append({
            'uplift': uplift,
            'hybrid_conv_per_1k': hybrid_row['conv_per_1k_mean'],
            'trigger_conv_per_1k': trigger_row['conv_per_1k_mean'],
            'gap': gap,
            'combined_std': combined_std,
            'ratio': ratio,
            'verdict': verdict,
        })
    print(pd.DataFrame(gap_rows).to_string(index=False))


if __name__ == "__main__":
    main()
