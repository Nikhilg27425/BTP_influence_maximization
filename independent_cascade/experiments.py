"""
Experiments reproducing results from:
  "Influence Maximization in Independent Cascade Networks
   Based on Activation Probability Computation"
  Yang, Brenner, Giua — IEEE Access 2019

Usage:
  python experiments.py [all | table3 | tables4_5 | tables6_7 | tables8_9 | fig7_8]
"""

import time
import random
import sys
import os
from functools import partial

sys.path.insert(0, os.path.dirname(__file__))

from graph import make_grid_graph, make_highschool_graph, make_airport_graph, influence_spread
from monte_carlo import monte_carlo
from path_method import path_method
from steady_state import steady_state_spread, sss_noself, sss_bounded_path
from seed_selection import select_top_k, ranked_replace, greedy, _precompute_scores

# ── Dataset paths ────────────────────────────────────────────────────────────
_DIR = os.path.dirname(__file__)
HIGHSCHOOL_PATH = os.path.join(_DIR, "moreno_highschool", "out.moreno_highschool_highschool")
AIRPORT_PATH    = os.path.join(_DIR, "opsahl-usairport", "out.opsahl-usairport")

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt(v, d=4):
    return "  o.o.t" if v is None else f"{v:.{d}f}"

def timed(fn, *args, **kwargs):
    t0 = time.time()
    result = fn(*args, **kwargs)
    return result, time.time() - t0

def sep(title=""):
    w = 70
    print("\n" + "=" * w)
    if title:
        print(title)
        print("=" * w)

# ── Table 3 ───────────────────────────────────────────────────────────────────

def experiment_table3():
    sep("TABLE 3 — Activation probabilities on the 5-node example (Fig. 2)")

    nodes = [1, 2, 3, 4, 5]
    # Reconstructed from paper equations (see README for derivation)
    p = {1: {2: 0.3}, 2: {4: 0.2}, 3: {1: 0.2, 2: 0.1}, 4: {2: 0.3}, 5: {3: 0.4}}
    seed_set = [5]

    pi_pm  = path_method(nodes, p, seed_set)
    pi_sss = steady_state_spread(nodes, p, seed_set, eps=1e-10)
    pi_sn  = sss_noself(nodes, p, seed_set, eps=1e-10)
    pi_bp  = {b: sss_bounded_path(nodes, p, seed_set, b0=b, eps=1e-10) for b in range(5)}

    hdr = f"{'Method':<30}" + "".join(f"  Node{n}" for n in nodes)
    print(hdr)
    print("-" * len(hdr))

    def row(name, pi):
        return f"{name:<30}" + "".join(f"  {fmt(pi[n])}" for n in nodes)

    print(row("Path Method",          pi_pm))
    print(row("SteadyStateSpread",    pi_sss))
    print(row("SSS-Noself",           pi_sn))
    for b in range(5):
        print(row(f"SSS-Bounded-Path(b0={b})", pi_bp[b]))

    print("\nExpected (paper Table 3):")
    print(f"{'Path Method':<30}  0.0800  0.0616  0.4000  0.0123  1.0000")
    print(f"{'SteadyStateSpread':<30}  0.0800  0.0678  0.4000  0.0132  1.0000")
    print(f"{'SSS-Noself':<30}  0.0800  0.0630  0.4000  0.0126  1.0000")
    print(f"{'SSS-Bounded-Path(b0=0)':<30}  0.0800  0.0400  0.4000  0.0080  1.0000")
    print(f"{'SSS-Bounded-Path(b0=1)':<30}  0.0800  0.0630  0.4000  0.0126  1.0000")

# ── Tables 4 & 5 ─────────────────────────────────────────────────────────────

