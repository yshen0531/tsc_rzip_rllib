# R_geo/Z_geo 1 ms NR1R2 command/readback coordinate repair

Status: prospectively frozen before implementation and before any NR1R2 TSC
plant advance on 2026-08-13 Asia/Shanghai.

## 1. Immutable NR1R1 result

NR1R1 at source revision `2685710` ran nine authentic advances. Both hold
rollouts passed. Pattern A's first pulse then produced all 14 expected signed
effects with an exact maximum observed current change of `0.30000 A`. Before
issuing its q0 return, the pre-step gate stopped with:

```text
ISSUED_SLEW:pattern_a_primary.issued.1[11] exceeds the exact 0.3 A step limit
```

No return or later rollout ran. NR1R1 is immutable and incomplete.

PF3L exposes the defect. Its active pulse Card15 command is `-13.530 kA-turn`
and its q0 return command is `-13.500 kA-turn`, exactly `+0.300 A` after the
100-turn conversion. Its TSC pulse readback is `-13.530001 kA-turn`, which
includes the already observed fixed readback offset. The gate incorrectly
subtracted that readback from the next nominal command and obtained
`+0.30001 A`.

This mixed two distinct coordinates. Exact action safety must validate
successive serialized commands. Exact physical-effect safety must separately
validate successive readbacks. Neither comparison may mix one command with
one readback.

## 2. Frozen identity and unchanged experiment

```text
contract             rgeo-zgeo-1ms-nr1r2-v1
campaign             rgeo_zgeo_1ms_nr1r2_command_readback_v1
intended use         interface_validation
fixed source         1100 ms
control period       1 ms
single-turn limit    |delta I_i| <= 0.3 A per step, equality allowed
coil order           TSC
Card15 unit          kA-turn
```

NR1R2 keeps the identical six four-step rollouts, exact target Card15 fields,
24-advance maximum, geometry/Ip/current envelope, direct k-to-k+1 effect,
return, replay, stop behavior and claim boundary of NR1/NR1R1. It changes no
runner, TSC, target, queue, controller, model, optimizer, tolerance or pulse
amplitude.

## 3. Only authorized implementation change

Maintain two exact-decimal current paths in TSC order:

1. `active_command`: the canonical 1100 ms Card15 fields before the first
   issue, then the preceding issued target fields;
2. `actual_readback`: the original decimal `coil_currents.csv` fields at
   each state.

For every issue, require
`abs(next_command_i - active_command_i) <= 0.3 A`. After every plant advance,
independently require
`abs(next_readback_i - actual_readback_i) <= 0.3 A`. Equality is allowed in
both; any exact excess is rejected. First-effect signs and center-return
equivalence remain readback-to-readback tests.

Generated `inputa` fields must still match the frozen target exactly. The
primary record must expose both coordinates so an independent auditor can
detect accidental mixing. Tests must reproduce the PF3L command transition
`-13.530 -> -13.500 kA-turn = +0.300 A`, its readback transition, and reject
an actual excess in either coordinate.

## 4. Qualification gates and routes

Before real TSC, require local and installed-server full tests, exact deployed
hashes, public imports, compile/shell validation, a zero-TSC immutable NR1R1
forensic, and a fresh zero-TSC NR1R2 offline PASS. The NR1R1 forensic must
confirm its old stop identity, one pulse advance, exact observed 0.3 A, exact
proposed command return 0.3 A, and mixed-coordinate 0.30001 A diagnosis.

Fresh routes:

```text
offline failure     ONE_MS_NR1R2_OFFLINE_FAIL_NO_TSC
safety/action fail  ONE_MS_NR1R2_SAFETY_FAIL_STOP
effect/timing fail  ONE_MS_NR1R2_EFFECT_CONTRACT_FAIL_STOP
replay fail         ONE_MS_NR1R2_REPLAY_NOT_QUALIFIED
all gates pass      ONE_MS_NR1R2_INTERFACE_QUALIFIED
```

Only all-gates PASS may close 1 ms NR1. Every NR1-family record remains
forbidden from model fitting, training and expert data.
