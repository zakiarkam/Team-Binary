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
MAIN_SUMMARY_PATH = "outputs/sparsity_sweep_summary.csv"
RAW_OUTPUT_PATH = "outputs/sparsity_sweep_raw_extreme.csv"
SUMMARY_OUTPUT_PATH = "outputs/sparsity_sweep_summary_extreme.csv"

MAX_MESSAGES_PER_USER = 4
EXTREME_SPARSITY_LEVELS = [0.85, 0.90, 0.95, 0.99]
SEEDS = range(1, 6)  # seeds_per_level = 5, same as main sweep

STRATEGIES = [
    ('fixed', fixed_strategy, FIXED_COMPLEXITY),
    ('trigger', trigger_strategy, TRIGGER_COMPLEXITY),
    ('hybrid', hybrid_strategy, HYBRID_COMPLEXITY),
]


def build_summary(raw_df: pd.DataFrame, sparsity_levels) -> pd.DataFrame:
    summary_rows = []
    for sparsity in sparsity_levels:
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


def gap_vs_noise_table(summary_df: pd.DataFrame, strategy_a: str, strategy_b: str, sparsity_levels) -> pd.DataFrame:
    rows = []
    for sparsity in sparsity_levels:
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
    for sparsity in EXTREME_SPARSITY_LEVELS:
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

    summary_df = build_summary(raw_df, EXTREME_SPARSITY_LEVELS)
    summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)
    print(summary_df.to_string(index=False))

    for label, strategy_a, strategy_b in [
        ('Hybrid vs Trigger', 'hybrid', 'trigger'),
        ('Hybrid vs Fixed', 'hybrid', 'fixed'),
        ('Trigger vs Fixed', 'trigger', 'fixed'),
    ]:
        print()
        print(f"=== {label}: gap-vs-noise on conv_per_1k (extreme sparsity only) ===")
        print(gap_vs_noise_table(summary_df, strategy_a, strategy_b, EXTREME_SPARSITY_LEVELS).to_string(index=False))

    assert os.path.exists(MAIN_SUMMARY_PATH), (
        f"{MAIN_SUMMARY_PATH} not found — run scripts/run_sparsity_sweep.py first "
        f"to generate the 0.0-0.8 summary before combining with extreme levels."
    )
    main_summary_df = pd.read_csv(MAIN_SUMMARY_PATH)
    combined_summary_df = pd.concat([main_summary_df, summary_df], ignore_index=True)
    combined_sparsity_levels = sorted(combined_summary_df['sparsity'].unique())

    print()
    print("=== Hybrid vs Trigger: full trend, sparsity 0.0 -> 0.99 ===")
    print(gap_vs_noise_table(combined_summary_df, 'hybrid', 'trigger', combined_sparsity_levels).to_string(index=False))


if __name__ == "__main__":
    main()
