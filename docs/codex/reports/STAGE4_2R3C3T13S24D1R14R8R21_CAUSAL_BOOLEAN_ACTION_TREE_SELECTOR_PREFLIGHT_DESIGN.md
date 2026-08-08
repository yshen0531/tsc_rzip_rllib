# Stage4.2R3c3T13S24D1R14R8R21 causal Boolean action-tree selector preflight design

Frozen prospectively on 2026-08-08 Asia/Shanghai after both R8R20 physical
phase raw-integrity audits passed, but before opening any R8R20 formal
outcome, repair count, complete-cube oracle, final verdict, or route.  No
R8R20 trajectory outcome was used to choose this design.

## 1. Conditional scientific boundary

R8R21 becomes active only if final R8R20 primary and independent audits agree
exactly on the already frozen route:

```text
DIRECT_BOOLEAN_CUBE_COMPLETION_PASS_CAUSAL_SELECTOR_DESIGN_REQUIRED
```

If R8R20 instead takes its authority-FAIL or integrity-FAIL route, R8R21 is
vetoed without implementation or output.  The applicable R8R20 branch must
then be followed without changing this document.

R8R21 asks whether the complete measured four-decision Boolean action tree
supports a deployable causal selector under pair-held-out replay.  It does
not fit a point plant model, use the held oracle online, execute TSC, certify
continuous-action authority, or establish Gate A.

## 2. Immutable sources and controller boundary

Authenticate the complete final R8R20 primary and independent evidence and
all source fingerprints that R8R20 authenticated.  The physical alphabet,
timing, and actuator boundary remain:

```text
U = canonical direction 2, sign +1, scale 1.0
V = canonical direction 1, sign -1, scale 1.0
decision task steps = [10, 14, 18, 22]
formal arrival = 250/270 ms
formal hold endpoint = 350/370 ms
```

At a live decision the selector may use only:

1. current and past visible R/Z/Ip;
2. current and past 14-coil readback;
3. the user target and current task clock;
4. its own previously issued U/V prefix; and
5. fixed training parameters frozen by this design.

It may not use pair/history labels, source or candidate outcomes, future
state/action, wire or vessel current, unavailable simulator state, an oracle
code, or another rollout.  All Card15, incremental-action, total-action,
current, cosine, off-basis, saturation, exact-target-refresh, fallback, and
safe-stop checks remain unchanged from R8R20/R8R15.

## 3. Exact causal feature

Construct a separate selector at each action-tree node.  A node is identified
only by the selector's own U/V prefix, never by a context label.  Immediately
before each decision, form this feature from the last four available visible
states, oldest first:

```text
for each of four states:
  (R-target_R) / 0.030
  (Z-target_Z) / 0.030
  (Ip-target_Ip) / 10000

at the current state:
  14 coil currents divided by their frozen per-coil absolute limits

current minus previous-decision coil current:
  14 components divided by the same limits
```

The first decision uses the state at the delegated-prefix endpoint as both
the current and previous-decision current.  No fitted centering, whitening,
feature selection, response-dependent scaling, or hyperparameter search is
allowed.  Euclidean distance in this fixed 40-dimensional feature is the
only neighborhood metric.

## 4. Pair-held-out action-tree construction

The sixteen contexts remain grouped into the eight immutable physical pairs,
each containing its two hidden-history members.  Use exactly eight
leave-one-pair-out folds.  Both members of the held pair are excluded from
all neighbor sets, suffix values, tie breaking, and support calibration.

For each training context and every U/V prefix, enumerate the physically
measured descendant codes.  Assign each descendant a deterministic
lexicographic terminal score:

```text
1. formal pass before formal fail
2. larger minimum frozen formal margin
3. smaller integrated normalized R/Z/Ip squared error through the unchanged
   formal endpoint
4. smaller maximum current utilization
5. ASCII code order as the final tie break
```

