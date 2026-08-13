# Current status

> **1 ms NR1 stopped on a numeric validation defect; NR1R1 frozen
> (2026-08-13 Asia/Shanghai).** The authentic NR1 run at `129a091` performed
> nine advances: both four-step hold rollouts passed, then Pattern A stopped
> immediately after its first pulse. The only primary failure claimed PF3L
> exceeded 0.3 A. Exact raw `coil_currents.csv` differencing instead gives
> `(-13.530001 - -13.500001) * 1000 / 100 = -0.300000 A`; all 14 components
> obeyed the hard bound. The false stop came from subtracting binary64
> reconstructions. There was no actual slew exceedance, runtime/TSC failure,
> boundary failure, or control-model result. The old run is immutable and
> incomplete.
>
> A separate NR1R1 identity is now frozen before implementation or new TSC.
> It retains the same six prefixes and at most 24 advances, while validating
> observed kA-turn text and turn conversion in exact decimal arithmetic.
> It does not add a tolerance or hidden reserve and must still reject every
> exact increment above 0.3 A. NR2 remains blocked.

> **1 ms NR1 authorized and prospectively frozen (2026-08-13
> Asia/Shanghai).** After NR0 PASS at `34b580f`, the user explicitly authorized
> continued development and new server TSC. Work moved to branch
> `codex/rgeo-zgeo-1ms-nr1`. Before implementation result or plant advance,
> the exact six-rollout/four-step interface-validation design was frozen in
> `docs/codex/reports/RGEO_ZGEO_1MS_NR1_SAFETY_EFFECT_QUALIFICATION_DESIGN.md`.
> It permits at most 24 authentic 1 ms advances after local, installed-server,
> and zero-TSC offline gates pass.
>
> A minimal read-only server preflight verified the canonical paths, virtual
> environment and required 1100 ms source files, with no actual related TSC
> process. A zero-plant formatter calculation found positive and negative
> nonzero Card15 targets within the 0.3 A hard limit for all 14 coils; the
> coarsest local grid was 0.1 A. No historical raw was read and no server file
> or plant state was changed. NR1 data is `interface_validation`, forbidden
> from fitting or expert use. Model, controller, MPC and tracking conclusions
> remain untested.

> **1 ms route restarted from NR0 (2026-08-13 Asia/Shanghai).** The user
> replaced the prior route contract with a 1 ms control period and an exact
> hard limit `|delta I_i| <= 0.3 A` per control step for every single-turn
> coil in TSC order. The endpoints `+0.3 A` and `-0.3 A` are permitted; no
> smaller hidden operating cap is implied. Card15 remains serialized in
> kA-turn, with turn conversion explicit and unchanged.
>
> Work started from tracked-clean checkpoint `ad4302b` on new branch
> `codex/rgeo-zgeo-1ms-nr0`. The preservation checkpoint `cbdf874` and
> current source checkpoint both exist locally. The prior 10 ms / 3 A NR0,
> NR1 and NR2 results remain immutable historical evidence and do not qualify
> the new route.
>
> Restarted NR0 adds only a distinct pure contract, parsers/dataclasses,
> fail-closed timing/slew/history validation, public exports, synthetic tests,
> and this documentation. It does not alter the runner, environment,
> controller, reward, termination, Card15 formatting, queue/effect timing, or
> TSC state semantics. It accesses no server/raw fixture and executes no TSC,
> training, model, planner, Oracle, MPC, RL, or data generation. Final test,
> commit and push evidence is recorded in
> `docs/codex/reports/RGEO_ZGEO_1MS_NR0_RESULT.md`. Restarted NR1 remains a
> separate authorization boundary.

> **NR2 finite causal model comparison completed as redesign FAIL
> (2026-08-13 Asia/Shanghai).** The immutable 60-trajectory campaign completed
> 480/480 authentic plant advances: development/calibration 44/44 and fresh
> holdout 16/16. Independent audits passed 540 state checks, all 480 Card15
> action checks, 2,700 required raw-file checks, exact split/spec/rank gates,
> and every boundary/Ip/current/slew/TSC safety gate. Fresh holdout stayed
> locked until four calibrated ensembles were frozen at bundle SHA-256
> `ead32665...d9f9`.
>
> On one-shot fresh holdout, ARX/GRU/LSTM/TCN all passed the `R_geo/Z_geo/Ip`
> point and interval gates: joint point success was 100%, joint coverage was
> 97.66--100%, and p95 scaled geometry/Ip error was 0.476--0.530. All four
> nevertheless failed the prospectively frozen `<=0.05 A` p95 recursive
> coil-readback gate. ARX was best at 0.15677 A; neural candidates were
> 1.03--1.31 A and provided no useful gain. Final route is
> `CAUSAL_MODEL_COMPARISON_FAIL_REDESIGN`; there is no qualified model and NR3
> is blocked. This is a model/state-propagation design failure, not runtime,
> raw, Card15, safety, geometry-signal, controller, MPC, or global plant
> failure. Full evidence is in `docs/codex/reports/RGEO_ZGEO_NR2_RESULT.md`.

> **NR1 fixed-1100-ms prefix replay qualified (2026-08-13
> Asia/Shanghai).** At implementation checkpoint `c56a72a`, server staging,
> installed tests, public imports, source hashes, and the offline gate passed
> before real TSC. The frozen campaign completed 4/4 short trajectories and
> 32/32 plant advances with every safety gate passing. Independent raw
> reprocessing authenticated 36/36 states, 32/32 exact Card15 targets, and
> 36/36 safety checks. Both the center-hold and small nonzero reversible-pulse
> replay pairs had exactly zero parsed difference in boundary geometry, Ip,
> 14 coil currents, and the full wire-current vector. Total campaign wall
> time was 462.572410909 s.
>
> This is only fixed-source exact-prefix replay qualification. It is not an
> arbitrary-state snapshot/branch Oracle, controller, model, MPC, tracking,
> teacher-data, or deployment result. All NR1 raw is
> `interface_validation` and forbidden from fitting/expert use. A transported
> trailing CR produced an odd but unique run-directory name; raw was preserved
> in place and the independent audit selected it exactly. Full details and
> report hashes are in `docs/codex/reports/RGEO_ZGEO_NR1_RESULT.md`.

> **NR1 prospectively frozen before plant advance (2026-08-13
> Asia/Shanghai).** The user authorized continued staged development and
> server TSC. Work moved to branch `codex/rgeo-zgeo-nr1-safety-oracle` from
> NR0 checkpoint `a5257ee`. A minimal read-only server interface check found
> paired finite boundary and limiter data at the fixed 1100 ms source. The
> accepted contract computes `R_geo=0.708635102 m`,
> `Z_geo=0.035241343 m`, `R_mid=0.7919 m`, and `Ip=31286.4059 A`, making the
> source HFS regardless of its legacy LFS directory label. No TSC/plant step
> was run by that check.
>
> The frozen NR1 design permits only four eight-step trajectories after
> implementation and offline qualification: a representable Card15-center
> hold and exact replay, plus one 0.05-normalized alternating-sign pulse with
> immediate exact-center return and exact replay. All 32 advances are
> `interface_validation`, forbidden from expert/training use. Missing geometry,
> safety/Ip/current/slew failure, abnormal TSC, or replay mismatch fails
> closed. A pass can qualify only fixed-1100-ms prefix replay, not arbitrary
> snapshot branching, a teacher dataset, a controller, MPC, or RL.

> **New-route proposal recorded; no implementation or new TSC yet
> (2026-08-12 Asia/Shanghai).** The user retired the former Stage4.2/R8
> fixed-local-model-to-MPC-expert route as the active route. This does not
> invalidate or reinterpret any prior raw data, PASS/FAIL, report, or package.
> The pre-supersession preservation checkpoint is `cbdf874`.
>
> The newly recorded goal is safe, causal, approximate following of user
> `R_geo/Z_geo` endpoint/path commands from the fixed 1100 ms start, in a
> reasonable finite work domain and with negotiable motion duration. The
> controlled coordinates are the bounding-box center of one valid plasma
> boundary, not `xmag/zmag` and not the current pressure-weighted `rc/zc`.
> LFS/HFS is a deterministic label from `R_geo` relative to the midplane
> inner/outer-limiter radial midpoint; trajectories may cross it repeatedly.
> Ip is not user-commanded but remains a coupled observed and safety state.
>
> The recommended main architecture is history-conditioned,
> uncertainty-aware constrained receding-horizon control. A branch/prefix
> replay TSC Oracle is a future optional teacher/planner candidate, while a
> structured probabilistic history model plus constrained NMPC is the
> scalable main-controller candidate. It must not be called robust before
> calibrated error, recovery, and recursive-feasibility conditions pass.
> Outer RL is optional and must prove added value.
> See `docs/codex/RGEO_ZGEO_NEW_CONTROL_ARCHITECTURE.md`.
>
> This discussion produced documents only. It changed no controller code,
> configuration, package, server file, or TSC result and ran no feasibility
> experiment. The next executable stage is repository-only NR0, defined at
> the top of `CURRENT_TASK.md`; it requires a new user-authorized conversation
> and must pause before any NR1 TSC work.

> **NR0 repository interface implemented locally (2026-08-13
> Asia/Shanghai).** Branch `codex/rgeo-zgeo-history-control` adds a pure
> fail-closed `R_geo/Z_geo` signal, command, Ip-constraint, evidence-identity,
> and causal history/action contract plus synthetic tests.  It uses only the
> explicit same-state `gfile.boundary_R/boundary_Z` plasma boundary and the
> paired limiter trace; there is no magnetic-axis, centroid, historical-alias,
> split-source, or silent fallback.  The history keeps one belief identity
> across LFS/HFS crossings and explicitly distinguishes issued, serialized/
> quantized, queued, applied, and measured-current stages.
>
> NR0 changes no existing controller, environment semantics, reward,
> termination, Card15 formatter, queue/effect timing, runner, or TSC state.
> It uses synthetic tests only and has not accessed the server, run TSC,
> trained/fitted a model, tested an Oracle, implemented MPC/RL, or generated
> any experiment/learning data.  Validation/commit/push details are recorded
> at handoff.  NR1 remains unauthorized pending explicit user confirmation.
>
> Local verification: NR0 plus adjacent actuator/causal-observer tests pass
> 25/25; repository compileall and isolated NR0 import pass.  The Windows full
> discovery run executed 1,283 tests: 1,256 passed and 27 legacy Linux-only
> modules failed at import because Windows has no `resource` module.  The
> repository JSON scan parsed 28,402 UTF-8 JSON files and found four preexisting
> evidence files outside NR0 that are non-UTF-8 or not valid JSON.  These are
> environment/preexisting-evidence findings, not NR0 interface failures; NR0
> did not modify them.

---

## Archived status at route supersession

> All later uses of `active`, `next`, `authorized`, or equivalent imperative
> language are preserved historical wording only and grant no current
> authority. Do not resume R51R4D4 or any legacy conditional successor.

> **Final R8R51R4D3 center-bridged two-pulse geometry PASS; R51R4D4 design
> freeze active (2026-08-10 Asia/Shanghai).** R51R4D3 completed at prospective
> design/implementation/package checkpoints `bdfeeae / 80e7059 / 602c8a4`.
> Project-venv local source and fresh empty direct-copy validation, followed by
> server staging and installed validation in the existing server virtualenv,
> passed 1,299/1,299 hashes, 154 manifest JSON (155 including the manifest),
> 512 Python compilations, 461/461 `bash -n`, focused `8/8`, and full
> `1626/1626`, with one expected isolated-package/server skip. Direct
> `scp -r` used no archive. One initial staging wrapper returned a local
> PowerShell `NativeCommandError` only because successful unittest progress on
> remote stderr was misclassified; the remote log already said PASS and an
> immediate stderr-merged repeat exited zero.
>
> The accepted zero-TSC primary and structurally independent scalar paths
> authenticated corrected final R51R4D1 and constructed all 250 frozen ordered
> schedules as two independent q0-to-target pulses separated by exact return at
> task step 16 and an exact zero-increment q0-center bridge at step 17. Every
> frozen criterion passed `250/250`; context and history-pair coverage passed
> `10/10 / 5/5`. Discrete, action-stream, and coverage agreement were exact;
> maximum numerical difference was `2.220446049250313e-16`. Maximum incremental
> action/current utilization were `0.2111111111111112 / 0.3912`; minimum second-
> transition cosine was `0.9999999999999999`, and maximum off-basis residual
> was `0.09907590194856301` under the unchanged 0.10 cap. Action-stream digest:
> `fa186ce6d9363ef6513f0bdd6d529d645570b0c05caeb335a49d75381c6e9339`.
>
> The inherited post-return componentwise-zero command diagnostic remained
> `0/250`, but it was prospectively frozen as diagnostic-only; exact physical
> center/Card15/current and all formal schedule gates passed `250/250`. D3 ran
> zero TSC, raw, snapshot, plant step, response, controller, model, or
> optimization. Final route is
> `REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_CENTER_BRIDGED_TWO_PULSE_SCHEDULE_PREFLIGHT_COMPLETE_R51R4D4_DESIGN_REQUIRED`.
> This is action geometry only, not response, authority, controller, MPC,
> formal-control, plant-reachability, or Gate A evidence. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4D3_FORENSIC_REPORT.md`.
> Before any new TSC, freeze R51R4D4's real-response matrix, safety/raw/
> independent gates, routes, and no-learning boundary. All probes remain
> forbidden from learning; Gate A and Gate B remain blocked.

> **Final R8R51R4D1 direct two-transport geometry failure; next redesign must
> be frozen before construction (2026-08-10 Asia/Shanghai).** R51R4D1 was a
> zero-new-TSC 250-spec action-geometry preflight over ten failed contexts and
> the complete ordered product of five frozen transport targets. The original
> `ba89426` dual attempt falsely reported `0/250` eligible because both paths
> added an undeclared requirement that every post-return refresh command
> representation be componentwise binary64 zero. Exact stored-center current,
> exact post-return q0 Card15/current, return, clock, and q0 gates were already
> 250/250; no TSC, raw, controller, response, or plant result was affected.
>
> The one-predicate fix was frozen/implemented/packaged at
> `ebf96e9 / 238e9e2 / b98f9c8`. It retained the rejected predicate as a
> diagnostic and hard-required the original aggregate action-stream digest
> `d1607012ca5e39cca3b3113c269c569c754603c49704cef419b239d810ea7ccb`.
> Accepted local and empty-copy plus server staging/installed validation passed
> 1,292 hashes, 154 JSON, 509 Python compilations, 460 `bash -n`, focused
> `10/10`, and full `1618/1618`, with one expected isolated-package skip.
> Direct `scp -r` used no archive.
>
> Under fresh corrected identity, primary and independent agreed on every
> event digest, criterion, eligibility, and coverage set, with maximum
> numerical difference `3.3306690738754696e-16`. Corrected eligibility was
> `68/250`, but frozen context coverage passed `0/10`: contexts 0--3 had eight
> eligible pairs each and contexts 4--9 had six each, below the required ten;
> the latter six contexts also lacked complete `d2m` successor support.
> Incremental/off-basis gates passed only `178/250 / 190/250`; maximum
> incremental action was `0.3518518518518519` and maximum off-basis residual
> `0.2885170771363397`. Final route is
> `REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_TWO_TRANSPORT_SCHEDULE_GEOMETRY_INSUFFICIENT_NO_REAL_TSC`.
>
> This is a direct target-to-target action-geometry/support design FAIL, not a
> runtime, source, current-equivalence, controller, plant, formal-control,
> real-MPC, or global-reachability result. R51R4D2 is blocked and unrun. Exact
> report: `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4D1_FORENSIC_REPORT.md`.
> The active action is to freeze a new zero-TSC center-bridged/split sequential
> schedule redesign before generating it. All evidence is forbidden from
> learning; Gate A, expert data, BC, DAgger, residual RL, and Gate B remain
> blocked.

> **Final R8R51R4 sustained-dwell authority failure; R8R51R4D1 active
> (2026-08-10 Asia/Shanghai).** The immutable R51R4 v2 campaign completed
> 100/100 authentic full-horizon trajectories and 3,620 plant steps with zero
> runtime, safety, restart, causality, Card15, saturation, forbidden-input, or
> raw-integrity failure. Its original primary and independent raw audits
> falsely selected the execution-failure route because they compared real TSC
> current with a binary64-reconstructed nominal current using binary equality.
> Exact physical actions and currents were already correct.
>
> The separately frozen zero-new-TSC repair at contract/implementation/package
> checkpoints `4059e98 / 0a1d062 / 7be4a30` retained exact action, physical-
> current, state, event-order, and forbidden-input gates and changed only the
> nominal-current comparison to the pre-existing `rtol=0, atol=1e-12 A`
> contract. Primary NumPy and independent scalar replay passed 100/100 and
> agreed exactly: q0 `100/100`, all event currents/actions `2,620/2,620`,
> dwell zero increments and unchanged physical currents `400/400`, return
> `100/100`, post-return center `1,820/1,820`; maximum nominal-current
> difference was `2.842170943040401e-14 A`. The repair produced zero new TSC,
> raw, controller execution, plant step, snapshot, model, or optimization, and
> the original state hash remained
> `59c914a6e772c5b8333a62060ca2fec862736949c15077ee925fe200b90617d9`.
>
> Only after both raw audits passed, the unchanged formal evaluator opened 110
> rows. Candidate passes were 0/100, repairs 0/10, and the measured oracle
> remained 6/16. All ten failed baselines had a positive best minimum-margin
> gain (`0.0004796984--0.0085314272`), but none crossed zero. Independent
> formal algebra agreed on every outcome and route with maximum numerical
> difference `4.440892098500626e-16`. Final route is
> `REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_INSUFFICIENT_LONGER_SEQUENTIAL_REDESIGN_REQUIRED`.
> This is a genuine single-transport/dwell action-family design failure, not a
> runtime, deployment, restart, raw, reporting, safety, solver, formal-
> evaluator, real-MPC, or global plant-reachability conclusion.
>
> Local source/fresh empty-copy and server staging/installed validation passed
> 1,284 hashes, 153 strict JSON, 506 Python compilations, 459 server `bash -n`,
> focused `19/19`, and full `1608/1608` with one expected isolated-package
> skip. Direct `scp -r` used no archive. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4_FORENSIC_REPORT.md`.
>
> Conditional R51R5 is blocked and unrun. Before per-row results were read,
> the zero-new-TSC R51R4D1 two-transport exact-return schedule preflight was
> frozen at `e1ddc9e`, design SHA-256
> `ccc279be94ac230b86ebea80b07572fe057aab2110657989a261d37cd6988645`.
> It fixes 250 ordered-pair constructions at steps 12/16/20 and dual exact
> action/safety/coverage gates. R51R4D1 is active. All R51R4 data are probes
> forbidden from learning; Gate A, expert data, BC, DAgger, residual RL, and
> Gate B remain blocked.

> **R8R51R4 dual-offline PASS and conditional R8R51R5 design frozen before
> real response (2026-08-10 Asia/Shanghai).** R51R4 implementation and its
> separately audited scientific-FAIL source-authentication hotfix are at
> `938dbad / aba76c1`; accepted installed package checkpoint is `7b394cb`.
> Local and server existing-venv validation passed 1,279 declared hashes,
> 1,281 empty-copy physical files, 153 package JSON, 503 Python compilations,
> 459 server `bash -n`, focused `12/12`, and full `1601/1601`, with one
> expected isolated-package/server skip. Transfer used direct `scp -r` and no
> local archive operation.
>
> The first v1 offline output stopped before construction because R51R4
> incorrectly required final R51R3 server evidence `passed=true`; authentic
> R51R3 is an integrity PASS and preregistered scientific FAIL, so its evidence
> correctly has `passed=false`. The frozen v1 output has zero raw/TSC/plant
> steps and remains `...BLOCKED_BY_SOURCE`. The authentication-only fix now
> requires exact route, integrity/independent PASS, scientific FAIL, zero new
> execution, and zero exclusion; it changes no R51R4 action, schedule, matrix,
> threshold, controller, or TSC semantics.
>
> Under fresh accepted v2 identity, primary and structurally independent
> offline construction passed all `100/100` event streams with exact digest
> `485f5d9a8498bd86f6d08a936000aab1fb6cc31c403e2f29c62a2d6488f5916e`.
> Maximum incremental normalized action is `0.2111111111111112`; maximum
> predicted current utilization is `0.3912`. This remains zero TSC, zero raw,
> zero plant step, and no response has been generated or viewed.
>
> Before real authorization, conditional R51R5 was prospectively frozen at
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R5_WHOLE_PAIR_CAUSAL_SEQUENTIAL_RESPONSE_MODEL_TUBE_PREFLIGHT_DESIGN.md`,
> SHA-256
> `8fea65fb325effcf70431284c6831b6493dc9d99b9d27bbeccc7ce81aad45da9`.
> It can run only if final R51R4 repairs at least one failed context and reaches
> the exact R51R4 PASS route. The active next action is R51R4 real authorization
> and its single fresh 100-trajectory campaign. Gate A remains blocked.

> **Final R8R51R3 authority failure and frozen R8R51R4 sustained-dwell
> sentinel (2026-08-10 Asia/Shanghai).** R8R51R3 completed at prospective
> design/implementation/package checkpoints `1a2cb6d / 9bdcddb / 06e4728`.
> Local project-venv source and fresh empty direct-copy validation passed
> 1,272 declared hashes, 1,274 physical files, 151 strict JSON, 500 Python
> compilations, focused `9/9`, and Windows-shimmed full `1589/1589`. Server
> staging/installed validation reproduced 1,272 hashes, 458 `bash -n`, 151
> JSON, 500 Python compilations, focused `9/9`, and full `1589/1589`, with
> one expected isolated-package skip. Transfer was direct `scp -r` without
> archives; both hosts used only existing virtual environments.
>
> A first shell invocation failed while redirecting its log below a parent
> directory that did not yet exist. The common launcher and Python never
> started, the intended run path remained absent, and no scientific result
> was opened. The accepted retry used the identical frozen run identity after
> creating only the allowed stage root.
>
> Primary and structurally independent scalar raw algebra authenticated final
> R51R2, all 208 R51R1 candidates, and all 16 matching R8R7 baselines. All
> 224 full-horizon rows were retained; baseline formal PASS reproduced
> `6/16`. Candidate passes were `78/208`, but they occurred only in the same
> six contexts whose baseline already passed. All ten failed contexts had a
> strict best-margin improvement, yet gains were only
> `0.0001220817--0.0034286285`; repairs were `0/10` and the measured oracle
> remained `6/16`. Primary/independent discrete results were exact and the
> maximum numerical difference was `4.440892098500626e-16`.
>
> Final route is
> `REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_SINGLE_TRANSPORT_RETURN_HOLD_AUTHORITY_INSUFFICIENT_SEQUENTIAL_MODEL_REQUIRED`.
> R51R3 created zero TSC, raw, snapshots, controller, plant steps, model fits,
> model selection, or optimization. This is a genuine measured short-action-
> family authority failure, not runtime, deployment, raw, restart, reporting,
> real-MPC, global-reachability, or Gate A evidence. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R3_FORENSIC_REPORT.md`,
> SHA-256
> `5cfdd4282f9f859b07f899638dd12c306227f1ff358aec1e86c04ee9ca5cb31e`.
>
> Before any successor offline construction or response, R51R4 was frozen at
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4_FAILED_CONTEXT_SUSTAINED_TRANSPORT_DWELL_SENTINEL_DESIGN.md`,
> SHA-256
> `15f3f8405920bb6ed06f0f257db9bb2566ffaadfdee0df81040a49d1c523f6ad`.
> It fixes the ten failed contexts, the development-selected candidates
> `d0m/d1p/d2m/d3p/u1p50`, return task steps `16/18`, and 100 trajectories.
> A dual exact offline Card15/action/current gate is mandatory before real TSC;
> no threshold may weaken. Before opening any real response, freeze conditional
> R51R5. All trajectories remain probes forbidden from learning. R51R4 is not
> Gate A; expert data, BC, DAgger, residual RL, and Gate B remain blocked.

> **Final R8R51R2 whole-pair model result and frozen R8R51R3 authority
> audit (2026-08-10 Asia/Shanghai).** R8R51R2 completed at design/
> implementation/accepted-package checkpoints `ce66bb7 / eedf15e / 2e96b75`.
> A first package at `b0aeca1` passed local empty-copy and server staging/
> installed validation, but its invocation stopped before model construction
> because the primary and independent source locators omitted R51R1's actual
> `_370ms` config suffix. Server source bytes matched the expected hash and the
> stopped v1 stage contained zero files. The path-only repair/package at
> `4863644 / 2e96b75` added a regression test without changing any model,
> response, fold, tube, or scientific gate.
>
> Accepted local source and empty direct-copy plus server staging/installed
> validation passed 1,265 declared hashes, 1,267 physical files, 494 Python
> compilations, 457/479 applicable shell parses, focused `9/9`, and full
> `1580/1580`, with one expected isolated-package skip. Transfer was direct
> `scp -r` without archives and both hosts used only existing virtual
> environments. Package manifest/SHA256SUMS hashes are
> `2c6d8d3dd269bfd6d3d02432e1644de901322beb496f97f81e77eeb750d86b02 /`
> `84393457e63c3d32006b1749e0053382cf01dafd2a7ddc491df34a2ceb58c098`.
>
> Primary and structurally independent server recomputation authenticated all
> 208 immutable R51R1 rows and passed prediction, point-error, nested-tube, and
> cap gates `208/208 / 208/208 / 208/208 / 8/8`. There were zero forbidden
> inputs or excluded rows and exactly zero numerical disagreement. Maximum
> state-13/state-14 physical errors were
> `[1.780870698162285e-05, 3.736242752193625e-06, 5.993494138041089,
> 3.862420243622e-05, 7.156778008633018e-06, 10.103048139910582]` in
> `[m,m,A,m,m,A]`; all maximum tube half-widths were the frozen floors
> `[.015,.015,3000,.015,.015,3000]`. It ran zero new TSC, raw, snapshot,
> controller, plant step, model selection, or optimization.
>
> Final route is
> `REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_WHOLE_PAIR_CAUSAL_MODEL_COMPLETE_CONTROLLER_PREFLIGHT_REQUIRED`.
> This is only a finite state-12-to-state-13/14 causal response-model PASS,
> not a full-suffix model, controller, MPC, formal-control PASS, or Gate A.
> Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R2_FORENSIC_REPORT.md`,
> SHA-256
> `bf7a56dd3b1c2c166a4fd10a4e6ddb3cbb3387b18af9d5834266d6767816058a`.
>
> Before any R51R1 candidate formal metric, repair mapping, or oracle was
> computed, the zero-new-TSC R51R3 full-horizon authority audit was frozen at
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R3_SINGLE_TRANSPORT_RETURN_HOLD_FORMAL_AUTHORITY_AUDIT_DESIGN.md`,
> SHA-256
> `7f65a14032131ef24a8fb3bb337ec33b3485c8a416fc401d034b96ad1cf93e40`.
> It must evaluate all 16 matching R8R7 baselines and all 208 actual R51R1
> single-transport/exact-return/hold trajectories under the immutable formal
> contract, with independent raw algebra and no exclusions. PASS requires at
> least one of ten failed baselines repaired and a baseline-plus-candidate
> oracle of at least `7/16`. Either outcome remains pre-controller and not
> Gate A. All R8-family trajectories remain probes forbidden from learning;
> Gate A, expert data, BC, DAgger, residual RL, and Gate B remain blocked.

> **Final R8R51R1 q0-integration result and active zero-TSC R8R51R2
> boundary (2026-08-10 Asia/Shanghai).** R8R51R1 completed at design/
> implementation/executed-package checkpoints `ce66bb7 / bbb83b3 / 1baf670`.
> Primary and independent offline construction passed all `208/208` cells.
> The one authorized real campaign then produced 208/208 strict, successful,
> full-horizon authentic TSC trajectories and 7,488 plant steps. Raw inventory
> is 208 files, 6,692,740 bytes, digest
> `0ce9ac9211c00b403f0ef7235cfde81a1e42751fa230d245cd2dc396fc3e3d33`.
> Restart, source state/trace prefix, causality, calibration, exact q0/candidate
> Card15 events, within-context q0 prefix, issue-plus-one candidate effect,
> finite response, exact return, current, abnormal, and forbidden-input gates
> all passed `208/208`; maximum current utilization was `0.3924`, with zero
> runtime failures, safety stops, or forbidden traces.
>
> The original primary and independent both selected the execution-failure
> route only because `q0_first_effect_at_issue_plus_one` used binary array
> equality between state-11 current and a binary64-reconstructed nominal
> readback. State-11 action matched task-step-10 trace action `208/208`,
> state-10 action matched task-step-9 trace action `208/208`, and state-11
> physical current equaled state-10 current exactly `208/208`. Only three
> contexts reconstructed byte-identically, hence `39/208`; maximum current
> discrepancy was only `2.842170943040401e-14 A`.
>
> A reporting-only contract/implementation/package at `1dc42f8 / c5a1311`
> retained exact action comparisons and applied the already frozen
> `rtol=0, atol=1e-12 A` numerical-equivalence rule. Primary NumPy and
> structurally independent scalar raw recomputations agreed exactly and
> passed `208/208`. The hotfix executed zero TSC, raw, controller, or plant
> step and did not overwrite the old reports or state. Original
> primary/independent/state hashes remain
> `925dbed532e4dcda721592fe409158c7defd89636d94affef9157646df5981a1 /`
> `bd7f4a35fbb011abfe282e386080967449f6695486954f2614f4957a12908a4b /`
> `3ba2068fdeae0e4a508e648381a080d49c35c933c9f37c76f1b1fb8e4ac34b54`.
> Accepted hotfix primary/independent/compact/final hashes are
> `fe7edca96abbbb204216c61a92a40e2ffbded762c9c153804deef7e53bc9d151 /`
> `b5c2f4d0acf23ef9d3874c2404bbb0495541e75f1903ef51bf5f407b2fc7a02b /`
> `4f3d922d1f855e5ebe12b96bb844e8d4538296e41ad535d96adfeb997f12641d /`
> `38b87b3e4ffd082b018944f12e36c4b2bcd70c900e09007e816a357c2c9e7efd`.
>
> Final corrected route is
> `REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_R51R2_MODEL_PREFLIGHT_REQUIRED`.
> The old route is preserved evidence of a summary/statistics reporting bug,
> not runtime, deployment, raw, restart, causality, action, controller,
> safety, plant, MPC, reachability, or Gate A failure. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R1_FORENSIC_REPORT.md`,
> SHA-256
> `746a907449f5e43c01f3b34ab3a30b0e5e694e5dee614ffcf903be794981e744`.
>
> Do not rerun R8R51 or R8R51R1. The active task is the already frozen R51R2
> zero-new-TSC whole-pair causal model/tube preflight (`ce66bb7`, design SHA
> `8955235246fb79bc7e855abde79b32e0269f24774e1452bf380e77966eeab095`).
> It must retain its exact 44D causal feature, fixed 180D representation,
> eight physical-pair outer folds, nested training-only ridge/tube selection,
> physical floors, caps, and no-planning-before-model-PASS boundary. Every
> R51/R51R1 trajectory remains a probe forbidden from learning. R51R1 is
> identification integrity only; Gate A, expert data, BC, DAgger, residual
> RL, and Gate B remain blocked.