def experiment_tables4_5():
    sep("TABLE 4 — Sum of activation probabilities on Series-Grid")

    SEED = 42
    m_values  = [2, 3, 4, 5, 6, 7]
    seed_k    = {2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 2}
    OOT_LIMIT = 30  # seconds

    res = {k: {} for k in ["MC", "PM", "SSS", "SN"]}

    for m in m_values:
        random.seed(SEED)
        nodes, p = make_grid_graph(m, seed=SEED + m)
        seed_set = random.sample(nodes, seed_k[m])

        pi, _  = timed(monte_carlo, nodes, p, seed_set, 10000)
        res["MC"][m] = influence_spread(pi)

        if m <= 3:
            pi, t = timed(path_method, nodes, p, seed_set)
            res["PM"][m] = influence_spread(pi) if t < OOT_LIMIT else None
        else:
            res["PM"][m] = None

        pi, _ = timed(steady_state_spread, nodes, p, seed_set)
        res["SSS"][m] = influence_spread(pi)

        pi, _ = timed(sss_noself, nodes, p, seed_set)
        res["SN"][m] = influence_spread(pi)

    hdr = f"{'Method':<22}" + "".join(f"   m={m}" for m in m_values)
    print(hdr); print("-" * len(hdr))
    for key, label in [("MC","Monte Carlo"),("PM","Path Method"),
                       ("SSS","SteadyStateSpread"),("SN","SSS-Noself")]:
        print(f"{label:<22}" + "".join(f"  {fmt(res[key][m])}" for m in m_values))

    sep("TABLE 5 — SSS-Bounded-Path sums on Series-Grid")
    b0_vals = [0, 1, 2, 3, 4, 20, 40, 65, 85, 135]
    bp = {b: {} for b in b0_vals}

    for m in m_values:
        random.seed(SEED)
        nodes, p = make_grid_graph(m, seed=SEED + m)
        seed_set = random.sample(nodes, seed_k[m])
        for b in b0_vals:
            pi, _ = timed(sss_bounded_path, nodes, p, seed_set, b0=b)
            bp[b][m] = influence_spread(pi)

    hdr = f"{'b0':<8}" + "".join(f"   m={m}" for m in m_values)
    print(hdr); print("-" * len(hdr))
    for b in b0_vals:
        print(f"{b:<8}" + "".join(f"  {fmt(bp[b][m])}" for m in m_values))

# ── Tables 6 & 7 ─────────────────────────────────────────────────────────────

def experiment_tables6_7():
    sep("TABLE 6 — Per-node activation probabilities on m=3 grid")

    SEED = 42
    nodes, p = make_grid_graph(3, seed=SEED + 3)
    random.seed(SEED)
    seed_set = random.sample(nodes, 1)
    print(f"Seed node: {seed_set}")

    pi_mc  = monte_carlo(nodes, p, seed_set, 10000)
    pi_pm  = path_method(nodes, p, seed_set)
    pi_sss = steady_state_spread(nodes, p, seed_set)
    pi_sn  = sss_noself(nodes, p, seed_set)

    hdr = f"{'Method':<22}" + "".join(f"  N{n:02d}" for n in nodes)
    print(hdr); print("-" * len(hdr))
    for name, pi in [("Monte Carlo", pi_mc), ("Path Method", pi_pm),
                     ("SteadyStateSpread", pi_sss), ("SSS-Noself", pi_sn)]:
        print(f"{name:<22}" + "".join(f"  {fmt(pi[n])}" for n in nodes))

    sep("TABLE 7 — SSS-Bounded-Path per-node on m=3 grid")
    b0_vals = [0, 1, 2, 3, 4, 20, 40, 65, 85, 135]
    hdr = f"{'b0':<8}" + "".join(f"  N{n:02d}" for n in nodes)
    print(hdr); print("-" * len(hdr))
    for b in b0_vals:
        pi = sss_bounded_path(nodes, p, seed_set, b0=b)
        print(f"{b:<8}" + "".join(f"  {fmt(pi[n])}" for n in nodes))

# ── Tables 8 & 9 ─────────────────────────────────────────────────────────────

