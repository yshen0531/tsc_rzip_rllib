# R_geo/Z_geo 1 ms ID-2Z9 late-root branch utility/support result

Date: 2026-08-19 Asia/Shanghai

## Result

ID-2Z9 is final as
`ONE_MS_ID2Z9_LATE_ROOT_BRANCH_UTILITY_SUPPORT_PASS_FIVE_CONTEXT_MODEL_ONLY`.
The physical implementation revision was
`63f68c2bef9adf91595ab5021b716c0fd088b813`; the reporting-only independent
auditor repair was `01164ef1d4170cbdc7b56595448d5d0dc0c156e1`.

The server completed all 11 frozen canonical-source rollouts: ten fresh
fit-weight sibling windows and one zero-fit critical replay. Counters are
exactly 11 resets, 847 advance attempts, 847 `gotsc` calls, 847 verified
successors and 858 retained states. The required raw inventory is 4,290 files,
50,530,128,792 bytes, digest
`308a222e8b4f6f4d40babeadc685ce7b9693f1abd8277ec90dc7c7a8c417d5fe`.

Both fresh decision rounds passed their prospectively frozen utility gate:

- state 61 selected `b2f2`; terminal worst normalized score improved from
  matched `hold4` `3.737459254` to `3.156328518`;
- state 65 selected `f2b2`; the final score was `2.983667001`;
- the complete selected sequence is
  `f4 -> b2f2 -> f2b2 -> b2f2 -> f2b2`;
- final improvement relative to the state-61 matched hold is
  `0.753792253`, above the frozen `0.05` gate;
- the exact selected-path replay passed.

The result is not capture. Across terminal states 72--77 the selected path's
maximum source-relative R/Z distance is `26.767972 mm`, maximum R/Z step speed
is `0.298366700 m/s`, and maximum source-relative Ip fraction is
`0.036971927`. Thus the 25-mm/0.1-m/s capture gate fails even though the Ip
gate passes.

## Independent audit repair

The first independent audit is preserved as FAIL. It inherited ID-2Z6's
hard-coded state ceiling of 1169 ms and expected the ID-2Z9 result schema on
per-rollout compacts that are intentionally emitted by the reused ID-2Z7
executor. It therefore rejected every valid 1170--1177 state directory and
every compact identity. This was an auditor/reporting defect after all plant
work, not a raw, action, prefix, runtime or scientific failure.

The separately committed reporting-only repair changed only those two audit
assumptions. Server focused tests passed 10/10 and all one-ms tests passed
466/466. It then reparsed the same immutable raw with zero new TSC and
reproduced 11 rollouts, 858 states, all counters, all frozen metrics, the full
inventory and the final route with no failures. Primary / repaired-audit
SHA-256 values are:

```text
c0137121efd593af6b00dd690fd0b4bec6b6f094720c40f28e99b59d2ac59d6d
13430405c3b1cedd092fe3408e1908b53707fc734052d1cbfdf104fa31298d97
```

## Scientific boundary and next step

This is finite source-local teacher utility and prospective development-data
evidence. It proves neither capture, hold, recovery, Recourse-L1, waypoint
tracking, controller safety nor R_mid crossing. The ten new siblings may be
combined with the fifteen previously frozen complete development windows only
under whole-decision-context grouping. The critical replay has zero fitting
weight.

The only authorized successor is one final five-context comparison of the
same two ID-2Z8 model classes and unchanged capacity: the strongly regularized
stable sequence-response model and the same backbone plus GRU4 residual. A
larger network, calibration, blind holdout and controller execution remain
blocked. If neither candidate passes all five held-context folds, this model
form/support route stops; it must not become another capacity ladder.
