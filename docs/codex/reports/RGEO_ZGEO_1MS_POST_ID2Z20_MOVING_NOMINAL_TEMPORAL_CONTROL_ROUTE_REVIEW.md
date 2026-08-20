# Post-ID-2Z20 moving-nominal temporal-control route review

Date: 2026-08-20

## Decision

ID-2Z20 remains final as
`ONE_MS_ID2Z20_PHASE_A_SIGNED_AUTHORITY_FAIL_CLOSE_GRAMMAR`. Its failed
one-issue pulse/exact-return grammar is not reopened. The next work is a
decision-complete, zero-new-TSC co-design of the moving nominal, the exact
per-issue Card15 allocation and an augmented terminal/viability object.

This review does not authorize a model, a TSC rollout, feedback, capture,
Authority-L0, Recourse-L1, a waypoint, a path or an R_mid crossing. It
authorizes only implementation and server execution of one read-only
ID-2Z21 contract audit over already tracked compact evidence. A real TSC
campaign may be designed only if that audit can freeze a materially new,
non-saturated sustained-allocation family before seeing new plant results.

## What ID-2Z20 did and did not close

ID-2Z20 tested the exact full-F prefix through state 32, then held the state-32
active target fixed. Each signed arm displaced that frozen center for one
issue and returned to the same center on the next issue. The clean Phase-A
FAIL closes that exact grammar. It does not test a residual allocation around
the contemporaneous moving full-F target.

The distinction is load-bearing. The tracked full-F reference and the
reported held-center continuation have the following finite comparison:

| continuation | state 48 distance / speed | late worst distance / speed |
|---|---:|---:|
| held state-32 center | 26.807 mm / 0.587 m/s | 35.557 mm / 0.567 m/s |
| continuing full-F | 23.207 mm / 0.218 m/s | 28.255 mm / 0.417 m/s |

The ID-2Z20 signal failure is nevertheless real. Only b0 passed the
individual arm gate; b1/b2 were approximately 14--18 um, b3 approximately
4 um, and the best weakest-direction projection was 9.88/10.32 um versus the
frozen 20 um threshold. The isolated b0+ state-35 excursion remains a
phase-specific hybrid observation, not smooth two-axis authority.

ID-2Z18 supplies the complementary boundary. Its sustained signed schedules
separate by about 0.093--0.150 mm after 4 ms, 0.179--0.420 mm after 8 ms and
2.715--7.464 mm over the full trace. Sustained temporal action therefore has
measurable plant effect. However all fourteen development histories still
failed six-state capture. More roots alone would improve support but would
not establish control-aligned authority or terminal viability.

## Route correction

Three objects must now be co-designed instead of being tested serially by
another hand-authored macro ladder.

### Moving nominal and action allocation

Full-F consumes the complete 0.3 A issue budget on at least one coil. A
residual action may not be added on top of full-F. Each 1 ms command must be
chosen inside one exact Card15 slew polytope by allocating or replacing the
nominal increment, for example continue-F, reduce/skip-F, brake, or use a
prospectively supported transverse mode. Legacy runner clipping is forbidden.

The nominal share itself is a control variable. ID-2Z15 rejected constant
fractional-F and fixed duty as standalone open-loop endpoints; it did not
test state-dependent fractional nominal plus feedback. A new construction
must therefore be state/event dependent, not another constant fraction scan.

### Terminal semantics

The six-state source capture gate remains unchanged at 25 mm, 0.1 m/s and 5%
source-Ip offset. It remains the strong stationary-capture milestone and may
not be weakened after a result.

It is no longer the only admissible object for development learning. A
separate augmented moving-terminal/viability object must include at least
R_geo, Z_geo, causal one-ms R/Z velocity, Ip, active target/current, pending
effect, action age/history and remaining exact-action reserve. Success on a
moving terminal is trajectory-relative evidence only; it cannot be promoted
to stationary waypoint hold, fallback or Recourse-L1.

### Temporal semantics

Merely extending the observation horizon is not a new route. Every admitted
candidate must prospectively define first effect, sustained allocation,
switch/braking, terminal allocation and a sufficiently long post-action tail.
Single-frame dips and post-action rebound cannot satisfy persistent authority.

## ID-2Z21 zero-TSC audit

