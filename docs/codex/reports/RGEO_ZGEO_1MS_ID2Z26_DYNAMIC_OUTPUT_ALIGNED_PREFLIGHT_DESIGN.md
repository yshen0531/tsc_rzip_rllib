# ID-2Z26 dynamic output-aligned allocation preflight design

ID-2Z26 is a zero-TSC, zero-fit exact-action gate.  It does not reopen or
reclassify ID-2Z25.  It constructs a new lineage with full-F through issue 31,
a `0.50F` transition center through issue 55, and a common held tail through
state 73.  Two new residual coordinates are frozen before execution:

```text
q_R = 0.5 * (r5 - r6)
q_Z = 0.5 * (r5 + r6)
```

Here `r5` is the exact p05-plus field increment and `r6` is the exact
half-scaled p06-plus field increment used in the prior centered construction.
These combinations are design seeds only.  The primary and independent
preflights must reconstruct them from tracked evidence and prove every
actual Card15 stream.

The prospective campaign has eleven 73-step rollouts: one matched transition
center, one zero-fit continuing-full-F diagnostic, two phases times two axes
times two sign orders, and one zero-fit replay.  Each branch holds one signed
coordinate for eight issues and its exact opposite for eight issues, returning
to the matched center target before the common tail.  No interpolation,
clipping, retry or future actual current is allowed.

PASS requires rank two, condition at most 1.2, every signed issue no larger
than 0.3 A, nonnegative absolute-current headroom, exact full-F prefix, exact
cumulative target closure and complete streams at both phases.  FAIL consumes
zero TSC and requires action/nominal redesign.  PASS authorizes only a
separately frozen fresh D0 campaign; it is not response, authority, capture,
recovery, model or controller evidence.
