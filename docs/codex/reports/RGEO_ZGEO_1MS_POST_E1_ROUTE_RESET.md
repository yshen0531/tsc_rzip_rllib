# R_geo/Z_geo 1 ms post-E1 route reset

Date: 2026-08-14 Asia/Shanghai

Final documentation route:

```text
POST_E1_ROUTE_RESET_ID0_VECTOR_TAIL_DESIGN_REQUIRED
```

## 1. Scope and final goal

This review records the user's accepted route correction.  It changes no
controller, runner, Card15, queue, reward, termination or TSC state semantics.
It ran no server command, TSC, plant advance, fit, training or optimization.

The final goal remains safe, causal and approximate tracking of user relative
`R_geo/Z_geo` displacements, paths or waypoints from the fixed 1100 ms
takeover, under a 1 ms control period and the exact per-turn, per-coil hard
limit `|I_i[k+1]-I_i[k]| <= 0.3 A`.  Ip is a coupled observation plus
soft-hold/hard-safety quantity.  History remains continuous through every
`R_mid` crossing.  Source hold and any single primitive are dependencies,
not replacements for the finite-domain two-axis goal.

Before every issue, current same-step paired-boundary `R_geo/Z_geo` and
same-step Ip are exact noiseless observables.  The complete causal observation
and controller-owned action/readback/queue history accumulated since takeover
is available.  Belief and uncertainty cover latent dynamics, pre-1100
initial uncertainty, future response and model mismatch; they do not estimate
current or past R/Z/Ip measurement error.

## 2. Evidence judgment

NR0 and NR1R2 remain valid foundations.  The earliest substantive route
error was NR2 model comparison before q0 evolution, lag/tail support,
position/history contrasts and a connected work domain were established.
NR2R1 consequently qualified no model.  Its opened holdout remains consumed
diagnostic evidence and may not tune a successor.

B0 proved that q0 is not a finite source hold or recovery.  C1a qualified
canonical-source full-prefix replay only as a finite offline mechanism; its
worst complete rollout time of about 56.5 s excludes a 1 ms online Oracle
claim.  C2a/A1/A2/A3 established small, context-dependent and direction-
dependent authority.  A3's p03 level2 correction is aligned with source
drift but is only about 5.07 percent of the q0 R/Z displacement norm at
state16.  Existing records therefore do not establish nominal hold,
two-sided vector authority, recovery, position dependence, a model or a
controller.

The A4 zero-TSC support audit remains final: only 16/32 transitions have
direct same-prefix support, with the first gap at issue16 -> state17,
level2 effect-age 15.  Exact state16 observation does not reveal state17.

## 3. E1 is parked

The frozen E1 identity and its implementation checkpoint are retained but
inactive.  E1 is not deployed or run.  Its single unknown successor, one
direction, one action age, lack of repeat/sign/baseline contrasts and
forbidden model/calibration use give insufficient information for the final
route.  It must not start an E2/E3 action-age ladder merely because code
exists.

The unfinished E1 package-verifier worktree changes are preserved and are not
part of this route checkpoint.  E1 may be reconsidered only under a new
explicit decision; no current stage imports, packages, deploys or runs it.

## 4. Two distinct contracts

### 4.1 TSC-only prospective empirical identification

This contract may expose a prospectively frozen finite number of previously
unseen digital-twin transitions.  Requiring every new simulator successor to
have already been observed would make identification circular.  The contract
must still freeze and independently audit:

- actual Card15 fields, requested/serialized/applied/readback coordinates,
  queue/effect clocks and the exact `0.3 A` adjacent limit;
- paired-boundary validity, Ip, absolute current, limiter and finite outer
  envelopes at every available state;
- the precise unknown-transition set, maximum attempts/resets/advances,
  no-retry rule and stop-after-observation behavior;
- raw evidence identity, deployment/package identity and failure routes; and
- development, calibration and unopened holdout roles before generation.

This is finite simulator exposure.  An unseen successor has no pre-action
plant tube merely because the current observation is exact.  The resulting
data may support only the prospectively declared identification role and may
not self-qualify controller safety, recovery, expert behavior, BC or RL.

### 4.2 Controller-grade qualification

