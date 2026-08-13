# R_geo/Z_geo 1 ms NR2R2A identifiability audit result

Final route:

```text
ONE_MS_NR2R2A_IDENTIFIABILITY_AUDIT_COMPLETE_SOURCE_BASELINE_RECOVERY_DESIGN_REQUIRED
```

NR2R2A completed exactly its local, zero-TSC, zero-fit scope.  Primary and
independent implementations authenticated the same 28 NR2R1 development/
calibration compact records and agreed at the frozen `1e-12` tolerance.  No
holdout, server raw, server command, TSC, model, controller or optimizer was
used.

## Result

The old campaign is not a supported eight-step causal identification set.
Using complete histories only, with no padding:

| Split / action coordinate | largest full-column-rank lag | lag-8 rank |
|---|---:|---:|
| development / issued increment | 7 | 94/112 |
| development / q0 offset | 7 | 94/112 |
| calibration / issued increment | 3 | 40/112 |
| calibration / q0 offset | 2 | 41/112 |

Even the development full-rank edge is poorly supported: the lag-7 condition
number is about `14,513` for issued increments and `202` for q0 offsets.
These figures do not prove a 7 ms physical memory length.  They show that the
existing action schedule cannot independently identify the eight-frame kernel
that the old ARX representation assumed.

The other decisive gaps are unchanged and now machine-recomputed:

- 28/28 trajectories start from the same physical 1100 ms state;
- 476/476 states are HFS and there is only one position anchor;
- there are zero independent full-horizon all-q0 baselines;
- all targets remain inside `q0 +/- 0.3 A`, so cumulative center movement was
  never tested;
- no same primitive is repeated across position anchors and no matched-time/
  different-position or matched-position/different-arrival-history contrast
  exists; and
- the old model repeats its first frame as missing history, includes
  `step/16`, and has no explicit stable passive/innovation state.

Therefore NR2R1 cannot separate position, absolute time, common drift and
arrival history.  The user's position/history hypothesis remains physically
plausible but unmeasured.  A larger recurrent network on these records would
not repair the experimental geometry.

## State representation decision

The next model must retain exact Card15/readback/queue semantics and observe
`R_geo/Z_geo/Ip`, all 14 actual coil currents, causal action history,
queue/action age, time/dt, `R_geo-R_mid` and missing masks.  It must estimate a
shared velocity/drift/passive/innovation belief with calibrated uncertainty at
1100 ms.  The 48-wire vector stays diagnostic/auxiliary unless deployment
availability is separately proved.  History never resets at `R_mid`.

No model class is selected.  The next fresh evidence must first establish a
q0-command baseline, same-prefix repeatability, a measured tail window and a
non-circular hold/backup/recovery route.  Returning the coil command to q0 is
not plasma recovery.

## Erratum

NR2R2A found one derived-summary error in the preceding descriptive audit.
The maximum signed-pair Ip half-difference is `30.14075 A` at development pair
0, horizon 6, not `22.50995 A`.  Both new implementations reproduce the
correct value.  R/Z scalars, raw/compact records and architecture conclusions
are unchanged.

## Authorization boundary

This is an audit-complete result, not a predictor or control PASS.  It does
not authorize NR3, fitting, MPC, RL, Oracle replay or a TSC campaign by
itself.  The next action is to freeze the separate source baseline,
repeatability and hold/recovery sentinel, including exact stop bounds and
maximum plant budget, before implementation or server deployment.
