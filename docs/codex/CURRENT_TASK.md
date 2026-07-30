# CURRENT_TASK.md — Stage4.2R3c2 restart target-state regulation MPC

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

Development results now frozen:

```text
R3b fresh phase-zero control                  0/32
R3c ideal-visible phase alignment            20/32
R3c1 authenticated R17 R/Z/Ip alignment      16/32
```

R3c and R3c1 are permanently failed development results. Do not overwrite,
resume, or relabel them.

## 2. R3c1 final forensic conclusion

Exact run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c1_runs/
stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218
```

Final independent result:

```text
control raw / environment success             32/32
exact plant restart                            32/32
causal and valid phase trace                   32/32
formal control pass                            16/32
runtime / restart / causality errors               0
real closed-loop formal failures                  16
```

R3c1 initially had four phase-20 first-sample runtime exceptions. Exact
pre-hotfix evidence was preserved; a semantics-preserving resume recomputed
only those four tasks, which all passed. A later postprocessor compatibility
bug was reporting-only. Neither incident explains the final 16 control
failures.

R3c1 repaired none of R3c's 12 failures and regressed four prefix-9 weak
offset-target cases:

```text
R3c -> R3c1
pass -> pass    16
fail -> fail    12
pass -> fail     4
fail -> pass     0
```

Static nearest R/Z/Ip phase matching is therefore insufficient to reconstruct
the dynamic controller state of a restart. The fresh controller lacks
initial velocity/history, integral, previous correction, and a measured
pending-action queue even when its visible point is close to R17.

Load-bearing evidence:

```text
run inventory digest
  5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f

independent raw forensics SHA-256
  29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd

no-TSC restart-regulation diagnostic SHA-256
  9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d

formal report
  docs/codex/reports/STAGE4_2R3C1_FORENSIC_REPORT.md

compact evidence
  docs/codex/audits/stage4_2r3c1_result_20260730_143218/
```

Large final raw JSON.GZ and snapshot trees remain server-side.

## 3. Active task

Implement Stage4.2R3c2 as a new controller and experiment identity. The
prospective design is frozen in:

```text
docs/codex/reports/STAGE4_2R3C2_PREREGISTERED_DESIGN.md
```

Identity:

```text
stage
  Stage4.2R3c2

package revision
  r42r3c2_restart_target_state_regulation_mpc_v1

controller revision
  restart_target_state_regulation_mpc_v42r3c2
```

R3c2 must:

- authenticate exact R3b, R3c, and R3c1 source evidence;
- reuse the exact R3c1 32-case development matrix and visible phase selector;
- preserve the phase-zero original R17 controller path exactly;
- for every nonzero visible restart phase, enter target-state regulation MPC
  at task step zero and remain there through the formal horizon;
- use zero vR/vZ only at the unavailable first sample and causal current-run
  finite differences thereafter;
- retain frozen response-model cap, terminal gains, scheduler, weak probe
  schedule, limits, and phase-aligned delay-queue priming;
- never use source actions, source/current wire currents, current-run future
  values, pair/member/prefix labels, or observed pass/fail outcomes;
- pass the full offline no-gotsc action/causality/source-authentication gate
  before real TSC.

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

R/Z tolerance, 0.1 m/s speed threshold, Ip thresholds, and arrival streak
are unchanged. Formal task time starts at zero.

R3c2 uses inspected development snapshots and calibration. Therefore even a
32/32 PASS is same-digital-twin development closure only. It cannot validate
independent hidden-history, unseen initial state, unseen target, continuous
parameters, plant error, noise, disturbance recovery, or long hold.

## 5. Required validation and server loop

Before real TSC:

- Python compile and all repository JSON parse;
- focused and complete unit tests;
- import closure and package hash verification;
- exact source, run-inventory, raw-forensic, and diagnostic hashes;
- empty-directory direct-copy deployment simulation;
- no undeclared source-tree dependency;
- exact remote project/virtualenv preflight;
- server `bash -n`, executable-bit, package, import, compile, and complete
  tests;
- offline four-source full-horizon phase-zero/action preservation;
- offline exact 32-case prospective first-action reproduction;
- offline hidden-wire invariance and forbidden-input proof;
- zero real-TSC raw and no plant advance in the offline phase.

Then:

```text
deploy directly without archives
→ validate staging and canonical server trees
→ run offline gate
→ safely continue the same new R3c2 identity into 32 real-TSC controls
→ postprocess every raw JSON.GZ on the server
→ retain large raw/snapshots server-side
→ download compact audit/results/logs only
→ verify hashes and independently analyze raw evidence
→ write the final R3c2 forensic report
```

## 6. Advancement rule

R3c2 PASS requires 32/32 environment, restart, causality, regulator trace,
and formal control, plus both members passing in all 16 pair groups.

If it fails, preserve the raw evidence and create a new controller revision
only from a concrete raw-data diagnosis. Do not tune cases individually or
weaken the gate.

If it passes, proceed only to independently preregistered R3d with newly
generated prospective histories and initial states.

BC, DAgger, and bounded residual RL remain blocked. They cannot start before
restart, hidden history, continuous parameters, noise, disturbance recovery,
and independent long hold are complete.
