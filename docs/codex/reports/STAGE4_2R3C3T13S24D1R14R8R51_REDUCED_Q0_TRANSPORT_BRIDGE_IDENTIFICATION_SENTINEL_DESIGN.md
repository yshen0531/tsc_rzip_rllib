# Stage4.2R3c3T13S24D1R14R8R51 reduced q0-transport bridge identification sentinel design

Status: prospectively frozen on 2026-08-09 after final R8R49 offline evidence,
but before any R8R51 implementation, server offline gate, Ray, `gotsc`, TSC,
controller, plant step, raw trajectory, or response outcome.

## 1. Development evidence and new identity

R8R49 is immutable at:

```text
Q0_TO_TRANSPORT_BRIDGE_SENTINEL_OFFLINE_FAIL_NO_REAL_TSC
```

Its primary and independent offline constructions agreed exactly on 208/256
passes. The only 48 failures were `u0p50`, `u0p75`, and `v0p50` in all 16
contexts, solely because exact Card15 issue/return off-basis residual exceeded
the frozen 0.10 cap. R8R49 ran zero TSC, so no R8R51 physical response has
been observed.

R8R51 is a new experimental identity. It uses R8R49 only as disclosed
development screening of exact action representability. It does not relabel
R8R49 as a pass, weaken a gate, resume its identity, or claim independent
selection evidence.

The source gate must authenticate final R8R49 route plus these exact hashes:

```text
offline primary       8258e0369de1b79814efec2e3ec85bd843e37bc387b0d21fa4996e32de68d655
offline independent   d1dec48db8e915d673d2db7a4b5ea95ed316ba838cdc404cbbb2a1ad91c302f9
offline construction  fd112e5fdb1527059003cccf5bd2219e6f0fd175306aafe8edf71a4073a41002
all specs             fb4164bbe109a0994f5fd7c163d19e788be093d8b69e0adc37bbc5389f6f4afc
source authentication 75aeb74cbc70e4bc392dd9b1250c41d2768274bf7845252f7b020c8bcbf6aa9b
stage state           8afbfec8f9ba33cf7763cef8fe7bd06425f5a06890309892f9de251b97790962
stage manifest        a71349895dc20e17fb529bb1842f07d45bf6d1737a072e40420cc1bf90484044
```

Any mismatch blocks R8R51 before TSC.

## 2. Frozen finite matrix

Use the same 16 authenticated R8R31/R8R46 contexts and exactly these 13
nonzero R8R31 candidate IDs, in this order:

```text
d0m d0p d1p d2m d3m d3p
u1p00 u1p25 u1p50
v0p75 v1p00 v1p25 v1p50
```

The experiment therefore contains exactly:

```text
8 physical pairs x 2 histories x 13 candidates = 208 trajectories
```

No candidate or context may be removed after response inspection. The frozen
13x4 binary64 q matrix has:

```text
rank                                                   4
singular values
  [2.5248762345905194, 2.4109126902482387,
   1.4142135623730951, 1.4142135623730951]
condition number                         1.7853571071357124
float64 little-endian C-order SHA-256
  5d6b6c20a704eceda43db7cbaece445d1655a4d62da16d185b308bc27ed4b674
```

The corresponding 13x4 requested physical-coordinate matrix has rank four
and SHA-256
`82e26d01b53fc8bb986ab5a127f8400bc10dcd823a879450ab54275fc2e50543`.
The three excluded R8R49 candidates are repeated amplitudes of directions
already retained; all four independent q directions remain present.

## 3. Exact causal schedule

Each trajectory starts from its authentic source restart and preserves the
same source controller/action/state prefix through completed state 10. Then:

```text
task step 10  exact Card15 q0 hold at visible current
task step 11  no new transport action; exact q0 observation hold
task step 12  issue the assigned fixed nonzero candidate
state 13      required first physical effect of the task-12 issue
state 14      second response observation
task step 14  exact return to the stored pretransport Card15 center
steps 15..end exact stored-center refresh to original 35/37 horizon
```

The effect contract remains issue plus one. Pair/history labels, future
measurements, wire/vessel current, source outcomes, and formal labels are
forbidden controller inputs. Every worker is a fresh controller actor and a
fresh TSC process with the authentic full plant snapshot.

## 4. Unchanged action and safety gates

The dual offline construction must pass all 208 cells before real execution:

```text
exact Card15 q0, issue, observation, return, and later refresh     208/208
candidate identity and exact frozen coordinate                     208/208
incremental normalized action Linf <= 0.25                         208/208
total normalized action abs <= 1.0                                 208/208
predicted current utilization <= 0.55                              208/208
desired/applied current cosine >= 0.98                             208/208
relative off-basis residual <= 0.10                                208/208
no current clipping or saturation                                  208/208
```

No threshold may be widened. A failed offline cell permanently stops R8R51
without TSC. During real execution, the same gates run before each plant
advance. A failed action is rejected and no later plant step is permitted.

## 5. Real execution and raw audit

After primary/independent offline agreement and explicit authorization, run
exactly one fresh 208-trajectory campaign. Resume is allowed only for missing
specifications with unchanged package, controller, source, matrix, schedule,
and gates. Do not rerun a complete trajectory.

Primary and structurally independent raw audits must authenticate and
recompute:

```text
strict raw parse and immutable spec identity                       208/208
authentic plant restart and source state/action prefix              208/208
causal/forbidden-input trace                                        208/208
within-context q0 prefix identity through completed state 12        208/208
exact assigned candidate issue at task step 12                      208/208
first effect at state 13                                            208/208
finite state-13 and state-14 R/Z/Ip response                        208/208
exact stored-center return at task step 14                          208/208
full 35/37-step safe horizon                                        208/208
current utilization <= 0.55, zero clipping/saturation/abnormal      208/208
context/candidate bridge coverage                                   208/208
raw response and prefix digests                                      exact
```

Any runtime/parse/source/restart/causality/integrity failure uses an execution
failure route and stops. Any genuine action/current/return/plant safety gate
failure uses a safety/design route. These classifications must not be merged.

## 6. Routes

```text
R8R49/source identity mismatch
  REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_BLOCKED_BY_SOURCE

any primary/independent offline construction failure
  REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_OFFLINE_FAIL_NO_REAL_TSC

runtime, raw, restart, causality, or integrity failure
  REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_EXECUTION_FAIL_STOP

real action/current/return/plant safety gate failure
  REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_SAFETY_FAIL_REDESIGN

all offline, execution, raw, and independent gates pass
  REDUCED_Q0_TRANSPORT_BRIDGE_IDENTIFICATION_COMPLETE_MODEL_PREFLIGHT_REQUIRED
```

A PASS is only a fresh finite q0-to-first-transport bridge-identification
result. It authorizes only the separately frozen conditional R8R52 zero-TSC
model/tube preflight.

## 7. Formal and learning boundary

Formal tracking is diagnostic only. Arrival remains by 250 ms with hold
through 350 ms for slew 1.0/1.1, and by 270 ms with hold through 370 ms for
slew 0.9, using 30 mm R/Z, 0.1 m/s speed, 10 kA Ip, and the frozen three-step
arrival streak. The 35/37-step horizon does not expand the deadline.

Every R8R51 trajectory is an identification probe and is forbidden from
expert, BC, DAgger, residual-RL, or other learning data. R8R51 is not a model,
controller, real MPC, long-hold, robustness, plant-reachability, or Gate A
qualification.
