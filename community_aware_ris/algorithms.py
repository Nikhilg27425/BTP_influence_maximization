"""
Community-Aware RIS (CA-RIS) — Proposed Algorithm.

This module implements the CA-RIS algorithm which extends the D-RIS framework
(Sun & Chen 2021) to account for community structure in social networks.

Problem Motivation
------------------
Standard RIS (and D-RIS) maximise raw influence spread σ(S).  Because real
social networks are modular, seed nodes tend to cluster in the largest
community — creating an echo-chamber effect where small communities receive
little or no influence.

Proposed Objective
------------------
CA-RIS optimises a fairness-adjusted objective:

    F(S) = σ(S) − λ · I(S)

where
  σ(S)  = expected influence spread (estimated via RRR-set coverage)
  I(S)  = imbalance measure — how unevenly seeds are distributed across
           communities (details below)
  λ ≥ 0 = trade-off parameter.  λ=0 → standard RIS; larger λ → more fairness.

Imbalance measure I(S)
----------------------
We use the normalised Gini coefficient of the per-community seed counts:

    I(S) = Gini( {|S ∩ C_c| / |C_c|}_{c=1}^{m} )

i.e. the Gini coefficient of the fractional seed density across communities.
This is 0 when every community gets seeds proportional to its size and 1 when
all seeds land in one community.

Algorithm — Three Steps (Section 3.7.3 of the report)
------------------------------------------------------
1. Detect communities using the Louvain algorithm (python-louvain / networkx).
2. Generate θ RRR sets using the D-RIS procedure.
3. Community-quota greedy coverage:
     a. Compute per-community quota:  q_c = floor(k · |C_c| / n)
        Total quota may be < k due to rounding; remaining slots are filled
        greedily without restriction (fairness-relaxed).
     b. At each greedy step, pick the node u that maximises the marginal
        coverage of remaining RRR sets, subject to:
          — the community of u has not yet exhausted its quota, OR
          — all quotas are exhausted (fallback to unconstrained greedy).
        If no quota-eligible node gives positive coverage, relax the
        quota constraint for this round (quota relaxation rule).

This guarantees every community receives at least one seed (when possible)
while maintaining competitive overall spread.

Evaluation Metrics (Section 3.7.5)
-----------------------------------
  1. Influence Spread σ(S)         — evaluated via Monte Carlo IC simulation
  2. Community Coverage            — fraction of communities with ≥ 1 seed
  3. Seed Distribution Entropy     — entropy of seed counts across communities
  4. Runtime                       — wall-clock time

References
----------
[2]  Blondel V.D. et al. (2008). Fast unfolding of communities in large networks.
     J. Stat. Mech., P10008.
[3]  Borgs C. et al. (2014). Maximizing Social Influence in Nearly Optimal Time.
     SODA 2014.
[6]  Gleeson J.P. et al. (2014). Competition-induced criticality in a model of
     meme popularity. Phys. Rev. Lett., 112, 048701.  (echo-chamber effect)
[12] Fortunato S. (2010). Community detection in graphs. Phys. Rep., 486, 75–174.
[14] Sun G., Chen C. (2021). Influence Maximization Algorithm Based on Reverse
     Reachable Set. Mathematical Problems in Engineering, Hindawi.
"""

import math
import random
from collections import Counter, defaultdict


# ─────────────────────────────────────────────────────────────────────────────
# RRR-set generation  (reused from D-RIS, Section 3.7.2)
# ─────────────────────────────────────────────────────────────────────────────

def build_reverse_adjacency(nodes, p):
    """
    Pre-compute reverse adjacency for efficient RRR-set generation.

    rev_p[v] = [(u, prob), ...]  means edge u→v with probability prob.
    Building this once amortises the cost across all theta RRR-set calls.
    """
    rev_p = {v: [] for v in nodes}
    for u in nodes:
        for v, prob in p[u].items():
            rev_p[v].append((u, prob))
    return rev_p