ID-2Z21 is a read-only, zero-fit, zero-new-TSC contract audit. It must:

1. authenticate the frozen ID-2Z18 and ID-2Z20 identities and routes;
2. reproduce the held-center versus continuing-full-F lineage distinction;
3. reconstruct exact F/A/a/E/e/H Card15 increments and the per-issue feasible
   allocation set without odd-symmetry or clipping assumptions;
4. report saturation/headroom and reject unconditional nominal-plus-residual
   addition;
5. evaluate signed 2/4/8 ms R/Z and terminal-velocity effects from the
   complete ID-2Z18 family pairs, with unique family/event weighting;
6. distinguish persistent effects from isolated hybrid states;
7. state whether existing evidence can prospectively nominate at least one
   non-saturated, sustained, control-aligned segment family for a new
   fit-eligible campaign; and
8. emit either a bounded campaign-design route or a finite action-basis /
   nominal redesign blocker.

The audit is not allowed to fit a predictor, tune thresholds, read unopened
calibration/blind schedules, run TSC or declare authority/capture/recovery.
Its thresholds and rules are frozen before server execution.

## Conditional fresh campaign

Only an ID-2Z21 readiness result may open one separately frozen fresh
sustained-allocation campaign. The intended upper bound is two complete
causal roots and approximately 10--14 rollouts, not an open-ended tree. It
must include matched continuing-moving-nominal references, a small crossed
set of predeclared signed sustained segments, complete switch/braking/tail
semantics, exact Card15 allocation and whole-root data roles fixed before
TSC. Negative complete development trajectories remain fit eligible;
replays and validations have zero fit weight; censored windows are not labels.

The prospective data-readiness gate is about sustained, control-aligned
signal rather than complete Recourse. Indicative thresholds to be checked
and frozen by ID-2Z21 are 0.10 mm paired R/Z effect over 4 ms or 0.20 mm over
8 ms, at least 0.05 m/s terminal-velocity effect, persistence over multiple
states, more than one useful task-plane direction and cross-root consistency
or an explicitly observable event partition.

## Learning, authority and recourse dependencies

Machine learning is not blocked until all capture physics is hand solved.
Once a fresh D0-quality sustained/control-aligned dataset exists, a bounded
shadow candidate-value/event model may be developed in parallel with
Authority-L0 and Recourse-L1 work. It should predict candidate sequence
response distributions, terminal increment/velocity, viability margin,
event probability and OOD support. Current R/Z/Ip and exact actuator limits
remain direct inputs/calculations, not hidden states to relearn.

Only two small model forms may be compared: a structured stable causal model
and the same backbone plus one small event-aware residual/mixture. There is
no third-model or tuning ladder.

A real model-selected feedback sentinel remains the AND of:

```text
fresh model calibration/blind holdout PASS
AND finite control-aligned authority PASS
AND Recourse-L1 PASS
AND the exact hard interface PASS
```

TSC sibling branch evaluation that observes candidate futures is an offline,
wall-clock-slow Oracle/teacher only. A real feedback action must be selected
before plant advance by a frozen rule/model using only current exact R/Z/Ip
and causal history.

## Hard stops

- If exact non-saturated allocation cannot be constructed, redesign the
  action basis or takeover nominal with zero new TSC.
- If existing evidence cannot nominate a persistent control-aligned segment,
  do not collect more neighboring histories and do not train a model.
- If the fresh sustained-mode gate fails, close that temporal grammar; do not
  append duration, phase or amplitude micro-stages.
- If the sustained modes pass but a frozen feedback class has no utility
  relative to continuing moving nominal, close that feedback class.
- If local moving-terminal utility exists without stationary capture, allow
  at most one prospectively bounded model/policy route; do not restart a
  manual capture ladder.
- If fresh model calibration/blind holdout or Recourse-L1 fails, do not run a
  controller.

## Final-goal boundary

The final goal remains fixed-1100-ms takeover with exact same-step R_geo,
Z_geo and Ip observation; complete causal takeover history; exact Card15 and
at most 0.3 A per coil per issue; independent hard safety and recovery; and
safe approximate two-axis waypoint/path following, eventually including
bidirectional repeated R_mid crossing without resetting belief. Moving-
terminal tracking is an intermediate construction and may not replace the
final stationary waypoint/hold and recovery requirements.
