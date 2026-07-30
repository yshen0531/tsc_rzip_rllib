# CURRENT_TASK.md — Stage4.2R3c3T1 transport-response identification

## 1. Certified checkpoint

Terminology:

```text
R1  = Stage4.2R1 authentic TSC plant-state restart
R17 = Stage4.1R17 frozen finite static-grid controller source
```

Certified foundations:

```text
Stage4.1R17 finite clean static grid                    18/18
Stage4.2R1c authentic plant-state restart               18/18
Stage4.2R2 causal controller-state restart              18/18
Stage4.2R3c3 bounded local response identification     256/256
```

Frozen development control results:

```text
R3b fresh phase-zero control                  0/32
R3c ideal-visible phase alignment            20/32
R3c1 authenticated R17 R/Z/Ip alignment      16/32
R3c2 zero-nominal restart regulator          12/32
```

R3b, R3c, R3c1, R3c2, and R3c3 are immutable. Do not overwrite, relabel, or
weaken their gates.

## 2. R3c3 response-bank result

Exact R3c3 run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3_runs/
stage4_2r3c3_restart_task_clock_local_response_identification_20260730_182427
```

Authenticated compact bank:

```text
R3c3 raw / causal exact probe                         256/256
R3c1 baseline contexts                                 32/32
signed response groups                                128/128
matched-hidden-history groups                           64/64
conditioned rank-4 groups                               32/32
```

Fingerprints:

```text
R3c3 raw inventory
  88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563

audit response bank SHA-256
  51bb4eeabfc8a4c5cc3983d75469f484a2278e6ef37cf03cf93ac650f9404b32

controller response bank SHA-256
  6610dd4c434497240cb89ef0fbaa40716e42df68168efa66cddb919dd8679cf0

bank manifest SHA-256
  a17322dcfc1d019de0455950c95e45b0b7d0f8f29fc3c68a22211481f261a066

bank provenance digest
  5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6
```

The controller-facing bank has zero forbidden pair/history/source/raw/result/
wire/pass/fail keys. Source identities and exact R3c1 baseline trajectories
exist only in the separate audit bank.

## 3. R3c4 pre-execution design veto

The four-basis candidate was tested before implementation using an optimistic
audit-only model:

```text
exact R3c1 baseline
+ bounded linear combination of all four authenticated R3c3 odd responses
```

The evaluator reproduced all 32 R3c1 PASS values and margins exactly.
Exhaustive-grid and per-endpoint convex epigraph checks agreed:

```text
R3c1 baseline feasible                         16/32
bounded four-basis oracle feasible             16/32
failed contexts repaired                        0/16
best remaining failed margin              -0.0603147
worst remaining failed margin             -0.3585158
```

This is a pre-execution design flaw, not a real R3c4 closed-loop failure.
R3c4 controller code, offline launch, real TSC launch, and raw count are all
zero/not run.

The rejected design is frozen in:

```text
docs/codex/reports/STAGE4_2R3C4_PREREGISTERED_DESIGN.md
docs/codex/audits/stage4_2r3c4_response_bank_20260730/
stage4_2r3c4_offline_feasibility.json
```

Do not implement or launch R3c4 from the four-basis bank. Do not enlarge
coefficients beyond `[-1,1]` or reinterpret unvalidated amplitude
extrapolation as controller authority.

## 4. Active task

Build Stage4.2R3c3T1 as a new identification identity:

```text
purpose
  bounded long-separation zero-net transport-response identification

baseline controller
  exact R3c1 authenticated visible-manifold controller

source response bank
  exact authenticated R3c3 compact bank

new transport bases
  transport_mode0
  transport_mode1