def generate_rrr_set(nodes, rev_p):
    """
    Generate one Random Reverse Reachable (RRR) set.

    1. Choose a uniformly random target node v.
    2. BFS backward from v in a sampled subgraph:
         For each in-neighbour u of current node w, include edge u→w
         with probability p[u][w].
    3. Return the set of all ancestors of v in the sampled subgraph.

    Complexity: O(avg_in_degree × |RRS|) per call.
    """
    v = random.choice(nodes)
    visited = {v}
    queue = [v]

    while queue:
        w = queue.pop()
        for u, prob in rev_p[w]:
            if u not in visited and random.random() <= prob:
                visited.add(u)
                queue.append(u)

    return list(visited)


def generate_rrr_sets(nodes, rev_p, theta):
    """Generate theta RRR sets and return as a list."""
    return [generate_rrr_set(nodes, rev_p) for _ in range(theta)]


# ─────────────────────────────────────────────────────────────────────────────
# Standard greedy coverage  (shared helper used by RIS and D-RIS baselines)
# ─────────────────────────────────────────────────────────────────────────────

def _greedy_coverage(R, k):
    """
    Greedy maximum-coverage seed selection (no community constraint).

    Iteratively selects the node that covers the most remaining RRR sets,
    then removes all sets that node covers.  Returns seed set of size k.
    """
    R = list(R)
    seed_set = []
    for _ in range(k):
        if not R:
            break
        flat = [node for rrs in R for node in rrs]
        if not flat:
            break
        best = Counter(flat).most_common(1)[0][0]
        seed_set.append(best)
        R = [rrs for rrs in R if best not in rrs]
    return seed_set


def _greedy_coverage_estimate(R, k):
    """Greedy coverage without modifying R — used for θ estimation."""
    R_copy = list(R)
    selected = []
    for _ in range(k):
        if not R_copy:
            break
        flat = [node for rrs in R_copy for node in rrs]
        if not flat:
            break
        best = Counter(flat).most_common(1)[0][0]
        selected.append(best)
        R_copy = [rrs for rrs in R_copy if best not in rrs]
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# Community-quota greedy  (CA-RIS core — Step 3 of the algorithm)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_quotas(community_to_nodes, k):
    """
    Compute per-community seed quotas using proportional allocation.

        q_c = floor(k · |C_c| / n)

    Remaining slots (k − Σq_c) are distributed to the largest communities
    first (largest-remainder method) to ensure Σq_c = k exactly.

    Returns dict: community_id → quota (int ≥ 0).
    """
    n = sum(len(nodes) for nodes in community_to_nodes.values())
    communities = sorted(community_to_nodes.keys())

    # Floor quotas
    raw = {c: k * len(community_to_nodes[c]) / n for c in communities}
    floor_q = {c: int(raw[c]) for c in communities}
    remainder = k - sum(floor_q.values())

    # Distribute remainder by largest fractional part
    fracs = sorted(communities, key=lambda c: -(raw[c] - floor_q[c]))
    for c in fracs[:remainder]:
        floor_q[c] += 1

    return floor_q


