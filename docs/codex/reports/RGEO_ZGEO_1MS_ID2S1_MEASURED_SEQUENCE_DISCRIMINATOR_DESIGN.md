# ID-2S1 measured sequence discriminator design

## Question

ID-2S0 used a deliberately non-physical additive shift-three construction to
nominate four two-arm sequences. ID-2S1 asks the narrow empirical question:
do those exact sequences, when executed from the canonical 1100 ms source and
the admitted f03 causal prefix, produce a useful time-resolved two-dimensional
response set without violating the finite simulator envelope or the Ip gate?

This is a TSC-only development discriminator. It does not fit, calibrate, or
select a model. It does not qualify authority, a transition tube, recourse,
recovery, a controller, MPC, transport, crossing, adaptation, expert data, or
RL.

## Frozen campaign

Exactly four fresh rollouts are run, in this order:

1. `p04_plus__then__p07_minus`
2. `p07_minus__then__p07_minus`
3. `p07_minus__then__p07_plus`
4. `p07_plus__then__p04_plus`

Every rollout replays the exact f03 conditioner and p03 nominal prefix. The
first arm is held at issues 24--25 and returns to the admitted nominal target
at issue 26. The second arm is held at issues 27--28 and returns at issue 29.
The nominal target remains active through issue 33, and state 34 is retained.
Each stream is regenerated from the frozen ID-2P1 Card15 construction and
must match the corresponding hash-bound ID-2S0 action stream exactly.

There is one reset per branch, no retry or resume after any advance attempt,
and no cleanup action. The hard budget is four resets and 136 issue attempts,
TSC calls, and verified advances. A complete campaign retains 140 states and
700 required artifacts. The server output directory must be new and raw data
must remain uncompressed.

## Runtime gates

Before every issue, the current same-step paired-boundary `R_geo/Z_geo` and
same-step `Ip` are exact/noiseless observables. The complete controller-owned
post-1100 causal action/current history is available. The next successor is
not known before the issue.

The existing one-ms runner wrapper must enforce, before calling the legacy
runner, exact Card15 representability, absolute current bounds, adjacent
per-coil slew `<= 0.3 A`, paired-boundary validity, Ip, the inner issue
clearance at issues 24 and 27, and the outer finite envelope. It also checks
each observed successor and the empirical `2 mm / 2 mm / 100 A` step trip.
Those empirical trips and the observed margins are stop thresholds, not a
pre-action plant tube or a real-device safety theorem. Any failure stops
before the next issue and preserves partial raw evidence.

## Measured statistics and gates

The hash-bound fresh ID-2R1 f03 baseline is the matched nominal reference.
All four ID-2S1 branches must match that baseline exactly through state 24 and
through issued action 23. The measured paired response uses states 25--34.

For each sequence the result records:

- the complete ten-state `R_geo/Z_geo/Ip` response;
- peak R/Z norm and maximum absolute Ip response;
- the fixed ID-2S0 additive R/Z construction; and
- the actual-minus-additive interaction residual, reported descriptively.

Across all forty measured R/Z response samples, sixteen evenly spaced target
directions are evaluated by maximum projected progress. The scientific gate
requires at least `0.02 mm` progress in every direction, maximum angular gap
strictly below `180 deg` among samples of norm at least `0.02 mm`, and maximum
absolute paired Ip response at most `100 A`. No additivity-error threshold is
used: interaction is the object being measured and is not tuned or waived.

## Routes

- storage gate failure: no TSC;
- input, evidence, reproduction, or action-stream failure: no TSC;
- runtime/interface/envelope failure: stop immediately and preserve raw;
- raw-integrity failure: preserve raw and do not interpret science;
- matched-prefix failure: deep review;
- measured geometry or Ip failure: stop this sequence grammar for route
  review;
- complete execution, raw audit, prefix gate, and scientific gate PASS:
  authorize only a separately frozen fresh sequence replay/tube and residual
  reserve design.

Even a PASS is finite source-local, f03-history, HFS, 34 ms evidence. It does
not demonstrate arbitrary target tracking, long hold, different positions,
R_mid crossing, recovery, closed-loop control, or deployability.
