# Fixed-1000 D2 history-conditioned candidate-value campaign

## Decision being tested

M0 and M1 closed the current one-step point-prediction ladder. D2 changes
the supervised object rather than increasing model capacity. It will create
matched finite-horizon outcomes for the same candidate set under different
complete causal histories, so a later model can learn candidate value and
risk/refusal directly.

## Frozen experiment

Every rollout begins from the qualified fixed-1000 source and lasts 48 plant
advances. At issue 8 it applies one already qualified D1 cumulative macro:
`even_plus` or `odd_plus`, including exact ramp, plateau, cumulative return
and q0 tail. At issue 24 it applies one of five prospectively fixed choices:
matched baseline, even plus/minus, or odd plus/minus. Candidate responses are
always differenced against the matched baseline with the identical
conditioner history.

The development matrix has 2 conditioner histories x 5 candidates = 10
fit-eligible primary trajectories. Two preregistered critical trajectories
are exact replay only and receive zero fit weight. Total budget is 12 resets
and 576 attempted plant advances with no retry. Calibration histories and
blind histories remain unopened.

## Gates and claim boundary

Offline gates bind the exact D1 Card15 construction and evidence, every
cumulative return, the complete action streams, hard current/slew/limiter/Ip
envelopes and the fixed data roles. Runtime fails closed before the next
issue. Scientific gates require both histories to retain h4/h8 signal,
signed separation, finite two-axis geometry, bounded Ip and bounded return
tail; a single hybrid frame cannot substitute for a sustained h4/h8 label.

PASS means only that this finite matched-history candidate-value development
dataset is usable for a direct value/risk model. It does not qualify a point
model, Authority, capture, hold, Recourse or a feedback controller. FAIL
stops this exact composed D1 grammar and requires action/history redesign;
arms, phases or gates may not be added after seeing the result.
