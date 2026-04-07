"""
Monte Carlo simulation for the Independent Cascade model.
Used to estimate influence spread sigma(S) for CELF and CELF++ experiments.
"""

import random
from collections import defaultdict


def simulate_once(nodes, p, seed_set):
    """Run one IC simulation. Returns set of activated nodes."""
    active = set(seed_set)
    newly_active = set(seed_set)
    while newly_active:
        next_active = set()
        for u in newly_active:
            for v, prob in p[u].items():
                if v not in active and random.random() <= prob:
                    next_active.add(v)
        active |= next_active
        newly_active = next_active
    return active


def mc_spread(nodes, p, seed_set, num_runs=10000):
    """
    Estimate influence spread sigma(seed_set) by Monte Carlo.
    Returns average number of activated nodes over num_runs runs.
    """
    total = 0
    for _ in range(num_runs):
        total += len(simulate_once(nodes, p, seed_set))
    return total / num_runs
