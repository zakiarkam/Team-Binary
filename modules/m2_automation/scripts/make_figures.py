import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 14,
})

FIGURES_DIR = "outputs/figures"

STRATEGY_ORDER = ['fixed', 'trigger', 'hybrid']
STRATEGY_COLORS = {
    'fixed': '#4C72B0',    # blue
    'trigger': '#DD8452',  # orange
    'hybrid': '#55A868',   # green
}

# Route colors mirror strategy colors, since each hybrid route delegates to
# (or mimics) the corresponding pure strategy's behavior.
ROUTE_ORDER = ['fallback', 'trigger_path', 'blended']
ROUTE_COLORS = {
    'fallback': STRATEGY_COLORS['fixed'],
    'trigger_path': STRATEGY_COLORS['trigger'],
    'blended': STRATEGY_COLORS['hybrid'],
}

# Consistent segment palette for any figure that groups by segment_name.
SEGMENT_PALETTE = {
    'High Intent': '#4C72B0',
    'Loyal Customer': '#55A868',
    'Price Sensitive': '#C44E52',
    'Low Engagement': '#8172B2',
    'New Cold User': '#CCB974',
}


def savefig(fig, name, rect=None):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = os.path.join(FIGURES_DIR, name)
    if rect is not None:
        fig.tight_layout(rect=rect)
    else:
        fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Wrote {path}")


def significance_ratio(row_a, row_b, mean_col, std_col):
    gap = row_a[mean_col] - row_b[mean_col]
    combined_std = np.sqrt(row_a[std_col] ** 2 + row_b[std_col] ** 2)
    ratio = abs(gap) / combined_std if combined_std > 0 else float('inf')
    return ratio


def route_for_user(row):
    if row['segment_name'] == 'New Cold User' or row['ml_score'] < 0.30:
        return 'fallback'
    elif row['segment_name'] in ('High Intent', 'Loyal Customer'):
        return 'trigger_path'
    else:
        return 'blended'


def figure1_strategy_comparison_bars():
    summary = pd.read_csv('outputs/multiseed_summary.csv')
    summary = summary.set_index('strategy').loc[STRATEGY_ORDER].reset_index()
    colors = [STRATEGY_COLORS[s] for s in summary['strategy']]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    ax = axes[0]
    bars = ax.bar(summary['strategy'], summary['conv_per_1k_mean'],
                   yerr=summary['conv_per_1k_std'], capsize=6, color=colors)
    offset = ax.get_ylim()[1] * 0.03
    for bar, val, std in zip(bars, summary['conv_per_1k_mean'], summary['conv_per_1k_std']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + std + offset,
                f"{val:.2f}", ha='center', va='bottom')
    ax.set_title("Per-send conversion efficiency: 20-seed mean")
    ax.set_ylabel("Conversions per 1000 sends")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.1)

    ax2 = axes[1]
    conv_rate_pct = summary['conv_rate_mean'] * 100
    conv_rate_std_pct = summary['conv_rate_std'] * 100
    bars2 = ax2.bar(summary['strategy'], conv_rate_pct, yerr=conv_rate_std_pct, capsize=6, color=colors)
    offset2 = ax2.get_ylim()[1] * 0.03
    for bar, val, std in zip(bars2, conv_rate_pct, conv_rate_std_pct):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + std + offset2,
                  f"{val:.2f}%", ha='center', va='bottom')
    ax2.set_title("User-level conversion rate: 20-seed mean")
    ax2.set_ylabel("Conversion rate (%)")
    ax2.set_ylim(0, ax2.get_ylim()[1] * 1.1)

    row = {s: summary[summary['strategy'] == s].iloc[0] for s in STRATEGY_ORDER}
    tf = significance_ratio(row['trigger'], row['fixed'], 'conv_per_1k_mean', 'conv_per_1k_std')
    hf = significance_ratio(row['hybrid'], row['fixed'], 'conv_per_1k_mean', 'conv_per_1k_std')
    ht = significance_ratio(row['hybrid'], row['trigger'], 'conv_per_1k_mean', 'conv_per_1k_std')
    annotation = (
        f"Trigger vs Fixed: {tf:.2f}σ | "
        f"Hybrid vs Fixed: {hf:.2f}σ | "
        f"Hybrid vs Trigger: {ht:.2f}σ"
    )
    fig.text(0.5, 0.98, annotation, ha='center', va='top', fontsize=10)

    savefig(fig, 'strategy_comparison_bars.png', rect=[0, 0, 1, 0.92])


