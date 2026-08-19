# R_geo/Z_geo 1 ms ID-2Z7 branch-continuation result

Date: 2026-08-19  
Implementation revision: `cb5c7a40c112208d13e3f2b42ded820d445b1c90`  
Remote run: `rgeo_zgeo_1ms_id2z7_runs/20260819_cb5c7a40_v1`

## Result

The final route is
`ONE_MS_ID2Z7_BRANCH_CONTINUATION_PASS_REPLAY_RECOURSE_AND_SMALL_MODEL_DESIGN_ONLY`.
This is a clean finite teacher-utility and prospective development-data PASS.
It is not a capture, hold, recovery, controller, waypoint, crossing or plant
reachability PASS.

The run completed exactly 11 fresh resets and 759/759 attempted, `gotsc` and
verified one-ms advances. All eleven paths completed to state 69; there were
zero empirical safe stops. The retained raw inventory before cleanup was
3,850 files, 45,347,551,480 logical bytes, with digest
`acafcc901839bb52d68d42b8fd47dc8de37a9099029a5400915951fe6990d539`.
The structurally separate audit reparsed 770 raw states and all 3,850 files,
recomputed all prefix, round, scientific and route fields, and passed with no
failures.

## Frozen decisions

The inherited audited state-49 round selected `f4`. The fresh state-53 round
selected `b2f2`; the fresh state-57 round selected `f2b2`. The resulting
three-macro sequence is:

```text
f4 -> b2f2 -> f2b2
```

The exact zero-fit replay matched the selected trajectory. The complete
fit-weight count is 15: five external audited ID-2Z6 round-0 windows plus ten
fresh ID-2Z7 sibling windows. Interrupted ID-2Z6 round-1 paths, ID-2Z5 paths
and the replay have zero fitting and selection weight.

Round 1 improved the normalized terminal score from the matched hold value
`3.676826525` to `3.594410535`. Round 2 improved its matched hold value
`3.594410535` to `3.274747499`. Relative to the original state-49 hold score
`4.407677637`, the selected path improved by `1.132930138`, so the frozen
teacher-utility gate passed.

## Important negative result

The selected path did not capture. Across terminal states 64--69 its source
distance increased from `25.07765` to `26.38866 mm`, while its one-ms R/Z
speed increased from `0.28059` to `0.32747 m/s`. Its source-relative Ip
fraction remained within the five-percent gate. Thus the finite branch
teacher found a materially better sequence than the matched holds, but not a
terminal set or a Recourse-L1 candidate.

The fifteen windows contain only three independent decision contexts
(states 49, 53 and 57), each with five sibling actions. They are sufficient
to run one prospectively bounded low-capacity development comparison, but not
to claim broad history generalization or to justify a high-capacity recurrent
world model. Any fitted successor must use whole-context folds, report
support/OOD, and require fresh calibration and blind whole-history holdout.

## Validation and retention

Before TSC, the installed server passed shell and Python syntax checks, the
focused ID-2Z7 suite 9/9, all one-ms tests 448/448, the 25/25 two-round action
matrix, source/evidence hashes, run-root isolation and the zero-TSC storage
gate. The run root was exactly `<output>/rollouts`; no historical raw root was
used.

After compact retrieval and hash verification, only the exact audited raw
`rollouts/` subtree was irreversibly removed, reclaiming 46,050,216,111
filesystem bytes. Top-level compact JSON, result, independent audit, offline
preflight and logs remain. Server free space after cleanup was
136,051,212,288 bytes.

## Authorization boundary

This PASS authorizes design and server evaluation of one bounded two-candidate
small-model comparison over the frozen development windows, plus a separate
fresh replay/Recourse-L1 design review. It does not authorize controller
execution, expert/BC/DAgger/RL use, online neural adaptation, calibration or
holdout reuse, or a claim that the B/F/H grammar can capture.
