# ID-1A context/anchor pilot result

Date: 2026-08-14 (Asia/Shanghai)

## Evidence identity

- implementation revision: `8dcd072076fe505e7c9e7432210fec858985926b`
- frozen config SHA-256: `883945f8a15ba1d9aabe037fde6e51ba420cb7a59ba792df1064611b3ba196bf`
- primary compact SHA-256: `7f0f972d6e76a97a5480d047ceb12b6218d3b642bb157792cfda55227cd508fb`
- independent compact SHA-256: `d2bba86a3c9ad181793f0003e947f84009d4d868e1e37e4cc02747ae163e6b48`
- remote raw directory: `rgeo_zgeo_1ms_id1a_runs_20260814_8dcd0720`
- raw inventory: 4,000 required files, 47,114,339,200 bytes, digest
  `4cbd6e4e437ff1e3e5422646fef316f5d67d196b2faa224c472b6dca5405e6f5`

The tracked primary and independent compact results are under
`docs/codex/audits/rgeo_zgeo_1ms_id1a_result_20260814_8dcd0720/`.
Their repository-normalized byte hashes are respectively
`5c31b06ded7e08588a2ac897ed55008e4fcdcdde0f3cfb3c13d18a19fd44a2cf`
and `c2f511b7ff09e67c8fb387eeade40890a5afc419acd3aeed8d22ab4f90c823dd`;
the two hashes above identify the byte-exact downloaded server compacts.

## Execution and scientific classification

All 32 canonical resets, 768 issue attempts, 768 `gotsc` calls, 768 verified
plant advances and 800 states completed. Exact Card15/action timing, boundary,
Ip, coil/wire current, limiter, slew, raw inventory and the preregistered
repeatability comparisons passed. The independent server-side raw reparse has
`audit_passed=true` and reproduced the primary metrics and route.

The final route is
`ONE_MS_ID1A_HISTORY_CONTRAST_FAIL_REDESIGN`. This is a clean finite
identification-design FAIL, not a runtime, package, actuator, raw, TSC, model,
controller or reachability failure. The frozen field
`development_data_eligible` is false. No ID-1A trajectory may be used for
model fitting, calibration, holdout, expert data or controller qualification.

Signal, Ip and all six per-context numerical rank/best-pair-condition gates
passed. The two failed prospective contrasts were:

- `history_p04_minus`: maximum matched-q0 response difference
  `0.000927286 mm`, below the `0.002 mm` gate;
- `anchor_p07_plus`: pre-probe R/Z separation `0.092390247 mm`, below the
  `0.1 mm` gate, although its maximum response difference was
  `0.221526505 mm`.

The sibling `history_p04_plus` and `anchor_p03_minus` contrasts passed. This
does not permit weakening the frozen all-context route after seeing the data.

## Post-result zero-TSC causal audit

The ID-1A response-vector statistic averaged states at effect ages 1--4 after
a one-issue probe at issue 10. The schedule returned to q0 at issue 11.
Because the actuator effect is `issue+1`, only state 11 is the probe's pure
first effect; state 12 already contains the q0-return effect. Consequently the
four-state mean is a valid sequence-response descriptor, but it is not a
clean local action vector or a one-action controllability column.

A read-only recomputation of the tracked compact trajectories found:

- pure effect age 1: four p03/p07 signed rays at late q0 have maximum angular
  gap about `151.6 deg`, hence positively span R/Z;
- mixed age 1--4 mean: maximum angular gap about `310.6 deg`, hence lies in
  one half-plane;
- ages 3--13 after the return edge again have maximum angular gaps below
  `128 deg` in the checked states.

This establishes a temporal-primitive/metric design flaw, not a plant
unidirectionality theorem. Rank two alone was also too weak: several ID-1A
context matrices were rank two while their measured rays did not positively
span the plane.

## Route

Do not fit ID-1A and do not rerun it. The next prospective stage must isolate
one action regime over its measurement window. ID-1B therefore uses a
four-issue persistent dwell before the q0 return, measures the same active
target through effect ages 1--4, and gates positive spanning and directional
support explicitly. ID-1B is still simulator identification; PASS can select
a temporal/action basis only. Fresh history/anchor development data, then
fresh grouped calibration and holdout, remain required before any controller.
