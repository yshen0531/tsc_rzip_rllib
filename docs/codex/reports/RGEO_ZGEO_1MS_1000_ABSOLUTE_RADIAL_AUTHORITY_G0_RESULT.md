# Fixed-1000 absolute radial Authority G0 result

G0 completed all 8 authentic rollouts and 512/512 plant advances.  The
independent server-side raw audit passed 520 states, 512 issued Card15 checks
and 504 later observed-slew checks.  The depth-16 replay had zero R/Z/Ip,
14-coil and 48-wire difference.  There was no runtime, solver, interface,
current, limiter, raw or reporting failure.

The frozen scientific route is nevertheless
`ONE_MS_NR1000G0_ABSOLUTE_RADIAL_AUTHORITY_INSUFFICIENT_REDESIGN`.  Terminal
state56--64 metrics were:

| path | worst distance (mm) | max speed (m/s) | distance gain vs q0 | speed gain (m/s) | max Ip fraction |
|---|---:|---:|---:|---:|---:|
| matched q0 | 23.538658 | 0.318027 | 0 | 0 | 0.029654 |
| depth04 | 22.739890 | 0.279082 | 3.393% | 0.038946 | 0.026206 |
| depth08 | 22.087664 | 0.273101 | 6.164% | 0.044926 | 0.022669 |
| depth12 | 21.441638 | 0.461217 | 8.909% | -0.143191 | 0.019054 |
| depth16 | 20.949227 | 0.485320 | 11.001% | -0.167293 | 0.015229 |
| depth24 | 20.638224 | 0.171123 | 12.322% | 0.146904 | 0.007187 |
| depth32 | 20.134588 | 0.141825 | 14.462% | 0.176202 | 0.001955 |

Depth32 missed the preregistered 15% distance gate by 0.5384 percentage
points.  The gate is not weakened after seeing the result.  No candidate
reached the 5 mm / 0.1 m/s diagnostic capture gate.

The finite physical conclusion is narrower and more useful than "no
authority": sustained even-plus allocation materially reduces both late
distance and speed, and releases Ip offset, but a single issue-0 ramp followed
by permanent hold does not meet the absolute radial Authority contract.
Depth12/16 also show that terminal speed is non-monotone in depth, so deeper
amplitude alone is not a justified repair.

This exact depth matrix is closed.  There will be no depth36/40 or adjacent
duration ladder.  The authorized successor is a separately frozen nominal
schedule/action-semantics redesign that combines the already measured early
even-minus transport benefit with the late even-plus braking benefit.  It
must remain a fixed-budget Authority experiment; it cannot train a model or
claim hold, Recourse, 2-D tracking or controller qualification.

Compact result SHA-256 is `2c363a4631b1981aa5d86e0abd9ee1a962ceccd934c4b6a053fb9464481777c6`;
independent audit SHA-256 is `c658dac8f84e4c4a768232887fa9102b76659303378facb7e2db9cdbd7d136a4`.
