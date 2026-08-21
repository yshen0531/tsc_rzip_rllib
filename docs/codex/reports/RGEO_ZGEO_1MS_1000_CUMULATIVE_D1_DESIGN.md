# Fixed-1000 cumulative temporal D1 design

D1 is the one bounded successor opened by D0R1. It keeps the same exact q0
center and the same even/odd signed coordinates, but replaces the isolated
four-issue offset with a cumulative temporal primitive: four one-ms levels up,
four issues at level four, four exact levels down to q0, then a long q0 tail.
This directly tests the action/history cells a feedback controller would need
and does not read any fixed-1100 response.

Two issue phases (8 and 24), two axes and two signs give eight primary
development rollouts. Phase-24 even-minus and odd-plus receive one integrity
replay each. The total budget is ten resets and at most 480 advance attempts,
with no retry. Every cumulative Card15 target, every adjacent step, absolute
current, exact return, limiter, Ip and 50 mm R/Z envelope must pass before or
during execution. Safe-stopped/incomplete rows are not fit eligible.

Scientific PASS requires sustained h4/h8 signal, signed separation and a
two-axis response geometry at each phase; h12/h16 return-tail response is also
bounded. It opens a small short-horizon history-conditioned model and a
separate Authority design only. D1 is not hold, capture, recovery, Recourse,
feedback, waypoint tracking or R_mid crossing.
