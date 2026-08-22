# Fixed-1000 hybrid radial Authority G1 result

## Result

G1 stopped fail-closed during the first novel rollout. The frozen primary
route is:

```text
ONE_MS_NR1000G1_EXECUTION_OR_HARD_SAFETY_FAIL_STOP
```

This is an action-allocation and observed-readback-margin design failure. It
is not a scientific result for the early-minus/late-plus hypothesis, a plant
control failure, an Authority failure, or evidence of global unreachability.

The fresh matched-q0 branch completed all 64 advances. The next rollout,
`m04_cross_p32`, completed six verified issue-to-effect transitions. Its
issue-5 target was an exact Card15 command and the issued target change was
exactly `0.3 A`. The independently reparsed state1006 current changed by
`0.30001 A` on TSC-order coils 10 and 11. The hard `<=0.3 A` readback contract
therefore stopped execution before issue6. There is no state1007, later
candidate, replay, scientific terminal metric, or control verdict.

## Immutable counters

```text
reset calls                         2
advance attempts                   70
gotsc calls                        70
verified plant advances            70
matched-q0 raw states              65
partial candidate raw states        7
partial candidate issued actions    6
forbidden state1007 present     false
```

The observed-current sequence checked after the source-bias transition was:

```text
issue1 -> state2     0.20001 A
issue2 -> state3     0.14583333333333333333333333 A
issue3 -> state4     0.20000 A
issue4 -> state5     0.30000 A
issue5 -> state6     0.30001 A  STOP
```

The reporting-only independent route is:

```text
ONE_MS_NR1000G1_PARTIAL_RAW_FORENSIC_PASS_ACTION_ALLOCATION_MARGIN_REDESIGN
```

It authenticated the partial stop only and did not alter the primary FAIL.

## Evidence identity

```text
G1 implementation/source revision
3057b6ad55b83b38d99cd9c387d358c06e2783c6

partial forensic implementation revision
c36e28a9

result.json
cf98e1236d30a70950586c9a2be793a342016ebb9bbeb0ed0ccbddc7fb9bffcd

matched_q0.json
1770ae4a4682ee0090bf7cf491864ff65615f162da2d3152e445eda5a21320ab

m04_cross_p32.json
c9ce3833ee5b506826369159c4cc1647bb03300043daa63227c3edb8216ae2df

offline_preflight.json
15fcf2eee19c595393b6d2dbc34bda63979fcb2b8970e64648b885a10ed87b56

failure_forensic.json
0fd01c0bc03da31a51989bad77a805a4a38b1246e4c27ea9f1718f4adbb97bc2
```

The server deployment matched the two forensic source hashes, `py_compile`
passed, and the focused G0/G1/forensic regression passed `9/9`. The forensic
performed zero TSC and zero plant advances.

## Route decision

G1 may not resume, retry, or be changed in place. Its scalar cross-zero
matrix is not followed by a neighboring depth, phase, or rate ladder. The
next identity must change the action semantics:

1. reserve explicit margin between exact Card15 target slew and the hard
   observed-current `0.3 A` limit;
2. construct one joint 14-dimensional allocation over independently measured
   radial/even and vertical/odd coordinates, with no silent clipping;
3. choose from the allocation using current exact R/Z/Ip and causal history,
   rather than replaying another fixed scalar schedule;
4. validate every cumulative target, transition, current limit and return or
   continuation offline before a new TSC call;
5. retain matched no-action and absolute distance/velocity/Ip utility gates.

No G1 partial row is promoted to a model, calibration, holdout, Authority,
Recourse, controller or expert-data claim. The final goal remains safe causal
two-axis instruction/path tracking from fixed 1000 ms, followed by hold,
recovery and repeated bidirectional R_mid crossing with continuous belief.
