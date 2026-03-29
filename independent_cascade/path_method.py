"""
Path Method: exact activation probability computation via evolution graph.
Algorithm 1 from the paper. Exponential complexity O(6^N) — only for small networks.

Each cell C_k = (Ap_k, Ac_k, P_k):
  Ap_k : frozenset of past active nodes
  Ac_k : frozenset of current active nodes
  P_k  : probability of reaching this cell
"""

from itertools import chain, combinations


def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def arc_probability(p, Ap_i, Ac_i, S_k):
    """
    Compute P_a(i, k): probability that exactly the nodes in S_k get activated
    from Ac_i, given that Ap_i | Ac_i are already active.

    For each node r in S (inactive out-neighbors of Ac_i):
      - if r in S_k: at least one node in Ac_i activates it
      - if r not in S_k: no node in Ac_i activates it
    """
    # S = out-neighbors of Ac_i that are not yet active
    S_k = frozenset(S_k)
    prob = 1.0

    # Collect all inactive out-neighbors of Ac_i
    S_all = set()
    for q in Ac_i:
        for r in p[q]:
            if r not in Ap_i and r not in Ac_i:
                S_all.add(r)

    for r in S_all:
        # probability that r is NOT activated by any node in Ac_i
        p_not_activated = 1.0
        for q in Ac_i:
            if r in p[q]:
                p_not_activated *= (1.0 - p[q][r])

        if r in S_k:
            # r must be activated by at least one node in Ac_i
            prob *= (1.0 - p_not_activated)
        else:
            # r must NOT be activated by any node in Ac_i
            prob *= p_not_activated

    return prob


def path_method(nodes, p, seed_set):
    """
    Algorithm 1: Path Method.
    Returns dict: node -> exact activation probability pi_j^p.
    """
    seed_set = frozenset(seed_set)

    # Each cell: (Ap, Ac, P)
    cells = []   # list of [Ap, Ac, P]
    cell_index = {}  # (Ap, Ac) -> index in cells

    # Initial cell
    Ap1 = frozenset()
    Ac1 = seed_set
    P1 = 1.0
    cells.append([Ap1, Ac1, P1])
    cell_index[(Ap1, Ac1)] = 0

    new = [0]  # indices of cells to explore

    while new:
        i = new.pop(0)
        Ap_i, Ac_i, P_i = cells[i]

        # S = inactive out-neighbors of Ac_i
        S = set()
        for q in Ac_i:
            for r in p[q]:
                if r not in Ap_i and r not in Ac_i:
                    S.add(r)

        # Enumerate all subsets S' of S
        for S_prime in powerset(S):
            S_prime = frozenset(S_prime)
            Ap_k = Ap_i | Ac_i
            Ac_k = S_prime
            Pa = arc_probability(p, Ap_i, Ac_i, S_prime)
            P_k = P_i * Pa

            key = (Ap_k, Ac_k)
            if key in cell_index:
                # Equivalent cell exists — just add arc weight
                k = cell_index[key]
                cells[k][2] += P_k
            else:
                k = len(cells)
                cells.append([Ap_k, Ac_k, P_k])
                cell_index[key] = k
                if Ac_k:  # non-terminal: add to exploration queue
                    new.append(k)

    # Compute activation probabilities from terminal cells
    pi = {node: 0.0 for node in nodes}
    for node in nodes:
        if node in seed_set:
            pi[node] = 1.0
            continue
        for Ap, Ac, P in cells:
            if len(Ac) == 0 and node in Ap:  # terminal cell containing node
                pi[node] += P

    return pi
