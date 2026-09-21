"""
Monte Carlo simulation for the Independent Cascade (IC) model.

Used to evaluate the true influence spread σ(S) of seed sets produced by
CA-RIS, D-RIS, and RIS.  Identical in logic to ris/monte_carlo.py — kept
as a separate file so this module is self-contained.
"""

import random


def simulate_once(p, seed_set):
    """
    Run one IC simulation from seed_set.

    At each round, every newly active node u attempts to activate each
    out-neighbour v with probability p[u][v].  The process continues until
    no new activations occur.

    Returns the set of all activated node IDs.
    """
    active = set(seed_set)
    newly_active = set(seed_set)

    while newly_active:
        next_wave = set()
        for u in newly_active:
            for v, prob in p[u].items():
                if v not in active and random.random() <= prob:
                    next_wave.add(v)
        active |= next_wave
        newly_active = next_wave

    return active


def mc_spread(p, seed_set, num_runs=10_000):
    """
    Estimate influence spread σ(seed_set) by Monte Carlo simulation.

    Parameters
    ----------
    p        : forward adjacency dict  p[u][v] = propagation probability
    seed_set : list of seed node IDs
    num_runs : number of IC simulations (default 10,000)

    Returns
    -------
    float — average number of activated nodes across num_runs simulations.
    """
    if not seed_set:
        return 0.0
    total = sum(len(simulate_once(p, seed_set)) for _ in range(num_runs))
    return total / num_runs


def mc_spread_per_community(p, seed_set, node_to_community,
                             community_to_nodes, num_runs=5000):
    """
    Estimate per-community influence spread via Monte Carlo.

    For each simulation run, tracks how many nodes in each community are
    activated.  Returns dict: community_id → average activated count.

    Useful for analysing whether influence actually reaches all communities,
    not just whether a seed was assigned there.
    """
    community_ids = list(community_to_nodes.keys())
    totals = {cid: 0 for cid in community_ids}
    community_node_set = {
        cid: set(nodes) for cid, nodes in community_to_nodes.items()
    }

    for _ in range(num_runs):
        activated = simulate_once(p, seed_set)
        for cid in community_ids:
            totals[cid] += len(activated & community_node_set[cid])

    return {cid: totals[cid] / num_runs for cid in community_ids}
