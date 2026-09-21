"""
Result persistence and plotting for CA-RIS experiments.

Saves results to:
  results/<dataset>_<timestamp>/
    summary.json     — full structured results
    metrics.csv      — flat table, one row per algorithm
    lambda_sweep.csv — sweep results (if applicable)

Plots saved to the same directory:
  comparison_bar.png    — bar chart of all 4 metrics (CA-RIS vs D-RIS vs RIS)
  lambda_tradeoff.png   — spread vs fairness as λ varies
  community_dist.png    — per-community seed distribution heatmap
  per_community_mc.png  — per-community MC spread (if available)
"""

import os
import json
import csv
import math
import datetime
from collections import defaultdict

# ── Matplotlib setup ──────────────────────────────────────────────────────────
import matplotlib
matplotlib.use('Agg')           # non-interactive backend — safe everywhere
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ── Directory helpers ─────────────────────────────────────────────────────────

def make_run_dir(dataset_name, base="results"):
    """
    Create a timestamped results directory.
    Returns the path string.
    """
    _dir = os.path.dirname(__file__)
    base_path = os.path.join(_dir, base)
    os.makedirs(base_path, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(base_path, f"{dataset_name}_{ts}")
    os.makedirs(run_dir, exist_ok=True)
    print(f"  [results] Writing to: {run_dir}")
    return run_dir


# ── JSON / CSV persistence ────────────────────────────────────────────────────

def save_summary_json(run_dir, dataset, k, lam, eps, modularity,
                      num_communities, results):
    """
    Save full experiment summary as JSON.
    Strips non-serialisable fields (RRR sets) before saving.
    """
    clean = {}
    for algo, r in results.items():
        clean[algo] = {
            'seeds': r['seeds'],
            'theta': r['theta'],
            'time_s': round(r['time'], 4),
            'mc_spread': r.get('mc_spread'),
            'sigma_hat': r.get('sigma_hat'),
            'cc': r.get('cc'),
            'entropy': r.get('entropy'),
            'gini': r.get('gini'),
            'quota_used': {str(k2): v for k2, v in r.get('quota_used', {}).items()},
            'quota_relaxed_steps': r.get('relaxed_steps', []),
        }

    payload = {
        'dataset': dataset,
        'k': k,
        'lambda': lam,
        'eps': eps,
        'modularity': round(modularity, 6),
        'num_communities': num_communities,
        'timestamp': datetime.datetime.now().isoformat(),
        'algorithms': clean,
    }

    path = os.path.join(run_dir, "summary.json")
    with open(path, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"  [results] Saved summary.json")
    return path


def save_metrics_csv(run_dir, results, metric_keys=None):
    """
    Save a flat CSV with one row per algorithm.

    Columns: algorithm, sigma_hat, mc_spread, cc, entropy, gini, time_s, theta
    """
    if metric_keys is None:
        metric_keys = ['sigma_hat', 'mc_spread', 'cc', 'entropy', 'gini',
                       'time_s', 'theta']

    path = os.path.join(run_dir, "metrics.csv")
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['algorithm'] + metric_keys)
        for algo, r in results.items():
            row = [algo] + [r.get(k, '') for k in metric_keys]
            writer.writerow(row)
    print(f"  [results] Saved metrics.csv")
    return path


def save_lambda_sweep_csv(run_dir, sweep_results):
    """Save λ-sweep results as CSV."""
    if not sweep_results:
        return None
    path = os.path.join(run_dir, "lambda_sweep.csv")
    keys = ['lam', 'sigma_hat', 'mc', 'cc', 'entropy', 'gini', 'time']
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for r in sweep_results:
            writer.writerow([r.get(k, '') for k in keys])
    print(f"  [results] Saved lambda_sweep.csv")
    return path


# ── Plotting ──────────────────────────────────────────────────────────────────

