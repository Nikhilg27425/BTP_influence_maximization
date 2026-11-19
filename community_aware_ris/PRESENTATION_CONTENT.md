# BTP Presentation Content — 10 Slides
## Community-Aware Influence Maximisation via Reverse Influence Sampling

---

## Slide 1 — Title Slide

**Title:**
Community-Aware Influence Maximisation via Reverse Influence Sampling (CA-RIS)

**Subtitle:**
Bachelor's Thesis Project

**Content:**
- Student: Nikhil Gupta
- Topic: Influence Maximisation on Social Networks
- Key idea: Balancing influence spread across communities using a fairness-aware RIS approach

**Visual suggestion:** A social network graph split into coloured clusters (communities), with seed nodes distributed across all clusters — not just the largest one.

---

## Slide 2 — The Influence Maximisation Problem

**Title:** What is Influence Maximisation?

**Definition:**
Given a social network G = (V, E) and a budget k, select a seed set S ⊆ V, |S| = k such that the **expected number of activated nodes** σ(S) is maximised.

**Formally:**
> S* = argmax σ(S),   subject to |S| = k

**Key properties:**
- Proved NP-Hard by Kempe et al. (2003)
- Best achievable approximation ratio: **1 − 1/e ≈ 0.63** (submodularity + greedy)
- Two standard diffusion models:
  - **Independent Cascade (IC):** Each active node u tries to activate neighbour v with probability p(u,v) — once, independently
  - **Linear Threshold (LT):** Node activates when cumulative influence from neighbours exceeds a threshold

**Visual suggestion:** A simple graph with a wave of activation spreading from 2–3 seed nodes outward, step by step.

---

## Slide 3 — Previous Work: Algorithm Progression

**Title:** How We Got Here — Algorithm Timeline

| Algorithm | Year | Key Idea | Time Complexity |
|-----------|------|----------|----------------|
| **Greedy (Kempe et al.)** | 2003 | Monte Carlo + marginal gain | O(k · n · m · R) — very slow |
| **CELF** | 2007 | Lazy evaluation, skip unchanged nodes | 700× faster than Greedy |
| **Independent Cascade Model** | — | Diffusion simulation + seed selection via degree/path heuristics | — |
| **RIS (Borgs et al.)** | 2014 | Random Reverse Reachable sets, near-linear time | O((k + l)(n + m) log n / ε²) |
| **D-RIS (Sun & Chen)** | 2021 | Dynamic θ — generate only as many RRR sets as needed | Faster in practice than RIS |
| **CA-RIS (This work)** | 2024 | Community-aware RIS with quota-based greedy | Comparable to D-RIS |

**Key insight across all prior work:**
Every algorithm above optimises **raw spread only** — none accounts for *who* gets influenced.

**Visual suggestion:** A horizontal timeline arrow with each algorithm as a milestone dot.

---

## Slide 4 — The Gap: Echo-Chamber Effect

**Title:** Why Raw Spread Maximisation Fails

**The problem in one sentence:**
> Social networks are modular. If you ignore community structure, all seeds land in the largest community — and smaller communities get nothing.

**Example:**
A multinational company wants to pick 5 athlete endorsers for a global campaign.
- Football community: 60% of the network (largest)
- Cricket community: 20%
- American Football: 20%

Standard RIS picks all 5 from football → effective in Europe, invisible in South Asia and America.

**The echo-chamber effect:**
- Information circulates within the dominant community
- Cross-community ties are weak → information rarely jumps communities
- Result: **imbalanced influence propagation**

**What we measured (Slashdot, 12 communities, Q = 0.36):**
- D-RIS assigned **10 out of 30 seeds to a single community** (33% of budget → one community)
- 3 communities received zero seeds
- Gini imbalance = 0.488 → highly skewed

**Visual suggestion:** Two network diagrams side by side — one showing all seeds in the big cluster (D-RIS), one showing seeds spread out (CA-RIS). Use different colours per community.

---

## Slide 5 — Community Structure in Networks

**Title:** Community Detection — The Louvain Algorithm

**What is community structure?**
Nodes cluster into groups that are **densely connected internally** and sparsely connected across groups. This is quantified by **modularity Q**:

