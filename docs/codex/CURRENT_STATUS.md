# Current status

## Stage4.2R3c2 failed; Stage4.2R3c3 is preregistered

Status timestamp: 2026-07-30 Asia/Shanghai

Current local branch:

```text
codex/stage4_2r3c2-restart-regulation
```

R3c2 implementation checkpoint:

```text
c4b9143  restart target-state regulation MPC
```

## R3c2 exact result

Remote run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c2_runs/
stage4_2r3c2_restart_target_state_regulation_mpc_20260730_164616
```

Final raw-derived result:

```text
expected/final raw                                32/32
environment success                               32/32
fresh controller / fresh TSC                      32/32
exact plant restart                               32/32
causal complete regulator trace                 1152/1152
formal contract pass                              12/32
real formal failures                                  20
```

Final classification:

- runtime/environment errors: 0;
- final packaging/import errors: 0;
- raw/snapshot corruption: 0;
- statistics/reporting errors: 0;
- plant-restart failures: 0;
- controller-causality failures: 0;
- solver failures: 0;
- saturated action elements: 0/16,128;
- deployment-command incident: one pre-run quoting/install failure, fully
  restored and revalidated before TSC;
- controller-design failure: zero-nominal terminal damping is not a
  finite-horizon restart transport controller;
- real closed-loop formal failures: 20.

R3c1-to-R3c2 outcome movement:

```text
pass -> pass    12
fail -> fail    16
pass -> fail     4
fail -> pass     0
```

Grouped R3c2 outcome:

```text
prefix 5                    0/16
prefix 9                   12/16
nominal target              8/16
offset target               4/16
normal actuator             8/16
weak actuator               4/16
```

The 20 formal failures all have unavoidable position violations. Four also
have unavoidable endpoint-late-speed violations. Hidden-history robustness
remains inconclusive because six pair groups passed both members and ten
failed both members.

## Evidence

```text
run inventory
  147 files / 3,287,591 bytes
  2119d2edad615dbb9594ad4332b758a9cf7ffc2e62b988650c41297aace8cff2

raw inventory
  32 files / 1,070,893 bytes
  b01a07c9dc136677f323d292d0f9388904cc39663514bf4025f4fa4fed767653

server audit SHA-256
  87461800e5fd9ea6f228d49e36269eb80ffbb537720fcf804c69812ed2ddf7cf

independent raw forensics SHA-256
  644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2

local compact inventory
  12 files / 903,923 bytes
  35ac2b2731047a7e2d5e67e63d28b9eb108b649c31cb712af012a20fd3a2f0b1

formal report
  docs/codex/reports/STAGE4_2R3C2_FORENSIC_REPORT.md

compact evidence
  docs/codex/audits/stage4_2r3c2_result_20260730_164616/
```

Large raw JSON.GZ and snapshot trees remain server-side.

## Active next step

R3c3 is frozen in:

```text
docs/codex/reports/STAGE4_2R3C3_PREREGISTERED_DESIGN.md
```

R3c3 is not another controller attempt. It is a 256-rollout,
identification-only campaign using the exact R3c1 target-conditioned nominal
controller plus fixed `0.0075`, bidirectional, zero-net mode-0/mode-1 probes
at task-state anchors 5 and 17.

It will independently test:

- exact restart and causal task-relative probe execution;
- bounded local central symmetry;
- four-basis response conditioning;
- matched-visible hidden-history response disagreement.

The probe bank cannot enter an expert dataset. Formal outcomes are recorded
but are not used to pass an identification probe.

Only a passed R3c3 may support an R3c4 restart-integrated
target-conditioned deadline MPC. A hidden-history response disagreement
failure instead routes to causal observer/history-state identification.

## Still blocked

Reliable restart MPC closure, independent new histories, unseen targets,
continuous actuator/plant variation, noise, disturbance recovery, and
independent long hold remain unvalidated. BC, DAgger, and bounded residual RL
are prohibited.