# Consistent colour palette across all plots
COLORS = {
    'CA-RIS': '#2196F3',   # blue  — proposed
    'D-RIS':  '#FF9800',   # orange — baseline
    'RIS':    '#4CAF50',   # green  — baseline
}
HATCH = {
    'CA-RIS': '',
    'D-RIS':  '//',
    'RIS':    'xx',
}


def plot_comparison_bar(run_dir, results, dataset, k, lam, modularity):
    """
    4-panel bar chart comparing CA-RIS, D-RIS, RIS across all evaluation metrics.

    Panels:
      1. Influence Spread σ̂(S) and MC σ(S)
      2. Community Coverage CC(S)
      3. Seed Distribution Entropy H(S)
      4. Gini Imbalance I(S)
    """
    algos = [a for a in ['CA-RIS', 'D-RIS', 'RIS'] if a in results]
    x = np.arange(len(algos))
    bar_w = 0.5

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle(
        f"CA-RIS vs Baselines — {dataset}  (k={k}, λ={lam}, Q={modularity:.3f})",
        fontsize=14, fontweight='bold', y=1.01
    )

    def _bar(ax, vals, title, ylabel, highlight_high=True, fmt='.2f'):
        colors = [COLORS.get(a, '#999') for a in algos]
        hatches = [HATCH.get(a, '') for a in algos]
        bars = ax.bar(x, vals, width=bar_w, color=colors)
        for bar, h in zip(bars, hatches):
            bar.set_hatch(h)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels(algos, fontsize=10)
        ax.yaxis.grid(True, linestyle='--', alpha=0.5)
        ax.set_axisbelow(True)
        # Value labels on bars
        for bar, v in zip(bars, vals):
            if v is not None:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01 * max(vals),
                        f'{v:{fmt}}', ha='center', va='bottom', fontsize=9)
        # Highlight best bar
        if highlight_high:
            best_idx = int(np.argmax([v if v is not None else -1 for v in vals]))
        else:
            best_idx = int(np.argmin([v if v is not None else 1e9 for v in vals]))
        bars[best_idx].set_edgecolor('black')
        bars[best_idx].set_linewidth(2.0)

    # Panel 1: Spread
    ax1 = axes[0, 0]
    mc_available = any(results[a].get('mc_spread') is not None for a in algos)
    if mc_available:
        # Grouped bars: σ̂ and MC side by side
        w = 0.3
        x2 = np.arange(len(algos))
        sig_hat = [results[a].get('sigma_hat', 0) for a in algos]
        mc_vals = [results[a].get('mc_spread') or 0 for a in algos]
        b1 = ax1.bar(x2 - w/2, sig_hat, width=w,
                     color=[COLORS.get(a, '#999') for a in algos],
                     label='σ̂ (RRR)', alpha=0.9)
        b2 = ax1.bar(x2 + w/2, mc_vals, width=w,
                     color=[COLORS.get(a, '#999') for a in algos],
                     label='σ (MC)', alpha=0.5,
                     hatch='//')
        ax1.set_title('Influence Spread', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Activated nodes', fontsize=9)
        ax1.set_xticks(x2)
        ax1.set_xticklabels(algos, fontsize=10)
        ax1.legend(fontsize=8)
        ax1.yaxis.grid(True, linestyle='--', alpha=0.5)
        ax1.set_axisbelow(True)
        for bar, v in zip(b1, sig_hat):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.01,
                     f'{v:.1f}', ha='center', va='bottom', fontsize=8)
        for bar, v in zip(b2, mc_vals):
            if v:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.01,
                         f'{v:.1f}', ha='center', va='bottom', fontsize=8)
    else:
        sig_hat = [results[a].get('sigma_hat', 0) for a in algos]
        _bar(ax1, sig_hat, 'Influence Spread σ̂(S)', 'Activated nodes (RRR est.)', fmt='.1f')

    # Panel 2: Community Coverage
    cc_vals = [results[a].get('cc', 0) for a in algos]
    _bar(axes[0, 1], cc_vals, 'Community Coverage CC(S)',
         'Fraction of communities with ≥1 seed', fmt='.3f')
    axes[0, 1].set_ylim(0, min(1.15, max(cc_vals) * 1.3 + 0.05))

    # Panel 3: Seed Entropy
    h_vals = [results[a].get('entropy', 0) for a in algos]
    _bar(axes[1, 0], h_vals, 'Seed Distribution Entropy H(S) [normalised]',
         'Normalised entropy [0–1]', fmt='.3f')
    axes[1, 0].set_ylim(0, min(1.15, max(h_vals) * 1.3 + 0.05))

    # Panel 4: Gini Imbalance
    gini_vals = [results[a].get('gini', 0) for a in algos]
    _bar(axes[1, 1], gini_vals, 'Gini Imbalance I(S)  [lower = more balanced]',
         'Gini coefficient [0–1]', highlight_high=False, fmt='.3f')
    axes[1, 1].set_ylim(0, min(1.15, max(gini_vals) * 1.3 + 0.05))

    # Legend patch for proposed vs baseline
    patches = [
        mpatches.Patch(color=COLORS['CA-RIS'], label='CA-RIS (proposed)'),
        mpatches.Patch(color=COLORS['D-RIS'],  label='D-RIS (baseline)'),
        mpatches.Patch(color=COLORS['RIS'],    label='RIS (baseline)'),
    ]
    fig.legend(handles=patches, loc='lower center', ncol=3,
               fontsize=10, bbox_to_anchor=(0.5, -0.04))

    fig.tight_layout()
    path = os.path.join(run_dir, "comparison_bar.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [results] Saved comparison_bar.png")
    return path


