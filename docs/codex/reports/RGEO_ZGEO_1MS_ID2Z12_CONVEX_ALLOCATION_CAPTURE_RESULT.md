# R_geo/Z_geo 1 ms ID-2Z12 convex-allocation capture result

Date: 2026-08-20 Asia/Shanghai

## Result

ID-2Z12 completed its exact preregistered identity at implementation revision
`4095655d`. Server validation passed focused `10/10` and all one-ms `492/492`
tests. The zero-TSC preflight admitted all `81/81` root/main action sequences
and reported zero plant calls.

The real campaign then completed:

```text
rollouts / reset calls                         19 / 19
verified plant advances                    1463 / 1463
retained states                                  1482
required artifacts                         7410 / 7410
required artifact bytes                    87279313368
inventory SHA-256     b53e5dd5e0556fbf385b482f251b3bcd67be58e4cd1bfa17a11a4011bb4e771a
execution / raw / prefix / replay          PASS / PASS / PASS / PASS
independent raw audit                       PASS, failures=[]
models / calibration / holdout read          0 / 0 / 0
```

The exact selected allocations were:

```text
state-61 round        b4     (alpha_B=+1.0, alpha_F=0.0)
state-65 round        pf4    (alpha_B=-0.5, alpha_F=+0.5)
fresh selected replay                                  exact
six-state capture                                      FAIL
```

The immutable final route is:

```text
ONE_MS_ID2Z12_SIGNED_BF_CONVEX_BASIS_NO_CAPTURE_CLOSE_ROUTE
```

## Quantitative result

At state 61, hold's terminal normalized score was `3.3163391`. `b4` was the
best frozen candidate at `3.0134058`, an improvement of `0.3029333`; `bf4`
and `f4` also improved by `0.1913503` and `0.1693881`. None captured.

At the selected state-65 history, the b4 continuation itself became worse
than hold. The only candidate meeting the `0.02` improvement gate was `pf4`:

```text
arm    score       max distance    max speed      max |Ip-source|/|Ip0|
hold4  3.0134058   29.111665 mm    0.301341 m/s  3.07053%
pf4    2.9836694   28.769669 mm    0.298367 m/s  3.13375%
```

The selected path therefore found finite local utility but reached no
capture basin. Its closest single-state normalized capture score was
`1.418440` at state 62 (`26.003222 mm`, `0.141844 m/s`, `3.59853% Ip`). No
state on the trajectory simultaneously satisfied `25 mm / 0.1 m/s / 5%`,
and terminal states 72--77 moved from `27.469283` to `28.769669 mm` while
speed remained `0.277381--0.298367 m/s`.

## Scientific classification

This is a clean finite action-basis/capture failure, not a runtime, Card15,
current, boundary, prefix, raw, replay or reporting failure. It closes the
complete signed convex span of the frozen B/F increments at this exact
state-61 causal history under the two four-issue receding decisions and the
unchanged capture contract.

It does not prove global plant unreachability, failure of every 14-D action
basis, failure from an earlier takeover state, or impossibility of a
different nominal/capture co-design. It does not authorize relaxing the
capture set, adding a denser B/F coefficient grid, appending a third B/F
round, or training a larger model on this failed grammar.

## Route decision

The next route moves earlier in the takeover trajectory and changes the
physical action basis. Before another TSC campaign it must:

1. separate transport, velocity arrest and terminal recourse from the first
   moving-nominal decision rather than patching capture after state 61;
2. audit a genuinely new exact Card15 direction outside the signed B/F span,
   its slew/headroom polytope and measured finite response support;
3. freeze one bounded joint nominal/capture campaign with no post-result
   action additions;
4. keep exact observation/history, current/Ip/boundary gates, fresh replay
   and independent raw audit unchanged.

Only a true finite capture plus replay may open Recourse-L1 design. Model,
calibration, holdout, controller, waypoint/path and R_mid claims remain
blocked.

## Evidence and cleanup

Tracked compact evidence is under
`docs/codex/audits/rgeo_zgeo_1ms_id2z12_20260820_4095655d_v1`.
Load-bearing hashes include:

```text
result.json                 1bfc88b5b2f85a0f8c5c2ad3db39af3ba0c8d5f36a77efb92e175c8678927397
independent_raw_audit.json  f776df44f54634fb87664bb5d435f4154fe06237783d99148de55cb7807a9876
server_validation.log      dd0ad427394eee4dfd55371de05e601694c1383e5f49dcbd7c18775ba3b7c318
server_run.log             40ca7dfe30b1430138e05e03e006ba1a277f2d2ad46e250e70986165a092a702
```

After all 25 downloaded compact/log files matched the server SHA-256 list,
the exact `88638097421`-byte remote output tree and its stage-specific
temporary logs were irreversibly deleted. Server free space returned to
`118121205760` bytes. No unrelated server path was touched.
