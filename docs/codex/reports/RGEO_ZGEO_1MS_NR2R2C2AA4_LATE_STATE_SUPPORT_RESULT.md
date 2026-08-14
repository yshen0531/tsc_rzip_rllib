# R_geo/Z_geo 1 ms NR2R2C2aA4 late-state support audit result

Date: 2026-08-14 Asia/Shanghai

Final route:

```text
ONE_MS_NR2R2C2AA4_LATE_STATE_CAUSAL_SUPPORT_FAIL_NO_TSC
```

## Scope and identity

This was a repository-local, zero-TSC causal-support audit at source revision
`49faa8b93907b8828f9c168a623733a4393a2be6`. It authenticated the frozen A4
config/design, the tracked q0/A2/A3 compact records and the A3 independent
audit. It read six compact trajectory records and read no holdout or raw
record. It accessed no server, advanced no TSC plant, ran no controller or
optimizer, and fit or trained no model.

The machine result is retained at
`docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa4_support_20260814_49faa8b9/result.json`.
The audit implementation and its six focused tests are committed separately
at `49faa8b9`.

## Exact observation contract

The user clarified and this result freezes the following decision semantics:

- before issuing action `u[k]` at every 1 ms decision boundary, the controller
  receives the current true, noiseless `R_geo[k]`, `Z_geo[k]` and `Ip[k]`;
- `R_geo/Z_geo` still come from one valid paired boundary at that same state,
  and a missing or invalid boundary rejects the action fail closed;
- the complete causal observation and controller-owned action/readback/queue
  history from the 1100 ms takeover through step `k` is available, although a
  model may use a finite window or a compressed state; and
- `state[k+1]` is not observable before issuing `u[k]`.

Consequently, current or past `R_geo/Z_geo/Ip` are not hidden variables and
must not be reconstructed by a measurement observer. Belief and uncertainty
remain necessary only for unobserved internal memory, model mismatch and the
future response after an action. This audit makes no claim that a pre-1100 ms
history is exposed by the present controller interface.

## Result

Input integrity passed, but only 16 of the 32 required A4 transitions had
direct same-prefix support:

| transition family | result |
|---|---:|
| issue 0 -> state 1, q0 | supported |
| issue 1 -> state 2, p03 level1 | supported |
| issue 2..15 -> states 3..16, p03 level2 effect-age 1..14 | supported |
| issue 16..31 -> states 17..32, p03 level2 effect-age 15..30 | unsupported |

The first unsupported transition is therefore exactly
`issue 16 -> state 17`, level2 effect-age 15. At issue 16, `state16` and its
entire causal history are known exactly. What is absent is a previously
measured successor under the same complete prefix and Card15 target, or a
prospectively qualified state/history tube with a one-step bound.

The state16 margins are large but only descriptive:

| remaining margin | R | Z | Ip |
|---|---:|---:|---:|
| to the frozen inner boundary | 15.956549 mm | 13.755202 mm | 1471.724395 A |
| to the frozen outer boundary | 40.956549 mm | 38.755202 mm | 3036.044690 A |

Across the consumed A3 records, the largest observed one-step changes were
`0.803476 mm R / 0.827237 mm Z / 42.719 A Ip`. A4's empirical
`2 mm / 2 mm / 100 A` stop thresholds are about
`2.489 / 2.418 / 2.341` times those values. Neither the margins nor these
empirical multiples prove the unseen action-age 15..30 successors. The q0
late path and A3 return tail use different actions and histories and cannot be
substituted.

## Classification and route

The A4 implementation and real campaign remain unimplemented and unrun. This
is a causal-support/preflight FAIL, not an interface runtime failure, server
deployment failure, p03 scientific hold failure, model/controller failure or
closed-loop result. The frozen A4 gates were not weakened or reinterpreted.
The final objective remains finite-domain, safe, causal two-axis relative/
path/waypoint tracking; A4 is only a source-hold bootstrap discriminator.

Under the existing strict rule that every new successor must have independent
pre-action support, the only immediately executable vector campaign is a
repeat-only source-prefix qualifier over already observed impulses. It cannot
create a new signed, cumulative or late-action-age cell. Thus the route now
has an explicit bootstrap decision before any further TSC:

1. obtain an independent prospective transition tube/bound; or
2. separately authorize a simulator-only empirical one-step exploration
   contract, with its development trajectory forbidden from controller,
   expert or learning qualification and with qualification remaining a fresh
   identity.

Exact noiseless observations make successor checks, stopping and replanning
reliable after every advance. They do not by themselves supply a pre-action
bound for an unobserved successor.
