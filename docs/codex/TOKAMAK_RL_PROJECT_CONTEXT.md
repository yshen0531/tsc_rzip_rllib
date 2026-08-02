# TOKAMAK_RL_PROJECT_CONTEXT.md

## 1. Project identity

Repository:

```text
https://github.com/yshen0531/tsc_rzip_rllib
```

Local development is performed in the VS Code workspace on Windows. The server has a same-name working project but is not Git-managed.

Primary code areas:

```text
configs/
scripts/
tsc_rzip_rllib/
tests/
current-stage root .sh files
```

Historical code and output may be read only when required as scientific source evidence.

## 2. Server environment

```text
SSH alias:             tsc-airgap
actual login:          yangshen0711@10.10.60.108
expected HOME:         /home/yangshen0711
remote project:        $HOME/tsc_all/tsc_rzip_rllib
remote staging root:   $HOME/tsc_software
Python virtualenv:     $HOME/tsc_all/tsc_simulation/venv_simu
root access:           no
outbound internet:     no
server Git usage:      no
```

The remote staging root and project root are not interchangeable. Verify both before work. Run the project from `$HOME/tsc_all/tsc_rzip_rllib`.

Typical historical run pattern:

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
source /home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/activate
chmod +x ./*.sh
./run_<stage>_nohup.sh
```

Use the exact launcher for the current stage.

## 3. Transfer constraint

Windows local files must not be compressed or extracted. Transfer directly with `scp`/`sftp`.

Do not use ZIP/TAR/7z as an intermediate representation.

For a clean server code replacement, transfer the complete current source directories and current-stage root files. Do not leave stale files in the four primary code directories.

## 4. Scientific history, condensed

### B99 and route change

The B99 series showed that pure actor-critic/MPO training directions were not reliable enough to own the full 14-coil control problem.

The route changed to:

```text
low-dimensional, evidence-backed MPC expert
→ imitation
→ bounded residual RL
```

RL must never restart from unconstrained direct ownership of the 14 coils.

### Stage1/1.1

- real TSC controllability analysis;
- three primary SVD control modes;
- frozen real TSC Jacobian: 175×105.

### Stage2

- low-dimensional CEM trajectory optimization.

### Stage3

- strict trajectories;
- long-hold work;
- goal-conditioned trajectory library;
- receding-horizon MPC;
- Stage3.4 goal-conditioned 350 ms MPC baseline.

### Stage4.1R3–R8

- R3 control-aware residual observer;
- delay-aware and gain/slew-aware control;
- finite weak-slew closure;
- confidence-gated delay/slew identification;
- exact persistent initialization reproduces Oracle;
- separate pre-control calibration;
- correction of queue bookkeeping and untrusted-default-start behavior.

### Stage4.1R9–R11

These stages explored terminal feedback and longer horizons.

Important route correction:

- 550 ms, 750 ms, and 2 s runs are diagnostics;
- they do not change the formal arrival deadline;
- a long observation window must be separated from the arrival specification.

### Restored formal timing

The immutable formal contract is:

```text
normal/strong slew:
  arrival by 250 ms
  hold through 350 ms

weak slew 0.9:
  arrival by 270 ms
  hold through 370 ms
```

The 30 mm R/Z, 0.1 m/s speed, and frozen Ip gates remain unchanged.

### Stage4.1R12–R17

The weak-slew delay=1/2 failures were investigated without changing formal time.

Key findings:

- post-deadline damping cannot repair a metric already failed at the deadline;
- early braking must be delay-pipeline aware;
- handoff that discarded target-conditioned nominal control/integral state was flawed;
- the 175×105 model did not cover all state-36/37 tail dynamics;
- bounded local response probes were used;
- small-signal superposition was validated;
- large-amplitude bidirectional symmetry was not validated;
- one-sided braking remained predictable and monotonic.

Frozen Stage4.1R17 finite baseline:

```text
18/18 formal finite static-grid cases
delay=1 weak-slew patch: 6× one-sided braking
delay=2 weak-slew patch: 7× one-sided braking
trusted calibration token exact replay: yes
```

Limitations:

- same clean digital twin;
- only two targets;
- discrete static delay/slew grid;
- no authentic restart;
- no unseen hidden history;
- no continuous parameter changes;
- no plant/Jacobian mismatch;
- no measurement-noise robustness;
- no disturbance recovery;
- no deployment claim.

The global minimum formal margin is very thin in at least one unchanged source case, so finite-grid PASS is not broad robustness.

## 5. Certified restart foundations

Stage4.2R1 means authentic TSC plant-state restart action replay. Its R1c
result is certified for all 18 finite clean same-source cases:

- exact source-action capture;
- authentic snapshot at 200 ms elapsed / 1300 ms absolute TSC time;
- 18 complete manifests and 144 payload files;
- exact 14-coil and full 48-wire state;
- 18 fresh TSC restart suffixes;
- exact visible, action, and full-wire suffix;
- immutable formal contract 18/18.

R1 intentionally restored no controller state.

Stage4.2R2 then persisted causal controller state: observer history,
integrator, previous correction, pending delay queue, trusted calibration,
modeled delay/slew, controller phase, and source/code fingerprints. It stored
no future action or measurement. The offline gate recomputed 282 suffix
actions exactly, and 18 fresh controller/TSC processes reproduced online
actions, visible state, and full-wire state exactly while preserving the
formal contract 18/18.

Both results are finite same-source restart foundations, not robustness
claims. Their global minimum formal signed margin is only
`1.0456920999768471e-05`.

## 6. Current near-term objective

Stage4.2R3 and R3a completed 54/54 and 72/72 authentic state-generation
rollouts respectively, without runtime or corruption errors. Both remain
failed under their original preregistered hidden-state gates and neither ran
conditional control. R3a did establish that common expert prefixes generate
different authenticated initial-state groups and that delayed counter-pulses
produce a measurable hidden-history difference up to 0.527 A.

Stage4.2R3b completed its full prospective campaign. Authentic state
construction passed: 72/72 state runs and snapshots, 14 accepted pairs, and
four selected prefix-by-direction pairs. All 32 fresh restart control
rollouts then failed the immutable formal contract despite exact plant
restart and causal controller execution.

Independent raw forensics found that the restart states were closest to R17
visible phases 12--20, while the fresh controller restarted its time-indexed
nominal reference at phase zero. Nominal cases began inside the formal R/Z
box and offset-target cases entered by 50--80 ms, but all left by 80--110 ms
and ended with 149--223 mm box error. Original-start R17 sources for the same
specifications remain 32/32 formal PASS. This is a different-initial-state
controller-design failure, not a plant-restart failure.

Stage4.2R3c completed its offline gate and 32/32 authentic controls. Plant
restart and causality were exact, but formal control passed only 20/32. All
16 prefix-9 controls passed; only 4/16 prefix-5 controls passed. Independent
raw forensics found no runtime, deployment, corruption, restart, causality,
or solver error. The 12 failures are genuine closed-loop failures.

R3c's causal phase alignment substantially repaired the R3b phase-zero
mismatch, but it matched restart R/Z/Ip against an ideal nominal trajectory.
It selected phases 11--13 while the same states were nearest to authenticated
actual R17 visible phases 12--20, with the largest underestimate under delay
2 / slew 0.9.

R3c1 later completed 32/32 authentic controls with exact restart and causal
execution but passed formal control only 16/32. R3c2's zero-nominal terminal
regulator then passed only 12/32. Both are genuine controller-development
failures, not restart, runtime, corruption, or reporting failures.

R3c3 and T1--T11 subsequently identified bounded restart responses and
tested fixed linear, quadratic, target-residual, interaction-aware, and
time-localized response families. T9 proved material reproducible
combined-action interaction. T10 exactly fitted its measured interaction
nodes but remained 16/32 with 0/16 repairs. T11 completed 416/416 authentic
persistent-step probes and passed restart, causality, symmetry, matched
history, rank, and current gates, but its frozen condition gate passed only
25/32.

Post-T11 read-only server forensics found that four condition failures occur
in baseline formal passes, while thirteen baseline formal failures already
pass condition. None of the twelve measured T11 single-probe corners repairs
any of the sixteen failed baselines. Stage4.2R3c3T12 authenticated all 416
T11 raw files and froze the condition-first fixed-basis route as vetoed. It
ran no controller or plant and did not change T11's clean identification
FAIL.

The no-new-TSC Stage4.2R3c3T13 task completed the specification for a
finite-horizon, state-conditioned, interaction-aware transport/braking MPC
with formal task time separated from local model phase and deterministic
causal restart-state/actuator-queue reconstruction. Its V4 audit
authenticated 1,408 existing raw files and passed causality 1,504/1,504, but
the fixed Stage3.4 lifted Jacobian passed the relative prediction gate
0/1,504. It is therefore vetoed as an unqualified restart predictor; this is
a model-design conclusion, not global plant unreachability or a new
closed-loop failure.

T13 ends as `MINIMAL_SENTINEL_REQUIRED`. Stage4.2R3c3T13S1 then completed
its one authorized 52-rollout single-step transition sentinel over four
bookend contexts. Exact execution, restart, causality, snapshot, package,
raw, rank, condition, current, and reporting gates passed, but central
symmetry passed 0/24 and matched hidden-history response passed 0/12. Its
official route is `SENTINEL_FAIL_STOP_IDENTIFICATION`.

Read-only raw forensics found that requested actions were symmetric 24/24,
while actual first-effect coil-current symmetry was 0/24. Of 336 active
compared command components, 304 were smaller than one Card15 `.3E`
formatter grid. Immediate plant symmetry remained only 3/24, immediate
matched-history agreement 6/12, and all full formal windows failed. Thus
finite action resolution is material but is not the only model gap. This is
an identification/model/action-resolution design FAIL, not runtime, restart,
reporting, real-MPC, or global-unreachability evidence.

The active Stage4.2R3c3T13S2 task is a zero-new-TSC exact Card15 actuator and
causal-observability audit over the immutable T13S1 raw. It must preserve
pair/history/wire/future-input prohibitions and route unresolved latent state
to a multi-hypothesis/tube model. A later successful development controller
must still be followed by independent new histories and restart states
before new-target work.

T13S2 then completed with zero new plant steps. Exact Card15 target current
did not exactly equal TSC current readback: only 13,000/36,400 components
matched at `1e-9 A`, with maximum residual `1.0e-5 A`, so the frozen route is
`ACTUATOR_MAPPING_IMPLEMENTATION_GAP`. Eight exact causal-state collisions
had different applied current paths; no exact same-feature/same-input
observational alias was present. All 24 matched histories were finitely
separable in the clean allowed feature, but observer/noise/history
extrapolation remains unvalidated.

T13S2R1 read-only forensics found a fixed 14-coil development readback bias
from four baselines and reproduced all 33,600 signed-probe components within
`1e-9 A`. This retrospective split supports a quantized actuator nominal plus
nonzero uncertainty, not a point plant model.

T13S3 then implemented the exact quantized actuator, immutable causal
unknown-velocity restart observer, forbidden-field rejection, and
fail-closed multi-hypothesis transition tube. Its isolated tests passed
15/15 and the installed Linux suite passed 654/654 with one expected skip.
It ran no TSC and closes as `INTERFACE_COMPLETE_HOLDOUT_REQUIRED`, not a
plant-model or controller result.

T13S4 then stopped at its mandatory offline lattice gate before any real
trajectory. The complete 52-spec audit found only 11 offline-complete specs
and 41 design failures: 40 issue actions conflicted with the frozen
four-local-step and 0.25 incremental-action requirements, and one exact
Card15 inverse was not representable. Raw, plant advances, and TSC were all
zero. T13S4 is final as `LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC`; it is not a
runtime, restart, plant-control, or real-MPC failure.

T13S5 then completed all 68 authentic q2 restart trajectories. Runtime,
deployment, restart, causality, raw, snapshot, current, and final-report
integrity passed. The exact final route is `LATTICE_HOLDOUT_FAIL_REDESIGN`:
development rank/condition passed only 2/4 cells, a non-vacuous tube passed
3/4, and consumed independent-history validation passed relative error 0/32.

Source and raw timing forensics found a design error: T13S5 replaced the
final Card15 action after the inherited software delay queue, so every probe
reached TSC current at `issue_step + 1`, independent of its delay label. The
preregistered delay-2 response states were therefore late. This cannot
explain away the delay-zero result, whose already-correct immediate states
still achieved 0/16 relative-error validation across the independent q2
history. The single static cross-history map is therefore also genuinely
insufficient in this finite envelope.

T13S6 then completed that zero-new-TSC reinterpretation and was independently
recomputed directly from all raw. Corrected timing restored all four
development maps to rank four with maximum condition 7.9548 and all four
tubes inside their caps. The consumed q2 validation nevertheless passed
containment only 14/32 and relative error only 2/32, with maximum scaled
error 1.0974. Its certified route is
`IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN`. The effect-time bug and
cross-history model failure are therefore distinct, real findings.

T13S7 then authenticated all 120 q1/q2 raw files but failed its frozen audit.
Only 24/112 held-out rows had a supported hypothesis and all four S1 hard
maps had rank zero. Source and raw forensics proved this was primarily a new
audit-design error: S1 probes enter before the inherited delay queue and all
24 groups obey `issue+delay+1`, while S5 replaces the post-queue Card15 action
and all 32 groups obey `issue+1`. The 24 apparent S1-hard successes at the
wrong immediate states were zero-input/zero-output vacuity, not model
evidence. T13S7 does not cleanly test multi-history compatibility.

T13S7R1 corrected the campaign effect contracts and restored all 16 local
ranks and tubes, but its frozen selector had input support for 0/112 held-out
rows. Even searching all three same-stratum maps supported only 16/112 rows,
all in one S5 hard/transport context pair, and cross-campaign support was
zero. The final route is
`CAMPAIGN_SPECIFIC_CAUSAL_MULTI_HYPOTHESIS_TUBE_INSUFFICIENT_REDESIGN`.

T13S8 removed the adjacent cancellation transition. Support improved to
64/112, but containment reached only 29/112 and relative error 39/112. All
S1 pre-queue rows remained unsupported while all S5 post-queue rows became
supported, proving both an excitation incompatibility and a remaining
supported cross-history model failure.

T13S9 then completed 68/68 authentic q1 identification trajectories through
the same post-queue Card15 coordinate as T13S5 q2. Raw, snapshot, restart,
causality, runtime, current, statistics, and reporting integrity passed, as
did all four development rank/condition/tube gates. Its consumed internal q1
history diagnostic nevertheless passed containment only 15/32 and relative
error only 20/32. T13S9 is therefore an identification completion result,
not a controller or MPC pass.

The active T13S10 task is a prospectively frozen zero-new-TSC combined
first-effect audit over all T13S5 q2 and T13S9 q1 raw. It uses only measured
14-coil current and causal R/Z/vR/vZ/Ip at the common post-queue
`issue_step + 1` effect state, with eight leave-one-context-out folds and a
label-free same-stratum hypothesis bank. A pass permits only a fresh q3
identification holdout design; a failure requires observer, active
calibration, or nonlinear state-conditioned tube redesign. Formal timing is
unchanged and no controller, MPC, expert data, BC, DAgger, or RL is
authorized.

## 7. Medium-term objectives

After hidden-history and different-initial-state robustness:

1. multiple authenticated restart times;
2. new preregistered R/Z/Ip targets not used for policy selection;
3. bounded plant/Jacobian mismatch;
4. continuously varying delay, gain, and slew rather than a static bank;
5. measurement noise and observer robustness;
6. disturbance injection and recovery;
7. independent long-hold tests after formal arrival, with horizon chosen from
   dynamics rather than route drift.

## 8. Long-term objectives

Only after the MPC expert is reliable:

1. Define expert dataset schema with full causal context and safety metadata.
2. Collect MPC expert trajectories across the validated envelope.
3. Behavior Cloning.
4. DAgger with safety shields and expert intervention.
5. Bounded residual RL.
6. Independent evaluation on unseen initial states, histories, targets, perturbations, and continuous parameters.
7. Deployment-oriented safety validation.

Bounded residual RL may correct a reliable MPC expert. It may not directly replace it or own all 14 coils without hard bounds.
