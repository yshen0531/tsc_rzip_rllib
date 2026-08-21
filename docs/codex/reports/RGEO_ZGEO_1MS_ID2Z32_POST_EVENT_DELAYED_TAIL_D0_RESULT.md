# ID2Z32 post-event delayed-tail D0 result

Date: 2026-08-21

## Reporting/design erratum

The initially saved scientific route is not a valid issue-56 plant-response
test. A subsequent zero-TSC action-stream forensic, added before any successor
model or campaign, proved that all four issue-56 branches were byte/number
identical to the matched baseline for all 73 issued actions. The builder put
the entire branch construction inside an `issue <= 55` condition, so a branch
starting at issue 56 executed no branch action. The zero response is therefore
tautological.

The corrected classification is
`ACTION_STREAM_CONSTRUCTION_DESIGN_FAIL_NO_SCIENTIFIC_ISSUE56_RESPONSE_TEST`.
The original result and independent audit are preserved as evidence of exact
execution of the wrong action streams; their saved signal-FAIL route must not
carry a plant, authority or q-cell conclusion. The earlier statement below
that the post-event q cell is scientifically closed is superseded. A new
identity may reconstruct the originally intended moving-center signed streams,
but it must prove nonzero branch/baseline action separation before TSC.

ID2Z32 completed all 10 prospectively frozen simulator rollouts and all
730/730 one-millisecond plant advances. The run retained 740 states and 3,700
required artifacts (43,580,763,760 bytes). Exact prefix, Card15, bridge,
current, raw and replay gates passed, and the independent raw audit reproduced
the primary route and every load-bearing scientific metric.

The final route is
`ONE_MS_ID2Z32_POST_EVENT_DELAYED_TAIL_D0_SIGNAL_FAIL_CLOSE_CELL`. This is a
clean scientific signal failure, not a runtime, deployment, interface, raw,
replay or reporting failure.

At issue 50 all four q_R/q_Z signed branches passed. Their h4 response norms
were 0.0539--0.0591 mm, h8 norms were 0.1682--0.2187 mm, persistence cosines
were 0.9879--0.9997, and the signed sets passed the frozen two-dimensional
geometry gates. At issue 56, however, all four matched branches had exactly
zero paired R/Z/Ip response at h4 and h8. Both issue-56 geometry checks
therefore failed with a 360-degree angular gap and zero weakest projection.
The issue-50 q_Z+ replay was exact.

None of the ID2Z32 rows may be fit: the data matrix did not execute its frozen
scientific comparison. This result neither validates nor invalidates the
post-event q coordinate.

The next bounded route is a zero-new-TSC nominal/action-allocation audit. It
must decide whether to construct a materially new unsaturated temporal
allocation/basis or revise the moving nominal/takeover. Any successor needs a
new prospective data identity and fresh calibration/whole-family blind
validation. Authority-L0 and Recourse-L1 remain separate prerequisites for
real feedback.

Evidence:

- implementation revision: `c6b1c5b9b4bf3e350c7567af2f84f070c33bf879`
- server output: `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z32_20260821_c6b1c5b9_v1`
- primary SHA-256: `b704bc754d537cd1c4d885541dd687b3bb359b1742f98a03b5c895398f5b0e7d`
- independent SHA-256: `e478e79f0d5424f2cdb867011d7eaebe909a5c280d4f7a369cf1666dd62b83a9`
- action-stream forensic SHA-256: `710f31b0887cc0cd834224318c6d77071d85177f09b8131db3f168bc4ea8b673`
- raw inventory digest: `e7601a252393b22146fb6fa5890889fa96130b80b3e73e3b3d695302136df51a`
- compact evidence: `docs/codex/audits/rgeo_zgeo_1ms_id2z32_20260821_c6b1c5b9_v1/`

After compact recovery and local/server SHA verification, only this run's
server `rollouts/` subtree was irreversibly removed. Server result/audit and
logs remain; available space after cleanup was 163,825,262,592 bytes.
