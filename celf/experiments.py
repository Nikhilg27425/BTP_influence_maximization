"""
Experiments for CELF (Cost-Effective Lazy Forward) algorithm.

Based on:
  Leskovec J., Krause A., Guestrin C., Faloutsos C., VanBriesen J., Glance N. (2007).
  Cost-effective outbreak detection in networks. KDD 2007.

  Goyal A., Lu W., Lakshmanan L.V.S. (2011).
  CELF++: Optimizing the Greedy Algorithm for Influence Maximization. WWW 2011.

Compares:
  - Naive Greedy  (Kempe et al. 2003) — O(k·N·MC), correctness baseline
  - CELF          (Leskovec et al. 2007) — lazy-forward, dramatically fewer MC calls

Datasets: NetHEPT (ca-HepTh) and NetPHY (ca-HepPh) from SNAP arXiv collaboration networks.
Probability models:
  WC — Weighted Cascade: p(u,v) = 1/in_degree(v)
  IC — Uniform IC: p(u,v) = 0.1

Usage:
  python experiments.py hept_wc [--k 20] [--runs 1000]
  python experiments.py hept_ic [--k 20] [--runs 1000]
  python experiments.py phy_wc  [--k 20] [--runs 1000]
  python experiments.py phy_ic  [--k 20] [--runs 1000]
  python experiments.py all     [--k 20] [--runs 1000]
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(__file__))

from graph import load_collaboration_network
from monte_carlo import mc_spread
from algorithms import greedy, celf

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIR      = os.path.dirname(__file__)
HEPT_PATH = os.path.join(_DIR, "data", "NetHEPT.txt")
PHY_PATH  = os.path.join(_DIR, "data", "NetPHY.txt")

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_K        = 20      # paper uses 100; 20 is practical for quick runs
DEFAULT_NUM_RUNS = 1000    # paper uses 10,000; 1000 gives good approximation
SEED             = 42

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

def run_experiment(name, nodes, p, k=DEFAULT_K, num_runs=DEFAULT_NUM_RUNS,
                   run_greedy=False):
    """
    Run CELF (and optionally naive Greedy) on a graph.
    Prints per-step progress and a final summary table.
    """
    n_edges = sum(len(p[u]) for u in nodes)
    sep(f"Experiment: {name}")
    print(f"  Nodes: {len(nodes):,}  |  Edges: {n_edges:,}  "
          f"|  k={k}  |  MC runs={num_runs:,}")

    results = {}

    # ── Naive Greedy (optional) ───────────────────────────────────────────────
    if run_greedy:
        sep(f"[{name}] Naive Greedy")
        (S_g, hist_g, lookups_g), t_g = timed(greedy, nodes, p, k, num_runs)
        results['Greedy'] = dict(seeds=S_g, spread=hist_g[-1],
                                 time=t_g, lookups=lookups_g,
                                 history=hist_g)
        print(f"\n  Greedy done: spread={hist_g[-1]:.2f}  "
              f"time={t_g:.1f}s  lookups={lookups_g:,}")

    # ── CELF ──────────────────────────────────────────────────────────────────
    sep(f"[{name}] CELF")
    (S_celf, hist_celf, lookups_celf), t_celf = timed(celf, nodes, p, k, num_runs)
    results['CELF'] = dict(seeds=S_celf, spread=hist_celf[-1],
                           time=t_celf, lookups=lookups_celf,
                           history=hist_celf)
    print(f"\n  CELF done: spread={hist_celf[-1]:.2f}  "
          f"time={t_celf:.1f}s  lookups={lookups_celf:,}")

    # ── Summary ───────────────────────────────────────────────────────────────
    sep(f"SUMMARY — {name}")

    # Spread curve
    print(f"\n  Spread vs k:")
    hdr = f"  {'k':<5}" + (f"  {'Greedy':>12}" if run_greedy else "") + f"  {'CELF':>12}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for i, cs in enumerate(hist_celf):
        row = f"  {i+1:<5}"
        if run_greedy and i < len(results['Greedy']['history']):
            row += f"  {results['Greedy']['history'][i]:>12.2f}"
        row += f"  {cs:>12.2f}"
        print(row)

    # Efficiency table
    print(f"\n  Efficiency comparison:")
    hdr2 = f"  {'Metric':<30}" + (f"  {'Greedy':>12}" if run_greedy else "") + f"  {'CELF':>12}"
    print(hdr2)
    print("  " + "-" * (len(hdr2) - 2))

    if run_greedy:
        g = results['Greedy']
        print(f"  {'Running time (s)':<30}  {g['time']:>12.2f}  {t_celf:>12.2f}")
        print(f"  {'Speedup vs Greedy':<30}  {'1.00x':>12}  {g['time']/t_celf:>11.2f}x")
        print(f"  {'Total MC evaluations':<30}  {g['lookups']:>12,}  {lookups_celf:>12,}")
        print(f"  {'Avg evaluations/step':<30}  {g['lookups']/k:>12.1f}  {lookups_celf/k:>12.1f}")
        print(f"  {'Evaluation reduction':<30}  {'baseline':>12}  "
              f"{(1 - lookups_celf/g['lookups'])*100:>10.1f}%")
        print(f"  {'Final spread':<30}  {g['spread']:>12.2f}  {hist_celf[-1]:>12.2f}")
    else:
        print(f"  {'Running time (s)':<30}  {t_celf:>12.2f}")
        print(f"  {'Total MC evaluations':<30}  {lookups_celf:>12,}")
        print(f"  {'Avg evaluations/step':<30}  {lookups_celf/k:>12.1f}")
        print(f"  {'Final spread':<30}  {hist_celf[-1]:>12.2f}")

    print(f"\n  Paper reports (k=100, 10k runs):")
    print(f"    HeptWC: CELF 245 min, avg 18.7 lookups/step")
    print(f"    HeptIC: CELF 5269 min, avg 190.5 lookups/step")
    print(f"    PhyWC:  CELF 1241.6 min, avg 18.6 lookups/step")

    return results

# ── Dataset-specific wrappers ─────────────────────────────────────────────────

def experiment_hept_wc(k=DEFAULT_K, num_runs=DEFAULT_NUM_RUNS, run_greedy=False):
    nodes, p = load_collaboration_network(HEPT_PATH, 'WC')
    return run_experiment("NetHEPT-WC", nodes, p, k, num_runs, run_greedy)

def experiment_hept_ic(k=DEFAULT_K, num_runs=DEFAULT_NUM_RUNS, run_greedy=False):
    nodes, p = load_collaboration_network(HEPT_PATH, 'IC')
    return run_experiment("NetHEPT-IC", nodes, p, k, num_runs, run_greedy)

def experiment_phy_wc(k=DEFAULT_K, num_runs=DEFAULT_NUM_RUNS, run_greedy=False):
    nodes, p = load_collaboration_network(PHY_PATH, 'WC')
    return run_experiment("NetPHY-WC", nodes, p, k, num_runs, run_greedy)

def experiment_phy_ic(k=DEFAULT_K, num_runs=DEFAULT_NUM_RUNS, run_greedy=False):
    nodes, p = load_collaboration_network(PHY_PATH, 'IC')
    return run_experiment("NetPHY-IC", nodes, p, k, num_runs, run_greedy)

# ── Entry point ───────────────────────────────────────────────────────────────

EXPERIMENTS = {
    "hept_wc": experiment_hept_wc,
    "hept_ic": experiment_hept_ic,
    "phy_wc":  experiment_phy_wc,
    "phy_ic":  experiment_phy_ic,
}

if __name__ == "__main__":
    args = sys.argv[1:]

    # Parse flags
    k = DEFAULT_K
    num_runs = DEFAULT_NUM_RUNS
    run_greedy = "--greedy" in args
    args = [a for a in args if a != "--greedy"]

    if "--k" in args:
        idx = args.index("--k")
        k = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    if "--runs" in args:
        idx = args.index("--runs")
        num_runs = int(args[idx + 1])
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    target = args[0] if args else "hept_wc"
    random.seed(SEED)

    if target == "all":
        for name, fn in EXPERIMENTS.items():
            if os.path.exists(HEPT_PATH if "hept" in name else PHY_PATH):
                fn(k=k, num_runs=num_runs, run_greedy=run_greedy)
    elif target in EXPERIMENTS:
        EXPERIMENTS[target](k=k, num_runs=num_runs, run_greedy=run_greedy)
    else:
        print(f"Unknown: '{target}'. Choose from: " + ", ".join(EXPERIMENTS))
        print("Flags: --k N  --runs N  --greedy")
