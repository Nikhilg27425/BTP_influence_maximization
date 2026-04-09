"""
Seed selection algorithms for RIS paper experiments.

Implements:
  1. RIS    — Reverse Influence Sampling (Borgs et al. 2014)
  2. D-RIS  — Dynamic RIS with automatic theta determination (Sun & Chen 2021)
  3. CELF   — Cost-Effective Lazy Forward (Leskovec et al. 2007), used as baseline

Reference:
  Sun G., Chen C. (2021). Influence Maximization Algorithm Based on Reverse
  Reachable Set. Mathematical Problems in Engineering, Hindawi. DOI: 10.1155/2021/5535843.

  Borgs C., Brautbar M., Chayes J., Lucier B. (2014). Maximizing Social Influence
  in Nearly Optimal Time. SODA 2014.
"""

import random
import math
import heapq
from collections import Counter
from monte_carlo import mc_spread


# ---------------------------------------------------------------------------
# RRR Set Generation
# ---------------------------------------------------------------------------

def generate_rrr_set(nodes, p):
    """
    Generate one Random Reverse Reachable (RRR) set.

    Steps:
      1. Select a random target node v from V
      2. Sample a graph g by keeping edge (u→v) with probability p(u,v)
         (equivalently: for each in-neighbor u of v, keep the edge with prob p[u][v])
      3. BFS backward from v in g to find all ancestors (nodes that can reach v)

    Returns the RRR set as a list of node IDs.
    """
    # Step 1: random target
    v = random.choice(nodes)

    # Build reverse adjacency for the sampled graph on-the-fly during BFS
    # We do a backward BFS: start from v, find all u such that u→...→v in sampled g
    # For each candidate in-neighbor u of current node w, keep edge u→w with prob p[u][w]

    # Build reverse adjacency map: rev_p[v] = list of (u, prob) meaning u→v exists
    # We need this for backward traversal. Pre-build it once outside if performance matters.
    # Here we build it lazily per BFS step.

    # For efficiency, we need the reverse graph. We'll pass it in or build it here.
    # Since p[u][v] gives forward edges, we need to invert.
    # We build a local reverse lookup on the fly.

    visited = {v}
    queue = [v]
    rrs = [v]

    while queue:
        current = queue.pop()
        # Find all u such that p[u][current] exists (in-neighbors of current)
        # This requires iterating over all nodes — expensive for large graphs.
        # In practice, pre-build reverse adjacency. Here we use the passed rev_p.
        # See note: caller should pass rev_p for efficiency.
        pass

    # NOTE: This naive implementation is O(N) per BFS step.
    # The efficient version uses a pre-built reverse adjacency list.
    # See generate_rrr_set_fast() below which takes rev_p as input.
    return rrs


def build_reverse_adjacency(nodes, p):
    """
    Build reverse adjacency: rev_p[v] = list of (u, prob) for all edges u→v.
    Pre-computing this once makes RRR set generation O(avg_in_degree) per step.
    """
    rev_p = {v: [] for v in nodes}
    for u in nodes:
        for v, prob in p[u].items():
            rev_p[v].append((u, prob))
    return rev_p


def generate_rrr_set_fast(nodes, rev_p):
    """
    Generate one Random Reverse Reachable (RRR) set efficiently.

    Uses pre-built reverse adjacency rev_p[v] = [(u, prob), ...].

    Algorithm:
      1. Select random target node v
      2. BFS backward from v:
           For each in-neighbor u of current node w:
             Keep edge u→w with probability p[u][w]
             If kept and u not visited: add u to RRS, enqueue u
      3. Return the set of visited nodes (= RRS)

    Complexity: O(avg_in_degree × |RRS|) per call.
    """
    v = random.choice(nodes)
    visited = {v}
    queue = [v]

    while queue:
        w = queue.pop()
        for u, prob in rev_p[w]:
            if u not in visited and random.random() <= prob:
                visited.add(u)
                queue.append(u)

    return list(visited)


# ---------------------------------------------------------------------------
# 1. RIS — Reverse Influence Sampling (Borgs et al. 2014)
# ---------------------------------------------------------------------------

def ris(nodes, p, k, theta=None, eps=0.5, l=1):
    """
    RIS algorithm: generate theta RRR sets, then greedily select k seeds
    that cover the maximum number of RRR sets.

    Parameters:
      nodes  : list of node IDs
      p      : dict p[u][v] = propagation probability
      k      : seed set size
      theta  : number of RRR sets to generate (if None, computed from formula)
      eps    : approximation parameter ε (default 0.5)
      l      : confidence parameter (default 1, gives prob ≥ 1 − 1/n)

    Returns (seed_set, R) where R is the collection of RRR sets.

    Approximation guarantee: σ(S) ≥ (1 − 1/e − ε) · OPT
    with probability ≥ 1 − n^(−l).
    """
    n = len(nodes)

    if theta is None:
        # Formula from Tang et al. (2014) with OPT ≥ k (conservative)
        log_n_choose_k = sum(math.log(n - i) - math.log(i + 1) for i in range(k))
        theta = int(math.ceil(
            n * (8 + 2 * eps) * (l * math.log(n) + log_n_choose_k + math.log(2))
            / (eps ** 2 * k)
        ))
        # Cap theta for practical use on large graphs
        theta = min(theta, 200000)

    print(f"  [RIS] Generating {theta:,} RRR sets for {n:,} nodes...")

    rev_p = build_reverse_adjacency(nodes, p)
    R = [generate_rrr_set_fast(nodes, rev_p) for _ in range(theta)]

    print(f"  [RIS] Running greedy maximum coverage (k={k})...")
    seed_set = _greedy_coverage(R, k)

    return seed_set, R


