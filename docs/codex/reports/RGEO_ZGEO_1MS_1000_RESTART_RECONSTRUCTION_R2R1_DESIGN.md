# Fixed-1000-ms restart reconstruction R2R1

R2 is final as `ONE_MS_NR1000S0R2_INITIAL_RECONSTRUCTION_FAIL`. Its first
full-input call reached internal time 0.10253 s in 180 s, produced a normal
progress trace and timed out under the inherited one-ms runner process budget.
It did not complete a state, start a second run, or run restart validation.
This is a runtime-budget design FAIL, not an input, TSC-physics, interface,
model or controller conclusion. R2 is not resumed.

R2R1 is a new identity. It preserves the exact R2 full non-restart input,
source hashes, semantic and time gates, two independent full runs, two
one-ms restarts, maximum four invocations, and no-retry rule. The only change
is `initial_tsc_timeout_s=2700`, prospectively chosen from R2's measured
progress before R2R1 execution. The two restart validations retain the source
config's 180-s bound.

PASS authorizes only a new canonical-source interface identity. It does not
qualify a model, teacher, Authority, Recourse, feedback, path or waypoint.
