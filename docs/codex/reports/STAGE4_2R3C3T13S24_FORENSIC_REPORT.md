# Stage4.2R3c3T13S24 final training-boundary forensic report

## Result

The real S24 training boundary is complete and immutable. It did not reach
model fitting, calibration, or holdout. The coarse campaign route is
`SEQUENTIAL_IDENTIFICATION_RUNTIME_FAIL`, but independent reconstruction from
all raw files proves that the terminal scientific cause is an action-schedule
design failure, not a TSC/runtime, restart, causality, corruption, or reporting
failure.

```text
active raw                                             600 / 600
successful authentic training baselines                24 / 24
complete successful sequential trajectories           522 / 576
structured sequential failures                         54 / 576
allowed 0.50 sequential-cancel incremental failures    54 / 54
other active failure classes                                  0
strict parse / identity / restart / causality          600 / 600
actually executed 0.25 cancel events passed          1152 / 1152
actually executed 0.50 cancel events passed          1026 / 1080
maximum 0.25 cancel increment                       0.2360657249
maximum 0.50 cancel increment                       0.3506501714
calibration outcomes opened                                false
holdout outcomes opened                                    false
```

The static S23R1 replay used the stored source-baseline cancellation center.
After a real sequential issue changed the plant state, the current feedback
center moved. Returning to the stored Card15 center therefore required an
additional normalized-action increment of 0.1474415 through 0.2152652 in the
54 failures. The guard correctly rejected the action before that failing
cancellation was applied. This is a real finite-envelope mismatch between the
static schedule preflight and online sequential plant response.

## Runtime hotfix boundary

The first sequence attempt failed before its first S24 action because
`_basis_current` applied `float()` to a dictionary. Its 576 failed raw files
are separately archived and were never reused as scientific trajectories.
The dictionary-to-ordered-columns hotfix changed only the in-memory
representation and preserved controller and experiment semantics. The 24
successful baselines were safely reused; all 576 sequence trajectories were
rerun.

```text
archived pre-hotfix raw count                              576
archived bytes                                       13706096
archived inventory digest
332a227f1fb2ccfb01b773e156beecf2a5b4cb70e86b4c3dc5149a092ef1071c

active raw inventory digest
fae5f62671296c837e00158fe204a1630fc70aace87be650ad13d75928f20c70
active raw bytes                                      34003877
```

## Provenance and validation

```text
local branch
codex/stage4_2r3c3t13s24-sequential-transition

deployed experiment checkpoint
9841948

S24 run
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24_runs/
stage4_2r3c3t13s24_sequential_transition_identification_20260803_111226_0c71836

S24 log
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t13s24_training-sequence_20260803_121237.log

hotfixed implementation SHA-256
29283348f004f90eeea5e563ae2e5397397e324bfb6b51ecff3436398938c6e9
state SHA-256
d461c6f46488031d59846acc5340dab2cfad6819b4e29db9b335f4e4cd59ad6f
manifest SHA-256
5eee5548ec72ebedcebf3e01e3d5b1072a447f1d78d9b8c55274c5f22540217e
training gate SHA-256
9320ca7355d55142ba4081ce31c45afc91f0aa1e30d8c90fc529ee0a1bfc8701
complete log SHA-256
36cda108ec3318418ee37d957a9d603bb56869b8ab4ffa25fc923a2ea700edea
independent forensics SHA-256
d04749ea5d6349ec35568b8be2b9536911c64352dd9b7f098686bfe21b493111
```

Server validation after the run used only the existing project virtualenv:
the 486-file package verification passed, 16 focused tests passed, and the
complete Linux suite passed 917 tests with one expected skip. No global Python
or package installation was used.

## Classification and next route

```text
runtime/environment error in active run                    no
deployment/import error after hotfix                        no
raw/snapshot corruption                                     no
statistics/reporting error                                  no
plant-restart mismatch                                      no
controller-causality failure                                no
design failure                                             yes
real MPC control conclusion                         not tested
```

S24 may not be resumed and its partial success raw may not be mixed into a
replacement model. The prospectively frozen S24D1 zero-TSC contracted replay
is applicable because every 0.25 cancellation passed and every failure was the
single allowed 0.50 cancellation class. S24D1 uses only the fixed amplitude
map `0.25/0.25/0.225/0.225`; a pass can authorize only a fresh real-TSC safety
sentinel, never the full replacement campaign, MPC, expert data, BC, DAgger,
or RL.
