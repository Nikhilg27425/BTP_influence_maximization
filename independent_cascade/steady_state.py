"""
Fixed-point activation probability algorithms:
  1. SteadyStateSpread   (Algorithm from Aggarwal et al., discussed in paper Section 3.2)
  2. SSS-Noself          (Algorithm 2)
  3. SSS-Bounded-Path    (Algorithm 3)
"""

import math
from graph import in_neighbors  # noqa: F401 (kept for potential use)


# ---------------------------------------------------------------------------
# 1. SteadyStateSpread
# ---------------------------------------------------------------------------

def steady_state_spread(nodes, p, seed_set, eps=1e-8):
    """
    Equation 1 fixed-point iteration.
    pi_j^s = 1 - prod_{i in N_j^in} (1 - pi_i^s * p_{i,j})  for j not in seed
    Returns dict: node -> pi_j^s
    """
    seed_set = set(seed_set)
    pi = {node: (1.0 if node in seed_set else 0.0) for node in nodes}

    while True:
        pi_new = {}
        for j in nodes:
            if j in seed_set:
                pi_new[j] = 1.0
            else:
                prod = 1.0
                for i, nbrs in p.items():
                    if j in nbrs:
                        prod *= (1.0 - pi[i] * nbrs[j])
                pi_new[j] = 1.0 - prod

        delta = sum(abs(pi_new[j] - pi[j]) for j in nodes if j not in seed_set)
        pi = pi_new
        if delta < eps:
            break

    return pi


# ---------------------------------------------------------------------------
# 2. SSS-Noself (Algorithm 2)
# ---------------------------------------------------------------------------

def sss_noself(nodes, p, seed_set, eps=1e-8):
    """
    Algorithm 2: SSS-Noself.
    For each non-seed node q, maintain a shadow network G[q] where q's
    influence is removed. The activation probability of j is computed
    using pi_i^[j] (i.e., i's probability in the network without j's influence).

    Returns dict: node -> pi_j^n
    """
    seed_set = set(seed_set)
    non_seed = [n for n in nodes if n not in seed_set]

    # pi[q][j] = activation probability of j in network G[q]
    # Initialize
    pi_q = {}
    for q in non_seed:
        pi_q[q] = {node: (1.0 if node in seed_set else 0.0) for node in nodes}

    # pi[j] = activation probability of j (used for the main network)
    pi = {node: (1.0 if node in seed_set else 0.0) for node in nodes}

    while True:
        pi_q_new = {q: {} for q in non_seed}
        pi_new = {}

        for j in nodes:
            if j in seed_set:
                pi_new[j] = 1.0
                for q in non_seed:
                    pi_q_new[q][j] = 1.0
            else:
                # Update pi[j] using pi_i^[j] from previous iteration
                prod = 1.0
                for i, nbrs in p.items():
                    if j in nbrs:
                        # use pi^[j][i]: i's prob in network without j
                        if j in non_seed:
                            prod *= (1.0 - pi_q[j].get(i, 0.0) * nbrs[j])
                        else:
                            prod *= (1.0 - pi[i] * nbrs[j])
                pi_new[j] = 1.0 - prod

                # Update pi^[q][j] for each q != j
                for q in non_seed:
                    if q == j:
                        # p^[q]_{i,j} = 0 when i==q or j==q, so pi^[q][q] stays 0
                        pi_q_new[q][j] = 0.0
                    else:
                        prod_q = 1.0
                        for i, nbrs in p.items():
                            if j in nbrs and i != q:  # remove q's outgoing edges
                                prod_q *= (1.0 - pi_q[q].get(i, 0.0) * nbrs[j])
                        pi_q_new[q][j] = 1.0 - prod_q

        # Check convergence
        delta1 = sum(abs(pi_new[j] - pi[j]) for j in non_seed)
        delta2 = max(
            (sum(abs(pi_q_new[q].get(j, 0) - pi_q[q].get(j, 0)) for j in non_seed)
             for q in non_seed),
            default=0.0
        )
        delta = max(delta1, delta2)

        pi = pi_new
        pi_q = pi_q_new

        if delta < eps:
            break

    return pi


# ---------------------------------------------------------------------------
# 3. SSS-Bounded-Path (Algorithm 3)
# ---------------------------------------------------------------------------

def sss_bounded_path(nodes, p, seed_set, b0=0, eps=1e-8):
    """
    Algorithm 3: SSS-Bounded-Path.
    Computes activation probabilities along paths of length <= sp_j + b0.
    b0=0 gives SPM (lower bound), b0->inf converges to SteadyStateSpread.

    sp_j = first step s at which pi_j^bp becomes non-zero.
    Node j is only updated at steps s where s <= sp_j + b0.
    Once sp_j is known, b_j = sp_j + b0 is the last allowed step.

    Returns dict: node -> pi_j^bp(b0)
    """
    seed_set = set(seed_set)
    non_seed = [n for n in nodes if n not in seed_set]

    pi = {node: (1.0 if node in seed_set else 0.0) for node in nodes}
    sp = {node: math.inf for node in non_seed}   # shortest path step
    b_limit = {node: math.inf for node in non_seed}  # last allowed update step

    s = 0
    while True:
        pi_new = {node: pi[node] for node in nodes}
        any_active = False

        for j in non_seed:
            # Only update if we haven't exceeded the bound
            if s <= b_limit[j]:
                prod = 1.0
                for i, nbrs in p.items():
                    if j in nbrs:
                        prod *= (1.0 - nbrs[j] * pi[i])
                new_val = 1.0 - prod

                # Detect first activation: set sp_j and bound
                if new_val > 0.0 and pi[j] == 0.0:
                    sp[j] = s      # sp_j = current step (0-indexed)
                    b_limit[j] = s + b0  # last step = sp_j + b0

                pi_new[j] = new_val
                any_active = True

        if not any_active:
            break

        delta = sum(abs(pi_new[j] - pi[j]) for j in non_seed)
        pi = pi_new
        s += 1

        if delta < eps:
            break

    return pi
