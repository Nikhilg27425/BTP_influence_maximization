"""
Seed selection algorithms for CELF paper experiments.

Implements:
  1. Greedy  — naive greedy (Kempe et al. 2003), O(k·N·MC)
  2. CELF    — Cost-Effective Lazy Forward (Leskovec et al. 2007)

Reference:
  Leskovec J., Krause A., Guestrin C., Faloutsos C., VanBriesen J., Glance N. (2007).
  Cost-effective outbreak detection in networks. KDD 2007.

  Goyal A., Lu W., Lakshmanan L.V.S. (2011).
  CELF++: Optimizing the Greedy Algorithm for Influence Maximization. WWW 2011.
"""

import heapq
from monte_carlo import mc_spread


# ---------------------------------------------------------------------------
# 1. Naive Greedy (Kempe et al. 2003)
# ---------------------------------------------------------------------------

def greedy(nodes, p, k, num_runs=10000):
    """
    Naive greedy: at each step pick the node with maximum marginal gain.
    O(k × N × num_runs) — used as correctness baseline for small k.

    Returns (seed_set, spread_history, node_lookups)
    """
    S = []
    current_spread = 0.0
    spread_history = []
    node_lookups = 0

    for step in range(k):
        best_node, best_gain = None, -1.0
        for u in nodes:
            if u in S:
                continue
            spread = mc_spread(nodes, p, S + [u], num_runs)
            node_lookups += 1
            gain = spread - current_spread
            if gain > best_gain:
                best_gain, best_node = gain, u

        S.append(best_node)
        current_spread += best_gain
        spread_history.append(current_spread)
        print(f"  [Greedy] step {step+1}/{k}: node={best_node}  "
              f"spread={current_spread:.2f}  lookups_so_far={node_lookups}")

    return S, spread_history, node_lookups


# ---------------------------------------------------------------------------
# 2. CELF — Cost-Effective Lazy Forward (Leskovec et al. 2007)
# ---------------------------------------------------------------------------

def celf(nodes, p, k, num_runs=10000):
    """
    CELF algorithm using a max-heap sorted by marginal gain.

    Key idea — submodularity property:
      The marginal gain of a node can only DECREASE as the seed set grows.
      So if a node's gain was computed in a previous iteration, it is still
      an UPPER BOUND on its current gain. We only recompute when a node
      reaches the top of the heap.

    Heap entries: (-mg, node, flag)
      mg   = marginal gain Δu(S) w.r.t. current seed set S
      flag = |S| when mg was last computed

    Algorithm:
      1. Initialize heap: compute sigma({u}) for all nodes
      2. For each seed to pick:
           a. Pop top node u from heap
           b. If u.flag == |S|: mg is current → pick u as seed
           c. Else: recompute mg w.r.t. current S, reinsert, repeat

    Returns (seed_set, spread_history, node_lookups)
    """
    S = []
    current_spread = 0.0
    spread_history = []
    node_lookups = 0

    # ── Step 1: Initialize heap ───────────────────────────────────────────────
    print(f"  [CELF] Initializing heap for {len(nodes)} nodes "
          f"({num_runs} MC runs each)...")
    heap = []
    for u in nodes:
        mg = mc_spread(nodes, p, [u], num_runs)
        node_lookups += 1
        heapq.heappush(heap, (-mg, u, 0))   # flag=0 → computed when |S|=0

    # ── Step 2: Greedy selection with lazy evaluation ─────────────────────────
    for step in range(k):
        recomputed = 0
        while True:
            neg_mg, u, flag = heapq.heappop(heap)
            mg = -neg_mg

            if flag == len(S):
                # mg is up-to-date w.r.t. current S → pick u
                S.append(u)
                current_spread += mg
                spread_history.append(current_spread)
                print(f"  [CELF] step {step+1}/{k}: node={u}  "
                      f"spread={current_spread:.2f}  recomputed={recomputed}  "
                      f"total_lookups={node_lookups}")
                break
            else:
                # Recompute marginal gain w.r.t. current S
                new_mg = mc_spread(nodes, p, S + [u], num_runs) - current_spread
                node_lookups += 1
                recomputed += 1
                heapq.heappush(heap, (-new_mg, u, len(S)))

    return S, spread_history, node_lookups
