# Stage4.2R3c3T13S6 immediate-effect reinterpretation report

## Result

Stage4.2R3c3T13S6 completed its frozen read-only audit of all 68 immutable
T13S5 trajectories. The corrected post-queue effect states repair every
development rank/condition/tube gate, but the already-consumed independent
history validation still fails decisively. The final route is:

```text
IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN
```

This is a finite cross-history transition-model design failure. It is not a
runtime, deployment, raw, snapshot, restart, causality, statistics,
reporting, real-MPC, or global-reachability failure.

## Exact identities and evidence

```text
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel

frozen design commit
  f89b54c  Preregister T13S6 immediate-effect audit
main audit implementation
  efc5b30  Implement T13S6 immediate-effect audit
project-state checkpoint
  1eff78e  Record T13S5 result and activate T13S6
independent raw audit implementation
  7e7639d  Add independent T13S6 raw audit
independent audit layout hotfix
  99d2b2d  Fix T13S6 independent audit variant layout

main staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s6_efc5b30
independent staging
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s6_independent_99d2b2d

source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s5_runs/
  stage4_2r3c3t13s5_real_20260802_d048686

main result
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s6_audits/
  stage4_2r3c3t13s6_immediate_effect_20260802_efc5b30/
  stage4_2r3c3t13s6_immediate_effect_audit.json
  SHA-256
  2f3f373fd1ff6c4080af18147783f8a0a009b6b490b4b4e773c4e106b8044375

independent raw audit
  same directory / stage4_2r3c3t13s6_independent_raw_audit.json
  SHA-256
  fc96514c1eb054c858fca8ee58085d4d7d78de470c3685c210e523e5021ebea4

main log SHA-256
  20b01f7fb653cad182a9d76e297be8a275c9147e038b0c4d472aa1c9e8fd4989
independent log SHA-256
  3ac1fb2ab791b4120d626717af0710f53bd640efc5f899ff84351fbeb85069d1
```

The four main staging contents matched their frozen SHA-256 rows. The main
server test passed 4/4. The independent server test passed 4/4. The current
repository-local Windows virtual environment passed the complete suite
688/688 with the existing POSIX-resource portability shim.

## Raw-to-route result

```text
raw expected / authenticated                         68 / 68
raw bytes                                           3,610,097
raw inventory digest
  09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
trace identity                                      68 / 68
target Card15 symmetry                              32 / 32
corrected pre-effect causality                      32 / 32
observed current signal                             32 / 32
observed current symmetry                           32 / 32
development signal                                  16 / 16
development rank/condition                            4 / 4
development non-vacuous tube                          4 / 4
maximum finite condition                         7.9547833
maximum tube/cap ratio                            0.2020750
consumed validation containment                     14 / 32
consumed validation relative error <= 0.10            2 / 32
consumed validation pre-effect causality             32 / 32
maximum validation scaled relative error          1.0973948
forbidden model or trace inputs                            0
```

Per-cell consumed validation:

```text
cell             containment   relative-error pass   maximum error
easy transport        2 / 8             0 / 8          0.9990279
easy braking          8 / 8             0 / 8          1.0392374
hard transport        2 / 8             2 / 8          0.6005729
hard braking          2 / 8             0 / 8          1.0973948
```

Only the two signs of the hard-transport coil-index-8 component pass the
relative-error gate. The failure is broad across both directions and
transport/braking windows; it is not a single outlier.

The independent audit opened and hashed every raw JSON.GZ, reconstructed
causal backward velocity from R/Z, recomputed the two-state 28-component
measured-current input and ten-component R/Z/vR/vZ/Ip output, refit all four
minimum-norm maps and residual tubes, and recomputed all 32 validation rows.
Its raw arrays, models, validation errors, booleans, summary, and route agree
with the main audit within `1e-12`.

## Error classification

The first independent-audit invocation stopped before output because the
post-result tool looked for payloads under a nonexistent nested `variants`
directory. The real run stores exactly 68 payloads in the run-level
`stage4_2r3c3t13s5_environment_variants` directory. Commit `99d2b2d`
changed only that forensic lookup and added a regression test; a new staging
identity was used. This was an independent-audit input-layout bug, not an
experiment or result bug.

```text
runtime/environment error                              no
packaging/deployment error                             no
raw or snapshot corruption                            no
plant restart or controller causality failure          no
main statistics/reporting error                        no
independent-audit first-attempt layout bug             yes, fixed
T13S5 delay-2 declared-effect-state design error        yes, confirmed
single static cross-history map design failure          yes, confirmed
real MPC executed                                      no
global plant unreachability shown                      no
```

Correcting the effect states is scientifically important: hard transport
changes from rank zero to rank four and hard braking from rank one to rank
four. It does not rescue the route. The corrected development result only
shows locally informative immediate responses in each source history; it
does not make one history's map transferable to another.

## Frozen conclusions and next action

T13S5 remains `LATTICE_HOLDOUT_FAIL_REDESIGN`; T13S6 does not rewrite its
preregistered result or recover blind status. All 120 future-combined S1/S5
probe trajectories remain forbidden from expert data.

The next action is a separately frozen zero-new-TSC causal
state-conditioned, multi-hypothesis feasibility audit over the already
consumed q1 and q2 raw. It must use only current/past visible state, causal
velocity/unknown flags, measured coil current, current-run command state,
formal time, target, and finite actuator settings. A pass can authorize only
a fresh q3 independent-history holdout design; a fail requires observer/tube
redesign before another physical campaign.

No controller, Ray, `gotsc`, TSC, plant step, snapshot, MPC, BC, DAgger, or
RL operation was run in T13S6. Formal arrival/hold timing and all tolerances
were unchanged.
