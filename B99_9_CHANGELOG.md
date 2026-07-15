# B99.9 Changelog

## Purpose

B99.8 proved that deterministic evaluation is necessary, but its actor guard was not transactional:

- a trial permission did not guarantee exactly one actor optimizer step;
- evaluation happened several iterations after the step;
- the close-to-best margin was too loose;
- rollback did not restore Adam momentum;
- dual variables continued winding up while actor updates were blocked.

B99.9 replaces that mechanism with a real safe policy-improvement transaction.

## 1. Dual-source resume

B99.9 uses two checkpoints from the same B99.8 run:

- `--resume`: B99.8 `final` or latest `iter_*`, providing mature reward critics, cost critics, critic optimizer, iteration and env-step counters;
- `--policy-resume`: B99.8 `best_error_score`, overriding actor, log-eta and dual lambda values.

Actor and eta optimizers are reset after policy import, removing momentum from rejected or later-degraded B99.8 actor steps.

## 2. Ordinary actor updates disabled

The normal `updates_per_iter=24` path is critic/cost-critic only:

- actor update suppressed;
- eta update suppressed;
- dual update frozen;
- reward critic, cost critics and target critics continue learning.

This prevents hidden actor movement outside the guard.

## 3. Transactional actor proposal

Every configured trial:

1. snapshot actor, log-eta, actor optimizer, eta optimizer, update count, action scale and physics blend alpha;
2. force exactly one MPO actor optimizer step on one replay batch;
3. retain the extra critic update but restore all policy-side state;
4. construct candidate actors along the proposal direction;
5. evaluate candidates immediately in deterministic TSC;
6. accept only a verified multi-scenario improvement;
7. otherwise restore the complete policy snapshot.

## 4. Bidirectional line search

Candidate step multipliers are:

```text
-0.25, 0.125, 0.25, 0.5, 1.0
```

The small negative step is intentional. B99.8 showed that three positive actor steps all worsened deterministic R/Z. A negative candidate tests whether the critic-derived direction is locally reversed relative to the real TSC objective. It is accepted only if real deterministic multi-scenario evaluation improves.

## 5. Two-stage real-environment evaluation

Selection stage:

- evaluate all five candidates on the fixed target;
- reject immediately if no reliable candidate improves the fixed-target baseline.

Validation stage:

- evaluate the selected candidate on two nearby target scenarios;
- compare against cached baseline results for all three scenarios;
- aggregate with `mean + 0.5 * worst`;
- reject if aggregate improvement is below threshold or any scenario regresses too much.

Scenarios:

```text
fixed
R target -0.01 m, Z target +0.02 m
R target +0.01 m, Z target -0.02 m
```

## 6. Hold-aware guard score

The score is no longer terminal-only. It includes:

- terminal R/Z error;
- late-window R/Z RMS error;
- late velocity;
- late hold fraction;
- weak Ip penalty;
- weak action penalty.

R/Z late RMS dominates. Ip remains a soft monitor.

## 7. Exact rollback

Rejected transactions restore:

- actor parameters and buffers;
- log-eta;
- actor Adam state;
- eta Adam state;
- learner update count;
- action scale;
- physics-blend alpha.

Accepted fractional steps reset actor Adam, because full-proposal moments are inconsistent with an interpolated parameter step.

## 8. Dual anti-windup

Dual updates are frozen during B99.9 transactional training. The imported protected-policy lambda values remain in the actor cost term, but they cannot keep integrating while the actor is blocked.

## 9. Ip priority consistency fix

B99.8 relaxed Ip in the top-level reward, but the active curriculum stage still overrode several Ip settings with stricter values. B99.9 makes both layers consistent:

```text
w_ip = 0.005
w_ip_guard = 0.02
ip_guard_a = 10000 A
reach_success_ip_tol = 6000 A
hold_success_ip_tol = 8000 A
quality_success_ip_tol = 6000 A
quality_success_max_ip_error = 10000 A
```

Ip constrained cost remains weak with 5--8 kA-scale tolerances.

## 10. Checkpoints and logs

New outputs:

```text
actor_transactions.jsonl
accepted_latest/
best_error_score/
```

`best_error_score` is written only from reliable transactional multi-scenario evaluation. Legacy rollout best selection and the B99.8 periodic guard are disabled.
