# ID2Z25 centered co-allocation D0 result

## Final outcome

The final route is:

`ONE_MS_ID2Z25_CENTERED_D0_SIGNAL_FAIL_CLOSE_CELL`

All 15 authentic rollouts and `975/975` advances completed. The independent
audit reparsed 990 states and reproduced all 4,950 artifacts
(`58,303,994,760` bytes, inventory digest
`8634cd56c5eedf2f46458d1ef8972701cb12e974698c574fcfb1491728d163a1`),
all causal prefixes, exact Card15 actions, the replay and the final metrics.

The first primary report incorrectly used the execution-failure route after
all plant work because the config omitted the inventory-only
`diagnostic_artifacts` key. The original report and both failed reporting
audits remain preserved. A zero-plant reporting hotfix bound the original
result SHA, added only the already-retained `sprsina` inventory name and
run-root identity, and produced the final independently audited result. No
action, threshold, raw file, reset or TSC step changed.

## Scientific failure

Ten of twelve signed branch rows passed all h4/h8 signal, persistence and Ip
gates. Two p00 order/phase rows failed only persistence direction:

- issue24 `p00_minus/minus_then_plus`: h4 `0.132606 mm`, h8 `0.291458 mm`,
  cosine `-0.957004`;
- issue32 `p00_minus/plus_then_minus`: h4 `0.142195 mm`, h8 `0.380439 mm`,
  cosine `-0.972464`.

Both change sign between h4 and h8. Ip responses are only `34.29 A` and
`33.89 A`, so this is not an Ip gate artifact. All p05/p06 branches and the
other p00 order at each phase passed; the exact replay passed.

The pooled six-direction geometry was positive-span at h4 and h8 in both
phases, with maximum angular gaps `93.69--105.50 deg` and weakest projections
`0.058--0.186 mm`. This remains diagnostic and cannot override a preregistered
per-branch persistence failure.

## Control interpretation

The centered nominal itself is weak for the eventual task. Its terminal
six-state diagnostic is `36.487 mm / 0.548 m/s`, versus the same-campaign
full-F diagnostic `28.255 mm / 0.416 m/s`; neither captures. The residual
responses are measurable but sub-millimetre, and one axis has phase/order
hybrid reversals. Input rank and pooled positive span therefore do not make
this cell a usable Authority-L0 or recovery grammar.

Per the frozen stop rule, the entire exact `0.50F`, two-phase, three-axis,
8+8 centered cell is closed. The project will not salvage only the ten
passing rows for a model, drop p00 after seeing the result, or run adjacent
share/phase/duration variants. All ID2Z25 trajectories remain zero-fit design
evidence; no model, calibration, holdout, Authority-L0 or controller is
authorized by this result.

## Next route boundary

The next step must be a bounded zero-TSC route-level redesign of nominal
transport, slew allocation and terminal/velocity objective. It must decide
between a materially different state-dependent time-sharing/bang allocation
and a new Card15 action/takeover basis; it may not be another centered-cell
micro-ladder. Any later learning stage must use a newly prospective data
identity and remain parallel to, not a substitute for, Authority-L0 and
Recourse-L1.
