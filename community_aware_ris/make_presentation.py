"""
Generates PRESENTATION.pptx for the CA-RIS BTP project.
Run with:  .venv/bin/python community_aware_ris/make_presentation.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BG   = RGBColor(0x0d, 0x1b, 0x2a)
BLUE      = RGBColor(0x1a, 0x73, 0xe8)
ACCENT    = RGBColor(0xf4, 0xa2, 0x61)
GREEN     = RGBColor(0x2e, 0xcc, 0x71)
RED       = RGBColor(0xe7, 0x4c, 0x3c)
WHITE     = RGBColor(0xff, 0xff, 0xff)
LIGHT_GREY= RGBColor(0xcc, 0xcc, 0xcc)
MID_GREY  = RGBColor(0x88, 0x88, 0x88)
CARD_BG   = RGBColor(0x14, 0x2a, 0x40)
HEADER_BG = RGBColor(0x0a, 0x14, 0x1e)
PURPLE    = RGBColor(0x9b, 0x59, 0xb6)

W  = Inches(13.33)   # widescreen 16:9
H  = Inches(7.5)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

BLANK = prs.slide_layouts[6]   # completely blank layout

# ── Helpers ────────────────────────────────────────────────────────────────────

def add_slide():
    return prs.slides.add_slide(BLANK)

def bg(slide, color=DARK_BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color

def box(slide, x, y, w, h, fill=None, line=None, line_color=None):
    shape = slide.shapes.add_shape(1, x, y, w, h)   # MSO_SHAPE_TYPE.RECTANGLE = 1
    shape.line.fill.background() if line is None else None
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(line if line else 1)
    else:
        shape.line.fill.background()
    return shape

def txt(slide, text, x, y, w, h, size=18, bold=False, color=WHITE,
        align=PP_ALIGN.LEFT, wrap=True, italic=False):
    txb = slide.shapes.add_textbox(x, y, w, h)
    tf  = txb.text_frame
    tf.word_wrap = wrap
    p   = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.color.rgb = color
    run.font.italic = italic
    return txb

def card(slide, x, y, w, h, fill=CARD_BG, line_color=None):
    s = slide.shapes.add_shape(1, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line_color:
        s.line.color.rgb = line_color
        s.line.width = Pt(1)
    else:
        s.line.fill.background()
    return s

def htxt(slide, text, x, y, w, h, size=18, bold=False, color=WHITE, align=PP_ALIGN.LEFT, italic=False):
    """Multi-paragraph helper — split on \n."""
    txb = slide.shapes.add_textbox(x, y, w, h)
    tf  = txb.text_frame
    tf.word_wrap = True
    lines = text.split('\n')
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.size  = Pt(size)
        run.font.bold  = bold
        run.font.italic = italic
        run.font.color.rgb = color
    return txb

def slide_num_label(slide, n, total=10):
    txt(slide, f"Slide {n} / {total}", Inches(11.8), Inches(7.1),
        Inches(1.4), Inches(0.3), size=9, color=MID_GREY, align=PP_ALIGN.RIGHT)

def section_line(slide, y=Inches(1.15)):
    ln = slide.shapes.add_shape(1, Inches(0.5), y, Inches(12.33), Pt(2))
    ln.fill.solid(); ln.fill.fore_color.rgb = BLUE
    ln.line.fill.background()

def tag_pill(slide, text, x, y, fill=BLUE, text_color=WHITE):
    b = card(slide, x, y, Inches(2.0), Inches(0.32), fill=fill)
    txt(slide, text, x + Inches(0.08), y + Inches(0.04),
        Inches(1.9), Inches(0.28), size=9, color=text_color,
        bold=True, align=PP_ALIGN.CENTER)

def table_header(slide, cols, x, y, col_widths, row_h=Inches(0.38)):
    cur_x = x
    for i, (col, cw) in enumerate(zip(cols, col_widths)):
        c = card(slide, cur_x, y, cw, row_h, fill=BLUE)
        txt(slide, col, cur_x + Inches(0.06), y + Inches(0.08),
            cw - Inches(0.1), row_h - Inches(0.1),
            size=10, bold=True, color=WHITE)
        cur_x += cw

def table_row(slide, vals, x, y, col_widths, row_h=Inches(0.35),
              fill=CARD_BG, colors=None):
    cur_x = x
    for i, (val, cw) in enumerate(zip(vals, col_widths)):
        c = card(slide, cur_x, y, cw, row_h, fill=fill)
        c_color = colors[i] if colors and i < len(colors) else LIGHT_GREY
        txt(slide, str(val), cur_x + Inches(0.06), y + Inches(0.07),
            cw - Inches(0.1), row_h - Inches(0.1),
            size=9.5, color=c_color)
        cur_x += cw

def hbar(slide, x, y, w, h, pct, fill=BLUE, label="", bg_color=None):
    # background track
    bg_c = bg_color or RGBColor(0x20, 0x35, 0x4a)
    bk = card(slide, x, y, w, h, fill=bg_c)
    # filled portion
    filled_w = max(Inches(0.05), int(w * pct / 100))
    fc = card(slide, x, y, filled_w, h, fill=fill)
    if label:
        txt(slide, label, x + Inches(0.05), y + Inches(0.02),
            w - Inches(0.1), h - Inches(0.04), size=8, color=WHITE, bold=True)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)

# Gradient-like accent rect on left
c1 = card(sl, 0, 0, Inches(0.18), H, fill=BLUE)

# BTP tag
tag_pill(sl, "Bachelor's Thesis Project · 2024", Inches(0.4), Inches(0.5),
         fill=RGBColor(0x1a, 0x40, 0x70))

# Main title
htxt(sl, "Community-Aware\nInfluence Maximisation\nvia Reverse Influence Sampling (CA-RIS)",
     Inches(0.4), Inches(1.1), Inches(7.8), Inches(2.4),
     size=34, bold=True, color=WHITE)

# Subtitle / description
htxt(sl,
     "Designing an influence maximisation algorithm that selects seed nodes\n"
     "distributed in a balanced way across all communities — achieving\n"
     "diverse propagation while maintaining competitive influence spread.",
     Inches(0.4), Inches(3.65), Inches(7.5), Inches(1.3),
     size=13, color=LIGHT_GREY)

# Student
txt(sl, "Nikhil Gupta", Inches(0.4), Inches(5.0), Inches(4), Inches(0.4),
    size=14, bold=True, color=ACCENT)

# Right side — stat chips
chip_data = [
    ("Proposed Algorithm",  "CA-RIS",             BLUE),
    ("Datasets",            "Slashdot · Epinions", BLUE),
    ("Key Result (Gini)",   "−64% vs D-RIS",       GREEN),
    ("Community Coverage",  "+22% vs D-RIS",       GREEN),
    ("Spread Cost",         "Only −5.5%",          ACCENT),
]
cx = Inches(8.8); cy = Inches(1.0)
for label, val, col in chip_data:
    c = card(sl, cx, cy, Inches(4.1), Inches(0.9),
             fill=RGBColor(0x14, 0x28, 0x40),
             line_color=col)
    txt(sl, label, cx+Inches(0.12), cy+Inches(0.05),
        Inches(3.9), Inches(0.3), size=8.5, color=MID_GREY)
    txt(sl, val,   cx+Inches(0.12), cy+Inches(0.42),
        Inches(3.9), Inches(0.4), size=14, bold=True, color=col)
    cy += Inches(1.05)

# Tags row
tags = [("Independent Cascade", BLUE), ("Louvain Detection", PURPLE),
        ("RIS / D-RIS", GREEN), ("Gini Fairness", ACCENT)]
tx = Inches(0.4); ty = Inches(5.6)
for t, col in tags:
    tag_pill(sl, t, tx, ty, fill=col)
    tx += Inches(2.15)

slide_num_label(sl, 1)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — PROBLEM DEFINITION
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "The Influence Maximisation Problem",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)

# Left column
card(sl, Inches(0.4), Inches(1.3), Inches(5.9), Inches(2.3), fill=CARD_BG)
txt(sl, "Formal Definition", Inches(0.55), Inches(1.38),
    Inches(5.6), Inches(0.35), size=12, bold=True, color=ACCENT)
htxt(sl,
     "Given a directed social network G = (V, E) and budget k,\n"
     "find a seed set S ⊆ V, |S| = k such that expected\n"
     "activated nodes σ(S) is maximised.",
     Inches(0.55), Inches(1.78), Inches(5.7), Inches(0.85), size=11, color=LIGHT_GREY)
# Formula box
c = card(sl, Inches(0.55), Inches(2.65), Inches(5.6), Inches(0.5),
         fill=RGBColor(0x0a, 0x20, 0x38), line_color=BLUE)
txt(sl, "S* = argmax  σ(S)   subject to  |S| = k",
    Inches(0.65), Inches(2.72), Inches(5.4), Inches(0.4),
    size=13, bold=True, color=RGBColor(0x90, 0xca, 0xf9),
    align=PP_ALIGN.CENTER)

card(sl, Inches(0.4), Inches(3.75), Inches(5.9), Inches(1.75), fill=CARD_BG)
txt(sl, "Why It's Hard", Inches(0.55), Inches(3.83),
    Inches(5.6), Inches(0.35), size=12, bold=True, color=ACCENT)
htxt(sl,
     "→  NP-Hard (Kempe et al. 2003) — exponential activation paths\n"
     "→  σ(S) requires Monte Carlo simulation to estimate\n"
     "→  Best approximation ratio: 1 − 1/e ≈ 0.632\n"
     "→  Guaranteed by submodularity + greedy selection",
     Inches(0.55), Inches(4.22), Inches(5.7), Inches(1.2), size=10.5, color=LIGHT_GREY)

# Right column — IC Model
card(sl, Inches(6.8), Inches(1.3), Inches(6.1), Inches(3.6), fill=CARD_BG)
txt(sl, "Independent Cascade (IC) Model", Inches(6.95), Inches(1.38),
    Inches(5.9), Inches(0.35), size=12, bold=True, color=ACCENT)
htxt(sl,
     "Each newly active node u attempts to activate neighbour v\n"
     "with probability p(u,v) — exactly once, independently.\n"
     "Process cascades in discrete rounds until no new activations.",
     Inches(6.95), Inches(1.78), Inches(5.9), Inches(0.75), size=10.5, color=LIGHT_GREY)

# Pseudocode box
c = card(sl, Inches(6.95), Inches(2.6), Inches(5.7), Inches(1.1),
         fill=RGBColor(0x07, 0x12, 0x1a), line_color=RGBColor(0x30, 0x50, 0x70))
htxt(sl,
     "while newly_active not empty:\n"
     "    for u in newly_active:\n"
     "        for v in neighbours(u):\n"
     "            if random() ≤ p(u,v):  activate(v)",
     Inches(7.05), Inches(2.68), Inches(5.5), Inches(1.0),
     size=9.5, color=RGBColor(0x90, 0xca, 0xf9))

txt(sl, "Linear Threshold (LT) Model", Inches(6.95), Inches(3.8),
    Inches(5.9), Inches(0.3), size=11, bold=True, color=ACCENT)
htxt(sl,
     "Node v has threshold θᵥ ~ Uniform[0,1]. Activates when the weighted\n"
     "sum of active neighbours exceeds θᵥ. Models peer pressure scenarios.",
     Inches(6.95), Inches(4.15), Inches(5.9), Inches(0.65), size=10.5, color=LIGHT_GREY)

# Bottom row — properties
props = [
    ("Monotone",    "Adding seeds never decreases σ(S)", GREEN),
    ("Submodular",  "Diminishing returns hold for all S,T", BLUE),
    ("(1−1/e) guarantee", "These two properties ensure greedy achieves 0.632×OPT", ACCENT),
]
px = Inches(0.4); py = Inches(5.6)
pw = Inches(4.1)
for i, (title, desc, col) in enumerate(props):
    cx2 = px + i * Inches(4.3)
    c = card(sl, cx2, py, Inches(4.2), Inches(0.95), fill=CARD_BG, line_color=col)
    txt(sl, title, cx2+Inches(0.1), py+Inches(0.08),
        Inches(4.0), Inches(0.3), size=11, bold=True, color=col)
    txt(sl, desc, cx2+Inches(0.1), py+Inches(0.42),
        Inches(4.0), Inches(0.45), size=9, color=LIGHT_GREY)

slide_num_label(sl, 2)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — ALGORITHM PROGRESSION
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "Previous Work — Algorithm Progression",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)
txt(sl, "Five algorithms studied and implemented — each solving a limitation of the previous.",
    Inches(0.5), Inches(1.2), Inches(12.3), Inches(0.4), size=12, color=LIGHT_GREY)

algos = [
    ("Greedy",    "Kempe et al. · 2003", BLUE,
     "First formulation as discrete optimisation. Picks node with highest marginal gain in σ(S). "
     "Uses 10,000 MC simulations per step. (1−1/e) guarantee.",
     "O(k·n·m·R) — prohibitively slow"),
    ("CELF",      "Leskovec et al. · 2007", BLUE,
     "Exploits submodularity — a node's marginal gain can only decrease. "
     "Sorted queue skips unchanged nodes. Same guarantee as Greedy.",
     "700× faster than Greedy"),
    ("IC Study",  "Independent Cascade", RGBColor(0x55, 0x88, 0xbb),
     "In-depth IC implementation: path-based influence, steady-state analysis, "
     "degree/betweenness/greedy seed selection on Moreno & US Airport networks.",
     "Heuristic baselines"),
    ("RIS",       "Borgs et al. · 2014", BLUE,
     "Random Reverse Reachable sets — BFS backward from random nodes. "
     "Node covering most RRR sets maximises σ(S). Near-linear time.",
     "Near-linear O((k+l)(n+m)log n / ε²)"),
    ("D-RIS",     "Sun & Chen · 2021", BLUE,
     "Computes θ dynamically from OPT estimate — generates only needed RRR sets. "
     "Significantly faster than standard RIS. Primary baseline for CA-RIS.",
     "3–5× faster than RIS"),
    ("CA-RIS",    "This work · 2024", ACCENT,
     "Extends D-RIS with community-structure awareness via Louvain + quota-greedy. "
     "First to change what problem is solved: balanced spread across communities.",
     "Proposed Contribution ★"),
]

# Vertical timeline line
ln = sl.shapes.add_shape(1, Inches(1.1), Inches(1.65), Pt(3), Inches(5.4))
ln.fill.solid(); ln.fill.fore_color.rgb = RGBColor(0x20, 0x40, 0x60)
ln.line.fill.background()

for i, (name, year, col, desc, perf) in enumerate(algos):
    y = Inches(1.6) + i * Inches(0.9)
    # dot
    dot = sl.shapes.add_shape(9, Inches(0.85), y + Inches(0.08),
                               Inches(0.22), Inches(0.22))   # 9=oval
    dot.fill.solid(); dot.fill.fore_color.rgb = col
    dot.line.fill.background()
    # name
    txt(sl, name, Inches(1.25), y, Inches(1.6), Inches(0.35),
        size=12, bold=True, color=col)
    txt(sl, year, Inches(2.9), y + Inches(0.04), Inches(2.2), Inches(0.3),
        size=9, color=MID_GREY, italic=True)
    # desc
    txt(sl, desc, Inches(5.2), y, Inches(5.5), Inches(0.6),
        size=9.5, color=LIGHT_GREY)
    # perf badge
    b_col = GREEN if name == "CELF" or name == "D-RIS" else (
            ACCENT if name == "CA-RIS" else RED if name == "Greedy" else BLUE)
    tag_pill(sl, perf, Inches(10.8), y + Inches(0.04),
             fill=RGBColor(0x14, 0x28, 0x40))
    txt(sl, perf, Inches(10.82), y + Inches(0.08), Inches(2.3), Inches(0.28),
        size=8, color=b_col, bold=True)

    # separator line
    if i < len(algos) - 1:
        sep = sl.shapes.add_shape(1, Inches(1.25), y + Inches(0.72),
                                   Inches(11.6), Pt(1))
        sep.fill.solid(); sep.fill.fore_color.rgb = RGBColor(0x20, 0x35, 0x4a)
        sep.line.fill.background()

slide_num_label(sl, 3)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — ECHO CHAMBER EFFECT
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "The Gap — Echo-Chamber Effect",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)

# Quote box
c = card(sl, Inches(0.4), Inches(1.25), Inches(12.5), Inches(1.1),
         fill=RGBColor(0x14, 0x25, 0x1a),
         line_color=ACCENT)
# Left accent bar
lb = card(sl, Inches(0.4), Inches(1.25), Inches(0.07), Inches(1.1), fill=ACCENT)
htxt(sl,
     '"All the algorithms are completely unaware of community structure. '
     'If seed nodes are selected without considering community structure, many chosen '
     'nodes will belong to the same largest community while smaller communities will '
     'have little to no influence."',
     Inches(0.6), Inches(1.35), Inches(12.1), Inches(0.9),
     size=11, italic=True, color=RGBColor(0xf4, 0xc5, 0x8a))

# Left card — example
card(sl, Inches(0.4), Inches(2.5), Inches(5.9), Inches(3.1), fill=CARD_BG)
txt(sl, "🌍  Real-World Example", Inches(0.55), Inches(2.58),
    Inches(5.7), Inches(0.35), size=12, bold=True, color=ACCENT)
htxt(sl,
     "A multinational company wants 5 athlete endorsers for a global campaign.",
     Inches(0.55), Inches(2.98), Inches(5.7), Inches(0.5), size=10.5, color=LIGHT_GREY)

communities = [("Football community", 60, GREEN), ("Cricket community", 20, BLUE),
               ("American Football", 20, ACCENT)]
by = Inches(3.52)
for name, pct, col in communities:
    txt(sl, f"{name}  ({pct}%)", Inches(0.6), by, Inches(5.5), Inches(0.28),
        size=9.5, color=LIGHT_GREY)
    hbar(sl, Inches(0.6), by + Inches(0.3), Inches(5.1), Inches(0.22), pct,
         fill=col, label=f"{pct}%")
    by += Inches(0.6)

htxt(sl,
     "Standard RIS picks ALL 5 from football → invisible in South Asia & America.",
     Inches(0.55), Inches(5.35), Inches(5.7), Inches(0.5),
     size=10, bold=False, color=RED)

# Right card — actual D-RIS failure
card(sl, Inches(6.8), Inches(2.5), Inches(6.1), Inches(3.1), fill=CARD_BG)
txt(sl, "📊  What D-RIS Actually Did (Slashdot, k=30)",
    Inches(6.95), Inches(2.58), Inches(5.9), Inches(0.35),
    size=11, bold=True, color=ACCENT)
htxt(sl, "12 communities detected. Seed assignment breakdown:",
     Inches(6.95), Inches(2.98), Inches(5.9), Inches(0.3), size=9.5, color=LIGHT_GREY)

rows = [
    ("C3  (154 nodes)", "10 / 30 seeds  ⚠ 33% of budget!", RED),
    ("C4  (116 nodes)", "0 seeds  ✗", RED),
    ("C7  (46 nodes)",  "0 seeds  ✗", RED),
    ("C9  (19 nodes)",  "0 seeds  ✗", RED),
    ("C10 (828 nodes)", "7 seeds", LIGHT_GREY),
]
ry = Inches(3.35)
for comm, seeds, col in rows:
    txt(sl, comm,  Inches(7.0), ry, Inches(2.5), Inches(0.32), size=9.5, color=LIGHT_GREY)
    txt(sl, seeds, Inches(9.6), ry, Inches(3.1), Inches(0.32), size=9.5, color=col, bold=(col==RED))
    ry += Inches(0.37)

tag_pill(sl, "Gini Imbalance = 0.488  (severely skewed)",
         Inches(6.95), Inches(5.28), fill=RGBColor(0x40, 0x10, 0x10))
txt(sl, "Gini Imbalance = 0.488  (severely skewed)",
    Inches(7.1), Inches(5.3), Inches(5.5), Inches(0.35), size=10, color=RED, bold=True)

# Bottom 3 cards
causes = [
    ("🔄 Echo Chamber", "Information circulates only within dense communities — never crosses weak inter-community ties."),
    ("📉 Diminishing Returns", "Multiple seeds in same community overlap heavily — marginal gain drops fast."),
    ("⚖️ Fairness Need", "Public health, global marketing, campaigns — reaching ALL communities matters more than one number."),
]
cx2 = Inches(0.4)
for title, desc in causes:
    c = card(sl, cx2, Inches(5.7), Inches(4.1), Inches(0.85), fill=CARD_BG)
    txt(sl, title, cx2+Inches(0.1), Inches(5.76), Inches(3.9), Inches(0.3),
        size=10, bold=True, color=ACCENT)
    txt(sl, desc, cx2+Inches(0.1), Inches(6.1), Inches(3.9), Inches(0.4),
        size=8.5, color=LIGHT_GREY)
    cx2 += Inches(4.35)

slide_num_label(sl, 4)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — COMMUNITY STRUCTURE & DATASETS
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "Community Structure & Datasets",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)

# Left — Louvain
card(sl, Inches(0.4), Inches(1.3), Inches(5.9), Inches(5.3), fill=CARD_BG)
txt(sl, "What is Community Structure?", Inches(0.55), Inches(1.38),
    Inches(5.7), Inches(0.35), size=12, bold=True, color=ACCENT)
htxt(sl,
     "Nodes cluster into groups that are densely connected internally "
     "and sparsely connected across groups.",
     Inches(0.55), Inches(1.78), Inches(5.7), Inches(0.55), size=10.5, color=LIGHT_GREY)

c = card(sl, Inches(0.55), Inches(2.38), Inches(5.6), Inches(0.5),
         fill=RGBColor(0x0a, 0x20, 0x38), line_color=BLUE)
txt(sl, "Q = Σ_c [ e_c − a_c² ]     Q > 0.3 → strong community structure",
    Inches(0.65), Inches(2.46), Inches(5.4), Inches(0.38),
    size=11, bold=True, color=RGBColor(0x90, 0xca, 0xf9), align=PP_ALIGN.CENTER)

txt(sl, "The Louvain Algorithm", Inches(0.55), Inches(3.0),
    Inches(5.7), Inches(0.3), size=12, bold=True, color=ACCENT)
louvain_steps = [
    "Phase 1: Move each node to neighbour community that maximises ΔQ",
    "Phase 2: Aggregate communities into super-nodes, build new graph",
    "Repeat until no improvement — near-linear time O(n log n)",
    "Used by Facebook & Twitter for large-scale community detection",
]
sy = Inches(3.35)
for step in louvain_steps:
    txt(sl, f"→  {step}", Inches(0.6), sy, Inches(5.65), Inches(0.38),
        size=10, color=LIGHT_GREY)
    sy += Inches(0.42)

# Right — datasets
for di, (name, icon, stats, q_val, q_col, note) in enumerate([
    ("Slashdot0902", "📡",
     [("Full nodes", "82,168"), ("Full edges", "870,161"),
      ("Subgraph nodes", "2,000"), ("Subgraph edges", "13,418"),
      ("Communities", "12"), ("Modularity Q", "0.3575"),
      ("Largest community", "828 nodes (41.4%)"), ("Smallest", "19 nodes")],
     "Strong community structure", ACCENT,
     "Technology news — users grouped by interest (open source, politics, games)"),
    ("soc-Epinions1", "🌐",
     [("Full nodes", "75,879"), ("Full edges", "508,837"),
      ("Subgraph nodes", "2,000"), ("Subgraph edges", "74,364"),
      ("Communities", "6"), ("Modularity Q", "0.2393"),
      ("Largest community", "555 nodes (27.8%)"), ("Smallest", "18 nodes")],
     "Moderate community structure", GREEN,
     "Consumer trust network — denser, more uniform community sizes"),
]):
    dy = Inches(1.3) + di * Inches(2.75)
    card(sl, Inches(6.8), dy, Inches(6.1), Inches(2.6), fill=CARD_BG)
    txt(sl, f"{icon}  {name}", Inches(6.95), dy + Inches(0.1),
        Inches(5.9), Inches(0.38), size=13, bold=True, color=WHITE)
    # stats grid
    for si, (k, v) in enumerate(stats):
        col2 = si % 2
        row2 = si // 2
        sx = Inches(6.95) + col2 * Inches(3.0)
        sy2 = dy + Inches(0.55) + row2 * Inches(0.42)
        txt(sl, k + ":", sx, sy2, Inches(2.0), Inches(0.35), size=9, color=MID_GREY)
        is_q = k == "Modularity Q"
        txt(sl, v, sx + Inches(1.3), sy2, Inches(1.6), Inches(0.35),
            size=9.5, bold=is_q, color=q_col if is_q else WHITE)

slide_num_label(sl, 5)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — CA-RIS ALGORITHM
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "CA-RIS — The Proposed Algorithm",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)

# Objective box
c = card(sl, Inches(0.4), Inches(1.28), Inches(12.5), Inches(1.1),
         fill=RGBColor(0x0a, 0x20, 0x38), line_color=BLUE)
txt(sl, "Modified Objective:",
    Inches(0.6), Inches(1.35), Inches(2.5), Inches(0.35), size=11, color=MID_GREY)
txt(sl, "F(S) = σ(S)  −  λ · I(S)",
    Inches(3.1), Inches(1.32), Inches(5), Inches(0.5),
    size=22, bold=True, color=RGBColor(0x90, 0xca, 0xf9), align=PP_ALIGN.CENTER)
htxt(sl,
     "σ(S) = influence spread  |  I(S) = Gini imbalance across communities  |  λ = fairness trade-off (λ=0 → standard RIS)",
     Inches(0.6), Inches(1.78), Inches(12.1), Inches(0.4), size=10, color=LIGHT_GREY)

# 3 step boxes
steps = [
    ("1", "Community Detection", BLUE,
     "Run Louvain on undirected\nprojection of G\n\n"
     "→ node → community id\n"
     "→ community → node list\n"
     "→ Modularity Q\n\n"
     "Near-linear O(n log n)\n~0.21s on Slashdot"),
    ("2", "RRR Set Generation", BLUE,
     "Dynamic θ (D-RIS style)\n\n"
     "1. θ₀ = n · ln(n) / k\n"
     "2. Generate θ₀ RRR sets\n"
     "3. Estimate OPT from coverage\n"
     "4. Recompute θ, generate more\n\n"
     "Each RRR set: backward BFS\nfrom random node, follow\nedges with prob p(u,v)"),
    ("3", "Quota Greedy Coverage", ACCENT,
     "Compute quotas:\nq_c = ⌊k · |C_c| / n⌋\n(largest-remainder)\n\n"
     "For each of k steps:\n"
     "→ Pick best node, quota > 0\n"
     "→ If none: relax constraint\n"
     "→ Remove covered RRR sets\n"
     "→ Decrement community quota"),
]
for i, (num, title, col, body) in enumerate(steps):
    sx = Inches(0.4) + i * Inches(4.35)
    c = card(sl, sx, Inches(2.5), Inches(4.2), Inches(3.6), fill=CARD_BG, line_color=col)
    # Number
    txt(sl, num, sx + Inches(0.15), Inches(2.55), Inches(0.6), Inches(0.6),
        size=28, bold=True, color=col)
    txt(sl, title, sx + Inches(0.6), Inches(2.65), Inches(3.5), Inches(0.4),
        size=13, bold=True, color=col)
    htxt(sl, body, sx + Inches(0.15), Inches(3.1), Inches(3.95), Inches(2.8),
         size=9.5, color=LIGHT_GREY)
    # Arrow between boxes
    if i < 2:
        txt(sl, "→", sx + Inches(4.25), Inches(4.1), Inches(0.4), Inches(0.4),
            size=20, color=BLUE, bold=True, align=PP_ALIGN.CENTER)

# Gini formula bottom
c = card(sl, Inches(0.4), Inches(6.2), Inches(12.5), Inches(0.9),
         fill=RGBColor(0x0a, 0x1a, 0x10), line_color=GREEN)
txt(sl, "Imbalance I(S) — Gini Coefficient:",
    Inches(0.6), Inches(6.28), Inches(3.5), Inches(0.35), size=10, color=MID_GREY)
txt(sl, "density_c = |S ∩ C_c| / |C_c|      Gini = Σᵢ Σⱼ |dᵢ − dⱼ| / (2 · m · Σᵢ dᵢ)      Gini=0: perfect balance  |  Gini=1: all seeds in one community",
    Inches(0.6), Inches(6.63), Inches(12.1), Inches(0.4),
    size=10, color=RGBColor(0x90, 0xca, 0xf9))

slide_num_label(sl, 6)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — EVALUATION METRICS
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "Evaluation Metrics",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)
txt(sl, "Four metrics evaluated for each algorithm — capturing both effectiveness and fairness.",
    Inches(0.5), Inches(1.2), Inches(12.3), Inches(0.4), size=12, color=LIGHT_GREY)

metrics = [
    ("1", "📈", "Influence Spread  σ(S)", "σ(S) = (1/R) · Σ |activated_r(S)|",
     "Average nodes activated over R=10,000 IC simulations.\n"
     "Primary measure of raw effectiveness.\n"
     "This is the ONLY metric optimised by all prior algorithms.\n"
     "Higher is better.", BLUE),
    ("2", "🌐", "Community Coverage  CC(S)", "CC(S) = |{c : S ∩ Cₓ ≠ ∅}| / m",
     "Fraction of m communities with ≥1 seed node.\n"
     "CC=1.0 → every community represented.\n"
     "CC=0.75 → 25% of communities completely ignored.\n"
     "Higher is better.", GREEN),
    ("3", "🎲", "Seed Entropy  H(S)", "H(S) = −Σ_c p_c · log₂(p_c) / log₂(m)",
     "Normalised Shannon entropy of seed distribution.\n"
     "H=1 → seeds as uniform as possible.\n"
     "H=0 → all seeds in one community.\n"
     "Higher is better.", PURPLE),
    ("4", "⚖️", "Gini Imbalance  I(S)", "I(S) = Gini({|S∩Cₓ|/|Cₓ|} for all c)",
     "Gini coefficient of per-community seed densities.\n"
     "Measures coverage inequality proportional to community size.\n"
     "This is the I(S) term in F(S) = σ(S) − λ·I(S).\n"
     "Lower is better.", ACCENT),
]

for i, (num, icon, name, formula, desc, col) in enumerate(metrics):
    col2 = i % 2; row2 = i // 2
    mx = Inches(0.4) + col2 * Inches(6.5)
    my = Inches(1.75) + row2 * Inches(2.75)
    c = card(sl, mx, my, Inches(6.3), Inches(2.6), fill=CARD_BG, line_color=col)
    txt(sl, f"{icon}  {name}", mx+Inches(0.15), my+Inches(0.1),
        Inches(6.0), Inches(0.38), size=12, bold=True, color=col)
    cb = card(sl, mx+Inches(0.15), my+Inches(0.55), Inches(6.0), Inches(0.42),
              fill=RGBColor(0x07, 0x12, 0x20), line_color=RGBColor(0x30, 0x50, 0x80))
    txt(sl, formula, mx+Inches(0.25), my+Inches(0.62), Inches(5.8), Inches(0.3),
        size=10, color=RGBColor(0x90, 0xca, 0xf9))
    htxt(sl, desc, mx+Inches(0.15), my+Inches(1.05), Inches(6.0), Inches(1.4),
         size=9.5, color=LIGHT_GREY)

slide_num_label(sl, 7)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — SLASHDOT RESULTS
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "Results — Slashdot Dataset",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)
txt(sl, "2,000 nodes · k=30 · λ=0.5 · p=0.01 · 12 communities · Q=0.3575 · Largest community = 41.4%",
    Inches(0.5), Inches(1.2), Inches(12.3), Inches(0.4), size=11, color=LIGHT_GREY)

# Main results table
card(sl, Inches(0.4), Inches(1.68), Inches(7.1), Inches(3.0), fill=CARD_BG)
txt(sl, "Main Comparison Table", Inches(0.55), Inches(1.73),
    Inches(7.0), Inches(0.3), size=11, bold=True, color=ACCENT)

headers = ["Metric", "CA-RIS", "D-RIS", "RIS"]
cw = [Inches(2.5), Inches(1.4), Inches(1.4), Inches(1.4)]
table_header(sl, headers, Inches(0.5), Inches(2.1), cw, row_h=Inches(0.36))

rows_data = [
    ("MC Spread σ(S)",          "62.25",        "65.85",  "68.89",   [LIGHT_GREY, LIGHT_GREY, LIGHT_GREY, GREEN]),
    ("RRR Estimate σ̂(S)",      "72.84",        "75.90",  "73.22",   [LIGHT_GREY, LIGHT_GREY, GREEN, LIGHT_GREY]),
    ("Community Coverage",       "91.7% (11/12)","75.0%", "91.7%",   [LIGHT_GREY, GREEN, RED, GREEN]),
    ("Seed Entropy H(S)",        "0.806",        "0.759",  "0.815",   [LIGHT_GREY, LIGHT_GREY, RED, GREEN]),
    ("Gini Imbalance I(S) ↓",    "0.175",        "0.488",  "0.414",   [LIGHT_GREY, GREEN, RED, LIGHT_GREY]),
    ("Runtime (s)",              "0.18",         "0.20",   "0.67",    [LIGHT_GREY, GREEN, LIGHT_GREY, RED]),
    ("RRR sets θ",               "53,322",       "59,918", "200,000", [LIGHT_GREY, GREEN, LIGHT_GREY, RED]),
]
for ri, (m, ca, dr, ris, cols) in enumerate(rows_data):
    ry = Inches(2.46) + ri * Inches(0.34)
    fill = CARD_BG if ri % 2 == 0 else RGBColor(0x16, 0x2e, 0x44)
    table_row(sl, [m, ca, dr, ris], Inches(0.5), ry, cw,
              row_h=Inches(0.34), fill=fill, colors=cols)

# Relative change bars
card(sl, Inches(0.4), Inches(4.78), Inches(7.1), Inches(1.9), fill=CARD_BG)
txt(sl, "CA-RIS vs D-RIS — Relative Change",
    Inches(0.55), Inches(4.83), Inches(7.0), Inches(0.3), size=11, bold=True, color=ACCENT)

changes = [
    ("Gini Imbalance",       64.1, "−64.1%", GREEN, True),
    ("Community Coverage",   22.2, "+22.2%", GREEN, True),
    ("Seed Entropy",          6.2, "+6.2%",  GREEN, True),
    ("Spread cost",           5.5, "−5.5%",  RED,   False),
]
by2 = Inches(5.2)
for label, pct, badge, col, good in changes:
    txt(sl, label, Inches(0.6), by2, Inches(2.3), Inches(0.28), size=9.5, color=LIGHT_GREY)
    hbar(sl, Inches(2.95), by2 + Inches(0.03), Inches(3.5), Inches(0.25),
         pct, fill=col, label=badge)
    by2 += Inches(0.33)

# Right — per community distribution
card(sl, Inches(7.9), Inches(1.68), Inches(5.0), Inches(5.0), fill=CARD_BG)
txt(sl, "Per-Community Seed Distribution",
    Inches(8.05), Inches(1.73), Inches(4.8), Inches(0.3),
    size=11, bold=True, color=ACCENT)
# legend
for li, (lbl, col) in enumerate([("CA-RIS", BLUE), ("D-RIS", ACCENT), ("RIS", GREEN)]):
    lx = Inches(8.05) + li * Inches(1.5)
    b = sl.shapes.add_shape(1, lx, Inches(2.1), Inches(0.14), Inches(0.14))
    b.fill.solid(); b.fill.fore_color.rgb = col; b.line.fill.background()
    txt(sl, lbl, lx + Inches(0.18), Inches(2.08), Inches(1.2), Inches(0.25),
        size=8.5, color=LIGHT_GREY)

comm_rows = [
    ("C10 (41%)", 828, 12, 7,  1),
    ("C3",        154,  2, 10, 11),
    ("C5",        173,  3,  3,  4),
    ("C1",        172,  3,  2,  2),
    ("C4",        116,  2,  0,  2),
    ("C7",         46,  1,  0,  1),
    ("C9",         19,  0,  0,  0),
]
cy2 = Inches(2.4)
for comm, size, ca_s, dr_s, ris_s in comm_rows:
    txt(sl, comm, Inches(7.95), cy2, Inches(1.3), Inches(0.28), size=8.5, color=MID_GREY)
    bx = Inches(9.35)
    for seeds, col, is_zero in [(ca_s, BLUE, False), (dr_s, ACCENT, dr_s == 0), (ris_s, GREEN, False)]:
        if is_zero:
            lbl = "0 ✗"
            fc = RED
        else:
            lbl = str(seeds)
            fc = col
        bw = max(Inches(0.18), Inches(0.18 * seeds)) if seeds > 0 else Inches(0.3)
        hbar(sl, bx, cy2 + Inches(0.03), Inches(1.1), Inches(0.22),
             min(seeds * 7, 95) if seeds else 0,
             fill=fc, label=lbl)
        bx += Inches(1.2)
    cy2 += Inches(0.42)

# Key call-out
c = card(sl, Inches(7.9), Inches(5.75), Inches(5.0), Inches(0.85),
         fill=RGBColor(0x20, 0x10, 0x00), line_color=ACCENT)
htxt(sl,
     "⚠  D-RIS assigned 10/30 seeds to C3 alone (33% budget).\n"
     "CA-RIS quota caps each community proportionally.",
     Inches(8.05), Inches(5.82), Inches(4.8), Inches(0.75), size=9.5, color=ACCENT)

slide_num_label(sl, 8)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — EPINIONS + LAMBDA SWEEP
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "Results — Epinions  &  λ Sweep Analysis",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)

# Epinions table
card(sl, Inches(0.4), Inches(1.28), Inches(6.5), Inches(3.65), fill=CARD_BG)
txt(sl, "Epinions Results  (k=30, λ=0.5)",
    Inches(0.55), Inches(1.33), Inches(6.3), Inches(0.3), size=11, bold=True, color=ACCENT)
txt(sl, "6 communities · Q=0.2393 · Largest = 27.8% · 74,364 edges",
    Inches(0.55), Inches(1.65), Inches(6.3), Inches(0.28), size=9, color=MID_GREY)

eh = ["Metric", "CA-RIS", "D-RIS", "RIS"]
ecw = [Inches(2.1), Inches(1.3), Inches(1.3), Inches(1.3)]
table_header(sl, eh, Inches(0.5), Inches(2.0), ecw, row_h=Inches(0.36))
erows = [
    ("MC Spread σ(S)",     "196.07", "199.25", "202.89", [LIGHT_GREY, LIGHT_GREY, LIGHT_GREY, GREEN]),
    ("Community Coverage", "83.3%",  "83.3%",  "83.3%",  [LIGHT_GREY, LIGHT_GREY, LIGHT_GREY, LIGHT_GREY]),
    ("Seed Entropy",       "0.874",  "0.867",  "0.852",  [LIGHT_GREY, GREEN, LIGHT_GREY, RED]),
    ("Gini Imbalance ↓",   "0.192",  "0.310",  "0.376",  [LIGHT_GREY, GREEN, LIGHT_GREY, RED]),
    ("Runtime (s)",        "0.42",   "0.46",   "2.36",   [LIGHT_GREY, GREEN, LIGHT_GREY, RED]),
    ("RRR sets θ",         "37,020", "36,785", "200,000",[LIGHT_GREY, LIGHT_GREY, GREEN, RED]),
]
for ri, (m, ca, dr, ri_s, cols) in enumerate(erows):
    fill = CARD_BG if ri % 2 == 0 else RGBColor(0x16, 0x2e, 0x44)
    table_row(sl, [m, ca, dr, ri_s], Inches(0.5),
              Inches(2.36) + ri * Inches(0.34), ecw,
              row_h=Inches(0.34), fill=fill, colors=cols)

# Epinions gains
gains = [
    ("Gini −38% vs D-RIS", GREEN), ("Spread cost −1.6%", ACCENT),
    ("5.6× faster than RIS", BLUE),
]
gx = Inches(0.5)
for glabel, gcol in gains:
    tag_pill(sl, glabel, gx, Inches(4.75), fill=CARD_BG)
    txt(sl, glabel, gx + Inches(0.08), Inches(4.78),
        Inches(1.9), Inches(0.25), size=8.5, color=gcol, bold=True)
    gx += Inches(2.1)

# Lambda sweep table
card(sl, Inches(7.3), Inches(1.28), Inches(5.6), Inches(3.0), fill=CARD_BG)
txt(sl, "λ Sweep — Slashdot  (λ ∈ {0 → 2},  k=30)",
    Inches(7.45), Inches(1.33), Inches(5.4), Inches(0.3),
    size=11, bold=True, color=ACCENT)
lh = ["λ", "σ̂(S)", "CC", "Entropy", "Gini", "Time"]
lcw = [Inches(0.6), Inches(0.9), Inches(0.9), Inches(0.9), Inches(0.9), Inches(0.8)]
table_header(sl, lh, Inches(7.4), Inches(1.7), lcw, row_h=Inches(0.34))
lrows = [
    ("0.00", "72.58", "0.909", "0.786", "0.186", "0.17s"),
    ("0.25", "74.10", "0.909", "0.786", "0.186", "0.23s"),
    ("0.50", "74.22", "0.909", "0.786", "0.186", "0.20s"),
    ("1.00", "74.40", "0.909", "0.786", "0.186", "0.21s"),
    ("2.00", "74.34", "0.909", "0.786", "0.186", "0.18s"),
]
for ri, row in enumerate(lrows):
    fill = CARD_BG if ri % 2 == 0 else RGBColor(0x16, 0x2e, 0x44)
    table_row(sl, list(row), Inches(7.4),
              Inches(2.04) + ri * Inches(0.33), lcw,
              row_h=Inches(0.33), fill=fill)

# Key finding box
c = card(sl, Inches(7.3), Inches(4.38), Inches(5.6), Inches(1.5),
         fill=RGBColor(0x14, 0x25, 0x14), line_color=GREEN)
lb2 = card(sl, Inches(7.3), Inches(4.38), Inches(0.07), Inches(1.5), fill=GREEN)
txt(sl, "🔑  Key Finding", Inches(7.5), Inches(4.44),
    Inches(5.3), Inches(0.3), size=11, bold=True, color=GREEN)
htxt(sl,
     "CC, Entropy, and Gini are FLAT across all λ values — "
     "the σ̂ variation is RRR sampling noise.\n\n"
     "→ The community-quota greedy is the primary driver of fairness, "
     "not the λ penalty term. λ only influences θ via OPT estimation.",
     Inches(7.5), Inches(4.8), Inches(5.2), Inches(1.0),
     size=9.5, color=LIGHT_GREY)

# 3 big stats
stats3 = [("−64%", "Gini Slashdot", ACCENT), ("−38%", "Gini Epinions", GREEN),
          ("−5.5%", "Max spread cost", RED)]
sx3 = Inches(0.4)
for sval, slabel, col in stats3:
    c = card(sl, sx3, Inches(6.1), Inches(4.1), Inches(0.95), fill=CARD_BG, line_color=col)
    txt(sl, sval, sx3+Inches(0.15), Inches(6.15), Inches(3.8), Inches(0.5),
        size=24, bold=True, color=col, align=PP_ALIGN.CENTER)
    txt(sl, slabel, sx3+Inches(0.15), Inches(6.65), Inches(3.8), Inches(0.3),
        size=10, color=MID_GREY, align=PP_ALIGN.CENTER)
    sx3 += Inches(4.4)

slide_num_label(sl, 9)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — CONCLUSIONS
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide(); bg(sl)
txt(sl, "Conclusions & Future Work",
    Inches(0.5), Inches(0.25), Inches(12), Inches(0.6), size=26, bold=True)
section_line(sl)

# Left — modules + contributions
card(sl, Inches(0.4), Inches(1.28), Inches(6.3), Inches(2.6), fill=CARD_BG)
txt(sl, "What Was Implemented", Inches(0.55), Inches(1.33),
    Inches(6.1), Inches(0.3), size=11, bold=True, color=ACCENT)

modules = [
    ("independent_cascade/", "IC Model — diffusion simulation, path analysis",  BLUE),
    ("greedy/",              "Greedy + EGA (Edge-based Greedy Algorithm)",       BLUE),
    ("celf/",                "CELF — Cost-Effective Lazy Forward",               BLUE),
    ("ris/",                 "RIS — Reverse Influence Sampling",                 BLUE),
    ("community_aware_ris/", "CA-RIS — Proposed Contribution  ★",               ACCENT),
]
my2 = Inches(1.72)
for mname, mdesc, col in modules:
    is_p = col == ACCENT
    bg_c = RGBColor(0x20, 0x18, 0x05) if is_p else CARD_BG
    if is_p:
        c = card(sl, Inches(0.5), my2, Inches(6.1), Inches(0.36),
                 fill=bg_c, line_color=ACCENT)
    txt(sl, mname, Inches(0.6), my2+Inches(0.04), Inches(2.1), Inches(0.28),
        size=9, bold=True, color=col)
    txt(sl, mdesc, Inches(2.75), my2+Inches(0.04), Inches(3.6), Inches(0.28),
        size=9, color=LIGHT_GREY if not is_p else ACCENT)
    txt(sl, "✅", Inches(6.2), my2+Inches(0.04), Inches(0.3), Inches(0.28),
        size=9, color=GREEN)
    my2 += Inches(0.42)

# Contributions
card(sl, Inches(0.4), Inches(4.0), Inches(6.3), Inches(2.6), fill=CARD_BG)
txt(sl, "Core Contributions", Inches(0.55), Inches(4.05),
    Inches(6.1), Inches(0.3), size=11, bold=True, color=ACCENT)

contribs = [
    ("1", "Community-aware objective",
     "F(S)=σ(S)−λ·I(S) — first RIS algorithm to change what problem is solved"),
    ("2", "Community-quota greedy",
     "Proportional allocation ensures balanced distribution without losing (1−1/e) guarantee"),
    ("3", "Empirical validation",
     "Gini −38–64% vs D-RIS on two SNAP datasets; spread cost only 1.6–5.5%"),
]
cy3 = Inches(4.45)
for num, title, desc in contribs:
    txt(sl, num, Inches(0.55), cy3, Inches(0.4), Inches(0.4),
        size=18, bold=True, color=BLUE)
    txt(sl, title, Inches(1.0), cy3, Inches(5.5), Inches(0.28),
        size=10, bold=True, color=WHITE)
    txt(sl, desc, Inches(1.0), cy3+Inches(0.3), Inches(5.5), Inches(0.35),
        size=8.5, color=LIGHT_GREY)
    cy3 += Inches(0.72)

# Right — limitations + future work
card(sl, Inches(7.1), Inches(1.28), Inches(5.8), Inches(1.75), fill=CARD_BG)
txt(sl, "Limitations", Inches(7.25), Inches(1.33),
    Inches(5.6), Inches(0.3), size=11, bold=True, color=RED)
htxt(sl,
     "→  Very small communities (<20 nodes) rarely appear in RRR sets under p=0.01 — receive zero seeds\n"
     "→  λ sweep shows quota mechanism dominates; λ penalty needs tighter integration into greedy scoring",
     Inches(7.25), Inches(1.7), Inches(5.6), Inches(1.2), size=9.5, color=LIGHT_GREY)

card(sl, Inches(7.1), Inches(3.15), Inches(5.8), Inches(3.45), fill=CARD_BG)
txt(sl, "Future Work", Inches(7.25), Inches(3.2),
    Inches(5.6), Inches(0.3), size=11, bold=True, color=BLUE)
future = [
    ("Full-graph experiments",   "Run on complete 82k/75k-node graphs for richer community granularity"),
    ("k-sensitivity analysis",   "Vary k ∈ {10,20,30,40,50} — show spread–fairness trade-off vs budget"),
    ("λ in greedy scoring",      "Integrate λ directly into marginal gain at each greedy step"),
    ("Adaptive probabilities",   "Higher p for intra-community (strong ties), lower for inter-community"),
]
fy = Inches(3.6)
for ftitle, fdesc in future:
    txt(sl, f"→  {ftitle}", Inches(7.25), fy, Inches(5.6), Inches(0.28),
        size=10, bold=True, color=ACCENT)
    txt(sl, fdesc, Inches(7.5), fy+Inches(0.3), Inches(5.3), Inches(0.3),
        size=8.5, color=LIGHT_GREY)
    fy += Inches(0.72)

# Final result strip
c = card(sl, Inches(0.4), Inches(6.7), Inches(12.5), Inches(0.7),
         fill=RGBColor(0x0a, 0x20, 0x38), line_color=BLUE)
for ri, (val, label, col) in enumerate([
    ("−64%", "Gini (Slashdot)", ACCENT),
    ("+22%", "Coverage (Slashdot)", GREEN),
    ("−38%", "Gini (Epinions)", GREEN),
    ("−5.5%", "Max spread cost", RED),
    ("~0.4s", "Runtime CA-RIS", BLUE),
]):
    rx = Inches(0.6) + ri * Inches(2.5)
    txt(sl, val,   rx, Inches(6.72), Inches(2.3), Inches(0.3),
        size=16, bold=True, color=col, align=PP_ALIGN.CENTER)
    txt(sl, label, rx, Inches(7.0), Inches(2.3), Inches(0.3),
        size=8, color=MID_GREY, align=PP_ALIGN.CENTER)

slide_num_label(sl, 10)

# ── Save ───────────────────────────────────────────────────────────────────────
OUT = "/Users/nikhilgupta/Desktop/btp/community_aware_ris/PRESENTATION.pptx"
prs.save(OUT)
print(f"Saved: {OUT}")
