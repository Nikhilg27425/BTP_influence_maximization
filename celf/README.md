# CELF — Cost-Effective Lazy Forward Algorithm

Python implementation of the CELF algorithm for influence maximization.

Based on:

> **"Cost-effective outbreak detection in networks"**
> Jure Leskovec, Andreas Krause, Carlos Guestrin, Christos Faloutsos, Jeanne VanBriesen, Natalie Glance
> *KDD 2007*

> **"CELF++: Optimizing the Greedy Algorithm for Influence Maximization in Social Networks"**
> Amit Goyal, Wei Lu, Laks V.S. Lakshmanan — *WWW 2011 Poster*
> DOI: 10.1145/1963192.1963217

---

## What This Is

The naive greedy algorithm for influence maximization (Kempe et al. 2003) is quadratic in the number of nodes — at each of k steps it evaluates all N nodes, giving O(k × N × MC_runs) total simulations. For a 10k-node network with k=100 and 10,000 MC runs, that's **10 billion simulations**.

CELF exploits the **submodularity** of the influence spread function to dramatically reduce the number of evaluations:

> The marginal gain of a node can only **decrease** as the seed set grows.
> So a node's previously computed gain is an **upper bound** on its current gain.
> We only recompute when a node reaches the top of the heap.

This reduces the number of MC evaluations from O(k × N) to roughly O(N + small_constant × k).

---

## Key Concept — Submodularity

A function f is submodular if:
```
f(S ∪ {w}) − f(S)  ≥  f(T ∪ {w}) − f(T)    whenever S ⊆ T
```

In plain terms: adding a node to a smaller seed set gives at least as much gain as adding it to a larger seed set. The influence spread function σ(S) is submodular under both IC and LT models.

CELF uses this to avoid recomputing marginal gains unnecessarily.

---

## CELF Algorithm

```
1. Initialize max-heap Q:
   For each node u: compute mg(u) = σ({u}), push (-mg, u, flag=0) to Q

2. For each seed to pick (step 1..k):
   While True:
     Pop top node u from Q
     If u.flag == |S|:          # mg is up-to-date → pick u
       S = S ∪ {u}
       break
     Else:                      # mg is stale → recompute
       mg(u) = σ(S ∪ {u}) − σ(S)
       u.flag = |S|
       Push updated u back to Q
```

The `flag` tracks when the marginal gain was last computed. If `flag == |S|`, the gain is current. Otherwise it's an upper bound and needs recomputing.

---

## Algorithms Implemented

| Algorithm | Complexity | Description |
|-----------|-----------|-------------|
| Naive Greedy | O(k × N × MC) | Evaluates all nodes at every step. Correctness baseline. |
| CELF | O(N × MC + small × k × MC) | Lazy-forward with heap. Dramatically fewer evaluations. |

---

## Datasets

