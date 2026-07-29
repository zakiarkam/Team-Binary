"""Paired t-test on before vs after optimization final scores."""

import pandas as pd
from scipy.stats import ttest_rel

import config


def run(comparison_df: pd.DataFrame) -> pd.DataFrame:
    t, p = ttest_rel(comparison_df["before_final_score"], comparison_df["after_final_score"])
    significant = bool(p < 0.05)

    result = pd.DataFrame(
        [{"test": "paired_t_test", "t_statistic": t, "p_value": p, "significant_at_0.05": significant}]
    )
    result.to_csv(config.SIGNIFICANCE_CSV, index=False)
    print(f"Paired t-test: t={t:.4f}, p={p:.4f} | significant={significant}")
    return result
