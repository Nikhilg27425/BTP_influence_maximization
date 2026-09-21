"""
Experiments for Community-Aware RIS (CA-RIS) — Proposed Algorithm.

Compares CA-RIS against D-RIS and RIS on the Slashdot and Epinions datasets
using four evaluation metrics:
  1. Influence Spread σ(S)       — Monte Carlo IC simulation
  2. Community Coverage          — fraction of communities with ≥ 1 seed
  3. Seed Distribution Entropy   — uniformity of seed placement across communities
  4. Runtime                     — wall-clock time

Usage
-----
  python experiments.py slashdot [--k 50] [--lam 0.5] [--eps 0.5] [--sub N]
  python experiments.py epinions [--k 50] [--lam 0.5] [--eps 0.5] [--sub N]
  python experiments.py all      [--k 50] [--lam 0.5] [--eps 0.5] [--sub N]

  --k   N      seed set size (default 50)
  --lam F      λ trade-off parameter for CA-RIS (default 0.5)
  --eps F      approximation parameter ε (default 0.5)
  --sub N      subsample N nodes via BFS for quick testing
  --no-mc      skip Monte Carlo spread evaluation (faster, no σ(S) values)
  --lambda-sweep  run CA-RIS for λ ∈ {0, 0.25, 0.5, 1.0, 2.0} and plot trade-off

Examples
--------
  # Quick test on 2000-node subgraph, k=20
  python experiments.py slashdot --sub 2000 --k 20

  # Full run on Epinions, k=50, λ=0.5
  python experiments.py epinions --k 50 --lam 0.5

  # λ trade-off sweep on Slashdot subgraph
  python experiments.py slashdot --sub 2000 --k 20 --lambda-sweep
"""

import sys
import os
import time
import random
import math

sys.path.insert(0, os.path.dirname(__file__))

from graph import (load_snap_directed, sample_subgraph,
                   detect_communities_louvain_fallback, community_stats)
from algorithms import (ca_ris, dris, ris,
                        community_coverage, seed_distribution_entropy,
                        gini_imbalance, fairness_objective, print_metrics)
from monte_carlo import mc_spread, mc_spread_per_community
from results import save_and_plot

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIR          = os.path.dirname(__file__)
SLASHDOT_PATH = os.path.join(_DIR, "data", "Slashdot0902.txt")
EPINIONS_PATH = os.path.join(_DIR, "data", "soc-Epinions1.txt")

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_K    = 50
DEFAULT_LAM  = 0.5
DEFAULT_EPS  = 0.5
DEFAULT_P    = 0.01
EVAL_RUNS    = 10_000
SEED         = 42

# ── Helpers ───────────────────────────────────────────────────────────────────

def sep(title=""):
    w = 72
    print("\n" + "=" * w)
    if title:
        print(title)
        print("=" * w)


def timed(fn, *args, **kwargs):
    t0 = time.time()
    result = fn(*args, **kwargs)
    return result, time.time() - t0


# ── Core experiment ───────────────────────────────────────────────────────────

