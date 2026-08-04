# Stage4.2R3c3T13S24D1R14R3 sign-split response feasibility design

Frozen: 2026-08-04, after the final D1R14R2 primary and independent raw
forensics and its separately labelled posthoc architecture diagnostic, but
before D1R14R3 implementation or execution.

## Purpose and scientific boundary

D1R14R2 proved that the fixed four-direction mixed-basis response is not
centrally symmetric throughout the finite eight-context envelope. Its frozen
route remains:

```text
MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED
```

D1R14R3 does not weaken, remove, reinterpret, or rerun that gate. It is a
zero-new-TSC raw-data audit of a different prospective architecture: separate
positive and negative local response branches about the same authentic zero
baseline. It asks only whether each sign branch independently has finite
signal and four conditioned directions in the already sampled local
development envelope.

R3 is not a controller, model fit, time-distributed identification result,
MPC feasibility result, hidden-history robustness result, expert dataset, BC,
DAgger, or RL stage. No R2 probe trajectory may enter an expert dataset.

## Immutable R2 evidence boundary

The audit must authenticate this exact server source and result boundary:

```text
R2 design checkpoint                                      5f7fb80
R2 implementation checkpoint                              e7fe6c8
R2 package checkpoint                                     ca2815a
R2 package fingerprint digest
  d1c142aac0469822808f1440f718e6f5389d62ba6476bb5428f5db050187247d
R2 PACKAGE_MANIFEST.json SHA-256
  79fb42b5066c722066fa99c0b63668b1497ff8edd558650a7a79bb50a8c163f1
R2 SHA256SUMS SHA-256
  9c067fc5b6edf5d0cbb905a27a1d14b942b64741fb46f3f5e05bbb447c82c0c3
fixed mixed-basis matrix digest
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
spec digest
  ff5e29f1ebb94dd2c8b9602d85021938ad578be37765a297d6d7df562e39bb35
raw files / bytes                                      72 / 2,254,876
raw inventory digest
  c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649
final_result.json SHA-256
  3df193e52ee0ce8fe72620af9f72597f58af4419c6386c37d62fb051bcefd79a
server_independent_forensics_v1.json SHA-256
  68f21e95694c607084b9cc7d39732bcda05d57a14f6f3cc4f1e78e8941e7e2df
stage_state.json SHA-256
  46552980d1514eec75fc5df9b76b7c9c4c49aa0ec13f180dc7fdc3113d1468c6
```

The canonical server run is:

```text
$HOME/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r2_runs/
  stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1
```

R3 must strictly parse and hash all 72 raw JSON files, the eight restart
snapshots, specs, execution, manifest, state, primary result, independent
result, config, and complete offline/real/postprocess logs. It must repeat all
R2 source-package, R1A, D1R13, D1R11, restart, prefix, causality, issue,
cancellation, current, forbidden-input, horizon, raw-integrity, and safety
authentications. It may not accept the R2 summary or verdict as raw evidence.

The posthoc diagnostic has SHA-256:

```text
2a843ca4f9d05e1f5fbb7036313652fce2093062bf7a4b1fa969ad599f406f61
```

It may be authenticated as design provenance, but none of its saved branch
metrics, rows, counts, or conclusions may be used as D1R14R3 numerical input.
All R3 metrics must be independently recomputed from raw trajectories.

## Mandatory reproduction of the failed R2 model

Before evaluating the new architecture, both R3 implementations must
recompute R2's original shared odd-response geometry over normalized
`(R,Z,vR,vZ,Ip)` from authentic state 11 through the actual 35/37 endpoint:

```text
output scales                                      0.03, 0.03, 0.1, 0.1, 10000
minimum odd peak                                      0.005466000000009519
maximum even/odd peak ratio                              0.8528017842241936
maximum odd-column condition number                       8.802962394477525
signal gate                                                   32 / 32
central-symmetry gate                                        28 / 32  FAIL
rank-four context gate                                          8 / 8
condition <= 20 context gate                                    8 / 8
```

The four failed context/direction/sign-independent pairs and their raw
even/odd ratios must agree with the frozen R2 result. Any mismatch is a source
or reproduction failure and prevents sign-split evaluation. Reproducing this
failure is required evidence, not a failure of R3.

## Fixed sign-split construction

For each of the eight authenticated contexts, let `Y0(t)` be its zero-baseline
trajectory, `Y+d(t)` the positive direction `d` trajectory, and `Y-d(t)` the
negative trajectory. No interpolation, smoothing, phase shift, truncation,
outlier removal, scale search, direction search, or context pooling is
allowed.

For each sign and direction, construct exactly:

```text
positive branch column d = normalize_outputs(Y+d(t) - Y0(t))
negative branch column d = normalize_outputs(Y0(t) - Y-d(t))
t = authentic state 11 through the member's actual endpoint, inclusive
```

