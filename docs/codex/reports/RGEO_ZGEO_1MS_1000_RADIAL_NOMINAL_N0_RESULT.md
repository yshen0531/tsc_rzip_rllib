# Fixed-1000 radial nominal N0 result

N0 completed five authentic rollouts and all 320 authorized plant advances.
The depth-12 critical replay is exact and the independent raw audit passed
all 325 states, 320 action checks and 315 later observed-slew checks.

The preregistered scientific gate failed. Terminal state56--64 results were:

| depth | worst distance (mm) | max speed (m/s) | distance change vs q0 | speed change vs q0 (m/s) |
|---:|---:|---:|---:|---:|
| 4 | 23.654815 | 0.379450 | -0.49% | -0.061423 |
| 8 | 24.284962 | 0.378249 | -3.17% | -0.060222 |
| 12 | 24.903398 | 0.379654 | -5.80% | -0.061627 |
| 16 | 25.373873 | 0.413895 | -7.80% | -0.095868 |

Negative changes mean worse. The matched q0 window is `23.538658 mm` and
`0.318027 m/s`. No candidate met the stronger capture diagnostic.

The trajectories nevertheless show a deterministic transient response: the
depth-16 path was about `1.63 mm` closer than q0 around state16 before the
late rebound. The finite conclusion is therefore that issue-0 even-minus
ramp-then-hold is not a radial nominal, not that the coordinate has no plant
effect. These prospectively fit-eligible negative trajectories should be
used by the bounded causal short-horizon model; the static depth ladder is
closed.
