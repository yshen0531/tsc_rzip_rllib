# R_geo/Z_geo 1 ms NR2R2C2aA2 supported-cube direction result

Date: 2026-08-14 Asia/Shanghai

Final scientific route:

```text
ONE_MS_NR2R2C2AA2_SUPPORTED_CUBE_DIRECTIONS_FAIL_REDESIGN
```

## Identity and validation

The design and implementation checkpoints are `104cfd5 / 8bd6964`. Exact
local/server hashes matched for the config, selection audit, primary runner,
independent auditor, focused test and launcher. Validation before real TSC was:

```text
local focused tests                         11/11
server focused tests                        11/11
server full suite                         1697/1697, one expected skip
offline preflight                              PASS
offline plant advances                            0
maximum frozen adjacent issue delta             0.3 A
```

The first attempted offline SSH command had a shell-quoting error and created
no plant result. The corrected invocation passed. This is a command-launch
error, not a stage or TSC failure.

## Authentic execution and independent audit

The server run was:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
rgeo_zgeo_1ms_nr2r2c2aa2_runs/
rgeo_zgeo_1ms_nr2r2c2aa2_supported_cube_directions_20260814_8bd6964
```

All three fresh canonical-source rollouts completed: 96/96 authentic 1 ms
advances and 99 states. No runtime, paired-boundary, limiter, Card15,
requested/readback slew, absolute-current, Ip, preissue-margin, outer-envelope
or successor-bound failure occurred. The maximum observed successor changes
over the three paths were `0.79909 mm R / 0.84181 mm Z / 33.2962 A Ip`, inside
the frozen `2 mm / 2 mm / 100 A` bound. Maximum issued and observed
single-turn changes both used the allowed `0.3 A`.

The structurally separate raw audit passed and reproduced every scientific
metric exactly:

```text
required final-raw files                         495
required final-raw bytes               5,830,399,476
inventory SHA-256  72611161f6f01e2374a89a6bfad998621b5b9103217314582a5d6e85660d0279
primary result SHA-256 9e94ce75071c0b9a05d0b4f97943273d272857c1c2d4136768702efda59e096f
independent SHA-256    c8e1a06c558531c83c222856f53d2d634aa4739372e14f413505165a64887ef9
maximum metric difference                                                   0
```

The audit reparsed the paired boundary, R_mid, Ip, all 14 coil currents, all
48 wire currents, action stream and required artifact inventory. Generated
`sprsina` remains diagnostic and does not qualify snapshot identity.

## Scientific result

All three directions opposed the q0 path at every state in the frozen
authority window, but none passed all unchanged C2aA1 gates:

| candidate | mean opposition | positive | maximum | max abs Ip vs q0 | route |
|---|---:|---:|---:|---:|---|
| p03-minus | 0.355931 mm | 14/14 | 0.523279 mm | 37.6619 A | FAIL maximum gate |
| p04-minus | 0.186802 mm | 14/14 | 0.273952 mm | 54.1139 A | FAIL mean and maximum |
| p07-minus | 0.159783 mm | 14/14 | 0.248190 mm | 28.0876 A | FAIL mean and maximum |

For p03-minus, opposition rose from `0.0613 mm` at state 3 to `0.5233 mm` at
state 16, with one small state-15 dip. Its mean and sign gates passed, while
the preregistered `1.5 mm` maximum gate did not. That gate is not weakened or
reinterpreted after the result: C2aA2 remains a scientific FAIL and found no
candidate eligible for its fresh-validation route.

The three endpoints still followed the large common source drift. They ended
about `-17.51..-17.65 mm R`, `+23.27..+23.45 mm Z` and `-339.5..-342.3 A Ip`
from source. This stage was an authority discriminator, not a nominal-hold
gate; these endpoint values are diagnostic.

This is a finite supported-cube action-direction authority FAIL. It is not a
runtime, interface, raw, model, controller, MPC, recovery, closed-loop or
global reachability failure. It also does not erase the descriptive evidence
that p03-minus has the strongest persistent sign-consistent effect of the
tested family.

## Next boundary

The evidence now supports a distinct question, not a threshold change: can
the p03-minus Card15 increment be accumulated one additional level, with each
single-turn step still `<=0.3 A`, while preserving hard bounds and producing
a prospectively specified incremental gain over this frozen p03 level? That
must be a separately frozen cumulative-domain sentinel with its own repeated
execution and independent audit. C2aA2 cannot itself authorize Nominal-H1,
C2b, a model, atlas, MPC, online adaptation or learning.
