# Stage4.2R3c3T11 persistent-step identification report

## Result

Stage4.2R3c3T11 completed all 416 authentic restart TSC rollouts. The final
classification is a clean **identification-design FAIL** caused only by the
frozen six-basis response-conditioning gate:

```text
execution                                                  416/416 PASS
extended baseline prefix                                     32/32 PASS
central symmetry                                            192/192 PASS
matched hidden-history response                               96/96 PASS
velocity response rank 6                                      32/32 PASS
velocity condition <= 25                                      25/32 FAIL
maximum velocity condition                                  38.9150751
maximum current utilization                             0.3904 <= 0.55
```

This is not a runtime, deployment, restart, causality, solver, raw-data,
snapshot, statistics, or reporting failure. It is also not a real MPC
failure: T11 is an identification experiment and executes no candidate MPC.

## Provenance

```text
local branch
  codex/stage4_2r3c3t11-persistent-step-identification

implementation commit
  322ade2  feat(stage4.2r3c3t11): implement persistent-step identification

deployed package/inventory fix
  40944f9  fix(stage4.2r3c3t11): use ordinal package inventory

forensics evidence checkpoint
  5e9d3d0  docs(stage4.2r3c3t11): record final identification forensics

PACKAGE_MANIFEST.json
  951aa9abc92603859382fc02643c4f6e0d2c696b76868be743bf56ea9fb17b84

SHA256SUMS
  90761c1e37983323104dc00d7fd1c2d803f229a7a2007b0467cd8424f8623980

runtime package fingerprint
  7e5020174ac7b2ec89e3a0f471b1a4e7f21c4aa69eb5aaad8fe829c54fe77a53
```

The server package passed 243/243 hashes, shell syntax, Python compile/JSON,
the focused suites, and 618/618 complete tests. The installed validation log
SHA-256 is
`dd340ad728d7bf97213bbe6003a9d72500b6a942983e7086a695cac0cccf7765`.

Remote identities:

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t11_runs/
  stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9

campaign log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t11_persistent_step_response_identification_20260731_224518.log

independent audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t11_audits/
  stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9
```

The campaign used the frozen `128 + 128 + 128 + 32` Ray batches and wrote
exactly 32 extended baselines plus 384 signed probes. No task was rerun or
resumed after completion.

## Raw, snapshot, and manifest forensics

The 416 JSON.GZ files total 19,273,198 bytes and remain on the server. An
independent server-side inventory rehashed every raw file and reproduced the
reported digest exactly:

```text
raw inventory digest
  f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3

raw count / parse errors
  416 / 0

snapshot identities
  8 expected / 8 actual / 8 passed / 0 failed

reported summary exact on raw recomputation
  yes
