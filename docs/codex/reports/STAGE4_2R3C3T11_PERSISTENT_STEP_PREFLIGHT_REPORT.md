# Stage4.2R3c3T11 persistent-step preflight report

## Result

The corrected T11 offline preflight passed both frozen public actuator
cases. It executed no Ray, `gotsc`, TSC, plant step, controller, trajectory,
or snapshot.

```text
actuator cases                                             2/2
existing schedule rank                                   12/12
new persistent-step rank                                   6/6
augmented schedule rank                                  18/18
maximum augmented normalized condition              3.1459621
minimum new-column residual outside old span        0.7726912
bounded and exact zero net                                2/2
all frozen preflight gates                               PASS
```

The result authorizes implementation of the frozen 416-task real
identification identity. It does not authorize a controller or R3c4.

## Provenance

```text
local branch
  codex/stage4_2r3c3t11-persistent-step-preflight

design implementation
  3798a21

rank hotfix
  0b61f93

exact T3/T9 source-reference hotfix and package v2
  a9807b9

design config SHA-256
  073ac84d4d9c8c3caf9fdcb485e2cc8aeb0ae65c5c7b5aed7e65b579d440e4dd

preflight JSON SHA-256
  a449fd5447bd174b5fa067f464c651bc5a1d3e146bae7f67d22535eed076dfbd

preflight log SHA-256
  aec6db4f4c35436825b66181adb888dc0b9b1622c6aaf2c6c0886ca2eb009050
```

Remote output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t11_preflights/
stage4_2r3c3t11_persistent_step_preflight_v3_20260731_a9807b9/
stage4_2r3c3t11_persistent_step_response_preflight_v1.json
```

The exact existing-bank source is the T3 eight-basis bank authenticated by
T6 and T9, SHA-256
`6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86`.
T6, T9, and T10 compact source hashes were also authenticated exactly.

## Case details

```text
delay 0, slew 1.0
  T9 reproduction error                         1.3323e-15
  augmented condition                           3.1459621
  minimum novelty residual                      0.7726912

delay 2, slew 0.9
  T9 reproduction error                                  0
  augmented condition                           3.0900455
  minimum novelty residual                      0.7904114
```

Each case contains the same six public schedules: transport and braking
steps for modes 0, 1, and 2. Every schedule has seven nonzero issues, exact
zero requested net, component bound `0.0075`, and post-contract
neutralization at physical effect states 39 through 44.

## Error classification

Before the valid result, the first Linux package validation stopped on a
CRLF checksum-file defect. Two offline preflight invocations then stopped
before writing JSON because T11 reconstructed the old schedule space from
the wrong same-shape T7 bank; one also exposed an unnormalized numerical
rank calculation. These were packaging and offline source/reporting bugs.
They produced no scientific result and changed no experiment semantics.

The valid v3 result has no runtime, raw-data, snapshot, solver, statistics,
or reporting error. Because it is action-space-only, it supplies no restart,
hidden-history, control, or plant-response conclusion.

## Frozen next identity

```text
32 extended zero-probe baselines
32 contexts x 6 bases x 2 signs = 384 signed probes
416 authentic restart TSC rollouts total
```

Real acceptance must require exact execution/restart/causality, central
symmetry, matched-history response invariance, current utilization at most
`0.55`, response rank 6, and velocity condition at most 25 in all 32
contexts. Formal tracking remains diagnostic. Probe trajectories remain
forbidden from expert data. The 250/270 ms arrival and 350/370 ms hold
contract is unchanged.
