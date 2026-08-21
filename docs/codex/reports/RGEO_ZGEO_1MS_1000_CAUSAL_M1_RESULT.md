# Fixed-1000 causal M1 result

M1 completed server-only development after `771/771` one-ms tests passed. It
ran no TSC and made no plant advance. The frozen model used the same 25 M0
development trajectories, q0-relative response targets, explicit absolute
issue encoding, causal state/action history and three fixed network seeds.

The result is FAIL. Mean paired-response NRMSE was `0.9762167771`, only
`2.378322%` better than predicting zero response. Fold R p95 was
`0.1137/0.1444/0.2540/0.3688/0.7637/0.8001 mm`; N0 shallow and deep were
worse than the zero-response comparator (`1.282669/1.300030`) and retained
reversed peak directions. Z and Ip remained comparatively easy, so the
load-bearing failure is radial hybrid/history generalization rather than an
interface or optimizer error.

The result emits no artifact and permanently closes further one-step point
model expansion on this dataset. The next route changes the learning target
to direct multi-horizon candidate value with risk/support refusal, using a
fresh prospectively split sustained-action campaign. This does not authorize
calibration, holdout, Authority, Recourse, feedback or controller execution.
