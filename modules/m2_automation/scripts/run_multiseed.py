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
RAW_OUTPUT_PATH = "outputs/multiseed_results_raw.csv"
SUMMARY_OUTPUT_PATH = "outputs/multiseed_summary.csv"

MAX_MESSAGES_PER_USER = 4
SIGNAL_SPARSITY = 0.0
SEEDS = range(1, 21)  # seeds 1..20 — seed=42 already covered by run_comparison.py

STRATEGIES = [
    ('fixed', fixed_strategy, FIXED_COMPLEXITY),
    ('trigger', trigger_strategy, TRIGGER_COMPLEXITY),
    ('hybrid', hybrid_strategy, HYBRID_COMPLEXITY),
]

SUMMARY_METRICS = [
    ('conv_rate', 'conversion_rate'),
    ('conv_per_1k', 'conv_per_1000'),
    ('messages_sent', 'messages_sent'),
    ('days_to_convert', 'days_to_convert'),
]


def build_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    summary_rows = []
    for name, _, _ in STRATEGIES:
        subset = raw_df[raw_df['strategy'] == name]
        row = {'strategy': name}
        for prefix, col in SUMMARY_METRICS:
            row[f'{prefix}_mean'] = subset[col].mean()
            row[f'{prefix}_std'] = subset[col].std()
        summary_rows.append(row)
    return pd.DataFrame(summary_rows)


def gap_analysis(summary_df: pd.DataFrame) -> pd.DataFrame:
    def get_row(name):
        return summary_df[summary_df['strategy'] == name].iloc[0]

    pairs = [
        ('Trigger vs Fixed', get_row('trigger'), get_row('fixed')),
        ('Hybrid vs Fixed', get_row('hybrid'), get_row('fixed')),
        ('Hybrid vs Trigger', get_row('hybrid'), get_row('trigger')),
    ]
    metrics = [
        ('conv_per_1k', 'conv_per_1k_mean', 'conv_per_1k_std'),
        ('conv_rate', 'conv_rate_mean', 'conv_rate_std'),
    ]

    gap_rows = []
    for pair_name, row_a, row_b in pairs:
        for metric_name, mean_col, std_col in metrics:
            gap = row_a[mean_col] - row_b[mean_col]
            combined_std = np.sqrt(row_a[std_col] ** 2 + row_b[std_col] ** 2)
            ratio = abs(gap) / combined_std if combined_std > 0 else float('inf')
            if ratio > 2.0:
                verdict = "SIGNIFICANT"
            elif ratio > 1.0:
                verdict = "MARGINAL"
            else:
                verdict = "INSIDE NOISE BAND"
            gap_rows.append({
                'comparison': pair_name,
                'metric': metric_name,
                'gap': gap,
                'combined_std': combined_std,
                'ratio': ratio,
                'verdict': verdict,
            })

    return pd.DataFrame(gap_rows)


def main():
    users_df = pd.read_csv(USERS_PATH)

    rows = []
    for seed in SEEDS:
        np.random.seed(seed)
        for name, strategy_fn, complexity in STRATEGIES:
            events_df = simulate_campaign(
                users_df, strategy_fn,
                max_messages_per_user=MAX_MESSAGES_PER_USER, seed=seed, signal_sparsity=SIGNAL_SPARSITY,
            )
            result = evaluate_events(events_df, strategy_name=name, complexity=complexity)
            rows.append({
                'seed': seed,
                'strategy': name,
                'conversion_rate': result['conversion_rate'],
                'conv_per_1000': result['conversions_per_1000_sends'],
                'messages_sent': result['messages_sent'],
                'days_to_convert': result['avg_days_to_convert'],
            })

    raw_df = pd.DataFrame(rows)
    os.makedirs('outputs', exist_ok=True)
    raw_df.to_csv(RAW_OUTPUT_PATH, index=False)

    summary_df = build_summary(raw_df)
    summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)
    print(summary_df.to_string(index=False))

    gap_df = gap_analysis(summary_df)
    print()
    print(gap_df.to_string(index=False))

    conv_per_1k_verdicts = {
        row['comparison']: row['verdict']
        for _, row in gap_df[gap_df['metric'] == 'conv_per_1k'].iterrows()
    }

    print()
    print("=== Interpretation (gap vs noise only — not a best-strategy verdict) ===")
    print(f"Trigger vs Fixed: {conv_per_1k_verdicts['Trigger vs Fixed']}")
    print(f"Hybrid vs Fixed: {conv_per_1k_verdicts['Hybrid vs Fixed']}")
    print(f"Hybrid vs Trigger: {conv_per_1k_verdicts['Hybrid vs Trigger']}")


if __name__ == "__main__":
    main()
