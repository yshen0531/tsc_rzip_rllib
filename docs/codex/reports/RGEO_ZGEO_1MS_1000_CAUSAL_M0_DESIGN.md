# Fixed-1000 causal short-horizon M0 design

M0 is the first model trained exclusively on the new fixed-1000 lineage. It
uses the 25 prospectively fit-eligible B0, D0R1, D1 and N0 primary compact
trajectories. Integrity replays, calibration, holdout, controller rows and
all fixed-1100 evidence are excluded.

The model predicts the next 1 ms R/Z/Ip increment. Every prediction is
re-centered on the exact current R/Z/Ip observation and uses only causal
velocity, exact issued Card15 target, current readback and compressed action
history. The executed target lattice has numerical rank six; M0 retains that
full span instead of collapsing it to the conceptual two-axis basis.

One frozen standardized ridge model is compared with an action-blind model
using the same state/time backbone. Six whole schedule/phase folds hold out
D0 phase 10, D0 phase 24, D1 phase 8, D1 phase 24, N0 shallow depths and N0
deep depths. Selection requires per-fold absolute one-step gates, paired
response NRMSE, action-aware improvement over the blind comparator, and
peak response direction. There is no hyperparameter search and no neural
successor in this identity.

PASS is development-only and may create a compact artifact for a separately
prospective fresh switching sentinel. It does not open calibration, holdout,
Authority, Recourse, feedback, waypoint tracking or R_mid crossing. FAIL
closes this smooth fixed-feature model and requires one bounded diagnostic
before deciding whether the missing structure is hybrid/event representation
or action/history support.
