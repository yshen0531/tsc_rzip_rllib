# R_geo/Z_geo 1 ms ID-2Z10 five-context model result

Date: 2026-08-19 Asia/Shanghai

ID-2Z10 is final as
`ONE_MS_ID2Z10_FIVE_CONTEXT_MODEL_FAIL_ACTION_BASIS_CONTROL_REVIEW`.
Implementation revision `31b90c237e0801ff4ff083343a2b8b15db19ce6b`
passed server focused 6/6 and all one-ms 472/472 tests. A transfer-mode execute
bit omission caused one pre-fit `Permission denied`; after verifying that no
output existed, the server execute bit was restored and the unchanged identity
ran once. The comparison used zero TSC/plant/controller/optimizer operations,
read zero calibration/holdout records and emitted no model artifact.

The stable model achieved mean/max response NRMSE `0.229901/0.323605`, minimum
peak cosine `0.991803`, maximum Z p95 `0.261297 mm` and maximum Ip p95
`29.5101 A`. It failed R p95 (`0.726041 mm`) and best-arm regret (`0.194231`).

The stable-plus-GRU4 candidate achieved mean/max response NRMSE
`0.233554/0.395545`, minimum peak cosine `0.985044`, maximum Z p95
`0.197005 mm` and maximum Ip p95 `21.2987 A`. It was worse on maximum R p95
(`0.873908 mm`) and retained the same maximum regret (`0.194231`).

Both candidates predicted `b4` in all five held contexts. Measured best arms
were `f4`, `b2f2`, `f2b2`, `b2f2`, `f2b2` at states 49/53/57/61/65. The two
new late contexts had modest regrets (`0.02790`, `0.03034`), but the inherited
state-49 failure remained decisive and every fold exceeded the frozen 0.3-mm
R p95 gate. The GRU residual did not improve action ranking.

The deterministic replay audit reproduced the complete result exactly with no
failures. Primary / audit SHA-256:

```text
eb725e6feeb3d46a04aebdd2e2bbb97ab15217db314644f466403f634b23e618
dac2cf62251a4f6d64d5fa1f5b92c6d950c8b10b7266fd9b9164a613a4b13c48
```

This FAIL closes the present low-capacity B/F/H response-model form under its
frozen gates. It does not prove that machine learning, recurrent models, the
plant, or two-axis control are impossible. It does show that simply adding two
nearby contexts and refitting the same action-memory/GRU classes does not solve
the ranking or absolute-R error problem. Per the preregistered stop rule, a
larger network, calibration, blind holdout and controller use are not
authorized. The project must pause for an action-basis/control-utility and
model-target review before another development campaign.
