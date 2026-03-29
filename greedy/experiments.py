"""
Experiments reproducing results from:
  "A New Greedy Algorithm For Influence Maximization On Signed Social Networks"
  Aybike Şimşek — Gazi Mühendislik Bilimleri Dergisi, 2019, 5(3): 250-257
  DOI: 10.30855/gmbd.2019.03.06

Reproduces Fig. 1 (Epinions) and Fig. 2 (Slashdot):
  Positive influence spread vs seed set size k = 1..20
  Algorithms: EGA, IC-P Greedy, Out-Degree, Random

Usage:
  python experiments.py epinions [--sub N]   # full or subgraph of N nodes
  python experiments.py slashdot [--sub N]
  python experiments.py both     [--sub N]

Examples:
  python experiments.py epinions --sub 500   # quick test on 500-node subgraph
  python experiments.py both                 # full datasets (hours)
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(__file__))

from graph import load_snap_signed, sample_subgraph
from ic_p_model import positive_influence, influence_sets_all_nodes
from algorithms import ega, icp_greedy, out_degree_heuristic, random_selection

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIR          = os.path.dirname(__file__)
EPINIONS_PATH = os.path.join(_DIR, "data", "soc-sign-epinions.txt")
SLASHDOT_PATH = os.path.join(_DIR, "data", "soc-sign-Slashdot090221.txt")

K_VALUES  = list(range(1, 21))   # k = 1..20 matching paper Fig. 1 & 2
NUM_RUNS  = 20000                 # MC runs for EGA influence set computation
EVAL_RUNS = 20000                 # MC runs for final spread evaluation
QUICK_RUNS = 1000                 # reduced runs for quick/demo mode
SEED      = 42

# ── Helpers ───────────────────────────────────────────────────────────────────

def sep(title):
    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)

def timed(fn, *args, **kwargs):
    t0 = time.time()
    result = fn(*args, **kwargs)
    return result, time.time() - t0

# ── Core experiment ───────────────────────────────────────────────────────────

def run_experiment(dataset_name, nodes, w, pol, num_runs=20000, eval_runs=20000):
    n_edges = sum(len(w[u]) for u in nodes)
    pos_edges = sum(1 for u in nodes for v in w[u] if pol[u].get(v, 1) == 1)
    neg_edges = n_edges - pos_edges
    print(f"\n  Nodes: {len(nodes):,}  |  Edges: {n_edges:,}  "
          f"|  Pos: {pos_edges:,}  Neg: {neg_edges:,}")

    results   = {}
    run_times = {}

    # ── EGA ──────────────────────────────────────────────────────────────────
    sep(f"[{dataset_name}] EGA")
    seed_set_ega, t_ega = timed(ega, nodes, w, pol, max(K_VALUES), num_runs)
    print(f"  Built in {t_ega:.1f}s  |  Seeds: {seed_set_ega}")
    results["EGA"]   = {}
    run_times["EGA"] = t_ega
    for k in K_VALUES:
        spread = positive_influence(nodes, w, pol, seed_set_ega[:k], eval_runs)
        results["EGA"][k] = spread
        print(f"  k={k:2d}  spread={spread:.2f}")

    # ── IC-P Greedy ───────────────────────────────────────────────────────────
    sep(f"[{dataset_name}] IC-P Greedy")
    seed_set_icp, t_icp = timed(icp_greedy, nodes, w, pol, max(K_VALUES), num_runs)
    print(f"  Built in {t_icp:.1f}s  |  Seeds: {seed_set_icp}")
    results["IC-P Greedy"]   = {}
    run_times["IC-P Greedy"] = t_icp
    for k in K_VALUES:
        spread = positive_influence(nodes, w, pol, seed_set_icp[:k], eval_runs)
        results["IC-P Greedy"][k] = spread
        print(f"  k={k:2d}  spread={spread:.2f}")

    # ── Out-Degree ────────────────────────────────────────────────────────────
    sep(f"[{dataset_name}] Out-Degree Heuristic")
    seed_set_od = out_degree_heuristic(nodes, w, max(K_VALUES))
    results["Out-Degree"]   = {}
    run_times["Out-Degree"] = 0.0
    for k in K_VALUES:
        spread = positive_influence(nodes, w, pol, seed_set_od[:k], eval_runs)
        results["Out-Degree"][k] = spread
        print(f"  k={k:2d}  spread={spread:.2f}")

    # ── Random ────────────────────────────────────────────────────────────────
    sep(f"[{dataset_name}] Random Baseline")
    results["Random"]   = {}
    run_times["Random"] = 0.0
    for k in K_VALUES:
        random.seed(SEED + k)
        seeds  = random_selection(nodes, k)
        spread = positive_influence(nodes, w, pol, seeds, eval_runs)
        results["Random"][k] = spread
        print(f"  k={k:2d}  spread={spread:.2f}")

    # ── Summary ───────────────────────────────────────────────────────────────
    algos = ["EGA", "IC-P Greedy", "Out-Degree", "Random"]
    sep(f"RESULTS — {dataset_name} — Positive Influence Spread")
    hdr = f"{'k':<4}" + "".join(f"  {a:<14}" for a in algos)
    print(hdr)
    print("-" * len(hdr))
    for k in K_VALUES:
        print(f"{k:<4}" + "".join(f"  {results[a][k]:<14.2f}" for a in algos))

    sep(f"RUNNING TIMES — {dataset_name}")
    for a in algos:
        print(f"  {a:<16}: {run_times[a]:.2f}s")
    if run_times["IC-P Greedy"] > 0:
        speedup = run_times["IC-P Greedy"] / run_times["EGA"]
        print(f"\n  Speedup EGA vs IC-P Greedy: {speedup:.1f}x  "
              f"(paper reports ~5x on full datasets)")

    return results, run_times

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    # Parse --sub N and --quick
    sub_n = None
    quick = "--quick" in args
    args  = [a for a in args if a != "--quick"]

    if "--sub" in args:
        idx   = args.index("--sub")
        sub_n = int(args[idx + 1])
        args  = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    target = args[0] if args else "both"

    num_runs  = QUICK_RUNS if quick else NUM_RUNS
    eval_runs = QUICK_RUNS if quick else EVAL_RUNS
    if quick:
        print(f"[QUICK MODE] Using {num_runs} MC runs instead of {NUM_RUNS}")

    datasets = {
        "epinions": (EPINIONS_PATH, "Epinions"),
        "slashdot": (SLASHDOT_PATH, "Slashdot"),
    }

    to_run = list(datasets.items()) if target == "both" else [(target, datasets[target])]

    for key, (path, name) in to_run:
        if not os.path.exists(path):
            print(f"\n[SKIP] {name} not found at: {path}")
            continue

        sep(f"Loading {name}")
        nodes, w, pol = load_snap_signed(path)
        print(f"  Full graph: {len(nodes):,} nodes, "
              f"{sum(len(w[u]) for u in nodes):,} edges")

        if sub_n:
            print(f"  Sampling subgraph of {sub_n} nodes...")
            nodes, w, pol = sample_subgraph(nodes, w, pol, sub_n, seed=SEED)
            print(f"  Subgraph: {len(nodes)} nodes, "
                  f"{sum(len(w[u]) for u in nodes)} edges")

        run_experiment(name, nodes, w, pol, num_runs=num_runs, eval_runs=eval_runs)
