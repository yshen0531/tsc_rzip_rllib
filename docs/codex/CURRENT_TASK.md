# CURRENT_TASK.md — Stage4.2R3c3 restart task-clock response identification

## 1. Certified checkpoint

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

Completed development results:

```text
R3b fresh phase-zero control                  0/32
R3c ideal-visible phase alignment            20/32
R3c1 authenticated R17 R/Z/Ip alignment      16/32
R3c2 zero-nominal restart target regulator   12/32
```

R3b, R3c, R3c1, and R3c2 are permanently frozen development results. Do not
overwrite, resume, relabel, or weaken their gates.

## 2. R3c2 final forensic conclusion

Exact run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c2_runs/
stage4_2r3c2_restart_target_state_regulation_mpc_20260730_164616
```

Independent raw result:

```text
control raw / environment success             32/32
exact plant restart                            32/32
causal and complete regulator trace          1152/1152
formal control pass                            12/32
runtime / restart / causality / solver errors      0
real closed-loop formal failures                  20
```

R3c2 used zero nominal physical coefficients and a zero nominal feature for
every nonzero restart phase. It repaired none of R3c1's 16 failures and
regressed four R3c1 passes:

```text
R3c1 -> R3c2
pass -> pass    12
fail -> fail    16
pass -> fail     4
fail -> pass     0
```

All 16 prefix-5 cases failed. In representative normal-actuator prefix-5
cases, maximum action fell from roughly 0.55--0.92 under R3c1 to roughly
0.08 under R3c2. This is a genuine controller-design failure: terminal
damping is not finite-horizon restart transport.

Load-bearing evidence:

```text
run inventory
  147 files / 3,287,591 bytes
  2119d2edad615dbb9594ad4332b758a9cf7ffc2e62b988650c41297aace8cff2

raw control inventory
  32 files / 1,070,893 bytes
  b01a07c9dc136677f323d292d0f9388904cc39663514bf4025f4fa4fed767653

independent raw forensics SHA-256
  644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2

formal report
  docs/codex/reports/STAGE4_2R3C2_FORENSIC_REPORT.md

compact evidence
  docs/codex/audits/stage4_2r3c2_result_20260730_164616/
```

Large raw JSON.GZ and snapshot trees remain server-side.

## 3. Why another controller is not run immediately

The eventual controller must restore target-conditioned nominal transport
and optimize velocity against the formal task deadline. The existing lifted
model cannot be silently stretched:

- R14 retained the nominal plan but rebounded after its state-35 model
  boundary;
- R15B validated a small-signal model only around the old late weak-slew
  baseline;
- R16 invalidated large-amplitude bidirectional extrapolation;
- R17 is only a finite one-sided braking patch.

The authentic restart bank therefore needs its own bounded task-clock
response identification before R3c4 MPC code is allowed.

## 4. Active task

Implement Stage4.2R3c3 exactly as frozen in:

```text
docs/codex/reports/STAGE4_2R3C3_PREREGISTERED_DESIGN.md
```

Identity:

```text
stage
  Stage4.2R3c3

package revision
  r42r3c3_restart_task_clock_local_response_identification_v1

controller revision
  restart_task_clock_local_response_probe_v42r3c3
```

R3c3 is identification-only. It must:

- authenticate exact R3b snapshots and exact final R3c1/R3c2 evidence;
- use the exact R3c1 target-conditioned nominal controller as baseline;
- preserve the exact 32 restart contexts;
- run four fixed two-mode zero-net basis probes with both signs in every
  context, for exactly 256 real TSC rollouts;
- use amplitude `0.0075` and task-state first-effect anchors 5 and 17;
- preserve scheduler, gain/slew, delay queue, physical limits, formal
  horizons, and controller causality;
- strip pair/history/prefix/result identity before controller construction;
- postprocess all raw JSON.GZ on the server;
- test central symmetry, conditioning, and matched-hidden-history odd-response
  disagreement using the preregistered thresholds;
- keep probe trajectories out of every expert dataset.

Formal tracking is recorded but is not an R3c3 acceptance requirement.

## 5. Formal contract

The formal contract remains unchanged even though R3c3 is identification:

```text
slew 1.0:
  arrive no later than 250 ms
  hold/evaluate through 350 ms

slew 0.9:
  arrive no later than 270 ms
  hold/evaluate through 370 ms

R/Z tolerance                 30 mm
speed threshold               0.1 m/s
Ip thresholds                 frozen
arrival streak                frozen
```

No task clock, deadline, threshold, or probe-analysis gate may be changed
after observing R3c3.

## 6. Required validation and loop

Before real TSC:

- Python compile and all repository JSON parse;
- focused and complete unit tests;
- import closure and package checksum verification;
- exact source fingerprint and resume-compatibility tests;
- empty-directory direct-copy deployment simulation;
- server preflight, `bash -n`, executable bits, import, compile, package, and
  complete tests in the existing virtualenv;
- offline exact phase-zero and R3c1 baseline preservation;
- offline exact 256-case probe-grid/causality/zero-net audit;
- hidden-wire invariance;
- zero raw and no real TSC in the offline phase.

Then:

```text
deploy directly without archives
→ validate staging and canonical server trees
→ run the offline no-TSC gate
→ continue the same new R3c3 identity into exactly 256 real TSC probes
→ monitor the actual job
→ postprocess all large raw JSON.GZ on the server
→ download compact evidence only
→ independently verify hashes and raw-derived metrics
→ write the final R3c3 forensic report
```

## 7. Advancement

If R3c3 passes all identification gates, preregister R3c4 as a new
restart-integrated target-conditioned deadline MPC. R3c4 may use only the
validated bounded response envelope and only visible state/current,
target, and actuator estimates for model selection.

If central symmetry fails, create a new smaller-envelope identification
stage. If matched-hidden-history response disagreement fails, stop
visible-only MPC work and implement causal observer/history-state
identification first. If conditioning fails, expand the basis prospectively.

Independent new histories, new targets, continuous actuator/plant variation,
noise, disturbance recovery, and independent long hold remain unvalidated.
BC, DAgger, and bounded residual RL remain prohibited.
