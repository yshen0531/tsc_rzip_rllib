# ID2Z30 fresh q-model qualification result

Date: 2026-08-21  
Implementation revision: `f976ea5a3d0ed8ce3469d614f67c90a24cfbf52e`  
Config SHA-256: `37b0bdfeb56079cd6de9fe95805de96294848534d75cda620e5ba179049f1c95`

## Frozen result

ID2Z30 completed all ten prospectively frozen fresh trajectories: ten resets,
730/730 verified plant advances, 740 retained states and 3,700 required raw
artifacts. Execution, exact Card15 action streams, prefix checks, raw
integrity and the exact calibration replay passed. The structurally separate
raw auditor accepted the completed evidence with no failures.

The issue-36 calibration family passed the unchanged model gates:

- scaled response RMSE `0.0563540`;
- scaled absolute-error p95 `0.1106675`;
- minimum R/Z direction cosine `0.9815484`;
- maximum terminal response-velocity error `0.0251391 m/s`;
- h8 action-ranking regret `0`.

The calibration PASS opened the four issue-44 blind trajectories. The blind
family failed the frozen point-model and calibrated-tube gates:

- scaled response RMSE `0.6725395`;
- scaled absolute-error p95 `0.1936435`;
- minimum R/Z direction cosine `0.2653222`;
- maximum terminal response-velocity error `0.0473644 m/s`;
- h8 action-ranking regret `0`;
- calibrated-tube containment `94/96`, maximum ratio `16.2864`.

The immutable final route is
`ONE_MS_ID2Z30_FRESH_BLIND_FAIL_CLOSE_Q_MODEL_ROUTE`. This is a clean fresh
model-qualification FAIL, not a runtime, actuator, prefix, raw, replay,
controller, Authority-L0, Recourse or plant-reachability failure. The model
was not refit and the planned zero-fit cardinal feedback sentinel was not
opened.

Primary result SHA-256:
`f5bd3a3a85f22f0781aa81d82e528763b9aeefd59819a72e49fac14de46d3925`.
Independent audit SHA-256:
`75a486f2054d9f3d010b33789947b63a47b0536332f2fb626bfacb0683e4c013`.

## Bounded post-result attribution

The two containment failures are both the issue-44 `q_Z+` branch at h5:

| component | signed prediction error | calibrated tube | ratio |
|---|---:|---:|---:|
| R | `-0.647808 mm` | `0.039776 mm` | `16.2864` |
| Z | `+0.0941895 mm` | `0.0268115 mm` | `3.5130` |

The other three blind branches each passed their branch metrics. In the
matched baseline, the isolated positive-R transition occurs at state 50
(`+0.343287 mm` from state 49); under `q_Z+` it occurs one state earlier at
state 49 (`+0.319810 mm` from state 48). At h6--h8 the paired response returns
to the smooth-response scale. Thus the observed failure is an action-linked
one-millisecond event-phase shift, not a persistent 0.65 mm gain change. This
is descriptive attribution from the frozen compact trajectories; it neither
identifies a physical cause nor licenses a post-hoc tube enlargement.

## Decision record

1. Preserve ID2Z30 as FAIL; do not weaken its gate or consume its blind rows
   as calibration for the frozen model.
2. Do not run the planned ID2Z31 feedback sentinel with this model.
3. Do not add network capacity. The next model identity, if pursued, must
   represent or fail closed around the observable event phase. Its action
   mask is part of the model/controller contract, not a reporting patch.
4. A bounded successor may use ID2Z30 only as development/design evidence to
   freeze an event guard and must obtain fresh calibration and fresh
   whole-family validation away from, and across, that guard before any TSC
   feedback sentinel.
5. Source-centred capture, Authority-L0, Recourse-L1 and final two-axis path
   control remain independent open gates. Moving-reference preflight success
   is not a substitute for them.

After the compact result, independent audit and all per-rollout compact JSON
files were copied and SHA-256 checked locally, the exact server-side
`rollouts/` raw tree (44,254,698,916 bytes) was deleted under the user's
authorized current-stage cleanup policy. The compact evidence, result, audit
and launcher log remain available; raw deletion is irreversible on the
server.