def community_quota_greedy(R, k, node_to_community, community_to_nodes):
    """
    Community-quota greedy seed selection — the core of CA-RIS.

    Algorithm
    ---------
    1. Compute per-community quotas q_c (proportional to community size).
    2. Build a fast index: for each node, count how many RRR sets contain it.
    3. At each of k steps:
         a. Find the best quota-eligible node (one whose community still has
            remaining quota > 0) that covers the most remaining RRR sets.
         b. If no quota-eligible node covers any set, relax the constraint and
            pick the globally best node (quota-relaxation rule).
         c. Add the chosen node to the seed set and remove covered RRR sets.
         d. Decrement the quota of the chosen node's community.

    Returns
    -------
    seed_set         : list of k seed node IDs
    quota_used       : dict  community_id → seeds actually assigned
    quota_relaxed_at : list of steps where the quota was relaxed (0-indexed)
    """
    # Step 1: quotas
    quotas_remaining = _compute_quotas(community_to_nodes, k)

    # Step 2: working copy and node → RRR set indices mapping
    R_active = [set(rrs) for rrs in R]          # list of sets for O(1) membership
    total_sets = len(R_active)

    # node_coverage[node] = number of active RRR sets containing node
    node_coverage = Counter()
    for rrs in R_active:
        for node in rrs:
            node_coverage[node] += 1

    seed_set = []
    quota_used = defaultdict(int)
    quota_relaxed_at = []

    for step in range(k):
        if not R_active:
            break

        # Step 3a: find best quota-eligible node
        best_node = None
        best_count = -1

        # Check quota-eligible nodes first
        quota_eligible_communities = {
            c for c, q in quotas_remaining.items() if q > 0
        }

        for node, count in node_coverage.most_common():
            if count == 0:
                break
            cid = node_to_community.get(node)
            if cid in quota_eligible_communities:
                best_node = node
                best_count = count
                break

        # Step 3b: quota relaxation — fall back to unconstrained best
        if best_node is None or best_count == 0:
            quota_relaxed_at.append(step)
            if node_coverage:
                best_node, best_count = node_coverage.most_common(1)[0]
            else:
                break

        if best_count == 0:
            break

        # Step 3c: add seed and remove covered RRR sets
        seed_set.append(best_node)
        cid = node_to_community.get(best_node)

        # Identify which RRR sets are now covered (contain best_node)
        covered_indices = [
            i for i, rrs in enumerate(R_active) if best_node in rrs
        ]
        covered_set = set(covered_indices)

        # Update node_coverage: decrement counts for all nodes in covered sets
        for i in covered_indices:
            for node in R_active[i]:
                node_coverage[node] -= 1
                if node_coverage[node] == 0:
                    del node_coverage[node]

        # Remove covered sets
        R_active = [rrs for i, rrs in enumerate(R_active)
                    if i not in covered_set]

        # Step 3d: decrement quota
        if cid is not None and quotas_remaining.get(cid, 0) > 0:
            quotas_remaining[cid] -= 1
        quota_used[cid] += 1

    return seed_set, dict(quota_used), quota_relaxed_at


# ─────────────────────────────────────────────────────────────────────────────
# θ determination  (D-RIS style, Section 3.7.2 / Sun & Chen 2021)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_theta(n, k, opt_est, eps=0.5, l=1):
    """
    Compute the required number of RRR sets θ given an OPT estimate.

    Formula (Tang et al. 2014):
        θ = n(8+2ε)(l·ln n + ln C(n,k) + ln 2) / (ε² · OPT_est)

    Capped at 200,000 for practical use on large graphs.
    """
    log_n_choose_k = sum(
        math.log(n - i) - math.log(i + 1) for i in range(k)
    )
    theta = int(math.ceil(
        n * (8 + 2 * eps)
        * (l * math.log(n) + log_n_choose_k + math.log(2))
        / (eps ** 2 * opt_est)
    ))
    return min(theta, 200_000)


# ─────────────────────────────────────────────────────────────────────────────
# CA-RIS  (proposed algorithm — main entry point)
# ─────────────────────────────────────────────────────────────────────────────

