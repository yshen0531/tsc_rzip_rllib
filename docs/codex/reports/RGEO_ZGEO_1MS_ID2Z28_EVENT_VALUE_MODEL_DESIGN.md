# ID-2Z28 bounded event/value model and utility design

ID-2Z28 is a zero-new-TSC development model over the prospectively weighted
ID2Z27 D0 rows. It fits only the issue-32 matched signed q_R/q_Z responses and
uses issue 40 as a whole-phase internal validation. The transition-center
baseline supplies the observed nominal continuation. The continuing-full-F
diagnostic, exact replay, ID2Z25 and every calibration/holdout identity have
zero training weight.

The sole learned object is a finite causal eight-step response kernel. For
each output-aligned axis, the signed odd step response is differenced into an
FIR kernel; no future actual current, future RZI, label, family id or hidden
simulator field is an input. The model predicts deviations from the exactly
observed/recentered nominal trajectory, not a long free-running world state.

The frozen internal validation gates are scaled response RMSE <=0.12, scaled
absolute-error p95 <=0.20, minimum per-state R/Z direction cosine >=0.98,
maximum terminal response-velocity error <=0.05 m/s and maximum 64-direction
h8 action-ranking regret <=0.02 mm. Scales are 0.1 mm, 0.1 mm and 25 A.
These are development-selection gates, not calibrated uncertainty or control
qualification.

If the model gates pass, a fixed exhaustive search evaluates every eight-slot
sequence over center, +/-q_R and +/-q_Z against the observed phase-32 and
phase-40 center baselines. It minimizes the worst h4--h8 normalized capture
score. The winner and its sign inverse must be rendered as exact Card15
streams with the already qualified eight-slot cumulative return bridge,
<=0.3 A slew and positive absolute-current headroom.

Authority-sentinel readiness additionally requires at least 15% predicted
worst-score improvement over matched center. Failure of this utility gate is
not model failure and does not weaken the external capture criteria. It means
the current 0.50F-centered q cell is too weak for the next control-aligned
sentinel and routes to a single nominal-share/action-allocation redesign.
There is no adjacent duration/phase/kernel/model-capacity ladder. A PASS may
authorize only a separately frozen fresh Authority-L0 sentinel design; it is
not Authority, capture, Recourse, calibration, holdout or controller evidence.
