# Stage4.2R3c3T13S24D1R14R7R1 forensic report

## Final result

D1R14R7R1 completed its zero-new-TSC continuous-lag response-model study and
is final as:

```text
CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_FAIL_BROADER_DECONFOUNDED_IDENTIFICATION_REQUIRED
```

The continuous temporal parameterization repaired R7's structural lag-26/27
coverage defect. All four nested whole-pair folds were defined, all 256 outer
predictions were finite, and the primary and structurally independent
implementations agreed within the frozen `1e-10` relative / `1e-12` absolute
tolerance. The fitted center nevertheless failed the unchanged response
gates. This is a causal response-model design failure, not a runtime,
deployment, source-authentication, raw-corruption, statistics, reporting,
controller, plant-restart, control, or MPC failure.

No controller, Ray, `gotsc`, TSC, or plant step ran. No new raw was created.
All R2/R4/R6 probe raw remains forbidden from expert datasets.

## Exact implementation and paths

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition

R7 structural-failure / R7R1 design checkpoint
  81552da

R7R1 implementation checkpoint
  8087a1c

R7R1 package checkpoint
  3c90f21

package revision
  r42r3c3t13s24d1r14r7r1_continuous_lag_response_model_v1

manifest SHA-256
  42ef999cdd3e6135c562c15111762a97332fc35dac5c8535828edfa0d4f549c5

SHA256SUMS SHA-256
  755e1e29d35d587cb0d44431f07330b2cd8bea56cd62888327904e12d0f6477f

remote staging
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s24d1r14r7r1_3c90f21_v1

remote output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r7r1_audits/
  stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model_20260804_3c90f21_v1

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r7r1_offline_20260804_3c90f21_v1.log

installed-validation log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r7r1_installed_validation_20260804_3c90f21_v1.log
```

The 888-file package was transferred directly without an archive. Its empty
directory simulation, staging installation, and canonical installation each
verified every declared hash. The complete local, staging, and installed
suites passed `1131/1131`; the isolated/Linux suites had one expected skip.
All 9,773 repository-local JSON files parsed locally, all 98 declared package
JSON files parsed after installation, and compile/import closure passed using
only the project/server virtual environments.

## Source and output inventory

The exact authenticated response bank is unchanged from R7:

```text
source raw read in place                           320
R2 / R4 / R6 source raw                  72 / 200 / 48
deconfounded response rows                         256
contexts / physical pairs                         8 / 4
new raw / controller / plant / TSC          all zero
bank digest
  e7c2b1725ecdbeb5618e6ed9ae1345b7a752d8dc68e823bc2451723c5bd71694
```

Primary output inventory before descriptive forensics:

```text
detailed  1,366,851 bytes
  8e46e13a985ad701c8ddb5bedfa58da723fb392e0ebca40d7dc876b846c8ab03
independent  1,304,935 bytes
  53c23fd7f31d13bb48b87f21b1a20918e103f87e514291925acb5144d7bcd03c
manifest  1,056 bytes
  2007d104e21c0f26e9f3fba54805caed4e76f3cd4b9a1e7ec73e2cb314f82d2c
summary  3,150 bytes
  78f6e74f9fbc1d30fe08063da7a60453cde53e8d23135281bfef1c0eecbc3b8d
```

The large detailed and independent outputs remain server-side. The compact
summary, manifest, log, and server-side descriptive forensics are in:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r7r1_20260804_3c90f21/
```

The compact forensics SHA-256 is
`4a43aba667f0f33c3d52d95edf6de5a8f5a42eac56c3588b51eaeeb236d6971c`.

## Recomputed gates

```text
finite predictions                                  256 / 256
all response gates                                  150 / 256
relative-L2 gate                                    206 / 256
cosine gate                                         161 / 256
peak-ratio gate                                     196 / 256
scaled point-error gate                             256 / 256
tube cap                                                   PASS

maximum relative L2                                2.8666592379
minimum response cosine                            0.1899193709
peak-ratio range                         0.1601688053--3.2735052329
maximum scaled point error                         0.0300526710

predicted signal                                    256 / 256
predicted rank four                                  64 / 64
predicted condition <= 20                            64 / 64
maximum predicted condition                        15.4034595026
minimum predicted peak                              0.0035202855
```

Whole-pair pass counts were `48/64`, `50/64`, `30/64`, and `22/64`.
Direction pass counts were `10/64`, `47/64`, `52/64`, and `41/64` for
directions zero through three. Issue-step pass counts increased from `23/64`
at state 10 to `51/64` at state 22. The error is therefore systematic across
held physical pairs, early state, and action direction; it is not one damaged
row or a summary artifact.

## Post-result diagnostics and boundary

A labelled retrospective diagnostic authenticated the exact matched R4/R6
direction-zero requests. R6 is exactly `1.5x` R4 in requested coordinates for
48/48 matched context/time/sign rows. Scaling the measured R4 response by
1.5 has median relative error `0.1001449319`, but the two p9 physical pairs
reach `0.5005200010` and `0.8482887417`. Thus the omitted request amplitude is
a real confounder, while a globally linear amplitude correction is also
insufficient. This diagnostic SHA-256 is
`cea6b8c0d36685868c10cc1dfd87f6cee1a29de620a342f8ae780d9e71d3aaa9`.

A second retrospective screen evaluated R7's nonlinear context kernel with a
fixed tail extrapolation. Its best development-only candidate improved to
`218/256`, but directions one through three still passed only `165/192`; it
cannot rescue R7 or R7R1. Its SHA-256 is
`70b7dc6a54a3eefc159abe2fe11938b53167fc1c3f1bd0290bee6dca5d51da47`.

These post-result screens are architecture diagnostics, not validation and
not route passes. They motivate using the already authenticated full 304-row
amplitude-paired bank, explicit revealed request scale, the complete causal
visible history, a nonlinear context model, and an independently defined
tail. If that zero-new-TSC development stage still fails unchanged gates, a
new broader deconfounded identification campaign is required before any MPC.

## Classification and next action

```text
runtime/environment error                         no
packaging/import/deployment error                 no
source authentication or raw corruption          no
statistics/reporting error                        no
undefined temporal tail                           repaired
causal response-center model design failure       yes
new controller / plant / TSC result               none; not run
real closed-loop or restart conclusion            none
```

The next stage is the prospectively frozen zero-new-TSC D1R14R7R2
action-conditioned full-history kernel audit. It may authorize only design of
a fresh authentic multi-pulse validation sentinel. Model fitting, MPC,
expert data, BC, DAgger, bounded residual RL, and all later robustness claims
remain blocked.
