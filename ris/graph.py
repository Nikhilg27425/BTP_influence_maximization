"""
Graph utilities for RIS / D-RIS experiments.

Loads Slashdot and Epinions social networks from SNAP.
Both are directed unsigned graphs.

Two probability settings:
  WC  (Weighted Cascade): p(u,v) = 1 / in_degree(v)
  IC  (Independent Cascade uniform): p(u,v) = p  (default 0.01 for large graphs)
"""

from collections import defaultdict
import random


def load_snap_directed(filepath, prob_model='IC', p_uniform=0.01):
    """
    Load a SNAP directed network (unsigned edge list).

    prob_model:
      'WC'  — Weighted Cascade: p(u,v) = 1 / in_degree(v)
      'IC'  — Uniform IC: p(u,v) = p_uniform (default 0.01)

    Returns (nodes, p) where p[u][v] = propagation probability.
    """
    edges = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            u, v = int(parts[0]), int(parts[1])
            if u != v:
                edges.append((u, v))

    nodes_set = set()
    in_deg = defaultdict(int)
    for u, v in edges:
        nodes_set.add(u)
        nodes_set.add(v)
        in_deg[v] += 1

    nodes = sorted(nodes_set)
    p = {n: {} for n in nodes}

    for u, v in edges:
        if prob_model == 'WC':
            p[u][v] = 1.0 / in_deg[v] if in_deg[v] > 0 else 0.0
        else:  # IC uniform
            p[u][v] = p_uniform

    return nodes, p


def sample_subgraph(nodes, p, n_nodes, seed=42):
    """
    Extract a subgraph of n_nodes nodes by BFS from a high-degree seed node.
    Useful for quick experiments on large graphs.
    Returns (sub_nodes, sub_p).
    """
    random.seed(seed)

    out_deg = {u: len(p[u]) for u in nodes}
    start = max(out_deg, key=out_deg.get)

    visited = []
    queue = [start]
    seen = {start}
    while queue and len(visited) < n_nodes:
        u = queue.pop(0)
        visited.append(u)
        neighbors = list(p[u].keys())
        random.shuffle(neighbors)
        for v in neighbors:
            if v not in seen and len(seen) < n_nodes:
                seen.add(v)
                queue.append(v)

    sub_nodes = sorted(visited[:n_nodes])
    sub_set = set(sub_nodes)

    # Recompute in-degrees within subgraph for WC
    in_deg = defaultdict(int)
    for u in sub_nodes:
        for v in p[u]:
            if v in sub_set:
                in_deg[v] += 1

    sub_p = {n: {} for n in sub_nodes}
    for u in sub_nodes:
        for v, prob in p[u].items():
            if v in sub_set:
                # Preserve IC uniform or recompute WC
                if in_deg[v] > 0:
                    sub_p[u][v] = prob  # keep original prob (IC uniform stays same)

    return sub_nodes, sub_p