def figure2_funnel_by_strategy():
    events = pd.read_csv('outputs/event_logs.csv')
    stages = ['Sent', 'Opened', 'Clicked', 'Converted']

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))

    for ax, strat in zip(axes, STRATEGY_ORDER):
        g = events[events['strategy'] == strat]
        sent = len(g)
        opened = int(g['opened'].sum())
        clicked = int(g['clicked'].sum())
        converted = int(g.groupby('user_id')['converted'].any().sum())
        counts = [sent, opened, clicked, converted]

        y_pos = range(len(stages))
        ax.barh(y_pos, counts, color=STRATEGY_COLORS[strat])
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(stages)
        ax.invert_yaxis()
        ax.set_xlabel("Count")
        ax.set_title(strat.capitalize())

        for i, c in enumerate(counts):
            ax.text(c, i, f" {c:,}", va='center', fontsize=9)

        pct_open = opened / sent * 100 if sent else 0.0
        pct_click = clicked / opened * 100 if opened else 0.0
        pct_conv = converted / clicked * 100 if clicked else 0.0
        ax.text(0.5, 1.15,
                 f"open/sent={pct_open:.1f}%  click/open={pct_click:.1f}%  conv/click={pct_conv:.1f}%",
                 transform=ax.transAxes, ha='center', fontsize=9)

    fig.suptitle("Message funnel by strategy (seed=42)")
    savefig(fig, 'funnel_by_strategy.png', rect=[0, 0, 1, 0.90])


def figure3_sparsity_sweep():
    summary = pd.read_csv('outputs/sparsity_sweep_summary.csv')

    fig, ax = plt.subplots(figsize=(9, 6))
    for strat in STRATEGY_ORDER:
        sub = summary[summary['strategy'] == strat].sort_values('sparsity')
        ax.errorbar(sub['sparsity'], sub['conv_per_1k_mean'], yerr=sub['conv_per_1k_std'],
                     label=strat, color=STRATEGY_COLORS[strat], marker='o', capsize=4)

    ax.set_xlabel("signal_sparsity")
    ax.set_ylabel("conv_per_1k")
    ax.set_title("Efficiency degradation under increasing signal sparsity (5 seeds/level)")
    ax.legend(loc='center left')

    hybrid_sub = summary[summary['strategy'] == 'hybrid'].sort_values('sparsity').reset_index(drop=True)
    trigger_sub = summary[summary['strategy'] == 'trigger'].sort_values('sparsity').reset_index(drop=True)
    ratios = [
        significance_ratio(hybrid_sub.iloc[i], trigger_sub.iloc[i], 'conv_per_1k_mean', 'conv_per_1k_std')
        for i in range(len(hybrid_sub))
    ]

    ymin, ymax = ax.get_ylim()
    headroom_top = ymax + (ymax - ymin) * 0.12
    ax.set_ylim(ymin, headroom_top)
    annotation_y = ymax + (ymax - ymin) * 0.04
    for x, r in zip(hybrid_sub['sparsity'], ratios):
        ax.annotate(f"{r:.2f}σ", xy=(x, annotation_y), ha='center', fontsize=8, color='dimgray')

    savefig(fig, 'sparsity_sweep.png')


