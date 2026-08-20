# ID-2Z30 fresh q-model qualification design

ID-2Z30 is the one prospective fresh qualification campaign authorized by
ID-2Z29. It does not refit or select a model. It freezes the ID-2Z28 FIR
payload, first calibrates a finite error envelope at issue 36, and opens the
issue-44 whole-family blind records only if calibration and exact replay pass.
No feedback sentinel is part of this identity.

The ten-rollout maximum, in mandatory order, is:

1. one fresh matched transition-center baseline;
2. four issue-36 q_R/q_Z signed calibration branches;
3. one exact replay of issue-36 q_Z plus;
4. four issue-44 q_R/q_Z signed blind branches.

All paths replay the exact full-F prefix through issue 31, use the qualified
`0.50F` transition center, hold one signed q increment for eight issues,
return through the exact eight-slot Card15 bridge, and retain the common tail
through state 73. Calibration and blind families are whole-trajectory
separate. The replay has zero statistical weight. No ID2Z27 row is reused as
fresh qualification evidence.

The fixed model predicts each signed branch as plus or minus the stored
phase-32 odd response. Calibration must pass the unchanged ID2Z28 aggregate
gates. Its per-horizon/output error envelope is then frozen as
`1.5 * max_abs_calibration_error + floor`, where floors are `0.02 mm R`,
`0.02 mm Z`, and `5 A Ip`. Blind qualification requires all `96/96` branch /
horizon/output residuals inside that envelope and independently passes the
same aggregate response, direction, terminal-velocity and ranking gates.
Zero-response cosine is a failure, not an automatic pass.

Before every issue and after every successor, the existing exact Card15,
`<=0.3 A` slew, absolute current, paired-boundary, Ip, finite-value,
45 mm/9% simulator-development shell, 50 mm/10% outer envelope and empirical
2 mm/2 mm/150 A post-successor guards remain unchanged. These empirical
guards are not controller-grade pre-action bounds. Any execution, prefix,
raw or replay failure is inconclusive and stops before blind opening where
possible.

A PASS freezes the model payload and calibrated finite envelope for a
separately identified, zero-fit four-cardinal moving-reference feedback
sentinel plus one replay. It does not authorize arbitrary actions, source
capture, Authority-L0, Recourse-L1 or controller qualification. A calibration
FAIL leaves blind unopened. A blind FAIL closes this q-model route; no new
kernel, network, gate or adjacent phase may be added under this identity.

The hard maximum is ten resets, 730 advance attempts/calls/verified advances,
740 retained states and 3,700 required artifacts. There is no retry after any
plant attempt. Raw can be removed only after complete independent server-side
reparse and local/remote compact hash recovery.
