"""
Graph utilities for Community-Aware RIS experiments.

Loads Slashdot and Epinions social networks (same datasets as RIS module).
Adds community detection via the Louvain algorithm on an undirected projection
of the directed graph.

Two probability settings:
  WC  (Weighted Cascade): p(u,v) = 1 / in_degree(v)
  IC  (Independent Cascade uniform): p(u,v) = p  (default 0.01)

Community detection:
  Uses the Louvain method (python-louvain / community package) which maximises
  the modularity Q.  The directed graph is treated as undirected for community
  detection — this is standard practice because Louvain is defined on undirected
  graphs and community structure is a global property of the network topology.

References:
  [2]  Blondel V.D. et al. (2008). Fast unfolding of communities in large
       networks. J. Stat. Mech., P10008.
  [12] Fortunato S. (2010). Community detection in graphs. Phys. Rep., 486, 75–174.
"""

from collections import defaultdict
import math
import random


# ── Graph loading ─────────────────────────────────────────────────────────────

def load_snap_directed(filepath, prob_model='IC', p_uniform=0.01):
    """
    Load a SNAP directed network (unsigned edge list).

    Parameters
    ----------
    filepath    : path to SNAP .txt edge list
    prob_model  : 'WC' (Weighted Cascade) or 'IC' (Uniform IC)
    p_uniform   : edge probability used when prob_model='IC'

    Returns
    -------
    nodes : sorted list of node IDs
    p     : dict  p[u][v] = propagation probability  (forward adjacency)
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
        else:
            p[u][v] = p_uniform

    return nodes, p


def sample_subgraph(nodes, p, n_nodes, seed=42):
    """
    Extract a subgraph of n_nodes nodes by BFS from the highest-degree seed node.
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

    in_deg = defaultdict(int)
    for u in sub_nodes:
        for v in p[u]:
            if v in sub_set:
                in_deg[v] += 1

    sub_p = {n: {} for n in sub_nodes}
    for u in sub_nodes:
        for v, prob in p[u].items():
            if v in sub_set:
                sub_p[u][v] = prob

    return sub_nodes, sub_p


# ── Community detection ───────────────────────────────────────────────────────

def detect_communities_louvain(nodes, p):
    """
    Detect communities using the Louvain algorithm.

    The directed graph (nodes, p) is projected to an undirected graph for
    community detection — an edge {u, v} exists if u→v or v→u in p.

    Requires: python-louvain  (pip install python-louvain)
              which is imported as `community`

    Parameters
    ----------
    nodes : list of node IDs
    p     : forward adjacency dict  p[u][v] = prob

    Returns
    -------
    node_to_community : dict  node → community_id (int, 0-indexed)
    community_to_nodes: dict  community_id → list of node IDs
    modularity        : float Q value of the detected partition
    """
    try:
        import community as community_louvain
        import networkx as nx
    except ImportError as e:
        raise ImportError(
            "Community detection requires python-louvain and networkx.\n"
            "Install with:  pip install python-louvain networkx"
        ) from e

    # Build undirected NetworkX graph
    G = nx.Graph()
    G.add_nodes_from(nodes)
    for u in nodes:
        for v in p[u]:
            if v in G:
                G.add_edge(u, v)

    # Run Louvain
    partition = community_louvain.best_partition(G)  # node → community_id

    # Remap community IDs to be 0-indexed and contiguous
    unique_ids = sorted(set(partition.values()))
    remap = {old: new for new, old in enumerate(unique_ids)}
    node_to_community = {n: remap[partition[n]] for n in nodes}

    # Build reverse mapping
    community_to_nodes = defaultdict(list)
    for node, cid in node_to_community.items():
        community_to_nodes[cid].append(node)

    # Compute modularity
    modularity = community_louvain.modularity(partition, G)

    return dict(node_to_community), dict(community_to_nodes), modularity


