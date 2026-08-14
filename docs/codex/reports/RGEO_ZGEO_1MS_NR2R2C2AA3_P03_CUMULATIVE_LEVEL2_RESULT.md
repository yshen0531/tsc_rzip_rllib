# R_geo/Z_geo 1 ms NR2R2C2aA3 p03 cumulative-level2 result

Date: 2026-08-14 Asia/Shanghai

Final route:

```text
ONE_MS_NR2R2C2AA3_P03_CUMULATIVE_LEVEL2_PASS_TIME_VARYING_C2A_DESIGN_ONLY
```

## Identity and execution

The prospective design and plant implementation checkpoints are
`0821c78 / e01411d`. Exact server deployment hashes matched. Before TSC,
focused tests passed 15/15, the server suite passed 1701/1701 with one
expected skip, and the zero-plant offline gate passed with maximum adjacent
issue delta exactly `0.3 A`.

Both fresh canonical-source replays completed: 64/64 authentic advances and
66 states. Maximum successor changes were `0.803476 mm R / 0.827237 mm Z /
42.7190 A Ip`, inside the prospective `2 mm / 2 mm / 100 A` bound. Maximum
issued and observed current steps were both `0.3 A`. The checked geometry,
Ip, all 14 coil currents, all 48 wire currents, actions and semantic artifact
hashes were exact between replays. `sprsina` was non-identical and remains
diagnostic.

## Audit correction and raw integrity

The first independent audit parsed the raw files but stopped before verdict
with `KeyError: artifact_sha256`: its local state rows did not retain the
already computed artifact hashes needed by the pair comparator. Checkpoint
`134b133` added only those audit fields and a regression test. No action,
threshold, primary result, raw file or TSC step changed. Server full tests then
passed 1702/1702 with one expected skip.

The corrected independent audit passed and reproduced every metric exactly:

```text
required final-raw files                         330
required final-raw bytes               3,886,932,984
inventory SHA-256  08749807d68650a23d7575aad66c4fe15919ab9e7ce7d4caa898837b0b3e5fa4
primary result SHA-256 1e082fda5e87e74655f53215b4815edb563ffd386516b704abd34a5393d71b76
independent SHA-256    12be18d78acb1fe373bb975e8153f41e1802bc56ff872c8400cacb9ed24834c1
maximum total/incremental metric difference                              0 / 0
```

## Scientific result

Both identical replays produced:

| frozen metric | measured | gate |
|---|---:|---:|
| mean total opposition | 0.741923 mm | >=0.500 mm |
| positive total states | 14/14 | 14/14 |
| maximum total opposition | 1.072706 mm | >=0.750 mm |
| mean incremental opposition over level1 | 0.385992 mm | >=0.150 mm |
| positive incremental states | 14/14 | >=11/14 |
| maximum absolute Ip difference from q0 | 75.758 A | <=100 A |

Total opposition increased from `0.2147 mm` at state 3 to `1.0727 mm` at
state 16. The level2-minus-level1 increment was positive at every state and
grew from `0.1534 mm` to `0.5494 mm`. This is direct finite evidence that a
second exact p03 Card15 increment can be accumulated safely and adds useful
authority in this source/time/history envelope.

It is not a hold result. After return to q0, the endpoints were still
`-17.5588 mm R / +23.0815 mm Z / -346.471 A Ip` from source. Nor does the PASS
establish linear scaling, a general cumulative command domain, a controller,
recovery, MPC, closed-loop tracking or global reachability.

## Next boundary

This PASS authorizes only a separately prospective time-varying C2a nominal
search using the already qualified q0, p03 level1 and p03 level2 cells. The
search must preserve the exact 1 ms/Card15/paired-boundary/current/Ip/successor
interfaces and independent raw audit. Nominal-H1 requires a separately frozen
fresh validation after a candidate is selected. C2b, atlas, model fitting,
MPC, adaptation and learning remain blocked.
