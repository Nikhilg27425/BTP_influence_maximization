# Community-Aware RIS (CA-RIS) — Proposed Algorithm

Python implementation of the **CA-RIS** algorithm, the proposed research
contribution of this BTP project.  CA-RIS extends the D-RIS framework
(Sun & Chen 2021) with community-structure awareness to achieve balanced
influence propagation across all communities in a social network.

---

## Motivation

Standard RIS and D-RIS maximise raw influence spread σ(S).  Because real
social networks are **modular** (nodes cluster into dense communities), the
greedy seed selection concentrates all k seeds in the largest community —
creating an **echo-chamber effect** where small communities receive little
or no influence.

> *"In many scenarios — such as public health campaigns or global product
> marketing — reaching all communities is more important than maximising
> raw spread alone."*

---

## Proposed Objective

Instead of optimising only spread, CA-RIS introduces a fairness–spread
trade-off:

```
F(S) = σ(S) − λ · I(S)
```

| Symbol | Meaning |
|--------|---------|
| σ(S)  | Expected influence spread, estimated via RRR-set coverage |
| I(S)  | Imbalance measure — Gini coefficient of per-community fractional seed density |
| λ ≥ 0 | Trade-off parameter.  λ=0 → standard RIS; larger λ → more fairness |

---

## Algorithm — Three Steps

### Step 1 — Community Detection (Louvain)
Detect communities using the Louvain algorithm, which maximises the
modularity Q.  The directed graph is projected to undirected for detection
(standard practice).

```
node_to_community, community_to_nodes, Q = louvain(G)
```

### Step 2 — RRR Set Generation (D-RIS procedure)
Generate θ Random Reverse Reachable (RRR) sets using the D-RIS dynamic
θ-determination strategy:

```
1. θ_0 = n · ln(n) / k                    # initial estimate
2. Generate θ_0 RRR sets
3. Estimate OPT from coverage fraction
4. Recompute θ = n(8+2ε)(l·ln n + ln C(n,k) + ln 2) / (ε² · OPT_est)
5. Generate additional sets if θ_new > |R|
```

### Step 3 — Community-Quota Greedy Coverage
Enforce balanced seed distribution via per-community quotas:

```
q_c = floor(k · |C_c| / n)   (largest-remainder for exact sum = k)

For i = 1..k:
  u* = argmax coverage(u)  subject to  quota(community(u)) > 0
  if no quota-eligible node:
      relax constraint (quota-relaxation rule)
      u* = argmax coverage(u)   # unconstrained
  S.append(u*)
  R = R \ { RRR ∈ R : u* ∈ RRR }
  quota[community(u*)] -= 1
```

> If a community cannot meet its quota due to sparse RRR coverage, the
> constraint is relaxed to maintain competitive overall spread.

---

## Evaluation Metrics

| # | Metric | Definition |
|---|--------|-----------|
| 1 | **Influence Spread σ(S)** | Average activated nodes over MC simulations |
| 2 | **Community Coverage CC(S)** | \|{c : S ∩ C_c ≠ ∅}\| / m |
| 3 | **Seed Distribution Entropy H(S)** | Normalised Shannon entropy of seed counts |
| 4 | **Runtime** | Wall-clock time vs RIS / D-RIS |

Imbalance I(S) = Gini coefficient of {|S ∩ C_c| / |C_c|} across all communities.

---

## Project Structure

```
community_aware_ris/
├── graph.py          # Graph loader (SNAP format) + Louvain community detection
├── algorithms.py     # CA-RIS, D-RIS baseline, RIS baseline, fairness metrics
├── monte_carlo.py    # IC simulation for spread evaluation
├── experiments.py    # Experiment runner + λ-sweep + CLI
├── data/
│   ├── Slashdot0902.txt   → symlink to ris/data/
│   └── soc-Epinions1.txt  → symlink to ris/data/
└── README.md
```

---

## Dependencies

```bash
pip install python-louvain networkx
```

`python-louvain` is imported as `community` (the package name on PyPI is
`python-louvain`; the import is `import community`).

> **Fallback**: if `python-louvain` is not installed, the code automatically
> falls back to a built-in label-propagation algorithm.  The fallback is
> sufficient for testing but less accurate than Louvain for final experiments.

---

## How to Run

```bash
cd community_aware_ris/

# Quick test — 2000-node subgraph, k=20 seeds, λ=0.5
python experiments.py slashdot --sub 2000 --k 20

# Full run on Epinions, k=50, λ=0.5 (default), skip MC for speed
python experiments.py epinions --k 50 --no-mc

# λ trade-off sweep (shows spread vs fairness for λ ∈ {0, 0.25, 0.5, 1, 2})
python experiments.py slashdot --sub 2000 --k 20 --lambda-sweep

# Both datasets
python experiments.py all --k 50 --lam 0.5

# Custom λ
python experiments.py slashdot --sub 3000 --k 30 --lam 1.0
```

| Flag | Default | Description |
|------|---------|-------------|
| `--k N` | 50 | Seed set size |
| `--lam F` | 0.5 | λ fairness parameter |
| `--eps F` | 0.5 | Approximation parameter ε |
| `--sub N` | — | Subsample N nodes (BFS) for quick testing |
| `--no-mc` | — | Skip Monte Carlo spread evaluation |
| `--lambda-sweep` | — | Run λ ∈ {0, 0.25, 0.5, 1.0, 2.0} sweep |

---

## Expected Results

CA-RIS is expected to show the following trade-offs compared to D-RIS:

| Metric | CA-RIS vs D-RIS |
|--------|----------------|
| Influence Spread σ(S) | Slightly lower (spread–fairness trade-off) |
| Community Coverage CC(S) | **Significantly higher** (key contribution) |
| Seed Entropy H(S) | **Higher** (more uniform distribution) |
| Gini Imbalance I(S) | **Lower** (more balanced) |
| Runtime | Comparable (Louvain runs in near-linear time) |

The λ parameter controls the trade-off — λ=0 recovers standard RIS behaviour,
larger λ increases fairness at the cost of some raw spread.

---

## Datasets

Both from [Stanford SNAP](https://snap.stanford.edu/data/index.html):

| Dataset | Nodes | Edges | Description |
|---------|-------|-------|-------------|
| Slashdot0902 | 82,168 | 948,464 | Slashdot social network (Feb 2009) |
| soc-Epinions1 | 75,879 | 508,837 | Directed Epinions trust network |

Both datasets exhibit strong community structure (high modularity Q),
making them ideal benchmarks for community-aware algorithms.

---

## References

- [2]  Blondel V.D. et al. (2008). Fast unfolding of communities in large networks.
       *J. Stat. Mech.*, P10008.
- [3]  Borgs C. et al. (2014). Maximizing Social Influence in Nearly Optimal Time.
       *SODA 2014*.
- [6]  Gleeson J.P. et al. (2014). Competition-induced criticality. *Phys. Rev. Lett.*
       (echo-chamber effect)
- [12] Fortunato S. (2010). Community detection in graphs. *Phys. Rep.*, 486, 75–174.
- [14] Sun G., Chen C. (2021). Influence Maximization via Reverse Reachable Set.
       *Math. Problems in Engineering*, Hindawi.
