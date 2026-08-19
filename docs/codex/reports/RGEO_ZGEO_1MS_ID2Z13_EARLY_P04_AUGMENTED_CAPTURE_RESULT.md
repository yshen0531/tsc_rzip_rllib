# R_geo/Z_geo 1 ms ID-2Z13 early p04-augmented capture result

Date: 2026-08-20 (Asia/Shanghai)

## Final classification

ID-2Z13 is final as
`ONE_MS_ID2Z13_EARLY_P04_AUGMENTED_GRAMMAR_NO_CAPTURE_NEW_BASIS_REQUIRED`.
This is a clean finite action-grammar/scientific FAIL. It is not a runtime,
TSC, prefix, Card15, raw-integrity, replay, reporting, global-reachability,
controller or plant-unreachability failure.

The implementation identity is
`030d40333b07bc54adb7bf7bab37cf2d8d2bb4c3`; the subsequent test-only fix did
not change the physical implementation. The frozen config SHA-256 is
`2bcc3652b4b6980a5804cf97263f1148e1dae60e139916ce767207e79b95bd4b`.

## Execution and evidence

- server focused tests: `10/10` PASS;
- all server one-ms tests: `502/502` PASS;
- zero-TSC offline root/main matrix: `81/81` PASS;
- authentic rollouts: `19/19` complete, with zero guarded stops;
- resets / verified advances / states: `19 / 1463 / 1482`;
- required artifacts: `7410`, `87279313368` bytes;
- raw inventory digest:
  `3b4b83b6200108cd7ade951f877a89b8407e49aea83bf43552f9d4c92669a0ec`;
- fresh selected-path replay: exact PASS;
- independent raw reparse: PASS with no failures and the same final route.

The primary result SHA-256 is
`b5ec36dbc1fb4f947f87efb5d7d0681245fa7ada87e518052f0ad0cfcaa093e1`.
The independent raw audit SHA-256 is
`217d81c8f0c43b418292d7de0ac1bd44c8c73e7c8ee175415d2ca5db535fe2ed`.
All 25 downloaded compact/log files matched their server SHA-256 values.

## Scientific result

At the state-49 root the frozen nine-arm teacher selected `b8`. Its terminal
worst normalized score was `3.9541117424`, versus `4.1755298024` for hold;
terminal maxima were `30.806178 mm`, `0.395411 m/s` and `2.28615%` source-Ip
departure. After committing the first four `B` tokens, the state-53 teacher
selected `b4f4`. Its score was `3.3163391059`, versus `4.2403269551` for the
matched hold, and its terminal maxima were:

```text
source R/Z distance       29.665859 mm
R/Z one-step speed         0.331634 m/s
absolute source-Ip offset  2.74480 %
```

All six terminal states had to meet `25 mm`, `0.1 m/s` and `5%`; therefore
capture failed. No p04 arm was selected. At the root, p04-minus and
p04-plus/hold scored `4.545426` and `4.210108`, both worse than hold. At the
main decision, p04-minus/hold scored `4.288007`, while p04-plus/hold improved
only to `4.026834`, still far outside capture and far behind the selected
B/F arms. Thus the independently ranked third actuator direction did not
repair the finite early B/F grammar at these exact state-49/state-53
histories.

The selected path equals the previously observed `b8 -> b4f4` path and the
fresh replay was exact. ID-2Z13 therefore closes this exact p04-augmented
nine-arm, two-round source-local grammar. It does not reject p04 globally,
all earlier schedules, every Card15 direction, longer feedback, arbitrary
sequence search, or global two-axis reachability.

## Route decision

Do not add p04 depth, a neighbouring root, a third round, a denser B/F grid,
a larger predictor or a relaxed capture gate. The next work is a bounded
zero-new-TSC remaining-action-basis and earlier nominal/reachability review.
It must decide, before any further plant campaign, whether an already measured
non-smooth p09/p01-class direction has enough prospective value to justify
one final finite campaign, or whether this source-local action grammar must be
closed in favour of a materially different nominal/authority construction.

No model, calibration, holdout, controller, Recourse-L1, waypoint/path or
R_mid-crossing result was produced.

## Retention

After the independent audit and all server/local compact hashes matched, only
the exact remote `rollouts/` subtree for this stage was removed. The deletion
freed the raw tree irreversibly; the server compact/logs, local compact copies,
full inventory digest and independent audit remain. Server free space after
cleanup was `118112768000` bytes.
