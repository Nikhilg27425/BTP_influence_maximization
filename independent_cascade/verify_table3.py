import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from path_method import path_method
from steady_state import steady_state_spread, sss_noself, sss_bounded_path

nodes = [1, 2, 3, 4, 5]
# Fig. 2: circuit exists — node 4 is also an in-neighbor of node 2
# edges: 5->3 (0.4), 3->1 (0.2), 3->2 (0.1), 1->2 (0.3), 2->4 (0.2), 4->2 (0.3)
# This creates the circuit 2->4->2 that causes SteadyStateSpread to overestimate
p = {
    1: {2: 0.3},
    2: {4: 0.2},
    3: {1: 0.2, 2: 0.1},
    4: {2: 0.3},
    5: {3: 0.4}
}
seed_set = [5]

pi_pm  = path_method(nodes, p, seed_set)
pi_sss = steady_state_spread(nodes, p, seed_set, eps=1e-10)
pi_sn  = sss_noself(nodes, p, seed_set, eps=1e-10)
pi_bp  = {b0: sss_bounded_path(nodes, p, seed_set, b0=b0, eps=1e-10) for b0 in range(5)}

print('Node:              1       2       3       4       5')
print(f'Path Method:    {pi_pm[1]:.4f}  {pi_pm[2]:.4f}  {pi_pm[3]:.4f}  {pi_pm[4]:.4f}  {pi_pm[5]:.4f}')
print(f'SteadyState:    {pi_sss[1]:.4f}  {pi_sss[2]:.4f}  {pi_sss[3]:.4f}  {pi_sss[4]:.4f}  {pi_sss[5]:.4f}')
print(f'SSS-Noself:     {pi_sn[1]:.4f}  {pi_sn[2]:.4f}  {pi_sn[3]:.4f}  {pi_sn[4]:.4f}  {pi_sn[5]:.4f}')
for b0 in range(5):
    print(f'BP(b0={b0}):       {pi_bp[b0][1]:.4f}  {pi_bp[b0][2]:.4f}  {pi_bp[b0][3]:.4f}  {pi_bp[b0][4]:.4f}  {pi_bp[b0][5]:.4f}')

print()
print('Expected (Table 3 from paper):')
print('Path Method:    0.0800  0.0616  0.4000  0.0123  1.0000')
print('SteadyState:    0.0800  0.0678  0.4000  0.0132  1.0000')
print('SSS-Noself:     0.0800  0.0630  0.4000  0.0126  1.0000')
print('BP(b0=0):       0.0800  0.0400  0.4000  0.0080  1.0000')
print('BP(b0=1):       0.0800  0.0630  0.4000  0.0126  1.0000')
