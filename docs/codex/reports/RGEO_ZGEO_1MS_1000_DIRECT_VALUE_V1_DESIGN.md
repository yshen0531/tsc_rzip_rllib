# Fixed-1000 V1 direct no-action/candidate value model design

V1 is the single model authorized by D3.  It is not a recursive world model
and does not estimate the already exact current R/Z/Ip.  For a causal history
at issue 24 it predicts two additive sets at h4 and h8: the measured
no-action continuation and each candidate's response relative to that
continuation.  Their Minkowski sum is the absolute candidate endpoint set.

The four whole-history development contexts are D2 even-plus/odd-plus and D3
block4-plus/block4-minus.  D2 supplies baseline and even/odd signed candidates;
D3 additionally supplies block4 signed candidates.  Missing block4 labels in
D2 are absent, never imputed as zero.  Replays and all calibration/blind rows
have zero fit weight.

The model is one candidate-specific robust empirical set: componentwise
median center plus maximum development deviation and fixed R/Z/Ip floors.
No-action and candidate-response heads are separate.  A deployable causal
support vector uses state-24 R/Z/Ip, the state20--24 velocity, and projections
of current/current-innovation onto even, odd and block4 coordinates.  A fresh
row outside the frozen candidate-specific nearest-history radius must refuse.

Evaluation is leave-one-whole-history-out.  It tests no-action and absolute
candidate endpoint containment, all informative directional rankings, final
set widths, Ip and causal support distances.  There is no frame-level split,
hyperparameter search, second neural candidate or gate adjustment.

PASS emits one immutable development artifact and authorizes only a separately
frozen fresh calibration campaign followed by an unopened whole-history blind
campaign.  FAIL closes this candidate library without a third model or extra
nearby histories.  Authority, Recourse, feedback and path tracking remain
blocked regardless of V1's development result.

