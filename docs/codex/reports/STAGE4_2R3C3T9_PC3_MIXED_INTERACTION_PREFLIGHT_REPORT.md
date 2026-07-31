# Stage4.2R3c3T9 PC3 and mixed-interaction preflight report

## Result

The frozen T9 action-design preflight passed every preregistered gate:

```text
actuator                         delay 0 / slew 1.0   delay 2 / slew 0.9
PC3 singular value                         1.134704              0.777812
minimum four-direction coverage            0.999912              0.995362
complete action rank                          12/12                 12/12
complete normalized condition               2.55106               2.55106
selected action rank                            9/9                   9/9
selected normalized condition               1.23002               1.23002
factorial common amplitude                  0.010607              0.010607
```

T6 source/PC1/PC2 schedules were reproduced with zero maximum error. Maximum
candidate/old-span orthogonality error was below `2.5e-17`, and every
standalone/factorial schedule is bounded, delay-causal, zero-net, and begins
neutralizing only at physical state 39.

This result proves action-schedule novelty and a valid prospective
mixed-action experiment. It does not prove a useful PC3 plant response, a
small interaction, response conditioning, hidden-history robustness, formal
control, or R3c4 feasibility.

## Exact revision and paths

```text
local branch
  codex/stage4_2r3c3t9-mixed-interaction-preflight

implementation/design commit
  cbb970b

remote project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

remote compact output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t9_preflights/
  stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b/
  stage4_2r3c3t9_pc3_mixed_interaction_preflight_v1.json

remote execution log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b.log

remote validation log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t9_preflight_installed_validation_cbb970b.log
```

Exact hashes:

```text
preflight JSON
9a37168cce679df7deeb242bceb996c11f41bf9e589459e27386ece45f41e560

execution log
401ffb2c23c776c3dd25db575465eb3240d6fbc7605fd4498d8d734bd7cda7db

validation log
04b6b20ce90ec5d2f7f19c4240b8d20a0781daf9327cf29f548d021e0756e895
```

The compact local evidence is preserved under:

```text
docs/codex/audits/
stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b/
```

## Evidence and recomputation

The preflight authenticated:

```text
R17 expert raw                                             18/18
R3c1 exact restart control raw                             32/32
T3 eight-basis bank samples                                32/32
T6 preflight hash exact                                       yes
T7 feasibility hash exact                                     yes
T8 headroom diagnostic hash exact                             yes
```

The downloaded JSON was parsed independently. All serialized standalone and
factorial schedules were re-summed:

```text
issue rows per nonbaseline schedule                            41
formal L2 maximum                                           0.015
formal component maximum                              0.006592
cancellation component maximum                        0.003096
maximum absolute requested net                      1.31e-18
first cancellation physical state                            39
```

The output directory contains only one `196362`-byte compact JSON. No T9
Ray, gotsc, TSC, trajectory, raw, or snapshot process/artifact was created.

## Validation

Before deployment:

```text
Python compile                                                  PASS
all repository JSON parse                         2416 files, PASS
focused T9 tests                                      4/4 PASS
complete local tests                               587/587 PASS
package/checksum inventory                         203/203 exact
empty-directory direct-copy test                  587/587 PASS
```

After direct uncompressed patch deployment:

```text
previous remote package                            199/199 exact
new remote package                                 203/203 exact
all declared shell syntax                                   PASS
package scientific guards                                  PASS
T6 compatibility focused tests                         8/8 PASS
complete server tests                              587/587 PASS
```

No package, test, or preflight failure occurred. Several command-construction
attempts failed locally before SSH execution because of PowerShell quoting or
a reserved variable name; they changed no remote scientific state. One
read-only remote query initially used the system Python instead of the frozen
virtualenv and was rerun correctly. These are tooling/environment errors, not
experiment results.

## Classification

```text
runtime/environment error affecting preflight science       none
deployment/package error                                    none
raw/snapshot corruption                                     none
statistics/reporting error                                  none
action-design defect                                        none found
real T9 plant response                                      not run
real closed-loop controller                                 not run
```

The T9 real identification identity may now be implemented, but only with the
frozen 224-task matrix:

```text
32 extended baselines
64 standalone PC3 signed probes
128 direct stress-by-PC3 factorial probes
```

R3c4 remains unauthorized. BC, DAgger, and residual RL remain prohibited.