> **Final R8R51 implementation-gate failure and frozen R8R51R1/R51R2
> boundary (2026-08-09 Asia/Shanghai).** R8R51 completed at design,
> implementation, and package checkpoints `a82effc / 274e970 / 04d3250`.
> Local project-venv source and fresh empty direct-copy validation plus server
> staging/installed validation passed 1,248 hashes, 149 JSON, 488 Python
> compilations, 455 server `bash -n`, focused `10/10`, and full `1553/1553`,
> with one expected isolated-package skip. Transfer was direct `scp -r`
> without archive creation/extraction, and both hosts used only their
> existing virtual environments.
>
> Primary/independent offline construction passed and agreed on all `208/208`
> fixed cells. The one authorized real campaign then produced 208 structured
> stops before task-step-10 q0 application. Raw inventory is 208 files,
> 5,155,700 bytes, digest
> `ea6ba731534adc810adac98172971aed031a42355ac8c443a3aceab6831751dd`.
> Original primary and independent raw routes agree exactly, but source-aware
> prefix forensics refined the classification: spec, restart, semantic states
> 0--10, semantic trace 0--9, calibration, and forbidden-input gates are all
> `208/208`. Every exception has only the undeclared
> `q0_zero_target=false`; all nine frozen Card15/action/current/saturation
> criteria are true. The exact q0 refresh was only
> `3.3333333296544274e-06--3.7037037048793097e-06`, with predicted current
> utilization `0.36545--0.3907`.
>
> No task-step-10 trace, state 11, q0 action, candidate construction,
> candidate action, or physical response exists. The generic state field
> `response_outcomes_opened=true` is therefore a reporting bug and was
> preserved rather than rewritten. Final route is
> `REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_IMPLEMENTATION_GATE_FAIL_NEW_IDENTITY_REQUIRED`.
> This is an implementation/integration and offline/real gate-parity failure
> before physical action, not runtime, restart, causality, raw, plant safety,
> authority, tracking, MPC, reachability, or Gate A evidence. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51_FORENSIC_REPORT.md`,
> SHA-256
> `82f665bc00cb948dea09adf591860d889b424bef030d763518fca705c929b843`.
>
> R8R51 is immutable and may not resume/rerun. Its conditional R8R52 source
> gate requires PASS and is blocked. Before any successor implementation or
> response inspection, R8R51R1 and conditional R8R51R2 were frozen at
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R1_Q0_GATE_INTEGRATION_SENTINEL_DESIGN.md`
> (`9f8b68063c69e7ff973e0a8aae4e5cdfc0274340b3d7303fc109b5ed01ec4e76`)
> and
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R2_REDUCED_Q0_TRANSPORT_BRIDGE_WHOLE_PAIR_CAUSAL_MODEL_PREFLIGHT_DESIGN.md`
> (`8955235246fb79bc7e855abde79b32e0269f24774e1452bf380e77966eeab095`).
> Active R8R51R1 uses a new identity and the unchanged 16x13 schedule; its
> only integration correction removes the undeclared exact-zero predicate
> and forces offline/real use of one shared q0-event constructor. Even PASS
> is identification only. Every R8-family trajectory remains forbidden from
> learning; Gate A, all learning, and Gate B remain blocked.

> **Final R8R49 offline-stop boundary (2026-08-09 Asia/Shanghai).** R8R49
> was frozen at design checkpoint `8427bfe` and implemented at `6fd0610`.
> Pre-TSC source-locator and 63-character source-hash defects were repaired
> without changing controller/action/gate semantics at `06c7020` and
> `e76a797`; final package checkpoint is `3966426`. Local project-venv source
> and fresh empty direct-copy validation, then server staging/installed
> validation, passed 1,239 hashes, 146 JSON, 485 Python compilations, 454
> server `bash -n`, focused `10/10`, and full `1543/1543`, with one expected
> isolated-package skip. Transfer was direct `scp -r` without archives.
>
> Final primary authenticated all sources and constructed 256/256 frozen
> cells, but only 208/256 passed. Independent recomputation agreed exactly:
> construction digest
> `d9ac2bb9e5ad372f37a78a6245ab8908ce4b9d6f30718975d13c215d27e70968`.
> The 48 failures are exactly `u0p50`, `u0p75`, and `v0p50` in all 16
> contexts. Read-only inner-gate recomputation found that the only failure is
> off-basis residual above the frozen 0.10 cap at both issue and return:
> `0.137722--0.138006`, `0.132895--0.133428`, and
> `0.104011--0.104611`, respectively. Every cosine and other exact
> Card15/action/current/refresh criterion passed.
>
> Final route is
> `Q0_TO_TRANSPORT_BRIDGE_SENTINEL_OFFLINE_FAIL_NO_REAL_TSC`. The stage has
> zero raw, Ray, `gotsc`, TSC, controller, or plant step; response outcomes
> were never opened. This is an exact-action experimental-design failure,
> not runtime, deployment, source, raw, restart, reporting, controller,
> formal-control, real-MPC, plant-reachability, safety, or Gate A evidence.
> Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R49_FORENSIC_REPORT.md`.
>
> The frozen gate will not be weakened and R8R49 cannot resume. Conditional
> R8R50 requires R8R49 PASS and is blocked. The active boundary is to freeze
> a new-identity reduced-candidate bridge sentinel using the 13 uniformly
> admissible candidates, which retain all four canonical directions. Even a
> future sentinel PASS is identification only. Gate A and all learning remain
> blocked; every R8-family trajectory remains forbidden from learning.

> **Final R8R48 and authorized conditional R8R49 bridge-identification
> boundary (2026-08-09 Asia/Shanghai).** R8R48 completed at design/
> implementation/package checkpoints `8427bfe / b80a50a / b2870d7`.
> Local source and fresh empty direct-copy plus server staging/installed
> validation passed all 1,232 hashes, 146 strict JSON including manifest, 482
> Python compilations, 453 server `bash -n`, focused `9/9`, and full
> `1533/1533`, with one expected isolated-package skip. Direct `scp -r` was
> used without archives; both hosts used only their existing virtual
> environments.
>
> Primary and structurally independent paths authenticated final R8R46 and
> rebuilt exactly 560 trajectories, 16 contexts, 35 schedules, and 3,360
> intervals. Source, bank, q0 prefix, bridge matrix, geometry, route, and
> outcome agreements are all true; maximum geometric distance difference is
> exactly `0.0`.
>
> Every context had exactly one physical trajectory matching its q0 prefix
> through task step 12: the q0 baseline itself. Authentic step-12 nonzero
> transport bridges were `0/256`, with 256 missing cells, zero metadata-only
> substitutions, and zero later-interval substitutions. The 44D feature gate
> nevertheless supported `256/256`, while the global 8D transition hull
> supported `32/256`. Geometric support therefore cannot be treated as an
> executed physical bridge.
>
> Final route is
> `Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_ABSENT_FRESH_SENTINEL_REQUIRED`.
> R8R48 has seven files totaling 440,250 bytes and zero raw/snapshot/spec,
> fit, Ray, `gotsc`, TSC, controller, or plant step. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R48_FORENSIC_REPORT.md`.
>
> Conditional R8R49 was frozen before R8R48 result generation at `8427bfe`,
> SHA-256
> `16f321003e7801ac36a5bc97bdb66928a37f469ffb01b31aa09136c2e4a46173`.
> Its exact source condition is now satisfied. R8R49 is the active finite
> 16-context by 16-candidate q0-to-first-transport identification sentinel;
> it is not a controller or Gate A qualification. Gate A and all learning
> remain blocked, and every R8-family trajectory is forbidden from learning.

> **Final R8R46, blocked R8R47, and active causal-bridge audit boundary
> (2026-08-09 Asia/Shanghai).** R8R46 completed at design/implementation/
> original-package checkpoints `9cb7580 / 75b0ba1 / 7d53cc1`, with the
> independent serialization hotfix/package at `c6b04ea / 561dcb4`. Local
> source and fresh empty direct-copy validation, then server staging and
> installed validation, passed all 1,224 declared hashes, 479 Python
> compilations, focused `13/13`, and full `1524/1524`; server also passed 452
> `bash -n` checks, with one expected isolated-package skip. Both hosts used
> only their existing virtual environments and transfer was direct `scp -r`
> without archive creation or extraction.
>
> Primary completed normally. The first independent attempt completed model
> reconstruction but stopped before comparison/write because a NumPy array in
> the independent artifact was not JSON serializable. The audit-only hotfix
> applied the existing JSON-safe conversion and added a regression test; it
> changed no bank, model, innovation, tube, metric, planner, action, gate,
> route, or primary result. Primary was not rerun. The accepted independent
> rerun and finalizer used new logs in the same zero-TSC directory. All ten
> comparison fields are true and all six maximum numerical differences are
> exactly `0.0`.
>
> Whole-pair validation passed with adapted/cold normalized squared-error
> ratio `0.42640699597516946`, all `8/8` folds improved, and maximum fold ratio
> `0.8117445903495492`. Whole-schedule validation passed every absolute
> point/tube/containment/support/finite/forbidden-input/clipping gate, but the
> frozen usefulness ratio was `1.2383400549755048 > 0.95`; 26/35 schedules
> improved and the maximum held-schedule ratio was `2.1935323358398033`.
> Planning was therefore correctly not run. Final route is
> `Q0_CALIBRATION_CAUSAL_INNOVATION_MODEL_INSUFFICIENT_NO_TSC`.
>
> R8R46 has exactly eight server files totaling 123,559,216 bytes and zero
> raw/JSON.GZ/snapshot/spec, Ray, `gotsc`, TSC, controller, or plant step.
> Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R46_FORENSIC_REPORT.md`,
> checkpoint `04bb224`, SHA-256
> `996a1304e11a8bd8225aa6c1d4d76649442c2c5d398baf60fdf3d49a21db65ae`.
>
> Conditional R8R47 was frozen prospectively at `51637b5`, design SHA-256
> `544eb5a9054693e2e0696853bd803ba4a9f72f221b4f60315420c3095683a2d8`.
> Its exact source gate requires R8R46 PASS, so it is permanently blocked and
> must not be implemented or run. The active boundary is a separately frozen,
> zero-new-TSC audit of whether the authenticated 560-trajectory bank contains
> authentic causal support from the exact q0 calibration prefix to later
> nonzero transport actions. This is a support/experiment-design question,
> not another gain fit. Gate A and all learning remain blocked; every R8-family
> trajectory remains forbidden from learning.

> **Final R8R44, blocked R8R45, and frozen R8R46 checkpoint (2026-08-09
> Asia/Shanghai).** R8R44 completed at design/implementation/original-package
> checkpoints `5af9163 / f95e428 / 509b7b4`, with independent metric-view
> hotfix/package checkpoints `0e0685c / 6f0df5d`. The hotfix only supplied
> the three already generated gate fields required by the inherited R8R43
> metric comparator; it changed no bank, model, tube, support, planner,
> action, safety, authority, or primary result.
>
> Local source and fresh empty direct-copy validation passed 1,216/1,216
> hashes, 144 JSON, 476 Python compilations, focused `13/13`, and full
> Windows-shimmed `1511/1511`. Server staging and installed validation
> repeated those gates plus 451 `bash -n`, with one expected isolated-package
> skip. Transfer was direct `scp -r`, no archive was created/extracted, and
> both hosts used only their existing virtual environments. A first local
> focused invocation omitted the Windows resource shim and stopped at import;
> the required shim-first focused/full runs passed. This was a validation-
> command error, not a code regression.
>
> Primary completed normally. The first independent attempt stopped after
> rebuild with `KeyError: combined_tube_cap_passed`; its failure log is
> preserved. After the audit-only hotfix, independent and finalizer completed
> in the same zero-TSC run without rerunning primary. All ten source/bank/
> model/prediction/tube/metric/planning/discrete/route/outcome agreements are
> true and all six maximum numerical differences are exactly `0.0`.
>
> All `16/16` contexts completed safe searches and all six fault injections
> selected hold. No full-tube robust-formal suffix existed, so the deployable
> policy selected exact hold `16/16`: predicted repairs `0/10`, regressions
> `0/6`, fallback-plus-plan oracle `6/16`, and nonzero deployable first
> actions `0/16`. Best failing suffixes did contain nonzero first candidates
> with predicted current utilization about `0.36495--0.3904`, but their worst
> formal-margin violations were `0.2373889664--1.4074872271`; they were
> correctly forbidden from deployment.
>
> Final route is
> `FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC`.
> The stage has eight files, zero raw/snapshot/spec, zero Ray, `gotsc`, TSC,
> controller, or plant step. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R44_FORENSIC_REPORT.md`,
> checkpoint `96ef252`, SHA-256
> `0242dd40f3128e23673239bddbabe8068b2c19a9182f1f0da94679286a6c7556`.
>
> Conditional R8R45 was prospectively frozen at `c5cd07f`, SHA-256
> `edb03567dabc9332a9a0a0c18534c3c4dddec5e05c26c586f2e88aab7c5d15cc`,
> before any R8R44 result. Its exact source gate requires R8R44 PASS, so it is
> blocked without implementation or TSC. Before any new R8R46 computation,
> the q0-calibration causal-innovation design was frozen at `9cb7580` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R46_Q0_CALIBRATION_CAUSAL_INNOVATION_CONTROLLER_PREFLIGHT_DESIGN.md`,
> SHA-256
> `f12206844c181d9610d96588c8f44e3a47cc6661120b208b2ab9c04b57f66e1e`.
> R8R46 is active and zero-TSC. It forces q0 hold through the first measured
> interval, enables bounded same-rollout innovation only afterward, and
> requires new held-pair/held-schedule post-calibration model/tube/usefulness
> plus controller-authority gates. Gate A and all learning remain blocked;
> every R8-family trajectory remains forbidden from learning.

> **Final R8R43 and frozen R8R44 checkpoint (2026-08-09 Asia/Shanghai).**
> R8R43 completed at design/implementation/package checkpoints
> `849d2fa / b87a5c6 / 64a035c`. Local source and fresh empty direct-copy
> plus server staging and installed validation passed 1,209/1,209 hashes,
> 143 strict JSON including manifest, 473 Python compilations, 450 server
> `bash -n`, focused `12/12`, and full `1498/1498`, with one expected server
> isolated-evidence skip. Transfer was direct `scp -r`; both hosts used only
> their existing project/server virtual environments.
>
> The first staging wrapper completed every check but returned 127 after a
> Windows-pipe CR produced a final `$'\\r'` command. A CR-stripping retry
> reproduced all validation with exit zero. A preceding retry stopped before
> tests because first-pass `py_compile` caches invalidated the one-time total
> physical-file count. These were validation-wrapper/newline and cache-
> counting errors, not package, compilation, test, runtime, or scientific
> failures. No source semantics changed.
>
> Primary, independent, and finalizer wrapper exit codes were `0/0/0`.
> Both zero-new-TSC paths authenticated the exact 560-trajectory,
> 35-schedule, 3,360-record bank and all three digests. Cardinality passed
> `1161/1161` with minimum 210 training rows; pair support passed `8/8`.
> Independent bank, model, predictions, neighbors, tubes, metrics, route,
> and outcome were exact; every maximum numerical difference was `0.0`.
>
> The fixed `0.25 global-ridge + 0.75 local-affine` cold ensemble passed.
> Whole-pair point maximum was
> `[0.00756670,0.0148517,132.147,0.0354889,0.0473960]`, tube was
> `[0.015,0.0185647,3000,0.05,0.0592450]`, containment was `72800/72800`,
> and support was `8/8`. Whole-schedule point maximum was
> `[0.00122534,0.00200138,50.3766,0.0151853,0.0303343]`, tube was
> `[0.015,0.015,3000,0.05,0.05]`, and containment was `72800/72800`.
> Every frozen point, tube, finite, containment, support, and forbidden-input
> gate passed without clipping.
>
> Final route is
> `FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED`.
> R8R43 has eight files and zero raw/JSON.GZ/snapshot, Ray, `gotsc`, TSC,
> controller, or plant step. This is a repeatedly used development-bank
> finite model PASS, not independent holdout, controller, MPC, formal-
> control, plant-reachability, or Gate A evidence. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R43_FORENSIC_REPORT.md`,
> SHA-256
> `4aa54a2ff560ba525bb33eef48b082f75cb1142be127fd1ebc13c9b43d3efe55`.
> Six compact files totaling 742,655 bytes are downloaded; the 94.26 MB
> model and detailed evidence remain at the exact server path recorded
> there.
>
> Before any R8R43 result was opened, conditional R8R44 was frozen at
> `5af9163`, design SHA-256
> `8151ee6f9cf086b134f83f4b4ab8cb84d065a204cd5bef928843ae5d41befad6`.
> The R8R43 PASS satisfies its source gate. Active R8R44 is a zero-TSC,
> measurement-recentered finite controller preflight with frozen actuator,
> safety, support, fault-injection, and authority gates. Even a PASS may
> authorize only a separately frozen real-sentinel design. Gate A and all
> learning remain blocked; every R8-family trajectory remains forbidden from
> learning.

> **Final R8R41, blocked R8R42, and frozen R8R43 checkpoint (2026-08-09
> Asia/Shanghai).** R8R41 completed at design/implementation/final-package
> checkpoints `e132925 / 8e551b1 / 2fb0766`, with authentication-only hotfix
> `aa5ae10`. Local source and fresh empty direct-copy plus server staging and
> installed validation passed 1,203/1,203 hashes, 142 strict JSON including
> manifest, 470 Python compilations, 449 server `bash -n`, focused `12/12`,
> and full `1486/1486`, with one expected server isolated-evidence skip.
> Transfer was direct `scp -r`; both hosts used only their existing
> project/server virtual environments.
>
> The first `f26cea3_v1` primary invocation stopped before model fit because
> eight expected R8R39 hashes had correct visible prefixes/suffixes but
> incorrect transcribed middle bytes. Direct server hashing established the
> complete values. The `aa5ae10` hotfix changed only source authentication;
> the stopped directory and logs remain preserved. A separate install-
> wrapper quoting error occurred after a successful copy and was resolved by
> a reporting-only validation retry. Neither event is a scientific result,
> runtime/plant failure, or model-semantic change.
>
> Final primary, independent, and finalizer wrapper exit codes were `0/0/0`.
> Both zero-new-TSC paths authenticated the exact 560-trajectory,
> 35-schedule, 3,360-record bank and all three digests. Local cardinality
> passed `1161/1161` with minimum 210 training rows; pair support passed
> `8/8`. Independent bank, model, predictions, neighbors, tubes, metrics,
> route, and outcome were exact; every maximum numerical difference was
> `0.0`.
>
> The fixed `0.5 global-ridge + 0.5 local-affine` cold ensemble passed the
> entire whole-pair gate: point maximum
> `[0.00504759,0.00994719,113.723,0.0256763,0.0333021]`, tube
> `[0.015,0.015,3000,0.05,0.05]`, containment `72800/72800`, support `8/8`.
> Whole-schedule point maximum was
> `[0.00148865,0.00190061,84.7788,0.0236891,0.0535701]`, tube
> `[0.015,0.015,3000,0.05,0.0669627]`, and containment `72800/72800`.
> Every tube cap and all but the schedule `vZ` point cap passed; `vZ`
> exceeded `0.05` by `0.003570131890090245 m/s`.
>
> Final route is
> `FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC`. The
> final stage has eight files and zero raw/JSON.GZ/snapshot, Ray, `gotsc`,
> TSC, controller, or plant step. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R41_FORENSIC_REPORT.md`,
> SHA-256
> `668f94efe561d76616b354fda9de91591d9a1d2297d3025c13ce679ee6f3d0aa`.
> Six compact files totaling 741,502 bytes are downloaded; the 94.27 MB
> model and detailed evidence remain at the exact server path recorded
> there.
>
> Conditional R8R42 was frozen before R8R41 results at `6921179`, design
> SHA-256
> `7902135995b137f8b9ffc0b110c187c7ee86c60e631ead3c56fc6672a22efbea`.
> Its exact source gate requires final R8R41 PASS, so it is blocked without
> implementation or execution.
>
> Before any new computation, active R8R43 was frozen at `849d2fa` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R43_FIXED_AFFINE_DOMINANT_GLOBAL_RIDGE_LOCAL_AFFINE_COLD_ENSEMBLE_PREFLIGHT_DESIGN.md`,
> SHA-256
> `7586aa8315d7f099c631e852d4178a859850cbc25d0646feae5f5296b227cb61`.
> It fixes the exact binary midpoint `0.25 global + 0.75 local-affine`, with
> no weight scan or gate change. This is disclosed development-bank model
> selection. A FAIL ends scalar cold-ensemble interpolation on this bank and
> requires a separately frozen causal online innovation/adaptation route
> with a meaningful new validation boundary. Gate A and all learning remain
> blocked; every R8-family trajectory remains forbidden from learning.

> **Final R8R39, blocked R8R40, and frozen R8R41 checkpoint (2026-08-09
> Asia/Shanghai).** R8R39 completed at design/implementation/package
> checkpoints `3fa8397 / 56712ae / 40e2c22`. Local source and empty direct-
> copy plus server staging and installed validation passed 1,197/1,197
> hashes, 141 JSON including manifest, 467 Python compilations, 448 server
> `bash -n`, focused `11/11`, and full `1474/1474`, with one expected server
> isolated-evidence skip. Transfer was direct `scp -r`; both hosts used only
> their existing project/server virtual environments.
>
> Primary, independent, and finalizer wrapper exit codes were `0/0/0`.
> Both zero-new-TSC paths authenticated the exact 560-trajectory,
> 35-schedule, 3,360-record bank and all three digests. Cardinality passed
> `1161/1161` with minimum 210 training rows; held-pair support passed `8/8`.
> Independent bank, model, predictions, neighbors, tubes, metrics, route, and
> outcome were exact; all maximum numerical differences were `0.0`.
>
> The fixed equal global-ridge/local-constant cold ensemble failed. Whole-
> pair maximum point error was
> `[0.00708876,0.0171723,80.0548,0.0277354,0.0515296]`, tube was
> `[0.015,0.0214654,3000,0.05,0.0644120]`, and containment was
> `72758/72800`. Whole-schedule maximum point error was
> `[0.00682291,0.0119714,121.256,0.0527404,0.0985733]`, tube was
> `[0.015,0.015,3000,0.0659255,0.123217]`, and containment was
> `72800/72800`. Whole-pair Z/vZ/containment, whole-schedule vR/vZ, and the
> combined tube gate failed.
>
> Final route is
> `FIXED_EQUAL_GLOBAL_LOCAL_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC`. The stage has
> eight files, zero raw/JSON.GZ/snapshot, and zero Ray, `gotsc`, TSC,
> controller, or plant step. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R39_FORENSIC_REPORT.md`.
> SHA-256
> `cf553030cc807ce3b694bbc8cbf8dd71d6d726afe2d896ed2b73c324945266da`.
> Six compact files totaling 740,658 bytes are downloaded; the 94.18 MB
> model and detailed evidence remain at the exact run root recorded there.
>
> Conditional R8R40 was frozen before R8R39 execution at `61c4185`, design
> SHA-256
> `48802fa45048caab7219a593b5bdbbb776d71bcf7a5895c0dfb6a42287c3ef90`.
> It requires final R8R39 PASS and is therefore blocked without
> implementation or execution.
>
> Before any next computation, active R8R41 was frozen at `e132925` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R41_FIXED_EQUAL_GLOBAL_RIDGE_LOCAL_AFFINE_COLD_ENSEMBLE_PREFLIGHT_DESIGN.md`,
> SHA-256
> `445e3522839a36eb3ee403ceccfbe7909f50b9b031f5d5f2951361627f4a3362`.
> It keeps the exact R31 global expert and fixed equal weights but replaces
> the rejected local constant with the already specified R34 k64 centered
> local-affine ridge expert under a new stable dual-implementation gate.
> Gate A and all learning remain blocked; every R8-family trajectory remains
> forbidden from learning.

> **Final R8R37, blocked R8R38, and frozen R8R39 checkpoint (2026-08-09
> Asia/Shanghai).** R8R37 completed at design/implementation/package
> checkpoints `7bc61c0 / 46fa888 / 44a94ed`. Local source and empty direct-
> copy plus server staging and installed validation passed 1,189/1,189
> hashes, 140 JSON including manifest, 464 Python compilations, 447 server
> `bash -n`, focused `11/11`, and full `1463/1463`, with one expected server
> isolated-evidence skip. Transfer was direct `scp -r`; both hosts used only
> their existing project/server virtual environments.
>
> Primary, independent, and finalizer wrapper exit codes were `0/0/0`.
> Both zero-new-TSC paths authenticated the exact 560-trajectory,
> 35-schedule, 3,360-record bank, all three digests, 1,161/1,161 cardinality
> heads with minimum 210 training rows, and 8/8 held-pair support folds. The
> 43 folds produced 1,075 gains: minimum/mean/maximum
> `0.305063 / 0.778346 / 1.0`, with 517 interior and 558 upper projections.
>
> The fixed architecture failed. Whole-pair maximum point error was
> `[0.0107255,0.0181541,149.299,0.0578928,0.0830866]`, tube was
> `[0.015,0.0226926,3000,0.0723660,0.103858]`, and containment was
> `72785/72800`. Whole-schedule maximum point error was
> `[0.0112621,0.0250644,168.329,0.0692899,0.107082]`, tube was
> `[0.015,0.0313305,3000,0.0866124,0.133853]`, and containment was
> `72800/72800`. Combined tube and absolute model gates failed.
>
> Aggregate adapted/cold L1 ratios were `0.419017` whole-pair and `0.688370`
> whole-schedule. All pair folds improved, but `R8R28_g2_UUUU=1.30997` and
> `R8R28_g2_VVVV=1.33170` regressed, so the all-fold usefulness gate also
> failed. Independent bank and neighbors were exact; maximum scaled gain,
> prediction, tube, and metric differences were `7.88760e-15`,
> `6.10623e-15`, `2.77556e-15`, and `2.77556e-15`, all below `1e-9`.
>
> Final route is
> `TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_MODEL_FAIL_NO_TSC`. The stage has
> eight files, zero raw/JSON.GZ/snapshot, and zero Ray, `gotsc`, TSC,
> controller, or plant step. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R37_FORENSIC_REPORT.md`,
> SHA-256
> `e5a6780ce81f7afe7be83c18586e8b3388a6656edc31dc396505e794fa9ceb64`.
>
> Before any R8R37 result was opened, R8R38 was frozen at `7aa9383`, SHA-256
> `d2c86894db9f48969a96e1b8e8ebec265a598a12aaef058f74aefbf757b88caa`.
> Its source requires final R8R37 PASS, so it is blocked and was not
> implemented. Post-result interval forensics found the whole-pair maximum
> vR/vZ tubes at interval 0, where causal innovation is necessarily zero;
> pure gain tuning cannot repair the full gate.
>
> Before any ensemble computation, active R8R39 was frozen at `3fa8397` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R39_FIXED_EQUAL_GLOBAL_RIDGE_LOCAL_CONSTANT_COLD_ENSEMBLE_PREFLIGHT_DESIGN.md`,
> SHA-256
> `f6005ee27d87c0a72043fc8bdc75d16bd074baa9d405a1d72e545e72f0003bbb`.
> It fixes a response-blind `0.5/0.5` global-ridge/local-constant cold
> ensemble in every held fold, with no weight or outcome search. Gate A and
> all learning remain blocked; every R8-family trajectory remains forbidden
> from learning.

> **Final R8R35 and blocked prospective R8R36 checkpoint (2026-08-09
> Asia/Shanghai).** R8R35 completed at design/implementation/package
> checkpoints `7c83240 / ff2340e / 70236b3`. Local source and empty direct-
> copy plus server staging and installed validation passed 1,181/1,181
> hashes, 139 JSON including the manifest, 461 Python compilations, 446
> server `bash -n`, focused `11/11`, and full `1452/1452`, with one expected
> isolated/server skip where applicable. Transfer was direct `scp -r`; both
> hosts used only their existing virtual environments.
>
> Primary and independent zero-new-TSC paths rebuilt the exact 560-
> trajectory, 35-schedule, 3,360-record bank and all three frozen digests.
> Cardinality passed 1,161/1,161 heads with minimum training count 210; all
> 8/8 held-pair state-support folds passed. Independent neighbor identities,
> bank, route, and outcome were exact. Maximum scaled prediction, tube, and
> metric differences were `7.21645e-15`, `2.77556e-15`, and `2.77556e-15`,
> below the frozen `1e-9` gate.
>
> The fixed local-constant/unit-gain last-innovation model nevertheless
> failed. Whole-pair maximum point error was
> `[0.0107255,0.0181541,149.299,0.0578928,0.0830866]`, tube was
> `[0.015,0.0226926,3000,0.0723660,0.103858]`, and containment was
> `72786/72800`. Whole-schedule maximum point error was
> `[0.0112621,0.0250644,168.329,0.0692899,0.107082]`, tube was
> `[0.015,0.0313305,3000,0.0866124,0.133853]`, and containment was
> `72800/72800`. Z/vR/vZ point and schedule tube caps failed; combined tube
> also failed.
>
> Causal adaptation was measurably useful in aggregate: adapted/cold
> normalized L1 ratios were `0.375758` for whole-pair and `0.739326` for
> whole-schedule, both below the frozen `0.95`. All 8 pair folds improved,
> but three schedule folds regressed: `R8R14_d0_p=1.03581`,
> `R8R28_g2_UUUU=1.12480`, and `R8R28_g2_VVVV=1.13978`. Thus the separately
> frozen every-fold no-regression usefulness gate also failed.
>
> Final route is
> `CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_MODEL_FAIL_NO_TSC`. The stage has
> eight files, zero raw/JSON.GZ/snapshot, zero Ray, `gotsc`, TSC, controller,
> or plant steps. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R35_FORENSIC_REPORT.md`,
> SHA-256
> `150e5a22dc804a7ce3cdde6305bbd96478f9bc40bdb813e24d2fa636991b8655`.
>
> Before any R8R35 result was opened, the conditional R8R36 controller-
> preflight design was frozen at `f0eb69f`, SHA-256
> `0c2f3e6b048d05b087a9ce9c746df057f2f70eab5dfdfafefe7e10ac10aa4ac9`.
> Its prospective source gate requires an exact R8R35 PASS, so it is blocked
> and was not implemented or executed. R8R35 is a finite causal
> model/adapter-design FAIL, not a runtime, numerical, controller, MPC,
> formal-control, plant-reachability, or Gate A result.
>
> Before any R8R37 gain fit or prediction, the next eligible training-only
> diagonal innovation-gain design was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R37_TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_SCHEDULE_GENERALIZING_PREFLIGHT_DESIGN.md`,
> SHA-256
> `6433312711b9b107a218bb5701ef6070a0dfbc482fd492d983437c32637fb843`.
> It retains the exact R8R35 cold predictor and all unchanged gates, but fits
> 25 `[0,1]`-projected diagonal gains solely inside each training fold. Gate A
> and all learning remain blocked; all R8-family evidence remains forbidden
> from learning.

> **Final R8R34 and prospective R8R35 checkpoint (2026-08-09
> Asia/Shanghai).** R8R34 completed at design/implementation/package
> checkpoints `1380fe1 / 366dd55 / 335373f`. Its first independent attempt
> stopped on a singular direct intercept system; the mathematically equivalent
> centered-intercept hotfix/package `b3d2ab9 / 8531fad` ran in a new v2
> directory. Failure-only finalizer/package `24a7851 / fbf2848` changed no
> model, prediction, tube, tolerance, or primary result.
>
> Final local, empty direct-copy, server-staging, and installed validation
> passed 1,174/1,174 hashes, 138 JSON, 458 Python compilations, 445 server
> `bash -n`, focused `11/11`, and full `1441/1441` with one expected isolated-
> evidence skip. Transfer was direct `scp -r`; both hosts used only their
> existing project/server virtual environments.
>
> The exact 560-trajectory, 35-schedule, 3,360-record bank and all three
> digests reproduced. Fixed local cardinality passed all 1,161 heads with
> minimum training count 210. The whole-schedule model passed: maximum point
> error `[0.00180312,0.00294031,55.7966,0.0143598,0.0178805]`, tube
> `[0.015,0.015,3000,0.05,0.05]`, containment `72800/72800`. The whole-pair
> model failed: maximum point error
> `[0.0100858,0.0197562,151.185,0.0465098,0.0627917]`, tube
> `[0.015,0.0246953,3000,0.0581372,0.0784897]`, containment
> `72217/72800`. All tube caps and 8/8 state-support folds passed, but Z/vZ
> point caps and 100% containment did not. Planning remained closed. Primary
> route is
> `CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC`.
>
> Independent bank, tube, planning, route, and scientific-outcome agreements
> passed, but the frozen scaled `1e-9` gate failed: maximum prediction, tube,
> metric, and planning differences were `6.91767e-7`, `4.82947e-14`,
> `1.74206e-7`, and `0.0`. The tolerance was not changed. Accepted overall
> route is
> `CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP`,
> classified as `independent_numerical_reproducibility_gate_failure` layered
> on the unchanged primary whole-pair model failure.
>
> R8R34 executed zero Ray, `gotsc`, TSC, controller, plant step, raw, or
> snapshot. It is not a restart, real-control, plant-reachability, formal-
> control, MPC, or Gate A result. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R34_FORENSIC_REPORT.md`,
> SHA-256
> `66a999d89932c38bc392035777d50ba1679cbbf0238aca12bce2f595fa800c43`.
>
> Before opening detailed R8R34 metrics or failed-row identities, R8R35 was
> frozen at `7c83240` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R35_CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_SCHEDULE_GENERALIZING_PREFLIGHT_DESIGN.md`,
> SHA-256
> `ad451b7b14ea1e3dcd84c029042b58068a4879f891e0cbcedd69f546f623fbbf`.
> It fixes a slope-free response-blind 64-neighbor local constant plus a
> unit-gain, one-completed-interval causal innovation update, with unchanged
> outer model gates, a prospective five-percent measurable-benefit gate, no
> fold regression, and no search. Gate A and all learning remain blocked;
> all R8-family evidence remains forbidden from learning.

> **Final R8R33 and prospective R8R34 checkpoint (2026-08-09
> Asia/Shanghai).** R8R33 completed its fixed rank-12 primary at checkpoints
> `82d1307 / cd66c4a / 9c777c7`; a failure-only finalizer at
> `c5cf429 / d1d266d` changed no scientific calculation or gate. Final local,
> empty-copy, server-staging, and installed validation passed 1,168/1,168
> hashes, 137 JSON, 455 Python compilations, 444 server `bash -n`, focused
> `9/9`, and full `1430/1430` with one expected server/isolated skip.
>
> The exact 560-trajectory, 35-schedule, 3,360-record bank and all three
> digests reproduced. Fixed rank 12 passed all 1,161 representation heads;
> minimum numerical rank was 13. The primary model still failed. Whole-pair
> maximum point error was
> `[0.00526394,0.00387221,322.794,0.0768160,0.178383]`, tube was
> `[0.015,0.015,3000,0.0960200,0.222979]`, and containment was
> `72793/72800`. Whole-schedule maximum point error was
> `[0.0356034,0.222100,3879.07,0.500309,1.27386]` and tube was
> `[0.0445043,0.277625,4848.84,0.625387,1.59233]`. Planning did not run.
> Primary scientific route:
> `UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC`.
>
> Independent bank, route, and outcome agreement passed, but R8R33's frozen
> unscaled absolute `1e-12` dual-solver gate failed. Maximum prediction,
> model, outer, and schedule/planning differences were respectively
> `1.03597e-11`, `4.74453e-9`, `1.11200e-8`, and `2.58265e-6`. No tolerance
> was changed. Accepted overall route is
> `UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP`,
> classified as `independent_numerical_reproducibility_gate_failure` while
> preserving the separate primary model failure.
>
> R8R33 executed zero Ray, `gotsc`, TSC, controller, plant step, raw, or
> snapshot. It is not a restart, real-control, plant-reachability, formal-
> control, MPC, or Gate A result. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R33_FORENSIC_REPORT.md`,
> SHA-256
> `9cea9a4412f1375ffb4aa9924d02d05e063801c0965f3214f2dd9db5d3286ff2`.
>
> Before any failed-row inspection or next-stage calculation, R8R34 was
> frozen at `1380fe1` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R34_CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZING_FEEDBACK_PREFLIGHT_DESIGN.md`,
> SHA-256
> `21d86f169cd92ede5263e2a9c6a4fc189e070f5cbfa1bd4dbd7d493fabf8f0c2`.
> It is a fixed response-blind causal 64-neighbor local-affine zero-TSC
> preflight with a prospectively scaled dual-implementation gate. Gate A and
> all learning remain blocked; all R8-family evidence remains forbidden from
> learning.

> **Prospective R8R33 uniformly supported rank-12 checkpoint (2026-08-09
> Asia/Shanghai).** After final R8R32 and before any R8R33 transform, fit,
> prediction, residual, tube, support result, plan, implementation, package,
> action, raw, or TSC, the new zero-TSC identity was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R33_UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZING_FEEDBACK_PREFLIGHT_DESIGN.md`,
> SHA-256
> `51063dc6f2ecede5d42a0cbf5cde6aa4736628ed38f27d3a5edaeba95a368189`.
>
> R8R33 fixes PCA rank 12 and transformed dimension 78 with no search. The
> value is exactly one below R8R32's independently reproduced all-fold
> minimum rank 13. This is a new consumed-development identity, not a change
> to R8R32. All source, causal q4, whole-pair/schedule, point/tube/support,
> Card15/action/current, formal, planning, independent, zero-TSC, and
> learning-prohibition gates remain unchanged. Even PASS only permits design
> of a fresh finite controller sentinel; Gate A and learning remain blocked.