Any action issued by a claimed rolling controller continues to require a
prospectively calibrated pre-action transition tube, hard-constraint margin,
and an independently qualified contingency/recovery continuation.  Timeout,
OOD, invalid boundary and interface failure must refuse or fall back
atomically.  Terminal/recoverable-set or equivalent recursive-feasibility
evidence is required for continued replanning.  The current action may not
use expected information gain or a future uncertainty shrink as its safety
argument.

Thus source hold/Recourse-L1 no longer blocks all TSC-only identification,
but remains mandatory before controller-grade transport, tracking and active
probing claims.

## 5. Next evidence: ID-0 source-local vector/tail pilot

The next stage is a prospective design, not immediate model code.  It should
use new canonical-source records whose identification roles are declared
before generation.  Its minimum questions are:

1. whether actual Card15 directions have repeatable two-sided R/Z signal;
2. the complete effect/tail window and action-age dependence;
3. early-versus-late issue/context differences under matched q0 prefixes;
4. the full `[delta R, delta Z, delta Ip]` response cone, singular values,
   conditioning and Ip cost;
5. cumulative-level usefulness, saturation or reversal; and
6. the minimum causal history representation supported by the data.

The initial candidate pool may include the actual p03/p04/p07 direction
families because their input and descriptive output geometry is non-collinear.
They are not preselected as a controller basis.  A1's adverse p07-plus result
requires explicit two-sided testing, and every calculation must use the
actual 14-dimensional Card15 vectors rather than sign labels.  Each action
family needs a matched q0 baseline, a short pulse or separately declared
dwell/cumulative primitive, exact return, a full prospective tail window and
at least finite repeatability evidence.

The first development skeleton may use two fresh q0 baselines plus three
candidate directions by two signs by two issue contexts.  This approximate
14-trajectory skeleton is not a calibration or qualification sample size;
the exact matrix, horizon, repetitions and budget must be frozen by the ID-0
design audit before implementation.

## 6. Data roles and gates

Evidence roles remain immutable:

- NR1/B0/C1a: interface, baseline or replay evidence only;
- NR2R1 and A1--A3: consumed design evidence only;
- E1: dormant and, even if later run under its old identity, forbidden from
  model fitting/calibration/qualification;
- new ID-0 development families: structure, direction, tail and memory
  selection only;
- fresh calibration families: uncertainty/tube calibration only; and
- unopened whole-prefix/history/anchor holdout: opened only after model,
  features, horizon, tube and hashes are frozen.

Sibling branches and all rows sharing a prefix/history/anchor remain in one
split.  Steps are never treated as independent samples.  Interface, response
SNR, repeatability, tail support, signed response cone, rank/minimum singular
value/condition, Ip cost and non-vacuous prediction support must pass before
model comparison.

## 7. Position/history factorization and model order

ID-0 cannot prove position dependence because source position, absolute time
and history remain coupled.  Only after ID-0 passes may a second prospective
stage create a small HFS set of matched-time/different-position and matched-
position/different-arrival-history contrasts, with the same baselines and
primitives at every anchor.  TSC-only exploratory anchors may precede
controller-grade recourse under the identification contract; controller
transport may not.

After those gates, compare in this order:

```text
exact actuator/readback/queue
  -> exact current R/Z/Ip recentering at each prefix
  -> time-indexed nominal evolution
  -> stable low-order latent-memory/state-space model
  -> continuous LPV/local-mixture scheduling
  -> optional small GRU/TCN residual only after fresh whole-family benefit
```

Evaluation must start from many real causal prefixes, initialize with exact
current R/Z/Ip and history, and perform H-step future rollouts.  A single free
rollout from 1100 ms is not an adequate proxy for a 1 ms receding controller.

Only a qualified model/tube plus nominal corridor and two-sided residual
authority may proceed to Recourse-L1, a reference governor and constrained
rolling control.  Low-dimensional adaptation starts in shadow mode on fresh
controller histories.  Dedicated probes, deep online updates, RL, student
distillation and ILC remain later optional stages.

## 8. Authorization boundary

The user accepted this route and authorized continued staged development,
including server TSC after a separately committed prospective ID-0 design,
implementation, package, installed-validation and zero-plant gates pass.
This report itself runs no TSC and does not predetermine an ID-0 PASS.  A
design, interface, deployment, raw-integrity, signal, identifiability or
safety failure must stop under its own route and may not be hidden by a larger
model.
