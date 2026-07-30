# Current status

## Stage4.2R3c3 passed; Stage4.2R3c4 preregistration is next

Status timestamp: 2026-07-31 Asia/Shanghai

Current local branch:

```text
codex/stage4_2r3c3-restart-response-id
```

Runtime implementation checkpoint:

```text
8623bcf  final R3c3 runtime and package
```

Independent forensic checkpoint:

```text
83e78e4  independent raw response forensics
```

## R3c3 exact result

Remote run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3_runs/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427
```

Raw-derived result:

```text
expected / parsed raw                         256 / 256
environment success / completed               256 / 256
exact plant restart                            256 / 256
causal exact probe execution                   256 / 256
central-symmetry groups                        128 / 128 PASS
matched-hidden-history groups                    64 / 64 PASS
conditioned rank-4 response groups               32 / 32 PASS
maximum selected condition number              8.0984 <= 25
maximum current utilization                    0.3904 <= 0.55
formal contract pass                           125 / 256
real formal failures                           131 / 256
```

Formal tracking was preregistered as diagnostic-only. Probe trajectories are
identification data and are forbidden from every expert dataset.

Final classification:

- runtime/environment errors: 0;
- packaging/import/deployment errors affecting the run: 0;
- raw/snapshot corruption: 0;
- statistics/reporting errors: 0;
- plant-restart failures: 0;
- controller-causality failures: 0;
- probe-execution/solver failures: 0;
- response-identification design failures: 0;
- real formal failures of perturbed probe trajectories: 131;
- finite development-envelope identification success: yes;
- independent hidden-history robustness: not validated.

## Response bounds

```text
central even velocity RMSE max      0.0012790224 m/s  <= 0.004
central even position RMSE max      0.0001068371 m    <= 0.0005
central even Ip RMSE max            2.8750260 A       <= 20

hidden odd velocity RMSE max        0.0013169411 m/s  <= 0.006
hidden odd position RMSE max        0.0001102332 m    <= 0.001
hidden odd Ip RMSE max              2.4495309 A       <= 40

condition number min / mean / max   1.8785 / 3.9845 / 8.0984
```

Within the exact four-pair development bank and the `0.0075` local probe
envelope, matched-visible alternate hidden histories had sufficiently
similar signed responses. This is not an independent new-history control
result.

## Evidence

```text
runtime/audit package digest
  1ba40b276a6a998e266e68d044c8ad3e819d86b6f7c8e52c7c60c6000a05a661

run inventory
  1048 files / 25,371,364 bytes
  ef377ce1367d7a969b8f90cdb247445106f50b8706146f4c97b312892e909754

raw inventory
  256 files / 8,933,607 bytes
  88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563

server audit SHA-256
  5172fc54a8446418bbcccd31c84515f62ad2594a52904b831a3b2064d52a44b4

independent raw forensics SHA-256
  1a1d1acb2b6401a726a5e313301d9a37643cf023b4d2013a9f9c37e23f8a097b

local compact inventory
  30 files / 1,871,530 bytes
  ed2443a8e3ea5d9559517a815df33bbb706263a3559f902953fcc940898cc957
```

Formal report:

```text
docs/codex/reports/STAGE4_2R3C3_FORENSIC_REPORT.md
```

Compact evidence:

```text
docs/codex/audits/stage4_2r3c3_result_20260730_182427/
```

Large raw JSON.GZ and generated environment variants remain server-side.

## Active next step

Freeze a compact authenticated R3c3 response bank on the server, download
only that compact model, and preregister Stage4.2R3c4.

R3c4 must be a new restart-integrated target-conditioned deadline MPC. It
may use only:

- current and past visible state/current measurements;
- the requested target;
- causal actuator delay/gain/slew estimates;
- the frozen R3c1 nominal controller;
- the bounded R3c3 local response envelope.

It may not use source actions/results, future current-run values, full wire
current, pair/history/prefix labels, or probe trajectories as demonstrations.
It must preserve the immutable 250/350 ms and 270/370 ms formal contract.

## Still blocked

A reliable restart MPC expert, independent new histories and initial states,
unseen targets, continuous actuator/plant variation, noise, disturbance
recovery, and independent long hold remain unvalidated. BC, DAgger, and
bounded residual RL remain prohibited.
