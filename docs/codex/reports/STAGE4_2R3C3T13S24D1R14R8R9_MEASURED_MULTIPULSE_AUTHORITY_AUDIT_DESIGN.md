# Stage4.2R3c3T13S24D1R14R8R9 measured multipulse authority audit design

## 1. Frozen question

R8R8 stopped before TSC because its frozen robust objective selected zero at
all 64 decision origins. The aggregate R8R7 formal diagnostics are already
public: 6/16 baselines and 12/32 fixed multipulse trajectories passed. Those
aggregates do not reveal whether a measured schedule repaired a failed
baseline, preserved only the same passes, or exchanged repairs for regressions.

Before inspecting that context-level mapping, R8R9 freezes this question:

```text
Does the already measured canonical-scale four-pulse alphabet contain any
real formal-control authority beyond its matching zero-action baseline?
```

R8R9 is a read-only route discriminator. It is not MPC, a controller run, a
new identification, a robustness qualification, Gate A, or learning.

## 2. Immutable sources

R8R9 reads the accepted R8R7 v1 run in place and authenticates:

```text
all / baseline / multipulse specs               exact SHA-256
baseline primary / independent raw audits       exact SHA-256
multipulse primary / independent raw audits     exact SHA-256
final report / stage manifest / stage state     exact SHA-256
baseline raw inventory                 16 files / 487298 bytes
multipulse raw inventory               32 files / 1068664 bytes
R8R7 final route and scientific PASS                 exact
```

It also authenticates the accepted R8R8 v2 primary detailed/summary, corrected
independent audit, manifest, and state. R8R8 must remain a zero-TSC, zero-raw
offline failure with 0/64 nonzero selections. The preserved pre-report-fix
independent artifact is evidence only and is not a scientific source.

All 48 R8R7 JSON.GZ files are strictly parsed on the server. No large raw file
is copied locally.

## 3. Frozen computations

For every R8R7 specification, reconstruct the unchanged formal evaluator from
the authenticated source context and evaluate raw R/Z/Ip twice:

1. the compact algebraic `FormalEvaluator.evaluate` path; and
2. the existing full tracking-metric path used by the source campaign.

Pass booleans, minimum signed margin, mean signed margin, and selected arrival
time must agree within absolute tolerance `1e-12` for all 48 trajectories.

Group results only by the already public physical context key
`(pair_id, history_member)`. For each of 16 contexts report:

```text
baseline formal result and signed margins
both measured schedule formal results and signed margins
best measured schedule by minimum margin, then mean margin, then schedule index
best schedule minimum-margin gain over baseline
whether a failed baseline is repaired by either schedule
whether either schedule strictly improves the baseline minimum margin
```

The context-level outcome is used only after every source, raw, and metric-
equivalence gate passes.

R8R8 score attribution is independently recomputed from its 576 stored forecast
rows for the frozen robust score, point-only diagnostic, and common-static-tube
diagnostic. It may explain the zero selection but cannot change any R8R8 gate.

## 4. Prospective gates and routes

Integrity gates:

```text
R8R7 source/hash/route/raw authentication                  PASS
R8R8 source/hash/route/zero-TSC authentication             PASS
strict raw parse and finite trajectories                    48/48
dual formal-metric equivalence                              48/48
known aggregate reproduction           baseline 6/16, multipulse 12/32
R8R8 robust selection reproduction                          0/64
new raw / Ray / gotsc / TSC / controller / plant steps       0/0/0/0/0/0
```

Measured-authority scientific gate:

```text
failed R8R7 baselines                                      10
failed baselines repaired by at least one measured schedule >= 1
measured-oracle formal pass contexts                       >= 7/16
```

The oracle includes the unchanged baseline as a do-nothing option, so its
formal pass count cannot regress. It is an authority diagnostic only; it does
not prove that a causal selector can identify the winning schedule.

Routes are frozen as:

```text
source, raw, metric-equivalence, or aggregate mismatch
  MEASURED_MULTIPULSE_AUTHORITY_SOURCE_OR_AUDIT_FAIL_NO_TSC

integrity passes but no measured formal repair
  MEASURED_MULTIPULSE_FORMAL_AUTHORITY_INSUFFICIENT_ACTION_REDESIGN_REQUIRED

at least one measured repair and oracle count >= 7/16
  MEASURED_MULTIPULSE_AUTHORITY_PRESENT_CAUSAL_SELECTOR_DESIGN_REQUIRED
```

A PASS authorizes only a separately frozen causal selector/controller design.
A FAIL requires a new action architecture or identification; it does not prove
global plant unreachability. Neither route authorizes expert data, BC, DAgger,
residual RL, Gate A, or reuse of any probe trajectory as a demonstration.

## 5. Execution and evidence policy

Run only with the existing server virtual environment. Read large raw in place
and download only compact JSON/log evidence. Use direct file transfer without
local compression or extraction. Primary output and a source-independent
postcheck must use distinct filenames. Any implementation/reporting error is
classified separately and cannot be converted into a scientific result.
