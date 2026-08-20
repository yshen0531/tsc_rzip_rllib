# ID-2Z19R1 zero-fit attribution design

## Purpose

ID-2Z19R1 completed its frozen two-candidate development comparison without
opening calibration or blind holdout data.  Neither candidate was eligible.
The post-ID-2Z18 route permits exactly one zero-fit attribution before the
model branch stops or requests targeted new evidence.

This attribution reads only the immutable ID-2Z19R1 result, independent
audit and 9,408-row out-of-fold prediction ledger.  It fits no model, changes
no gate, reads no calibration or holdout record, and runs no TSC or plant
step.

## Frozen questions

1. Did terminal one-step increment and terminal R/Z velocity fail in every
   whole-history fold for both candidates?
2. Is the failure explained solely by held-family support, or does it remain
   in folds whose frozen support gate passes?
3. Did the fixed TCN residual satisfy its preregistered relative-improvement
   and componentwise non-regression gates?
4. At which absolute endpoint issues do R terminal-increment errors above the
   frozen 0.5 mm cap recur?
5. How many informative paired-response rows reverse R/Z direction, and at
   which pair/origin/horizon cells do they occur?

The attribution must identify every row by candidate, fold, family, origin,
horizon and endpoint.  It may summarize repeated endpoint events but may not
assign an unobserved physical mechanism.

## Frozen decision

If both candidates fail terminal velocity and terminal increment in all
eight folds, at least seven folds per candidate pass support, no candidate is
eligible, and the TCN relative selection gate fails, classify the result as:

```text
ONE_MS_ID2Z19R1_ATTRIBUTION_COMMON_TERMINAL_INCREMENT_MODEL_CLASS_FAIL_AUTHORITY_AXIS_AND_TARGETED_REDESIGN_REQUIRED
```

That route closes calibration, blind holdout, a third model, larger network,
grid search and post-result gate changes.  The independently required
authority/recovery axis remains open.  Any later model identity must be
prospectively redesigned around the observed terminal/event error and new
control-relevant evidence; this attribution does not itself authorize new
data, a controller or TSC.

Any mismatch in source hashes, row count, independent audit, fold identity or
the frozen result instead routes to an integrity stop and yields no scientific
classification.

