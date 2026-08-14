# R_geo/Z_geo 1 ms NR2R2C2aA2 supported-cube direction discriminator

Date: 2026-08-14 Asia/Shanghai

Prospective identity:

```text
rgeo-zgeo-1ms-nr2r2c2aa2-supported-cube-directions-v1
```

## Question and evidence boundary

C2aA1 safely rejected one persistent p07-plus level. C2aA2 asks the smaller
next question: does any of three prospectively selected minus-sign directions,
held at the already supported componentwise `q0 +/- 0.3 A` boundary, produce
persistent opposition to the source q0 path?

Candidate selection used only consumed NR2R1 development records. In states
2--5 after their first event, p03-minus, p04-minus and p07-minus each had 4/4
positive same-time opposition to q0. Their descriptive means were only
`0.06620 / 0.05319 / 0.04188 mm`; this is deliberately not treated as a
plant map or authority PASS. Exact provenance and values are frozen in the
tracked selection audit. No invalid holdout, calibration refit, model,
optimizer or server raw was used.

## Frozen schedules

Each candidate starts from a fresh canonical 1100 ms reset and executes 32
one-millisecond advances. All three reach their full target at issue step 2,
so the authority window is the common states 3--16.

- `p03_minus`: q0 at steps 0--1, full at 2--15, q0 at 16--31.
- `p04_minus`: q0 at 0, level1 at 1, full at 2--15, level1 at 16, q0 at
  17--31.
- `p07_minus`: the same level schedule as p04-minus.

The p03 full target was already issued as a development impulse. The p04 and
p07 full targets are exact Card15 doubled offsets from their already issued
level1 fields. Every target stays componentwise inside `q0 +/- 0.3 A`; every
adjacent single-turn issue delta is at most `0.3 A`, with equality allowed.
This design does not test cumulative migration beyond that cube.

## Unchanged hard gates

The runner must fail closed before or immediately after each advance on an
invalid paired boundary, limiter geometry, exact Card15 mismatch, requested or
readback slew above `0.3 A`, absolute-current breach, Ip breach, unavailable
next-step reserve, outer-envelope breach, or successor change beyond
`2 mm R / 2 mm Z / 100 A Ip`. It retains the C2aA1 inner/outer source margins
of `25/50 mm R,Z` and `5/10% Ip`. Legacy runner clipping may not be relied on.

For each candidate and every state `k=3..16`:

```text
opposition[k] = (R_candidate[k] - R_q0[k])
              - (Z_candidate[k] - Z_q0[k])
```

A candidate passes only if all unchanged C2aA1 authority gates pass:

```text
mean opposition                 >= 0.25 mm
positive opposition fraction    >= 0.5
maximum opposition              >= 1.5 mm
maximum |Ip_candidate-Ip_q0|    <= 100 A
```

The primary result must retain all final raw state directories and actions.
An independent auditor must reparse paired boundary geometry, R_mid, Ip, all
14 coil currents, all 48 wire currents, exact issue/effect history, Card15
fields and the four semantic artifact hashes. `sprsina` remains a diagnostic
hash and does not qualify snapshot identity.

## Routing

- If no candidate passes, route
  `ONE_MS_NR2R2C2AA2_SUPPORTED_CUBE_DIRECTIONS_FAIL_REDESIGN` and stop. The
  result rejects only this frozen family inside this finite source envelope.
- If one or more candidates pass, route
  `ONE_MS_NR2R2C2AA2_SUPPORTED_CUBE_DIRECTION_FOUND_FRESH_VALIDATION_REQUIRED`.
  Freeze the passing candidate before a separate fresh repeated validation.

Even PASS is not Nominal-H1, bounded-tube recovery, a response atlas, a
model, MPC, online adaptation, RL, closed-loop control, or global
reachability evidence. No later stage is implicitly authorized.
