import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src.evaluation import evaluate_events
from src.simulator import simulate_campaign
from src.strategies.fixed import OPERATIONAL_COMPLEXITY as FIXED_COMPLEXITY
from src.strategies.fixed import fixed_strategy
from src.strategies.hybrid import OPERATIONAL_COMPLEXITY as HYBRID_COMPLEXITY
from src.strategies.hybrid import hybrid_strategy
from src.strategies.trigger import OPERATIONAL_COMPLEXITY as TRIGGER_COMPLEXITY
from src.strategies.trigger import trigger_strategy

USERS_PATH = "data/processed/users_with_ml_scores.csv"
RAW_OUTPUT_PATH = "outputs/sparsity_sweep_raw.csv"
SUMMARY_OUTPUT_PATH = "outputs/sparsity_sweep_summary.csv"

MAX_MESSAGES_PER_USER = 4
SPARSITY_LEVELS = [0.0, 0.2, 0.4, 0.6, 0.8]
SEEDS = range(1, 6)  # seeds_per_level = 5

STRATEGIES = [
    ('fixed', fixed_strategy, FIXED_COMPLEXITY),
    ('trigger', trigger_strategy, TRIGGER_COMPLEXITY),
    ('hybrid', hybrid_strategy, HYBRID_COMPLEXITY),
]


def build_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    summary_rows = []
    for sparsity in SPARSITY_LEVELS:
        for name, _, _ in STRATEGIES:
            subset = raw_df[(raw_df['sparsity'] == sparsity) & (raw_df['strategy'] == name)]
            summary_rows.append({
                'sparsity': sparsity,
                'strategy': name,
                'conv_per_1k_mean': subset['conv_per_1k'].mean(),
                'conv_per_1k_std': subset['conv_per_1k'].std(),
                'conv_rate_mean': subset['conv_rate'].mean(),
                'conv_rate_std': subset['conv_rate'].std(),
                'messages_sent_mean': subset['messages_sent'].mean(),
            })
    return pd.DataFrame(summary_rows)


def gap_vs_noise_table(summary_df: pd.DataFrame, strategy_a: str, strategy_b: str) -> pd.DataFrame:
    rows = []
    for sparsity in SPARSITY_LEVELS:
        row_a = summary_df[(summary_df['sparsity'] == sparsity) & (summary_df['strategy'] == strategy_a)].iloc[0]
        row_b = summary_df[(summary_df['sparsity'] == sparsity) & (summary_df['strategy'] == strategy_b)].iloc[0]

        gap = row_a['conv_per_1k_mean'] - row_b['conv_per_1k_mean']
        combined_std = np.sqrt(row_a['conv_per_1k_std'] ** 2 + row_b['conv_per_1k_std'] ** 2)
        ratio = abs(gap) / combined_std if combined_std > 0 else float('inf')

        if ratio <= 1.0:
            verdict = 'tied'
        elif gap > 0:
            verdict = f'{strategy_a}_wins'
        else:
            verdict = f'{strategy_a}_loses'

        rows.append({
            'sparsity': sparsity,
            f'{strategy_a}_conv_per_1k': row_a['conv_per_1k_mean'],
            f'{strategy_b}_conv_per_1k': row_b['conv_per_1k_mean'],
            'gap': gap,
            'combined_std': combined_std,
            'ratio': ratio,
            'verdict': verdict,
        })

    return pd.DataFrame(rows)


def main():
    users_df = pd.read_csv(USERS_PATH)

    rows = []
    for sparsity in SPARSITY_LEVELS:
        for seed in SEEDS:
            for name, strategy_fn, complexity in STRATEGIES:
                events_df = simulate_campaign(
                    users_df, strategy_fn,
                    max_messages_per_user=MAX_MESSAGES_PER_USER, seed=seed, signal_sparsity=sparsity,
                )
                result = evaluate_events(events_df, strategy_name=name, complexity=complexity)
                rows.append({
                    'sparsity': sparsity,
                    'seed': seed,
                    'strategy': name,
                    'conv_rate': result['conversion_rate'],
                    'conv_per_1k': result['conversions_per_1000_sends'],
                    'messages_sent': result['messages_sent'],
                    'days_to_convert': result['avg_days_to_convert'],
                })

    raw_df = pd.DataFrame(rows)
    os.makedirs('outputs', exist_ok=True)
    raw_df.to_csv(RAW_OUTPUT_PATH, index=False)

    summary_df = build_summary(raw_df)
    summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)
    print(summary_df.to_string(index=False))

    for label, strategy_a, strategy_b in [
        ('Hybrid vs Trigger', 'hybrid', 'trigger'),
        ('Hybrid vs Fixed', 'hybrid', 'fixed'),
        ('Trigger vs Fixed', 'trigger', 'fixed'),
    ]:
        print()
        print(f"=== {label}: gap-vs-noise on conv_per_1k across sparsity ===")
        print(gap_vs_noise_table(summary_df, strategy_a, strategy_b).to_string(index=False))


if __name__ == "__main__":
    main()