```

The runtime and audit package fingerprints are identical, with zero changed
paths. The resolved config, control specs, formal timing contract, source
fingerprints, preflight, run manifest, filenames, experiment IDs, and
snapshot identities all match exactly. The independent server audit SHA-256
is `02933f9ee05f91f6db565e955e0106c65dc6591f273fb562e68ac2767d28c19c`.

Only compact derived evidence was downloaded. The raw tree, full 479,503-byte
server audit, and full 372,626-byte run inventory were intentionally not
downloaded. The compact forensic JSON SHA-256 is
`8cf365fcac69924c09bae51c9c5c1c3cc003959ff3e7a92111b387316a8b617b`;
all 14 downloaded load-bearing hashes matched it.

## Error classification

```text
runtime or environment errors                                  0
packaging/import/deployment errors in valid campaign           0
raw or snapshot corruption                                     0
plant restart fidelity failures                                0
controller causality failures                                  0
probe execution failures                                       0
baseline prefix mismatches                                     0
solver failures                                                0
forbidden controller inputs                                    0
statistics/reporting errors                                    0
design-gate failures                                           1
```

Before the valid campaign, the first staging package exposed a Windows
culture-sort versus Python ordinal-sort inventory mismatch. Commit `40944f9`
fixed only package inventory ordering; it ran no TSC and changed no
experiment semantics. A first launch command then stopped on shell quoting
before creating a PID or raw result. The corrected guarded launch ran the
campaign exactly once. A later read-only Ray task-summary command found that
the optional dashboard API was not enabled on port 8265; this monitoring
query error did not affect Ray workers or the campaign.

## Failed response contexts

All 32 response matrices have numerical rank 6. Seven exceed the
preregistered unnormalized condition limit of 25:

| pair | history | target | delay/slew | condition | normalized diagnostic | max column cosine |
|---|---|---|---:|---:|---:|---:|
| p5_q1 | minus | RZ+10/-10 | 2 / 0.9 | 28.3233 | 4.7855 | 0.6765 |
| p5_q2 | minus | RZ+10/-10 | 2 / 0.9 | 27.5370 | 4.0618 | 0.6485 |
| p5_q2 | minus | nominal | 2 / 0.9 | 37.2147 | 4.2114 | 0.6977 |
| p9_q1 | minus | RZ+10/-10 | 0 / 1.0 | 38.9151 | 12.3019 | 0.9148 |
| p9_q1 | minus | nominal | 0 / 1.0 | 30.8280 | 12.1290 | 0.8816 |
| p9_q2 | minus | RZ+10/-10 | 0 / 1.0 | 37.6285 | 8.1948 | 0.9182 |
| p9_q2 | plus | RZ+10/-10 | 0 / 1.0 | 28.4875 | 4.2523 | 0.7097 |

An independent raw implementation formed R/Z velocities with a 10 ms
backward difference, computed signed odd responses, selected states 3
through the frozen formal endpoint, and ran SVD. It reproduced every reported
condition value with maximum absolute error `4.97e-14`.

The weak columns are context-dependent. For example, failed contexts contain
transport-mode-2 norms as low as `4.98e-4` to `8.79e-4`, while strong
transport/braking-mode-0 columns reach roughly `8e-3` to `1.35e-2`. Several
p9/minus contexts additionally have column cosines above `0.88`. Thus the
failure is not rank loss; it is real finite-envelope response magnitude
imbalance, sometimes combined with near-collinearity. Column-normalizing or
raising the threshold after seeing the outcome would change the frozen gate
and is forbidden.

## What passed, and what it does not prove

Central-symmetry maxima were well inside the frozen limits:

```text
velocity RMSE   0.00167873 <= 0.004 m/s
position RMSE   0.00008922 <= 0.0005 m
Ip RMSE         2.90650 <= 20 A
```

Matched-history response maxima also passed:

```text
velocity RMSE   0.00159814 <= 0.006 m/s
position RMSE   0.00024413 <= 0.001 m
Ip RMSE         3.39855 <= 40 A
```

These are finite development-envelope identification results only. They do
not independently prove hidden-history closed-loop robustness. Probe
trajectories remain forbidden from expert datasets.

Formal tracking was diagnostic only: 207/416 total trajectories passed,
including exactly 16/32 unprobed baselines and 191/384 probes. The 500 ms
observation horizon did not change the 250/270 ms arrival deadlines or the
350/370 ms hold endpoints and is not a long-hold validation.

## Decision and next stage

Do not build the T11 six-basis response bank, run prospective R3c4
feasibility, implement R3c4, or enter BC/DAgger/residual RL. The prerequisite
32/32 response-conditioning gate failed.

The next stage must be a new prospectively frozen time-localized
identification design. It must add genuinely new temporal shapes that improve
weak-mode authority and separate the p9/minus near-collinear responses while
retaining common causal schedules, exact restart, paired histories, current
limits, exact post-contract neutralization, and the immutable formal timing.
It may use T11 only as authenticated development evidence. It must not repair
this result by post-hoc column normalization, threshold relaxation, relabeling
an unrun phase, or amplitude-only rescaling of the failed basis.

No new real TSC experiment is authorized until that schedule and its
action-space novelty/current/downstream-identifiability gates are
preregistered independently of its outcomes.
