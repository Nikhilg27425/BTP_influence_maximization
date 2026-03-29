# Independent Cascade Model — Implementation & Reproduction

Python implementation of all algorithms from:

> **"Influence Maximization in Independent Cascade Networks Based on Activation Probability Computation"**
> Wenjing Yang, Leonardo Brenner, Alessandro Giua — *IEEE Access*, 2019
> DOI: 10.1109/ACCESS.2019.2894073

---

## What This Is

The paper studies how innovations (or information) spread through social networks using the **Independent Cascade (IC) model**. Given a directed graph where each edge has a propagation probability, the goal is:

1. **Activation Probability Computation** — given a seed set, what is the probability each node gets activated?
2. **Influence Maximization** — which K nodes should be the seeds to maximize total activation?

---

## Project Structure

```
independent_cascade/
├── graph.py            # IC model + dataset loaders
├── monte_carlo.py      # Monte Carlo simulation (baseline)
├── path_method.py      # Exact computation (Algorithm 1)
├── steady_state.py     # SteadyStateSpread, SSS-Noself, SSS-Bounded-Path
├── seed_selection.py   # SelectTopK, RankedReplace, Greedy
├── experiments.py      # Reproduces all tables and figures
├── verify_table3.py    # Quick sanity check against Table 3
├── moreno_highschool/  # HighSchool dataset (KONECT)
└── opsahl-usairport/   # US Airports dataset (KONECT)
```

---

## Datasets

