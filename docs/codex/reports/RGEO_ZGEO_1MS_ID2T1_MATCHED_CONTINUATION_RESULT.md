# ID-2T1 matched continuation result

## Verdict

ID-2T1 completed all four authentic TSC continuations and the corrected
independent full-raw audit. The frozen route is:

`ONE_MS_ID2T1_MATCHED_CONTINUATION_CONTROL_UTILITY_FAIL_REVIEW`

This is a real, finite control-utility discriminator FAIL. It is not a
runtime, deployment, raw-integrity, prefix-replay, actuator, model-training,
controller, MPC, recovery, or plant-reachability failure.

## Identity and execution

- design revision: `3f857217`
- TSC implementation revision: `33ae7b968a5099e5add1b7fb28aacbb6c669b913`
- reporting-only revisions: `e7ed0616`, `07b12db5`
- config SHA-256:
  `49f736edb1a38bed1d2f6b41a44ebba041a4e7c836c93b5b09b9a77949f9b5d9`
- primary result SHA-256:
  `a53339a4bce5743562229e003bccfc16dcee70d775cd574965678d21364ff59d`
- corrected independent audit SHA-256:
  `323c3f5c0b4c386ba35d60d9214c2de986994638db0f4e431d24fc5bd19818aa`
- reset / TSC / verified advances: `4 / 136 / 136`
- retained states: `140`
- required artifacts: `700`, `8,245,009,360 bytes`
- inventory digest:
  `3cdb6c856db23c5112d995db16af18465fcc84375ce16bedc5dc401eb0365ee5`
- server validation before TSC: focused `6/6`; full one-ms suite `303/303`
- server focused validation after the reporting-only repairs: `6/6`

All four state-0--30/action-0--29 prefixes matched their respective ID-2S2
references. All actions, boundaries, Ip, coil/wire currents, step trips,
current limits and required raw artifacts passed. The independent audit
reparsed all 140 states, reproduced the inventory, metrics and FAIL route,
and reported no failures.

The first independent audit is retained with SHA-256
`569baa658421c91e9cd175ddd3d0c231b64bae663f1d82b4a4c41251035c82d6`.
It incorrectly treated the raw parser's absent `side` string as a mismatch
despite exact R_geo/R_mid, then a retained audit JSON was briefly enumerated
as a rollout. The repairs only derived HFS/LFS from `R_geo < R_mid` and read
the four frozen rollout filenames. No TSC was rerun and the scientific result
did not change.

## Measured result

The common p04+ continuation produced a clear but wrong-way response after
all four exact state-30 histories:

| preceding two-arm history | peak R/Z norm (mm) | best source-correction projection (mm) | best absolute source-distance improvement (mm) | max abs paired Ip (A) |
|---|---:|---:|---:|---:|
| p04+ then p07- | 0.09053 | -0.02923 | -0.02925 | 42.3592 |
| p07- then p07- | 0.09781 | -0.02953 | -0.02955 | 42.6244 |
| p07- then p07+ | 0.08836 | -0.02917 | -0.02919 | 42.8326 |
| p07+ then p04+ | 0.09205 | -0.02909 | -0.02911 | 41.9703 |

Signal and Ip were not the problem. Every response moved away from the
same-time direction back to the fixed 1100 ms source; therefore zero of four
histories passed the frozen utility gate. The maximum cross-history R/Z
response spread was only `0.009462 mm`, so within these four histories the
late response was consistently wrong-way rather than randomly unstable.

This contrasts with the earlier issue-24 p04+ response in the f03 sequence,
which had a strong positive-R/negative-Z source-correction component. The
current evidence therefore shows an action-time/evolving-state dependency;
it does not by itself separate absolute time, plasma position, passive-state
memory, or prior action age.

## Route decision

Do not continue a third-arm/fourth-arm schedule ladder and do not fit a larger
global network. The next useful step is a bounded zero-new-TSC timing/sign
attribution audit over the existing P1/S1/S2/T1 records. It should explicitly
compare the same Card15 p04+ primitive at issue 24 versus issue 30, using only
deployable exact R_geo/Z_geo/Ip, velocities, issued/readback/current history,
and event age. Its purpose is to freeze a small prospective fit-eligible
matched timing/history campaign, not to fully identify physics.

Only after that fresh campaign should a support-gated time/state-scheduled
low-order model be trained. Canonical-source TSC shooting remains an offline
Oracle/teacher candidate, not a 1 ms online controller. Authority, active
hold, bounded-tube recourse, static constrained control, calibration and blind
holdout remain later independent gates.