def detect_communities_louvain_fallback(nodes, p, seed=42):
    """
    Louvain detection with a pure-Python fallback if python-louvain is absent.

    The fallback is a simple label-propagation algorithm — it is less accurate
    than Louvain but requires no extra dependencies and is sufficient for
    testing.  It is NOT used in final experiments.

    Returns same (node_to_community, community_to_nodes, modularity) tuple;
    modularity is computed manually when using the fallback.
    """
    try:
        return detect_communities_louvain(nodes, p)
    except ImportError:
        print("  [WARNING] python-louvain not found. "
              "Using label-propagation fallback for community detection.")
        return _label_propagation(nodes, p, seed=seed)


def _label_propagation(nodes, p, seed=42, max_iter=100):
    """
    Simple synchronous label propagation for community detection.
    Used only as a fallback when python-louvain is unavailable.
    """
    rng = random.Random(seed)
    node_set = set(nodes)

    # Build undirected adjacency
    adj = defaultdict(set)
    for u in nodes:
        for v in p[u]:
            if v in node_set:
                adj[u].add(v)
                adj[v].add(u)

    labels = {n: i for i, n in enumerate(nodes)}

    for iteration in range(max_iter):
        order = nodes[:]
        rng.shuffle(order)
        changed = False
        for u in order:
            if not adj[u]:
                continue
            nbr_labels = [labels[v] for v in adj[u]]
            # Most common label among neighbours
            counts = defaultdict(int)
            for lbl in nbr_labels:
                counts[lbl] += 1
            best = max(counts, key=counts.get)
            if labels[u] != best:
                labels[u] = best
                changed = True
        if not changed:
            break

    # Remap to 0-indexed contiguous IDs
    unique = sorted(set(labels.values()))
    remap = {old: new for new, old in enumerate(unique)}
    node_to_community = {n: remap[labels[n]] for n in nodes}

    community_to_nodes = defaultdict(list)
    for node, cid in node_to_community.items():
        community_to_nodes[cid].append(node)

    # Compute modularity Q manually
    modularity = _compute_modularity(nodes, p, node_to_community)

    return dict(node_to_community), dict(community_to_nodes), modularity


def _compute_modularity(nodes, p, node_to_community):
    """
    Compute the undirected modularity Q of a partition.

    Q = (1/2m) Σ_{ij} [ A_ij - k_i * k_j / 2m ] * δ(c_i, c_j)

    where m = total edges in undirected projection, A_ij = 1 if edge exists,
    k_i = degree of node i, δ = Kronecker delta on community assignment.
    """
    node_set = set(nodes)

    # Build undirected edge set and degrees
    adj = defaultdict(set)
    for u in nodes:
        for v in p[u]:
            if v in node_set:
                adj[u].add(v)
                adj[v].add(u)

    m = sum(len(adj[u]) for u in nodes) / 2.0
    if m == 0:
        return 0.0

    degree = {u: len(adj[u]) for u in nodes}
    Q = 0.0
    for u in nodes:
        for v in adj[u]:
            if node_to_community[u] == node_to_community[v]:
                Q += 1.0 - degree[u] * degree[v] / (2.0 * m)
    Q /= (2.0 * m)
    return Q


# ── Community statistics ──────────────────────────────────────────────────────

def community_stats(community_to_nodes, node_to_community, p):
    """
    Print a summary of detected communities.

    Returns a dict with:
      num_communities : int
      sizes           : list of community sizes (sorted descending)
      largest_frac    : fraction of nodes in the largest community
      modularity_note : string (pass modularity separately for display)
    """
    sizes = sorted([len(v) for v in community_to_nodes.values()], reverse=True)
    n_total = sum(sizes)
    num_c = len(sizes)

    print(f"\n  Community structure summary:")
    print(f"    Detected communities : {num_c}")
    print(f"    Largest community    : {sizes[0]} nodes "
          f"({100*sizes[0]/n_total:.1f}% of graph)")
    print(f"    Smallest community   : {sizes[-1]} nodes")
    print(f"    Median size          : {sizes[num_c // 2]} nodes")
    if num_c <= 20:
        print(f"    All sizes            : {sizes}")
    else:
        print(f"    Top-10 sizes         : {sizes[:10]}")

    return {
        'num_communities': num_c,
        'sizes': sizes,
        'largest_frac': sizes[0] / n_total,
    }