At each replayed held node, take the three nearest training contexts.  For
each next symbol U or V, take in each neighbor the best descendant consistent
with the current prefix plus that symbol.  Rank a symbol by the worst of its
three neighbor scores, using the same lexicographic order.  Select the better
symbol.  At the root only, the authenticated do-nothing baseline is also an
allowed fail-closed choice and wins whenever neither U nor V has a
three-neighbor formal-pass lower bound.  Once an intervention begins, the
selector must remain inside the measured U/V tree and reevaluate its suffix
at every remaining decision.

The feature-support threshold is response-independent.  In each training
fold, compute the maximum nearest-neighbor distance obtained when each
training pair is itself left out of the other seven training pairs.  A held
node is supported only when its nearest training-context distance is no more
than `1.5` times that maximum.  Zero maximum distance requires exact held
distance zero.  Any unsupported node takes the root baseline fallback before
intervention or a frozen safe completion after intervention and records a
selector-support failure.

## 5. Exact measured-tree replay

The complete physical cube permits causal replay without stitching
counterfactual states.  For a fixed context, every measured code sharing the
already issued prefix must have identical visible state, coil current, and
controller trace through the next decision boundary within absolute
tolerance `1e-12`.  Primary and independent audits must check this for every
context, node, and descendant before selector evaluation.

After choosing the next symbol, replay follows one complete measured raw row
having that enlarged prefix.  Repeated selection therefore terminates at one
actually measured code; a state from one branch may never be joined to an
outcome from another branch.  A shared-prefix disagreement, missing branch,
or non-causal trace fails R8R21.

## 6. Frozen zero-TSC gates

R8R21 executes zero Ray, `gotsc`, TSC, controller, plant step, raw creation,
or snapshot creation.  Primary and structurally independent implementations
must agree on all source hashes, features, support distances, neighbor
orders, node decisions, fallbacks, selected terminal codes, formal metrics,
repairs, regressions, and route.  Numerical comparisons use absolute
tolerance `1e-12`; categorical decisions and inventories must be exact.

The preflight passes only if all are true:

```text
R8R20 final route and evidence authenticated                   yes
shared-prefix causal replay gates                       all/all
held visited nodes supported                            all/all
held selected trajectories finite and integrity-valid    16/16
held selector formal passes                              >= 7/16
failed R8R7 baselines repaired                           >= 1/10
passing R8R7 baselines regressed                           0/6
primary/independent selected codes and route               exact
```

PASS route:

```text
CAUSAL_BOOLEAN_ACTION_TREE_SELECTOR_PREFLIGHT_PASS_FRESH_HOLDOUT_DESIGN_REQUIRED
```

FAIL route:

```text
CAUSAL_BOOLEAN_ACTION_TREE_SELECTOR_INSUFFICIENT_MODEL_BASED_SEQUENCE_REDESIGN_REQUIRED
```

An authentication, integrity, causal-prefix, or independent-disagreement
failure uses:

```text
CAUSAL_BOOLEAN_ACTION_TREE_SELECTOR_EVIDENCE_FAIL_STOP
```

No threshold, feature, neighborhood size, fallback, fold, objective, or
route may change after R8R20 formal outcomes are opened.

## 7. Downstream boundary and learning prohibition

A PASS authorizes only a separately frozen fresh-context real-TSC design for
the causal receding action-tree controller.  That design must state an
independent finite context envelope, safety sentinel, fallback behavior,
formal success criterion, and later robustness sequence before any plant
advance.  Replaying the same sixteen development contexts alone cannot
qualify a fresh holdout or Gate A.

A FAIL rejects only this fixed feature, three-neighbor, pessimistic Boolean
tree selector.  It does not prove the plant unreachable or authorize a gate
relaxation.  It routes to a separately frozen causal model-based sequential
controller redesign.

All R8-family trajectories remain probe/controller-development evidence and
are forbidden from expert, BC, DAgger, and RL data.  Gate A, expert-data
creation, BC, DAgger, and residual RL remain blocked regardless of the R8R21
result.