def run_experiment(name, nodes, p, k=DEFAULT_K, lam=DEFAULT_LAM,
                   eps=DEFAULT_EPS, run_mc=True, eval_runs=EVAL_RUNS):
    """
    Full comparative experiment: CA-RIS vs D-RIS vs RIS.

    Steps
    -----
    1. Detect communities with Louvain.
    2. Run CA-RIS (proposed), D-RIS (baseline), RIS (baseline).
    3. Evaluate all four metrics for each algorithm.
    4. Print a structured comparison table.

    Returns dict of results keyed by algorithm name.
    """
    n_edges = sum(len(p[u]) for u in nodes)
    sep(f"Experiment: {name}")
    print(f"  Nodes: {len(nodes):,}  |  Edges: {n_edges:,}  "
          f"|  k={k}  |  λ={lam}  |  ε={eps}")

    # ── Step 1: Community detection ───────────────────────────────────────────
    sep(f"[{name}] Community Detection (Louvain)")
    (node_to_comm, comm_to_nodes, modularity), t_comm = timed(
        detect_communities_louvain_fallback, nodes, p
    )
    print(f"  Modularity Q = {modularity:.4f}  "
          f"(detected in {t_comm:.2f}s)")
    stats = community_stats(comm_to_nodes, node_to_comm, p)

    results = {}

    # ── Step 2a: CA-RIS (proposed) ────────────────────────────────────────────
    sep(f"[{name}] CA-RIS  (proposed, λ={lam})")
    (ca_out, t_ca) = timed(
        ca_ris, nodes, p, k, node_to_comm, comm_to_nodes, lam, eps
    )
    S_ca, R_ca, theta_ca, quota_ca, relaxed_ca = ca_out

    mc_ca = None
    if run_mc:
        print(f"  [CA-RIS] Evaluating MC spread ({eval_runs:,} runs)...")
        mc_ca = mc_spread(p, S_ca, eval_runs)

    results['CA-RIS'] = dict(
        seeds=S_ca, theta=theta_ca, time=t_ca,
        mc_spread=mc_ca, quota_used=quota_ca,
        relaxed_steps=relaxed_ca, R=R_ca
    )
    print_metrics('CA-RIS', S_ca, R_ca, nodes, comm_to_nodes,
                  node_to_comm, lam, mc_ca)

    # ── Step 2b: D-RIS (baseline) ─────────────────────────────────────────────
    sep(f"[{name}] D-RIS  (baseline, Sun & Chen 2021)")
    (S_dr, R_dr, theta_dr), t_dr = timed(dris, nodes, p, k, eps)

    mc_dr = None
    if run_mc:
        print(f"  [D-RIS] Evaluating MC spread ({eval_runs:,} runs)...")
        mc_dr = mc_spread(p, S_dr, eval_runs)

    results['D-RIS'] = dict(
        seeds=S_dr, theta=theta_dr, time=t_dr,
        mc_spread=mc_dr, R=R_dr
    )
    print_metrics('D-RIS', S_dr, R_dr, nodes, comm_to_nodes,
                  node_to_comm, lam, mc_dr)

    # ── Step 2c: RIS (baseline) ───────────────────────────────────────────────
    sep(f"[{name}] RIS  (baseline, Borgs et al. 2014)")
    (S_ris, R_ris), t_ris = timed(ris, nodes, p, k, eps)

    mc_ris = None
    if run_mc:
        print(f"  [RIS] Evaluating MC spread ({eval_runs:,} runs)...")
        mc_ris = mc_spread(p, S_ris, eval_runs)

    results['RIS'] = dict(
        seeds=S_ris, theta=len(R_ris), time=t_ris,
        mc_spread=mc_ris, R=R_ris
    )
    print_metrics('RIS', S_ris, R_ris, nodes, comm_to_nodes,
                  node_to_comm, lam, mc_ris)

    # ── Step 3: Summary comparison table ─────────────────────────────────────
    _print_summary(name, results, nodes, comm_to_nodes, node_to_comm,
                   k, lam, run_mc, eval_runs, stats, modularity)

    # ── Step 4: Per-community MC spread (optional, fast subset) ──────────────
    mc_per_comm = None
    if run_mc:
        sep(f"[{name}] Per-community MC spread (2,000 runs each)...")
        mc_per_comm = {}
        for algo in ['CA-RIS', 'D-RIS', 'RIS']:
            print(f"  Computing per-community spread for {algo}...")
            mc_per_comm[algo] = mc_spread_per_community(
                p, results[algo]['seeds'], node_to_comm, comm_to_nodes,
                num_runs=2000
            )

    # ── Step 5: Save results and plots ───────────────────────────────────────
    sep(f"[{name}] Saving results and generating plots...")
    save_and_plot(
        dataset=name, k=k, lam=lam, eps=eps,
        modularity=modularity,
        community_to_nodes=comm_to_nodes,
        node_to_community=node_to_comm,
        results=results,
        mc_per_comm=mc_per_comm,
    )

    return results