The negative response is oriented toward the corresponding positive input
coordinate solely to make column orientation consistent. Positive and
negative branches remain separate. They may not be averaged, pooled, or
substituted for one another.

For a branch, flatten the complete five-output time history of each direction
in fixed state-major/output-major order to form four columns. Compute each
column's raw L2 norm, divide each nonzero column by its own L2 norm, and apply
SVD to the resulting matrix. Rank uses relative tolerance `1e-10` times the
largest singular value. Condition number is largest divided by smallest
singular value.

## Frozen sign-split gates

There are exactly `8 contexts x 2 signs = 16` branches and 64 branch-direction
columns. Every branch and column must pass:

```text
finite values and complete authentic horizon                         required
peak absolute normalized five-output response per direction          >= 0.005
four nonzero L2 column norms                                          required
rank at relative tolerance 1e-10                                         4 / 4
unit-column condition number                                             <= 20
```

The fixed response scales remain:

```text
R 0.03 m, Z 0.03 m, vR 0.1 m/s, vZ 0.1 m/s, Ip 10000 A
```

The actual issued requested coordinates and the actual four physical effect
fields must also be exact sign opposites for all 32 signed pairs. This is an
action-construction authentication, not a replacement for R2's failed plant
response central-symmetry gate.

Because the sign-split model is explicitly piecewise, cross-sign central
symmetry is reported and required to reproduce R2's 28/32 failure, but is not
a sign-split acceptance gate. This architecture change is the preregistered
scientific question of R3; it is not an after-result threshold change.

## Primary and independent audit contract

The primary audit and a structurally separate independent audit must be
implemented, hashed, tested, and packaged before formal execution. Both read
the full raw boundary directly and must agree on:

- every authenticated input SHA and raw inventory;
- exact R2 shared-model reproduction and four failed pairs;
- all 64 direction peaks and L2 norms;
- all 16 ranks, singular values, and condition numbers;
- issued-coordinate and physical-field sign symmetry;
- failures, counts, extrema, route, and audit completion.

The independent implementation must not import the primary R3 computation
module or consume the primary R3 output to calculate its metrics. Comparing
the two completed outputs is a separate final step. JSON parsing must reject
nonstandard constants and duplicate keys, and every computed value must be
finite.

## Execution and storage contract

D1R14R3 creates zero new TSC trajectories and must never call `gotsc`. Its
offline spec count and real-TSC task count are both zero. Heavy raw processing
runs server-side with the existing project virtual environment. Large raw,
snapshots, and trajectory files remain on the server; only compact audit JSON,
inventories/hashes, configuration, logs, and the final report are transferred
directly without compression.

Before server execution, R3 must pass local compile/JSON, focused and complete
tests, import closure, package manifest/checksums, source-fingerprint tests,
and an empty-directory deployment simulation. The installed package must pass
remote path preflight, `bash -n`, package verification, and import/compile with
the existing server virtual environment. No global Python, Git, network, or
undeclared source tree may be used.

## Formal timing and conclusions not authorized

The immutable formal contract remains unchanged:

```text
slew 1.0/1.1: arrive by state 25 and hold/evaluate through state 35
slew 0.9:     arrive by state 27 and hold/evaluate through state 37
R/Z 0.03 m, speed 0.1 m/s, Ip 10000 A, arrival streak 3
```

R3 performs no control and therefore cannot pass or fail formal tracking. It
cannot establish transport controllability, time-shift invariance, prediction
accuracy, MPC feasibility, authentic closed-loop control, hidden-history
robustness, continuously varying parameter robustness, noise tolerance,
disturbance recovery, long hold, or readiness for RL.

## Frozen routes

```text
source/package/raw/safety authentication failure
  SIGN_SPLIT_RESPONSE_FEASIBILITY_SOURCE_FAIL_NO_TSC

original R2 shared-model metrics or failed pairs not reproduced exactly
  SIGN_SPLIT_RESPONSE_FEASIBILITY_R2_REPRODUCTION_FAIL_NO_TSC

any of 64 signal, 16 rank, or 16 condition gates fails
  SIGN_SPLIT_RESPONSE_FEASIBILITY_BRANCH_FAIL_REDESIGN_REQUIRED

all source, reproduction, issued-symmetry, and sign-split gates pass
  SIGN_SPLIT_RESPONSE_FEASIBILITY_PASS_TIME_SHIFT_SENTINEL_DESIGN_REQUIRED
```

A PASS authorizes only prospective design of a fresh authentic, independently
cancelled, time-shifted sign-split safety/identification sentinel. It does not
authorize that real-TSC campaign itself, response fitting, controller or MPC
implementation, expert data, BC, DAgger, or bounded residual RL.