> **Final R8R32 rank-regularized checkpoint (2026-08-09 Asia/Shanghai).**
> The first `be82504_v1` attempt safely stopped at the first genuine rank
> shortfall but its broad exception handler mislabeled that model-design gate
> as execution failure. Its failure JSON is preserved at SHA-256
> `433d8de7e8f32ed7992ec0f8b719542d6969df2664c5534db2fc648a5a1b54cd`.
> Hotfix `2d95371` changed only fail-closed rank reporting/control flow; package
> `3328499` passed local, empty-copy, server staging, and installed validation.
>
> Accepted v2 primary and independent audits authenticated the exact 560-row,
> 35-schedule, 3,360-record bank. Rank 32 passed 152/216 whole-pair heads and
> 665/945 whole-schedule heads: 817/1,161 overall, with 344 failures and
> minimum rank 13. All five independent maximum differences were `0.0`.
> Regression, prediction, tube, support, planning, and formal-plan phases did
> not run; their zero fields are explicitly phase-closed. Final route:
> `RANK_REGULARIZED_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC`.
>
> R8R32 executed zero Ray, `gotsc`, TSC, controller, plant step, raw, or
> snapshot. It is a PCA32 representation-design FAIL, not a runtime,
> deployment, source, reporting, real-MPC, plant-reachability, or Gate A
> result. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R32_FORENSIC_REPORT.md`,
> SHA-256
> `d05df9e88d8f9aeb2c9326a55ad27afc63c72a3eb24ab4c5a72ce6ede0557eb6`.
> All R8-family evidence remains forbidden from learning.

> **Prospective R8R32 rank-regularized schedule-generalization checkpoint
> (2026-08-09 Asia/Shanghai).** Before any R8R32 feature transform, PCA, fit,
> prediction, residual, tube, support result, plan, implementation, package,
> controller action, raw, or TSC, the next zero-new-TSC identity was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R32_RANK_REGULARIZED_SCHEDULE_GENERALIZING_FEEDBACK_PREFLIGHT_DESIGN.md`.
> Its SHA-256 is
> `d5e1e5e51b75267420282379386b24653180493e5f3fc3f19b6d6624c7ca838f`.
>
> R8R32 must reproduce R8R31's exact 560 trajectories, 35 schedules, 3,360
> records and all three bank digests. It retains the causal q4 input, whole-
> pair/schedule exclusions, unchanged point/tube caps, tube construction,
> state/action support, candidates, Card15/action/current gates, planning,
> formal timing, fallback, independent audit, and learning prohibition. The
> sole model change is fixed fold-local standardization plus sign-canonical
> PCA32, exact 178D score/action/score-by-q representation, and ridge `0.01`.
> No hyperparameter search or cap/tube relaxation is allowed.
>
> A model failure stops before planning with zero TSC. A complete zero-TSC
> model/planning PASS may authorize only design of a fresh finite real-
> controller sentinel. It is not Gate A. Gate A, expert data, BC, DAgger,
> residual RL, and all other learning remain blocked.

> **Final R8R31 aligned explicit-four-coordinate feedback checkpoint
> (2026-08-09 Asia/Shanghai).** R8R31 is final at checkpoints
> `728c235 / 53858ea / 96c232e / 3bc46b8 / 0768826`. The final package has
> 1,153 declared files; local source and empty direct-copy plus server staging
> and installed validation passed 135 JSON files including manifest, 449
> Python compilations, focused `11/11`, and full `1411/1411` (server expected
> skip 1), plus server `bash -n` for 442 shell files. Direct transfer used no
> archive and both systems used only their existing project virtualenvs.
>
> Primary and structurally independent zero-new-TSC paths authenticated 560
> aligned trajectories, 35 schedules, and 3,360 records. Whole-pair point,
> support, tube, and `72,800/72,800` containment passed. The whole-schedule
> gate failed: maximum point error was
> `[0.0031825394,0.0038637885,157.5748424,0.0547769867,0.1072493982]`, so vR
> and vZ exceeded `0.05`; maximum tube was
> `[0.015,0.015,3000,0.0684712333,0.1340617477]`, so vZ exceeded `0.08`.
> Planning remained closed. All independent numerical differences were `0.0`.
>
> Final route:
> `ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_PREFLIGHT_FAIL_NO_TSC`.
> R8R31 ran zero Ray, `gotsc`, TSC, controller, plant step, raw, or snapshot.
> This is a finite schedule-generalization model/uncertainty design FAIL, not
> a runtime, controller, real-MPC, plant-reachability, or Gate A result. Exact
> report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R31_FORENSIC_REPORT.md`.
> Before any new fit or result, freeze a new-identity schedule-generalizing
> causal model with unchanged whole-pair/schedule, safety, formal, point/tube,
> independent, fail-closed, and learning-prohibition gates. Gate A and all
> learning remain blocked.

> **Prospective R8R31 aligned explicit-four-coordinate feedback checkpoint
> (2026-08-09 Asia/Shanghai).** After R8R30 was sealed at `b73a8c1`, and
> before any R8R31 bank row, feature, fit, support, implementation, plan,
> package, action, raw, or TSC, the aligned identity was frozen. Exact design:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R31_ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_SENTINEL_DESIGN.md`,
> SHA-256
> `eee31b04fe57fcf2d4da4a397657ff8d26b76c83db9f42bb13b3275b2ea4ed8e`.
>
> R8R31 inherits R8R30's 4D q, 44D causal/238D expanded feature, 17
> candidates, six decisions, model/tube/support/search, fault fallback,
> hard-safety, two-phase, formal, independent, and learning-prohibition
> contracts. It excludes all g3 rows and uses exactly R8R23 `432` + six
> non-U/V R8R14 schedules `96` + R8R28 g2 `32` = 560 aligned trajectories,
> 35 schedules, and 3,360 interval records. Every included major issue falls
> on `[10,12,14,16,18,22]`; interval interiors contain refresh only.
>
> Offline model/support, predicted repair/oracle/regression, nonzero action,
> fault injection, and exact independent gates must pass before TSC.
> Conditional real execution remains safety `4` then qualification `12`; a
> real PASS requires repair `>=1/10`, formal `>=7/16`, and regression `0/6`.
> Even PASS is not Gate A and learning remains blocked.

> **Final R8R30 static-timing checkpoint (2026-08-09 Asia/Shanghai).** R8R30
> stopped before config, implementation, feature, fit, support, plan, package,
> deployment, action, raw, or TSC. Its six-decision model samples
> `[10,12,14,16,18,22]`, but the included R8R28 g3 rows contain unencoded
> major issues at 13 and 19 inside two predicted intervals. Treating those
> origins as zero new coordinate would train against targets caused by future
> actions absent from the causal feature. Final route:
> `EXPLICIT_FOUR_COORDINATE_FEEDBACK_PREFLIGHT_FAIL_NO_TSC`.
>
> This is a prospective source/action-timing design FAIL, not a model-fit,
> runtime, raw, controller, TSC, plant, or Gate A result. Exact audit:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R30_STATIC_TIMING_AUDIT.md`,
> SHA-256
> `5822af88f966207035ac45571a64b0a82fca7845666386d112aa691adf3bbde5`.
> R8R30 is immutable. The eligible new identity retains the 4D/44D/238D
> model but excludes g3, producing 560 aligned trajectories, 35 schedules,
> and 3,360 interval rows. Gate A and learning remain blocked.

> **Prospective R8R30 explicit-four-coordinate measurement-recentered
> feedback checkpoint (2026-08-09 Asia/Shanghai).** After R8R29 was closed at
> `7724088`, and before any R8R30 feature value, fit, tube, support, plan,
> implementation, action, package, raw, or TSC, the corrected identity was
> frozen. Exact design:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R30_EXPLICIT_FOUR_COORDINATE_MEASUREMENT_RECENTERED_FEEDBACK_SENTINEL_DESIGN.md`,
> SHA-256
> `6a65a7ed7e84cbd89f420e2461928ce0cafcf30a96768b8836d67ccc9508d1f4`.
>
> R8R30 retains R8R29's 592 exact source trajectories, 17 candidates, six
> decisions, safety/formal/fallback/two-phase gates, and learning prohibition,
> but explicitly defines `q=[d0,d1,d2,d3]`. The exact feature is 44D (`12
> visible + 14 current + 14 current delta + 4 previous q`); its 18 ordered
> action terms plus four 44D interaction blocks produce a 238D expansion.
> The 592 trajectories yield 3,552 six-interval records. A non-issue source
> step uses `q=0` as no new canonical increment/current-target hold; measured
> refresh actions remain in causal histories.
>
> Whole-pair and 37-schedule jackknife model/tube gates, 8D task-step action
> support, 16 safe searches, a predicted repair, zero fallback regressions,
> oracle `>=7/16`, a nonzero first action, six fallback fault injections, and
> exact independent agreement are required before TSC. Conditional execution
> remains safety `4` then qualification `12`; a real PASS still requires a
> real repair, `>=7/16`, and zero regressions. Even PASS is not Gate A.

> **Final R8R29 static-design checkpoint (2026-08-09 Asia/Shanghai).** R8R29
> stopped before config, implementation, fit, tube, support, plan, package,
> deployment, raw, snapshot, Ray, `gotsc`, TSC, controller action, or plant
> advance. Its frozen 42D/133D R8R23 feature admits only previous/current 2D
> U/V coordinates, while the same design requires six additional signed axes.
> Those actions cannot be represented without changing the frozen feature and
> transition-support identity. Final route:
> `FULL_BASIS_MEASUREMENT_RECENTERED_FEEDBACK_PREFLIGHT_FAIL_NO_TSC`.
>
> This is a prospective architecture/feature-contract design FAIL, not a
> runtime, package, source, raw, restart, causality, Card15, safety, model-fit,
> controller, real-MPC, formal-control, plant, Gate A, or reachability result.
> Exact audit:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R29_STATIC_DESIGN_AUDIT.md`,
> SHA-256
> `b0b8ddfc2f7c7374c593609a3a2794db8cc825e3b7585995925330cab603854b`.
> R8R29 is immutable. Before any model fit, freeze a new identity with an
> explicit 4D signed-axis coordinate, 44D causal feature, 238D expansion,
> task-step support, and independent reconstruction. Gate A and learning
> remain blocked.

> **Prospective R8R29 full-basis measurement-recentered receding-horizon
> feedback checkpoint (2026-08-09 Asia/Shanghai).** After final R8R28 was
> sealed at `3b7bd68`, and before any R8R29 config, implementation, model fit,
> tube, support result, plan, controller action, metric, raw, or TSC, the next
> controller identity was frozen. Exact design:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R29_FULL_BASIS_MEASUREMENT_RECENTERED_RECEDING_HORIZON_FEEDBACK_SENTINEL_DESIGN.md`,
> SHA-256
> `6de6c55bd9b45962a57a93e44f1b285ac6e80e5a1a1e967116f69630a57fcf5c`.
>
> R8R29 deduplicates exactly 592 consumed development trajectories: R8R23's
> 432-row U/V/model bank, 96 R8R14 rows for the six signed axes not already
> represented by U/V, and all 64 changed-timing R8R28 rows. It preserves the
> R8R23 42D causal/133D action-expanded ridge family, R8R25 whole-pair tube,
> unchanged hard action/current/Card15 and formal contracts, and forbids all
> source data from learning. Whole-pair model/tube/support and an offline
> predicted-repair gate must pass independently before any TSC.
>
> The frozen controller has 17 ordered candidates: zero, six non-U/V signed
> axes at scale 1, and U/V scales `0.50/0.75/1.00/1.25/1.50`. It replans at
> `[10,12,14,16,18,22]`, executes only the first robust-formal safe/supported
> exact-Card15 action, then discards the suffix and re-centers on the next
> measured state. Best failing plans are forbidden; every model/support/
> solver/construction fault falls back to the current exact-target hold.
> Offline failure ends with zero TSC. If offline passes, run safety `4` then
> qualification `12` with formal outcomes closed until all raw passes dual
> causal replay.
>
> A real scientific PASS requires at least one real repair among ten failed
> baselines, at least `7/16` formal controller passes, and zero regressions of
> six baseline passes. Even a PASS is only a finite deterministic feedback
> core and still requires all remaining Gate A robustness axes. Gate A and all
> learning remain blocked.

> **Final R8R28 front-loaded cumulative endpoint timing-authority checkpoint
> (2026-08-09 Asia/Shanghai).** Design/implementation/package checkpoints are
> `e4264d1 / 7d8c40d / a31262d`. The exact package contains 1,143 declared
> files plus manifest/sums; manifest and sums SHA-256 are
> `ee7b8774...4597 / c40e78e3...dd9`. Project-venv local source and fresh
> empty direct-copy validation passed 133 JSON parses, 446 Python
> compilations, focused `10/10`, and full Windows-shimmed `1400/1400`.
> Manifest-only direct transfer contained exactly 1,145 physical files and no
> caches. Server staging and installed validation additionally passed 441
> `bash -n` checks and full `1400/1400` with one expected skip, using only the
> existing server virtual environment and no archive.
>
> The accepted server run is
> `stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel_20260809_a31262d_v1`.
> Dual offline paths authenticated R8R7/R8R14/R8R27 and agreed exactly on 64
> specs, 256 major exact-Card15 issues, 1,408 refreshes, maximum issue
> increment `0.1409259259259261`, and maximum predicted current use `0.3905`
> before any TSC. Safety then completed `16/16`, followed only after dual raw
> audit by qualification `48/48`. All 64 trajectories passed full horizon,
> calibration, event, target-chain, source-state/trace prefix, finite,
> current, and forbidden-input gates. The maximum measured current use was
> `0.3924`; there were 256 issues, 1,408 refreshes, and zero forbidden trace
> fields. Safety/qualification raw digests are `6c0bee54...df13 / f95e7cfb...88b`;
> the combined 64-file raw digest is `6ee50ed3...7b7f`. Large raw remains on
> the server and every trajectory is forbidden from learning.
>
> The unchanged evaluator reproduced all 16 R8R7 baselines and 80 saved
> metric rows exactly. Candidate results were g2 UUUU `5/16` with one
> baseline-pass regression, and g2 VVVV, g3 UUUU, g3 VVVV each `6/16` with
> zero regressions. All four repaired `0/10` failed baselines; the held
> baseline-or-candidate oracle remained `6/16`. Failed-context best margin
> gains were `0.0281374667--0.1365572984` (median `0.0912390854`) but none
> crossed the formal boundary. Primary/independent formal outcome, numeric,
> gate, and route agreement was exact with maximum difference `0.0`.
>
> Final route:
> `FRONT_LOADED_ENDPOINT_TIMING_AUTHORITY_INSUFFICIENT_BROADER_CAUSAL_CONTROLLER_REDESIGN_REQUIRED`.
> This is a finite action-timing/controller-family design FAIL, not runtime,
> deployment, source, restart, causality, Card15, current, raw, reporting,
> real-MPC, plant-unreachability, or Gate A evidence. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R28_FORENSIC_REPORT.md`,
> SHA-256
> `5b92791b750f4905313e45985eb2f1eca2a2d931cc7a6c734dc5799a59de5f2c`.
> Compact audit/manifest/sums SHA-256 are `af770eb4...09e / dfe3ba39...aa2e /
> 8595f333...4af8`. R8R28 is immutable and does not authorize another fixed
> schedule scan, a controller, MPC qualification, learning, or Gate A. Before
> any next calculation, implementation, or TSC, freeze a new-identity causal
> visible-state feedback-controller design with hard fallback and independent
> gates.

> **Prospective R8R28 front-loaded cumulative endpoint timing sentinel
> checkpoint (2026-08-09 Asia/Shanghai).** After final R8R27 was sealed at
> `95e17f1`, and before R8R28 implementation, configuration, offline action,
> metric, raw, or TSC, a new real-TSC timing-authority identity was frozen.
> Exact design:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R28_FRONT_LOADED_CUMULATIVE_ENDPOINT_TIMING_AUTHORITY_SENTINEL_DESIGN.md`,
> SHA-256
> `03c714797389872a9388b4ae8acd4711f6d2ad6db074ef25c22075ecbc8af099`.
>
> R8R28 preserves the exact R8R7 0--9 causal source prefix, R8R14 U/V
> endpoint definitions, four cumulative scale-1.0 issues, final cumulative
> coordinate, Card15/action/current/saturation gates, and formal timing. It
> changes only the second-through-fourth major issue times. The complete
> family is `g3=[10,13,16,19]` and `g2=[10,12,14,16]`, each with UUUU and
> VVVV, over all 16 contexts: 64 specs, 256 exact issues, and 1,408 refreshes.
>
> Dual offline construction must pass before any TSC. The frozen execution is
> safety `16` then qualification `48`, with formal outcomes closed until all
> raw passes dual audit. A scientific PASS requires a real repair of at least
> one of ten failed baselines and held baseline-plus-four-candidate oracle
> `>=7/16`; baseline fallback preserves all six passes. Even a PASS authorizes
> only a separately frozen causal feedback-controller design. R8R28 is not
> MPC or Gate A; learning remains blocked and all R8-family trajectories are
> forbidden from learning data. The active task is implementation and dual
> offline preflight under this exact identity.

> **Final R8R27 point-versus-reserve authority checkpoint
> (2026-08-09 Asia/Shanghai).** Design/implementation/initial-package/final-
> package checkpoints are `61ad6a2 / b214b53 / 682a3a8 / 0832c6b`. The
> dependency-complete package has 1,137 declared files plus manifest/sums;
> package manifest and sums SHA-256 are `879f2c12...009c7 / e0960836...c8aa`.
> Local source and a fresh empty direct-copy tree passed 132 strict JSON,
> 443 Python compilations, focused `8/8`, and full Windows-shimmed
> `1390/1390`. Server staging and installed validation additionally passed
> all 440 `bash -n` checks and full `1390/1390` with one expected skip, using
> only the existing server virtual environment and direct unarchived copy.
>
> Three fail-closed validation issues were separated from code/science. One
> local focused command omitted the Windows `resource` shim; the prescribed
> shimmed run passed. The first empty-copy tree exposed a missing packaged
> R8R26 compact dependency; `0832c6b` added the already committed seven-file
> compact source without changing computation. The first server staging tree
> was copied after local tests and contained generated `__pycache__`; exact
> physical-count validation rejected it before install. A new manifest-only
> v2 tree contained exactly 1,139 files and passed all staging/installed
> gates. These are invocation/packaging/transfer errors, not regressions or
> scientific outcomes.
>
> The accepted server run is
> `stage4_2r3c3t13s24d1r14r8r27_point_versus_reserve_authority_discriminator_20260809_0832c6b_v1`.
> It authenticated 432 trajectories, 27 schedules, 1,728 origins, and 11,232
> forecast points. Pair and combined tubes were elementwise identical; pair-
> versus-combined plans and combined-versus-R8R26 plans differed by exactly
> `0.0`.
>
> Every layer completed safe search `16/16`. Pair and combined reserve found
> robust plans `0/16`, repairs `0/10`, and fallback-plus-plan oracle `6/16`.
> Point-only found robust plans `6/16`, but all six were already-passing
> baseline contexts; it likewise repaired `0/10`, regressed `0/6`, and left
> oracle `6/16`. Point selected-violation range was `0--0.9226725021`; pair/
> combined remained `0.2315070911--1.4226725021`. Primary/independent model,
> tube, hull, three-layer plan, R8R26 reproduction, route, and outcome
> differences were all exactly `0.0`.
>
> Final route:
> `POINT_ACTION_TIMING_AUTHORITY_INSUFFICIENT_BROADER_CONTROLLER_REDESIGN_REQUIRED`.
> R8R27 ran zero Ray, `gotsc`, TSC, controller, plant step, raw, or snapshot.
> It is a finite action/timing/controller-family authority FAIL, not runtime,
> restart, reporting, real-MPC, plant-unreachability, or Gate A evidence. No
> controller sentinel or learning is authorized. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R27_FORENSIC_REPORT.md`,
> SHA-256
> `e1eb8cdf3c6585f8d5ac4f950dc32bf59a0c506cb1be727e2be0810474049e2f`.
> Compact evidence/manifest/sums SHA-256 are `1fca0ad5...0473 /
> e335fb77...046b / aa9675a3...9f62`; large detailed plans remain on the
> server. The active boundary is a separately frozen front-loaded causal
> action-timing sentinel. Gate A and all learning remain blocked, and every
> R8-family trajectory remains forbidden from learning data.

> **Prospective R8R27 point-versus-reserve authority discriminator
> checkpoint (2026-08-09 Asia/Shanghai).** After final R8R26 was sealed at
> `71bea5c`, and before any point-only search, plan, formal metric,
> classification, or route was computed, a zero-new-TSC discriminator was
> frozen. Exact design:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R27_POINT_VERSUS_RESERVE_AUTHORITY_DISCRIMINATOR_DESIGN.md`,
> SHA-256
> `3446d1bd81879f52c4f7b943282a2db5c67e6e2d74a43598c597af7c85a7b9f3`.
>
> R8R27 authenticates final R8R26 and reruns the identical 16-context finite
> search under three fixed layers: zero reserve, the immutable R8R25 pair
> tube, and the final R8R26 combined tube. Model, causal state and transition
> support, action boundary, decision timing, lattice, beam, refinement,
> ranking, formal contract, fallback, and independent tolerance do not
> change. The pair and combined layers must be elementwise equal and exactly
> reproduce R8R26 before point-only results are accepted.
>
> A point-only repair routes to uncertainty/excitation redesign; no point-only
> repair routes to a broader causal action/timing/controller family. A
> point-only pass is optimistic and never deployable. R8R27 executes zero
> TSC and cannot authorize a controller, Gate A, expert data, BC, DAgger, or
> RL. The active task is independent implementation and validation of this
> frozen discriminator.

> **Final R8R26 action-transition-supported multiresolution MPC preflight
> checkpoint (2026-08-09 Asia/Shanghai).** Design/implementation/package
> checkpoints are `42c1ff3 / 06ebbf7 / a1f4535`. The 1,124-file package plus
> manifest/sums passed local source and empty-direct-copy checks and server
> staging/installed checks: 125 strict JSON, 440 Python compilations, 439
> `bash -n`, focused `8/8`, and full `1382/1382` with one expected server
> skip. Only project/server virtual environments and unarchived direct copy
> were used. A first staging validation command had a quote-transport
> `SyntaxError` before tests; a standalone validation script then passed all
> gates. This was a validation-command error, not a package or code failure.
>
> The final server run is
> `stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight_20260809_a1f4535_v1`.
> It authenticated 432 trajectories, 27 schedules, 1,728 origins, and 11,232
> forecast points. All 27 leave-one-schedule-out folds passed: maximum
> R/Z/Ip/vR/vZ errors were `0.000939737 m / 0.001635735 m / 86.3158 A /
> 0.0145526 m/s / 0.0178840 m/s`, and containment was
> `56,160/56,160`. The schedule tube did not enlarge the immutable pair tube;
> final half-widths stayed `[0.015 m, 0.015 m, 3000 A, 0.05 m/s,
> 0.0538796472 m/s]`.
>
> Transition hull ranks/counts were `[2,3,3,3] / [13,15,15,15]`. All 16
> deterministic searches completed with zero state-unsupported nodes, but
> robust-formal plans were `0/16`; repairs were `0/10`, hybrid regressions
> `0/6`, and fallback-plus-plan oracle `6/16`. Best robust violation ranged
> `0.2315070911--1.4226725021`. Primary/independent source, schedule, hull,
> plan, route, and outcome differences were all exactly `0.0`. Final route:
> `ACTION_TRANSITION_SUPPORTED_MULTIRESOLUTION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED`.
>
> R8R26 executed zero Ray, `gotsc`, TSC, controller, plant, raw, or snapshot.
> It is a finite supported action-family/planning-authority FAIL, not a
> runtime, deployment, restart, reporting, real-MPC, global-unreachability,
> or Gate A result. No fresh controller sentinel or learning is authorized;
> all R8-family evidence remains forbidden from learning. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R26_FORENSIC_REPORT.md`,
> SHA-256
> `aeca922d442e2576c51dd1fb77423477c73692d483dece738e7ff51d8114d63e`.
> Compact audit SHA-256 is
> `1a5ab3e05f841ff55af75314ec89d2e4a033a574381d1b0047f1b4b3322b0cb4`.
>
> Before any new calculation or plant work, freeze a new-identity zero-TSC
> point-versus-reserve authority discriminator using the unchanged finite
> search under point-only, pair-tube, and combined-tube layers. Its result
> may route uncertainty/excitation versus action/timing redesign only; it
> cannot authorize a controller, MPC, Gate A, expert data, BC, DAgger, or RL.

> **Prospective R8R26 action-transition-supported multiresolution MPC
> preflight checkpoint (2026-08-09 Asia/Shanghai).** After final R8R25 was
> sealed at `ad6df5c`, and before any R8R26 schedule-held-out error, tube,
> hull, search, plan, formal metric, or route was computed, a zero-new-TSC
> redesign was frozen. Exact design:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R26_ACTION_TRANSITION_SUPPORTED_MULTIRESOLUTION_MPC_PREFLIGHT_DESIGN.md`,
> SHA-256
> `d79f64712b00c923711b5bac16f6001388edeb3e348c2b71b7c98c942289f853`.
>
> R8R26 retains the exact R8R25 all-eight point model and pair-jackknife tube,
> adds 27 leave-one-whole-schedule-out fits and a no-clipping schedule tube,
> and takes their componentwise maximum. A finite 325-level sixteenth-unit
> triangular U/V lattice is allowed only inside the interval-specific affine
> and convex hull of observed `(previous_q,q)` transitions and the unchanged
> causal state-support boundary. Every candidate still passes exact Card15,
> action, current, saturation, finite, and stop-before-advance checks.
>
> Search is prospectively fixed to a 33-level coarse set, beam width 256, 32
> terminal seeds, and deterministic `2/16` then `1/16` coordinate refinement.
> Robust-formal plans have strict priority. If none exists, the causal policy
> falls back to the frozen baseline continuation; it may never deploy the
> best failing plan or use a source outcome label. A PASS still requires at
> least one predicted repair, zero hybrid regressions, and oracle `>=7/16`,
> and authorizes only design of a fresh safety-first controller sentinel.
> R8R26 is not Gate A and all learning remains blocked. The active task is
> independent implementation and validation of this frozen zero-TSC design.