def _print_summary(name, results, nodes, comm_to_nodes, node_to_comm,
                   k, lam, run_mc, eval_runs, stats, modularity):
    """Print the structured comparison table."""
    sep(f"SUMMARY — {name}")

    algos = ['CA-RIS', 'D-RIS', 'RIS']
    m = len(comm_to_nodes)

    # Pre-compute all metrics
    metrics = {}
    for algo in algos:
        r = results[algo]
        S = r['seeds']
        R = r['R']
        cc = community_coverage(S, comm_to_nodes)
        _, norm_h = seed_distribution_entropy(S, comm_to_nodes)
        gini = gini_imbalance(S, comm_to_nodes)
        _, sigma_hat, _ = fairness_objective(
            S, R, nodes, comm_to_nodes, node_to_comm, lam
        )
        metrics[algo] = {
            'cc': cc,
            'entropy': norm_h,
            'gini': gini,
            'sigma_hat': sigma_hat,
            'mc': r['mc_spread'],
            'time': r['time'],
            'theta': r['theta'],
        }

    col_w = 14
    hdr = f"\n  {'Metric':<32}" + "".join(f"{a:>{col_w}}" for a in algos)
    div = "  " + "-" * (32 + col_w * len(algos))
    print(hdr)
    print(div)

    def row(label, key, fmt):
        vals = "".join(f"{fmt.format(metrics[a][key]):>{col_w}}" for a in algos)
        print(f"  {label:<32}{vals}")

    row("σ̂(S) RRR spread estimate", 'sigma_hat', '{:.2f}')
    if run_mc:
        row(f"σ(S) MC spread ({eval_runs//1000}k runs)", 'mc', '{:.2f}')
    row("Community Coverage CC(S)", 'cc', '{:.4f}')
    row("Seed Entropy (normalised)", 'entropy', '{:.4f}')
    row("Gini Imbalance I(S)", 'gini', '{:.4f}')
    row("Runtime (s)", 'time', '{:.2f}')
    row("RRR sets θ used", 'theta', '{:,}')

    print(div)

    # Relative change of CA-RIS vs D-RIS
    print(f"\n  CA-RIS vs D-RIS (relative change):")
    base = metrics['D-RIS']
    ca   = metrics['CA-RIS']
    if base['sigma_hat'] > 0:
        spread_delta = 100 * (ca['sigma_hat'] - base['sigma_hat']) / base['sigma_hat']
        print(f"    σ̂ change          : {spread_delta:+.1f}%")
    if base['cc'] > 0:
        cc_delta = 100 * (ca['cc'] - base['cc']) / base['cc']
        print(f"    CC change         : {cc_delta:+.1f}%")
    if base['entropy'] > 0:
        h_delta = 100 * (ca['entropy'] - base['entropy']) / base['entropy']
        print(f"    Entropy change    : {h_delta:+.1f}%")
    if base['gini'] > 0:
        gini_delta = 100 * (ca['gini'] - base['gini']) / base['gini']
        print(f"    Gini change       : {gini_delta:+.1f}%  (negative = more balanced)")

    print(f"\n  Network info:")
    print(f"    Communities (Louvain) : {m}")
    print(f"    Modularity Q          : {modularity:.4f}")
    print(f"    Largest community     : {stats['largest_frac']*100:.1f}% of nodes")
    print(f"    λ (fairness weight)   : {lam}")
    print(f"    k (seed set size)     : {k}")


# ── λ sweep experiment ────────────────────────────────────────────────────────

def lambda_sweep(name, nodes, p, k, eps=DEFAULT_EPS, run_mc=False,
                 lambdas=None):
    """
    Run CA-RIS for multiple λ values and report the spread–fairness trade-off.

    This directly shows the effect of the λ parameter:
      λ=0  → standard RIS (no fairness)
      λ↑   → more balanced seed distribution, potentially lower raw spread

    Parameters
    ----------
    lambdas : list of λ values to sweep (default [0, 0.25, 0.5, 1.0, 2.0])
    """
    if lambdas is None:
        lambdas = [0.0, 0.25, 0.5, 1.0, 2.0]

    sep(f"λ Sweep — {name}  (k={k})")

    node_to_comm, comm_to_nodes, modularity = \
        detect_communities_louvain_fallback(nodes, p)

    print(f"  Communities: {len(comm_to_nodes)}  |  Q={modularity:.4f}\n")

    sweep_results = []
    for lam in lambdas:
        print(f"\n  ── λ = {lam} ──")
        ca_out, t = timed(ca_ris, nodes, p, k, node_to_comm,
                          comm_to_nodes, lam, eps)
        S, R, theta, quota, relaxed = ca_out
        cc = community_coverage(S, comm_to_nodes)
        _, norm_h = seed_distribution_entropy(S, comm_to_nodes)
        gini = gini_imbalance(S, comm_to_nodes)
        _, sigma_hat, _ = fairness_objective(
            S, R, nodes, comm_to_nodes, node_to_comm, lam
        )
        mc_val = mc_spread(p, S, 5000) if run_mc else None
        sweep_results.append({
            'lam': lam, 'sigma_hat': sigma_hat, 'cc': cc,
            'entropy': norm_h, 'gini': gini, 'time': t, 'mc': mc_val,
        })
        mc_str = f"  MC={mc_val:.2f}" if mc_val else ""
        print(f"    σ̂={sigma_hat:.2f}{mc_str}  CC={cc:.4f}  "
              f"H={norm_h:.4f}  Gini={gini:.4f}  t={t:.2f}s")

    sep(f"λ Sweep Summary — {name}")
    col = 12
    header = (f"  {'λ':<8}{'σ̂(S)':>{col}}{'CC':>{col}}"
              f"{'Entropy':>{col}}{'Gini':>{col}}{'Time(s)':>{col}}")
    print(header)
    print("  " + "-" * (8 + col * 5))
    for r in sweep_results:
        mc_str = f" (MC={r['mc']:.2f})" if r['mc'] else ""
        print(f"  {r['lam']:<8.2f}"
              f"{r['sigma_hat']:>{col}.2f}"
              f"{r['cc']:>{col}.4f}"
              f"{r['entropy']:>{col}.4f}"
              f"{r['gini']:>{col}.4f}"
              f"{r['time']:>{col}.2f}"
              f"{mc_str}")

    # Save sweep CSV and plot
    from results import save_lambda_sweep_csv, plot_lambda_tradeoff, make_run_dir
    run_dir = make_run_dir(name.lower() + "_lambda_sweep")
    save_lambda_sweep_csv(run_dir, sweep_results)
    plot_lambda_tradeoff(run_dir, sweep_results, name, k)
    print(f"\n  λ sweep results saved to: {run_dir}/")

    return sweep_results


