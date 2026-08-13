# R_geo/Z_geo 1 ms NR1R1 exact-decimal readback repair

Status: prospectively frozen before implementation and before any NR1R1 TSC
plant advance on 2026-08-13 Asia/Shanghai.

## 1. Why NR1R1 is separate

The immutable NR1 run at source revision `129a091` stopped after nine plant
advances. Two four-step hold rollouts passed. The first Pattern A pulse was
then applied once and the runner stopped before any return or later rollout.
Its sole primary failure was:

```text
OBSERVED_SLEW:pattern_a_primary.observed.0[11] exceeds the exact 0.3 A step limit
```

Raw `coil_currents.csv` text for PF3L was `-13.500001 kA-turn` at 1100 ms
and `-13.530001 kA-turn` at 1101 ms. With 100 turns, exact decimal
conversion gives:

```text
(-13.530001 - -13.500001) * 1000 / 100 = -0.300000 A
```

All 14 exact-decimal observed increments were at or below 0.3 A. The
original validator first converted both fields to binary64 and then converted
the binary64 subtraction through decimal strings. For PF3L this yielded an
artificial magnitude slightly above 0.3 A. This is a numerical interface and
reporting defect, not an observed physical slew violation, TSC failure, or
control-model result.

The stopped NR1 directory, reports and verdict remain immutable. NR1R1 uses
a new contract/campaign identity and a fresh run directory; it neither
resumes nor overwrites NR1.

## 2. Frozen identity and unchanged experiment

```text
contract             rgeo-zgeo-1ms-nr1r1-v1
campaign             rgeo_zgeo_1ms_nr1r1_decimal_readback_v1
intended use         interface_validation
fixed source         1100 ms
control period       1 ms
single-turn limit    |delta I_i| <= 0.3 A per step, equality allowed
coil order           TSC
Card15 unit          kA-turn
```

NR1R1 retains, without change, the six four-step rollouts, target Card15
fields, maximum 24 authentic advances, 30 states, direct issue-at-k to
readback-at-k+1 effect contract, exact q0 return, safety envelope, replay
tolerances, stop behavior and claim boundary frozen in
`RGEO_ZGEO_1MS_NR1_SAFETY_EFFECT_QUALIFICATION_DESIGN.md`.

There is no new pulse amplitude, reserve, tolerance, queue, controller,
model, optimization, or adaptive behavior. Equality at exactly 0.3 A remains
accepted, and any exact decimal value above 0.3 A remains rejected.

## 3. Only authorized implementation change

For observed TSC coil-current checks, parse each finite decimal
`coil_currents.csv` kA-turn value without first subtracting binary64 values.
Convert component `i` to single-turn amperes using:

```text
I_i[A] = Decimal(ccoil_i[kA-turn]) * Decimal(1000) / Decimal(turns_i)
```

Perform issued, observed, first-effect-sign, and q0-return comparisons in
that decimal representation. JSON may store the exact amperes as decimal
strings alongside the existing float values. Geometry, Ip and wire-current
processing are unchanged.

The generic slew validator must continue to reject an explicit input
`0.30000000000000004 A`; the repair is not an epsilon or relaxed threshold.
Tests must cover exact 0.300000 acceptance from CSV-scale decimal inputs,
strict above-limit rejection, and the observed PF3L pair.

## 4. Gates and routes

Before real TSC, require focused and full local tests, installed-server full
tests, public imports, compile/shell checks, source hashes, and a new zero-TSC
offline PASS under the NR1R1 identity. A zero-TSC immutable-raw forensic must
also reproduce the old PF3L classification as exactly 0.300000 A while
retaining the old run's incomplete status.

Fresh NR1R1 routes are:

```text
offline failure     ONE_MS_NR1R1_OFFLINE_FAIL_NO_TSC
safety/action fail  ONE_MS_NR1R1_SAFETY_FAIL_STOP
effect/timing fail  ONE_MS_NR1R1_EFFECT_CONTRACT_FAIL_STOP
replay fail         ONE_MS_NR1R1_REPLAY_NOT_QUALIFIED
all gates pass      ONE_MS_NR1R1_INTERFACE_QUALIFIED
```

Only the all-gates route can close the 1 ms interface qualification and
permit a separately frozen NR2 design. NR1 and NR1R1 records remain forever
forbidden from model fitting, training and expert data.
