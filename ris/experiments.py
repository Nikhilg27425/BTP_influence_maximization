"""
Experiments for D-RIS (Dynamic Reverse Influence Sampling) algorithm.

Based on:
  Sun G., Chen C. (2021). Influence Maximization Algorithm Based on Reverse
  Reachable Set. Mathematical Problems in Engineering, Hindawi.
  DOI: 10.1155/2021/5535843.

Compares:
  - D-RIS  (Sun & Chen 2021) — dynamic RIS with automatic theta determination
  - RIS    (Borgs et al. 2014) — basic reverse influence sampling
  - CELF   (Leskovec et al. 2007) — lazy-forward greedy (baseline)

Datasets: Slashdot0902 and soc-Epinions1 from SNAP.
Probability model: Uniform IC with p=0.01 (default for large networks).

Usage:
  python experiments.py slashdot [--k 50] [--eps 0.5] [--sub N] [--compare]
  python experiments.py epinions [--k 50] [--eps 0.5] [--sub N] [--compare]
  python experiments.py all      [--k 50] [--eps 0.5] [--sub N]
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(__file__))

from graph import load_snap_directed, sample_subgraph
from monte_carlo import mc_spread
from algorithms import ris, dris, celf

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIR          = os.path.dirname(__file__)
SLASHDOT_PATH = os.path.join(_DIR, "data", "Slashdot0902.txt")
EPINIONS_PATH = os.path.join(_DIR, "data", "soc-Epinions1.txt")

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_K    = 50      # paper uses k=1..50
DEFAULT_EPS  = 0.5     # approximation parameter ε
DEFAULT_P    = 0.01    # uniform IC propagation probability
EVAL_RUNS    = 10000   # MC runs for spread evaluation
SEED         = 42

# ── Helpers ───────────────────────────────────────────────────────────────────

def sep(title=""):
    w = 70
    print("\n" + "=" * w)
    if title:
        print(title)
        print("=" * w)

def timed(fn, *args, **kwargs):
    t0 = time.time()
    result = fn(*args, **kwargs)
    return result, time.time() - t0

# ── Core experiment ───────────────────────────────────────────────────────────

def run_experiment(name, nodes, p, k=DEFAULT_K, eps=DEFAULT_EPS,
                   run_celf=False, eval_runs=EVAL_RUNS):
    """
    Run D-RIS (and optionally RIS and CELF) on a graph.
    Prints per-step progress and a final summary table.
    """
    n_edges = sum(len(p[u]) for u in nodes)
    sep(f"Experiment: {name}")
    print(f"  Nodes: {len(nodes):,}  |  Edges: {n_edges:,}  "
          f"|  k={k}  |  ε={eps}")

    results = {}

    # ── D-RIS ─────────────────────────────────────────────────────────────────
    sep(f"[{name}] D-RIS")
    (S_dris, R_dris, theta_dris), t_dris = timed(dris, nodes, p, k, eps)
    spread_dris = mc_spread(p, S_dris, eval_runs)
    results['D-RIS'] = dict(seeds=S_dris, spread=spread_dris,
                            time=t_dris, theta=theta_dris)
    print(f"\n  D-RIS done: spread={spread_dris:.2f}  "
          f"time={t_dris:.1f}s  theta={theta_dris:,}")

    # ── RIS ───────────────────────────────────────────────────────────────────
    sep(f"[{name}] RIS")
    (S_ris, R_ris), t_ris = timed(ris, nodes, p, k, eps=eps)
    spread_ris = mc_spread(p, S_ris, eval_runs)
    theta_ris = len(R_ris)
    results['RIS'] = dict(seeds=S_ris, spread=spread_ris,
                          time=t_ris, theta=theta_ris)
    print(f"\n  RIS done: spread={spread_ris:.2f}  "
          f"time={t_ris:.1f}s  theta={theta_ris:,}")

    # ── CELF (optional) ───────────────────────────────────────────────────────
    if run_celf:
        sep(f"[{name}] CELF")
        (S_celf, hist_celf, lookups_celf), t_celf = timed(
            celf, nodes, p, k, num_runs=1000
        )
        results['CELF'] = dict(seeds=S_celf, spread=hist_celf[-1],
                               time=t_celf, lookups=lookups_celf)
        print(f"\n  CELF done: spread={hist_celf[-1]:.2f}  "
              f"time={t_celf:.1f}s  lookups={lookups_celf:,}")

    # ── Summary ───────────────────────────────────────────────────────────────
    sep(f"SUMMARY — {name}")

    algos = ['D-RIS', 'RIS'] + (['CELF'] if run_celf else [])

    print(f"\n  Influence Spread (evaluated with {eval_runs:,} MC runs):")
    hdr = f"  {'Metric':<30}" + "".join(f"  {a:>12}" for a in algos)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    print(f"  {'Final spread (k=' + str(k) + ')':<30}" +
          "".join(f"  {results[a]['spread']:>12.2f}" for a in algos))
    print(f"  {'Running time (s)':<30}" +
          "".join(f"  {results[a]['time']:>12.2f}" for a in algos))

    if 'CELF' in results and results['CELF']['time'] > 0:
        print(f"  {'Speedup vs CELF':<30}" +
              "".join(f"  {results['CELF']['time']/results[a]['time']:>11.1f}x"
                      for a in algos))

    print(f"\n  RRR sets generated:")
    for a in ['D-RIS', 'RIS']:
        print(f"    {a}: {results[a]['theta']:,}")

    print(f"\n  Seed sets selected:")
    for a in algos:
        print(f"    {a}: {results[a]['seeds'][:10]}{'...' if k > 10 else ''}")

    print(f"\n  Paper reports (Slashdot/Epinions, k=1..50):")
    print(f"    D-RIS spread ≈ CELF spread (within a few percent)")
    print(f"    D-RIS time significantly better than CELF and RIS")

    return results

# ── Dataset-specific wrappers ─────────────────────────────────────────────────

def experiment_slashdot(k=DEFAULT_K, eps=DEFAULT_EPS, sub_n=None,
                        run_celf=False, p_uniform=DEFAULT_P):
    nodes, p = load_snap_directed(SLASHDOT_PATH, prob_model='IC',
                                  p_uniform=p_uniform)
    print(f"  Full graph: {len(nodes):,} nodes, "
          f"{sum(len(p[u]) for u in nodes):,} edges")
    if sub_n:
        print(f"  Sampling subgraph of {sub_n:,} nodes...")
        nodes, p = sample_subgraph(nodes, p, sub_n, seed=SEED)
        print(f"  Subgraph: {len(nodes):,} nodes, "
              f"{sum(len(p[u]) for u in nodes):,} edges")
    return run_experiment("Slashdot", nodes, p, k, eps, run_celf)


def experiment_epinions(k=DEFAULT_K, eps=DEFAULT_EPS, sub_n=None,
                        run_celf=False, p_uniform=DEFAULT_P):
    nodes, p = load_snap_directed(EPINIONS_PATH, prob_model='IC',
                                  p_uniform=p_uniform)
    print(f"  Full graph: {len(nodes):,} nodes, "
          f"{sum(len(p[u]) for u in nodes):,} edges")
    if sub_n:
        print(f"  Sampling subgraph of {sub_n:,} nodes...")
        nodes, p = sample_subgraph(nodes, p, sub_n, seed=SEED)
        print(f"  Subgraph: {len(nodes):,} nodes, "
              f"{sum(len(p[u]) for u in nodes):,} edges")
    return run_experiment("Epinions", nodes, p, k, eps, run_celf)

# ── Entry point ───────────────────────────────────────────────────────────────

EXPERIMENTS = {
    "slashdot": experiment_slashdot,
    "epinions": experiment_epinions,
}

if __name__ == "__main__":
    args = sys.argv[1:]

    # Parse flags
    k        = DEFAULT_K
    eps      = DEFAULT_EPS
    sub_n    = None
    run_celf = "--compare" in args or "--celf" in args
    args     = [a for a in args if a not in ("--compare", "--celf")]

    if "--k" in args:
        idx = args.index("--k")
        k = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    if "--eps" in args:
        idx = args.index("--eps")
        eps = float(args[idx + 1])
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    if "--sub" in args:
        idx = args.index("--sub")
        sub_n = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    target = args[0] if args else "slashdot"
    random.seed(SEED)

    if target == "all":
        for name, fn in EXPERIMENTS.items():
            path = SLASHDOT_PATH if name == "slashdot" else EPINIONS_PATH
            if os.path.exists(path):
                fn(k=k, eps=eps, sub_n=sub_n, run_celf=run_celf)
    elif target in EXPERIMENTS:
        path = SLASHDOT_PATH if target == "slashdot" else EPINIONS_PATH
        if not os.path.exists(path):
            print(f"Dataset not found at: {path}")
            sys.exit(1)
        EXPERIMENTS[target](k=k, eps=eps, sub_n=sub_n, run_celf=run_celf)
    else:
        print(f"Unknown: '{target}'. Choose from: " + ", ".join(EXPERIMENTS))
        print("Flags: --k N  --eps F  --sub N  --compare")