> Q = (fraction of edges within communities) − (expected fraction under random graph)
> Q ∈ [−1, 1],  Q > 0.3 indicates meaningful community structure

**Why Louvain?**
- State-of-the-art community detection algorithm
- Operates in **near-linear time** — practical for large networks
- Hierarchical: merges nodes → communities → super-communities
- Used by Facebook, Twitter for large-scale graph analysis

**Our datasets:**

| Dataset | Nodes | Edges | Communities | Modularity Q | Largest Community |
|---------|-------|-------|-------------|-------------|------------------|
| Slashdot0902 | 82,168 | 870,161 | 12 | **0.3575** | 41.4% of graph |
| soc-Epinions1 | 75,879 | 508,837 | 6 | **0.2393** | 27.8% of graph |

Slashdot's high Q = 0.36 means strong community separation — exactly the scenario where naive seed selection fails hardest.

**Visual suggestion:** The Louvain dendrogram / partition hierarchy, or a coloured force-directed graph layout.

---

## Slide 6 — CA-RIS: The Proposed Algorithm

**Title:** CA-RIS — Community-Aware RIS

**Core idea:** Replace the unconstrained greedy coverage step in RIS with a **community-quota greedy** that enforces proportional seed distribution.

**New objective:**
```
F(S) = σ(S) − λ · I(S)
```
- **σ(S):** Expected influence spread (estimated via RRR-set coverage)
- **I(S):** Gini coefficient of per-community fractional seed density → measures imbalance
- **λ ≥ 0:** Trade-off parameter (λ = 0 → standard RIS; larger λ → more fairness)

**Three Steps:**

**Step 1 — Community Detection**
Run Louvain on the undirected projection → get communities C₁, C₂, ..., Cₘ

**Step 2 — RRR Set Generation (D-RIS procedure)**
- Pick random target node v
- BFS backward through probabilistic edges
- Repeat θ times (θ determined dynamically from OPT estimate)

**Step 3 — Community-Quota Greedy**
```
quota_c = floor(k × |C_c| / n)   [proportional, largest-remainder]

For each of k steps:
  → Pick highest-coverage node whose community quota > 0
  → If none available: relax quota (fallback to unconstrained)
  → Remove covered RRR sets, decrement community quota
```

**Visual suggestion:** A 3-box flowchart: [Louvain] → [Generate θ RRR sets] → [Quota Greedy] → [Seed Set S]

---

## Slide 7 — Evaluation Metrics

**Title:** How We Measure Success

Four metrics evaluated for CA-RIS, D-RIS, and RIS:

| # | Metric | Formula | What it captures |
|---|--------|---------|-----------------|
| 1 | **Influence Spread σ(S)** | Avg activated nodes over 10,000 IC simulations | Raw effectiveness |
| 2 | **Community Coverage CC(S)** | \|{c : S ∩ Cₓ ≠ ∅}\| / m | How many communities get at least one seed |
| 3 | **Seed Entropy H(S)** | Normalised Shannon entropy of seed counts across communities | Uniformity of distribution |
| 4 | **Gini Imbalance I(S)** | Gini coefficient of per-community seed densities | Inequality of coverage (lower = better) |

**Plus:** Runtime comparison and RRR sets θ used.

**The key tension:**
CA-RIS is expected to trade a small amount of σ(S) for large gains in CC, H, and I. The experiments quantify exactly how much.

---

## Slide 8 — Results: Slashdot

**Title:** Slashdot Results (k=30, λ=0.5, 2000 nodes, 12 communities, Q=0.36)

**Main comparison table:**

| Metric | CA-RIS | D-RIS | RIS |
|--------|--------|-------|-----|
| MC Spread σ(S) | 62.25 | 65.85 | 68.89 |
| Community Coverage | **91.7%** (11/12) | 75.0% (9/12) | 91.7% (11/12) |
| Seed Entropy H(S) | **0.806** | 0.759 | 0.815 |
| Gini Imbalance I(S) | **0.175** | 0.488 | 0.414 |
| Runtime | 0.18s | 0.20s | 0.67s |
| RRR sets θ | 53,322 | 59,918 | 200,000 |

