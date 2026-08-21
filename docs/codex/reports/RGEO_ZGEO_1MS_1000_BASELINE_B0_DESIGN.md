# Fixed-1000 baseline B0 design

B0 is the first natural-drift measurement in the new fixed-1000 route. It
does not read or inherit fixed-1100 trajectories. Two canonical restarts hold
the exact source Card15 q0 command for 64 one-millisecond issues. The first
rollout is prospectively eligible as a development baseline; the second is a
zero-fit-weight integrity replay.

The budget is exactly two resets and at most 128 advance attempts, with no
retry. Current R_geo/Z_geo/Ip and all takeover causal history are available
before each issue. The first source-to-successor actual-current difference is
descriptive because restart readback and the active command are distinct
coordinates; every later observed transition retains the exact 0.3 A hard
gate. Limiter, absolute-current, 50 mm R/Z source radii and 10% Ip envelope
are fail-closed after every successor and before any further issue.

A PASS means only that the 64 ms q0 drift and replay are complete and can be
used to design a bounded signed temporal-response campaign. It is not a hold,
stability, Authority, model, recovery, Recourse or controller PASS. A hard or
execution failure stops this identity and requires route review rather than a
longer baseline.
