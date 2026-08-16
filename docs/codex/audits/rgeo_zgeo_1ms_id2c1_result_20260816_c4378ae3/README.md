# ID-2C1 tracked compact evidence

This directory records the compact, reviewable identity of the authentic
ID-2C1 server campaign. The 21.38 GB raw tree remains immutable on the server
at the path in `compact_evidence.json`; it was not downloaded or repurposed as
a fixture.

The primary result completed 11/11 rollouts and 352/352 verified one-ms TSC
advances. A post-run independent auditor initially sorted compact filenames
alphabetically and therefore compared the wrong campaign rows. Commit
`e2b2a1d3178d31ff105ec0cd1473d36846d0d457` corrected only that audit ordering;
`independent_audit_v2.json` then reparsed the unchanged raw tree and reproduced
all counters, inventory, phase-A metrics, phase-B metrics and selection.

The result is a finite empirical-development PASS. It is not repeatability,
model, calibration, holdout, tube, recourse, controller, MPC or reachability
qualification. Its only route authority is prospective ID-2C2 fresh-validation
design.
