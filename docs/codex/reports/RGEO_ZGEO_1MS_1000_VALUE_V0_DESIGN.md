# Fixed-1000 V0 direct candidate-value/risk model

V0 is the first model after the M0/M1 point-prediction ladder closed. It
uses only three development contexts: the D1 q0 history at issue 24 and the
two D2 conditioner histories. Each context has the same four sustained
candidate macros and matched-baseline h4/h8 R/Z/Ip responses.

For each candidate and horizon, V0 stores a componentwise empirical center
and uncertainty halfwidth. In each leave-one-history-out fold the center is
the training median and the halfwidth is the largest training deviation plus
fixed floors of 0.03 mm R, 0.03 mm Z and 10 A Ip. This deliberately avoids a
poorly supported history regressor. It asks whether a conservative finite
response set is already stable enough to select among known candidates.

The model is evaluated on complete held histories. Every R/Z/Ip response
component must be contained. Final all-context halfwidths must remain below
0.08 mm R/Z and 30 A Ip. Across 64 desired task-plane directions, the true
progress regret of the model-selected candidate must be at most 0.03 mm in
every fold and horizon; each context must have at least 0.10 mm robust h8
directional progress. Ip responses remain capped at 400 A.

V0 runs no TSC. PASS emits a development-only response-set artifact and
authorizes only fresh negative-conditioner calibration. It is not a full
trajectory model, probability model, Authority, Recourse or controller.
FAIL requires action/history/risk redesign and does not reopen point-model
capacity search.
