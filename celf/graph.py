"""
Graph utilities for CELF++ experiments.

Loads NetHEPT and NetPHY collaboration networks from SNAP.
Both are undirected — made directed by adding both arc directions (as per paper).

Two probability settings (following Kempe et al. and Chen et al.):
  WC  (Weighted Cascade): p(v,u) = 1 / in_degree(u)
  IC  (Independent Cascade uniform): p(v,u) = 0.1 for all arcs
"""

from collections import defaultdict


def load_collaboration_network(filepath, prob_model='WC'):
    """
    Load a SNAP collaboration network (undirected edge list).
    Makes it directed by adding both arc directions.

    prob_model:
      'WC'  — Weighted Cascade: p(u,v) = 1 / in_degree(v)
      'IC'  — Uniform IC: p(u,v) = 0.1

    Returns (nodes, p) where p[u][v] = propagation probability.
    """
    raw_edges = set()
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            u, v = int(parts[0]), int(parts[1])
            if u != v:
                raw_edges.add((u, v))
                raw_edges.add((v, u))   # make directed (both directions)

    nodes_set = set()
    in_deg = defaultdict(int)
    for u, v in raw_edges:
        nodes_set.add(u)
        nodes_set.add(v)
        in_deg[v] += 1

    nodes = sorted(nodes_set)
    p = {n: {} for n in nodes}

    for u, v in raw_edges:
        if prob_model == 'WC':
            p[u][v] = 1.0 / in_deg[v] if in_deg[v] > 0 else 0.0
        else:  # IC uniform
            p[u][v] = 0.1

    return nodes, p


def influence_spread(activation_probs):
    """Sum of activation probabilities = sigma(S)."""
    return sum(activation_probs.values())