> **R8R25 final training-cardinality-matched outer-jackknife checkpoint
> (2026-08-09 Asia/Shanghai).** Design/clarification/initial implementation
> checkpoints are `cc0dee5 / e37f84f / 9089006`. The initial package
> `d5c784e` passed all deployment validation, but its first primary attempt
> stopped before producing scientific output because a legitimate empty
> single-pair group in the frozen 13/15-sample final-horizon mask had NumPy
> shape `(0,)`. The failed stage contains zero files and its traceback is
> preserved. This was an implementation/data-shape error, not a model,
> control, TSC, or plant result.
>
> Hotfix/package checkpoints `6c5990c / f5094fe` normalize only an empty
> per-pair group to `(0,5)` while retaining nonempty finite cross-pair
> calibration. No scientific rule changed. The 1,118-file package passed
> local source and empty-direct-copy plus server staging/installed hashes,
> 124 JSON parses, 437 Python compilations, 438 `bash -n` checks, focused
> `10/10`, and full `1374/1374` with one expected skip. Only project/server
> virtual environments and direct unarchived transfer were used.
>
> The valid run authenticated 432 trajectories, 1,728 causal origins, and
> 11,232 forecast points. Source point-model and support reproduction
> differences were all `0.0`. Maximum R/Z/Ip/vR/vZ point errors were
> `0.00115977 m / 0.00325191 m / 75.222 A / 0.0177882 m/s /
> 0.0431037 m/s`; support passed `1728/1728`. The cross-outer tube contained
> `56,160/56,160` components and its maximum physical half-widths were
> `[0.015 m, 0.015 m, 3000 A, 0.05 m/s, 0.0538796472 m/s]`. Every point,
> containment, cap, support, finite, and forbidden-input gate passed.
>
> The model PASS opened the full eleven-level four-decision tree. All 16
> contexts had all `14,641` sequences safely complete and zero unsupported
> nodes, but no context had any robust-formal sequence. Predicted repairs were
> `0/10`, forced-plan regressions `6/6`, and baseline-plus-policy oracle stayed
> `6/16`. Primary and structurally independent model/tube/plan/source/route
> differences were exactly `0.0`. Final route:
> `TRAINING_CARDINALITY_MATCHED_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED`.
>
> R8R25 is a finite consumed-development-bank model/uncertainty PASS followed
> by an action-family/planning-authority FAIL. It executed zero Ray, `gotsc`,
> TSC, controller, plant advance, raw, or snapshot and is not real-MPC,
> plant-unreachability, or Gate A evidence. Exact report SHA-256 is
> `3b2fbcfa6435a5d8039ede9a4f305589d4299cb9a5117524d990aba9b18bec2a`;
> final compact SHA is `ecfbbe93...78bb8`. A fresh controller sentinel and
> all learning remain blocked. Before further computation or plant work,
> freeze a new-identity causal action-family/controller redesign.

> **R8R24 final causal local-residual-tube preflight checkpoint
> (2026-08-09 Asia/Shanghai).** Design/implementation/package checkpoints are
> `218e176 / 484f2a9 / 4b22492`. The 1,112-file package passed all hashes, 123
> JSON parses, compilation of 434 Python files, focused `8/8`, and full
> Windows-shimmed `1364/1364` locally and in a fresh empty direct-copy tree.
> Server staging and installed validation passed the same gates plus `bash -n`
> for all 437 shell files, with one expected isolated-evidence skip. Only the
> project and existing server virtual environments were used; no archive was
> created or extracted.
>
> R8R24 authenticated 432 immutable trajectories, 1,728 causal decision
> origins, and 11,232 forecast points. It exactly reproduced the R8R23 cold
> outer models, point metrics, and support with maximum differences `0.0`.
> Point errors remained below all caps, support passed `1728/1728`, and there
> were zero finite exclusions or forbidden inputs.
>
> The prospectively frozen same-interval/same-lead local residual rule used
> Euclidean 133D distance, `k=32` with all kth-distance ties, component maxima
> times `1.25`, fixed physical floors, and no clipping. It repaired containment
> from R8R23's `0.970388...` to `56,160/56,160 = 1.0`, but maximum vR/vZ
> half-widths remained `0.105299280302 / 0.181854519985 m/s`, above the
> unchanged `0.08` caps. The tube-cap gate therefore failed.
>
> Planning stayed closed. Zero plans/repairs and oracle `6/16` are fail-closed
> sentinel values, not controller evidence. Structurally independent fit,
> tube, plan, source-reproduction, outcome, and route agreed exactly with all
> maximum differences `0.0`. R8R24 executed zero Ray, `gotsc`, TSC,
> controller, plant advance, raw, or snapshot. Final route:
> `CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED`.
>
> This is a finite causal uncertainty-design FAIL, not runtime, deployment,
> source, restart, causality, reporting, real-MPC, Gate A, authority, or global
> reachability evidence. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R24_FORENSIC_REPORT.md`,
> SHA-256
> `23e23051fc0fef84d57d3a5f37b9031e9c1dfab7f07b972e05a6fb12359318ca`.
> Final detailed/summary/independent/report/model/manifest/state hashes are
> `0a795a08... / af587377... / a48e45fb... / 581d6e7c... /
> 06189773... / 6bcb93d3... / a9129cb0...`. The compact audit SHA is
> `90f0b6e3...48edc`; the 7.22 MB model remains on the server.
>
> R8R24 is immutable. Before any new uncertainty calculation or controller
> execution, freeze a separate new-identity causal model/uncertainty redesign.
> No R8-family TSC trajectory may be rerun or enter expert, BC, DAgger,
> residual-RL, or other learning data. Gate A remains blocked.

> **R8R23 final causal online-feedback preflight checkpoint
> (2026-08-09 Asia/Shanghai).** Design/implementation/package checkpoints are
> `0f61d94 / c4af11d / 7b2739c`. The 1,106-file package passed all hashes,
> 122 JSON parses, compilation of 431 Python files, focused `6/6`, and full
> Windows-shimmed `1356/1356` locally and in an empty direct-copy tree.
> Server staging and installed validation passed the same gates plus `bash -n`
> for all 436 shell files, with one expected isolated-evidence skip. Only the
> project and existing server virtual environments were used; no archive was
> created or extracted.
>
> Dual zero-new-TSC implementations authenticated 432 immutable source
> trajectories and independently rebuilt 1,728 causal decision origins and
> 11,232 forecast points under eight leave-whole-physical-pair-out folds.
> Feature and target digests are `14e1a15c...e849 / 037be84f...dcc`; support
> passed `1728/1728`, and there were zero forbidden inputs or finite
> exclusions. All point-error caps passed, with R/Z/Ip/vR/vZ maxima
> `0.00115977 m / 0.00325191 m / 75.222 A / 0.0177882 m/s /
> 0.0431037 m/s`.
>
> The frozen conservative model gate failed. The reserved tube contained
> `54,497/56,160 = 0.9703881766381767`, below the required `1.0`; maximum vR
> and vZ half-widths were `0.106771340225 / 0.183859708965 m/s`, above the
> unchanged `0.08` caps. The optional already-observed innovation update also
> failed: adapted/cold squared-error ratio `1.2263836369504335`, only `1/8`
> physical pairs improved, and 94 rows clipped. Innovation was therefore
> disabled and the cold predictor selected.
>
> The model failure kept the 11-level action tree closed. Zero safe plans,
> zero predicted repairs, and oracle `6/16` are fail-closed sentinel values,
> not controller or authority outcomes. Primary and structurally independent
> feature/fit/tube/plan/outcome/route results agreed exactly; maximum fit and
> tube differences were both `0.0`. R8R23 executed zero Ray, `gotsc`, TSC,
> controller, plant advance, raw, or snapshot. Final route:
> `CAUSAL_ONLINE_FEEDBACK_MODEL_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED`.
>
> This is a finite causal model/uncertainty-design FAIL, not runtime,
> deployment, source, restart, causality, reporting, real-MPC, Gate A,
> action-authority, or global reachability evidence. Final detailed/summary/
> independent/report/manifest/state/model hashes are `a40a9b89... /
> 4d900b3c... / af1b419b... / 3d1c88ac... / 2f3aef0b... /
> bd55964f... / 9bc1e2a0...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R23_FORENSIC_REPORT.md`,
> SHA-256
> `20168a98ec3117dd0b8cf0c7979dfd97bfe13db3f8da4bbeb0dff8f231b89b07`.
> The local compact audit SHA is `70d8c861...d59e`; the 7.22 MB model remains
> on the server and no raw was downloaded.
>
> R8R23 is immutable. Before any further output or controller execution,
> freeze a new-identity causal model/local uncertainty redesign. Any use of
> the consumed R8R23 bank is development only, never a fresh holdout or
> learning data. A model-design PASS may authorize only a separately frozen
> fresh finite real-controller sentinel. Gate A and all learning remain
> blocked.

> **R8R22 final bounded continuous-multidirection authority checkpoint
> (2026-08-09 Asia/Shanghai).** Design/initial implementation/initial package
> checkpoints are `d2627e3 / f08f498 / f9d19c1`. A reporting-only source-
> count hotfix and its package are `cd5c092 / fbfe431`. The 1,100-file
> package passed exact hashes, compilation, focused `12/12` then hotfix
> `13/13`, and full `1349/1349` then hotfix `1350/1350` locally, in empty
> direct-copy trees, in server staging, and after installation; all 435 shell
> files passed `bash -n`, with one expected isolated-evidence skip where
> applicable. No archive or global Python was used.
>
> R8R22 completed 160/160 authentic trajectories. Dual raw audits passed all
> runtime, full-horizon, restart/source-prefix state/trace, causality,
> calibration, candidate, exact target-chain, event, Card15, action, current,
> finite, forbidden-input, and inventory gates. Safety was `40/40` and
> qualification `120/120`; there were 640 exact issues and 3,520 refreshes.
> Maximum issue/refresh/current values were `0.2111111111111112 /
> 3.7037037048793097e-06 / 0.3924`. Safety raw is
> `40 / 1312632 bytes / 50a3ee18...885`; qualification raw is
> `120 / 3959765 bytes / ee2d1595...dab`.
>
> The first formal-primary attempt stopped before computing any metric because
> its R8R20 loader incorrectly required 160 source rows rather than the exact
> `6 codes * 16 contexts = 96`. Independent code and source evidence already
> used 96. Hotfix `cd5c092` changed only that reporting constant and added a
> dual 96-row regression test. All 160 raw were preserved; zero Ray, `gotsc`,
> TSC, controller, or plant steps were rerun. This was a reporting error, not
> a scientific or control failure.
>
> Corrected formal evaluation reproduced 432 rows exactly with maximum old-
> evaluator margin difference `0.0`. Baseline remained `6/16`. Nine new
> candidates passed `6/16`; `a1p50_w1p00` passed `5/16` and regressed one
> prior pass. New rows totaled `59/160`, but repaired `0/10` failed baselines,
> so the baseline-plus-new oracle remained `6/16`. Failed-context best margin
> gains were all positive: `0.03576556666666786--0.1759552514673881`, median
> `0.1249930059791512`. Primary/independent route, outcome, and numbers agreed
> exactly. Final route:
> `BOUNDED_CONTINUOUS_MULTIDIRECTION_AUTHORITY_INSUFFICIENT_ONLINE_FEEDBACK_MODEL_REDESIGN_REQUIRED`.
>
> This is a finite fixed-action-family authority FAIL, not runtime, restart,
> causality, raw, reporting, real-MPC, Gate A, or global reachability evidence.
> Before qualification/formal outcomes were opened, R8R23 causal online-
> innovation receding-horizon preflight was frozen at `0f61d94`, design SHA
> `fc06e9cf...d6b6d`; the exact FAIL route now activates that zero-new-TSC
> preflight. Final detailed/summary/independent/report/manifest/state hashes
> are `bc71fcd4... / 3db48da6... / c8663896... / 933263c6... /
> c8bbe57d... / 8b0566d3...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R22_FORENSIC_REPORT.md`,
> SHA-256
> `fdeef92777373090e4a170d7b971a132cee36019aff99b237396f3b21efdbe67`.
> All R8-family data remain forbidden from learning; Gate A remains blocked.

> **R8R20 final direct Boolean-cube completion checkpoint
> (2026-08-08 Asia/Shanghai).** Design/implementation/package checkpoints are
> `f13e88a / ad64f09 / 98c67c5`. The 1,094-file package passed exact hashes,
> JSON, compilation, focused `11/11`, and full `1337/1337` locally, in the
> empty direct-copy tree, in server staging, and after installation; server
> shell syntax passed and one isolated-evidence skip was expected. No archive
> or global Python was used.
>
> The first `_v1` safety launch suffered an SSH-session/result-persistence
> interruption after 24 TSC tasks had started. They completed without any
> persisted Python raw; the run and its workspaces are preserved and forbidden
> from scientific or learning use. Before outcomes were inspected, checkpoint
> `9921657` froze the incident and authorized one byte-identical clean `_v2`.
> This was an infrastructure failure, not a control result.
>
> Valid v2 completed 96/96 authentic trajectories. Dual raw audits passed all
> runtime, full-horizon, source-prefix state/trace, calibration, sequence,
> exact target-chain, event, Card15, action, current, finite, forbidden-input,
> and inventory gates. Safety was `24/24`, qualification `72/72`; there were
> 384 exact issues and 2,112 refreshes. Maximum issue/refresh/current values
> were `0.1409259259259258 / 3.7037037048793097e-06 / 0.3924`.
> Safety raw is `24 / 795803 bytes / a540618b...9cd`; qualification raw is
> `72 / 2405436 bytes / 546a4275...f989`.
>
> Formal evaluation then found every one of the sixteen U/V codes passed the
> same `6/16` baseline contexts and repaired `0/10` failures. The complete-
> cube oracle remained `6/16`, below the frozen `>=7/16` gate. Every failed
> context nevertheless had positive best margin gain
> `0.025541733333334093--0.1364830983921772` (median
> `0.08895878160707882`). Independent recomputation agreed exactly, with
> maximum margin difference `0.0`. Final route:
> `DIRECT_BOOLEAN_CUBE_AUTHORITY_INSUFFICIENT_CONTINUOUS_MULTIDIRECTION_REDESIGN_REQUIRED`.
>
> This is a finite binary-action-family authority FAIL, not runtime,
> deployment, restart, causality, raw, reporting, real-MPC, Gate A, global
> reachability, or wrong-direction evidence. The conditionally frozen R8R21
> action-tree selector (`fdf196c`, design SHA `781df71a...d734`) is vetoed
> without implementation/output because it required an R8R20 PASS. The active
> route is a separately frozen bounded continuous-multidirection redesign.
> Primary/detailed/independent/manifest/compact hashes are
> `ccff5a7e... / 0d30684c... / 6abbbaec... / 0bbaedd0... /
> b5663a12...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R20_FORENSIC_REPORT.md`,
> SHA-256
> `d7a86439b31d5d71f94ff96e05f8260e7503f20981660f4aae4e9866516be7ea`.
> All R8-family data remain forbidden from learning; Gate A remains blocked.

> **Prospective R8R20 direct Boolean-cube completion sentinel
> (2026-08-08 Asia/Shanghai).** After final R8R19 evidence, route, and report
> were sealed, but before any R8R20 implementation, construction, raw, TSC,
> or formal output, the design was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R20_DIRECT_BOOLEAN_CUBE_COMPLETION_AUTHORITY_SENTINEL_DESIGN.md`,
> SHA-256
> `8b49ef5f49d15b994cc4fc8b1a94313fa2782c297f98a31863e35e6886f1c07c`.
>
> The closed matrix is exactly the six unmeasured codes
> `UVUU,UUVU,UVVU,VUUV,VVUV,VUVV` over the same sixteen authentic contexts.
> Dual offline construction covers 96 specs, 384 exact issues, and 2,112
> stored-target refreshes under unchanged R8R15 Card15/action/current gates.
> Safety is prospectively fixed at four contexts times six codes (`24`);
> only complete dual raw agreement may authorize the remaining `72`.
>
> Formal evaluation stays closed until all 96 physical rows pass integrity.
> A scientific PASS requires at least one of ten baseline-failure repairs and
> complete-cube held oracle `>=7/16` under the unchanged 250/270 ms arrival
> and 350/370 ms hold contract. R8R20 is finite authority identification, not
> MPC or Gate A. All R8-family trajectories remain forbidden from learning.

> **R8R19 final saturated Boolean-kernel LOCO checkpoint
> (2026-08-08 Asia/Shanghai).** Design/implementation/package checkpoints are
> `f4c842b / e62c563 / 51b429a`. The 1,087-file package passed hashes, JSON,
> compilation, focused `9/9`, and full `1326/1326` locally and in the empty
> direct-copy tree. Server staging and installed validation additionally
> passed every hash and shell `bash -n`, with one expected isolated-evidence
> skip where applicable. No archive or global Python was used.
>
> Dual zero-new-TSC audits authenticated final R8R15--R8R18 evidence. All
> code-only rank, condition, weight, point-error, classification, and tube
> gates passed. Formal classification was `160/160`, but the fixed model
> passed only `156/160` LOCO rows because maximum minimum-margin error was
> `0.06413974895404673 > 0.05`. Maximum scaled point error was only
> `0.006226528571431423`. Primary augmented SVD and independent normal-
> equation solves agreed with maximum difference `7.105427357601002e-14`.
>
> R8R19 ran zero TSC, controller, plant step, raw, or snapshot. The authority
> phase was not opened. The final route is
> `SATURATED_BOOLEAN_KERNEL_MODEL_INADEQUATE_DIRECT_CUBE_COMPLETION_REDESIGN_REQUIRED`.
> Detailed/summary/independent/final/manifest/state/evidence hashes are
> `0f4980f4... / eca8813d... / b527acd0... / 73249b2c... /
> c9ef5908... / ad726417... / 1be9e2a6...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R19_FORENSIC_REPORT.md`,
> SHA-256
> `7cecea2eefc36991bde612452bcf3cc0cac5f9f34b2a1c778825f08ffdf5c939`.
>
> This is a finite model-design FAIL, not runtime, deployment, source, raw,
> restart, causality, reporting, controller, plant, real-MPC, Gate A, or
> global reachability. The active boundary is a separately frozen direct
> physical completion of the six missing Boolean sequences over the same
> finite contexts. Learning remains blocked and every R8-family trajectory
> remains forbidden from learning data.

> **Prospective R8R19 saturated Boolean kernel LOCO preflight
> (2026-08-08 Asia/Shanghai).** After final R8R18 evidence and route were
> sealed, but before any R8R19 response fit or output, the new zero-TSC design
> was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R19_SATURATED_BOOLEAN_KERNEL_LOCO_PREFLIGHT_DESIGN.md`,
> SHA-256
> `e0d8529512da14e144c3dfa7502ccc905a59b4f7cdef8ff9e73fc7cf927bdb25`.
>
> The finite nonparametric prior is the complete 16-feature Walsh map of the
> four-slot Boolean cube. Affine terms are unpenalized and all 11 degree-2--4
> terms use one code-only penalty `lambda=10`, fixed as the first closed-grid
> value meeting LOCO condition `<=64` and weight L2 `<=1.25`. No R8R18 row
> identity, residual, response state, or formal metric selected the model.
>
> All ten measured codes remain in a 160-row LOCO gate under the unchanged
> physical, formal-margin `0.05`, classification, and tube caps. Only a dual
> `160/160` PASS opens the same six closed missing-code predictions and the
> unchanged robust-authority gate. R8R19 runs zero TSC and can authorize only
> a separately frozen physical sentinel. It is not MPC or Gate A; learning
> remains blocked and all R8-family evidence remains forbidden from learning.

> **R8R18 final second-order Boolean ridge LOCO checkpoint
> (2026-08-08 Asia/Shanghai).** Design/implementation/package checkpoints are
> `1366017 / 7dae75a / e5003f5`. The 1,080-file package passed hashes, JSON,
> compilation, focused `9/9`, and full `1317/1317` locally and in the empty
> direct-copy tree. Server staging and installed validation additionally
> passed every hash and shell `bash -n`, with one expected isolated-evidence
> skip where applicable. The first install copy loop had a checksum-line
> parsing error after its restricted deletion; the exact validated staging
> tree restored the installation immediately, after which 1,080/1,080 hashes
> and the complete suite passed. No output, raw, or virtual environment was
> touched. This was a recovered deployment-script error, not a regression.
>
> Dual zero-new-TSC audits authenticated final R8R15/R8R16/R8R17 evidence.
> All code-only rank, condition, weight, point-error, classification, and tube
> gates passed. Formal classification was `160/160`, but the fixed model passed
> only `157/160` LOCO rows because maximum minimum-margin error was
> `0.05685241823211573 > 0.05`. Maximum scaled point error was only
> `0.0061002004751214535`. Primary augmented SVD and independent normal-
> equation solves agreed with maximum difference `8.881784197001252e-15`.
>
> R8R18 ran zero TSC, controller, plant step, raw, or snapshot. The authority
> phase was not opened. The final route is
> `SECOND_ORDER_BOOLEAN_RIDGE_MODEL_INADEQUATE_NONPARAMETRIC_SEQUENCE_REDESIGN_REQUIRED`.
> Detailed/summary/independent/final/manifest/state hashes are
> `d3b71fcf... / d67f2080... / b53cb993... / cfc5c381... /
> 50b9842d... / 660efeae...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R18_FORENSIC_REPORT.md`,
> SHA-256
> `22560269b6716e695c6a6c110536de5bc4765dd6d476755721e501625ca9ec1d`.
>
> This is a finite model-design FAIL, not runtime, source, raw, restart,
> causality, reporting, formal-evaluator, controller, plant, real-MPC, Gate A,
> or global reachability. A new-identity nonparametric sequence model must be
> frozen before computing its outputs. Learning remains blocked and every
> R8-family trajectory remains forbidden from learning data.

> **Prospective R8R18 second-order Boolean ridge LOCO preflight
> (2026-08-08 Asia/Shanghai).** After sealing aggregate R8R17 but before
> inspecting any failed-row identity or detailed residual, the zero-new-TSC
> design was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R18_SECOND_ORDER_BOOLEAN_RIDGE_LOCO_PREFLIGHT_DESIGN.md`,
> SHA-256
> `f7de518d1bc65588883d245eb7fd1de5f63b84c679713b38102db6047d28ab9d`.
>
> The fixed model has intercept, four slot signs, and all six pair
> interactions. Affine terms are unpenalized; pair terms use `lambda=10`,
> selected only from a closed code-geometry grid. All ten measured codes are
> validated by ten leave-one-code-out folds, exactly 160 held trajectories.
> Every `160/160` must pass unchanged R8R16/R8R17 physical, formal margin
> `0.05`, classification, and tube gates. Code-only stability caps include
> LOCO normal condition `<=32` and prediction-weight L2 `<=1.30`.
>
> Only a dual LOCO PASS opens predictions for the same six never-executed
> codes; robust authority remains `>=1/10` repairs and oracle `>=7/16` after
> the frozen uncertainty buffer. R8R18 runs zero TSC and may authorize only a
> separately frozen physical sentinel. It is not MPC or Gate A; learning
> remains blocked and all R8-family evidence remains forbidden from learning.

> **R8R17 final adjacent-switch interaction checkpoint
> (2026-08-08 Asia/Shanghai).** Design/implementation/package checkpoints are
> `614487a / 6b62ca6 / d7d291a`. The 1,073-file package passed hashes, JSON,
> compilation, focused `9/9`, and full `1308/1308` locally and in the empty
> direct-copy tree. Server staging and installed validation additionally
> passed real `bash -n` for every declared shell file, with one expected
> isolated-evidence skip where applicable. No archive or global Python was
> used.
>
> Dual zero-new-TSC audits authenticated final R8R15 and R8R16 evidence. All
> frozen rank/condition and tube gates passed; formal classification was
> `64/64`, but held calibration passed only `61/64`. Maximum minimum-margin
> error was `0.09336026574612744 > 0.05`, while maximum scaled point error was
> `0.008405966666665465`. Primary SVD and independent `lstsq` agreed on route
> and outcome with maximum difference `2.1316282072803006e-14`.
>
> R8R17 ran zero TSC, controller, plant step, raw, or snapshot. The final
> route is
> `ADJACENT_SWITCH_INTERACTION_MODEL_INADEQUATE_HIGHER_ORDER_REDESIGN_REQUIRED`.
> Detailed/summary/independent/final/manifest/state hashes are
> `b57f2afc... / da1c108b... / 2a5e8d30... / f87fba9b... /
> e0e850c3... / 6b16d1ad...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R17_FORENSIC_REPORT.md`,
> SHA-256
> `0162fa79e7fea0cb5ba8ef309eabed6be387341436b02c09e490b3426157852a`.
>
> This is a finite nonlinear model-design FAIL, not runtime, deployment,
> source, raw, restart, causality, reporting, formal-evaluator, controller,
> plant, physical-authority, real-MPC, Gate A, or global reachability. The
> active boundary is a separately frozen higher-order model with ten-code
> leave-one-code-out validation chosen without failed-row identity. Learning
> remains blocked and all R8-family evidence remains forbidden from learning.

> **Prospective R8R17 adjacent-switch interaction preflight
> (2026-08-08 Asia/Shanghai).** After sealing R8R16 but before inspecting its
> failed-row identity or any new fit/output, the zero-new-TSC R8R17 design was
> frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R17_ADJACENT_SWITCH_INTERACTION_BINARY_CUBE_PREFLIGHT_DESIGN.md`,
> SHA-256
> `5432fe3f292800910dc8f70e979fc4db89ffee3fa6053ad22383b9029ebc73d0`.
>
> R8R17 retains the exact R8R16 split and caps, adding only
> `a=(q10*q14+q14*q18+q18*q22)/3` to the fixed feature row. Code-only
> development/measured/full-cube geometry is frozen at rank-condition
> `6/6.6990427629`, `6/2.6131259298`, and `6/1.7320508076`. No R8R16
> per-code/context/state residual was used to select the feature.
>
> All `64/64` held calibration trajectories must meet the unchanged R8R16
> point, component, formal classification, minimum-margin `0.05`, and tube
> gates before the same six missing codes may be predicted. Robust authority
> remains `>=1/10` repairs and oracle `>=7/16` after the frozen two-times
> margin buffer. R8R17 runs zero TSC and can authorize only a separately
> frozen physical sentinel. It is not MPC or Gate A; learning remains blocked
> and all R8-family evidence remains forbidden from learning data.

> **R8R16 final temporal-affine completion preflight checkpoint
> (2026-08-08 Asia/Shanghai).** Design/implementation/package checkpoints are
> `d68aae4 / d7364e8 / e2325b0`. The 1,066-file empty direct-copy package
> passed exact hashes, JSON, shell syntax, compilation, focused `9/9`, and
> full `1299/1299` tests locally, in the empty copy, in server staging, and
> after installation, with one expected isolated-evidence skip where
> applicable. No archive or global Python was used.
>
> The zero-new-TSC primary and structurally independent audits authenticated
> the exact R8R15 source hashes and safety/qualification inventories. Both
> frozen matrices passed rank/condition (`5 / 3.1861406616` and
> `5 / 2.6131259298`), and the fixed tube passed. Held calibration reproduced
> formal classification `64/64` but passed every numerical gate only `63/64`:
> maximum minimum-formal-margin error was `0.05171944884413282`, above the
> frozen `0.05` cap. Maximum scaled point error was
> `0.004582066666663117`; component maxima were `0.137462 mm R / 0.108346 mm
> Z / 12.6991 A Ip`.
>
> Primary explicit-SVD and independent `lstsq` results agree in route and
> outcome with maximum numerical difference `5.329070518200751e-15`. The
> missing-six authority phase remained closed: its zero baseline/repair/
> oracle fields are sentinel values, not measured outcomes. R8R16 created
> zero TSC, controller step, plant step, raw, or snapshot. All seven compact
> JSON files (70,474 bytes) strictly parse and reproduce server hashes.
>
> The final route is
> `TEMPORAL_AFFINE_SEQUENCE_MODEL_INADEQUATE_NONLINEAR_SEQUENCE_REDESIGN_REQUIRED`.
> Detailed/summary/independent/final/manifest/state hashes are
> `5f8605e4... / be9a7b96... / 8f73d31d... / f17c4338... /
> 605b98ce... / 7b667943...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R16_FORENSIC_REPORT.md`,
> SHA-256
> `55da4885d8d886f9a28b525685b8a9d6665dd841f1186007b7fb054cd786df47`.
>
> R8R16 is a finite affine sequence-model design FAIL, not a runtime,
> deployment, source, raw, restart, causality, reporting, formal-evaluator,
> controller, plant, physical-authority, real-MPC, Gate A, or global-
> reachability result. It is immutable. The active boundary is a separately
> frozen nonlinear sequence-model redesign with unchanged held calibration
> and no relaxation of the observed `0.0517194488` miss. All R8-family
> trajectories remain forbidden from learning, and Gate A remains blocked.

> **Prospective R8R16 temporal-affine binary-cube completion preflight
> (2026-08-08 Asia/Shanghai).** Before R8R16 implementation, fitting,
> calibration output, missing-code prediction, ranking, formal result, or
> route, the zero-new-TSC model design was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R16_TEMPORAL_AFFINE_BINARY_CUBE_COMPLETION_PREFLIGHT_DESIGN.md`,
> SHA-256
> `2b48e9d6e74222977db1af687009f031aac3da90e9e6b008a856412cc119367b`.
>
> The five-parameter model uses fixed code features
> `[1,q10,q14,q18,q22]`. Development is frozen to
> `UUUU,VVVV,UVVV,UUVV,UUUV,VUUU`; already measured
> `VVUU,VVVU,UVUV,VUVU` are fixed retrospective calibration only. The exact
> six never-executed codes are `UVUU,UUVU,UVVU,VUUV,VVUV,VUVV`. Calibration
> must pass all `64/64` trajectory point/formal gates under fixed physical
> caps; missing-code authority is discounted by twice the maximum calibration
> formal-margin error.
>
> R8R16 runs zero Ray, `gotsc`, TSC, controller, plant step, or snapshot. A
> PASS requires at least one robust predicted repair and robust oracle
> coverage `>=7/16`, and authorizes only a separately frozen fresh physical
> sentinel. A calibration failure routes to nonlinear sequence redesign; an
> adequate model with no robust repair routes to continuous multidirection
> redesign. R8R16 is not MPC or Gate A, all R8-family trajectories remain
> forbidden from learning, and Gate A remains blocked.