def plot_lambda_tradeoff(run_dir, sweep_results, dataset, k):
    """
    Dual-axis line plot showing how spread and fairness metrics vary with λ.

    Left axis:  σ̂(S) — influence spread
    Right axis: CC(S), H(S), Gini I(S) — fairness metrics
    """
    if not sweep_results:
        return None

    lambdas    = [r['lam']       for r in sweep_results]
    sigma_hats = [r['sigma_hat'] for r in sweep_results]
    cc_vals    = [r['cc']        for r in sweep_results]
    h_vals     = [r['entropy']   for r in sweep_results]
    gini_vals  = [r['gini']      for r in sweep_results]
    mc_vals    = [r.get('mc')    for r in sweep_results]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()

    # Left: spread
    l1, = ax1.plot(lambdas, sigma_hats, 'o-', color='#2196F3',
                   linewidth=2.5, markersize=7, label='σ̂(S) RRR spread')
    if any(v is not None for v in mc_vals):
        mc_clean = [v if v is not None else float('nan') for v in mc_vals]
        ax1.plot(lambdas, mc_clean, 's--', color='#1565C0',
                 linewidth=1.5, markersize=6, label='σ(S) MC spread')

    # Right: fairness metrics
    l2, = ax2.plot(lambdas, cc_vals,   '^-',  color='#4CAF50',
                   linewidth=2, markersize=7, label='CC(S) community coverage')
    l3, = ax2.plot(lambdas, h_vals,    's--', color='#FF9800',
                   linewidth=2, markersize=7, label='H(S) seed entropy (norm)')
    l4, = ax2.plot(lambdas, gini_vals, 'D:',  color='#F44336',
                   linewidth=2, markersize=7, label='Gini I(S) imbalance')

    # Shade the "sweet spot" region (λ where CC is highest and spread still competitive)
    best_cc_idx = int(np.argmax(cc_vals))
    ax1.axvspan(lambdas[max(0, best_cc_idx-1)],
                lambdas[min(len(lambdas)-1, best_cc_idx+1)],
                alpha=0.08, color='green', label='_nolegend_')

    ax1.set_xlabel('λ (fairness–spread trade-off parameter)', fontsize=11)
    ax1.set_ylabel('Influence Spread (nodes)', fontsize=11, color='#2196F3')
    ax2.set_ylabel('Fairness Metrics [0–1]', fontsize=11, color='#555')
    ax1.tick_params(axis='y', labelcolor='#2196F3')

    ax1.set_title(
        f"Spread–Fairness Trade-off — {dataset}  (k={k})",
        fontsize=13, fontweight='bold'
    )

    lines = [l1, l2, l3, l4]
    labs  = [l.get_label() for l in lines]
    ax1.legend(lines, labs, loc='center left', fontsize=9,
               bbox_to_anchor=(0.01, 0.35))
    ax1.xaxis.grid(True, linestyle='--', alpha=0.4)

    fig.tight_layout()
    path = os.path.join(run_dir, "lambda_tradeoff.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [results] Saved lambda_tradeoff.png")
    return path


