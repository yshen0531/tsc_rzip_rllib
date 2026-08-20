# ID-2Z24R1 centered co-allocation preflight design

Date: 2026-08-20

## Purpose

ID-2Z24R1 is a zero-TSC, zero-fit exact-Card15 preflight. It decides whether a
finite interior transition nominal and three signed residual coordinates can
be represented jointly, accumulated and returned without clipping. It does
not measure plant response and cannot establish authority, capture, recovery,
Recourse, a model, or a controller.

The stage implements the approved post-ID2Z23 route review. ID2Z23 remains a
clean scientific FAIL for four-issue replacement vertices. That result is not
relabelled: this preflight changes the action coordinate from replacing full-F
to centered co-allocation inside the same per-issue slew polytope.

## Evidence and construction

The authenticated ID2Z23 `baseline_full_f` provides the exact source prefix
and the full-F Card15 increment. Three independently executed branches provide
the exact first-step p00-minus, p05-plus and p06-plus increments. The p05 pair
and both issue phases are retained as forensic evidence that the old result
was dominated by the omitted-F common component; they are not used as plant
labels for this stage.

For each candidate nominal share in the preregistered descending grid
`0.50, 0.45, 0.40, 0.35, 0.30, 0.25`, the preflight constructs each outgoing
Card15 target from the current exact field. It combines the nominal share with
fixed residual scales `0.50*p00-minus`, `1.00*p05-plus`, and
`0.50*p06-plus`, formats the combined target once, then reconstructs the exact
single-turn current. It never separately quantizes and adds two commands.

The selected share is the largest grid value for which all six signed
vertices are representable at every required state, have per-coil issued slew
at most `0.3 A`, stay inside absolute current limits, retain rank three with
condition at most two, and close exactly after the complete signed sequence.
There is no result-dependent amplitude tuning.

## Prospective stream

Every prospective stream has 65 issues and 66 states:

- issues 0--15: exact tracked full-F prefix;
- issues 16--47: the selected interior center increment;
- issues 48--64: hold the attained center target.

At each of the two frozen phases, issues 24 and 32, a signed branch replaces
16 center increments with eight `N+s*r` increments, seven `N-s*r`
increments, and one exact cumulative-center finish. Its issue-39 or issue-47
target, respectively, must equal the matched center baseline target
byte-for-byte. The finish is constructed before any TSC and must independently
pass the unchanged `0.3 A` slew and absolute-current gates; its difference
from the naive eighth opposite increment is reported. This is an exact action
closure, not a plant-state return or safety fallback.

If this preflight passes, it freezes a prospective campaign of exactly 15
rollouts: one matched center baseline, one zero-fit full-F diagnostic, twelve
phase/axis/starting-sign branches, and one zero-fit exact replay. Maximum
budget is 975 advance attempts and 990 retained states. The campaign is a
simulator-only development identity; it must still pass package, storage,
prefix, runtime, raw, replay and post-successor gates before its data can be
used.

## D0 and authority remain separate

The future D0 data-readiness gate asks for exact execution, repeatability and
persistent distinguishable action-conditioned signal. Negative or one-sided
response is valid model evidence. Positive span, capture and Recourse are not
D0 prerequisites and cannot be inferred from input rank.

If D0 passes, bounded event/value model development and a separate
Authority-L0/Recourse design may proceed in parallel. Real in-loop controller
execution still requires fresh model calibration and blind holdout, qualified
Authority/Recourse, and the hard interface AND gate.

## Stop rules

- Evidence or attribution mismatch: stop with zero TSC and repair only the
  audit/reporting layer.
- No grid point satisfies exact Card15, rank, condition, current and closure
  gates: close this centered cell. Do not try 0.4/0.6, nearby phases, nearby
  durations, or a model under the same route.
- Preflight PASS: authorize only a separately implemented, package-verified
  prospective campaign. It is not a TSC or scientific plant PASS.
- Future D0 FAIL: close this centered grammar without an amplitude/phase
  ladder and reconsider nominal/action allocation.
- Future D0 PASS: freeze all compacts before comparing at most the two already
  approved small model classes; no third-model escalation.

## Claim boundary

ID2Z24R1 can certify only an exact finite digital action construction and its
prospective experiment identity. It says nothing about output authority,
source capture, terminal viability, recovery, waypoint/path tracking,
position/history generalization, R_mid crossing, or deployment.

## Pre-execution erratum identity

The original ID2Z24 implementation-validation run executed zero TSC and found
that pure eight-plus/eight-minus repeated quantization did not close exactly,
although every local rank, condition, slew and current gate passed. That route
remains frozen as `ONE_MS_ID2Z24_CENTERED_CARD15_LATTICE_FAIL_NO_TSC`.
ID2Z24R1 changes only the final digital finish construction described above;
it does not weaken a plant or scientific gate.