def ca_ris(nodes, p, k, node_to_community, community_to_nodes,
           lam=0.5, eps=0.5, l=1):
    """
    Community-Aware RIS (CA-RIS) — the proposed algorithm.

    Combines D-RIS θ-determination with community-quota greedy seed selection
    to produce a seed set that balances influence spread with community fairness.

    Objective:  F(S) = σ(S) − λ · I(S)
      σ(S)  estimated via RRR-set coverage
      I(S)  = Gini coefficient of per-community fractional seed density
      λ     controls the spread–fairness trade-off (default 0.5)

    Parameters
    ----------
    nodes               : list of node IDs
    p                   : forward adjacency  p[u][v] = prob
    k                   : seed set size
    node_to_community   : dict  node → community_id
    community_to_nodes  : dict  community_id → list of nodes
    lam                 : λ trade-off parameter (0 = pure RIS)
    eps                 : approximation parameter ε
    l                   : confidence parameter

    Returns
    -------
    seed_set         : list of k seed node IDs
    R                : final collection of RRR sets (for spread estimation)
    theta_used       : total number of RRR sets generated
    quota_used       : dict  community_id → seeds assigned
    quota_relaxed_at : steps where quota relaxation was triggered
    """
    n = len(nodes)
    rev_p = build_reverse_adjacency(nodes, p)

    # ── Phase 1: initial θ estimate (D-RIS style) ─────────────────────────────
    theta_0 = max(int(n * math.log(n) / k), 1000)
    theta_0 = min(theta_0, 50_000)

    print(f"  [CA-RIS] n={n:,}  k={k}  λ={lam}  ε={eps}")
    print(f"  [CA-RIS] Generating initial {theta_0:,} RRR sets...")

    R = generate_rrr_sets(nodes, rev_p, theta_0)

    # ── Phase 2: OPT estimation and θ refinement ──────────────────────────────
    best_k = _greedy_coverage_estimate(R, k)
    covered = sum(1 for rrs in R if any(u in rrs for u in best_k))
    coverage_frac = covered / len(R)
    opt_est = max(coverage_frac * n, k)

    print(f"  [CA-RIS] Coverage fraction={coverage_frac:.4f}  "
          f"OPT_est={opt_est:.1f}")

    theta_new = _compute_theta(n, k, opt_est, eps, l)

    if theta_new > len(R):
        additional = theta_new - len(R)
        print(f"  [CA-RIS] Generating {additional:,} more RRR sets "
              f"(target θ={theta_new:,})...")
        R.extend(generate_rrr_set(nodes, rev_p) for _ in range(additional))
    else:
        print(f"  [CA-RIS] θ_new={theta_new:,} ≤ current |R|={len(R):,}. "
              f"No additional sets needed.")

    theta_used = len(R)
    m = len(community_to_nodes)
    print(f"  [CA-RIS] Final |R|={theta_used:,}  "
          f"communities={m}  Running quota-greedy...")

    # ── Phase 3: community-quota greedy ───────────────────────────────────────
    seed_set, quota_used, quota_relaxed_at = community_quota_greedy(
        R, k, node_to_community, community_to_nodes
    )

    if quota_relaxed_at:
        print(f"  [CA-RIS] Quota relaxed at steps: {quota_relaxed_at}")
    else:
        print(f"  [CA-RIS] All {k} seeds selected within quota constraints.")

    return seed_set, R, theta_used, quota_used, quota_relaxed_at


# ─────────────────────────────────────────────────────────────────────────────
# RIS baseline  (for comparison, same θ logic as ris/algorithms.py)
# ─────────────────────────────────────────────────────────────────────────────

def ris(nodes, p, k, eps=0.5, l=1):
    """
    Standard RIS (Borgs et al. 2014) — used as baseline comparison.

    Returns (seed_set, R).
    """
    n = len(nodes)
    log_n_choose_k = sum(math.log(n - i) - math.log(i + 1) for i in range(k))
    theta = int(math.ceil(
        n * (8 + 2 * eps) * (l * math.log(n) + log_n_choose_k + math.log(2))
        / (eps ** 2 * k)
    ))
    theta = min(theta, 200_000)

    print(f"  [RIS] Generating {theta:,} RRR sets for {n:,} nodes...")
    rev_p = build_reverse_adjacency(nodes, p)
    R = generate_rrr_sets(nodes, rev_p, theta)

    print(f"  [RIS] Running greedy coverage (k={k})...")
    seed_set = _greedy_coverage(R, k)
    return seed_set, R


# ─────────────────────────────────────────────────────────────────────────────
# D-RIS baseline  (for comparison, Sun & Chen 2021)
# ─────────────────────────────────────────────────────────────────────────────