Both from [Stanford SNAP](https://snap.stanford.edu/data/index.html) — arXiv collaboration networks:

| Dataset | SNAP file | Nodes | Edges (directed) | Description |
|---------|-----------|-------|-----------------|-------------|
| NetHEPT | ca-HepTh.txt | 9,875 | 51,946 | High Energy Physics Theory collaborations |
| NetPHY  | ca-HepPh.txt | 12,008 | 237,010 | High Energy Physics Phenomenology collaborations |

Both are undirected — made directed by adding both arc directions (as per paper).

**Two probability settings:**
- `WC` — Weighted Cascade: `p(u,v) = 1 / in_degree(v)`
- `IC` — Uniform IC: `p(u,v) = 0.1` for all arcs

---

## Project Structure

```
celf/
├── graph.py        # Dataset loader, WC/IC probability models
├── monte_carlo.py  # IC simulation, mc_spread()
├── algorithms.py   # Naive Greedy, CELF
├── experiments.py  # Experiment runner, CLI interface
├── data/
│   ├── NetHEPT.txt  (ca-HepTh from SNAP)
│   └── NetPHY.txt   (ca-HepPh from SNAP)
└── README.md
```

---

## How to Run

```bash
# NetHEPT Weighted Cascade, k=20 seeds, 1000 MC runs
python experiments.py hept_wc --k 20 --runs 1000

# NetHEPT Uniform IC
python experiments.py hept_ic --k 20 --runs 1000

# NetPHY Weighted Cascade
python experiments.py phy_wc --k 20 --runs 1000

# Also run naive Greedy for comparison (slow!)
python experiments.py hept_wc --k 5 --runs 500 --greedy

# All datasets
python experiments.py all --k 20 --runs 1000
```

---

## Our Results — NetHEPT-WC (k=20, 1000 MC runs)

**Graph:** 9,875 nodes, 51,946 directed edges. Probability model: WC.

### CELF Spread vs k

| k | Spread | Recomputed this step | Total lookups |
|---|--------|---------------------|---------------|
| 1 | 44.02 | 0 | 9,875 |
| 2 | 85.99 | 2 | 9,877 |
| 3 | 124.23 | 2 | 9,879 |
| 4 | 157.70 | 10 | 9,889 |
| 5 | 193.49 | 4 | 9,893 |
| 6 | 222.84 | 10 | 9,903 |
| 7 | 250.75 | 21 | 9,924 |
| 8 | 276.44 | 14 | 9,938 |
| 9 | 306.98 | 2 | 9,940 |
| 10 | 331.37 | 18 | 9,958 |
| 11 | 354.69 | 11 | 9,969 |
| 12 | 375.64 | 42 | 10,011 |
| 13 | 400.11 | 36 | 10,047 |
| 14 | 419.18 | 27 | 10,074 |
| 15 | 438.13 | 13 | 10,087 |
| 16 | 459.04 | 10 | 10,097 |
| 17 | 480.20 | 9 | 10,106 |
| 18 | 498.80 | 23 | 10,129 |
| 19 | 514.13 | 106 | 10,235 |
| 20 | 528.41 | 68 | 10,303 |

### Efficiency Summary

| Metric | CELF | Naive Greedy (estimated) |
|--------|------|--------------------------|
| Total MC evaluations | 10,303 | ~197,500 (9,875 × 20) |
| Evaluation reduction | — | ~95% fewer with CELF |
| Avg evaluations/step | 515.2 | 9,875 |
| Running time | 239.1s | ~4,700s (estimated) |
| Final spread (k=20) | 528.41 | same (identical seeds) |

**CELF used only 428 recomputations across all 20 steps after initialization** — confirming the lazy-forward optimization works as described.

### Seed Set Selected (k=20)
```
[19615, 1441, 63113, 30744, 23420, 33512, 44262, 48973, 40517, 63697,
 29715, 23282, 30160, 14017, 24394, 3423, 28950, 3624, 41687, 66135]
```

---

## Paper's Reported Results (k=100, 10,000 MC runs)

| Dataset | CELF time (min) | Avg lookups/step |
|---------|----------------|-----------------|
| HeptWC  | 245 | 18.7 |
| HeptIC  | 5,269 | 190.5 |
| PhyWC   | 1,241.6 | 18.6 |

The IC uniform setting (p=0.1) is much slower because higher propagation probabilities mean more nodes have non-trivial marginal gains, requiring more recomputations per step.

---

## Our Results vs Paper

| Metric | Paper (k=100, 10k runs) | Ours (k=20, 1k runs) |
|--------|------------------------|----------------------|
| Dataset | NetHEPT-WC | NetHEPT-WC |
| Avg lookups/step | 18.7 | 515.2* |
| Evaluation reduction vs Greedy | ~99% | ~95% |
| CELF behavior | Lazy-forward confirmed | Lazy-forward confirmed ✓ |

*Our higher avg/step is because the 9,875 initialization cost is amortized over only 20 steps instead of 100. The per-step recomputation count (2–106) is consistent with the paper's lazy-forward behavior.

---

## References

- Leskovec J., Krause A., Guestrin C., Faloutsos C., VanBriesen J., Glance N. (2007). Cost-effective outbreak detection in networks. *KDD 2007*, 420–429.
- Kempe D., Kleinberg J., Tardos É. (2003). Maximizing the spread of influence through a social network. *KDD 2003*, 137–146.
- Goyal A., Lu W., Lakshmanan L.V.S. (2011). CELF++: Optimizing the Greedy Algorithm for Influence Maximization in Social Networks. *WWW 2011 Poster*.
