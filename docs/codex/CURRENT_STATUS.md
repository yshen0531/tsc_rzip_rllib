# Current status

## Stage4.2R3c1 failed; Stage4.2R3c2 is preregistered

Status timestamp: 2026-07-30 Asia/Shanghai

Current local branch:

```text
codex/stage4_2r3c1-visible-manifold
```

R3c1 implementation and forensic checkpoints:

```text
be3065b  implementation
35e725c  semantics-preserving first-sample runtime hotfix
0898b28  reporting-only package-chain audit hotfix
1e3772d  independent raw forensic tool
```

## R3c1 exact result

Remote run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c1_runs/
stage4_2r3c1_authenticated_visible_manifold_phase_mpc_20260730_143218
```

Final result:

```text
expected/final raw                                32/32
environment success                               32/32
exact plant restart                               32/32
causal controller / valid phase trace             32/32
formal contract pass                              16/32
real closed-loop failures                             16
```

The initial run had four phase-20 first-sample runtime exceptions. Their
complete pre-hotfix evidence was preserved. A compatible resume recomputed
only those four experiment IDs; all four passed and all 28 prior-success raw
hashes remained exact. A missing executable bit caused one pre-TSC resume
launch failure. A later package-chain postprocessing defect was
reporting-only.

Final classification:

- final runtime/environment errors: 0;
- final deployment/import errors: 0;
- raw/snapshot corruption: 0;
- final statistics/reporting errors: 0;
- plant-restart failures: 0;
- controller-causality failures: 0;
- real closed-loop formal failures: 16;
- controller-design failure: static visible R/Z/Ip phase matching is
  insufficient.

R3c1 moved R3c outcomes as follows:

```text
pass -> pass    16
fail -> fail    12
pass -> fail     4
fail -> pass     0
```

It did not validate hidden-history robustness: eight pair groups passed both
members and eight failed both members, so common-mode failures mask history
sensitivity.

## Evidence

```text
run inventory
  166 files / 3,409,736 bytes
  5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f

independent raw forensics
  29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd

server audit
  0d81cbe3e0d9b67d72cf093143edd8a825a3b60ea5e3c449cf29de7cf0cc7712

pre-hotfix evidence manifest
  30303cc7a907a4ff2cd4c7680f3164990db39ac0495a6b978b9f4cac38a69cc9

restart-regulation no-TSC diagnostic
  9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d

formal report
  docs/codex/reports/STAGE4_2R3C1_FORENSIC_REPORT.md

compact evidence
  docs/codex/audits/stage4_2r3c1_result_20260730_143218/
```

No final large raw JSON.GZ or snapshot tree was downloaded.

## Active next step

Stage4.2R3c2 is frozen in:

```text
docs/codex/reports/STAGE4_2R3C2_PREREGISTERED_DESIGN.md
```

It preserves the exact phase-zero R17 path but starts causal target-state
regulation at task step zero for every nonzero visible restart phase.
Visible phase remains only for the branch, response-model phase, and
phase-aligned delay-queue initialization.

The server-side no-TSC diagnostic established:

```text
development first actions finite/solver success       32/32
hidden-wire invariant                                  32/32
zero-velocity causal bootstrap                         32/32
original R17 phase-zero/actions exact                    4/4
plant advance / real TSC                                    0
```

R3c2 is a new controller and experiment identity because its first actions
differ materially from R3c1. It must complete the entire local validation,
direct deployment, server validation, offline gate, real TSC, server
postprocessing, compact download, and independent analysis loop.

## Still blocked

Independent R3d histories, unseen targets, continuous actuator/plant
variation, noise, disturbance recovery, and independent long hold remain
unvalidated. BC, DAgger, and bounded residual RL are prohibited.
