"""
Monte Carlo simulation for the Independent Cascade model.
Average over `num_runs` simulations to estimate activation probabilities.
"""

import random
from collections import defaultdict


def simulate_once(nodes, p, seed_set):
    """
    Run one IC simulation. Returns set of activated nodes.
    """
    active = set(seed_set)
    newly_active = set(seed_set)

    while newly_active:
        next_active = set()
        for u in newly_active:
            for v, prob in p[u].items():
                if v not in active:
                    if random.random() <= prob:
                        next_active.add(v)
        active |= next_active
        newly_active = next_active

    return active


def monte_carlo(nodes, p, seed_set, num_runs=10000):
    """
    Estimate activation probabilities by averaging over `num_runs` simulations.
    Returns dict: node -> estimated activation probability.
    """
    counts = defaultdict(int)

    for _ in range(num_runs):
        activated = simulate_once(nodes, p, seed_set)
        for v in activated:
            counts[v] += 1

    return {node: counts[node] / num_runs for node in nodes}
