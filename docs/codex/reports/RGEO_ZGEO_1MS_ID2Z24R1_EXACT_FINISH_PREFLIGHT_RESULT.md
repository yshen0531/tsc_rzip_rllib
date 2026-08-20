# ID-2Z24R1 exact-finish preflight result

Date: 2026-08-21

ID2Z24R1 executed zero TSC calls, zero plant advances and zero fits. Its
primary preflight retained FAIL: exact final-target closure succeeded, but
some last-slot issued deltas were `0.4--1.0 A`, above the unchanged `0.3 A`
gate. This rules out concentrating the accumulated quantization correction in
one final slot.

The first R1 independent implementation incorrectly skipped the slew check on
that exact-finish slot and therefore disagreed with the primary. The focused
server test rejected the audit with `SELECTED_SHARE`, `PRIMARY_ROUTE` and
`PRIMARY_VERDICT`; no audit PASS is claimed. The primary failure is directly
supported by its per-stream issued deltas and is not weakened by this auditor
bug.

R1 is an implementation/design FAIL, not plant, runtime, authority, capture,
model or controller evidence. The separately identified R2 distributes the
same exact endpoint across all eight already frozen return slots and checks
every resulting issued delta independently. It adds no TSC rollout, phase,
amplitude, duration or data permission.