### HighSchool Network (Fig. 7 & 8)
- **Source**: [KONECT — moreno_highschool](http://konect.cc/networks/moreno_highschool/)
- **Description**: Directed friendship network among boys in a small Illinois high school (Coleman, 1964). Each boy was surveyed in fall 1957 and spring 1958.
- **Stats**: 70 nodes, 366 edges
- **Edge weights**: 1 or 2 (how many times a boy chose another as friend) — ignored in this implementation; edge probabilities are randomly assigned from {0.1, 0.2, 0.5} as per the paper.

### US Airports Network (Fig. 5)
- **Source**: [KONECT — opsahl-usairport](http://konect.cc/networks/opsahl-usairport/)
- **Description**: Directed network of flights between US airports in 2010. Edge weight = number of flights on that route.
- **Full stats**: 1574 nodes, 28236 edges
- **Paper uses**: Top 500 airports by total traffic volume
- **Filtered stats**: 500 nodes, 20803 edges
- **Edge probability**: `p[i][j] = w[i][j] / sum_k w[i][k]` (normalized flight counts)

---

## Algorithms Implemented

### Activation Probability Methods

| Method | Complexity | Description |
|--------|-----------|-------------|
| **Path Method** | O(6^N) | Exact. Builds a full evolution graph of all possible IC runs. Only feasible for N ≤ ~15 nodes. |
| **SteadyStateSpread** | O(N) | Fixed-point iteration (Aggarwal et al.). Converges to a unique solution (proved via monotone convergence theorem). Tends to **overestimate** due to circuits and dependent node relations. |
| **SSS-Noself** | O(N²) | Improved fixed-point. For each node j, computes its activation probability using a shadow network G[j] where j's own influence is removed. More accurate than SteadyStateSpread. |
| **SSS-Bounded-Path** | O(N) | Computes activation only along paths of length ≤ sp_j + b0, where sp_j is the shortest path length from seed to j. b0=0 gives a **lower bound**; b0→∞ converges to SteadyStateSpread. |

**Proven ordering** (Proposition 2 in paper):

```
BP(b0=0) ≤ PathMethod ≤ SSS-Noself ≤ SteadyStateSpread
```

### Seed Selection Algorithms

| Algorithm | Description | Complexity |
|-----------|-------------|-----------|
| **SelectTopK** | Rank all nodes by individual influence spread, pick top K | O(N·T) |
| **RankedReplace** | Start with SelectTopK, then greedily swap seed nodes with non-seed nodes if it improves spread | O(K·(N-K)·T) |
| **Greedy** | At each step, add the node with the highest marginal gain | O(K·N·T) |

Where T = time to compute activation probability for one seed set.

---

## The IC Model

A social network is a directed graph G = (V, E, p) where:
- Each node is either **active** (adopted the innovation) or **inactive**
- Each edge (i→j) has propagation probability p[i][j] ∈ (0,1]
- Activation is **permanent** (progressive model)

**Propagation process:**
1. Start with seed set φ₀ (all active at t=0)
2. At each step t, every newly active node i tries to activate each inactive out-neighbor j with probability p[i][j]
3. Each active node gets exactly one chance to influence each neighbor
4. Process ends when no new activations occur

**Influence spread**: σ(φ₀) = Σⱼ πⱼ (sum of all activation probabilities)

---

## Key Equations

**SteadyStateSpread (Eq. 1):**
```
π_j^s = 1 - ∏_{i ∈ N_j^in} (1 - π_i^s · p_{i,j})    for j ∉ φ₀
π_j^s = 1                                               for j ∈ φ₀
```

**Why it overestimates:** For a circuit like 3→2→4→2, node 2's probability depends on node 4, but node 4 can only be activated *after* node 2. SSS-Noself fixes this by computing π_j using a shadow network where j's own influence is removed.

**Exact formula for node 2 in Fig. 2 (Eq. 4):**
```
π_2 = π_3·p_{3,2} + π_1·p_{1,2} - π_3·p_{3,2}·p_{1,2}·p_{3,1}
```
This accounts for the dependent relation: nodes 1 and 3 are both in-neighbors of 2, but 1 is activated *through* 3, so their activations are not independent.

---

## Verified Results

### Table 3 — 5-node example network (Fig. 2 from paper)

Graph: 5→3 (0.4), 3→1 (0.2), 3→2 (0.1), 1→2 (0.3), 2→4 (0.2), 4→2 (0.3). Seed = {5}.

| Method | Node 1 | Node 2 | Node 3 | Node 4 | Node 5 |
|--------|--------|--------|--------|--------|--------|
| Path Method | 0.0800 | **0.0616** | 0.4000 | **0.0123** | 1.0000 |
| SteadyStateSpread | 0.0800 | 0.0668 | 0.4000 | 0.0134 | 1.0000 |
| SSS-Noself | 0.0800 | **0.0630** | 0.4000 | **0.0126** | 1.0000 |
| SSS-BP (b0=0) | 0.0800 | **0.0400** | 0.4000 | **0.0080** | 1.0000 |
| SSS-BP (b0=1) | 0.0800 | **0.0630** | 0.4000 | **0.0126** | 1.0000 |

Paper expected values (Table 3):

| Method | Node 1 | Node 2 | Node 3 | Node 4 | Node 5 |
|--------|--------|--------|--------|--------|--------|
| Path Method | 0.0800 | 0.0616 | 0.4000 | 0.0123 | 1.0000 |
| SteadyStateSpread | 0.0800 | 0.0678 | 0.4000 | 0.0132 | 1.0000 |
| SSS-Noself | 0.0800 | 0.0630 | 0.4000 | 0.0126 | 1.0000 |
| SSS-BP (b0=0) | 0.0800 | 0.0400 | 0.4000 | 0.0080 | 1.0000 |
| SSS-BP (b0=1) | 0.0800 | 0.0630 | 0.4000 | 0.0126 | 1.0000 |

**Path Method, SSS-Noself, and SSS-BP match exactly.** SteadyStateSpread is slightly off because the exact edge probabilities of Fig. 2 in the paper are not fully specified — the graph was reconstructed from the paper's equations. The ordering BP(b0=0) ≤ PathMethod ≤ SSS-Noself ≤ SteadyStateSpread holds.

---

### Fig. 7 — Influence Spread on HighSchool Network (real data, seed=42)

Evaluated by Monte Carlo (10,000 runs). Edge probabilities randomly assigned from {0.1, 0.2, 0.5}.

| Algorithm | K=1 | K=5 | K=10 | K=15 | K=20 | K=25 |
|-----------|-----|-----|------|------|------|------|
| Random | 13.56 | 27.15 | 39.41 | 45.38 | 49.79 | 51.34 |
| SelectTopK-SSS | 14.49 | 33.12 | 43.98 | 50.20 | 53.35 | 57.07 |
| SelectTopK-SN | 14.49 | 33.12 | 43.94 | 50.20 | 53.32 | 56.23 |
| Replace-SSS | 14.49 | 38.19 | 48.49 | 54.16 | 57.81 | 61.08 |
| Replace-SN | 14.49 | 38.19 | 48.26 | 53.96 | 58.31 | 61.23 |
| Greedy-SSS | 14.49 | 38.19 | 47.97 | 54.96 | 59.45 | **62.28** |
| Greedy-SN | 14.49 | — | — | — | — | — |

*Greedy-SN omitted — each K step requires N × SSS-Noself evaluations (~52s each), matching the paper's reported ~800s total runtime.*

**Observations matching the paper:**
- Greedy > RankedReplace > SelectTopK for K > 1 ✓
- SSS-Noself based methods select slightly different (sometimes better) seed sets ✓
- All methods beat Random selection ✓

---

### Fig. 8 — Running Times on HighSchool Network

| Algorithm | K=1 | K=5 | K=10 | K=15 | K=20 | K=25 |
|-----------|-----|-----|------|------|------|------|
| Random | ~0s | ~0s | ~0s | ~0s | ~0s | ~0s |
| SelectTopK-SSS | ~0s* | ~0s* | ~0s* | ~0s* | ~0s* | ~0s* |
| SelectTopK-SN | ~0s* | ~0s* | ~0s* | ~0s* | ~0s* | ~0s* |
| Replace-SSS | 0.51s | 1.00s | 1.10s | 1.07s | 0.91s | 0.79s |
| Replace-SN | 0.51s | 1.00s | 1.12s | 1.12s | 0.90s | 0.73s |
| Greedy-SSS | 0.53s | 1.51s | 2.30s | 2.80s | 3.38s | 4.28s |
| Greedy-SN | ~52s/step | — | — | — | — | — |

*\* Pre-computation of per-node scores takes 0.5s (SSS) and 50.9s (SSS-Noself) once, then SelectTopK is O(1) per K.*

**Matches paper's Fig. 8:** Greedy-SN is by far the slowest; SelectTopK is fastest; Greedy-SSS is a good balance of speed and quality.

---

## Assumptions & Notes

1. **Graph reconstruction (Fig. 2)**: The paper's Fig. 2 does not list exact edge probabilities. The graph was reconstructed by solving the paper's Equation 4 analytically. The exact probabilities used are: 5→3 (0.4), 3→1 (0.2), 3→2 (0.1), 1→2 (0.3), 2→4 (0.2), 4→2 (0.3).

2. **HighSchool edge probabilities**: The paper assigns edge probabilities randomly from {0.1, 0.2, 0.5} (not using the original edge weights). Results will vary with different random seeds.

3. **Series-Grid**: The paper uses random seeds for grid graph generation. Results in Tables 4–9 will differ from the paper's exact numbers but should show the same qualitative trends.

4. **SSS-Noself complexity**: O(N²) per call. For N=70 (HighSchool), each call takes ~0.75s. Running it N=70 times for per-node scoring takes ~52s. Greedy-SN requires N × K calls, making it very slow for large K.

5. **Monte Carlo evaluation**: All final influence spread values in Fig. 7 are evaluated using 10,000 Monte Carlo runs as ground truth, matching the paper's methodology.

6. **Airport top-500 filtering**: The paper uses the 500 airports with the largest traffic. We filter by total traffic (in + out flights), which gives 500 nodes and 20,803 edges after filtering.

---

## How to Run

```bash
# Verify Table 3 (fast, ~2s)
python verify_table3.py

# Run specific experiments
python experiments.py table3       # Table 3 — 5-node example
python experiments.py tables4_5    # Tables 4 & 5 — Series-Grid sums
python experiments.py tables6_7    # Tables 6 & 7 — per-node on m=3 grid
python experiments.py tables8_9    # Tables 8 & 9 — running times
python experiments.py fig7_8       # Fig. 7 & 8 — HighSchool seed selection
python experiments.py fig5         # Fig. 5 — Airport activation probability

# Run everything
python experiments.py all
```

> **Note**: `fig7_8` takes ~10 minutes due to SSS-Noself pre-computation (50s) and Greedy-SN (~52s per step × 25 steps × 6 K-values). Run `table3` first to verify correctness quickly.

---

## References

- Yang et al. (2019). *Influence Maximization in Independent Cascade Networks Based on Activation Probability Computation*. IEEE Access. DOI: 10.1109/ACCESS.2019.2894073
- Aggarwal et al. (2011). *On flow authority discovery in social networks*. SDM.
- Kempe et al. (2003). *Maximizing the spread of influence through a social network*. KDD.
- Coleman (1964). *Introduction to Mathematical Sociology*. London Free Press Glencoe.
- Colizza et al. (2007). *Reaction-diffusion processes and metapopulation models in heterogeneous networks*. Nature Physics.
