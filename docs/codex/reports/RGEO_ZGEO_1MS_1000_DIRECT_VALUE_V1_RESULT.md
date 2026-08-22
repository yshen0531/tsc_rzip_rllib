# Fixed-1000 V1 direct candidate-value model result

## Verdict

V1 ran on the server with zero TSC/reset/plant advance.  Its independent
artifact/metric audit passed.  The frozen development verdict is FAIL:

`ONE_MS_NR1000V1_DIRECT_CANDIDATE_VALUE_MODEL_INSUFFICIENT_CLOSE_LIBRARY`.

The failure is narrow but binding.  In leave-`odd_plus`-history-out
evaluation, the h8 no-action Z tail was `-0.095621 mm`; the predicted center
was `0.0 mm` with halfwidth `0.0846775 mm`, an excess of `0.0109435 mm`.
Thus 23/24 no-action components were contained.  The all-component gate was
prospectively frozen and is not widened after seeing this result.

## What passed

- all candidate absolute endpoints: 120/120 components contained across the
  four whole-history folds;
- maximum directional ranking regret: `0.012218 mm`;
- h8 weakest-best progress in every history: `0.279--0.335 mm`;
- final combined R/Z halfwidth: `0.178577 mm` (< `0.20 mm`);
- final combined Ip halfwidth: `38.2562 A` (< `50 A`);
- maximum observed candidate Ip response: `154.5364 A`;
- maximum development nearest-support distance: `0.499136` (< `0.55`);
- support, width, ranking, progress and Ip gates all passed.

These numbers show that D3's discrete candidate response/ranking structure is
strong and stable.  They do not permit changing V1's binary verdict or
opening fresh calibration under this identity.

## Required route review

The frozen V1 contract explicitly closes this candidate-library model route
on any development gate failure and forbids a third model or nearby-history
repair.  Authority, Recourse and feedback therefore remain closed.  The
project must pause for a high-level choice rather than silently add `0.011 mm`
to a floor.

The most defensible successor, if authorized under a new identity, is not a
larger network.  It is to separate the slowly varying no-action continuation
from candidate ranking: retain V1's measured candidate response/value result,
but make no-action continuation a calibrated set-valued safety object with
fresh prospective histories and refusal, then test Authority and Recourse in
parallel.  That is a route change and requires explicit approval.

