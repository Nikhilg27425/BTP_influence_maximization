"""
Seed set selection algorithms for Influence Maximization:
  1. SelectTopK    (Algorithm 4)
  2. RankedReplace (Algorithm 5)
  3. Greedy        (Algorithm 6)

Each takes a `compute_fn(nodes, p, seed_set) -> activation_probs` argument
so any activation probability method can be plugged in.

For efficiency, SelectTopK and RankedReplace pre-compute per-node scores once
and reuse them, avoiding redundant calls to expensive methods like SSS-Noself.
"""


def _sigma(nodes, p, seed_set, compute_fn):
    """Influence spread sigma(seed_set) = sum of activation probabilities."""
    return sum(compute_fn(nodes, p, list(seed_set)).values())


def _precompute_scores(nodes, p, compute_fn):
    """
    Compute sigma({j}) for every node j once and cache.
    This avoids re-running expensive methods (e.g. SSS-Noself) per K value.
    """
    return {j: _sigma(nodes, p, [j], compute_fn) for j in nodes}


# ---------------------------------------------------------------------------
# Algorithm 4: SelectTopK
# ---------------------------------------------------------------------------

def select_top_k(nodes, p, K, compute_fn, scores=None):
    """
    Pick the K nodes with the highest individual influence spread.
    Pass pre-computed `scores` dict to avoid redundant computation across K values.
    """
    if scores is None:
        scores = _precompute_scores(nodes, p, compute_fn)
    return sorted(scores, key=scores.get, reverse=True)[:K]


# ---------------------------------------------------------------------------
# Algorithm 5: RankedReplace
# ---------------------------------------------------------------------------

def ranked_replace(nodes, p, K, compute_fn, scores=None, eval_fn=None):
    """
    Start with SelectTopK, then iteratively swap seed nodes with non-seed nodes
    if the swap improves influence spread.

    scores  : pre-computed per-node individual scores (used for ranking)
    eval_fn : function used to evaluate multi-node seed set spread during swaps.
              Defaults to compute_fn. Pass a cheaper fn (e.g. SSS) when compute_fn
              is expensive (e.g. SSS-Noself) to match the paper's intent.
    """
    if scores is None:
        scores = _precompute_scores(nodes, p, compute_fn)
    if eval_fn is None:
        eval_fn = compute_fn

    seed_set = set(sorted(scores, key=scores.get, reverse=True)[:K])
    non_seed_sorted = sorted(
        [j for j in nodes if j not in seed_set],
        key=lambda j: scores[j], reverse=True
    )

    current_spread = _sigma(nodes, p, seed_set, eval_fn)

    for j in non_seed_sorted:
        seed_sorted_asc = sorted(seed_set, key=lambda i: scores[i])
        for i in seed_sorted_asc:
            candidate = (seed_set - {i}) | {j}
            new_spread = _sigma(nodes, p, candidate, eval_fn)
            if new_spread > current_spread:
                seed_set = candidate
                current_spread = new_spread
                break

    return list(seed_set)


# ---------------------------------------------------------------------------
# Algorithm 6: Greedy
# ---------------------------------------------------------------------------

def greedy(nodes, p, K, compute_fn):
    """
    Classic greedy: at each step add the node with the highest marginal gain.
    Guarantees (1 - 1/e) approximation of the optimal influence spread.
    """
    seed_set = []
    current_spread = 0.0

    for _ in range(K):
        best_node, best_gain = None, -1.0
        for j in nodes:
            if j in seed_set:
                continue
            gain = _sigma(nodes, p, seed_set + [j], compute_fn) - current_spread
            if gain > best_gain:
                best_gain, best_node = gain, j
        if best_node is not None:
            seed_set.append(best_node)
            current_spread += best_gain

    return seed_set
