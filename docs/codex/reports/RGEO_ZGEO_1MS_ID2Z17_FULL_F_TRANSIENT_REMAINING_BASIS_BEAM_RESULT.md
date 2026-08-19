# ID-2Z17 full-F-transient remaining-basis beam result

## Result identity

ID-2Z17 ran once on the server from implementation revision
`4bfcca2d7c7185dd4a08ef76db7a352005836f91`. The frozen config SHA-256 was
`4308452e9480574a13703b41816c6fc7145a4b559992aac86e2ced58a612486a`.
Before any plant advance, server validation passed the focused suite `13/13`,
the complete 1 ms suite `548/548`, the shell/compile checks, the storage gate,
and all `121/121` statically enumerated schedules.

The campaign completed all `18/18` authentic rollouts, `1170/1170` verified
plant advances, `1188` states and `5940` required artifacts. The independently
recomputed raw inventory was `69,964,793,712` bytes with digest
`07fe40a1a22e844c007f0ad2852e81d8c123a63b7c2ad154c0e5305339baed1e`.
Execution, exact Card15/current/slew, canonical-prefix, raw-integrity and fresh
selected-path replay gates passed. There were zero guarded safe stops, zero
model fits and zero calibration or holdout reads.

## Frozen scientific result

No branch satisfied the unchanged six-state capture gate. Round zero selected
two distinct base directions, `p08_plus4` and `p06_plus4`. The complete round
zero metrics were:

| arm | terminal worst score | max source distance (mm) | max speed (m/s) | max source-relative Ip |
|---|---:|---:|---:|---:|
| `p08_plus4` | 3.966136 | 28.361732 | 0.396614 | 2.27042% |
| `p06_plus4` | 3.993789 | 27.634035 | 0.399379 | 2.69403% |
| `p02_plus4` | 4.158449 | 28.614892 | 0.415845 | 2.37388% |
| `h4` | 4.164724 | 28.254919 | 0.416472 | 2.44142% |
| `p05_minus4` | 4.207454 | 28.656183 | 0.420745 | 2.37353% |
| `p00_plus4` | 4.213686 | 28.095753 | 0.421369 | 2.54964% |
| `p05_plus4` | 4.456507 | 28.235525 | 0.445651 | 2.51195% |
| `p02_minus4` | 4.494094 | 28.181317 | 0.449409 | 2.51186% |
| `p08_minus4` | 4.567745 | 28.436301 | 0.456774 | 2.61388% |
| `p06_minus4` | 4.635653 | 28.961522 | 0.463565 | 2.21146% |
| `p00_minus4` | 4.773237 | 28.861825 | 0.477324 | 2.35132% |

The six fixed second-layer continuations were:

| path suffix | terminal worst score | max source distance (mm) | max speed (m/s) | max source-relative Ip |
|---|---:|---:|---:|---:|
| `p08_plus4__p08_plus4` | 3.771440 | 28.167666 | 0.377144 | 2.12136% |
| `p06_plus4__p08_plus4` | 3.775304 | 27.771706 | 0.377530 | 2.54531% |
| `p08_plus4__p06_plus4` | 3.779677 | 27.835425 | 0.377968 | 2.53175% |
| `p06_plus4__p06_plus4` | 3.861888 | 27.155926 | 0.386189 | 2.95889% |
| `p08_plus4__h4` | 3.966136 | 28.361732 | 0.396614 | 2.27042% |
| `p06_plus4__h4` | 3.993789 | 27.634035 | 0.399379 | 2.69403% |

The selected `f100__f8__f8__p08_plus4__p08_plus4` path replayed exactly.
Relative to the inherited hold score `4.164724`, it improved the frozen score
by `0.393285` (`9.44%`), but its worst terminal speed was still `0.377144
m/s`, about `3.77` times the `0.1 m/s` capture threshold. The exact state-48
starting point was `23.207303 mm / 0.218018 m/s / +1007.7375 A`; every tested
round-zero arm subsequently had a minimum one-step speed above `0.238 m/s`.
The new directions therefore have finite trajectory effect, but this exact
late, two-layer cumulative grammar does not create a capturable terminal set.

The final route is
`ONE_MS_ID2Z17_NEW_BASIS_BEAM_NO_CAPTURE_PHYSICAL_REACHABILITY_REDESIGN_REQUIRED`.
It closes this exact state-48, two-layer, first-event cumulative grammar. It
does not prove global plant unreachability, absence of all p06/p08 authority,
or failure of a full-horizon feedback controller using a materially different
action allocation.

## Evidence and cleanup

Primary, independent, selected replay and launch-log SHA-256 values are:

- `58e89a7292b8f256bb58d1e633d0e46794852727675f9db79da188da13f37994`;
- `ad86d43a83dec29bf6b2d37f69a01c44518c548b7bb5cd53cf5ce9f70cbb1419`;
- `024084c99e17a7334d7130327af98aa7e9b910a60da8419c45cdaea507774ca1`;
- `7d31c9b81ff5b6ac09000ff547133459992c05b65a1b65dd19ed13af636b9f79`.

All `22/22` retained top-level compact/log files matched between server and
local SHA-256. Only after the independent raw audit and compact recovery, the
exact run's `rollouts/` subtree was removed (`71,071,432,704` filesystem
bytes). The compact JSONs and launch log remain on both machines; server free
space afterward was `118,093,258,752` bytes.

## Route decision

Do not add a third late layer, denser late amplitudes, a nearby state-48 root,
or train on ID-2Z17. The next bounded work is a zero-new-TSC full-horizon
reachability and learning-contract redesign. It must replace the repeated
late macro ladder with a prospectively fit-eligible, time-varying action
allocation that jointly treats transport, velocity capture, Ip/headroom and
terminal persistence from takeover. Any new model must be trained only on a
newly declared development identity and must predict control-relevant
increment/velocity and multi-step value under exact 1 ms truth recentering;
ID-2Z17 remains route evidence with zero fit weight.