def plot_community_distribution(run_dir, results, community_to_nodes, dataset, k):
    """
    Horizontal stacked bar chart: per-community seed allocation per algorithm.
    Shows top-25 communities by size.
    """
    algos = [a for a in ['CA-RIS', 'D-RIS', 'RIS'] if a in results]

    # Sort communities by size, keep top 25
    sorted_comms = sorted(community_to_nodes.items(),
                          key=lambda x: -len(x[1]))[:25]
    comm_labels = [f"C{cid}\n(n={len(nodes)})" for cid, nodes in sorted_comms]
    comm_ids    = [cid for cid, _ in sorted_comms]

    # Build seed count matrix: [algo][community]
    seed_counts = {}
    for algo in algos:
        S = set(results[algo]['seeds'])
        seed_counts[algo] = [
            sum(1 for n in community_to_nodes[cid] if n in S)
            for cid in comm_ids
        ]

    n_comms = len(comm_ids)
    y = np.arange(n_comms)
    h = 0.22
    offsets = np.linspace(-(len(algos)-1)*h/2, (len(algos)-1)*h/2, len(algos))

    fig, ax = plt.subplots(figsize=(10, max(6, n_comms * 0.35 + 2)))

    for i, algo in enumerate(algos):
        counts = seed_counts[algo]
        ax.barh(y + offsets[i], counts, height=h,
                color=COLORS.get(algo, '#999'),
                label=algo, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(comm_labels, fontsize=7)
    ax.set_xlabel('Number of seeds assigned', fontsize=10)
    ax.set_title(
        f"Per-Community Seed Distribution — {dataset}  (k={k})",
        fontsize=12, fontweight='bold'
    )
    ax.xaxis.grid(True, linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9)

    # Annotate: largest community fraction
    largest_size = len(sorted_comms[0][1])
    n_total = sum(len(v) for v in community_to_nodes.values())
    ax.text(0.98, 0.02,
            f"C{sorted_comms[0][0]} = {100*largest_size/n_total:.1f}% of graph",
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=8, color='#555')

    fig.tight_layout()
    path = os.path.join(run_dir, "community_dist.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [results] Saved community_dist.png")
    return path


def plot_per_community_mc(run_dir, mc_per_comm, community_to_nodes, dataset, k):
    """
    Bar chart of per-community MC spread for each algorithm.
    mc_per_comm: dict  algo → {cid: avg_activated}
    """
    if not mc_per_comm:
        return None

    algos = list(mc_per_comm.keys())
    sorted_comms = sorted(community_to_nodes.items(),
                          key=lambda x: -len(x[1]))[:20]
    comm_ids    = [cid for cid, _ in sorted_comms]
    comm_labels = [f"C{cid}" for cid in comm_ids]

    y = np.arange(len(comm_ids))
    h = 0.22
    offsets = np.linspace(-(len(algos)-1)*h/2, (len(algos)-1)*h/2, len(algos))

    fig, ax = plt.subplots(figsize=(10, max(6, len(comm_ids) * 0.4 + 2)))

    for i, algo in enumerate(algos):
        vals = [mc_per_comm[algo].get(cid, 0) for cid in comm_ids]
        ax.barh(y + offsets[i], vals, height=h,
                color=COLORS.get(algo, '#999'), label=algo, alpha=0.85)

    ax.set_yticks(y)
    ax.set_yticklabels(comm_labels, fontsize=8)
    ax.set_xlabel('Avg activated nodes (MC simulation)', fontsize=10)
    ax.set_title(
        f"Per-Community Influence Spread (MC) — {dataset}  (k={k})",
        fontsize=12, fontweight='bold'
    )
    ax.xaxis.grid(True, linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9)

    fig.tight_layout()
    path = os.path.join(run_dir, "per_community_mc.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [results] Saved per_community_mc.png")
    return path


def plot_runtime_comparison(run_dir, results, dataset, k):
    """Horizontal bar chart of runtimes."""
    algos = [a for a in ['CA-RIS', 'D-RIS', 'RIS'] if a in results]
    times = [results[a]['time'] for a in algos]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    bars = ax.barh(algos, times, color=[COLORS.get(a, '#999') for a in algos],
                   height=0.4)
    for bar, t in zip(bars, times):
        ax.text(bar.get_width() + 0.01 * max(times), bar.get_y() + bar.get_height()/2,
                f'{t:.2f}s', va='center', fontsize=10)

    ax.set_xlabel('Wall-clock time (seconds)', fontsize=10)
    ax.set_title(f'Runtime Comparison — {dataset}  (k={k})',
                 fontsize=12, fontweight='bold')
    ax.xaxis.grid(True, linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()

    path = os.path.join(run_dir, "runtime.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [results] Saved runtime.png")
    return path


# ── Master save-and-plot function ─────────────────────────────────────────────

def save_and_plot(dataset, k, lam, eps, modularity, community_to_nodes,
                  node_to_community, results, sweep_results=None,
                  mc_per_comm=None):
    """
    Convenience wrapper: create run directory, save all files, generate all plots.

    Parameters
    ----------
    dataset             : str name ('Slashdot' or 'Epinions')
    k, lam, eps         : experiment parameters
    modularity          : float Q from Louvain
    community_to_nodes  : community structure
    node_to_community   : node → community id
    results             : dict  algo → metrics (from run_experiment)
    sweep_results       : list of dicts from lambda_sweep (optional)
    mc_per_comm         : dict  algo → {cid: mc_spread} (optional)

    Returns
    -------
    run_dir : path where all files were saved
    """
    from algorithms import (community_coverage, seed_distribution_entropy,
                            gini_imbalance, fairness_objective)

    run_dir = make_run_dir(dataset.lower())

    # Enrich results with computed metrics for saving
    nodes_list = []
    for nodes_c in community_to_nodes.values():
        nodes_list.extend(nodes_c)

    for algo, r in results.items():
        S  = r['seeds']
        R  = r.get('R', [])
        r['time_s']   = round(r['time'], 4)
        r['cc']       = community_coverage(S, community_to_nodes)
        _, r['entropy'] = seed_distribution_entropy(S, community_to_nodes)
        r['gini']     = gini_imbalance(S, community_to_nodes)
        _, r['sigma_hat'], _ = fairness_objective(
            S, R, nodes_list, community_to_nodes, node_to_community, lam
        )

    # Persist
    save_summary_json(run_dir, dataset, k, lam, eps, modularity,
                      len(community_to_nodes), results)
    save_metrics_csv(run_dir, results)
    if sweep_results:
        save_lambda_sweep_csv(run_dir, sweep_results)

    # Plots
    plot_comparison_bar(run_dir, results, dataset, k, lam, modularity)
    plot_community_distribution(run_dir, results, community_to_nodes, dataset, k)
    plot_runtime_comparison(run_dir, results, dataset, k)
    if sweep_results:
        plot_lambda_tradeoff(run_dir, sweep_results, dataset, k)
    if mc_per_comm:
        plot_per_community_mc(run_dir, mc_per_comm, community_to_nodes, dataset, k)

    print(f"\n  All results saved to: {run_dir}/")
    return run_dir