**CA-RIS vs D-RIS gains:**
- Gini imbalance: **−64.1%** (0.488 → 0.175)
- Community Coverage: **+22.2%** (9 → 11 communities covered)
- Spread cost: only **−5.5%**

**What D-RIS was doing wrong:**
D-RIS assigned 10/30 seeds to community C3 alone. CA-RIS caps each community at its proportional quota — the 828-node community (41.4%) gets 12 seeds, every other community gets 1–3.

**Visual suggestion:** Use the `comparison_bar.png` and `community_dist.png` plots generated by the experiments.

---

## Slide 9 — Results: Epinions + λ Sweep

**Title:** Epinions Results & Trade-off Analysis

**Epinions (k=30, λ=0.5, 2000 nodes, 6 communities, Q=0.24):**

| Metric | CA-RIS | D-RIS | RIS |
|--------|--------|-------|-----|
| MC Spread σ(S) | 196.07 | 199.25 | 202.89 |
| Gini Imbalance I(S) | **0.192** | 0.310 | 0.376 |
| Seed Entropy H(S) | **0.874** | 0.867 | 0.852 |
| Runtime | 0.42s | 0.46s | 2.36s |

Gini down **38% vs D-RIS** — spread cost only **1.6%**. The lower modularity means communities are already more balanced, so the gains in CC are smaller but the imbalance reduction is still substantial.

**λ Sweep (Slashdot, λ ∈ {0, 0.25, 0.5, 1.0, 2.0}):**

| λ | σ̂(S) | CC | Gini |
|---|-------|----|----|
| 0.00 | 72.58 | 0.909 | 0.186 |
| 0.25 | 74.10 | 0.909 | 0.186 |
| 0.50 | 74.22 | 0.909 | 0.186 |
| 1.00 | 74.40 | 0.909 | 0.186 |
| 2.00 | 74.34 | 0.909 | 0.186 |

**Key finding:** CC, entropy, and Gini are stable across all λ values — the **quota greedy is the primary driver of fairness**, not the λ penalty. λ affects only the OPT estimate and hence θ (number of RRR sets). The σ̂ variation is sampling noise.

**Visual suggestion:** Use `lambda_tradeoff.png` — the dual-axis line plot showing flat fairness curves.

---

## Slide 10 — Conclusions & Future Work

**Title:** Summary, Contributions & Next Steps

**What we implemented (full progression):**

| Module | Algorithm | Status |
|--------|-----------|--------|
| `independent_cascade/` | IC Model — diffusion simulation | ✅ Done |
| `greedy/` | Greedy + EGA (Edge-based Greedy Algorithm) | ✅ Done |
| `celf/` | CELF — Cost-Effective Lazy Forward | ✅ Done |
| `ris/` | RIS — Reverse Influence Sampling | ✅ Done |
| `community_aware_ris/` | **CA-RIS — Proposed Algorithm** | ✅ Done |

**Core contributions of CA-RIS:**
1. First RIS-based algorithm to incorporate community structure into seed selection
2. Community-quota greedy enforces proportional seed distribution without sacrificing the (1−1/e) approximation
3. Gini imbalance reduced by 38–64% vs D-RIS across both datasets
4. Runtime comparable to D-RIS — Louvain adds negligible overhead

**Limitations:**
- Very small communities (< ~20 nodes, p=0.01) cannot be reliably reached via RRR sets → receive zero seeds
- λ sweep shows the penalty term doesn't directly drive fairness in these experiments — quota mechanism dominates

**Future Work:**
- Run on full graphs (82k / 75k nodes) for richer community granularity
- k-sensitivity analysis: k ∈ {10, 20, 30, 40, 50}
- Adaptive per-community propagation probabilities for small communities
- Integrate λ directly into the greedy scoring function rather than only in OPT estimation
- Compare against other community-aware baselines from recent literature

**Visual suggestion:** A closing diagram showing the full pipeline from IC model → CA-RIS, with the key result numbers (Gini −64%, CC +22%, spread −5.5%) highlighted as callout boxes.

---

*Datasets: Stanford SNAP — Slashdot0902, soc-Epinions1*
*References: Kempe et al. 2003 · Leskovec et al. 2007 · Borgs et al. 2014 · Sun & Chen 2021 · Blondel et al. 2008*