def experiment_tables8_9():
    sep("TABLE 8 — Running times (s) on Series-Grid")

    SEED = 42
    m_values = [2, 3, 4, 5, 6, 7]
    seed_k   = {2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 2}
    OOT = 30

    times = {k: {} for k in ["MC", "PM", "SSS", "SN"]}

    for m in m_values:
        random.seed(SEED)
        nodes, p = make_grid_graph(m, seed=SEED + m)
        seed_set = random.sample(nodes, seed_k[m])

        _, t = timed(monte_carlo, nodes, p, seed_set, 10000)
        times["MC"][m] = t

        if m <= 3:
            _, t = timed(path_method, nodes, p, seed_set)
            times["PM"][m] = t if t < OOT else None
        else:
            times["PM"][m] = None

        _, t = timed(steady_state_spread, nodes, p, seed_set)
        times["SSS"][m] = t

        _, t = timed(sss_noself, nodes, p, seed_set)
        times["SN"][m] = t

    hdr = f"{'Method':<22}" + "".join(f"   m={m}" for m in m_values)
    print(hdr); print("-" * len(hdr))
    for key, label in [("MC","Monte Carlo"),("PM","Path Method"),
                       ("SSS","SteadyStateSpread"),("SN","SSS-Noself")]:
        print(f"{label:<22}" + "".join(f"  {fmt(times[key][m])}" for m in m_values))

    sep("TABLE 9 — SSS-Bounded-Path running times on Series-Grid")
    b0_vals = [0, 1, 2, 3, 4, 20, 40, 65, 85, 135]
    bp_t = {b: {} for b in b0_vals}

    for m in m_values:
        random.seed(SEED)
        nodes, p = make_grid_graph(m, seed=SEED + m)
        seed_set = random.sample(nodes, seed_k[m])
        for b in b0_vals:
            _, t = timed(sss_bounded_path, nodes, p, seed_set, b0=b)
            bp_t[b][m] = t

    hdr = f"{'b0':<8}" + "".join(f"   m={m}" for m in m_values)
    print(hdr); print("-" * len(hdr))
    for b in b0_vals:
        print(f"{b:<8}" + "".join(f"  {fmt(bp_t[b][m])}" for m in m_values))

# ── Fig. 7 & 8 — Seed selection on HighSchool network ────────────────────────

def experiment_fig7_8():
    sep("FIG. 7 & 8 — Seed selection on HighSchool network (real data)")

    SEED = 42
    nodes, p = make_highschool_graph(HIGHSCHOOL_PATH, seed=SEED)
    print(f"HighSchool graph: {len(nodes)} nodes, "
          f"{sum(len(v) for v in p.values())} edges")

    K_values = [1, 5, 10, 15, 20, 25]

    fn_sss = partial(steady_state_spread, eps=0.01)
    fn_sn  = partial(sss_noself,          eps=0.01)

    # Pre-compute per-node scores once for each method (avoids N × expensive calls)
    print("\n  Pre-computing per-node scores (SSS)...")
    scores_sss, t = timed(_precompute_scores, nodes, p, fn_sss)
    print(f"    done in {t:.1f}s")

    print("  Pre-computing per-node scores (SSS-Noself)...")
    scores_sn, t = timed(_precompute_scores, nodes, p, fn_sn)
    print(f"    done in {t:.1f}s")

    spreads   = {}
    run_times = {}

    def run(name, algo_fn):
        spreads[name]   = {}
        run_times[name] = {}
        print(f"\n  Running {name}...")
        for K in K_values:
            random.seed(SEED)
            seed_set, t = timed(algo_fn, K)
            pi = monte_carlo(nodes, p, seed_set, num_runs=10000)
            spreads[name][K]   = influence_spread(pi)
            run_times[name][K] = t
            print(f"    K={K:2d}  spread={spreads[name][K]:.2f}  time={t:.3f}s")

    run("Random",         lambda K: random.sample(nodes, K))
    run("SelectTopK-SSS", lambda K: select_top_k(nodes, p, K, fn_sss, scores=scores_sss))
    run("SelectTopK-SN",  lambda K: select_top_k(nodes, p, K, fn_sn,  scores=scores_sn))
    run("Replace-SSS",    lambda K: ranked_replace(nodes, p, K, fn_sss, scores=scores_sss))
    run("Replace-SN",     lambda K: ranked_replace(nodes, p, K, fn_sn,  scores=scores_sn, eval_fn=fn_sss))
    run("Greedy-SSS",     lambda K: greedy(nodes, p, K, fn_sss))
    run("Greedy-SN",      lambda K: greedy(nodes, p, K, fn_sn))

    sep("FIG. 7 — Influence spread by algorithm")
    hdr = f"{'Algorithm':<18}" + "".join(f"  K={K:2d}" for K in K_values)
    print(hdr); print("-" * len(hdr))
    for name in spreads:
        print(f"{name:<18}" + "".join(f"  {spreads[name][K]:6.2f}" for K in K_values))

    sep("FIG. 8 — Running time (s) by algorithm")
    print(hdr); print("-" * len(hdr))
    for name in run_times:
        print(f"{name:<18}" + "".join(f"  {run_times[name][K]:6.3f}" for K in K_values))