def dris(nodes, p, k, eps=0.5, l=1):
    """
    D-RIS (Sun & Chen 2021) — used as baseline comparison.

    Returns (seed_set, R, theta_used).
    """
    n = len(nodes)
    rev_p = build_reverse_adjacency(nodes, p)

    theta_0 = max(int(n * math.log(n) / k), 1000)
    theta_0 = min(theta_0, 50_000)

    print(f"  [D-RIS] Initial θ_0={theta_0:,} for {n:,} nodes, k={k}...")
    R = generate_rrr_sets(nodes, rev_p, theta_0)

    best_k = _greedy_coverage_estimate(R, k)
    covered = sum(1 for rrs in R if any(u in rrs for u in best_k))
    coverage_frac = covered / len(R)
    opt_est = max(coverage_frac * n, k)

    print(f"  [D-RIS] Coverage fraction={coverage_frac:.4f}  "
          f"OPT_est={opt_est:.1f}")

    theta_new = _compute_theta(n, k, opt_est, eps, l)

    if theta_new > len(R):
        additional = theta_new - len(R)
        print(f"  [D-RIS] Generating {additional:,} more RRR sets "
              f"(target θ={theta_new:,})...")
        R.extend(generate_rrr_set(nodes, rev_p) for _ in range(additional))
    else:
        print(f"  [D-RIS] θ_new={theta_new:,} ≤ |R|={len(R):,}. Done.")

    theta_used = len(R)
    print(f"  [D-RIS] Final |R|={theta_used:,}. Running greedy coverage...")
    seed_set = _greedy_coverage(R, k)
    return seed_set, R, theta_used


# ─────────────────────────────────────────────────────────────────────────────
# Fairness / evaluation metrics  (Section 3.7.5)
# ─────────────────────────────────────────────────────────────────────────────

def community_coverage(seed_set, community_to_nodes):
    """
    Metric 2: Community Coverage.

    Fraction of communities that contain at least one seed node.

        CC(S) = |{c : S ∩ C_c ≠ ∅}| / m

    Returns a float in [0, 1].  CC=1 means every community has ≥ 1 seed.
    """
    m = len(community_to_nodes)
    if m == 0:
        return 0.0
    seed_set_s = set(seed_set)
    covered = sum(
        1 for nodes in community_to_nodes.values()
        if any(n in seed_set_s for n in nodes)
    )
    return covered / m


def seed_distribution_entropy(seed_set, community_to_nodes):
    """
    Metric 3: Seed Distribution Entropy.

    Shannon entropy of the seed count distribution across communities.
    Higher entropy → more uniform spread of seeds.

        H(S) = −Σ_c  p_c · log2(p_c)    where p_c = |S ∩ C_c| / |S|

    Normalised by log2(m) to give a value in [0, 1].
    Returns (raw_entropy, normalised_entropy).
    """
    m = len(community_to_nodes)
    k = len(seed_set)
    if k == 0 or m == 0:
        return 0.0, 0.0

    seed_set_s = set(seed_set)
    counts = Counter()
    for cid, nodes in community_to_nodes.items():
        counts[cid] = sum(1 for n in nodes if n in seed_set_s)

    entropy = 0.0
    for cid in community_to_nodes:
        p = counts[cid] / k
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(m) if m > 1 else 1.0
    return entropy, entropy / max_entropy


def gini_imbalance(seed_set, community_to_nodes):
    """
    Imbalance measure I(S) — Gini coefficient of fractional seed density.

    For each community c, compute:
        density_c = |S ∩ C_c| / |C_c|

    Then compute the Gini coefficient of these densities.

        Gini = (Σ_i Σ_j |d_i − d_j|) / (2 · m · Σ_i d_i)

    Returns 0 (perfect balance) to 1 (all seeds in one community).
    """
    seed_set_s = set(seed_set)
    densities = []
    for cid, nodes in community_to_nodes.items():
        size = len(nodes)
        count = sum(1 for n in nodes if n in seed_set_s)
        densities.append(count / size if size > 0 else 0.0)

    m = len(densities)
    if m == 0 or sum(densities) == 0:
        return 0.0

    # Gini coefficient
    total_diff = sum(abs(densities[i] - densities[j])
                     for i in range(m) for j in range(m))
    gini = total_diff / (2 * m * sum(densities))
    return gini