def figure4_complexity_vs_performance():
    from src.strategies.fixed import OPERATIONAL_COMPLEXITY as FIXED_COMPLEXITY
    from src.strategies.hybrid import OPERATIONAL_COMPLEXITY as HYBRID_COMPLEXITY
    from src.strategies.trigger import OPERATIONAL_COMPLEXITY as TRIGGER_COMPLEXITY

    complexity = {'fixed': FIXED_COMPLEXITY, 'trigger': TRIGGER_COMPLEXITY, 'hybrid': HYBRID_COMPLEXITY}
    summary = pd.read_csv('outputs/multiseed_summary.csv').set_index('strategy')

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    ax1 = axes[0]
    for strat in STRATEGY_ORDER:
        x = complexity[strat]
        y = summary.loc[strat, 'conv_per_1k_mean']
        ax1.scatter(x, y, s=350, color=STRATEGY_COLORS[strat], edgecolor='black', zorder=3)
        ax1.annotate(strat, (x, y), textcoords='offset points', xytext=(10, 10), fontsize=11)
    ax1.set_xlabel("Operational complexity")
    ax1.set_ylabel("Conversions per 1000 sends")
    ax1.set_title("Complexity vs per-send efficiency")

    ax2 = axes[1]
    for strat in STRATEGY_ORDER:
        x = complexity[strat]
        y = summary.loc[strat, 'conv_rate_mean'] * 100
        ax2.scatter(x, y, s=350, color=STRATEGY_COLORS[strat], edgecolor='black', zorder=3)
        ax2.annotate(strat, (x, y), textcoords='offset points', xytext=(10, 10), fontsize=11)
    ax2.set_xlabel("Operational complexity")
    ax2.set_ylabel("User-level conversion rate (%)")
    ax2.set_title("Complexity vs user-level conversion")

    fig.suptitle("Operational complexity vs performance")
    fig.text(0.5, 0.93,
              "No single strategy dominates both metrics: trigger optimizes per-send\n"
              "efficiency; fixed and hybrid optimize user-level reach at higher complexity.",
              ha='center', va='top', fontsize=10, fontstyle='italic')
    savefig(fig, 'complexity_vs_performance.png', rect=[0, 0, 1, 0.85])


def figure5_hybrid_routing_breakdown():
    users = pd.read_csv('data/processed/users_with_ml_scores.csv')
    users['route'] = users.apply(route_for_user, axis=1)

    route_counts = users['route'].value_counts().reindex(ROUTE_ORDER).fillna(0)

    events = pd.read_csv('outputs/event_logs.csv')
    hybrid_events = events[events['strategy'] == 'hybrid'].merge(
        users[['CustomerID', 'route']], left_on='user_id', right_on='CustomerID')
    conv_per_1k_by_route = hybrid_events.groupby('route')['converted'].apply(
        lambda s: s.sum() / len(s) * 1000).reindex(ROUTE_ORDER)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))

    ax1 = axes[0]
    colors = [ROUTE_COLORS[r] for r in ROUTE_ORDER]
    total = route_counts.sum()
    labels = [f"{r}\n{int(c)} ({c / total * 100:.1f}%)" for r, c in zip(ROUTE_ORDER, route_counts)]
    ax1.pie(route_counts, labels=labels, colors=colors, startangle=90)
    ax1.set_title("Population share by internal route")

    ax2 = axes[1]
    bars = ax2.bar(ROUTE_ORDER, conv_per_1k_by_route, color=colors)
    offset = ax2.get_ylim()[1] * 0.02
    for bar, val in zip(bars, conv_per_1k_by_route):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + offset, f"{val:.2f}", ha='center', va='bottom')
    ax2.set_ylabel("Conversions per 1000 sends")
    ax2.set_title("Efficiency by internal route")

    fig.suptitle("Hybrid strategy internal routing: population and performance")
    savefig(fig, 'hybrid_routing_breakdown.png', rect=[0, 0, 1, 0.90])