> **R8R15 final binary temporal-switching staircase checkpoint
> (2026-08-08 Asia/Shanghai).** Design/implementation/package checkpoints are
> `e3d5302 / 222f5d5 / f23c96e`. The 1,059-file empty direct-copy package
> passed exact hashes, compilation, focused `11/11`, and full `1290/1290`
> tests locally, in the empty copy, in server staging, and after installation,
> with one expected isolated-evidence skip where applicable. `bash -n` and
> compilation of 410 installed Python files also passed. No archive or global
> Python was used.
>
> Dual offline construction agreed exactly on `128/128` specs, `512/512`
> exact Card15 issues, and `2816/2816` stored-target refreshes. The 32 safety
> trajectories completed and passed exact primary/independent raw agreement
> before the 96 qualification trajectories were authorized. All `128/128`
> authentic trajectories passed runtime, full-horizon, physical-prefix,
> calibration, event, target-chain, action, current, finite-state, forbidden-
> input, and raw-integrity gates. Safety raw is `32 files / 1059431 bytes /
> 7d7a2b4f...`; qualification raw is `96 files / 3201665 bytes /
> a909e034...`. Maximum measured current use was `0.3924`, there were zero
> forbidden trace rows, no snapshot, and R8/R8R1/R8R12/R8R14 were not rerun.
>
> Formal evaluation reproduced baseline, immutable R8R12 `UUUU`, and
> immutable R8R14 `VVVV` at `6/16`. Every one of the eight new sequences
> (`UVVV,UUVV,UUUV,VUUU,VVUU,VVVU,UVUV,VUVU`) also passed exactly `6/16`,
> repaired `0/10` failed baselines, and regressed `0/6` baseline passes. The
> failed-context best minimum-margin gain was positive at
> `0.0255417333 / 0.0889587816 / 0.1364830984` min/median/max, but every best
> margin remained negative and the held oracle stayed `6/16`. Primary and
> the structurally independent formal implementation agree exactly, with
> maximum metric difference zero.
>
> The final route is
> `BINARY_TEMPORAL_SWITCHING_STAIRCASE_AUTHORITY_INSUFFICIENT_MODEL_BASED_SEQUENCE_REDESIGN_REQUIRED`.
> Summary/independent/final/manifest/state/compact hashes are `2c5b7e10... /
> cf896933... / cd1c3758... / 3d704e41... / 71d4a0d3... / cdba408f...`.
> Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R15_FORENSIC_REPORT.md`,
> SHA-256
> `ca51f7f7b9791199796e923704da84355b1ac5eb9c2669900165962d5a7fc04c`.
>
> R8R15 is a finite binary open-loop temporal-basis design FAIL, not a
> runtime, deployment, restart, causality, Card15, current, raw, reporting,
> formal-evaluator, safety, plant, real-MPC, Gate A, or global-reachability
> result. It is immutable. The active boundary is a separately frozen model-
> based sequence redesign with explicit evidence separation and unchanged
> hard contracts. All R8-family trajectories remain forbidden from learning,
> and Gate A remains blocked.

> **Prospective R8R15 binary temporal-switching staircase authority sentinel
> (2026-08-08 Asia/Shanghai).** Before R8R15 implementation, config, offline
> construction, raw, TSC, formal outcome, or route, the new temporal sequence
> basis was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R15_BINARY_TEMPORAL_SWITCHING_STAIRCASE_AUTHORITY_SENTINEL_DESIGN.md`,
> SHA-256
> `bc0651d9c07f25c961bb5251ab508bda45ddc611d2b32f052ea0592cfe938bfe`.
>
> The frozen symbols are `U=(direction 2,+1)` and `V=(direction 1,-1)` at
> scale 1.0 and decision steps `[10,14,18,22]`. Immutable R8R12 `UUUU` and
> R8R14 `VVVV` are reused without rerun. The eight new globally fixed codes
> are `UVVV, UUVV, UUUV, VUUU, VVUU, VVVU, UVUV, VUVU`, covering every
> single switch point in both orders and the two alternating controls.
>
> Dual offline exact construction must pass `128/128` specs, `512/512`
> issues, and `2816/2816` refreshes before any TSC. The physical partition is
> 32 safety followed only after exact dual raw agreement by 96 qualification
> trajectories. Formal outcomes remain closed until all 128 raw authenticate.
> A PASS requires at least one R8R15 repair among the ten failed baselines and
> a do-nothing-safe measured oracle of at least `7/16`; it authorizes only a
> separately frozen causal selector/controller design. R8R15 is not MPC or
> Gate A, all trajectories are forbidden from learning, and Gate A remains
> blocked.

> **R8R14 final cumulative multidirection authority-atlas checkpoint
> (2026-08-08 Asia/Shanghai).** Implementation/package checkpoints are
> `d737000 / 9874068`. The 1,053-file direct-copy package passed project,
> empty-copy, server-staging, and installed hashes/compile/focused/full
> validation at `10/10 / 1279/1279`, with one expected isolated-evidence skip
> where applicable. No archive or global Python was used.
>
> Dual offline construction agreed exactly on `112/112` specs, `448/448`
> cumulative exact-Card15 issues, and `2464/2464` stored-target refreshes.
> Maximum predicted issue/refresh increment was `0.1407407407 /
> 3.7037037e-6`, and maximum predicted current utilization was `0.3927`.
> Twenty-eight safety trajectories passed exact primary/independent raw
> agreement before 84 qualification trajectories were authorized.
>
> All `112/112` authentic trajectories passed runtime, full-horizon,
> source-prefix/restart, calibration, event, Card15 target-chain, current,
> finite-state, forbidden-input, and raw-integrity gates. Safety raw is `28
> files / 913832 bytes / 8fd9e0e5...`; qualification raw is `84 files /
> 2757127 bytes / 5bd7e233...`. There were 448 issues, zero forbidden trace
> rows, and maximum measured current utilization `0.3927`. R8/R8R1 were not
> rerun, and R8R14 created no snapshot.
>
> Formal evaluation reproduced baseline and reused R8R12 direction-2-positive
> counts at `6/16 / 6/16` with maximum metric difference zero. The seven new
> families passed 39 trajectories in total; each of all eight fixed
> direction/sign families passed only `5/16` or `6/16`, repaired `0/10`
> failed baselines, and at most regressed one baseline pass. The best measured
> candidate was direction-2 positive in six failed contexts and direction-1
> negative in four, but the held oracle remained `6/16`. Failed-context best
> gain min/median/max was `0.0255417333 / 0.0889587816 / 0.1364830984`.
> Primary and independent results agree exactly.
>
> The final route is
> `CUMULATIVE_MULTIDIRECTION_ATLAS_AUTHORITY_INSUFFICIENT_SEQUENCE_BASIS_REDESIGN_REQUIRED`.
> Summary/independent/final/manifest/state/compact hashes are `a9a9ee3e... /
> 5ab92427... / da8420de... / ce980faf... / 27a2d600... / 99af9763...`.
> Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R14_FORENSIC_REPORT.md`,
> SHA-256
> `306a51e6a83584a21a94928a3c6aa220292f628faa82831c0160f84fa2106be1`.
>
> R8R14 is a finite constant-direction cumulative sequence-authority design
> FAIL, not a runtime, deployment, restart, causality, Card15, current, raw,
> reporting, formal-evaluator, safety, plant, real-MPC, Gate A, or global-
> reachability result. It is immutable. The active boundary is a new frozen
> time-varying sequence basis; all R8-family trajectories remain forbidden
> from learning, and Gate A remains blocked.

> **Prospective R8R14 cumulative multidirection staircase authority
> identification (2026-08-08 Asia/Shanghai).** Before R8R14 implementation,
> configuration, offline construction, result, formal metric, raw, snapshot,
> or TSC, the new genuine sequence-identification design was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R14_CUMULATIVE_MULTIDIRECTION_STAIRCASE_AUTHORITY_IDENTIFICATION_DESIGN.md`,
> SHA-256
> `06360433fd33fd8706453e145eeadca7e37fa80f4e99193cf779e62ab3af4f0f`.
>
> R8R14 reuses but does not rerun the 16 exact R8R12 direction-2-positive
> staircases. It prospectively measures the seven missing `(direction,sign)`
> cumulative scale-1.0 families at `[10,14,18,22]` in all 16 R8R7 contexts:
> 28 safety rows followed, only after exact dual raw agreement, by 84
> qualification rows. Dual offline exact-Card15/action/current construction
> of all 112 rows is required before any worker or plant advance.
>
> Formal outcomes remain closed until all 112 new raw authenticate. A PASS
> requires at least one of ten failed baselines repaired and a do-nothing-safe
> evaluator-only oracle over baseline plus eight measured cumulative
> candidates of at least `7/16`. Even a PASS authorizes only a separately
> frozen causal selector/controller design, not direct TSC MPC. Every source
> and R8R14 trajectory is forbidden from learning; Gate A remains blocked.

> **R8R13 final measured-additive discriminator checkpoint (2026-08-08
> Asia/Shanghai).** Implementation/package checkpoints are `a4f999e /
> da1585d`. The 1,047-file direct-copy package passed local, empty-copy,
> server-staging, and installed hashes/JSON/compile/focused/full validation at
> `7/7 / 1269/1269`, with one expected isolated-evidence skip where
> applicable. No archive, global Python, Ray, `gotsc`, TSC, controller, plant
> advance, new raw, or snapshot was used.
>
> Primary and the structurally independent implementation authenticated and
> strictly parsed all 128 immutable source raw files: 16 R8R7 baselines, 96
> R8R11 direction-0 transients, and 16 R8R12 direction-2 staircases. They
> reproduced source formal counts `6/16 / 36/96 / 6/16`; both formal paths
> agreed with maximum difference zero. All 16 zero-correction controls were
> exact, and the maximum two-path additive difference was
> `1.0842021724855044e-19` against `1e-12`.
>
> Every one of the six globally fixed additive candidates stayed at `6/16`,
> repaired `0/10` failed baselines, and regressed `0/6` baseline passes. The
> frozen rank `[5,3,1,0,2,4]` selected issue step 22/sign positive only by the
> fourth tie-breaker; its failed-baseline gain min/median/max was
> `-0.0108065667 / 0.0886613584 / 0.1366534651`. Primary and independent
> candidate summaries, ranking, selection, numerics, gate, and route agree
> exactly.
>
> The final route is
> `MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_AUTHORITY_INSUFFICIENT_NEW_SEQUENCE_IDENTIFICATION_REQUIRED`.
> Detailed/summary/independent/final/manifest/state hashes are
> `3d0368cd... / 579e21f1... / 6cdae996... / 9d874cca... /
> 0ade6f4f... / b5adb166...`. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R13_FORENSIC_REPORT.md`,
> SHA-256
> `ecf78b5d36d7769c326f671b68b8c977e6830f2c75c0aca8b92cde57e2d0617a`.
>
> R8R13 is a finite optimistic measured-additive authority-design FAIL, not a
> runtime, deployment, source, raw, restart, causality, reporting,
> formal-evaluator, safety, combined-action, controller, plant, real-MPC,
> Gate A, or global-reachability result. It is immutable and may not be
> enlarged or tuned. The active route is a new prospectively frozen genuine
> sequence-identification stage. All R8-family trajectories remain forbidden
> from learning, and Gate A is blocked.

> **Prospective R8R13 measured additive multi-direction discriminator
> (2026-08-08 Asia/Shanghai).** Before R8R13 implementation, composition,
> formal metric, output, route, or any further TSC, a zero-new-TSC design was
> frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R13_MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_COMPOSITION_DESIGN.md`,
> SHA-256
> `f643d4ded6131db8264847f8ce4aff121c4165c49666eb7b7e34211c0c72bc1f`.
>
> R8R13 authenticates the exact 16 R8R7 baselines, 96 R8R11 direction-0
> transients, and 16 R8R12 direction-2 staircases. For each of six globally
> fixed R8R11 choices (`issue=[14,18,22]`, sign `[-,+]`), it prospectively
> composes only R/Z/Ip as `R8R12 + (R8R11 - baseline)` in all sixteen
> contexts. A single global choice must reach at least `7/16`, repair at least
> one failed baseline, and regress none of the six baseline passes. Primary
> and independent construction/formal paths must agree exactly.
>
> This is explicitly an optimistic separable measured-trajectory diagnostic.
> It composes no action/current/hidden state and runs zero Ray, `gotsc`, TSC,
> controller, or plant advances. A PASS can authorize only a separately
> frozen exact combined-action Card15/current preflight, never real TSC
> directly. Gate A and all learning remain blocked.

> **R8R12 v2 final cumulative direction-2 staircase checkpoint (2026-08-08
> Asia/Shanghai).** Corrected implementation/package checkpoints are
> `3203a02 / 523c706`. The 1,040-file direct-copy package passed local,
> empty-copy, server-staging, and installed focused/full validation at
> `10/10 / 1262/1262`, with one expected isolated-evidence skip where
> applicable. No archive or global Python was used.
>
> Dual zero-TSC construction passed exactly `64/64` staircase levels and
> `352/352` exact-target refreshes, with maximum predicted issue increment
> `0.1409259259`, refresh increment `3.7037037e-6`, and current utilization
> `0.3905`. Four safety trajectories then completed and passed exact
> primary/independent raw agreement before the remaining twelve were
> authorized. All `16/16` authentic v2 trajectories passed runtime,
> full-horizon, restart/physical-prefix, calibration, Card15 issue/refresh,
> current, finite-state, forbidden-input, and raw-integrity gates. Safety raw
> is `4 files / 130839 bytes / 8eb94b44...`; qualification raw is `12 files /
> 395289 bytes / b51d78d0...`. There were 64 issues, 352 refreshes, zero
> forbidden traces, and maximum current utilization `0.3924`.
>
> After dual raw authorization, formal evaluation reproduced the R8R7
> baseline at `6/16`; the fixed staircase also passed `6/16`. It improved the
> minimum signed margin in six of ten failed contexts and regressed four, but
> repaired `0/10`, so the held oracle remained `6/16`. Primary and independent
> formal outcomes, numerics, scientific gate, and route agree exactly with
> maximum difference zero. The final route is
> `CAUSAL_CUMULATIVE_DIRECTION2_STAIRCASE_AUTHORITY_INSUFFICIENT_SEQUENCE_REDESIGN_REQUIRED`.
> Detailed/summary/independent/final/manifest/state hashes are
> `123991e8... / 93df1e3e... / 848867b2... / 2a018bd0... /
> 48a09927... / e5410b24...`.
>
> R8R12 v2 is a finite fixed-policy action-authority design failure, not a
> runtime, deployment, construction, restart, causality, Card15, current,
> raw, reporting, formal-evaluator, safety, plant, real-MPC, or global-
> reachability result. Its identity is immutable and may not be tuned,
> resumed, or enlarged. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R12_FORENSIC_REPORT.md`,
> SHA-256 `431db78078df7e27def9cee633f91d69e89d48b1833feb82765c10add933ecbd`.
> The active boundary is a newly frozen genuinely multi-direction or
> otherwise genuinely different asymmetric causal sequence. Gate A and all
> learning remain blocked; all R8-family trajectories are forbidden from
> learning data.

> **R8R12 v1 construction failure and prospectively frozen v2 correction
> (2026-08-07 Asia/Shanghai).** R8R12 v1 is final as
> `CAUSAL_CUMULATIVE_DIRECTION2_STAIRCASE_EXECUTION_OR_SAFETY_FAIL_STOP`.
> Offline primary/independent construction passed exactly (`64/64` levels,
> `352/352` refreshes, maximum issue increment `0.1409259259`, maximum
> predicted current utilization `0.3905`) with zero raw/TSC. Four authorized
> safety tasks then all raised
> `D1R14R6 per-spec issue schedule changed` during controller construction.
> Each immutable raw contains one initial state, zero trace, zero action, zero
> plant advance, and no snapshot. Canonical safety inventory is `4 files /
> 17687 bytes / f59d7aa2...`; qualification raw and formal outcomes remain
> unopened.
>
> A reporting-only strict-JSON repair at `c9111cc`/package `4f14aa3` replaced
> absent maxima `inf` with `null` and authenticated the existing raw without a
> worker call. Independent raw recomputation exactly agreed with primary;
> primary/independent/manifest/state hashes are `d2772100... / 65f392cc... /
> 01b650ca... / 57217b2c...`. This is a controller-construction implementation
> failure before plant advance, not a control, safety-envelope, plant, formal,
> raw, or global-reachability result. v1 is immutable and may not resume.
>
> Before any v2 implementation or outcome, v2 is frozen with a new campaign
> identity/controller revision. The only correction is an inherited R6
> constructor placeholder schedule `14/15/16`; the subclass still exclusively
> owns the unchanged actual staircase `[10,14,18,22]` after the delegated
> 0--9 prefix. All context, action, current, Card15, timing, two-phase,
> scientific, and learning-prohibition gates remain unchanged. Exact report
> and v2 freeze:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R12_V1_CONSTRUCTION_FAILURE_AND_V2_CORRECTION.md`.
> Report SHA-256 is
> `2b3580dd049227f408bec6cded91acc742479224a6afe2a55087efef60b9fa47`.
> Gate A and all learning remain blocked.

> **Prospective R8R12 causal cumulative staircase checkpoint (2026-08-07
> Asia/Shanghai).** Before R8R12 implementation, configuration, specification,
> offline construction, candidate formal outcome, raw, or TSC, the new
> one-sided cumulative direction-2-plus authority sentinel was frozen at
> checkpoint `1d09508` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R12_CAUSAL_CUMULATIVE_DIRECTION2_STAIRCASE_AUTHORITY_SENTINEL_DESIGN.md`.
> Design SHA-256 is
> `46d959813a0810970e7ea6ab5a5a097c9afa5949e7642f22fc4b17a19ccd2f16`.
>
> R8R12 uses exactly one new trajectory for each of the 16 accepted R8R7
> contexts. At task steps `[10,14,18,22]` it constructs a new canonical
> direction-2 sign-plus exact Card15 target from current causal readback and
> refreshes that stored target through the next decision; level four is held
> through the unchanged 35/37-state endpoint. It deliberately has no final
> accumulated cancellation. Four safety rows must pass primary/independent
> execution and current gates before the remaining twelve qualification rows.
> Candidate formal outcomes stay closed until all 16 authenticate.
>
> The direction/sign was fixed from consumed R8R8 point-score diagnostics:
> direction-2 plus was best at 56/64 origins and at all `40/40` origins whose
> matching baseline failed. Those labels are not controller inputs. A PASS
> still requires at least one of ten failed baselines repaired and held-oracle
> coverage `>=7/16`; it authorizes only a separately frozen causal selector.
> R8R12 is not MPC or Gate A, and all of its trajectories are forbidden from
> learning datasets.

> **R8R11 final sustained exact-target-refresh checkpoint (2026-08-07
> Asia/Shanghai).** R8R11 is final as
> `SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_INSUFFICIENT_ASYMMETRIC_SEQUENCE_REDESIGN_REQUIRED`.
> It executed exactly 96 fresh authentic TSC trajectories in the frozen
> safety/qualification order. All 24 safety and 72 qualification rows passed
> runtime, full-horizon, restart, causal physical prefix, calibration, exact
> Card15 issue/refresh/cancel, current, finite-state, forbidden-input, and raw
> integrity gates. Safety raw is `24 files / 759481 bytes / 137fc402...`;
> qualification raw is `72 files / 2288228 bytes / 82958eb8...`. Maximum
> issue/cancel increment was `0.1742592593`, maximum refresh increment was
> `3.7037037e-6`, and maximum current utilization was `0.3924`.
>
> The first audits falsely rejected source-trace prefixes because R8R11 does
> not copy 13 source-only R4/R8R7 wrapper metadata keys. The separately
> audited reporting repair found `3120 / 9360` wrapper-only differences for
> safety/qualification, zero non-wrapper differences, preserved both raw
> inventories byte-for-byte, opened no formal outcome, created no raw, and
> left the primary controller hash `dd4ed571...` unchanged. Corrected primary
> and structurally independent audits then agreed exactly `24/24` and `72/72`.
> This was a reporting defect and did not warrant a TSC rerun.
>
> Under the unchanged formal contract, baseline coverage was `6/16`, candidate
> trajectory formal passes were `36/96`, and all ten failed baselines obtained
> a strict best-margin improvement of `0.0002495221--0.0017954458`. None was
> repaired, so held-oracle coverage remained `6/16` against the frozen
> `>=7/16` gate. Independent final recomputation agreed on all outcomes,
> numerics, scientific gate, and route with maximum difference zero. Primary
> detailed/summary, independent, final-report, manifest, and state hashes are
> `aecd3a9e... / 8214b9c0... / 13f4436f... / 903cdb4f... /
> aaa80624... / d805d7de...`.
>
> This is a finite sustained direction-zero action-authority design FAIL, not
> a runtime, deployment, restart, causality, raw, reporting, formal-evaluator,
> safety, real-MPC, plant, or global-reachability result. R8R11 is immutable
> and may not resume. The next route must prospectively freeze a genuinely
> asymmetric or multi-direction causal sequence under a new identity. Gate A
> and all learning remain blocked; every R8-family trajectory is forbidden
> from expert data. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R11_SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_SENTINEL_FORENSIC_REPORT.md`.
> Report SHA-256 is
> `8d1dbaf0c0055e00088a7d63e033d51104bdfa07fe46188581261327b09673f8`.

> **Prospective R8R11 sustained exact-target-refresh checkpoint (2026-08-07
> Asia/Shanghai).** Before R8R11 implementation, specs, offline construction,
> formal outcome, raw, or TSC, and without opening R8R10 context-level detailed
> outcomes, the next genuine sustained-action sentinel was frozen at checkpoint
> `d53d38d` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R11_SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_SENTINEL_DESIGN.md`.
> Design SHA-256 is
> `43a2ad925c78c4656a68e27a7243daf952edab1170c811c85c3d679ca1ab1707`.
>
> R8R11 prospectively uses all 16 accepted R8R7 contexts, direction-zero 1.5x,
> issue steps `[14,18,22]`, and both signs. Unlike every R8/R8R10 isolated
> pulse, it issues an exact Card15 target, reconstructs the same stored target
> from causal current readback one step later, and returns to the stored center
> at `issue+2`. Phase 1 contains 24 safety rollouts over four contexts; only
> exact primary/independent safety agreement authorizes the remaining 72, for
> at most 96 fresh authentic trajectories.
>
> Every issue/refresh/cancel is fail-closed before plant advance under the
> unchanged 0.25/0.24 incremental-action, Card15, current, saturation, and
> forbidden-input gates. Formal timing is unchanged. A PASS requires at least
> one of the ten R8R7 baseline failures repaired and held-oracle coverage at
> least `7/16`, and authorizes only a separately frozen causal selector design.
> R8R11 is not MPC or Gate A, and all of its trajectories remain forbidden
> from learning datasets.

> **R8R10 final replacement-scale authority checkpoint (2026-08-07
> Asia/Shanghai).** R8R10 is final as
> `REPLACEMENT_SCALE_FORMAL_AUTHORITY_INSUFFICIENT_SUSTAINED_ACTION_REDESIGN_REQUIRED`.
> Its zero-new-TSC primary and structurally independent audit authenticated
> and strictly parsed the immutable R4/R6/R8 development banks: `200 / 48 /
> 624` raw files with exact published digests. They reproduced the complete
> formal aggregates `50/200 / 12/48 / 234/624` and agreed on all selected
> pass, arrival, and signed-margin results for `312/312` rows with maximum
> numerical difference zero. R8 calibration and holdout remained unopened.
>
> Across 24 consumed development contexts, the zero baseline passed `8/24`.
> Canonical direction-zero 1.0x and replacement direction-zero 1.5x each had
> 48 formal-pass pulse trajectories, but their separate and combined
> do-nothing-safe oracles all remained `8/24`. Of 16 failed baselines,
> canonical improved the minimum margin in 15 and replacement improved it in
> all 16. Replacement min/median/max gains were
> `0.000050072836658 / 0.000210307502231 / 0.015329058949230`, yet canonical,
> replacement, and replacement-only repairs were all `0/16`.
>
> R8R10 ran zero Ray, `gotsc`, TSC, controller, or plant steps, created no raw
> directory, and modified no source evidence. Primary detailed/summary,
> independent, manifest, and state hashes are `dea560af... / e359a5ae... /
> 161180d5... / 60dfa552... / 8ab651f1...`. Local, empty direct-copy, staging,
> and installed validation passed compile, focused `6/6`, full `1243/1243`,
> and `1024/1024` declared hashes, with one expected isolated-evidence skip.
> The first native Linux checksum invocation stopped before compilation because
> CRLF was parsed as part of each path; the unchanged files then passed through
> a read-only CR-stripped verification stream.
>
> This is a finite fixed-amplitude action-authority design FAIL, not a runtime,
> deployment, restart, causality, raw, reporting, formal-evaluator, real-MPC,
> safety, plant, or global-reachability result. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R10_FORENSIC_REPORT.md`.
> Report SHA-256 is
> `1698e024fcbc9c00f65536915de37926b2cf927a7a5402a8655169cbeaccf1df`.
> Before computing another outcome, freeze a genuinely sustained or asymmetric
> causal action architecture under unchanged hard contracts. Gate A and all
> learning remain blocked; all R8-family evidence remains forbidden from
> expert data.

> **R8R9 final measured-authority checkpoint (2026-08-07
> Asia/Shanghai).** R8R9 is final as
> `MEASURED_MULTIPULSE_FORMAL_AUTHORITY_INSUFFICIENT_ACTION_REDESIGN_REQUIRED`.
> The zero-new-TSC primary and structurally independent audit authenticated
> the immutable R8R7 and R8R8 sources, strictly parsed all 48 R8R7 raw files,
> reproduced the published baseline/multipulse formal counts `6/16 / 12/32`,
> and agreed on both formal evaluators for `48/48` rows with zero maximum
> signed-margin difference.
>
> Of ten failing baselines, nine received a strict but small best-schedule
> minimum-margin improvement. The min/median/max gains were
> `-0.000105833333334 / 0.000125349647658 / 0.000926800000001`.
> Nevertheless, the two measured canonical-scale four-pulse schedules repaired
> `0/10`, so measured-oracle formal coverage remained `6/16` against the frozen
> `>=7/16` gate. The canonical-scale action alphabet therefore lacks measured
> formal-control authority for this route.
>
> R8R9 created no raw directory and ran zero Ray, `gotsc`, TSC, controller, or
> plant steps. Primary detailed/summary, independent, manifest, and state hashes
> are `4bda8b9d... / ffb67e2a... / 768a0a40... / 96655d1c... /
> e03c09df...`, rechecked at the original server path. Local, empty direct-copy,
> staging, and installed validation passed compile, focused `6/6`, full
> `1237/1237`, and `1017/1017` declared hashes, with one expected isolated-
> evidence skip where applicable.
>
> This is a finite measured-action-authority design FAIL, not a runtime,
> restart, raw, reporting, formal-evaluator, real-MPC, safety, plant, or global-
> reachability result. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R9_FORENSIC_REPORT.md`.
> Report SHA-256 is
> `66993c4d638dec5e9bc883e45ce6586a12b367b9a97bc214c36cc41c80454f98`.
> The next action architecture/discriminator must be frozen before its outcome
> is computed. Gate A and all learning remain blocked; all R8-family evidence
> remains forbidden from expert data.

> **R8R8 final and prospective R8R9 authority-audit checkpoint (2026-08-07
> Asia/Shanghai).** R8R8 is final as
> `CAUSAL_DISCRETE_PULSE_MPC_SOURCE_OR_OFFLINE_FAIL_NO_TSC`. The accepted v2
> primary authenticated R8R7, completed 576 forecasts, 64 decisions, and
> 512/512 exact Card15 issue/cancel constructions with no forbidden input or
> enumeration side effect, but selected a nonzero pulse 0/64 times. It failed
> the frozen minimum-one nonzero-selection gate before authorization. No raw
> directory, Ray, `gotsc`, TSC, controller action, or plant advance exists.
>
> The structurally independent recomputation agreed exactly: maximum prediction
> and score differences were both zero, selected candidates and exact actions
> agreed, and all five model hashes matched. Its first report incorrectly
> mapped audit agreement to the scientific PASS route. Reporting-only fix
> `98bcb9c`, packaged at `9b12970`, now separates audit PASS from scientific
> FAIL and preserves the primary route. The original independent JSON is
> preserved at SHA-256 `2144ddad...`; the corrected independent SHA-256 is
> `625a1bb289db927d037a448b6dba88d930246d5360c4c78155b79e2e272b53c1`.
> Primary summary / state hashes remain `eb7cf6eb... / c7914e8f...`.
>
> Local, empty direct-copy, staging, and installed validation passed compile,
> focused `12/12`, full `1231/1231`, and 1010/1010 declared hashes, with one
> expected isolated-evidence skip where applicable. A first corrected-launch
> command stopped before Python with `Permission denied` because the Windows
> direct copy did not retain an executable bit; its log is preserved. Explicit
> `bash` then completed the corrected zero-TSC audit under a new log.
>
> Retrospective score attribution found best-nonzero/zero ratios of
> `1.010167968 / 1.017218600 / 1.030202082` (min/median/max) for the frozen
> candidate-specific robust score. Point-only ratios were
> `0.995171374 / 0.997048163 / 0.999609468`: all 64 moved slightly in the
> favorable direction, but none met the frozen `<=0.995` gate. R8R8 is an
> objective/model/action-design FAIL, not a runtime, restart, causality, raw,
> formal-control, real-MPC, safety, or plant-reachability result. Exact report:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R8_FORENSIC_REPORT.md`.
>
> Before inspecting the context-level R8R7 formal mapping, R8R9 is frozen as a
> zero-new-TSC measured multipulse authority audit in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R9_MEASURED_MULTIPULSE_AUTHORITY_AUDIT_DESIGN.md`,
> SHA-256 `3cb4ca9768671aaf575f2cb71c8c33d8643156110dc68c0b1e7b4d714d3d4510`.
> It will determine whether either immutable real R8R7 schedule repaired any
> of the ten failing baselines. Gate A and all learning remain blocked.

> **Prospective R8R8 causal discrete-pulse MPC-core checkpoint (2026-08-07
> Asia/Shanghai).** Before any R8R8 implementation, offline candidate result,
> controller decision, formal outcome, raw trajectory, or TSC plant advance,
> the first genuine receding-horizon MPC core was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R8_CAUSAL_DISCRETE_PULSE_RECEDING_HORIZON_MPC_CORE_DESIGN.md`.
> Its SHA-256 is
> `0906ca9e58126cc2f414f167a685e766d95790ec4f3d28052debb4b5e6db0244`.
>
> R8R8 conditionally runs exactly 16 fresh authentic controlled trajectories
> over the accepted R8R7 baseline contexts. At task steps `[10,14,18,22]`, it
> exhaustively scores zero plus the eight fixed direction/sign canonical-scale
> pulses with the byte-authenticated static observer, four-step response
> model, and frozen tubes. It executes only the first exact Card15 pulse and
> next-step stored-center cancellation, then replans from actual causal state.
> Continuous mixtures/amplitudes, response-tail extrapolation, online
> adaptation, labels, matched futures, source future actions, and post-result
> tuning are forbidden.
>
> The frozen implementation checkpoint is `7e1dc89`. Local project-venv
> compilation and focused tests passed `10/10`; the complete unittest suite,
> after explicitly loading the existing Windows `resource` shim from
> `tests/conftest.py`, passed `1229/1229` with zero failures, errors, or skips.
> No R8R8 offline result, controller decision, raw trajectory, or TSC plant
> advance existed at that checkpoint. Packaging, empty-directory direct-copy
> validation, installed-server validation, and the dual offline gate are next.
>
> Package checkpoint `9179c9a` passed local empty-directory, server staging,
> and installed validation. The first server offline invocation then stopped
> before creating the R8R8 stage because source authentication incorrectly
> required R8R7 `phase_status == "finished"`; the immutable R8R7 state is
> actually `"complete"`. Its final/state/manifest hashes remained exactly
> `9ca6afce... / 04f643e0... / ae89fb2d...`, and its route, scientific gate,
> and verdict remained unchanged. The stopped v1 run root is preserved and
> contains no R8R8 stage, raw, decision, or TSC advance.
>
> The authentication-only hotfix is checkpoint `2b287cb`. It changes no model,
> objective, candidate, controller, action, gate, experiment identity, or
> physical semantics, and also adds structurally independent authentication of
> the same R8R7 files and raw inventories. Local focused tests passed `11/11`
> and the shimmed complete suite passed `1230/1230`. A separately named v2
> offline attempt is required after repackaging and deployment.
>
> Primary and structurally independent zero-TSC preflights must first agree on
> all 576 forecasts/scores, 64 selections, and 512 pure issue/cancellation
> constructions. Only a dual offline PASS authorizes TSC. The deterministic
> core then requires exact execution/integrity/safety and unchanged formal
> control `16/16`; a PASS still authorizes only separately frozen robustness
> qualification and is not Gate A. All R8R8 trajectories are forbidden from
> learning, and expert data, BC, DAgger, and residual RL remain blocked.

