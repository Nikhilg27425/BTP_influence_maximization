"""
Seed selection algorithms for signed influence maximization.

Implements:
  1. EGA       — Elitist Greedy Algorithm (Algorithm 1, Şimşek 2019)
  2. IC-P Greedy — baseline pure greedy (Algorithm 2, Li et al. 2014)
  3. Out-Degree  — heuristic baseline
  4. Random      — random baseline
"""

import random
import math
from ic_p_model import positive_influence, influence_sets_all_nodes


# ---------------------------------------------------------------------------
# Algorithm 1: EGA — Elitist Greedy Algorithm
# ---------------------------------------------------------------------------

def ega(nodes, w, pol, k, num_runs=20000):
    """
    Elitist Greedy Algorithm (EGA) — Algorithm 1 from Şimşek (2019).

    Steps:
      1. For each node u, compute I_u (set of positively influenced nodes)
         and avg influence |I_u| using IC-P simulation.
      2. Compute mean μ and std σ of all |I_u| values.
      3. Build elite list E = {u : |I_u| >= μ + σ}
      4. Greedily pick k seeds from E:
           - Pick u* = argmax_{u in E} |I_u|
           - Remove u* and all nodes in I_{u*} from E
           - Add u* to seed set S

    Returns seed set S (list of k nodes).
    """
    print(f"  [EGA] Computing influence sets for {len(nodes)} nodes "
          f"({num_runs} runs each)...")

    influenced_sets, avg_inf = influence_sets_all_nodes(nodes, w, pol, num_runs)

    # Compute μ and σ (Equations 3 & 4)
    values = list(avg_inf.values())
    mu    = sum(values) / len(values)
    sigma = math.sqrt(sum((v - mu) ** 2 for v in values) / len(values))
    threshold = mu + sigma

    print(f"  [EGA] μ={mu:.2f}, σ={sigma:.2f}, threshold={threshold:.2f}")

    # Build elite list E (Equation 5)
    E = {u: avg_inf[u] for u in nodes if avg_inf[u] >= threshold}
    print(f"  [EGA] Elite nodes: {len(E)} / {len(nodes)} "
          f"({100*len(E)/len(nodes):.1f}%)")

    # Greedy selection with discount
    S = []
    for _ in range(k):
        if not E:
            break
        # Pick most influential elite
        u_star = max(E, key=lambda u: E[u])
        S.append(u_star)

        # Remove u* and all nodes it influences from E
        to_remove = {u_star} | influenced_sets.get(u_star, set())
        for node in to_remove:
            E.pop(node, None)

    return S


# ---------------------------------------------------------------------------
# Algorithm 2: IC-P Greedy (Li et al., 2014)
# ---------------------------------------------------------------------------

def icp_greedy(nodes, w, pol, k, num_runs=20000):
    """
    IC-P Greedy — Algorithm 2 from Li et al. (2014).
    Pure greedy: at each step pick the node with maximum marginal gain
    in positive influence spread.

    Returns seed set S (list of k nodes).
    """
    S = []
    current_spread = 0.0

    for step in range(k):
        best_node, best_gain = None, -1.0
        for u in nodes:
            if u in S:
                continue
            spread = positive_influence(nodes, w, pol, S + [u], num_runs)
            gain   = spread - current_spread
            if gain > best_gain:
                best_gain, best_node = gain, u

        if best_node is not None:
            S.append(best_node)
            current_spread += best_gain
            print(f"  [IC-P Greedy] step {step+1}/{k}: added node {best_node}, "
                  f"spread={current_spread:.2f}")

    return S


# ---------------------------------------------------------------------------
# Out-Degree Heuristic
# ---------------------------------------------------------------------------

def out_degree_heuristic(nodes, w, k):
    """
    Pick the k nodes with the highest out-degree.
    Returns seed set (list).
    """
    out_deg = {u: len(w[u]) for u in nodes}
    return sorted(out_deg, key=out_deg.get, reverse=True)[:k]


# ---------------------------------------------------------------------------
# Random Baseline
# ---------------------------------------------------------------------------

def random_selection(nodes, k, seed=None):
    """
    Randomly select k seed nodes.
    Returns seed set (list).
    """
    if seed is not None:
        random.seed(seed)
    return random.sample(nodes, k)
