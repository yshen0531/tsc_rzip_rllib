# CURRENT_TASK.md — Stage4.2R3c1 authenticated visible-manifold phase MPC

## 1. Certified evidence checkpoint

Terminology:

```text
R1  = Stage4.2R1 authentic TSC plant-state restart
R17 = Stage4.1R17 frozen finite static-grid controller source
```

Certified foundations:

```text
Stage4.1R17 finite clean static grid         18/18
Stage4.2R1c authentic plant-state restart    18/18
Stage4.2R2 causal controller-state restart   18/18
minimum frozen formal signed margin          1.0456920999768471e-05
```

R3b completed 72/72 authentic state rollouts and generated four selected
matched-visible/different-hidden-history pairs. Its fresh phase-zero
controller failed formal control 0/32. The restart states were closest to
actual R17 visible phases 12--20, proving a controller-design failure rather
than plant-restart failure.

R3c then completed:

```text
offline original-start preservation            4/4
real TSC controls                              32/32
exact plant restart                            32/32
causal controller trace                       32/32
formal control pass                            20/32
prefix-9 control pass                          16/16
prefix-5 control pass                           4/16
runtime / corruption / restart errors               0
```

Exact R3c evidence:

```text
implementation / source-contract commits
  e8856f8
  a5513e9

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c_runs/
  stage4_2r3c_visible_state_phase_aligned_mpc_20260730_132807

run inventory digest
  278395b364bb355c73b5f6de7461478b4bb239584a3f6bf9bf048aad12be9d13

independent raw forensics SHA-256
  395427285a5bad0de9611629df0a13ade037ddd4f0e30e993e475a56c3dbafaa

report
  docs/codex/reports/STAGE4_2R3C_FORENSIC_REPORT.md

compact evidence
  docs/codex/audits/stage4_2r3c_result_20260730_132807/
```

R3c is permanently a failed 20/32 development result. Do not overwrite or
relabel it.

## 2. R3c diagnosis

R3c selected a causal phase from current R/Z/Ip and consistently aligned its
nominal reference, model lookup, delay queue, and braking transitions. This
removed the dominant R3b phase-zero mismatch and recovered all prefix-9
cases.

Its phase selector nevertheless matched against an ideal nominal trajectory:

```text
R3c selected phases                         11--13
nearest actual R17 visible phases           12--20
first-action difference from phase zero   1.16--2.00
first-action difference from selected     0.038--0.123
```

The selected phase underestimated physical closed-loop phase, especially for
delay 2 / slew 0.9. All 12 failures are genuine formal closed-loop failures
in prefix-5 cases. There were no runtime, deployment, raw, snapshot,
plant-restart, solver, or causality errors in the final run.

This supports one concrete design change: use the authenticated actual R17
closed-loop visible R/Z/Ip source trajectory as a static causal phase
reference instead of the ideal nominal sequence.

## 3. Active task

Implement Stage4.2R3c1 as a new controller and experiment identity. The
prospective design is frozen in:

```text
docs/codex/reports/STAGE4_2R3C1_PREREGISTERED_DESIGN.md
```

Planned identity:

```text
stage
  Stage4.2R3c1

package revision
  r42r3c1_authenticated_visible_manifold_phase_mpc_v1

controller revision
  authenticated_visible_manifold_phase_mpc_v42r3c1
```

R3c1 must:

- authenticate the exact R3b source, R3c run inventory, R3c forensics, four
  pair identities, and eight snapshot manifests;
- extract only phases 0..20 R/Z/Ip from each exact R17 source trajectory into
  a hashed frozen calibration table;
- never expose source actions, current-run future values, source coil/wire
  currents, snapshot labels, history-member labels, or 48-wire state to the
  controller;
- choose phase from current visible R/Z/Ip only, with the frozen R3c scales
  and earliest-tie rule;
- keep formal task time zero and preserve all other R3c controller semantics;
- pass an offline no-gotsc original-start/action-preservation and
  hidden-wire-invariance gate;
- execute the unchanged 32-case development matrix;
- report errors and control conclusions separately.

## 4. Formal and scientific constraints

The formal contract is unchanged:

```text
slew 1.0:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms
```

R/Z tolerance, 0.1 m/s speed threshold, Ip thresholds, and arrival streak are
unchanged. R3c1 may not shift the formal clock or tune the gate after seeing
results.

R3c1 reuses inspected development snapshots and source trajectories.
Therefore:

- R3c1 is same-digital-twin controller-development evidence only;
- its actual R17 R/Z/Ip table is calibrated reference data, not current-run
  future information;
- a PASS cannot validate independent hidden-history, different-initial-state,
  unseen-target, or continuous-parameter robustness;
- R3d with newly generated prospective histories remains mandatory after a
  PASS.

## 5. Required validation and server loop

Before real TSC:

- Python compile and all JSON parse;
- focused and complete unit tests;
- import closure and package hash verification;
- source, R3c-evidence, calibration, and resume-compatibility tests;
- empty-directory direct-copy deployment simulation;
- no undeclared external source dependency;
- exact remote path preflight;
- server `bash -n`, package verification, import/compile, and complete tests;
- offline original-start phase-zero and exact-action preservation;
- offline proof that no source action, hidden wire, or current-run future
  value enters phase selection or action computation;
- zero real-TSC raw in the offline phase.

Then:

```text
deploy directly without archives
→ validate staging and canonical server trees
→ run offline gate
→ safely resume the same identity for 32 real-TSC controls
→ postprocess every raw JSON.GZ on the server
→ download only compact audit/results/logs
→ verify hashes
→ write the final R3c1 forensic report
```

Large raw JSON.GZ and snapshot trees stay on the server.

## 6. Advancement rule

If R3c1 fails, preserve its raw evidence and create a new controller revision
only from a concrete raw-data diagnosis. Do not weaken the gate.

If R3c1 passes all 32 development cases, proceed only to independently
preregistered R3d with newly generated unseen histories and initial states.
Only successful independent confirmation can unblock new target and
continuous actuator/plant work.

Noise, disturbance recovery, long hold, BC, DAgger, and bounded residual RL
remain blocked.