# ── Dataset wrappers ──────────────────────────────────────────────────────────

def experiment_slashdot(k=DEFAULT_K, lam=DEFAULT_LAM, eps=DEFAULT_EPS,
                        sub_n=None, run_mc=True, p_uniform=DEFAULT_P,
                        do_lambda_sweep=False):
    nodes, p = load_snap_directed(SLASHDOT_PATH, prob_model='IC',
                                  p_uniform=p_uniform)
    print(f"  Slashdot: {len(nodes):,} nodes, "
          f"{sum(len(p[u]) for u in nodes):,} edges")
    if sub_n:
        nodes, p = sample_subgraph(nodes, p, sub_n, seed=SEED)
        print(f"  Subgraph : {len(nodes):,} nodes, "
              f"{sum(len(p[u]) for u in nodes):,} edges")
    if do_lambda_sweep:
        return lambda_sweep("Slashdot", nodes, p, k, eps, run_mc)
    return run_experiment("Slashdot", nodes, p, k, lam, eps, run_mc)


def experiment_epinions(k=DEFAULT_K, lam=DEFAULT_LAM, eps=DEFAULT_EPS,
                        sub_n=None, run_mc=True, p_uniform=DEFAULT_P,
                        do_lambda_sweep=False):
    nodes, p = load_snap_directed(EPINIONS_PATH, prob_model='IC',
                                  p_uniform=p_uniform)
    print(f"  Epinions: {len(nodes):,} nodes, "
          f"{sum(len(p[u]) for u in nodes):,} edges")
    if sub_n:
        nodes, p = sample_subgraph(nodes, p, sub_n, seed=SEED)
        print(f"  Subgraph : {len(nodes):,} nodes, "
              f"{sum(len(p[u]) for u in nodes):,} edges")
    if do_lambda_sweep:
        return lambda_sweep("Epinions", nodes, p, k, eps, run_mc)
    return run_experiment("Epinions", nodes, p, k, lam, eps, run_mc)


# ── Entry point ───────────────────────────────────────────────────────────────

EXPERIMENTS = {
    "slashdot": experiment_slashdot,
    "epinions": experiment_epinions,
}

if __name__ == "__main__":
    args = sys.argv[1:]

    # Parse flags
    k              = DEFAULT_K
    lam            = DEFAULT_LAM
    eps            = DEFAULT_EPS
    sub_n          = None
    run_mc         = True
    do_lam_sweep   = "--lambda-sweep" in args
    args = [a for a in args if a != "--lambda-sweep"]

    if "--no-mc" in args:
        run_mc = False
        args = [a for a in args if a != "--no-mc"]

    def _pop_flag(flag, cast, default, args):
        if flag in args:
            idx = args.index(flag)
            val = cast(args[idx + 1])
            args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]
            return val, args
        return default, args

    k,     args = _pop_flag("--k",   int,   DEFAULT_K,   args)
    lam,   args = _pop_flag("--lam", float, DEFAULT_LAM, args)
    eps,   args = _pop_flag("--eps", float, DEFAULT_EPS, args)
    sub_n, args = _pop_flag("--sub", int,   None,        args)

    target = args[0] if args else "slashdot"
    random.seed(SEED)

    kwargs = dict(k=k, lam=lam, eps=eps, sub_n=sub_n,
                  run_mc=run_mc, do_lambda_sweep=do_lam_sweep)

    if target == "all":
        for name, fn in EXPERIMENTS.items():
            path = SLASHDOT_PATH if name == "slashdot" else EPINIONS_PATH
            if os.path.exists(path):
                fn(**kwargs)
    elif target in EXPERIMENTS:
        path = SLASHDOT_PATH if target == "slashdot" else EPINIONS_PATH
        if not os.path.exists(path):
            print(f"Dataset not found at: {path}")
            sys.exit(1)
        EXPERIMENTS[target](**kwargs)
    else:
        print(f"Unknown target '{target}'. Choose from: "
              + ", ".join(EXPERIMENTS))
        print("Flags: --k N  --lam F  --eps F  --sub N  --no-mc  --lambda-sweep")
