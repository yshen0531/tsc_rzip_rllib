# Stage4.2R3c3T13S24D1R12 causal architecture forensic report

## Result

The D1R12 development study has failed the unchanged D1R11 transition-model
gate. Its route is:

```text
STABLE_CAUSAL_INNOVATION_STATE_SPACE_DEVELOPMENT_FAIL_DECONFOUNDED_IDENTIFICATION_REQUIRED
```

This is a zero-new-TSC transition-architecture/design failure. It is not a
runtime, deployment, restart, raw-corruption, statistics/reporting,
closed-loop MPC, control, or plant-unreachability result. D1R11 calibration
and fresh holdout remained unopened.

## Exact evidence boundary

The only raw outcomes consumed were the already-open D1R11 training files:

```text
training trajectories                         600 / 600
training raw bytes                             35,511,922
training inventory digest
  8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7
D1R11 calibration / holdout outcomes                 0 / 0
new raw / snapshots / Ray / gotsc / TSC / plant      all zero
```

Large D1R11 raw remains server-side at:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r11_runs/
stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_20260804_571b932_v1/
stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification/raw
```

The accepted development script and log remain server-side:

```text
.codex_tmp/d1r12_stable_innovation_probe_v1.py
  SHA-256 bfa98bcc602635dbb3ba32f0e527757dc117efbed83ee41a44bb426f8cb9231d

.codex_tmp/d1r12_stable_innovation_probe_v1.log
  SHA-256 e9ca8deddcee484e130736967e83bb7aa5b4872ea0921cfb79a66bbcdd1a9bac
```

Only the compact result was downloaded directly:

```text
docs/codex/audits/stage4_2r3c3t13s24d1r12_20260804/
d1r12_stable_innovation_probe_v1_compact.json

SHA-256
  e46cc9259e71de00b197726ab0cc4ac7e94943011b39be9a3ff5062e5869dc74
```

The local source checkpoint at analysis time was `145f2b5`. The D1R12 script
is preserved as a development artifact under `.codex_tmp`; it is not a
deployed controller or frozen package source.

## Causal interface

The stable innovation candidate used only:

- visible normalized R/Z/vR/vZ/Ip states 0 through 10;
- controller commands already issued at task steps 0 through 9;
- already executed causal calibration coordinates at steps 0 through 9;
- numeric R/Z/Ip target offsets;
- the formal task clock and horizon; and
- the current and three past already revealed four-dimensional requested
  coordinates.

It did not load a reference phase or visible-reference manifold. Pair and
history identifiers were used only to form and report the twelve outer
folds, never as predictor values. Coil currents, wire/vessel currents,
source actions/results, matched baseline values, current-run future values,
future measurements, and future executed actions were absent from the
predictor.

The model predicted only vR, vZ, and Ip. R and Z were advanced with the exact
10 ms discrete kinematic relation. The learned dynamic-state transition was
projected to each frozen spectral-radius cap before recursion.

## Whole-pair result

The deterministic grid covered:

```text
context PCA ranks                         4, 8, 12
ridge values                              0.01, 1, 100
spectral-radius caps                      0.8, 0.95, 0.995
context/current-action interaction        off, on
total candidates                          54
outer validation                          12 whole pairs / 600 trajectories
```

All 54 candidates failed both the unchanged `0.1` recursive point gate and
the frozen tube caps. The selected development candidate was rank 12,
ridge 1, radius cap 0.995, with no context-action interaction:

```text
maximum recursive scaled error                 0.83230558404196
median trajectory maximum error                0.50603741514036
component maxima R/Z/vR/vZ/Ip
  [0.1531778122, 0.2831731116, 0.7820425056,
   0.8323055840, 0.0934000434]
tube precursor halfwidths
  [0.3063556577, 0.5663462565, 1.5640860112,
   1.6646121681, 0.1868001367]
point-gate candidate count                            0 / 54
tube-cap candidate count                              0 / 54
```

Every held pair exceeded `0.4`; the worst held pair reached
`0.8323055840`. Stability projection therefore prevented divergent
recursion but did not repair the missing closed-loop context.

## Supporting development diagnostics

Several development-only probes were run to separate failure mechanisms.
They are route evidence, not alternate accepted models:

- causal GRU variants without future actions failed around `1.01--1.08`;
- a local causal k-nearest transition model failed at `1.3861`;
- a phase-labelled GRU still failed at `1.1808`, and phase was rejected as a
  potentially forbidden prefix surrogate regardless of that failure;
- 2,000-epoch and teacher-pretrained difficult-pair GRUs retained training
  errors `0.1933` and `0.2455`, with held errors `0.9221` and `0.9459`;
- simple causal baseline extrapolation failed at best at `1.1997`;
- even a deliberately forbidden oracle supplied with actual future executed
  actions failed at `0.3008`; and
- a causal context-conditioned baseline/response decomposition failed at
  `1.2333`, while its same-context linear response residual reached `0.5178`.

The four-expert GRU also stopped after eleven folds because an expert had
insufficient training rows. That is an exploratory-script design/runtime
error, not an experiment or TSC error. The phase-labelled script's emitted
`forbidden_label_inputs=0` field is a reporting error because that diagnostic
did use phase; it is excluded from accepted evidence.

## Scientific conclusion

D1R11 trajectories combine three evolving mechanisms after state 10:

1. authentic hidden-history-dependent plant response;
2. the R17 feedback controller and its causal queue/integrator state; and
3. online Card15 issue/cancel actions whose physical center changes with the
   closed loop.

The absolute future trajectory is therefore not a clean replacement-MPC
plant transition target. Stable recursion, causal calibration fingerprints,
past issued commands, local interpolation, neural recurrence, and even a
future-action oracle did not meet the unchanged gate. This does not prove
that the plant is uncontrollable or that a deconfounded plant model cannot be
built. It proves that the current D1R11 absolute closed-loop identification
target is inadequate for that purpose over the finite training boundary.

D1R11 and D1R12 probe trajectories remain forbidden from expert datasets.
No model, tube, MPC controller, expert data, BC, DAgger, or RL stage is
authorized.

## Next action

Freeze and execute a small authentic deconfounding safety sentinel. It must
reproduce the exact D1R11 causal calibration and state-0--10 prefix, then
apply exactly zero coil-current increment from task step 10 through the
unchanged formal horizon. The sentinel asks only whether the authentic plant
remains finite and the restart/action semantics remain exact without future
R17 feedback. A pass may authorize design of a separate zero-baseline
excitation sentinel, not a model campaign or MPC.
