# R_geo/Z_geo 1 ms ID-2D1R1 active-nominal duration/time result

Date: 2026-08-17 Asia/Shanghai

Implementation revision:
`3e5b28b32c31c66546ee0e08d63fcf1531b3c613`.

## Result

The server completed the frozen 24-rollout matrix with 24 resets, 768/768
advance attempts, 768/768 `gotsc` calls and 768/768 verified one-ms plant
advances. The raw tree contains 792 states and 3,960 required artifacts,
totalling 46,643,195,808 bytes. The inventory digest is
`bd726766870f08e98ae46342c3ad41763a465e2e6e0adef832b7e295af688b50`.

Primary route:
`ONE_MS_ID2D1R1_ACTIVE_NOMINAL_DURATION_TIME_DEVELOPMENT_PASS_STRUCTURED_MODEL_ONLY`.
Primary SHA-256 is
`f68d30865ed47503f32cf830da42e829b94bb6db6a3c4165d586a19ba726a7a8`.
Independent server-side raw reparse covered all 24 rollouts and 792 states,
reproduced the inventory and metrics, and passed with no failures. Its
SHA-256 is
`85e7d598332905a6a2de11a71816a2eb3d2d374cef62ac1b5ce685084ac0ae02`.

## Scientific evidence

The two held-nominal baselines are exactly repeatable in checked geometry,
Ip, 14 coil currents, 48 wire currents, issued actions and semantic
artifacts. The p04/p07 lag-16 block is rank 32/32 with condition 14.73875;
the separate p09 event lag-10 block is rank 10/10 with condition 1.

Every arm passed its response and Ip gates. Smooth-arm peak R/Z response
ranges from 51.783 to 749.761 micrometres and maximum absolute Ip response is
55.066 A. Event-arm peaks are 35.368 and 37.427 micrometres with maximum Ip
response 7.168 A. The maximum terminal/peak ratio is 0.3673.

The duration/time matrix also shows strong signed delayed structure. Several
p04-minus and p07-minus cells peak at state 27 around 0.63--0.75 mm, whereas
many corresponding plus cells peak near the issue edge at 0.05--0.16 mm.
This is authentic baseline-relative finite evidence, not a runtime or raw
error. It directly warns against a globally odd, instantaneous or single-
gain FIR model, but it does not by itself identify the nonlinear mechanism.

## Claim and next boundary

ID-2D1R1 is development-fit eligible only for a separately frozen structured
source-local model stage. That stage must preserve exact actuator/queue,
separate the active nominal, compare action-blind and stable low-order
p04/p07 candidates, keep p09 as an event channel, and evaluate on the
immutable ID-2C2 issue16/one-issue cells without future-current leakage.

This PASS is not calibration, blind context/history holdout, uncertainty
tube, recourse, controller/MPC, transport, crossing, expert or RL evidence.
The large delayed asymmetry must be represented or exposed as model failure;
it may not be hidden by fitting a larger recurrent network first.