```

The complete design was frozen before implementation:

```text
docs/codex/reports/STAGE4_2R3C3T1_PREREGISTERED_DESIGN.md
```

Frozen per-sign physical effect schedule:

```text
positive states 3,4,5,6,7,8
negative states 15,16,17,18,19,20
maximum component 0.0075
exact zero net
```

Matrix:

```text
32 contexts × 2 bases × 2 signs = 128 real TSC rollouts
```

Implementation sequence:

1. Implement a complete standalone R3c3T1 config, module, scripts, launchers,
   package manifest, checksums, tests, and server postprocessor.
2. Preserve exact R3c3/R3c1/bank fingerprints and new experiment identity.
3. Complete all local compile/JSON/test/import/package/deployment checks.
4. Deploy directly without archives and validate staging/canonical server
   trees with the existing venv.
5. Run the offline no-TSC gate and prove zero raw/plant advance.
6. Start exactly one new R3c3T1 real identity.
7. Monitor exact PID, log, raw count, task count, state, and finalization.
8. Postprocess all large raw server-side.
9. Download compact evidence only and independently recompute raw metrics.
10. If identification passes, build the combined six-basis compact bank and
    rerun the optimistic R3c4 feasibility gate.

## 5. Mandatory controller constraints

R3c3T1 may use only:

- current and past visible R/Z/Ip and 14-coil currents;
- target R/Z/Ip;
- causal actuator delay/gain/slew values available at task start;
- the exact R3c1 target-conditioned nominal controller;
- its own prospectively fixed transport schedule.

Forbidden controller inputs:

- source actions or source formal outcomes;
- future measurements, actions, or actuator state from the current run;
- source or current 48-wire/vessel current;
- pair, hidden-history, common-prefix, state-generation, source-experiment,
  pass/fail, or other-member labels;
- post-action telemetry unavailable at the action decision.

The schedule must remain causal and delay aware. Requested/applied probe
deltas must agree to absolute tolerance `1e-12`. Clipping is a failed
identification row.

All R3c3/R3c3T1 probe trajectories are identification data, not
demonstrations.

## 6. Immutable formal contract

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

Formal tracking remains diagnostic-only for identification probes. No
deadline or threshold may be changed.

## 7. Required validation and acceptance

Before real TSC:

- Python compile and all repository JSON parse;
- focused and complete unit tests;
- import closure and package checksum verification;
- exact R3b/R3c1/R3c2/R3c3/bank fingerprints;
- exact 32-context and 128-spec identity set;
- exact amplitude/sign/zero-net/delay-aware schedule tests;
- controller-input and future-information guards;
- hidden-wire and pair/history-label invariance;
- source-fingerprint and resume-compatibility tests;
- empty-directory direct-copy deployment simulation;
- server preflight, `bash -n`, import, compile, package, and complete tests;
- offline finite causal action computation for all 128 specs;
- zero raw, zero plant advance, and no real TSC in the offline phase.

Prospective real-result gates:

```text
environment / complete / exact restart / causal trace     128/128
exact requested/applied transport schedule                128/128
runtime / solver / clipping / forbidden-input errors            0
maximum current utilization                                  <= 0.55

central even velocity RMSE                               <= 0.004 m/s
central even position RMSE                               <= 0.0005 m
central even Ip RMSE                                     <= 20 A

matched-history odd velocity RMSE                        <= 0.006 m/s
matched-history odd position RMSE                        <= 0.001 m
matched-history odd Ip RMSE                              <= 40 A

transport-only rank / condition                          2/2, <= 25
combined six-basis rank / condition                      6/6, <= 25
```

No failed group may be removed after inspection.

## 8. Advancement

R3c3T1 PASS is only a bounded development-bank transport-response result.

R3c4 may resume only if:

```text
combined six-basis optimistic oracle feasibility        32/32
all coefficients                                        inside [-1,1]
baseline pass regressions                               0
formal contract                                         unchanged
```

If that gate fails, do not launch R3c4. Preserve raw and redesign the
transport model without weakening gates.

Independent histories/initial states, new targets, continuous actuator and
plant variation, noise, disturbance recovery, and independent long hold
remain unvalidated.

BC, DAgger, and bounded residual RL remain prohibited.
