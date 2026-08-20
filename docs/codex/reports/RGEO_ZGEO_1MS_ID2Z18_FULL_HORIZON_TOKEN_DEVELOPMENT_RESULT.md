# ID-2Z18 full-horizon token development result

## Result

ID-2Z18 completed the one authorized development campaign on the TSC server.
The final route is:

```text
ONE_MS_ID2Z18_FULL_HORIZON_DEVELOPMENT_DATA_PASS_MODEL_COMPARISON_ONLY
```

All `16/16` rollouts completed, comprising `1040/1040` attempted, issued and
verified plant advances. The run retained `5280` required artifacts totaling
`62,190,927,744` bytes with inventory digest
`05dcc1f085c5696698c9deeeb7e91bf915284af18b24b648fd9537db574b3652`.
No model was fit and no calibration or blind-holdout record was executed or
read.

The run used physical implementation revision
`dc577537f83d4a45ad34e6413fd77f963271420c`, config SHA-256
`93d17647efda97cfc97813f30a85b8639ccac4cae9575be4206597999137a0a6`,
and server output
`/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2z18_20260820_dc577537_v1`.

## Development gates

The exact F/A/E increment matrix had rank three and condition
`2.086086163909763`. The maximum R/Z separation for each signed schedule pair
over the frozen development window was:

| Pair | Maximum separation (mm) |
|---|---:|
| d00 | 7.070342 |
| d01 | 7.235924 |
| d02 | 7.464488 |
| d03 | 6.948733 |
| d04 | 6.684262 |
| d05 | 2.714654 |

All six exceed the frozen `0.05 mm` gate. The two zero-weight critical
replays (`baseline_half_f` and `d00_plus`) matched their source histories over
all checked observables and semantic artifacts. There were 14 unique
positive-weight histories and two replay histories with zero fit weight.

## Independent audit and reporting repair

The primary result SHA-256 is
`5fbba54efc3ae3a921d77fc32adb31a7af59775dc677b09bfbc209807e4d4d8c`.
The first independent audit, SHA-256
`60e4f8a93f5d428f799a65949620881fbbcdf2292806dccbfd991c98848a0bb1`,
is preserved as FAIL. Its only load-bearing mismatch came from comparing the
retained raw state-directory `inputa` after it had been rewritten with the
outgoing issue against the preissue compact/reference hash. The raw auditor
already reconstructed and checked every outgoing Card15 field against the
frozen action stream, so this was an audit-time representation mismatch, not
a plant, action, prefix, raw or scientific failure.

Revision `08e15ac02322ac4dc43caa38350a9fb52f24d6fb` changed only that audit
comparison to use the immutable preissue compact row, matching the qualified
prefix-audit semantics. It did not rerun TSC or change any trajectory,
threshold, model or result. The corrected independent audit, SHA-256
`6d7603de3e5d805082a61f1dde2a2148117105b130578f2dc98e9187a0d077b5`,
passed with zero failures and reproduced all counters, prefix checks,
scientific metrics, artifact counts/bytes/digest and final route.

## Cleanup and authorization boundary

After independent full-raw audit and exact local/remote recovery of all 20
compact JSON records and validation logs, only this run's exact `rollouts/`
subtree was removed. The operation freed `63,153,736,435` filesystem bytes;
remote free space afterward was `118,086,983,680` bytes. The deletion is not
recoverable from the server, while compact histories, inventory identities,
both audits and logs remain retained.

This PASS authorizes only a separately frozen comparison of exactly two
development models. It is not calibration, blind holdout, a calibrated tube,
authority, capture, recovery, controller, MPC, waypoint/path, R_mid crossing
or deployment evidence. The future `c00--c03` calibration and `v00--v03`
blind schedules remain unexecuted and unopened.
