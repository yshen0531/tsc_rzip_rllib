# Stage4.2R3c3T13S7R1 campaign-specific effect report

## Final result

T13S7R1 completed the frozen zero-new-TSC audit over all 120 immutable S1/S5
raw files. Its final route is:

```text
CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN
```

Correct campaign timing repaired every local rank defect, but none of the
112 held-out inputs was supported by a map selected under the frozen causal
feature rule. This is an excitation-coordinate/support design failure. It is
not a TSC runtime, plant restart, causality, raw-corruption, controller, MPC,
or plant-reachability result.

## Identities and evidence

```text
design checkpoint
  50c2a8f  Finalize T13S7 and preregister T13S7R1
implementation checkpoint
  0a4b39a  Implement T13S7R1 campaign effect audit
strict-JSON empty-support hotfix
  9e400e1  Handle empty T13S7 prediction summary
support-forensic checkpoint
  3d60b88  Record T13S7R1 result and add support forensic

final staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s7r1_9e400e1
server audit directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s7r1_audits/
  stage4_2r3c3t13s7r1_campaign_specific_20260802_9e400e1
main audit SHA-256
  9fb7c8ce1efc03a66d69b8b8c848bff9509196cfc2e7b583f98eb547dd829c80
main log SHA-256
  ec98d3f79dcfd318afd2425cbc8f727b0fd9c397bfbf363e0815ce9101406fd5
support forensic SHA-256
  6683df634729fee74294971f1e945bec0eddd7532bb06b650044da937f88c799
support-forensic log SHA-256
  6e4682d73ba7c04131a26f9390b6c61a0a0fe98a25cf6330bdaa76b4c7f66e06
```

The compact audit and forensic are tracked locally. The 120 source raw files
and their snapshots remain on the server.

## Validation and execution accounting

```text
local suite after implementation                         698 / 698
local suite after empty-support hotfix                    699 / 699
local suite after support forensic                        702 / 702
empty-directory focused deployment test                    11 / 11
server focused audit tests                                 11 / 11
server support-forensic tests                               3 / 3
new TSC / gotsc / plant trajectories                             0
```

The first server audit at implementation `0a4b39a` read the authenticated
raw and then raised `ValueError` while applying `max()` to an empty finite
error set. Its pipe initially hid the nonzero Python status, but it wrote no
result JSON. The `9e400e1` hotfix serializes the undefined maximum as JSON
`null`, adds a regression test, and changes no raw extraction, model,
selection, support, tube, threshold, or scientific semantics. The final run
used `pipefail` and completed normally.

## Raw and gate recomputation

```text
S1 raw / digest
  52 / de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603
S5 raw / digest
  68 / 09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
combined raw / bytes                           120 / 6,073,463
campaign-specific effect timing                         56 / 56
trace identity                                         120 / 120
signed response extraction                             112 / 112
pre-effect causality                                   112 / 112
local rank                                               16 / 16
local non-vacuous tube                                   16 / 16
maximum tube/cap ratio                                  0.202075
held-out rows                                                112
selected supported hypothesis                           0 / 112
componentwise containment                               0 / 112
finite relative errors available                        0 / 112
disjoint causal aliases                                        0
forbidden feature/trace inputs                                 0
```

Containment and relative error are zero-count because prediction was
correctly refused, not because 112 predictions were inaccurate. The finite
maximum is therefore `null`.

## Post-result support forensic

The diagnostic retained the frozen `0.15` support threshold and compared
each held-out input with all three same-stratum training maps, without
changing the final route:

```text
training comparisons                                         336
all supported comparisons                                     16
selected comparisons                                         224
selected supported comparisons                                 0
held-out rows with any all-training support                16 / 112
held-out rows with selected support                         0 / 112
held-out rows with cross-campaign support                   0 / 112
minimum selected projection residual                       0.202537
minimum cross-campaign projection residual                 0.485141
median all-training minimum residual                       0.790417
```

All 16 support hits were S5 hard/transport rows between the two S5 contexts,
with numerical-zero projection residual, and the frozen visible-feature
selector did not select that peer. S1-to-S1, S1-to-S5, S5-to-S1, all easy
rows, and both braking windows had no supported comparison. The problem is
therefore not only nearest-neighbor selection: the two-transition measured
input coordinate combines campaign-specific issue/cancel actuation geometry
that is not shared across the development contexts.

## Classification and next action

```text
runtime/environment error                              no
packaging/import/deployment error                      no
raw/snapshot corruption                               no
restart or controller causality failure                no
initial summary/reporting bug                         yes, fixed
frozen final statistics bug                            no
input-support/excitation-coordinate design failure    yes
response accuracy on unsupported rows                 not tested
real controller or MPC executed                        no
reliable MPC expert validated                          no
```

T13S7R1 is final and may not be rerouted. The next preregistered audit is
T13S8: a campaign-aware, first-physical-effect, single-transition model. It
removes the confounding adjacent cancellation transition from the model
input while retaining causal measured-current input, all contexts, strict
support, tubes, and holdout gates. A pass still requires a fresh q3 history
holdout. Probe trajectories remain forbidden from expert data, and all
MPC/BC/DAgger/RL gates remain closed.