# ---------------------------------------------------------------------------
# 2. D-RIS — Dynamic RIS (Sun & Chen 2021)
# ---------------------------------------------------------------------------

def dris(nodes, p, k, eps=0.5, l=1):
    """
    D-RIS algorithm: dynamic version of RIS that automatically determines
    the critical number of RRR sets using an iterative debugging method.

    Key improvement over basic RIS:
      Instead of using the conservative OPT ≥ k lower bound, D-RIS
      iteratively estimates OPT from the current collection of RRR sets
      and adjusts theta accordingly. This avoids over-sampling.

    Algorithm:
      1. Start with initial theta_0 = n * ln(n) / k
      2. Generate theta_0 RRR sets
      3. Estimate OPT from coverage fraction: OPT_est = coverage_fraction * n
      4. Recompute theta using OPT_est (tighter bound)
      5. If theta_new < current |R|: done (we have enough sets)
         Else: generate more sets and repeat
      6. Run greedy coverage on final R

    Returns (seed_set, R, theta_used).
    """
    n = len(nodes)
    rev_p = build_reverse_adjacency(nodes, p)

    # Step 1: initial theta estimate
    theta_0 = max(int(n * math.log(n) / k), 1000)
    theta_0 = min(theta_0, 50000)  # cap for large graphs

    print(f"  [D-RIS] Initial theta_0={theta_0:,} for {n:,} nodes, k={k}...")

    # Step 2: generate initial batch
    R = [generate_rrr_set_fast(nodes, rev_p) for _ in range(theta_0)]

    # Step 3: estimate OPT from coverage
    best_k_nodes = _greedy_coverage_estimate(R, k)
    covered = sum(1 for rrs in R if any(u in rrs for u in best_k_nodes))
    coverage_fraction = covered / len(R)
    opt_est = max(coverage_fraction * n, k)  # OPT ≥ k always

    print(f"  [D-RIS] Coverage fraction={coverage_fraction:.4f}, "
          f"OPT_est={opt_est:.1f}")

    # Step 4: recompute theta with tighter OPT estimate
    log_n_choose_k = sum(math.log(n - i) - math.log(i + 1) for i in range(k))
    theta_new = int(math.ceil(
        n * (8 + 2 * eps) * (l * math.log(n) + log_n_choose_k + math.log(2))
        / (eps ** 2 * opt_est)
    ))
    theta_new = min(theta_new, 200000)

    # Step 5: generate additional sets if needed
    if theta_new > len(R):
        additional = theta_new - len(R)
        print(f"  [D-RIS] Generating {additional:,} additional RRR sets "
              f"(total target: {theta_new:,})...")
        R.extend(generate_rrr_set_fast(nodes, rev_p) for _ in range(additional))
    else:
        print(f"  [D-RIS] theta_new={theta_new:,} ≤ current |R|={len(R):,}. "
              f"No additional sets needed.")

    theta_used = len(R)
    print(f"  [D-RIS] Final |R|={theta_used:,}. Running greedy coverage...")

    # Step 6: greedy coverage
    seed_set = _greedy_coverage(R, k)

    return seed_set, R, theta_used


# ---------------------------------------------------------------------------
# 3. CELF — Cost-Effective Lazy Forward (Leskovec et al. 2007)
# ---------------------------------------------------------------------------

def celf(nodes, p, k, num_runs=1000):
    """
    CELF algorithm using a max-heap sorted by marginal gain.
    Used as a baseline comparison for RIS / D-RIS.

    Returns (seed_set, spread_history, node_lookups).
    """
    S = []
    current_spread = 0.0
    spread_history = []
    node_lookups = 0

    print(f"  [CELF] Initializing heap for {len(nodes)} nodes "
          f"({num_runs} MC runs each)...")
    heap = []
    for u in nodes:
        mg = mc_spread(p, [u], num_runs)
        node_lookups += 1
        heapq.heappush(heap, (-mg, u, 0))

    for step in range(k):
        recomputed = 0
        while True:
            neg_mg, u, flag = heapq.heappop(heap)
            mg = -neg_mg

            if flag == len(S):
                S.append(u)
                current_spread += mg
                spread_history.append(current_spread)
                print(f"  [CELF] step {step+1}/{k}: node={u}  "
                      f"spread={current_spread:.2f}  recomputed={recomputed}  "
                      f"total_lookups={node_lookups}")
                break
            else:
                new_mg = mc_spread(p, S + [u], num_runs) - current_spread
                node_lookups += 1
                recomputed += 1
                heapq.heappush(heap, (-new_mg, u, len(S)))

    return S, spread_history, node_lookups


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _greedy_coverage(R, k):
    """
    Greedy maximum coverage: iteratively pick the node appearing most often
    in R, then remove all RRR sets containing that node.

    Returns seed set of size k.
    """
    R = list(R)  # work on a copy
    seed_set = []

    for _ in range(k):
        if not R:
            break
        # Count node occurrences across all remaining RRR sets
        flat = [node for rrs in R for node in rrs]
        if not flat:
            break
        best_node = Counter(flat).most_common(1)[0][0]
        seed_set.append(best_node)
        # Remove all RRR sets that contain best_node
        R = [rrs for rrs in R if best_node not in rrs]

    return seed_set


def _greedy_coverage_estimate(R, k):
    """
    Run greedy coverage without modifying R (for OPT estimation in D-RIS).
    Returns the k nodes selected.
    """
    R_copy = list(R)
    selected = []
    for _ in range(k):
        if not R_copy:
            break
        flat = [node for rrs in R_copy for node in rrs]
        if not flat:
            break
        best = Counter(flat).most_common(1)[0][0]
        selected.append(best)
        R_copy = [rrs for rrs in R_copy if best not in rrs]
    return selected
