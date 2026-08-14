# R_geo/Z_geo 1 ms NR2R2C2aA1 level-2 authority result

Date: 2026-08-14 Asia/Shanghai

Final route:

```text
ONE_MS_NR2R2C2AA1_LEVEL2_AUTHORITY_FAIL_REDESIGN
```

## Identity and validation

The prospective design was frozen at `64c2983`. Implementation checkpoint
`4845004` added the primary runner, a final-raw independent audit, focused
tests and the server launcher. Its first zero-TSC offline result correctly
stopped before plant execution because the implementation checked the
Card15 doubled-offset identity after separate repeating-decimal per-turn
conversions. The frozen design defines that identity in the exact Card15
field coordinate. Checkpoint `3e85a4b` moved only this audit predicate to
that coordinate and added a regression test; it changed no field, schedule,
threshold, safety rule or TSC semantics. The original offline FAIL is retained.

Accepted validation at `3e85a4b` was:

```text
local focused tests                         9/9
local Windows-shimmed full suite         1708/1708
server focused tests                        9/9
server full suite                        1691/1691, one expected skip
accepted offline plant advances             0
accepted offline action steps               32
maximum exact adjacent issue delta        0.15 A
```

The direct Windows run without the established POSIX `resource` shim had 27
import errors and no test-body failure. That is a local platform distinction,
not a C2aA1 regression.

## Authentic execution and raw integrity

The accepted server run was:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
rgeo_zgeo_1ms_nr2r2c2aa1_runs/
rgeo_zgeo_1ms_nr2r2c2aa1_level2_authority_20260814_3e85a4b
```

Both canonical-source replays completed: 2/2 rollouts, 64/64 authentic 1 ms
advances and 66 states. No runtime, boundary, limiter, Card15,
command/readback slew, absolute-current, Ip, preissue-margin, outer-envelope
or successor-bound failure occurred. Maximum observed successor changes were
`0.829781 mm R / 0.8209955 mm Z / 22.0120 A Ip`, inside the prospectively
frozen `2 mm / 2 mm / 100 A` bound. Maximum issued and observed single-turn
current changes were both `0.15 A`.

The independent raw audit reparsed every required state and exactly agreed
with the primary result:

```text
required final-raw artifact files                         330
required final-raw bytes                        3,886,932,984
inventory SHA-256  e297d26c2eb13d85dc10ced2a8dc7a954fbbbf31b8477e0ac6cba90ad169c594
primary result SHA-256 f069c33191a13f03c872c52e54d72d0ff40c1019e504b0e8337a435f60e36cd6
independent SHA-256    286a96b7e3ce5162a6adaa92dc424f05280b671b1bfe79d971c3250dc44ade15
maximum metric difference                                                  0
```

Paired `R_geo/Z_geo/R_mid`, Ip, all 14 coil currents, all 48 wire currents,
the action/effect stream and the four semantic artifact hashes were exact at
all states. Generated `sprsina` hashes were not exact, as in B0/C1a; this is
diagnostic only and does not qualify snapshot identity.

## Scientific result

The componentwise q0+/-0.3 A level2 target did not provide persistent
authority opposing q0's `(-R,+Z)` drift:

| authority metric, states 3..16 | measured | frozen gate |
|---|---:|---:|
| mean opposition | 0.0070801 mm | >=0.250 mm |
| positive states | 2/14 | >=7/14 |
| maximum opposition | 1.0156325 mm | >=1.500 mm |
| maximum absolute Ip deviation from q0 | 32.4491 A | <=100 A |

Both replays were bit-for-bit equal on the checked coordinates. Only states 5
and 12 were favorable (`1.01563 mm` and `0.95302 mm`); the other twelve
states were negative. Relative to the earlier constant level1 trajectory,
level2 made opposition worse at every state 3..16: the level2-minus-level1
mean was `-0.0743658 mm`, with 0/14 positive differences. Increasing this
particular static p07-plus direction therefore did not reveal a useful
persistent gain.

The endpoint remained close to q0 drift: `-17.701717 mm R`,
`+23.4364775 mm Z` and `-331.6315 A Ip` from source. This stage was not a
hold gate, so those endpoint values are diagnostic rather than a second
post-result criterion.

This is a finite action-direction/schedule authority FAIL. It is not a
runtime, interface, raw, model, controller, MPC, recovery, closed-loop or
global plant-reachability failure. It rejects this exact p07-plus cumulative
level and does not prove that another Card15 direction, a time-varying
sequence or a larger cumulatively slewed center cannot control the geometry.

## Next boundary

Nominal-H1, C2b, response atlas, model fitting and MPC remain blocked. The
next prospective C2a discriminator should stay inside the already supported
q0+/-0.3 A componentwise cube and test sign-reversed, persistently favorable
development directions before requesting any larger absolute-current domain.
The consumed NR2R1 development records may be used only to choose and freeze
that small candidate family; the invalid holdout remains forbidden. A new
stage must retain exact paired-boundary/current/slew/raw gates and its own
independent result audit.