> **R8R7 final fresh-interaction qualification (2026-08-07
> Asia/Shanghai).** R8R7 is final as
> `FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_PASS_MPC_DESIGN_REQUIRED`.
> Its 16 fresh zero-action baselines and 32 fresh four-pulse trajectories all
> completed with exact restart/source-prefix/calibration/causality, finite
> raw, zero forbidden trace, and unchanged hard action/current/Card15 gates.
> Baseline raw is 16 files / 487298 bytes / digest
> `46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5`;
> multipulse raw is 32 files / 1068664 bytes / digest
> `d8435c8cd61fd082e143d79a3628ad2274780faefc6b676367df917355f49e31`.
>
> The frozen static observer plus fixed R8R1 response model passed baseline
> point/tube `64/64 / 64/64` and multipulse point/tube `128/128 / 128/128`.
> Every baseline context passed 4/4, every multipulse context passed 8/8,
> every direction passed 32/32, both signs passed 64/64, and there were zero
> finite exclusions. Primary and structurally independent raw/model audits
> agree exactly. Final report / manifest / state SHA-256 values are
> `9ca6afce52442c1b7470cb8ff13a2eac4aab32de1e05a898d206f5fe76e01005`,
> `ae89fb2df01cd6758676baa895880e2005a1f8967c62ea4ae671ab61ea771e24`,
> and `04f643e09f414c5d5a305f1a3584450e12e5a39e8d062d454480df3c8d95fe7e`.
>
> The preserved first phase-two failure remains classified as a pre-action
> implementation/reporting error: all 32 files contain zero action and zero
> plant advance and are not counted in the scientific result. Formal tracking
> was diagnostic only (`6/16` baseline, `12/32` multipulse). R8R7 is therefore
> a finite interaction-model PASS, not MPC, formal-control, Gate A, or a
> learning result. All R8R7 trajectories are forbidden from expert data. The
> next authorized boundary is a separately frozen genuine receding-horizon
> MPC design. Full audit:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R7_FORENSIC_REPORT.md`.

> **R8R7 pre-action runtime hotfix checkpoint (2026-08-07
> Asia/Shanghai).** R8R7 phase-one baseline completed 16/16 authentic raw
> with exact restart/source prefix/causality and passed the frozen static
> observer gate 64/64 point and 64/64 tube; all 16 contexts passed 4/4.
> Primary and independent model results agree exactly. A reporting-only raw
> inventory schema mismatch was fixed at `a39c5a9` without changing raw,
> models, metrics, gates, or outcomes.
>
> The first authorized 32-task multipulse invocation produced 32 strict raw
> files but every controller constructor stopped at the same inherited R4
> issue-slot validation before returning an action. Every file has exactly
> one post-reset state, zero trace rows, zero action events, and zero plant
> advances. Inventory is 32 files / 145407 bytes / digest
> `7cadf53a6870980802009eef71e3d7c8e5c2707eb446d85f125851e239af160d`.
> The primary report then separately failed to serialize an unavailable
> maximum represented as `inf`.
>
> This is a pre-action controller-construction implementation error plus a
> reporting error, not a TSC, restart, safety, controller-design, plant,
> response-model, MPC, or reachability result. The semantics-preserving fix
> `4a8b558` uses an accepted historical R4 slot only as the inherited
> constructor placeholder; the overridden controller retains the frozen
> R8R7 issue clock `(10,14,18,22)`. Unavailable failure maxima serialize as
> `null`. The existing failed raw must be preserved and authenticated before
> the same 32 frozen specs may be retried once. Full audit:
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R7_MULTIPULSE_RUNTIME_HOTFIX_AUDIT.md`.

> **Superseding R8R7 prospective-design checkpoint (2026-08-07
> Asia/Shanghai).** Before any R8R7 implementation, derived metric,
> model/tube artifact, raw result, or TSC trajectory, the fresh multipulse
> static-observer interaction sentinel was frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R7_FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_SENTINEL_DESIGN.md`.
> Its SHA-256 is
> `a2d2abda8189ff475455ae945391948ede937ba49ab559d79f1c48c74e80067f`.
> It uses 16 contexts from the eight response-unopened former R8
> calibration/holdout pairs. Phase 1 is 16 fresh zero-future-action baselines;
> only a dual-audited static-observer PASS authorizes phase 2. Phase 2 is 32
> authentic four-pulse trajectories under two fixed schedules and unchanged
> Card15/current/safety gates, yielding 128 issue windows.
>
> The predictor is the byte-authenticated R8R6 static observer plus one fixed
> R8R1 PCA4/RBF2/ridge0.1 40 ms response deployment fit. Innovation, model
> selection, refit on R8R7 raw, and future/label inputs are forbidden. A PASS
> authorizes only a separately frozen MPC design. R8R7 is not MPC, Gate A,
> expert data, BC, DAgger, or RL, and all 48 possible trajectories are
> forbidden from learning datasets.
>
> **Superseding R8R6 final and static-observer handoff (2026-08-07
> Asia/Shanghai).** R8R6 is final as
> `CAUSAL_ONE_STEP_INNOVATION_NO_MEASURABLE_GAIN_STATIC_ROBUST_OBSERVER_SENTINEL_REQUIRED`.
> Its 20 whole-pair outer folds authenticated 20 physical pairs, 40 history
> contexts, 600 origins, and zero forbidden/future predictor inputs. Startup
> passed 40/40; adapted point, prescribed-issue, and tube gates passed
> 560/560, 120/120, and 560/560, with all 40 contexts passing, zero finite
> exclusions, zero clipping, and a tube below every frozen cap.
>
> The prospective innovation usefulness gate failed independently of observer
> qualification: adapted/cold aggregate MSE was `1.0781373396231766` against
> the required `<=0.95`, only 8/40 contexts strictly improved, only 12/40
> remained within the 1.05 context-regression limit, and the worst ratio was
> `1.287598795027994`. The fixed adapter is therefore disabled and the static
> linear/PCA32/ridge-1e-6 observer plus reserved global tube is selected.
>
> Primary and structurally independent numerical, route, and artifact hashes
> agree exactly. R8R6 ran zero Ray, `gotsc`, TSC, controller, or plant steps,
> created no raw directory, and modified no source trajectory. Final report,
> model, tube, final-stage report, manifest, and state SHA-256 values are
> `cf948786db23de51a5f30a8407cee30d06e8ddf1cafe4476f0c45a78c6a7eeea`,
> `3ba16449086097a42513987df97c95ec6d6d0d35d572e73992fa5eafdfc15519`,
> `747a6c24f9abed8a4ec6784e4699c7ebe557a049bb11e10ea9a1d5ca0254b8ea`,
> `d9e70003a3267ee01394472f4c2e4efdb03af65656a7dc1f2980a521b74528e3`,
> `2001bece45759d4d8ce8c17cf85e8c063c499ed313493a4e46b53246e52c4beb`,
> and `0cb80974ac25d2f5cdfeb6f69e825a5e71ab4caf388b94cd3ac890b35cb140be`.
> R8R6 is an observer-qualification PASS and adaptation-usefulness FAIL, not a
> controller, real-MPC, formal-control, plant, or Gate A result. The next step
> must be frozen as a fresh authentic static-observer interaction sentinel
> before implementation, metrics, or TSC; learning remains blocked.

> **Superseding R8R6 prospective-design checkpoint (2026-08-07
> Asia/Shanghai).** After final R8R5 primary/independent agreement, but before
> any R8R6 implementation, adapted prediction, residual, tube, metric, route,
> or artifact was computed, R8R6 was frozen at checkpoint `0352207` in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R6_CAUSAL_ONE_STEP_INNOVATION_OBSERVER_DESIGN.md`,
> SHA-256
> `6f8886f42321a2e99a97332ecf03c1827b5385ebfc50f6ee07fefefcafa182f1`.
> It is a zero-new-TSC 20-fold whole-pair development audit over the now-
> consumed 20 baseline pairs/40 histories/600 origins.
>
> The cold model remains fixed at linear/PCA32/ridge-1e-6. At origin 10 it is
> the startup/fallback observer. At each later origin the sole adapter uses
> the already observed one-step vR/vZ/Ip prediction innovation, fixed physical
> clipping `[0.02,0.02,1000]`, and fixed persistence `rho=0.8`; R/Z are
> reconstructed by exact causal integration. A new global adapted-residual
> tube uses the frozen higher-q95/every-context-higher-q90 construction with a
> prospective reserve multiplier 2.0 and unchanged caps. Adaptation must
> reduce aggregate MSE by at least 5%, avoid more than 5% context regression,
> and improve at least 24/40 contexts. If uncertainty gates pass without that
> measurable gain, the route explicitly selects the static robust observer
> rather than unnecessary adaptation. Even a pass authorizes only a separately
> frozen fresh interaction sentinel; MPC, Gate A, and learning remain blocked.

> **Superseding R8R5 final and causal-innovation handoff (2026-08-07
> Asia/Shanghai).** R8R5 is final at
> `CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED`. Its zero-new-
> TSC development phase passed 480/480 point rows, 128/128 prescribed issue
> rows, 480/480 tube rows, every context gate, and the tube cap. Primary and
> structurally independent development recomputations agreed exactly, then
> froze model/tube hashes
> `d3d7ecebbe51ca20e83cdb126682d2bebad749b8fd5cb67dd57b3baf416e77e4 /
> 3a436307a507b9aacda85321dd4d55e6bbcc996efe2e25c2b5026571c7108786`
> before authorizing holdout.
>
> All eight authentic blind baselines completed full horizon with exact
> runtime, restart-snapshot authentication, physical/action prefix, causality,
> zero future action, constant future current, Card15/current, finite raw, and
> reporting integrity. Raw inventory is eight files, 245493 bytes, digest
> `55cae64bf5b907b4cd6013615388dbb637dd2f1f14e49bda7fb49d11cf5b3d14`;
> maximum action/current utilization was `0.648149691358026 / 0.3924`.
>
> The frozen observer passed blind point rows 120/120 and prescribed issue
> rows 32/32 with zero finite-exclusion violation. Aggregate tube containment
> passed 117/120 against 114, but one context,
> `p5_q2_a0p900_gap4_settle4|plus_first`, contained 14/16 against the frozen
> 15/16 requirement. Read-only row forensics found three uncontained rows and
> only four violating cells, all Ip at future lags 11--12; every row still
> passed its point cap. Independent raw/model audits reproduced the primary
> result exactly.
>
> Final stage manifest/state hashes are
> `d737bb77a9547fac8c1378dab3fdbd63aeca60cc30fefc38ecf5dab181d441cc /
> dc564ddfb9edae9b044dfa358ddb98306b56f328a8fc06c60b8c43ade772e48c`.
> R8R5 is a finite uncertainty-qualification design FAIL, not a runtime,
> deployment, restart, raw, controller, formal-control, real-MPC, plant, or
> global-observability result. Exact report SHA-256 is
> `cd9f7f0c70e3c858193f7511abd1e0ece4fa612f6cfa1bf16b1bdebb038cc91c`;
> compact v2 row audit SHA-256 is
> `87e1ebc466ac8375ea76226787b22fe013f9de0c95b27a19d9d68499c77896ab`.
> All R8R5 trajectories remain forbidden from expert/learning data.

> **Superseding R8R5 prospective-design checkpoint (2026-08-07
> Asia/Shanghai).** After final R8R4 primary/independent agreement, but before
> any R8R5 fit, residual recomputation, tube value, metric, artifact, route,
> new TSC, or blind-holdout outcome, R8R5 is frozen in
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R5_CONTEXT_ROBUST_OBSERVER_HOLDOUT_DESIGN.md`,
> SHA-256
> `c7b5d570a6d74b39368e4ee4ef677f84a7a81b469a000515ea843e2797622daa`.
> It treats all R8R4 development evidence as consumed, fixes the R8R4-selected
> linear/PCA32/ridge-1e-6 point model, and recalibrates only one shared global
> tube from whole-pair OOF residuals. The scalar is prospectively fixed to
> `1.25 * max(global higher-q95 row ratio, every-context higher-q90 row
> ratio)`, with a floor at one. Context labels affect only development
> calibration of that global scalar and are never predictor inputs or
> deployment-time selectors.
>
> R8R5 runs zero development TSC. Only after point, tube-cap, construction,
> source, and structurally independent gates pass may it freeze model/tube
> hashes and run the eight still-unopened baseline histories under a new
> identity. All hard restart, causality, zero-future-action, Card15, current,
> raw/snapshot, and formal-timing contracts remain unchanged. Every stage
> trajectory is forbidden from expert/BC/DAgger/RL data. Even a blind-holdout
> PASS authorizes only a separately frozen combined adaptation validation;
> controller, MPC, Gate A, and learning remain blocked.

> **Superseding R8R4 final and context-robust-holdout handoff (2026-08-07
> Asia/Shanghai).** R8R4 is final at
> `FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT`. Eight/eight fresh
> development baselines completed with exact restart, source prefix,
> causality, zero future action, constant future current, Card15, finite raw,
> and snapshot integrity; the raw inventory is eight files, 245279 bytes,
> digest
> `8d0d6c2c8f7e4e8436f9ef958fb30e4276823a8004fbab97b8c50d71b1ed3f66`.
> Maximum normalized action and current utilization were
> `0.648149691358026 / 0.392`.
>
> The nested outer point gate passed 480/480 origins and 128/128 prescribed
> issue origins, with zero finite-exclusion violations and maximum scaled
> error `0.12737875204525517`. The selected candidate was
> linear/PCA32/ridge-1e-6. Its all-development OOF tube stayed below every
> cap and contained 457/480 origins against a 456 requirement, but only 27/32
> history contexts met their 90% floor. The five retained context counts were
> `12/14, 11/16, 12/16, 10/14, 12/14` against requirements
> `13,15,15,13,13`. Primary and structurally independent model audits agree
> exactly; no model or tube artifact was emitted.
>
> Final server inspection found development/holdout/model counts `8/0/0`,
> `holdout_outcomes_opened=false`, phase `development_model_failed`, and state
> SHA-256
> `617c6ea2e2ae81d5d1ad9f0de2f331a1b0d19caa3031dc76e4714ecc4c417015`.
> Primary detailed/summary/independent hashes are
> `af8cb6d75a435ecd96948b4c15a2e1929c98527edd5483c8f29c0c6394125dac`,
> `bde614d6ac34535d5f22f187925723969921e8333b41d429a32e0719cb8b3bfd`,
> and
> `12ee920fb0d49d46285bba31a443a24e09a5b6b9b3b1d0b5ddc61560a20fa86b`.
> This is a finite uncertainty-calibration/design FAIL, not runtime, restart,
> raw, controller, formal-control, real-MPC, plant, reachability, or global-
> observability evidence. The exact report SHA-256 is
> `57b43c220de0fe2e37ac1dde17b4054bcd7f679255de58e2d782ee1bea2b53a3`.

> **Superseding R8R4 prospective-design checkpoint (2026-08-07
> Asia/Shanghai).** Before any R8R4 implementation, fit, observer metric, new
> TSC trajectory, model/tube artifact, or route, the fresh causal observer
> identification campaign is frozen at
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R4_FRESH_CAUSAL_OBSERVER_IDENTIFICATION_DESIGN.md`,
> SHA-256
> `942b7698e9d19ee905d75dc7ee9fda370e642e9e986298af32d8f17ed22f8119`.
> It uses a new stage identity and exactly sixteen fresh, no-probe baseline
> trajectories: four whole development pairs/eight histories first, followed
> only after a dual-audited frozen model/tube by four blind holdout pairs/eight
> histories. R8's original calibration/holdout directories remain empty; the
> corresponding pair blueprints are consumed only in distinct R8R4 raw paths.
>
> R8R4 retains the exact R8R3 353-dimensional causal feature and kinematic
> output but prospectively expands the fixed candidate ranks to
> `32/48/64/96`. The new finite application gate requires 95% aggregate point
> coverage, 90% per-history coverage, no finite-exclusion-cap miss, and a
> frozen empirical tube with the same aggregate/per-history coverage. Point
> caps are 3 mm R/Z, 0.02 m/s vR/vZ, and 1000 A Ip; finite tube/exclusion caps
> are 10 mm, 0.05 m/s, and 3000 A. These are observer-development gates and
> do not alter formal 250/270 ms arrival, 350/370 ms hold, 30 mm, 0.1 m/s, or
> 10 kA acceptance.
>
> Every restart, source prefix, causality, zero-future-action, Card15, current,
> solver, raw, snapshot, and independent-integrity gate remains all-or-nothing.
> All R8R4 trajectories are forbidden from expert/BC/DAgger/RL data. Even a
> blind holdout PASS authorizes only a separately frozen combined adaptation
> validation; controller, MPC, Gate A, and learning remain blocked.

> **Superseding R8R3 final and fresh-identification handoff (2026-08-07
> Asia/Shanghai).** R8R3 is final at
> `CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED`.
> Primary and structurally independent zero-new-TSC recomputations agree
> exactly. The causal observer passed 346/360 complete outer origins and
> 89/96 prescribed issue origins inside its frozen component caps. All 30
> component-by-future-state violations were velocity only: vR 22 and vZ 8;
> maxima were 1.024 mm R, 0.828 mm Z, 0.0138785 m/s vR, 0.0107686 m/s vZ,
> and 36.83 A Ip. Every violation occurred at future lag 9--12.
>
> All 12 fold-local tubes contained their held rows, but all 12 exceeded the
> frozen vR and vZ caps; their worst ratios were 4.3145 and 2.1904. R also
> exceeded its tube cap in 2/12 folds. All twelve selected candidates used the
> maximum frozen PCA rank 32. No model artifact was emitted. This is a finite
> causal observer/model/data-coverage design FAIL, not a runtime, deployment,
> restart, causality, raw, reporting-route, controller, formal-control,
> real-MPC, plant, or reachability failure.
>
> Design/implementation/package checkpoints are
> `a0fa6bf / a3148a3 / e8cea14`. Local full tests and both staging/installed
> server suites passed 1176/1176; server runs had one expected isolated-data
> skip. Accepted primary detailed, summary, independent, and final-state
> SHA-256 values are respectively
> `a0db5c6db2687747ffd5de8a4a773635bfce15973e8e817eebe74a3356470a00`,
> `b8992e53a07e339015dc714377fcca57860dac3cb7b4b169d67e3623b520e364`,
> `4cb71b25ad69848349a2034fff335b9d869a56f709465be9baed6b209637f8ba`,
> and `e016c0ab9ee2c7a2f4701e553733c4392f48026f648450408cca4e19df9a9bcb`.
> Exact report SHA-256 is
> `e7d1efef0aaf227c828fe0653a8229a0444088453c0499244f26b0761aae9ad3`;
> compact evidence is under
> `docs/codex/audits/stage4_2r3c3t13s24d1r14r8r3_20260807_e8cea14/`.
>
> R8/R8R1/R8R2 authentication remained exact; R8 calibration/holdout remain
> unopened. R8R3 created zero raw and executed zero Ray, `gotsc`, TSC,
> controller, or plant advances. R8R3 is immutable. The active task is to
> prospectively freeze a new-identity fresh causal observer-identification
> campaign before any new fit, metric, or TSC. The practical finite-policy
> change may be used only prospectively on genuinely fresh development/
> holdout data; it cannot relabel R8R3. MPC, Gate A, expert data, BC, DAgger,
> and bounded residual RL remain blocked.

> **Superseding R8R3 prospective-design checkpoint (2026-08-07
> Asia/Shanghai).**  After R8R2 final independent agreement, and before any
> R8R3 feature matrix, fit, cross-validated prediction, observer metric,
> route, or artifact was computed, the next causal history no-action observer
> was frozen as R8R3.  The exact design is
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R3_CAUSAL_HISTORY_NO_ACTION_OBSERVER_DESIGN.md`,
> SHA-256
> `c55130a41f6522259d6fe9073686f0c86226c7dc11be7e93607b63f0abd0dfcb`.
> A structure-only server read in the existing virtual environment, with no
> fit or R8R3 performance metric, reconstructed 12 physical pairs, 24 history
> contexts, 96 prescribed windows, baseline lengths 36/38, and exactly 360
> eligible causal 10-history/12-future origin rows.
>
> R8R3 uses only already opened training baseline raw and runs zero new TSC.
> Its 353-dimensional deployable feature is restricted to own-trajectory
> visible history, already issued normalized actions, measured applied coil
> currents through the origin, numeric target offsets, and task clock.  It
> forbids labels, wire current, matched future, future measurement/current/
> action, and heldout outcome.  Twelve outer whole-pair folds and inner
> whole-pair selection cover a prospectively fixed 48-candidate linear/RBF
> kernel family.  All 360 outer rows must pass the unchanged component caps
> and fold-local finite tube containment; the 96 prescribed issue rows are an
> explicit subset gate.  R8 calibration/holdout remain unopened.
>
> A pass can authorize only a separately frozen zero-TSC combination with
> the already specified R8R2 innovation architecture.  A failure routes to a
> fresh causal observer-identification design.  Controller execution, MPC,
> Gate A, expert data, BC, DAgger, and bounded residual RL remain blocked.

> **Superseding R8R2 final and observer-route handoff (2026-08-07
> Asia/Shanghai).** R8R2 is final at
> `CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED`.
> Primary and structurally independent zero-new-TSC audits agree numerically
> and on the route.  The fixed causal four-state affine no-action forecast
> passed only 17/96 future windows, so the prospective all-window baseline
> gate stopped the study before any update fold, selected update lag, or
> development artifact.  Per issue state the pass counts were
> `0/24, 0/24, 11/24, 6/24` at task steps `10,14,18,22`; the maximum scaled
> error was `25.23346999999822`.  R/Z/vR/vZ/Ip violated their fixed caps in
> `20/31/61/72/0` rows.  This is a causal baseline-forecast/observer-design
> FAIL, not a runtime, restart, causality, raw, controller, TSC, real-MPC,
> formal-control, or plant-reachability result.
>
> The accepted implementation/package boundary is
> `a636583 / 3ce1e04 / c90e299`; the last checkpoint corrected only the
> descriptive R8R1 server-run identity.  Local full tests passed 1165/1165.
> Two pre-result deployment defects were preserved and rejected fail-closed:
> undeclared generated `.pyc` files in the first staging copy, then an
> absolute-path `cp --parents` installer that left nine R8R2 files missing
> and four old documentation hashes at the repository-relative paths.  The
> fresh v3 recovery used relative paths, passed 930/930 installed hashes,
> bash/compile/self-test, focused 8/8, and full 1165/1165 with one expected
> isolated-data skip.  Its unintended 930-file mirror was authenticated
> exactly before removal.  Neither defect computed an R8R2 metric or changed
> source raw, controller action, plant state, or scientific gates.
>
> R8/R8R1 authentication remained exact; R8 calibration and holdout remain
> unopened at 0/0.  R8R2 created zero raw and executed zero Ray, `gotsc`,
> TSC, controller, or plant advances.  Primary detailed, primary summary,
> independent, and final-state SHA-256 values are respectively
> `ad04374987ce4de599d71f4673ac110fe763928831e4c9610cdb117efd7977cf`,
> `05d761ef64c9e7c2373a6754184ecf42cf0a250d26ee235293e768c0416c0bb2`,
> `2ca90fab851c4131f7242bd9a5331286bde15ccaf47d251348b7d80a4597066c`,
> and `ee06726c8a5170ffd03a9465432ceed6f42053e2db8f710442c80c7809f07670`.
> Exact report and compact evidence are:
>
> ```text
> docs/codex/reports/
>   STAGE4_2R3C3T13S24D1R14R8R2_FORENSIC_REPORT.md
> docs/codex/audits/
>   stage4_2r3c3t13s24d1r14r8r2_20260807_c90e299/
> ```
>
> R8R2 is immutable; its failed affine no-action forecaster may not be tuned
> post-result.  The active task is to prospectively freeze a new-identity
> causal observer/identification design before computing any next-stage
> metric.  A development observer pass can authorize only a separately frozen
> combined online-adaptation validation.  MPC, expert data, BC, DAgger,
> bounded residual RL, and Gate A remain blocked.

> **Superseding R8R1 final and route-policy handoff (2026-08-06
> Asia/Shanghai).** R8R1 is final at
> `FIXED_CANDIDATE_SHORT_HORIZON_FAIL_CAUSAL_INNOVATION_REQUIRED`. The
> accepted audit package is `892ac7c` after focused state-path repair
> `ea4b404`; local and installed server full suites passed 1157/1157 with one
> expected isolated-data skip. The independent audit was rerun under a new
> log identity in the same immutable zero-TSC output directory. It agrees
> exactly with the primary on all horizon numerics, route, and absent model:
> 4/6/8/10/12-state response passes are `832/804/788/770/763` of 912.
> Independent SHA-256 is
> `3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c`;
> the final stage-state SHA-256 is
> `3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f`.
>
> The server postcheck strictly parsed 624/624 R8 training raw totaling
> 19,725,920 bytes; R8 calibration and holdout raw remain 0/0. R8R1 created
> no new raw or model and executed zero Ray, `gotsc`, TSC, controller, or
> plant advances. The first `KeyError: 'state'` is preserved as an
> independent-audit path/runtime defect repaired without changing scientific
> semantics. R8R1 is a fixed cold-start short-horizon response-center design
> FAIL, not a runtime, deployment, restart, causality, raw, formal-control,
> real-MPC, or plant-reachability result. The exact report and compact
> evidence are:
>
> ```text
> docs/codex/reports/
>   STAGE4_2R3C3T13S24D1R14R8R1_FORENSIC_REPORT.md
> docs/codex/audits/
>   stage4_2r3c3t13s24d1r14r8r1_20260806_892ac7c/
> ```
>
> The next causal online innovation/adaptation study is now prospectively
> frozen as R8R2 before implementation or result computation. Its exact
> design is
> `docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R2_CAUSAL_ONLINE_INNOVATION_ADAPTATION_DESIGN.md`,
> SHA-256
> `2613cd42b7b3a2e9c985c7ac1a9fd055fc20aa596e16add5a2e4c54cc8514dfe`.
> It is zero-new-TSC and keeps the matched no-action trajectory evaluator-only;
> online inputs come solely from the same probe trajectory prefix, known
> issued action, frozen cold-start prediction, and fixed causal no-action
> forecast. Whole-pair nested validation tests rolling 80 ms prediction after
> 20 or 40 ms of observations. No R8R2 metric has been viewed. Even a
> development PASS may authorize only a separately frozen fresh authentic
> interaction sentinel. MPC, expert data, BC, DAgger, bounded residual RL,
> and Gate A remain blocked.
>
> The final application policy remains safe, causal, approximate trajectory
> following rather than zero-error or universal optimality. Exact restart,
> causality, hard safety, integrity, the deterministic core formal contract,
> and prospective scientific gates are unchanged. Finite stochastic and
> continuous qualifications may use preregistered aggregate performance with
> every miss recorded and zero hard-safety violations. Pause at Gate A before
> expert-data/BC/DAgger and at Gate B before any bounded residual RL; stopping
> after a practically sufficient MPC is explicitly allowed.

> **Superseding live handoff (2026-08-05 Asia/Shanghai).** D1R14R8 is final
> at `PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP`. Its 624/624 fresh
> authentic training-extension trajectories passed runtime, exact restart,
> causal prefix/action, finite, solver, saturation, raw, snapshot, and
> independent audits. Combined with 304 immutable R2/R4/R6 responses, the
> frozen model passed only 719/912 whole-pair response rows: maximum relative
> L2 `1.5279087086`, minimum cosine `-0.1699449768`, peak ratio
> `0.1785241117--2.1303641273`. Point error, signal, and all predicted/actual
> rank-condition geometry passed; the vR tube precursor was
> `0.0101623700 m/s` against the unchanged `0.01 m/s` cap. The final
> independent audit is itself PASS but has `scientific_gate_passed=false` and
> exactly reproduces the primary scientific FAIL. Calibration/holdout remain
> 0/312 and 0/312, with no model artifact. This is a model/design failure, not
> runtime, restart, raw, reporting, real-control, or plant-unreachability
> evidence. The active task is to prospectively freeze a zero-new-TSC fixed-
> candidate short-horizon whole-pair discriminator; even a pass may authorize
> only a fresh multipulse sentinel. MPC, expert data, BC, DAgger, and bounded
> residual RL remain blocked.

> **Superseding live handoff (2026-08-04 Asia/Shanghai).** D1R14R7 stopped
> without a model result because its independent-per-lag architecture was
> undefined at weak-horizon lags 26/27 in one nested fold. The new-identity
> D1R14R7R1 continuous-lag package `3c90f21` repaired that structural defect
> and completed all four whole-pair folds with zero new TSC. Primary and
> independent results agree exactly within tolerance, but the center model
> passed only 150/256 responses: worst relative L2 `2.8666592379`, minimum
> cosine `0.1899193709`, peak ratio `0.1601688053--3.2735052329`. Point error,
> tube cap, signal 256/256, rank 64/64, and condition 64/64 passed. This is a
> response-model design FAIL, not runtime, deployment, raw, reporting,
> restart, control, or MPC failure. No controller/Ray/gotsc/TSC/plant ran.
> The active task is the prospectively frozen zero-new-TSC D1R14R7R2
> action-conditioned full-history nonlinear kernel audit over all 304 existing
> responses. A pass may authorize only fresh multi-pulse validation; MPC,
> expert data, BC, DAgger, and bounded residual RL remain blocked.

> **Superseding live handoff (2026-08-04 Asia/Shanghai).** D1R14R6 final
> package `1e62c2c` completed 48/48 fresh authentic direction-0 replacement
> probes. Primary and independent raw/snapshot recomputation agree: safety,
> exact source prefix/R4 issue state, causal issue/cancellation, and finite
> full horizons are 48/48; runtime, plant, solver, action, raw, snapshot, and
> reporting failures are zero. The combined R2/R4/R6 response bank passes
> signal 256/256, rank and condition 64/64, and issue antipodality 128/128;
> maximum condition is `12.1210121871`. Raw inventory is 48 files,
> 1,509,679 bytes, digest
> `c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83`.
> Formal tracking 12/48 is diagnostic only. The route is
> `DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED`.
> Large evidence remains server-side; compact evidence is under
> `docs/codex/audits/stage4_2r3c3t13s24d1r14r6_20260804_1e62c2c/`.
> The active task is a new, prospectively frozen zero-new-TSC causal
> deconfounded response-model fit with whole-history validation. Model, MPC,
> expert data, BC, DAgger, and bounded residual RL remain unvalidated/blocked.

> **Superseding live handoff (2026-08-04 Asia/Shanghai).** D1R10 is final as
> a finite probe-schedule safety PASS: 126/126 fresh authentic TSC raw and
> full horizons, 504/504 issue/cancel/margin events, exact restart/causality/
> calibration, no runtime/raw/snapshot/reporting failure, maximum cancellation
> increment `0.20245088117122614`, and maximum current utilization `0.392`.
> Formal tracking was diagnostic only and passed 28/126, so this is not a
> reliable MPC result. The post-run standalone-audit import hotfix produced a
> byte-identical audit and changed no experimental semantics. The active task
> is the separately frozen D1R11 full replacement identification campaign:
> 600 fresh training, 200 fresh calibration, and 200 fresh whole-pair holdout
> trajectories, ordered spec digest
> `e370269558ab079fe6d1f2293b2920b7774e3239942c7dd60ae4b638138f8c7a`.
> D1R10 raw is forbidden from fitting and expert data. MPC, BC, DAgger, and
> RL remain blocked.

> **Superseding live handoff (2026-08-03 Asia/Shanghai).** S20 is final as an
> excitation-sequence design FAIL. Its valid package-v2 run produced 24/24
> training-baseline raw: 23 complete successes and one guard-stopped partial
> trajectory before the eighth plant advance. Independent server forensics
> parsed all raw, authenticated 40/40 snapshots, passed restart/causality/
> actuator/exact-net checks for 23/23 successes, and replayed 184/184 probe
> paths without a plant advance. The failed nearest-quantized final action
> leaves coil 8 at `+0.0004 kA-turn`; the causal cumulative inverse is exactly
> representable 14/14 and passes all unchanged gates, but changes controller
> source and physical action, so S20 cannot resume. A separate stale terminal
> `phase_status` is reporting-only. Full forensic SHA-256 is
> `8a94fa842ab49a466ef3bbce07e248adb582f5abd461dca56a7bc81a1d39f890`.
> The active task is prospectively frozen S21: fresh 360-rollout identity,
> S20 steps 0--6, exact cumulative closure at step 7, then unchanged phased
> observer gates. No MPC, expert data, BC, DAgger, or RL is authorized.

> **Network-pause handoff (2026-08-03 07:45 Asia/Shanghai).**
> The user requested a controlled pause before disconnecting the network.
> The final read-only process check found no actual S20 driver, Ray campaign,
> or `gotsc` process; the only `pgrep` hit was the inspection shell matching
> its own command text.  No stop, cleanup, server file change, resume, or new
> experiment was performed.  Resume from the evidence below; do not create a
> new run or repeat completed TSC work merely because connectivity was lost.

## Active S20 forensic boundary at the network pause

Local branch and package checkpoints:

```text
branch                         codex/stage4_2r3c3t13s16-whitened-basis
S20 implementation             1861dbd
S19-authentication hotfix       9113198
installed package revision      r42r3c3t13s20_dynamic_exact_card15_pooled_observer_v2
```

Canonical remote run and logs:

```text
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s20_runs/
  stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_20260803_9113198

offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s20_offline_20260803_9113198.log

training-baseline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s20_training_baseline_20260803_9113198.log
```

The v2 offline gate authenticated S19, found zero hits among 900 prior T13
identities, passed all 40/40 snapshot and 40/40 preaction specifications,
and executed zero TSC/plant advances.  Its fingerprints are:

```text
manifest SHA-256                496f5cb5e813023faccbfb0b2ed7d299e497c1358ed9f958e2c6e06f0247dee7
initial-state SHA-256           d3cf0fe3203c87b216af8d8553e7559dfbf75534973433ea0ccb01e3790ec149
offline-result SHA-256          e6d5c5227f2c0d2e8d1a8d13902ca1bc704a3c6ed904eeec9873226ae65a2b3d
```

The training-baseline phase produced 24 raw JSON.GZ results: 23 completed
successfully and one is a correctly preserved structured partial failure.
The phase then stopped before every training probe, calibration phase, and
holdout phase.  The current terminal evidence is:

```text
state SHA-256                   940363eec1ac4b30691733571210b723146b245e8c3114543e619cc921f5ff59
training-baseline gate SHA-256  a04b4c820c6051df63d6d92848c27fa9bdef2d1a9fce15fb116002c24bc73100
raw count                       24
complete successes              23
structured partial failures      1
```

The failed specification is experiment
`s42r3c3_a40f88ad021de4a85a93`, pair
`p9_q1_a0p900_gap2_settle4`, `minus_first`, training regime D.  It completed
seven plant advances and stopped before the eighth with
`ValueError('T13S20 dynamic calibration sequence is not exact zero net')`.
The partial trajectory has eight states and seven controller-trace rows.

A zero-plant controller replay disabled only the final-net guard so that the
already planned eighth action could be inspected.  It showed that the
independently nearest-quantized eight-event sequence leaves only coil 8 at
`+0.0004 kA-turn`; every other final net component is exactly zero.  Before
the eighth action, the net is:

```text
[0.0, 0.01, 0.04, 0.02, 0.02, 0.02, 0.02,
 0.03, 0.0004, 0.024, 0.033, 0.02, 0.058, 0.048]
```

The cumulative inverse target exactly at the Card15 center is representable
on all 14 coils.  That exact candidate passes the unchanged action gates:
incremental norm `0.21480952666865222`, total norm
`0.2160478395061697`, and current utilization `0.3761`.  The first-pass
forensic output is
`analysis/s20_final_net_forensic.json`, SHA-256
`0ce1b4644fef05d029d588a6cfada32eca699b59ef41603238ae1b7676f75392`.
The server ran the earlier forensic script SHA-256
`eeb03ebfa817ab6db8459993fa75fbecaa3daadd515c1bb20114cbfc08f411c9`.

Current classification:

```text
runtime/environment error             no evidence
deployment/import error               no
raw corruption                        no evidence
partial-result reporting bug          no; preservation worked
plant restart/control conclusion      not established by the failed task
identified issue                      controller sequence-design defect
```

The 23 completed baselines have not yet received the independent full raw
audit required for restart/control claims, because the phase-level execution
gate failed closed.  Do not infer their scientific PASS from `success=true`.

The local task file `.codex_tmp/s20_final_net_forensic.py` has been extended
after the first server replay, but that revision has **not** been transferred
or run.  It is intended to compute the cumulative inverse action's frozen-
basis coordinate, cross-coordinate, cosine, and off-basis residual without
advancing the plant.  This is the first action after network restoration.
Use it to decide whether exact cumulative cancellation preserves the frozen
scientific action semantics.  If action semantics change, freeze S20 and use
a new S21 identity; do not resume S20.  If and only if the evidence proves a
pure implementation/aggregation defect with unchanged experiment identity,
controller semantics, task matrix, and physical actions, apply the repository
resume rules rather than rerunning completed raw tasks.

The earlier commit-`1861dbd` offline run failed before any TSC/raw because it
expected a legacy S19 digest.  Direct recomputation over unchanged S19 raw
proved the canonical inventory digest is
`3a2a468a92ea656b240280125ebac9b4e947d14bc3beb8e61a0fcdd82d1e01da`
(24 files, 1,300,417 bytes).  Commit `9113198` corrected only that
authentication/reporting assumption.  The empty run is preserved separately
and must not be resumed.

Large raw, snapshots, and inventories remain on the server.  Continue to
postprocess them there and download only compact evidence.  Reliable restart
MPC, expert data, BC, DAgger, and bounded residual RL remain blocked.

> Superseding live handoff (2026-08-02 Asia/Shanghai):
> Stage4.2R3c3T13S12 completed its zero-new-TSC natural-history observer
> preflight at hotfix commit `d2940b3`. The final server audit authenticated
> all 136 q1/q2 raw trajectories and passed history/current support, rank,
> fold-local whitening, interaction condition, tube, causality, and
> forbidden-input gates. Response containment passed 61/64, relative error
> 44/64, and both only 41/64; maximum scaled error was 1.701539079 despite a
> maximum interaction condition of 1.000000000000045. The final route is
> `CAUSAL_NATURAL_HISTORY_OBSERVER_PREFLIGHT_INSUFFICIENT_NONLINEAR_OBSERVER_REDESIGN`.
> One payload-target schema error and one module-path launch error are
> preserved as separate no-result, zero-plant incidents. Final result SHA is
> `1ccaaea1f8da5b5271331758a0a390c5dc663f98c5099299ff3a440007b94b4a`.
> This is an affine observer/model design failure, not runtime, raw, restart,
> reporting, controller, or real-MPC failure. The active task is prospective
> T13S13 broader same-trajectory sequence identification and recurrent or
> nonlinear set-valued observer design with a fresh history holdout. All
> MPC/expert/BC/DAgger/RL gates remain closed.

> Superseding live handoff (2026-08-01 Asia/Shanghai):
> Stage4.2R3c3T13S5 is implemented at package commit `d048686`; the local
> validation report is committed at `4d3e884`. Its frozen 68-rollout code,
> return-first cancellation audit, server postprocessor, launchers, tests,
> 307-file manifest, and checksums are complete. Local compile/JSON/hash and
> focused tests passed (13/13); the full Windows suite passed 677/677 with
> the established POSIX-`resource` shim. An empty direct-copy package passed
> 307/307 hashes and 677/677 tests with one expected isolated-data skip. The
> uncompressed package was transferred to
> `/home/yangshen0711/tsc_software/stage4_2r3c3t13s5_d048686`; staging Linux
> checks passed 307/307 hashes, all `bash -n` checks, Python/JSON/scientific
> guards, and 13/13 focused tests. The last verified installed project before
> connectivity loss was still T13S4 v1h2 with no T13S5 process. The subsequent
> install command never obtained an SSH session, and ten additional guarded
> attempts timed out before the SSH banner. Therefore installed T13S5 status
> is not claimed, no offline gate is claimed, and no T13S5 TSC/raw/result is
> claimed. On connectivity recovery: (1) read-only verify project manifest,
> four code directories, validation log, T13S5 PID/process and run/raw paths;
> (2) install from the exact staging path only if the project is still T13S4;
> (3) run installed package verification and the complete server suite;
> (4) run a fresh `COMMAND=offline` zero-plant gate; (5) only if it passes,
> launch exactly one 68-rollout T13S5 identity. Large raw must remain server-
> side. Real MPC, expert data, BC, DAgger, and bounded residual RL remain
> blocked.

> Superseding status (2026-08-02 Asia/Shanghai):
> Stage4.2R3c3T13S4 is final as
> `LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC`. Its mandatory offline audit covered
> 52/52 specifications and found 41 frozen lattice-design failures: 40 at
> issue because the four-local-step displacement exceeded the unchanged
> 0.25 incremental-action gate, and one exact Card15 cancellation failure.
> Only four baselines and seven signed probes completed offline. Raw, plant
> advances, Ray, `gotsc`, and TSC were all zero. Two aggregation/reporting
> defects were fixed under package revisions v1h1/v1h2 without changing any
> controller, threshold, schedule, or physical semantics; installed Linux
> validation passed 664/664 with one expected skip. T13S4 is an
> identification-design FAIL, not a runtime, restart, raw, plant-control, or
> MPC result. The active T13S5 design is separately frozen: 68 fresh
> trajectories, four lattice-native split directions, causal return-first
> cancellation, and the same q2 development/blind split. Its zero-TSC
> actuator preflight passed 8/8 with maximum input condition 7.9548. Real
> MPC, expert data, BC, DAgger, and bounded residual RL remain blocked.

> Superseding status (2026-08-01 Asia/Shanghai):
> Stage4.2R3c3T13S3 implemented and validated the exact quantized actuator,
> T13S2R1 development nominal plus a nonzero interval on every coil,
> immutable unknown-velocity causal restart state, strict forbidden/unknown
> field rejection, and fail-closed multi-hypothesis transition tube at commit
> `37e3913`. Local focused and isolated tests passed 15/15; the installed
> server suite passed 654/654 with one expected skip. All deployed hashes and
> the frozen predeployment 269-file package verified, and T13S3 executed zero
> TSC/plant steps. Its final route is
> `INTERFACE_COMPLETE_HOLDOUT_REQUIRED`, not point-model, observer, control,
> or robustness certification. The active T13S4 design is frozen before code
> or results. It uses dynamic symmetric Card15 field steps over the q2 pairs
> withheld from T13S1/T13S2R1, with `plus_first` development and
> `minus_first` blind until a hashed model/tube exists. Real MPC, expert data,
> BC, DAgger, and bounded residual RL remain blocked.

> Superseding status (2026-08-01 23:58 Asia/Shanghai):
> Stage4.2R3c3T13S2 completed a zero-new-TSC audit of all 52 immutable T13S1
> raw files. Exact Card15 target-current reconstruction matched 13,000/36,400
> observed current components at `1e-9 A`; maximum residual was `1.0e-5 A`,
> so its frozen route is `ACTUATOR_MAPPING_IMPLEMENTATION_GAP`. It found 8
> exact causal-feature collision groups, 0 same-feature/same-applied-path
> groups, 0 exact observational aliases, and finite clean separation in all
> 24 matched-history pairs. This does not validate observer robustness.
> T13S2R1 then used only four baselines to identify a fixed TSC-order
> readback-bias vector `[2,2,2,2,2,2,2,1,0,0,0,1,0,0] * 1e-6 kA-turn` and
> reproduced all 33,600 signed-probe components within `1e-9 A`; this is a
> retrospective development split, not an independent holdout. Both audits
> ran 0 TSC/plant steps, and server validation passed 639 tests with 1
> skipped. The active stage is the prospectively frozen offline T13S3
> quantized causal multi-hypothesis/tube interface. Real MPC, expert data,
> BC, DAgger, and residual RL remain blocked.

> Superseding status (2026-08-01 23:22 Asia/Shanghai):
> Stage4.2R3c3T13S1 completed its one authorized real campaign at remote run
> `stage4_2r3c3t13s1_runs/stage4_2r3c3t13s1_minimal_transition_sentinel_20260801_ecc05f6`.
> All 52/52 fresh `gotsc` trajectories completed successfully; the immutable
> raw inventory is 52 JSON.GZ files, 2,463,366 bytes, digest
> `de2be508888aa503628538a795474fbf70788252e7913f87af7603c5bc034603`.
> Exact restart, causality, solver, scheduler, current, rank, condition,
> snapshot, package, raw-parse, and summary-recomputation gates passed. The
> frozen scientific gates did not: central symmetry was 0/24 and matched
> hidden-history response was 0/12, although all corresponding absolute
> response gates passed. The official route is therefore
> `SENTINEL_FAIL_STOP_IDENTIFICATION`. This is an identification/model/action-
> resolution design failure, not a runtime, restart, raw-corruption,
> reporting, or real-MPC failure. The experiment must not be rerun or enlarged
> under the same identity, and its probe trajectories remain forbidden from
> expert data. The final read-only forensic at commit `9b8353d` completed on
> the server with 4/4 focused tests and the full 639-test suite passing (one
> skipped). It executed zero TSC/plant steps. Requested command symmetry was
> 24/24, but actual first-effect current symmetry was 0/24, immediate plant
> symmetry 3/24, full-window plant symmetry 0/24, immediate matched history
> 6/12, and full-window matched history 0/12. Of 336 active compared command
> components, 304 were below one Card15 `.3E` grid. Twenty compact evidence
> files were downloaded and authenticated; all 52 raw JSON.GZ remain on the
> server. The active task is the prospectively frozen, zero-new-TSC T13S2
> exact Card15 and causal-observability audit. T11 bank, R3c4, real MPC, BC,
> DAgger, and residual RL remain blocked.

> Superseding status (2026-08-01 Asia/Shanghai): Stage4.2R3c3T13 completed
> its no-new-TSC source architecture and time-resolved model audit. The V4
> audit authenticated 1,408 immutable R3c3/T1/T2/T6/T9/T11 raw files
> (62,444,406 bytes) in place. Causality and first-effect state passed
> 1,504/1,504, but the fixed Stage3.4 lifted Jacobian passed 0/576 signed,
> 0/896 finite-node, and 0/32 interaction prediction comparisons because
> every response failed the frozen relative time-shape gate. There was no
> runtime, deployment, raw, snapshot, statistics, reporting, restart, or
> causality error and no new controller/TSC run. T13 ends as
> `MINIMAL_SENTINEL_REQUIRED`; this vetoes the fixed Jacobian as an
> unqualified restart predictor, not the plant or global reachability. The
> 52-rollout Stage4.2R3c3T13S1 single-step transition sentinel is now frozen
> prospectively but is not implemented, authorized, or run. A sentinel PASS
> permits only offline model work; a scientific FAIL stops campaign
> expansion. R3c4, real MPC, BC, DAgger, and residual RL remain blocked. See
> `STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_REPORT.md`,
> `STAGE4_2R3C3T13_RESTART_MPC_ARCHITECTURE_SPEC.md`, and
> `STAGE4_2R3C3T13S1_MINIMAL_TRANSITION_SENTINEL_DESIGN.md`.

> Superseding status (2026-08-01 Asia/Shanghai): Stage4.2R3c3T12 completed a
> read-only authentication of all 416 immutable T11 raw files. It reproduced
> the exact 12/4/13/3 formal-versus-condition cross table, 0/16 measured
> single-probe repairs, 0.47%--11.46% best gap coverage, and one regression in
> 192 passing-baseline probe corners. There was no runtime, packaging, raw,
> snapshot, statistics, or reporting error and no new plant/controller run.
> T11 remains a 25/32 identification-design FAIL; the condition-first fixed
> response-basis route is vetoed. The active stage is the no-new-TSC
> Stage4.2R3c3T13 finite-horizon restart MPC architecture/evidence map. It may
> end only with an offline architecture specification or a separately frozen
> minimal sentinel requirement. R3c4 and BC/DAgger/residual RL remain blocked.
> See `STAGE4_2R3C3T12_FORMAL_GAP_ROUTE_DISCRIMINATOR_REPORT.md` and
> `STAGE4_2R3C3T13_FINITE_HORIZON_RESTART_MPC_ARCHITECTURE_PLAN.md`.

> Superseding status (2026-07-31 Asia/Shanghai): T9 completed a clean
> 224/224 mixed-interaction identification, and T10 then authenticated those
> raw trajectories in a preregistered six-term interaction-aware offline
> audit. Model fitting passed 32/32, but formal feasibility stayed 16/32 with
> 0/16 repairs. Every failed optimum was an exact measured T9 factorial
> corner, so interpolation and reporting explanations are excluded. The
> axis de-aliasing campaign and R3c4 are vetoed. The active route is a new
> time-localized transport-versus-braking response identification; no
> amplitude expansion, BC, DAgger, or residual RL is allowed. See
> `STAGE4_2R3C3T10_INTERACTION_AWARE_FEASIBILITY_REPORT.md`.

> Superseding status (2026-07-31 Asia/Shanghai): T6 completed 224/224 but
> failed its combined-bank design gate after a reporting-only hotfix. T7
> repaired conditioning but remained 16/32 with 0/16 repairs. T8 then
> expanded only the three new target directions through 4× under
> independently recomputed 14-coil current constraints; every scale
> remained 16/32 and maximum predicted current stayed 0.3904. Thus current
> headroom is not the bottleneck, R3c4 remains unauthorized, and the active
> route is a new target-relevant temporal/actuator combined-action
> identification preflight. See `docs/codex/CURRENT_TASK.md` sections
> 12--14 and `STAGE4_2R3C3T8_HEADROOM_DIAGNOSTIC_REPORT.md`. No T8 TSC,
> Ray, `gotsc`, controller or plant run occurred.

## Stage4.2R3c3T1 failed cleanly; Stage4.2R3c3T2 is preregistered

Status timestamp: 2026-07-31 Asia/Shanghai

Current local branch:

```text
codex/stage4_2r3c3t1-transport-response
```

Current checkpoints:

```text
b8e66da  preregister T1 transport response
ba8c455  implement and deploy T1 campaign
```

## T1 real result

Remote run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_runs/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Remote audit:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t1_audits/
stage4_2r3c3t1_long_separation_zero_net_transport_identification_20260730_204441
```

Compact local evidence:

```text
docs/codex/audits/stage4_2r3c3t1_result_20260730_204441/
```

Result:

```text
raw / execution / exact restart / causal             128/128
central symmetry                                       64/64
matched history                                        32/32
transport-only condition                               32/32
combined rank six                                      32/32
combined condition <= 25                               27/32
worst combined condition                          29.2962711
runtime / restart / causal / solver errors                  0
maximum current utilization                           0.3904
formal probe diagnostic pass/fail                      56/72
```

T1 is frozen as FAIL because of the preregistered combined-condition gate.
Formal tracking was diagnostic-only and was not used to change that result.

Fingerprints:

```text
runtime/audit package
  cea1e49470afed77387cdf3d636de38541c47998846a817edc32dafd9b60f44a

raw inventory
  f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f

run inventory
  159ee8f85fc07fec52280cb0f153a75d5f24b8bf69629502f8177b7810567c52

server audit
  0f24b44f32493b390832474d5c78cc2455a8ba0c455b496b16c04f8deaf3a2bd
```

No T1 task was resumed or rerun after completion.

## T1 forensic classification

```text
runtime/environment error                    no
package/deployment error                     no
raw/snapshot corruption                      no
T1 statistics/reporting error                no
plant restart failure                        no
real MPC control result                      not tested
identification-design failure                yes
```

The first read-only six-basis feasibility tool used position arrays for the
velocity condition calculation. Its invalid output is preserved with SHA
`a19169f1...`. Corrected v2 exactly reproduces the T1 27/32 condition count
and 29.2962711 maximum before computing formal feasibility:

```text
corrected diagnostic
  e7bc8f0168ff1d2019f1a9a232b5152a27d46a66a92f9542d31d80c6942c3164

optimistic six-basis formal pass               16/32
failed baseline contexts repaired               0/16
best remaining failed margin                -0.0458576
worst remaining failed margin               -0.3456933
```

Reducing transport mode 0 to scales 0.85, 0.80, 0.75, or 0.70 repairs
conditioning to 32/32 but leaves formal feasibility at 16/32. An
amplitude-only T2 is therefore vetoed before execution.

Full T1 report:

```text
docs/codex/reports/STAGE4_2R3C3T1_FORENSIC_REPORT.md
```

## Active T2 design

Prospective design:

```text
docs/codex/reports/STAGE4_2R3C3T2_PREREGISTERED_DESIGN.md
```

Frozen schedule:

```text
observation horizon                    50 steps / 500 ms
positive physical effects             states 3..8
negative physical effects             states 39..44
observation tail                       states 45..50
held transport mode 0 amplitude       0.0060
held transport mode 1 amplitude       0.0075
signed probe tasks                    128
```

Pre-implementation design review found that the 500 ms symmetry metric needs
a real baseline beyond the 350/370 ms source horizon. Design revision 2
therefore adds one zero-probe extended baseline per context:

```text
extended baselines                     32
signed probes                         128
total real TSC tasks                  160
```

No T2 code, offline run, server deployment, or real TSC preceded this
prospective correction.

The first negative physical effect is after both original formal hold
endpoints. Arrival remains due by 250/270 ms and formal hold remains through
350/370 ms. The longer run is identification-only, not a later deadline or
long-hold success.

Next implementation steps:

1. create a focused T2 branch and implementation checkpoint;
2. implement standalone config/module/launch/postprocess/tests;
3. complete local compile/JSON/full-test/import/package/empty-copy checks;
4. deploy directly without archives and validate the canonical server tree;
5. run the 160-spec offline no-TSC audit;
6. launch exactly one real T2 identity;
7. postprocess large raw server-side and download only compact evidence;
8. require T2 identification gates, then six-basis optimistic feasibility
   32/32 before any R3c4 implementation.

## Still unvalidated

A reliable restart MPC expert, independent histories and initial states,
unseen targets, continuous actuator and plant variation, noise, observer,
disturbance recovery, and independent long hold remain unvalidated.

BC, DAgger, and bounded residual RL remain prohibited.

## Stage4.2R3c3T9 preflight handoff

The post-T8 PC3/mixed-action preflight is complete at commit `cbb970b`.
No T9 TSC was executed.

```text
preflight gates                                      all PASS
PC3 singular value normal / weak            1.134704 / 0.777812
minimum four-direction coverage             0.999912 / 0.995362
complete action rank / condition             12 / 2.551060
selected action rank / condition              9 / 1.230022
factorial common amplitude                         0.0106066
prospective real task count                                224
```

Exact compact output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t9_preflights/
stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b/
stage4_2r3c3t9_pc3_mixed_interaction_preflight_v1.json

SHA-256
9a37168cce679df7deeb242bceb996c11f41bf9e589459e27386ece45f41e560
```

The active work is implementation of the frozen independent real
identification matrix:

```text
32 extended baselines
64 standalone PC3 signed probes
128 direct stress-by-PC3 factorial probes
```

This preflight does not authorize R3c4. Reliable MPC, independent unseen
histories/targets, continuous parameters, noise, disturbance recovery, and
independent long hold remain unvalidated. BC, DAgger, and residual RL remain
prohibited.

## Stage4.2R3c3T9 real-identification live handoff

The frozen 224-task T9 implementation is committed at `15e7033`. The
cross-process adapter/reporting-only hotfix is committed at `b489acc`:

```text
package revision
  r42r3c3t9_pc3_mixed_interaction_identification_v1h1

controller revision
  pc3_mixed_interaction_probe_v42r3c3t9_v1

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t9_runs/
  stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005

real launch log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090158.log

launch PID
  1618922
```

The v1h1 offline audit passed all 224 specs with zero plant advance. Server
validation passed 13/13 focused tests and 596/596 complete tests.

The real run produced its first result after about 1900 seconds. At the
first-batch boundary, 128/128 raw files decoded successfully:

```text
success / completed                                  128/128
Stage4.2R3c3T9 identity                              128/128
51-state trajectory / 50-row trace                   128/128
solver failures / forbidden-input rows                     0
abnormal trajectory rows                                   0
wire-current count in every recorded state                  48
```

The last remotely verified live state was:

```text
time                                      2026-07-31 17:51:54 +08:00
PID 1618922                                                   alive
raw files                                                   128/224
active second-batch gotsc processes                              96
main-log fatal/exception count                                    0
```

After that check, a read-only SSH poll hung and the server reset the
connection. Repeated direct SSH attempts then timed out before
authentication; the configured `tsc-airgap` hostname also remained
unresolved locally. This is an external connectivity/availability blocker,
not a TSC, Ray, controller, restart, statistics, or reporting result.

No new run, resume, stop, cleanup, postprocess, or server mutation was
performed after connectivity was lost. When access returns:

1. inspect PID `1618922`, the exact run above, raw count, full launch log,
   state, summary, and verdict;
2. do not create a new identity;
3. if all 224 raw are present, run the independent server postprocessor
   before deploying any later package;
4. if fewer than 224 raw are present, first establish the exact interruption
   cause and v1h1 package/source compatibility before any semantics-preserving
   resume;
5. keep large raw and snapshots on the server and download only compact
   audits, manifests, state, summaries, verdicts, and logs.

The earlier v1 run is separately classified by a compact forensic audit:

```text
run
  stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_083514_15e7033

raw decoded                                              224/224
structured startup failures                             224/224
trajectory / controller-trace lengths                         0/0
raw inventory digest
  05052110c7575c43d176fb42c63ca7c3a6480673113da0c0d86d0f9ee1519845

compact audit SHA-256
  45dbbabc7bdcfaad3fa2f2e0e1aa587edbd42e0f9fc30db31748198aee78b205
```

That v1 event is a Ray-worker contract installation/runtime code defect plus
a reporting-robustness defect. It contains no real TSC trajectory and yields
no plant, restart, or control conclusion.

## Stage4.2R3c3T9 final resolution

The connectivity incident ended without any server intervention. The exact
v1h1 run continued to 224/224 and produced complete summary/state/verdict
files. PID `1618922` exited normally and no T9 or `gotsc` process remains.

Independent server-side raw/snapshot postprocessing and a second strict raw
scan found:

```text
raw strict / successful                                  224/224
51-state trajectory / 50-row trace                       224/224
48-wire states                                      11424/11424
snapshot integrity                                           8/8
runtime / restart / causality / solver / forbidden errors       0
reported summary exact on recomputation                       yes
```

The final result is identification PASS and fixed-linear-route FAIL:

```text
standalone symmetry                                       32/32
PC3 history                                                16/16
mixed response                                             32/32
mixed history                                              16/16
nine-basis condition <=25                                  32/32
maximum condition                                      23.155208
mixed ratio <=0.10                                          2/32
PC3 modulation <=0.10                                       0/32
```

Load-bearing hashes:

```text
raw inventory
  e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2
