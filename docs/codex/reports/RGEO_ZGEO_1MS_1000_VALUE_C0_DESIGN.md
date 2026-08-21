# Fixed-1000 C0 fresh calibration design

C0 is a fresh, fixed-model calibration campaign. It does not train or update
V0. The V0 result and artifact are bound byte-for-byte before any TSC call.

Two histories that were absent from V0 development are frozen:
`even_minus` and `odd_minus` cumulative conditioners at issue 8. Within each
history, a matched baseline and all four frozen issue-24 candidates run to
state 48. One candidate in each history receives an integrity-only replay.
The campaign therefore has ten calibration rows, two zero-weight replays,
twelve resets and at most 576 plant advances. No result-dependent arm,
retry, phase or horizon may be added.

Execution, exact Card15, 0.3 A slew, current, limiter, Ip, raw and replay
gates remain fail-closed. The D2 signal, signed-separation, two-axis geometry
and return-tail gates are retained. The byte-fixed V0 response sets must
contain every h4/h8 R/Z/Ip component; directional candidate regret must be at
most 0.03 mm, and each fresh history must retain at least 0.10 mm robust h8
progress. Calibration cannot widen the set or refit its center.

PASS authorizes only design of one unopened mixed-history blind campaign.
It is not Authority, capture, Recourse, feedback or path tracking. FAIL
freezes V0 as not calibrated across negative histories and returns to
history/risk representation design without reopening the point-model ladder.
