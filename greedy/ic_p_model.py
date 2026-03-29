"""
IC-P (Polarity-related Independent Cascade) Model.

Extension of the IC model for signed networks (Li et al., 2014).

Rules (Equation 2 in paper):
  When active node u tries to influence inactive node v:
    - If pol[u][v] == +1 and u in A+:  v joins A+ (positively influenced)
    - If pol[u][v] == -1 and u in A+:  v joins A- (negatively influenced)
    - If pol[u][v] == +1 and u in A-:  v joins A- (negatively influenced)
    - If pol[u][v] == -1 and u in A-:  v joins A+ (positively influenced)
    - Propagation succeeds with probability w[u][v]

Positive influence spread f+(S) = |A+| at end of propagation.
"""

import random


def simulate_icp_once(nodes, w, pol, seed_set):
    """
    Run one IC-P simulation from seed_set (all seeds start as positively active).
    Returns (A_plus, A_minus): sets of positively and negatively influenced nodes.
    """
    seed_set = set(seed_set)
    A_plus  = set(seed_set)   # positively active
    A_minus = set()           # negatively active
    active  = set(seed_set)   # all active (A+ ∪ A-)

    newly_active = list(seed_set)  # (node, sign): seeds are all positive

    # Track sign of each newly active node for propagation
    newly_signed = {n: +1 for n in seed_set}

    while newly_signed:
        next_signed = {}
        for u, u_sign in newly_signed.items():
            for v, prob in w[u].items():
                if v in active:
                    continue
                if random.random() <= prob:
                    # Determine v's sign based on u's sign and edge polarity
                    edge_pol = pol[u].get(v, +1)
                    v_sign = u_sign * edge_pol  # +1 * +1 = +1, +1 * -1 = -1, etc.
                    if v not in next_signed:
                        next_signed[v] = v_sign
                    # If v already queued with different sign, positive wins
                    # (standard IC: first activation counts)

        for v, v_sign in next_signed.items():
            if v not in active:
                active.add(v)
                if v_sign == +1:
                    A_plus.add(v)
                else:
                    A_minus.add(v)

        newly_signed = next_signed

    return A_plus, A_minus


def positive_influence(nodes, w, pol, seed_set, num_runs=20000):
    """
    Estimate positive influence spread f+(S) by Monte Carlo simulation.
    Returns average |A+| over num_runs runs.
    """
    total = 0
    for _ in range(num_runs):
        A_plus, _ = simulate_icp_once(nodes, w, pol, seed_set)
        total += len(A_plus)
    return total / num_runs


def influence_sets_all_nodes(nodes, w, pol, num_runs=20000):
    """
    For each node u, compute its set of positively influenced nodes I_u
    (i.e., run IC-P with seed={u} and record which nodes end up in A+).

    Returns dict: node -> set of positively influenced nodes (by majority vote).
    Paper uses threshold p >= 0.5: if node v is in A+ in >= 50% of runs,
    it's considered influenced by u.

    Also returns avg_influence: node -> average |A+| (float).
    """
    influenced_sets = {}
    avg_influence   = {}

    for u in nodes:
        counts = {v: 0 for v in nodes}
        for _ in range(num_runs):
            A_plus, _ = simulate_icp_once(nodes, w, pol, [u])
            for v in A_plus:
                counts[v] += 1

        # I_u = nodes influenced with probability >= 0.5
        I_u = {v for v, c in counts.items() if c / num_runs >= 0.5}
        influenced_sets[u] = I_u
        avg_influence[u]   = sum(counts.values()) / num_runs

    return influenced_sets, avg_influence
