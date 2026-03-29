"""
Signed social network graph utilities for the IC-P model.

A signed network is G = (V, E, W, P) where:
  - V : set of nodes
  - E : set of directed edges
  - W : edge weights (propagation probabilities), w[u][v] in (0,1]
  - P : polarity matrix, P[u][v] in {+1, -1}

Weighted Cascade Setting (WCS):
  w(u, v) = 1 / in_degree(v)

Edge probability P[u][v]:
  +1  if v is positively influenced by u
  -1  if v is negatively influenced by u
"""

from collections import defaultdict


def load_snap_signed(filepath, delimiter='\t'):
    """
    Load a SNAP signed network file.
    Expected format (one edge per line, skip lines starting with #):
      src  dst  sign      (sign: +1 or -1)

    Returns (nodes, w, polarity) where:
      nodes    : sorted list of node IDs
      w[u][v]  : propagation probability (Weighted Cascade Setting)
      pol[u][v]: polarity +1 or -1
    """
    edges = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(delimiter)
            if len(parts) < 3:
                parts = line.split()
            u, v, s = int(parts[0]), int(parts[1]), int(parts[2])
            edges.append((u, v, s))

    # Collect nodes and in-degrees
    nodes_set = set()
    in_deg = defaultdict(int)
    for u, v, s in edges:
        nodes_set.add(u)
        nodes_set.add(v)
        in_deg[v] += 1

    nodes = sorted(nodes_set)
    w   = {n: {} for n in nodes}
    pol = {n: {} for n in nodes}

    for u, v, s in edges:
        # Weighted Cascade Setting: w(u,v) = 1 / in_degree(v)
        w[u][v]   = 1.0 / in_deg[v] if in_deg[v] > 0 else 0.0
        pol[u][v] = s  # +1 or -1

    return nodes, w, pol


def sample_subgraph(nodes, w, pol, n_nodes, seed=42):
    """
    Extract a subgraph of n_nodes nodes by BFS from a high-degree seed node.
    Useful for quick experiments on large graphs.
    Returns (sub_nodes, sub_w, sub_pol).
    """
    import random
    random.seed(seed)

    # Start BFS from the highest out-degree node
    out_deg = {u: len(w[u]) for u in nodes}
    start = max(out_deg, key=out_deg.get)

    visited = []
    queue = [start]
    seen = {start}
    while queue and len(visited) < n_nodes:
        u = queue.pop(0)
        visited.append(u)
        neighbors = list(w[u].keys()) + [i for i in nodes if u in w.get(i, {})]
        random.shuffle(neighbors)
        for v in neighbors:
            if v not in seen and len(seen) < n_nodes:
                seen.add(v)
                queue.append(v)

    sub_nodes = sorted(visited[:n_nodes])
    sub_set = set(sub_nodes)

    # Recompute in-degrees within subgraph for WCS
    in_deg = defaultdict(int)
    for u in sub_nodes:
        for v in w[u]:
            if v in sub_set:
                in_deg[v] += 1

    sub_w   = {n: {} for n in sub_nodes}
    sub_pol = {n: {} for n in sub_nodes}
    for u in sub_nodes:
        for v, _ in w[u].items():
            if v in sub_set and in_deg[v] > 0:
                sub_w[u][v]   = 1.0 / in_deg[v]
                sub_pol[u][v] = pol[u][v]

    return sub_nodes, sub_w, sub_pol


def out_degrees(nodes, w):
    """Return dict: node -> out-degree."""
    return {n: len(w[n]) for n in nodes}


def in_degrees(nodes, w):
    """Return dict: node -> in-degree."""
    deg = defaultdict(int)
    for u in nodes:
        for v in w[u]:
            deg[v] += 1
    return dict(deg)
