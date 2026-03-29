"""
Graph utilities for the Independent Cascade model.
G_IC = (V, E, p) where p[i][j] is the propagation probability of edge (i->j).
"""

import random
from collections import defaultdict


def make_grid_graph(m, seed=None):
    """
    Create a bidirectional grid graph with m^2 nodes (Series-Grid dataset).
    Nodes labeled 1..m^2. Edge probabilities drawn uniformly from {0.1, 0.2, 0.5}.
    """
    if seed is not None:
        random.seed(seed)

    nodes = list(range(1, m * m + 1))
    p = {i: {} for i in nodes}

    def idx(r, c):
        return r * m + c + 1

    for r in range(m):
        for c in range(m):
            u = idx(r, c)
            if c + 1 < m:
                v = idx(r, c + 1)
                p[u][v] = random.choice([0.1, 0.2, 0.5])
                p[v][u] = random.choice([0.1, 0.2, 0.5])
            if r + 1 < m:
                v = idx(r + 1, c)
                p[u][v] = random.choice([0.1, 0.2, 0.5])
                p[v][u] = random.choice([0.1, 0.2, 0.5])

    return nodes, p


def make_airport_graph(filepath, top_n=500):
    """
    Load the US airports network (opsahl-usairport).
    Filters to the top_n airports by total traffic volume (matching the paper).
    Edge probability: p[i][j] = w[i][j] / sum_k w[i][k]

    File format (KONECT):
      Lines starting with % are comments.
      Each data line: src dst weight
    """
    raw = defaultdict(lambda: defaultdict(float))
    traffic = defaultdict(float)

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('%'):
                continue
            parts = line.split()
            i, j, w = int(parts[0]), int(parts[1]), float(parts[2])
            raw[i][j] += w
            traffic[i] += w
            traffic[j] += w

    # Keep only top_n nodes by total traffic
    top_nodes = set(sorted(traffic, key=traffic.get, reverse=True)[:top_n])

    nodes = sorted(top_nodes)
    p = {n: {} for n in nodes}

    for i in nodes:
        neighbors = {j: w for j, w in raw[i].items() if j in top_nodes}
        if not neighbors:
            continue
        total = sum(neighbors.values())
        for j, w in neighbors.items():
            p[i][j] = w / total

    return nodes, p


def make_highschool_graph(filepath, seed=None):
    """
    Load the HighSchool friendship network (moreno_highschool).
    Edge probabilities randomly chosen from {0.1, 0.2, 0.5} as per the paper.

    File format (KONECT):
      Lines starting with % are comments.
      Each data line: src dst weight  (weight 1 or 2, ignored — paper uses random probs)
    """
    if seed is not None:
        random.seed(seed)

    edges = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('%'):
                continue
            parts = line.split()
            u, v = int(parts[0]), int(parts[1])
            edges.append((u, v))

    nodes = sorted(set(u for u, v in edges) | set(v for u, v in edges))
    p = {n: {} for n in nodes}
    for u, v in edges:
        p[u][v] = random.choice([0.1, 0.2, 0.5])

    return nodes, p


def in_neighbors(p, j):
    return [i for i, nbrs in p.items() if j in nbrs]


def out_neighbors(p, i):
    return list(p[i].keys())


def influence_spread(activation_probs):
    """Sum of all activation probabilities = sigma(phi_0)."""
    return sum(activation_probs.values())