def fairness_objective(seed_set, R, nodes, community_to_nodes,
                       node_to_community, lam):
    """
    Compute F(S) = σ̂(S) − λ · I(S)

    where σ̂(S) is the RRR-set coverage estimate of influence spread (scaled
    to expected node count) and I(S) is the Gini imbalance.

    Parameters
    ----------
    seed_set            : list of seed node IDs
    R                   : list of RRR sets used during seed selection
    nodes               : full node list (for normalisation)
    community_to_nodes  : community structure
    node_to_community   : node → community
    lam                 : λ trade-off parameter

    Returns
    -------
    F      : float — fairness-adjusted objective
    sigma  : float — RRR-based spread estimate
    imbal  : float — Gini imbalance
    """
    n = len(nodes)
    seed_s = set(seed_set)

    # σ̂(S): fraction of RRR sets covered × n
    if R:
        covered = sum(1 for rrs in R if any(u in rrs for u in seed_s))
        sigma = (covered / len(R)) * n
    else:
        sigma = 0.0

    imbal = gini_imbalance(seed_set, community_to_nodes)
    F = sigma - lam * imbal * n   # scale imbalance to same unit as sigma

    return F, sigma, imbal


def print_metrics(label, seed_set, R, nodes, community_to_nodes,
                  node_to_community, lam, mc_spread_val=None):
    """
    Pretty-print all four evaluation metrics for a seed set.

    Parameters
    ----------
    label           : string identifier (e.g. 'CA-RIS', 'D-RIS')
    seed_set        : list of selected seed node IDs
    R               : RRR sets (used for σ̂ estimation)
    nodes           : full node list
    community_to_nodes, node_to_community : community structure
    lam             : λ parameter
    mc_spread_val   : MC-evaluated spread (float or None if not computed)
    """
    cc = community_coverage(seed_set, community_to_nodes)
    raw_h, norm_h = seed_distribution_entropy(seed_set, community_to_nodes)
    F, sigma_hat, imbal = fairness_objective(
        seed_set, R, nodes, community_to_nodes, node_to_community, lam
    )

    print(f"\n  ── {label} Metrics ──")
    print(f"    Seeds selected        : {len(seed_set)}")
    print(f"    σ̂(S) RRR estimate    : {sigma_hat:.2f} nodes")
    if mc_spread_val is not None:
        print(f"    σ(S) MC spread        : {mc_spread_val:.2f} nodes")
    print(f"    Community coverage    : {cc:.4f}  "
          f"({int(cc * len(community_to_nodes))}/{len(community_to_nodes)} "
          f"communities)")
    print(f"    Seed entropy (norm)   : {norm_h:.4f}  (raw={raw_h:.4f} bits)")
    print(f"    Gini imbalance I(S)   : {imbal:.4f}")
    print(f"    F(S) = σ̂ − λ·I·n    : {F:.2f}  (λ={lam})")

    # Seed distribution breakdown
    seed_s = set(seed_set)
    print(f"\n    Per-community seed distribution:")
    com_sizes = sorted(
        community_to_nodes.items(), key=lambda x: -len(x[1])
    )
    for cid, cnodes in com_sizes[:20]:   # show top-20 communities
        count = sum(1 for n in cnodes if n in seed_s)
        bar = '█' * count + '░' * max(0, 1 - count)
        print(f"      C{cid:>3}: size={len(cnodes):>5}  seeds={count:>2}  {bar}")
    if len(com_sizes) > 20:
        print(f"      ... ({len(com_sizes) - 20} more communities)")