server audit
  05547765ca5e1282e58b0d33e454b0a2a4dd87ee16e85146261650510ebd05f8
```

Large raw and snapshot trees remain on the server. The active local work is
the prospectively frozen interaction-aware offline model audit. R3c4 and all
BC/DAgger/RL work remain unauthorized.

## Stage4.2R3c3T11 corrected offline-preflight handoff

T10's measured-corner authority failure led to a new six-direction
persistent transport/braking step schedule. T11 remains offline-only and has
executed zero real tasks.

Current branch and commits:

```text
branch   codex/stage4_2r3c3t11-persistent-step-preflight
design   3798a21
rank fix 0b61f93
source fix / installed package v2  a9807b9
```

Final validation before connectivity loss:

```text
local complete tests                                610/610
local empty-package focused tests                     14/14
server package hashes                                228/228
server focused tests                                   14/14
server complete tests                                610/610
server validation log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t11_installed_validation_v4_a9807b9.log
SHA-256
  8ef47cb218cc5bc006675e567bc2734f08f4d37c11019c5119f4aed3142e57a3
```

The initial Linux validation failure was CRLF in `SHA256SUMS`; no Python
test ran. Two later T11 invocations stopped with no output JSON because the
old 12-column matrix was reconstructed from the wrong same-shape T7 bank.
Forensics separated a numerical rank-scaling bug from the decisive source
reference bug. Package v2 now uses the exact T3 bank authenticated by T9:

```text
6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86
```

No invocation ran Ray, `gotsc`, TSC, a controller, or any plant step. There
is no T11 PASS/FAIL or plant conclusion yet. The corrected v3 path and log
have not been created by Codex because four subsequent SSH connections timed
out before authentication/session establishment.

Next action after connectivity recovery is one guarded run of
`run_stage4_2r3c3t11_preflight.sh` into
`stage4_2r3c3t11_persistent_step_preflight_v3_20260731_a9807b9`, followed by
server-side inspection and download of only the compact JSON/log. Do not
implement or launch the prospective 416 real tasks unless that exact
corrected preflight passes every frozen gate.

## Stage4.2R3c3T11 preflight final resolution

Connectivity recovered. The guarded corrected v3 paths were absent, and one
offline preflight completed successfully. Both actuator cases passed rank,
conditioning, novelty, bound, and zero-net gates. Maximum condition was
`3.1459620743`; minimum novelty residual was `0.7726912050`.

The compact JSON SHA-256 is
`a449fd5447bd174b5fa067f464c651bc5a1d3e146bae7f67d22535eed076dfbd`.
No real TSC, Ray, `gotsc`, controller, or snapshot was executed.

The active work is the independently implemented 416-task real
identification identity. R3c4 and all BC/DAgger/RL work remain prohibited.

## Stage4.2R3c3T11 authentic identification final result

The package at commit `40944f9` passed local and server validation, the
offline no-plant audit, and then completed all 416 real TSC tasks once. The
campaign used fixed batches `128 + 128 + 128 + 32`; all 416 raw files parse
and pass execution, exact restart, causality, schedule/application,
zero-net, solver, and forbidden-input checks.

Independent server postprocessing authenticated 8/8 snapshots, the exact
runtime package and manifest, and the reported summary. The only failed gate
is six-basis response conditioning:

```text
central symmetry                                      192/192
matched hidden-history response                         96/96
rank 6                                                  32/32
condition <= 25                                         25/32
maximum condition                                   38.9150751
maximum current                                      0.3904/0.55
```

Independent raw differencing/SVD matches the report to `4.97e-14`. This is a
clean identification-design FAIL, not a runtime, restart, raw, snapshot,
solver, reporting, or real-MPC failure. Formal tracking is diagnostic only:
207/416 overall and the unchanged 16/32 extended baselines.

Large raw and full inventories remain server-side. Compact local evidence is
under
`docs/codex/audits/stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9/server_compact/`.
The detailed report is
`docs/codex/reports/STAGE4_2R3C3T11_PERSISTENT_STEP_IDENTIFICATION_REPORT.md`.

Do not build the T11 response bank or R3c4. The active route is a new
prospectively frozen time-localized identification design that improves
weak-mode authority and separates the p9/minus near-collinear responses
without post-hoc normalization, amplitude-only rescaling, threshold changes,
or formal-timing changes. BC, DAgger, and residual RL remain prohibited.

## Current handoff: S18 complete, S19 active

Stage4.2R3c3T13S18 completed its development-only pooled observer preflight.
All 128 held rows passed the frozen tube and unchanged caps, the eight fold
hashes and saved predictions were exact, and independent server raw
recomputation matched.  It ran zero new TSC or plant steps.  Exact evidence is
in `docs/codex/reports/STAGE4_2R3C3T13S18_FORENSIC_REPORT.md`.

The active work is the separately frozen Stage4.2R3c3T13S19 prospective
campaign.  Its 20 whole-pair identities have zero hits in 900 parsed prior T13
identification raw files.  S19 uses 12 training, four calibration, and four
unopened holdout pairs for 360 real identification rollouts, with model and
tube hashes at the two phase boundaries.  No real MPC, expert data, BC,
DAgger, or residual RL is authorized.

## Current handoff: S23 final, schedule redesign active

The installed S23 package at commit `7aab947` passed package verification and
887 server tests with one expected skip. Its zero-TSC preflight completed
twice with byte-identical detailed, summary, and manifest hashes. S21 source
authentication and all 360 raw formal reproductions passed, but the frozen
dense Hadamard schedule passed only 1,920/3,840 issue gates and 3,720/3,840
cancellation gates. Rank, condition, novelty, exact target, zero-net,
current, and finite checks otherwise passed.

The exact final route is
`SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_FAIL_SCHEDULE_REDESIGN`. This is an
action-schedule-design failure with zero real controller or plant execution.
The detailed 10.86 MB output remains server-side; compact evidence and the
complete classification are in
`docs/codex/reports/STAGE4_2R3C3T13S23_FORENSIC_REPORT.md`.

S24 is vetoed. Active work is a new-identity, zero-TSC adaptive schedule
search followed by a separately frozen preflight. No new real campaign, MPC,
expert dataset, BC, DAgger, or residual RL is authorized yet.

## Current handoff: S23D1 final, S23R1 active

S23D1 completed its full 128,000-event catalog and 100,000-schedule bounded
search twice with byte-identical artifacts. Every issue step had 103/160
feasible sign pairs and steps 10--17 had 40/40 cancellation feasibility, but
none of five knot sets produced a random schedule with global condition at
most 3. The best requested condition was `7.2966498190`. This is a zero-TSC
schedule-architecture FAIL, not a plant or MPC result.

The active design is the separately frozen S23R1 amplitude-coded Hadamard
preflight. It uses fixed knots `10,13,15,17`, amplitudes `0.25` for the two
already-good Walsh patterns and `0.50` for the other two, and changes no
fidelity/action/current/formal gate. S23R1 must pass actual-coordinate replay
in all 40 contexts before any real sequential identification campaign can be
designed. S24, MPC, expert data, BC, DAgger, and RL remain unauthorized.

## Current handoff: D1R4 final, D1R5 active

Stage4.2R3c3T13S24D1R4 completed nine authentic real-TSC prefixes from package
checkpoint `da3f4b4`. All nine exactly restarted, reproduced the D1R2 prefix
and D1R3 0.175 split start, and advanced the plant once. Every causal state-19
exact-center finish required intervention 0.2712316553--0.3540255817 and was
rejected before application by the unchanged 0.24/0.25 gates. There were no
runtime, raw, snapshot, restart, causality, saturation, or current failures.
No trajectory reached the formal endpoint, so formal tracking was not run to
completion rather than failed 0/9.

The prospective audits' success-only aggregate omitted executed structured
prefix metrics. Reporting-only checkpoint `69dedc0` recomputed restart,
causality, calibration, source prefix, and split start as 9/9 and left the
route unchanged:

```text
CAUSAL_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED
```

The active stage is the zero-new-TSC D1R5 recursive split-return preflight. It
is prospectively frozen to use each authenticated state-19 measurement only
causally, construct another exact 0.175 intermediate, execute no plant step,
and authorize at most the design of a new real sentinel. Identification, MPC,
expert data, BC, DAgger, and RL remain unauthorized.

## Current handoff: D1R5 final, D1R6 active

D1R5 final package checkpoint `7389154` completed two byte-identical
zero-new-TSC outputs. The primary and independent tools each authenticated and
replayed 9/9 D1R4 rows, reproduced all nine rejected direct finishes, and
constructed the current-state-only exact-Card15 0.175 continuation in 9/9.
There were no forbidden inputs, new raw, snapshots, Ray, `gotsc`, TSC, or
plant steps. Five output JSON hashes matched exactly across the repeat.

The first two invocations exposed the same resume-only historical-package
authentication bug in the primary and then independent tool. Both are
preserved; neither ran TSC or advanced a plant. Fixes `b8626c1` and `55e7720`
changed only historical source authentication. Local and final server complete
tests passed 965/965, with one expected server skip.

The exact report is
`docs/codex/reports/STAGE4_2R3C3T13S24D1R5_FORENSIC_REPORT.md`. Compact
evidence is under
`docs/codex/audits/stage4_2r3c3t13s24d1r5_20260803_7389154/`; D1R4 raw stays
server-side.

The active design is D1R6, frozen before implementation in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R6_REAL_TSC_RECURSIVE_RETURN_SENTINEL_DESIGN.md`.
It permits exactly nine fresh 35-step authentic sentinels. Step 19 applies the
known-safe continuation, later continuations are causal and bounded, and an
exact-center finish is mandatory by task step 22. A pass permits only design
of a full replacement identification campaign. MPC, expert data, BC, DAgger,
and RL remain unauthorized.

## Current handoff: D1R6 final, fixed schedule redesign active

D1R6 execution package checkpoint `4177aa2` completed all nine authentic TSC
sentinels. Raw inventory is 9/9, 422133 bytes, digest
`351f7484bd3ec2f68f76cc2f17ea6bc93a6227e2078b8be2f0cdf9e84055fd89`.
Restart, causality, calibration, physical state/action/trace prefix, split
start, and first D1R5 continuation are exact 9/9. Every row safely executed
0.175 continuations at steps 19, 20, and 21, then stopped before applying an
unsafe step-22 finish. No full horizon or formal endpoint was reached.

The final route is
`CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED`. There were no
real-run runtime, solver, raw, snapshot, saturation, current, or forbidden
input errors. A reporting-only audit at `c33a368` corrected the physical
source-prefix count from 0/9 to 9/9 by excluding only two runtime timing
fields; route and experiment semantics are unchanged.

Large raw remains on the server. Compact hashes were verified after direct
download to
`docs/codex/audits/stage4_2r3c3t13s24d1r6_20260803_4177aa2/`. The exact report
is `docs/codex/reports/STAGE4_2R3C3T13S24D1R6_FORENSIC_REPORT.md`.

The active work is a zero-new-TSC, fixed-global sequential schedule redesign
and discriminator. It must preserve all geometry, action/current, rank,
exactness, forbidden-input, and formal-timing gates and may authorize at most
a fresh real safety sentinel. The full replacement campaign, MPC, expert
data, BC, DAgger, and RL remain blocked.

The D1R7 design has now been frozen before implementation in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R7_TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_DESIGN.md`.
It fixes the direction-2 timing basis `++++, +--+, -+-+, --++`, requested
matrix digest
`c4430a13b679ad8dcceb72c259051a5eebad03da47d86816d46c4385cd811d77`,
and 108 prospective specs. D1R7 is offline-only and may authorize only a
separate D1R8 design after double deterministic primary/independent replay.

## Current handoff: D1R7 final, D1R8 active

D1R7 final implementation/package checkpoints are `da578de` / `0c2311a`.
One initial accepted-output attempt stopped before output because the primary
reader incorrectly required all 54 authentic S24 cancellation failures at
slot 3/task step 18. Direct raw reconstruction found the unchanged valid
distribution `12,16,4,22` over slots/steps `(0,11),(1,14),(2,16),(3,18)`.
The primary and independent hotfix changed authentication/reporting only;
Ray, `gotsc`, TSC, controllers, and plant steps remained zero.

The final official runs are byte-identical across all five outputs. D1R7
authenticated 600 S24, 54 D1R2, and 9 D1R6 raw; passed 7,680 finite static
constructions, 3,840 issue, 3,840 cancellation, 1,280 central, 40 global, 160
slot, and 40 late gates; and froze 108 unique D1R8 specs. The route is
`TEMPORAL_BASIS_SUBSTITUTION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED`.
Exact report and compact evidence are in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R7_FORENSIC_REPORT.md` and
`docs/codex/audits/stage4_2r3c3t13s24d1r7_20260803_0c2311a/`.

The active D1R8 design is frozen before implementation in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R8_REAL_TSC_TEMPORAL_BASIS_SENTINEL_DESIGN.md`.
It permits exactly 108 fresh real-TSC safety sentinels over six rows and 18
contexts. A pass may authorize only design of a full replacement
identification campaign. MPC, expert data, BC, DAgger, and RL remain blocked.

## Current handoff: D1R10 final, D1R11 source-auth hotfix validated locally

D1R10 completed 126/126 authentic full-horizon sentinels with exact restart,
causality, calibration, issue/cancel/margin gates, no runtime/raw/snapshot
error, and a formal tracking diagnostic of 28/126. It authorized the
prospectively frozen 1,000-rollout D1R11 replacement identification campaign;
the probe data remains forbidden from expert datasets.

D1R11 implementation/package checkpoints `79d3c0a / 571b932` passed the
initial local and server package validations. Its first zero-TSC `offline`
invocation stopped before output because source authentication read the
nonexistent D1R9 field `primary_pass` instead of its official top-level
`passed` field. Every other D1R9 hash, matrix, row classification, route, and
independent audit check matched. No raw, controller, TSC, or plant step ran.

Source-authentication-only checkpoint `027f555` fixes the field lookup and
adds an official-schema regression test. Focused tests pass 8/8; the complete
local suite passes 1023/1023 when run with the repository's Windows `resource`
compatibility shim. The direct unshimmed discovery attempt is invalid on
Windows and produced 27 Unix-module import/collection errors; it is not a code
test failure. D1R11 remains at its mandatory zero-TSC gate pending hotfix
package deployment and server validation. MPC, expert data, BC, DAgger, and
RL remain unauthorized.

## Current handoff: D1R11 final, causal transition redesign active

D1R11 package checkpoint `05c8521` completed all 600 fresh training
trajectories. Independent server-side raw and snapshot recomputation found
600/600 exact authentic restarts and causal traces, 600 strictly parsed raw,
zero runtime/solver/action/current/corruption/report errors, and inventory
digest `8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7`.
Large raw and snapshots remain server-side; compact evidence is under
`docs/codex/audits/stage4_2r3c3t13s24d1r11_20260804_05c8521/`.

The frozen training-model phase evaluated all 24 L/SA/Q and ridge candidates.
All failed. The selected L/ridge-1 candidate reproduced 532/600 formal
diagnostics and had maximum recursive scaled error `0.9580646071` versus the
unchanged `0.1` limit. Calibration and fresh holdout were not run: 0/200 and
0/200, with no model or tube hash. The route is
`FULL_REPLACEMENT_TRANSITION_TRAINING_MODEL_FAIL`, a transition-model/design
failure rather than a runtime, restart, report, real-control, or plant result.

D1R11 is immutable. The active task uses only its 600 training raw as consumed
development data for a new-identity, zero-TSC causal architecture study. The
unopened D1R11 calibration/holdout remain forbidden. Whole-pair validation,
the 0.1 recursive point gate, tube caps, forbidden inputs, safety gates, and
formal timing remain unchanged. No fresh campaign is authorized until a new
architecture passes independent deterministic replay. MPC, expert data, BC,
DAgger, and bounded residual RL remain blocked.

## Current handoff: D1R14 final, D1R14R1 zero-TSC redesign preflight active

D1R14 v1 package `2d5304c` produced all 72 strict raw. Eight baselines reached
the full horizon; all 64 probes stopped before applying their state-10 issue.
All exact Card15, actuator, action, current, restart, prefix, runtime, plant,
raw, and snapshot checks passed. The stop was caused by inherited S24 dense-
row predicates that are structurally incompatible with the frozen D1R14
one-hot coordinates. Therefore v1 contains no signed plant response and no
geometry or MPC conclusion.

The immutable raw inventory is 72 files / 1,841,053 bytes / digest
`bf07f39c4b83666a48f545d89ab4c7cff18f6ef473a89133b7afd99fd34321df`.
Independent audit SHA is
`3a6958c2519da4d43e0d910a51d33c0c971352e01a2f68578c1bc4b6b6750e2b`.
The exact classification and v2 gate boundary are in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R14_V1_ISSUE_GATE_HOTFIX_AUDIT.md`.

The v1 run is frozen and will not resume. The fresh v2 package `d32761c`
subsequently completed 72/72 authentic TSC tasks. Exact restart/prefix, safety,
finite rows, issue/cancel, zero-baseline reproduction, raw, snapshot, runtime,
plant, solver, saturation/clipping, forbidden-input, and report checks all
passed. Its raw inventory remains on the server: 72 files / 2,239,479 bytes /
digest `0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3`.

The preregistered response geometry genuinely failed: signal 24/32, symmetry
27/32, rank 8/8, condition 7/8, minimum odd peak `0.0005766750`, maximum
even/odd `0.7567864`, and maximum condition `20.5851685`. The primary final
SHA is `1a65a37c301ba52325f586e0948b0b94b1266c540e2f2a332e5bc02df60a7da2`;
independent audit SHA is
`8e7d3d045477502c1060fe621f2c43235e1d530b59c5d22849337dd20aac3eae`.
Formal tracking 18/72 is diagnostic only.

The active work is a separately frozen D1R14R1 zero-new-TSC deterministic
mixed-basis recomputation and exact static Card15 issue preflight. A pass may
authorize only a fresh D1R14R2 real safety/geometry sentinel. MPC, expert data,
BC, DAgger, and bounded residual RL remain blocked.

D1R14R1 package `36f0d41` is now final. Source authentication and deterministic
search passed, with predicted minimum odd peak `0.006` and maximum condition
`3.7020780`. Static issue construction passed 48/64. The 16 failures were only
the third mixed direction's off-basis residual (`0.1359745 > 0.10`) in both
signs and all contexts; all action/current/exactness gates passed. No TSC or
plant/controller execution occurred. Route:
`POOLED_MIXED_BASIS_PREFLIGHT_FAIL_REDESIGN_REQUIRED`.

Development diagnosis found the first 0.025-grid feasible third-column scale
at `1.275`, with 64/64 static passes and maximum issue/idealized cancellation
`0.1401852`. Active work is a new frozen D1R14R1A zero-TSC replay of this fixed
candidate before any D1R14R2 real sentinel is authorized.

## Current handoff: D1R14R1A final, D1R14R2 design active

D1R14R1A implementation/package checkpoints are `58912e7 / b8040b6`. The
formal server replay authenticated the complete D1R14R1/D1R14 source chain,
matched fixed matrix digest
`c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c`,
and passed all 64/64 exact static issue constructions. Predicted minimum odd
peak was `0.005999999999999252`, maximum condition `3.7020780012`, maximum
off-basis residual `0.0990759019`, and maximum issue/linearized cancellation
increment `0.1401851852`. New raw, TSC, controller, and plant-step counts were
all zero.

The route is
`QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED`. Online
state-11 cancellation and plant response remain unvalidated. The compact
evidence and exact classification are under
`docs/codex/audits/stage4_2r3c3t13s24d1r14r1a_20260804_b8040b6/` and
`docs/codex/reports/STAGE4_2R3C3T13S24D1R14R1A_FORENSIC_REPORT.md`.

The active work is to freeze and implement D1R14R2 as a new 72-case authentic
safety/geometry sentinel over eight zero baselines and 64 signed fixed-mixed-
basis probes. It must validate the task-step-11 causal cancellation under both
the 0.24 prospective margin and original 0.25 cap before evaluating the
unchanged D1R14 geometry. Even a pass authorizes only a separate time-
distributed zero-baseline identification design. MPC, expert data, BC,
DAgger, and bounded residual RL remain blocked.

## Current handoff: D1R12 final, D1R13 zero-increment sentinel active

D1R12 read only the immutable 600-file D1R11 training boundary. Its accepted
stable causal innovation-state-space script hash is
`bfa98bcc602635dbb3ba32f0e527757dc117efbed83ee41a44bb426f8cb9231d`.
All 54 exact-kinematic, spectrally bounded candidates failed whole-pair
validation. The selected rank-12/ridge-1/radius-0.995 candidate reached
maximum recursive scaled error `0.83230558404196`; no point or tube candidate
passed. Forbidden, future-action, and future-measurement predictor counts were
all zero. New raw, Ray, TSC, and plant counts were all zero.

The route is
`STABLE_CAUSAL_INNOVATION_STATE_SPACE_DEVELOPMENT_FAIL_DECONFOUNDED_IDENTIFICATION_REQUIRED`.
This isolates a D1R11 absolute closed-loop transition-target design failure,
not a restart, runtime, report, control, real-MPC, or plant-unreachability
result. The exact report and compact JSON are under
`docs/codex/reports/STAGE4_2R3C3T13S24D1R12_CAUSAL_ARCHITECTURE_FORENSIC_REPORT.md`
and `docs/codex/audits/stage4_2r3c3t13s24d1r12_20260804/`.

The active D1R13 design is frozen before implementation in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R13_ZERO_INCREMENT_DECONFOUNDING_SENTINEL_DESIGN.md`.
It fixes eight authentic fresh-TSC baselines. Each must reproduce the D1R11
calibration/state-0--10 prefix, then issue exactly zero 14-coil current
increments to the unchanged state-35/37 horizon. Formal tracking is
diagnostic. A pass may authorize only a bounded zero-baseline excitation
sentinel design. MPC, expert data, BC, DAgger, and RL remain blocked.

## Current handoff: D1R13 final, D1R14 zero-baseline excitation active

D1R13 package checkpoint `df3910f` completed all 8/8 authentic trajectories.
All source restart/state/action/trace prefixes through state 10 were exact;
all 208 post-prefix actions and all coil-current increments were exactly
zero; all trajectories reached their 35/37-state horizons with finite R/Z/Ip,
coil and wire-current records. Runtime, plant-abnormality, solver,
saturation/clipping, forbidden-input, raw, snapshot, and report error counts
were zero. Maximum current utilization was `0.3904`. Formal tracking was
diagnostic only and passed 2/8.

The final route is
`ZERO_INCREMENT_DECONFOUNDING_SENTINEL_PASS_EXCITATION_SENTINEL_DESIGN_REQUIRED`.
The server raw inventory remains in place: 8 files, 241,738 bytes, digest
`f9b4dd9259736ebe2d26f9fcfd06bb0497be69a886de7ecc8d359009992f1c0a`.
Only compact evidence was downloaded to
`docs/codex/audits/stage4_2r3c3t13s24d1r13_20260804_df3910f/`.

Read-only design evidence proved the old D1R11 signed paths are confounded by
continuing R17 feedback and moving Card15 centers; they are not valid
responses about the D1R13 zero baseline. The active D1R14 design is frozen in
`docs/codex/reports/STAGE4_2R3C3T13S24D1R14_ZERO_BASELINE_SIGNED_EXCITATION_SENTINEL_DESIGN.md`.
It fixes 72 fresh trajectories: one zero baseline and eight signed probes per
context over eight contexts. A pass authorizes only design of a separate
time-distributed zero-baseline identification campaign. MPC, expert data, BC,
DAgger, and bounded residual RL remain blocked.

## Current handoff: D1R14R2 implementation locally validated

D1R14R2 is frozen before outcome inspection at design SHA-256
`5344a7436277c18d3a85a750d5516c69595c6d84090d47f9cc01af85b888896a`.
Its local implementation and structurally separate independent forensic now
cover the fixed mixed-matrix issue, causal stored-center cancellation, exact
zero continuation, source/R1A authentication, immutable resume identity, raw
and snapshot reconstruction, and unchanged response geometry. All 503
repository JSON files parsed, compileall passed, focused tests passed 15/15,
and the complete repository suite passed 1072/1072.

No D1R14R2 server deployment, offline run, controller, plant step, `gotsc`, or
TSC execution has occurred yet. The next safe boundary is package construction
and empty-tree validation, followed by installed-server validation and the
mandatory zero-TSC offline gate. MPC, expert data, BC, DAgger, and bounded
residual RL remain blocked.

## Current handoff: D1R14R2 final, sign-split feasibility redesign active

D1R14R2 implementation/package checkpoints `e7fe6c8 / ca2815a` completed the
full local-server-download-analysis loop. The 72 raw remain server-side with
inventory digest
`c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649`.
Primary and independent audits agree on 72/72 safety, 64/64 exact issue and
causal cancellation, 8/8 baselines, and zero runtime/restart/plant/solver/
raw/reporting errors.

The geometry route is a real design FAIL: symmetry 28/32 and maximum even/odd
`0.8528017842`, despite 32/32 signal and 8/8 rank/condition. The four failures
are confined to the matched `p9_q2_a0p900_gap3_settle4` histories. Exact
antipodal issue coordinates/fields exclude action quantization asymmetry.

Posthoc development analysis found 16/16 separate sign branches signal-bearing,
rank four, and conditioned below 20, but this does not alter the failed verdict
or authorize a campaign. The next task is to freeze and independently run a
zero-TSC sign-split feasibility audit. MPC, expert data, BC, DAgger, and RL
remain blocked.

## Current handoff: D1R14R3 final, D1R14R4 design active

D1R14R3 final package `ca49a36` completed a zero-new-TSC server raw audit.
The initial `85012c1` output remains frozen as `SOURCE_FAIL_NO_TSC` because of
one expected state-file SHA transcription error; the correct hash was already
present in pre-R3 checkpoint `73c5811`. Erratum checkpoint `aa3325a` changed
only that expected fingerprint and created a fresh v2 output.

Corrected primary/independent outputs passed and agree exactly. They preserve
R2's 28/32 central-symmetry FAIL, while the separate positive/negative branch
architecture passed signal 64/64, rank 16/16, condition 16/16, and exact issue
coordinate/field sign symmetry 32/32. Minimum signal is
`0.005310999999896815`; maximum condition is `9.55784063525667`. No new raw,
controller, plant, Ray, gotsc, or TSC ran.

Active work is the prospectively frozen D1R14R4 fresh time-shifted
sign-split safety/identification design. No model, MPC, expert-data, BC,
DAgger, or RL work is authorized yet.

## Current handoff: D1R14R4 final, D1R14R5 zero-TSC preflight active

D1R14R4 package `f5b8348` completed all 200 authentic TSC tasks. Raw count,
strict parse, success, safety, finite/full-horizon, and causal trace counts are
all 200/200; issue/cancellation is 192/192 and baseline reproduction is 8/8.
There are no runtime, restart, plant, solver, saturation/clipping, forbidden-
input, raw/snapshot, or reporting errors. All 200 raw files remain server-side
(6,285,765 bytes; digest
`44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9`).

The authentic response geometry failed only two direction-signal columns:
both signs of direction 0 at issue step 18 for the minus member of
`p9_q2_a0p750_gap4_settle4` measured `0.004465` and `0.004298` versus the
unchanged `0.005` floor. Signal is 254/256; rank and condition pass 64/64,
maximum condition is `11.5700741087`, and issue coordinate/field antipodality
is 128/128. Independent forensics exactly reproduce the failure route. This
is a real local identification-signal design failure, not a real control or
MPC result.

R4 is frozen. Active work is the new-identity D1R14R5 zero-TSC exact safety
preflight for a globally fixed 1.5x direction-0 candidate. It cannot use
context/history labels and cannot prove plant response or online cancellation.
The preregistered design SHA-256 is
`8383ef5e0cf7678adcf9f3c776fbe925e7b57b8e6e9398eae13bff35e1f5b400`.
Only a pass may authorize a separately designed 48-probe authentic sentinel.
All model/MPC/expert/BC/DAgger/RL routes remain blocked.

## Current handoff: D1R14R5 final, D1R14R6 real sentinel active

D1R14R5 package `a4c43bb` completed its zero-new-TSC server-side static
preflight and independent recomputation. It authenticated 272 immutable
source raw files in place, matched candidate digest
`69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8`,
and passed 48/48 exact issue constructions and 24/24 coordinate/field
antipodal pairs. Maximum issue and ideal return increments were both
`0.17481481481481495`, maximum predicted current utilization was `0.3799`,
and maximum off-basis residual was `0.05794563546539851`.

The final route is
`GLOBAL_DIRECTION0_GAIN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED`.
No new raw, plant, controller, Ray, gotsc, TSC, or formal-control evaluation
occurred. Earlier launcher/PYTHONPATH failures and report-order comparisons
are preserved as non-scientific errors; no accepted result or physical
semantics changed.

Active work is D1R14R6, frozen prospectively at design SHA-256
`aa59b97868ae74b9a7e5d19e76f5541b3d5ed36dc5c75cc57ddd839d535a9b5b`.
It is a fresh 48-rollout authentic direction-0 replacement sentinel over all
eight contexts, task steps 14/18/22, and both signs. A pass can authorize only
a separate causal transition-model-fit design. MPC execution, expert data,
BC, DAgger, and RL remain blocked.

## Current handoff: D1R14R7R2 final, D1R14R8 implementation active

D1R14R7R2 design/implementation/package checkpoints are
`5d35db2 / bcde159 / 995d81c`. Local empty-package, server staging, and
installed validation passed 898/898 hashes, focused 5/5 tests, and the full
1,136-test suite. The zero-TSC server audit read all 320 authenticated source
raw in place and created no raw, controller, Ray, gotsc, TSC, or plant step.

Primary and independent outputs agree exactly. R7R2 improved the canonical
R2/R4 subset to 200/256 and passed 36/48 R6 amplitude rows, but the final
236/304 response result still failed frozen relative-L2/cosine/peak gates.
Point error was 304/304, the tube passed, signal was 304/304, and canonical
plus operational rank/condition were each 64/64. The final route is
`ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED`.
This is a pair-coverage/model-center design failure, not runtime, raw,
restart, report, control, plant, or real-MPC evidence.

The exact report and compact evidence are:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R7R2_FORENSIC_REPORT.md
docs/codex/audits/
stage4_2r3c3t13s24d1r14r7r2_20260804_995d81c/
```

The new R8 partitioned broader-response design is frozen at final
pre-implementation SHA-256
`c225c6163fbf2146772fdabf100a34b13a3c6d59ee416f605698598acdc2022f`.
It adds eight fixed training pairs, then permits four calibration pairs only
after a model hash and four holdout pairs only after a tube hash. Maximum new
raw is 1,248, with later phases fail-closed. Active work is independent R8
implementation and full validation. MPC, expert data, BC, DAgger, and RL
remain blocked.