# ── Fig. 5 — Activation probability on Airport network ───────────────────────

def experiment_fig5():
    sep("FIG. 5 — Activation probability on US Airports network (top-500)")

    SEED = 42
    nodes, p = make_airport_graph(AIRPORT_PATH, top_n=500)
    print(f"Airport graph: {len(nodes)} nodes, "
          f"{sum(len(v) for v in p.values())} edges")

    K_values = [1, 5, 10, 15, 20, 25, 30]
    fn_sss = partial(steady_state_spread, eps=0.01)
    fn_sn  = partial(sss_noself,          eps=0.01)

    methods = [
        ("Monte Carlo",          lambda s: monte_carlo(nodes, p, s, 10000)),
        ("SteadyStateSpread",    lambda s: fn_sss(nodes, p, s)),
        ("SSS-Noself",           lambda s: fn_sn(nodes, p, s)),
        ("SSS-BP(b0=0)",         lambda s: sss_bounded_path(nodes, p, s, b0=0,  eps=0.01)),
        ("SSS-BP(b0=5)",         lambda s: sss_bounded_path(nodes, p, s, b0=5,  eps=0.01)),
    ]

    results = {name: {} for name, _ in methods}

    for K in K_values:
        random.seed(SEED)
        seed_set = random.sample(nodes, K)
        print(f"\n  K={K} seed_set size={len(seed_set)}")
        for name, fn in methods:
            pi, t = timed(fn, seed_set)
            results[name][K] = influence_spread(pi)
            print(f"    {name:<22}  spread={results[name][K]:.2f}  time={t:.2f}s")

    sep("FIG. 5 — Influence spread summary")
    hdr = f"{'Method':<24}" + "".join(f"  K={K:2d}" for K in K_values)
    print(hdr); print("-" * len(hdr))
    for name, _ in methods:
        print(f"{name:<24}" + "".join(f"  {results[name][K]:7.2f}" for K in K_values))

# ── Main ──────────────────────────────────────────────────────────────────────

EXPERIMENTS = {
    "table3":    experiment_table3,
    "tables4_5": experiment_tables4_5,
    "tables6_7": experiment_tables6_7,
    "tables8_9": experiment_tables8_9,
    "fig7_8":    experiment_fig7_8,
    "fig5":      experiment_fig5,
}

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target == "all":
        for name, fn in EXPERIMENTS.items():
            fn()
    elif target in EXPERIMENTS:
        EXPERIMENTS[target]()
    else:
        print(f"Unknown experiment '{target}'. Choose from: all, " + ", ".join(EXPERIMENTS))