def figure6_ml_model_diagnostics():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import auc, confusion_matrix, precision_recall_curve, roc_curve
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline

    from src.ml_model import CATEGORICAL_FEATURES, NUMERICAL_FEATURES, TARGET
    from src.ml_model import DATA_PATH as ML_DATA_PATH
    from src.ml_model import build_preprocessor

    df = pd.read_csv(ML_DATA_PATH)
    X = df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    lr_pipeline = Pipeline([
        ('preprocessor', build_preprocessor()),
        ('classifier', LogisticRegression(max_iter=2000, random_state=42)),
    ])
    lr_pipeline.fit(X_train, y_train)

    rf_pipeline = Pipeline([
        ('preprocessor', build_preprocessor()),
        ('classifier', RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)),
    ])
    rf_pipeline.fit(X_train, y_train)

    lr_proba = lr_pipeline.predict_proba(X_test)[:, 1]
    rf_proba = rf_pipeline.predict_proba(X_test)[:, 1]
    rf_pred = rf_pipeline.predict(X_test)

    fig, axes = plt.subplots(2, 2, figsize=(12, 11))

    ax = axes[0, 0]
    cm = confusion_matrix(y_test, rf_pred, labels=[0, 1])
    im = ax.imshow(cm, cmap='Blues')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Pred 0', 'Pred 1'])
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['True 0', 'True 1'])
    for i in range(2):
        for j in range(2):
            text_color = 'white' if cm[i, j] > cm.max() / 2 else 'black'
            ax.text(j, i, str(cm[i, j]), ha='center', va='center', color=text_color, fontsize=12)
    ax.set_title("Random Forest confusion matrix")
    fig.colorbar(im, ax=ax, fraction=0.046)

    ax = axes[0, 1]
    for name, proba, color in [('LR', lr_proba, STRATEGY_COLORS['fixed']), ('RF', rf_proba, STRATEGY_COLORS['hybrid'])]:
        fpr, tpr, _ = roc_curve(y_test, proba)
        auc_val = auc(fpr, tpr)
        ax.plot(fpr, tpr, label=f"{name} (AUC={auc_val:.3f})", color=color)
    ax.plot([0, 1], [0, 1], linestyle='--', color='gray')
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC curve")
    ax.legend()

    ax = axes[1, 0]
    base_rate = y_test.mean()
    for name, proba, color in [('LR', lr_proba, STRATEGY_COLORS['fixed']), ('RF', rf_proba, STRATEGY_COLORS['hybrid'])]:
        precision, recall, _ = precision_recall_curve(y_test, proba)
        pr_auc = auc(recall, precision)
        ax.plot(recall, precision, label=f"{name} (AUC={pr_auc:.3f})", color=color)
    ax.axhline(base_rate, linestyle='--', color='gray', label=f"Base rate ({base_rate:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall curve")
    ax.legend()

    ax = axes[1, 1]
    feature_names = rf_pipeline.named_steps['preprocessor'].get_feature_names_out()
    importances = rf_pipeline.named_steps['classifier'].feature_importances_
    imp_df = pd.DataFrame({'feature': feature_names, 'importance': importances}) \
        .sort_values('importance', ascending=False).head(10)
    ax.barh(imp_df['feature'][::-1], imp_df['importance'][::-1], color=STRATEGY_COLORS['hybrid'])
    ax.set_xlabel("Importance")
    ax.set_title("Top-10 RF feature importances")

    fig.suptitle("ML routing model: diagnostics")
    savefig(fig, 'ml_model_diagnostics.png', rect=[0, 0, 1, 0.94])


def main():
    figures = [
        ('strategy_comparison_bars.png', figure1_strategy_comparison_bars),
        ('funnel_by_strategy.png', figure2_funnel_by_strategy),
        ('sparsity_sweep.png', figure3_sparsity_sweep),
        ('complexity_vs_performance.png', figure4_complexity_vs_performance),
        ('hybrid_routing_breakdown.png', figure5_hybrid_routing_breakdown),
        ('ml_model_diagnostics.png', figure6_ml_model_diagnostics),
    ]

    succeeded = []
    for name, fn in figures:
        try:
            fn()
            succeeded.append(name)
        except Exception as e:
            print(f"ERROR building {name}: {e}")

    print()
    print("=== Figures successfully written ===")
    for name in succeeded:
        print(f"- outputs/figures/{name}")
    if len(succeeded) < len(figures):
        failed = [name for name, _ in figures if name not in succeeded]
        print()
        print("=== Figures that FAILED ===")
        for name in failed:
            print(f"- {name}")


if __name__ == "__main__":
    main()
