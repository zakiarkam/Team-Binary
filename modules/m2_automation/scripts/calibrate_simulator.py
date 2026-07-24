import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.evaluation import compare_strategies, evaluate_events
from src.simulator import simulate_campaign
from src.strategies.fixed import OPERATIONAL_COMPLEXITY as FIXED_COMPLEXITY
from src.strategies.fixed import fixed_strategy
from src.strategies.trigger import OPERATIONAL_COMPLEXITY as TRIGGER_COMPLEXITY
from src.strategies.trigger import trigger_strategy

USERS_PATH = "data/processed/users_merged.csv"
MAX_MESSAGES_PER_USER = 4
SEED = 42
SIGNAL_SPARSITY = 0.0  # warm population — this is a warm calibration


def main():
    users_df = pd.read_csv(USERS_PATH)

    fixed_events = simulate_campaign(
        users_df,
        fixed_strategy,
        max_messages_per_user=MAX_MESSAGES_PER_USER,
        seed=SEED,
        signal_sparsity=SIGNAL_SPARSITY,
    )
    trigger_events = simulate_campaign(
        users_df,
        trigger_strategy,
        max_messages_per_user=MAX_MESSAGES_PER_USER,
        seed=SEED,
        signal_sparsity=SIGNAL_SPARSITY,
    )

    # PART 1 — Mechanism check (the actual gate)
    combined_events = pd.concat([fixed_events, trigger_events], ignore_index=True)

    untriggered_rows = combined_events[combined_events['triggered'] == False]
    triggered_rows = combined_events[combined_events['triggered'] == True]

    n_unt = len(untriggered_rows)
    untriggered_convert_rate = untriggered_rows['converted'].mean()
    n_tri = len(triggered_rows)
    triggered_convert_rate = triggered_rows['converted'].mean()

    mechanism_ratio = triggered_convert_rate / untriggered_convert_rate

    print("=== Mechanism check ===")
    print(f"Untriggered sends: N={n_unt}, convert rate={untriggered_convert_rate:.4f}")
    print(f"Triggered sends:   N={n_tri}, convert rate={triggered_convert_rate:.4f}")
    print(f"Mechanism ratio (triggered / untriggered): {mechanism_ratio:.2f}x")

    mechanism_pass = 2.0 <= mechanism_ratio <= 3.0

    # PART 2 — Campaign-level efficiency (reported, not gated)
    fixed_result = evaluate_events(fixed_events, strategy_name='fixed', complexity=FIXED_COMPLEXITY)
    trigger_result = evaluate_events(trigger_events, strategy_name='trigger', complexity=TRIGGER_COMPLEXITY)
    comparison_df = compare_strategies([fixed_result, trigger_result])

    campaign_ratio = trigger_result['conversions_per_1000_sends'] / fixed_result['conversions_per_1000_sends']
    cold_count = (trigger_events['triggered'] == False).sum()
    pct_cold = cold_count / len(trigger_events)

    print()
    print("=== Campaign-level efficiency (reported) ===")
    print(comparison_df.to_string(index=False))
    print(f"Trigger conv/1k vs Fixed conv/1k: {campaign_ratio:.2f}x")
    print(f"NOTE: Campaign-level ratio is structurally lower than mechanism uplift")
    print(f"because trigger's pool contains {pct_cold:.0%} cold first-sends. The")
    print(f"mechanism check above validates the underlying uplift math directly.")

    print()
    if mechanism_pass:
        print(f"CALIBRATION PASS — mechanism ratio {mechanism_ratio:.2f}x is within [2.0, 3.0]. Proceed to Phase 7.")
        sys.exit(0)
    else:
        print(f"CALIBRATION FAIL — mechanism ratio {mechanism_ratio:.2f}x is outside [2.0, 3.0]. Do NOT proceed. Debug the simulator or the strategies.")
        sys.exit(1)


if __name__ == "__main__":
    main()
