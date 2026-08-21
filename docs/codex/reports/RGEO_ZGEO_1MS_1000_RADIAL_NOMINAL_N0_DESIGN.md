# Fixed-1000 radial nominal N0 design

N0 is a bounded radial nominal development campaign, not a controller. It
uses D1's exact even-minus Card15 coordinate from issue 0, ramps one exact
quantized level per millisecond to depths 4, 8, 12 or 16, and then holds the
attained target through state 64. A predeclared depth-12 replay has zero fit
weight. All four primary trajectories are prospectively development-fit
eligible.

The purpose is to determine whether this known radial coordinate can
materially reduce both the q0 terminal source-distance drift and its terminal
speed. Scientific PASS requires at least 15% improvement in the worst
state56--64 source distance and at least 0.03 m/s reduction in terminal
maximum speed in the same candidate. The existing 5 mm / 0.1 m/s / 5% Ip
capture goal is reported as a stronger diagnostic and is not weakened.

The campaign is limited to five resets and 320 advances with no retry. Every
action remains exact Card15, adjacent issued/readback slew remains at most
0.3 A, and the existing 50 mm R/Z and 10% Ip hard development envelope is
unchanged. PASS opens a compact exact-observation-recentered model and a
separate feedback/Authority design only. It is not hold, capture, recovery,
Recourse, waypoint tracking or R_mid crossing.
