# ID-2Z24 centered co-allocation preflight result

Date: 2026-08-21

ID-2Z24 stopped with route
`ONE_MS_ID2Z24_CENTERED_CARD15_LATTICE_FAIL_NO_TSC`. It ran zero TSC calls,
zero plant advances, zero fits, and read no calibration or holdout data. The
structurally separate recomputation passed and reproduced the same route.

The post-ID2Z23 attribution was reproduced exactly: omitted-F common action
energy was `0.6841139804`; the common R/Z response fractions were
`0.9141120219` at issue 24 and `0.8978133098` at issue 32; p05 odd response
cross-phase cosines were `0.9999975840` at h4 and `0.9999991376` at h8.

All six nominal-share candidates passed the local rank-three, condition,
signed-vertex slew and absolute-current checks. None passed the additional
requirement that eight independently quantized `N+s*r` increments followed
by eight independently quantized `N-s*r` increments land byte-for-byte on
the separately generated center baseline. The failure is accumulated Card15
rounding in the prospective action schedule, not a response or safety result.

The stage is frozen as a zero-TSC construction FAIL. It will not be silently
relabelled PASS. The authorized correction is a new pre-execution identity in
which the last opposite-sign slot targets the exact matched center field
directly. That finish remains subject to the unchanged `0.3 A` slew and
absolute-current gates, and its actual adjustment is reported. No plant gate,
data role, model role, amplitude grid, phase, duration, or rollout budget is
weakened.
