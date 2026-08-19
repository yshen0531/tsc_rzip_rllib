# R_geo/Z_geo 轨迹控制新路线：架构提案与研究边界

> **ID-2Z4R1 architecture freeze (2026-08-19):** exact one-ms observation,
> exact Card15 execution, persistent causal history and independent hard
> gates remain unchanged. The immediate finite search is moved upstream from
> state 97 to the exact state-93 prefix so that capture-switch timing is part
> of the decision rather than an unexamined consequence of five greedy
> p07-only selections. A fixed twelve-branch frontier combines p07-minus,
> bounded p03-unwind and dwell without clipping or simultaneous over-slew.
> An earlier state-89 draft was rejected at zero TSC because it had only
> 98.8 A target headroom; the 100-A floor was preserved.
>
> The stage evaluates absolute terminal capture; matched hold is optional
> descriptive evidence because the hold branch may legitimately leave the
> 25-mm runtime envelope before the common terminal window. Any finite PASS
> still requires fresh exact replay and Recourse-L1 before feedback control.
> Any finite FAIL closes only the frozen frontier and triggers an action-basis
> and terminal-objective review, not another manual macro-depth ladder. The
> resulting compact data may support development of a short-horizon,
> truth-recentered history model, while calibration/holdout and controller
> safety evidence stay fresh and separate.
>
> **Historical ID-2Z4 architecture freeze (2026-08-19):** the next bounded branch set
> time-shares p07-minus braking and p03-unwind second-axis action after the
> exact state-97 prefix. Twelve capture issues and twelve held-tail issues
> separate transient velocity arrest from capturable low-speed behavior.
> A six-state 25-mm/0.1-m/s/5%-Ip result is still only a finite sequence
> candidate; replay, uncertainty and recourse remain separate gates.
>
> **Historical post-ID-2Z3 architecture amendment (2026-08-19):** repeated p07-minus
> ramps provide finite braking authority but their held command is not a
> terminal or recoverable set. The architecture must separate transport,
> velocity arrest, and capture/hold actions. The next finite branch search
> uses exact Card15 time allocation between a braking direction and a
> second-axis/capture direction at the selected state-97 prefix. A branch
> result can nominate a sequence only; fresh replay, uncertainty and
> independent recourse remain mandatory before feedback control.
>
> **Historical ID-2Z3 architecture freeze (2026-08-19):** the high-level architecture
> remains exact one-ms observation and actuation, persistent causal belief,
> explicit uncertainty, reference governance and an independent hard safety/
> recourse layer.  The immediate discriminator is a bounded five-decision
> canonical-prefix braking search, not another fixed p03 depth and not a
> learned world model.  Each round measures hold, p03-forward4 and
> p07-minus4, observes an eight-ms tail, commits only the selected four-issue
> macro and replans from the resulting logical prefix.
>
> The selector prioritizes terminal four-state speed while bounding geometry
> regression and paired Ip.  A 25-mm/0.1-m/s/5%-Ip coarse stabilization gate
> is intentionally weaker and differently named than the historical 5-mm
> source short-hold gate; it can authorize only fresh repeat and recourse
> design.  Model/calibration evidence needs a new prospective identity, and
> no finite branch PASS may be promoted to feedback, recovery, waypoint or
> R_mid-crossing qualification.

> **Post-ID-2Z2 architecture amendment (2026-08-19):** exact one-ms
> paired-boundary observation, exact Card15 actuation, complete post-takeover
> causal history, explicit uncertainty and an independent hard safety layer
> remain unchanged. Two consecutive canonical-prefix decisions both select
> p03-forward4; p07-minus4 remains a lower-Ip eligible alternate. This proves
> finite repeated transport utility only. The selected path still has a
> material terminal error and speed, so it cannot be promoted to hold,
> terminal-set or recovery evidence.
>
> The immediate architecture task is a bounded rolling source-hold/braking
> search that starts from the selected two-macro causal prefix and evaluates
> a small exact action alphabet against matched hold. It must optimize
> persistent absolute geometry together with terminal speed and Ip, stop at a
> finite budget, and treat every rejected branch as simulator route evidence.
> It is not another fixed manual-depth ladder. Only a separately qualified
> hold/recourse result may open a source-local feedback controller; model and
> calibration data need a new prospective identity.

> **Post-ID-2Z1 architecture freeze (2026-08-19):** exact one-ms paired-boundary
> observation, exact Card15 actuation, causal history, explicit uncertainty
> and independent hard safety remain the architecture. ID-2Z1 supplied two
> finite useful transport macros at one late causal prefix, but neither is a
> hold, recovery policy or two-axis authority proof.
>
> The immediate stage is a two-decision canonical-prefix rolling branch
> campaign. It converts the first useful macro into measured receding-horizon
> decisions instead of extending another manual action-depth ladder. Each
> decision compares the same finite action alphabet against a matched hold,
> executes only the selected first four-issue macro in the logical main path,
> and retains all sibling branches as route evidence. A PASS can nominate a
> finite two-macro transport sequence and define the next hold/braking search;
> it cannot replace the future uncertainty-aware feedback model or independent
> recourse layer.
>
> **ID-2Y1R1 repair freeze (2026-08-19):** the original ID-2Y1 action matrix
> was rejected before TSC because two combinations fell below its own 95 A
> current-headroom gate. The gate is retained. A separate R1 identity replaces
> only those actions with two exact combinations at 95.8/95.2 A. This is an
> excitation-design repair, not a post-result scientific threshold change.
>
> **Post-ID-2Y1R1 architecture freeze (2026-08-19):** exact one-ms
> observability, Card15 actuation, causal history, explicit uncertainty and
> independent hard safety remain unchanged. Four late mixed ramps executed
> exactly but all met negative-R clearance before the hold window. Manual
> ramp-depth tuning is closed.
>
> The immediate architecture task is a same-prefix macro utility comparison,
> not a larger model. ID-2Z1 compares p03 forward/unwind and p04/p07 both
> signs against a matched hold baseline and requires persistent absolute
> progress over states70--73. This supplies a finite action alphabet for a
> later rolling sequence optimizer. It remains simulator-development evidence;
> model uncertainty, recourse and controller qualification stay separate AND
> gates.
>
> **Post-ID-2X1 architecture freeze (2026-08-19):** exact actuation, exact
> one-ms observation, causal history, explicit uncertainty and independent
> hard safety remain unchanged. ID-2X1 proves only that three fixed residual
> allocations around p03 level32 do not create a finite nominal hold. All
> branches stopped at preissue clearance with exact execution; no actuator,
> plant, model or global reachability theorem follows.
>
> ID-2Y1 performs one final hand-designed allocation test around the stronger
> p03 level64 transport. It begins p04-minus/p07-plus braking only after p03's
> full-slew increments finish, so the 0.3 A contract is never shared or hidden
> by clipping. If this finite schedule set fails, the architecture must move
> from manual ramp depth selection to bounded sequence/control-utility search
> and eventually measured-feedback rolling control. It must not start another
> micro-probe or network-capacity ladder.
>
> **ID-2X1 architecture freeze (2026-08-19):** both level52 and level64 p03
> holds reached the finite negative-R clearance before the terminal window.
> The p03-only allocation is therefore closed. The next bounded discriminator
> keeps the useful p03 level32 transport prefix but allocates sustained action
> time to p04-minus and p07-plus, whose measured signs address positive-R and
> negative-Z needs. Exact-TSC branches test these schedules directly; no model
> or linear superposition is presumed. Only a complete mixed branch with a
> stable states88--96 tail can nominate the next nominal candidate.
>
> **Historical ID-2W3R1 architecture freeze (2026-08-19):** ID-2W3 level52 hold
> was stopped by the finite 25 mm R clearance before its terminal window;
> exact action/current and independent raw gates passed. This did not yet
> decide the unstarted level64 branch, which ID-2W3R1 isolated under a new
> identity.
>
> **Historical ID-2W3 architecture freeze (2026-08-19):** the high-level
> architecture remains exact actuation plus exact one-ms observations, causal
> history, calibrated uncertainty and constrained rolling control. The
> selected p03 direction is not promoted to a nominal hold model: extending it
> through level78 did not improve the source distance after state32 and
> increasingly exchanged Z correction for negative-R drift.
>
> Before replacing the actuator basis, ID-2W3 freezes one finite two-level
> braking test at the already observed level52 and64 prefixes. Both branches
> hold their exact Card15 target through state96 and share the states88--96
> terminal hold gate. This distinguishes a delayed useful hold tail from a
> permanently moving p03-only path. It is the final p03-only discriminator.
> If it fails, later models must learn/control a new multi-direction allocation
> rather than approximate the rejected p03 ladder.

> **Historical post-ID-2W1 architecture amendment (2026-08-19):** retain exact actuation,
> exact one-ms observations, causal history, uncertainty-aware rolling
> control, and the separation between simulator development and controller
> qualification. ID-2W1 shows that allocating more time to p04/p07 makes the
> response measurable, but not persistently two-axis at adjacent common
> states. It also exposes a material cost from pausing the selected p03
> transport.
>
> Therefore the near-term nominal and residual problems must not be conflated.
> ID-2W2 therefore extends the selected p03 moving nominal once, from its
> measured level-31 horizon through level 79, and identifies transport,
> slowdown and braking locations under finite empirical stops. Only
> then design time-multiplexed residual sequences around that contemporaneous
> nominal. A transient state-25 positive span is useful sequence evidence,
> not a general actuator basis or recovery proof. Models resume only after a
> useful nominal/sequence target exists.

> **Historical ID-2W1 architecture freeze (2026-08-19):** before returning to model
> comparison, test one finite cumulative residual grammar at a common causal
> prefix. The grammar time-multiplexes p03 transport and a six-step p04/p07
> residual ramp, then performs an exact residual return and delayed p03
> catch-up. Uninterrupted and paused baselines expose the transport cost.
>
> Utility must exist at the same non-hybrid states for the four signed arms,
> persist across consecutive one-ms observations, and leave a bounded tail.
> A state-27 spike, asynchronous per-action peaks, or action ranking below
> the equivalence floor cannot establish authority. The result remains only
> an action-grammar gate before model, uncertainty, recovery and controller
> work.

> **Post-ID-2V0 architecture amendment (2026-08-19):** retain the exact
> actuator/queue, one-ms exact R_geo/Z_geo/Ip observation, causal memory,
> uncertainty, reference-governor and constrained rolling-control backbone.
> Change the immediate order: demonstrate a useful finite action grammar
> before collecting more histories or fitting another response model.
>
> The measured p04/p07 exact-return pulses are excitation primitives. Their
> horizon-8 effect is below `0.6%` of moving-nominal displacement and their
> terminal effect is below `0.019 mm`. A bounded same-prefix multi-arm branch
> campaign must therefore test sequence-level absolute progress,
> persistence/capture, Ip/current cost, and return/resume continuity. Only
> branch choices with real control utility become targets for a later
> support-gated model. Authority, recourse and controller qualification
> remain separate prospective gates.

> **Historical post-ID-2U2 architecture amendment (2026-08-18):** the exact actuator,
> moving nominal, exact one-ms observation, causal memory and constrained
> rolling-control architecture remains unchanged, but model qualification
> cannot proceed from a development split with zero arrival-pace variation.
> The local/event candidate failed response and ranking and the small GRU
> residual regressed, so capacity is not the next lever.
>
> Before another comparison, add one prospectively distinct development
> arrival history at each existing nominal-level/probe-time corner. Keep the
> original paced calibration and blind schedules unopened. The later model
> should remain support-gated and low capacity, with a persistent causal
> history residual retained only after whole-family gain. Authority and
> recovery remain separate AND gates before any controller.

> **Post-ID-2U2 control-utility amendment (2026-08-19; supersedes the
> automatic expansion above):** the exact actuator/queue, exact one-ms
> R_geo/Z_geo/Ip observation, causal memory, uncertainty,
> reference-governor, and constrained rolling-control backbone remains
> unchanged. The immediate order changes: an action grammar must show
> persistent, distinguishable control utility before more history data are
> collected solely to predict it.
>
> ID-2V0 is a zero-TSC/zero-fit decision audit. If the existing p04/p07
> exact-return grammar has adequate sustained utility, it may freeze one
> minimal history-support extension. Otherwise it must move finite
> same-prefix multi-arm TSC branch evaluation ahead of another model. p03 is
> a transport primitive, p04/p07 pulses are excitation primitives, and none
> is presumed to be the final control action. A later learned model amortizes
> useful branch decisions; it does not replace independent authority,
> recourse, calibration, or hard-safety gates.

> **ID-2U2 architecture freeze (2026-08-18):** the first model comparison
> after nominal realignment remains deliberately low capacity. Candidate A
> is a support-gated local mixture with separated moving-nominal continuation
> and paired action response plus stable event memory. Candidate B adds only
> a width-three persistent causal GRU residual. Both use exact current
> R_geo/Z_geo/Ip as a one-ms recentering anchor and share one-step dynamics
> across horizons 1--8. Family labels, future truth/current and wire state
> are forbidden inputs. A model PASS remains only one half of later
> model-plus-authority/recovery AND gates.

> **Post-ID-2U1 architecture amendment (2026-08-18):** the moving-nominal
> campaign confirms that the large delayed branch is sparse and conditional,
> not a universal smooth gain. The first candidate therefore uses explicit
> time, nominal level, event age, stable action memory, and support/OOD gates;
> the second is only a small persistent causal sequence residual that receives
> the same deployable history and exact current observations. Both predict
> deviation around the contemporaneous moving nominal and recenter every
> one-ms observation. A larger global world model is not a candidate.

> **Post-ID-2U0 architecture amendment (2026-08-18):** exact Card15
> pause/probe/return/resume allocation is the first admissible residual
> grammar around the selected moving p03 nominal. U0 froze a fresh 8-family,
> 40-stream campaign and separate development/calibration/blind roles without
> fitting a model or advancing TSC. The next model must learn action-
> conditioned deviations around the contemporaneous moving nominal, with
> explicit absolute time/event age and persistent causal history. State 27
> remains a guarded hybrid candidate until the fresh matched campaign decides
> whether it needs an explicit event head or OOD refusal.


> **ID-2U0 architecture correction (2026-08-18):** retain exact
> actuator/queue semantics, exact one-ms R_geo/Z_geo/Ip observations, causal
> history/belief and uncertainty-aware rolling control, but move the
> experimental centre back to ID-2C1's selected moving p03 stride-one
> nominal.  The held-after-issue-15 corridor was a local identification
> device, not the best measured transport.  Residual actions must be
> allocated by an exact Card15 grammar (for example pause/probe/return/resume)
> because the moving nominal already consumes the full `0.3 A` slew on some
> coils.  State-27 is treated as a guarded hybrid/return-edge event until
> prospective matched evidence says otherwise.  ID-2U0 is zero TSC and zero
> fit; only a fresh moving-nominal campaign may follow a passing preflight.

> **Post-ID-2T1 amendment (2026-08-18):** a common p04+ continuation after
> four exact state-30 histories was repeatably measurable but wrong-way for
> source-error correction in all four cases. The small cross-history spread
> and the contrast with its earlier issue-24 response require explicit
> time/evolving-state/action-age conditioning; they do not prove whether time,
> position or hidden passive memory is the isolated cause. Stop the open-loop
> sequence-extension ladder. Next use a zero-TSC attribution only to freeze a
> prospective fit-eligible timing/history campaign, then compare a small
> support-gated time/state-scheduled model. Offline canonical-source shooting
> remains a teacher/search tool, not a 1 ms online Oracle.

> **Historical post-ID-2S2 amendment (2026-08-18):** all four measured f03 two-arm
> trajectories and their paired responses reproduced exactly in a fresh TSC
> replay and independent full-raw audit. This qualifies finite deterministic
> canonical-source replay for bounded offline shooting design, not a 1 ms
> online Oracle and not a probabilistic transition tube. The next candidate
> search must optimize absolute time-resolved tracking/hold utility and hard
> margins directly; it may use the old additive construction only as a
> nomination heuristic and may not fit S1/S2. Any measured shooting PASS
> remains below residual reserve, bounded-tube recourse and controller gates.

> **Historical post-ID-2S1 amendment (2026-08-18):** Real two-arm sequence responses
> passed the finite time-resolved 2-D geometry and Ip discriminator, but two
> histories showed roughly `0.70 mm` R interaction relative to summing their
> isolated arms. The architecture must therefore treat action age, return
> edges, and the evolving causal state as dynamics inputs. Static pulse
> addition remains an action-search heuristic only. Fresh exact replay and a
> finite residual reserve are required next; neither two repeats nor exact
> digital-twin determinism may be promoted to a probabilistic safety tube.

> **Post-ID-2S0 amendment (2026-08-18):** The zero-TSC sequence selector
> nominated four exact two-arm f03 branches and passed independent
> recomputation. Its additive geometry is only a branch-reduction heuristic.
> The next stage measures those four sequences in fresh TSC development
> identities and explicitly reports interaction relative to the heuristic.
> Even a measured positive-span time series is not yet authority or recourse:
> a fresh replay/tube and residual-margin qualification remain separate AND
> gates before any controller or transport claim.

> **ID-2S0 architecture discriminator (2026-08-18):** the route now separates
> three objects explicitly: measured single-sequence evidence, a fixed no-fit
> additive branch nominator, and future real two-sequence TSC branches. Only
> the third can test sequence interaction. ID-2S0 chooses four branches under
> exact Card15 and directional-coverage gates while running zero plant work.
> It cannot establish authority or revive model calibration.

> **Historical post-ID-2R1 architecture discriminator (2026-08-18):** exact replay
> confirms that f03's sign/return-edge response is a repeatable finite hybrid
> behavior, not a one-off solver sample. The same-data global model ladder
> stays stopped. The next architecture discriminator is a bounded
> canonical-prefix short-sequence branch test that asks whether this exact
> action grammar supplies useful time-resolved two-axis progress.
>
> A fixed no-fit additive construction may nominate a small branch set, but
> it is not a plant model and cannot certify a sequence. Only the fresh TSC
> branches may support sequence utility, and even their PASS remains below
> repeatability/tube, residual reserve, Recourse-L1, and controller gates.

> **Historical ID-2R1 architecture discriminator (2026-08-18):** ID-2R0 preserved the
> global Q1R1 model FAIL but found a sharp support boundary: exact-schedule
> local causal-prefix transfer is highly accurate on `52/64` cells, while
> `f01/f03/f05` are singleton schedule strata. The unreplayed `f03` family is
> uniquely decisive because all four global-model response directions fail
> there.
>
> The immediate experiment is an integrity-only exact `f03` replay, not more
> training data. A repeatable `f03` anomaly moves sequence/time-dependent
> action utility and canonical-prefix shooting ahead of another surrogate;
> a mismatch stops before learning from that label. Even a replay PASS does
> not establish positive-span control authority, recovery, or a terminal
> set. Those remain independent AND gates before constrained rolling control.

> **Historical ID-2R0 architecture correction (2026-08-18):** Q1R1's final model FAIL
> is retained, but its prose family attribution is corrected from
> `h01/h03/h05` to the actual singleton schedule strata `f01/f03/f05`, with
> all four q03 ridge wrong-way responses in `f03`. No Q1 gate or result is
> changed.
>
> The immediate architecture discriminator is one bounded zero-new-TSC
> audit, not another learned model. It measures explicit local causal
> support and time-resolved action geometry. If the unreplayed `f03`
> singleton is decisive, it receives only an exact zero-weight replay. If
> supported local prediction is stable but schedule support is missing, data
> expansion is targeted. If supported histories still flip or the action
> grammar lacks useful sequence authority, canonical-source finite shooting
> moves ahead of another surrogate. A local model is considered only after
> both support and action utility exist. Fresh calibration and independent
> recovery remain later AND gates.

> **Historical post-ID-2Q1R1 architecture amendment (2026-08-18):** neither the global
> stable shared-response map nor its small persistent GRU residual generalized
> across the 16 whole-history families. Absolute short-horizon prediction was
> often adequate, but paired response, direction, action ranking and feature
> support failed. This ends the same-data global-model ladder; it does not
> reject exact-observation receding control or machine learning in general.
>
> Before another model or TSC campaign, separate local support from model
> form. If nearby complete causal histories predict response, use a small
> support-gated local mixture/LPV model with explicit OOD refusal. If the
> failing histories lack neighbors, collect only a targeted matched bridge.
> If neither route is reliable, qualify finite canonical-prefix TSC shooting
> earlier as an Oracle/teacher candidate. Fresh calibration, authority and
> recovery remain independent later gates.

> **Historical post-ID-2P1 model amendment (2026-08-18):** the missing matched duration,
> timing and history data passed all execution and independent raw gates.
> ID-2Q1 v1's zero-model preflight found that exact signed Card15 execution
> produces a rank-three subspace, not an ideal rank-two plane. ID-2Q1R1
> preserves the same evidence split and gates while retaining all three
> executed coordinates. It compares exactly two small models on 16 whole-history
> families: a stable shared-increment causal backbone and that same backbone
> with a bounded persistent GRU residual. Exact current R_geo/Z_geo/Ip remain
> direct noiseless inputs at each origin; the latent state represents response
> memory and future uncertainty, not measurement noise.
>
> Multi-horizon outputs are cumulative shared dynamics and must pass absolute,
> paired-response, direction and action-ranking gates. A PASS freezes one
> development model only. Fresh calibration, blind whole-history holdout,
> uncertainty, two-axis authority and recovery are still independent AND
> gates before any controller. Source-local 34 ms evidence is not position,
> transport, hold or R_mid-crossing evidence.

> **Historical post-ID-2O0 data amendment (2026-08-18):** the model comparison remains
> capped at two candidates, but it is blocked until ID-2P1 supplies the
> missing independent history and duration support. ID-2P1 is a balanced
> matched-baseline factorial campaign over the already admitted p04/p07
> Card15 action family; it is not a random 14-dimensional sweep and is not
> controller safety evidence.
>
> On PASS, K1 and P1 may train the shared-latent candidates. N1 calibration
> remains consumed challenge evidence and cannot become fit labels. A new
> calibration and genuinely new blind whole-history holdout remain mandatory
> after model freeze. Authority and recovery are still independent later AND
> gates.

> **Historical post-ID-2N1 readiness amendment (2026-08-18):** do not jump directly from
> fresh calibration failure to a larger recurrent model. The architecture
> first separates effective independent whole-history support from repeated
> transition/end-point rows. ID-2O0 audits deployable causal history,
> paired-response/event-age support, and action-ranking utility without fitting
> a model or running new TSC.
>
> If support passes, compare only (1) an explicit nominal plus stable
> low-order shared latent/belief response model and (2) that same backbone plus
> a small persistent causal GRU/TCN residual. Exact current R_geo/Z_geo/Ip,
> recent finite differences, actual/readback current and owned action/queue
> history are causal inputs; future readback and evaluator labels are not.
> Direct 1--8 ms outputs must share latent dynamics and obey cross-horizon
> consistency rather than acting as eight unrelated heads. If support fails,
> collect a single prospectively fit-eligible matched-factorial campaign
> instead of widening the network or reusing consumed probes.
>
> Fresh model calibration/holdout, two-axis authority, and recovery remain
> independent AND gates. Source-local 34 ms evidence does not establish
> multi-position scheduling, hold, transport or R_mid crossing.

> **Historical post-ID-2N1 architecture amendment (2026-08-18):** fresh calibration
> rejected the context-invariant fixed event-memory predictor before blind
> holdout. Exact actuator/queue semantics and exact 1 ms R_geo/Z_geo/Ip
> observation were intact; the failure is the future response representation.
> Two probe cells in the same fresh c01 history reversed paired response
> direction and several
> hold/return/tail phases were shifted relative to the frozen convolution.
>
> The architecture therefore keeps explicit nominal continuation but moves
> the learned response component to a genuinely causal state/current/action-
> history encoder with direct 1--8 ms predictions. The next bounded comparison
> should contain at most (a) stable low-order memory plus a small TCN residual
> and (b) a small GRU/TCN with persistent, non-rewritten history. Current truth
> is a direct input/recentering anchor, not a latent estimate; future readback
> and evaluator labels remain forbidden. Fresh calibration, a new blind
> whole-history holdout, two-axis authority, and recovery remain successive
> independent gates before constrained rolling control.

> **Post-ID-2M1 architecture amendment (2026-08-18):** the selected finite
> development predictor is now explicit time-indexed nominal plus stable
> signed/even Card15 memory and finite causal edge/dwell/return/tail features.
> It is re-centered on exact current R_geo/Z_geo/Ip at every real control
> cycle. It does not use evaluator labels or future readback.
>
> The attempted 12-dimensional observation/current innovation correction is
> rejected because its good one-step fit became catastrophic under 2/4 ms
> recursion. Exact observation remains an interface fact and a replanning
> anchor, not evidence that arbitrary state feedback features are safe.
> Fresh groupwise calibration and blind whole-history holdout now precede all
> use in constrained planning. Model validation still does not prove
> authority or recovery.

> **Historical post-ID-2M0 architecture amendment (2026-08-18):** exact attribution
> retains the signed/even fixed-pole model only as an action-response head.
> A complete candidate must separate shared nominal continuation from causal
> edge/dwell/return/tail dynamics and consume current exact R_geo/Z_geo/Ip
> through a small bounded innovation state. Actual-versus-issued current may
> enter only causally; future readback remains forbidden.
>
> ID-2M1 is capped at two small candidates and whole-history folds. Original
> cell weighting stays authoritative while unique-prefix and worst-event
> metrics prevent repeated sibling prefixes from hiding the mechanism. The
> flawed GRU recenter evaluator is not reused. A development PASS still
> precedes fresh calibration and new blind holdout; model evidence cannot
> substitute for two-axis authority or recovery evidence.

> **Historical ID-2M0 architecture correction (2026-08-17):** ID-2L1's best
> `stable_signed_even` model is retained only as a source-local probe-response
> component. It is an exogenous time/action-memory model: one-ms truth is an
> integration origin rather than a dynamics input, and actual-current
> innovation is unused. This falls short of the already confirmed
> exact-observation + low-order belief architecture.
>
> The short-horizon FAIL is localized to a few repeated conditioner
> hold/return/tail events, not a universal probe-response failure. The next
> bounded route separates nominal from matched action response, adds only
> causally visible action-edge/dwell/return-age memory, and then tests a
> low-dimensional stability-constrained R_geo/Z_geo/Ip/current innovation
> state. Cell, unique-prefix and worst-event metrics are all retained; no
> post-result deduplication changes ID-2L1. A larger recurrent network, new
> TSC, calibration or controller remains blocked until this discriminator is
> complete.

> **Post-ID-2L1 architecture amendment (2026-08-17):** the structured
> signed/even fixed-pole action memory is retained as the leading development
> backbone, but it is not yet a qualified model. It generalized signed
> response direction and magnitude much better than action-blind, odd-only,
> high-dimensional contextual, or GRU-residual alternatives, while failing
> strict exact-observation short-horizon absolute R gates.
>
> The next architecture decision must separate the explicit time nominal from
> causal issue/return-event and innovation correction. It must not replace the
> useful backbone with a larger monolithic network. A bounded local correction
> or hybrid event/direct-horizon head is only a candidate after zero-fit
> per-issue attribution. Fresh calibration and blind whole-history holdout
> remain AND gates before authority, recovery and control. The final waypoint
> and crossing goal is unchanged.

> **Historical post-ID-2K1 architecture amendment:** the complete fresh
> `history x direction x sign` development matrix passed its execution and
> evidence gates. Its plus/minus responses are strongly non-odd in the finite
> tested domain, while conditioner-history effects must still be evaluated as
> whole-family generalization rather than inferred from labels.
>
> The next model is explicitly layered: exact Card15/queue/current semantics;
> a time-indexed nominal continuation; stable low-order signed/even action
> memory; causal interaction with exact current R_geo/Z_geo/Ip and compressed
> takeover history; and an optional small neural residual retained only after
> held-family gain. One-ms truth recentering is an operating mode, not a
> substitute for credible multi-step prediction. Fresh calibration and blind
> whole-history holdout remain separate AND gates before authority, recovery
> and constrained control. The final waypoint/crossing goal is unchanged.

> **Historical post-ID-2J0 architecture amendment:** the frozen monolithic
> TCN remains wrong-way for three minus histories even when every prediction
> step is recentered on exact current R_geo/Z_geo/Ip truth. Recentring reduces
> nominal/free-recursion drift but cannot substitute for supported signed
> action-memory dynamics. Six of eight tested probe prefixes are outside the
> original development support.
>
> The backbone is therefore restored to the originally intended structured
> form: exact actuator/queue; explicit time-indexed active nominal; stable
> low-order latent action memory; and only then a small context-gated neural
> residual if fresh whole-family evidence warrants it. ID-2K1 factors eight
> complete histories against p04/p07 and both signs with matched baselines;
> its three extra replays are integrity checks rather than added fit weight.
> It does not
> open controller work. Fresh calibration, new blind history holdout,
> authority and recourse remain independent AND gates before constrained
> control. The final two-axis waypoint/repeated-crossing goal is unchanged.
>
> **Historical ID-2J0 architecture amendment:** a monolithic causal TCN is
> no longer the presumed plant backbone. ID-2J0 first measures whether exact
> 1 ms truth recentering repairs local response while free recursion fails,
> and whether blind histories lie outside development causal-prefix support.
> The post-holdout re-observation is diagnostic only because original raw was
> removed during server cleanup; it cannot be used to retrain or recalibrate.
>
> Unless the attribution contradicts it, the next model family is
> `exact actuator/queue + time-indexed nominal continuation + stable low-order
> latent action memory + small context-gated residual`. Current R_geo/Z_geo/Ip
> remain exact observed inputs, not latent estimates. Conditional uncertainty
> and OOD are whole-history/family quantities. Authority and controller-grade
> recourse remain independent AND gates after a fresh model holdout. The final
> fixed-1100-ms two-axis path/waypoint and repeated R_mid-crossing goal is not
> reduced to source holding.
>
> **Historical post-ID-2I1 architecture note:** the small causal TCN passed
> development and fresh calibration but failed the untouched whole-history
> holdout. Absolute prediction remained inside wider caps, yet calibrated
> joint coverage was `0/8`, response NRMSE exceeded action-blind normalization,
> and three groups predicted the peak R/Z response in the wrong half-plane.
> The current TCN/width pair is therefore not eligible for controller use.
>
> The architecture remains exact actuator/queue plus history-conditioned
> dynamics and uncertainty, but the next decision must separate nominal drift,
> action-memory support and uncertainty detection before selecting new data or
> a structured nominal-plus-stable-memory residual model. Exact/noiseless
> current R_geo/Z_geo/Ip and the final two-axis path/waypoint/R_mid-crossing
> goal are unchanged. Controller-grade tubes and recourse remain blocked.
>
> **Historical ID-2G1 architecture note (2026-08-17):** ID-2F1R1 passed its complete
> fresh repeated-context data gates and now permits a finite development
> model comparison. The architecture remains exact actuator/queue plus a
> history-conditioned dynamics model and uncertainty; current R_geo/Z_geo/Ip
> are exact observations rather than latent noisy states. Mechanism
> attribution is diagnostic, not a universal prerequisite for ML.
>
> ID-2G1 compares stable low-order/LPV, small GRU, causal TCN and a
> probabilistic ensemble under the same three whole-context LOCO folds. It
> evaluates rolling one-step, free recursive and evaluator-only paired
> response prediction without future-baseline leakage. Even a PASS is only
> a development-model result; fresh calibration, whole-context/history
> holdout, authority and recourse remain separate AND gates before rolling
> control. The final fixed-1100-ms, one-ms, safe two-axis path/waypoint and
> repeated R_mid-crossing goal is unchanged.
>
> **Historical ID-2F1R1 implementation note (2026-08-17):** the repeated-context
> development campaign uses a 34-issue horizon because the original 32-issue
> schedule supported only rank 28 of the declared 32-column lag-16 input
> block. This is a prospective data-geometry correction under a new identity,
> not a weakened post-result gate. It changes neither the exact/noiseless
> current R_geo/Z_geo/Ip contract nor the separation between TSC-only
> identification and controller-grade safety qualification.

> **Historical post-ID-2E1 learning amendment (2026-08-17):** the architecture no
> longer treats a complete mechanistic explanation of each valid boundary
> excursion as a prerequisite for machine learning. The hard requirement
> is causal availability: current exact R_geo/Z_geo/Ip and takeover-to-now
> observation/current/action history are available, while the next state and
> future actual current are not. A predictive model may learn a conditional
> distribution over continuous and jump responses without first naming the
> underlying TSC mechanism.
>
> The immediate route is fit-eligible repeated-context data, followed by a
> whole-history comparison of stable structured, GRU, TCN and probabilistic
> mixture/ensemble candidates. Raw full-boundary analysis is a bounded
> integrity diagnostic, not a universal gate. Fresh calibration, blind
> holdout, authority, tube, recourse and controller qualification remain
> distinct later stages. The final two-axis path/waypoint/crossing goal is
> unchanged.
>
> **Post-ID-2E1 architecture amendment (2026-08-17):** the source-local
> p04/p07 fixed-pole/FIR family failed grouped duration/time development
> before evaluator open. P09's separate event channel fit well, while
> p04/p07 minus cells showed isolated state19/state27 excursions. This
> supports retaining the nominal/residual decomposition but rejects treating
> all p04/p07 response as one smooth linear convolution. Before neural
> escalation, the route must distinguish a causally separable hybrid event
> from an unqualified/repeatability-unknown boundary or numerical branch.
> Controller-grade stages remain blocked and the final goal is unchanged.
>
> **ID-2E1 structured-model amendment (2026-08-17):** ID-2D1R1 is now a
> complete source-local fit-eligible development PASS. The immediate
> architecture discriminator is zero-new-TSC and decomposes a time-indexed
> active nominal from action-conditioned response. P04/p07 first compare
> stable fixed-pole odd, signed/even, time-scheduled and finite-FIR candidates
> under whole-schedule folds; p09 remains a separate stable event channel.
> The first development-eligible candidate is frozen before ID-2C2 is opened
> once as evaluator. A failure pauses for route review before any larger
> recurrent model. Calibration, context/history holdout, uncertainty tube,
> recourse and constrained control remain downstream and the final two-axis
> path/waypoint/crossing objective is unchanged.
>
> **ID-2D1R1 model-aligned support amendment (2026-08-17):** a smooth
> fixed-pole/low-order residual and a separately labelled event residual must
> not be given the same artificial memory-order gate. The unchanged campaign
> supports p04/p07 through 16 lags and the issue22 p09 event through its ten
> observed ages. R1 freezes those as separate full-rank blocks. This does not
> shorten physical memory by assumption: the later ID-2C2 evaluator retains
> the longer issue16 p09 tail, and failure there must reject or extend the
> event representation rather than leak evaluator data into fitting.

> **Post-ID-2C2 duration/time amendment (2026-08-17):** exact fresh replay
> validates the finite active-nominal/vector cells but cannot distinguish a
> causal dynamics model from a trajectory lookup. ID-2D1 therefore withholds
> the existing issue-16/one-issue cells as immutable evaluator evidence and
> varies p04/p07 duration and issue time around the same active nominal; p09
> remains a separate hybrid/event coordinate. Only after execution/raw,
> baseline repeatability, lag-support and signal/Ip gates pass may a later
> model compare an action-blind nominal with exact-actuator, stable low-order
> residual memory. Neural residuals, calibration, whole-context holdout,
> tube, recourse and control remain later gates. This source-local step does
> not replace the final multi-position/history/HFS-LFS goal.

> **ID-2C2 fresh-validation amendment (2026-08-17):** ID-2C1 supplied the
> first finite active-nominal plus signed residual evidence, not a model or
> safety proof. The selected p03-minus staircase reduced terminal source R/Z
> norm by about 34%, while p04/p07/p09 one-issue-return primitives produced
> measurable two-axis residuals. The architecture now requires a fixed-action
> fresh replay stage before fitting: exact whole-trajectory repeatability,
> nominal effect, two-sided signal, tail, Ip, rank/condition and positive
> spanning must all survive. A PASS opens only exact-actuator + time-indexed
> active nominal + stable low-order history/action model design, with the
> fresh ID-2C2 records kept evaluator-only. It does not skip later context/
> position factorization, calibration, blind holdout, tube, recourse or
> controller qualification.
>
> **ID-2C1 active-nominal amendment (2026-08-16):** ID-2C0 passed and
> localized the immediate architecture gap to active nominal authority plus
> residual vector evidence. The first TSC stage is therefore a bounded
> low-dimensional Card15 staircase search, followed conditionally by a
> matched local signed-vector family. It is not a world-model bakeoff and it
> cannot qualify safety. A successful candidate still needs fresh replay,
> then nominal-plus-stable-latent-plus-action-residual model development.
> Recovery-backed constrained control remains downstream of fresh grouped
> calibration and blind context/history holdout.
>
> **Post-ID-2C0 route amendment (2026-08-16):** control relevance now precedes
> a generic context bridge. ID-2B1's frozen FAIL is valid, but the signed and
> signed/even paired-response models structurally cancel their causal-history
> base and therefore cannot schedule response by context. The sole contextual
> candidate is too narrowly parameterized and undersupported to isolate model
> class from data coverage. The factor-of-eight p09 contrast also changes
> current R/Z/Ip with arrival history, so it is context evidence rather than a
> pure hidden-history theorem.
>
> The next dependency is a zero-TSC audit followed, only if prospectively
> authorized, by a bounded canonical-source time-varying sequence search for
> an active nominal corridor. A useful nominal must materially suppress the
> full R/Z drift and preserve Ip/current headroom; later fresh evidence must
> show two-sided, non-collinear residual action around it. P09 is an event or
> hybrid candidate until recurrence is measured, not a preselected smooth
> control basis. Only after this control-relevance gate should matched
> position/history development data and a nominal-plus-residual model be
> collected. Fresh calibration, blind holdout, tube and recourse still
> precede any controller TSC.
>
> **Post-ID-2B1 support amendment (2026-08-15):** a stable signed lifted
> model produced real development gain between two related histories but did
> not generalize to the unseen p03-arrival history; richer fixed interactions
> overfit. The architecture remains exact actuator + explicit stable memory +
> later residual, but the next dependency is context coverage, not model
> capacity. History interpolation must be established in a source-local HFS
> bridge before multi-anchor position scheduling. No calibration, tube,
> planner, controller or neural residual is authorized by ID-2B1.
>
> **Post-ID-2B0 model amendment (2026-08-15):** the first operational model
> candidate is a direct rolling finite-horizon lifted model with exact current
> observation, fixed stable memory poles and future issued Card15 actions.
> It is re-centred every 1 ms and has no unconstrained predicted-state
> feedback. This is a deliberately narrower precursor to the eventual
> stable latent/state-space backbone. Three whole causal contexts form atomic
> LOCO folds. Matched baselines are evaluator-only and action-conditioned
> response must improve over an action-blind history model in every fold.
> A structured PASS still requires fresh grouped calibration before any tube
> or planner; a FAIL routes to targeted context/history data rather than a
> larger network. The final two-axis/path/crossing goal is unchanged.
>
> **Post-ID-2A readiness amendment (2026-08-15):** ID-2A is the first
> development-fit-eligible dataset, and its deterministic factor-of-8.09
> p09-minus context difference confirms that causal history cannot be reduced
> to current R_geo/Z_geo/Ip and one instantaneous action. It still covers only
> three small-HFS contexts and two future primitive coordinates. Therefore an
> input-rank PASS is not a model-order, uncertainty, authority or controller
> qualification. The unexecuted ID-2B v1 config is superseded before fit.
> ID-2B0 first audits true state-10 history, matched-baseline response,
> descriptive low-order temporal structure, context support and future-current
> leakage with zero TSC and zero fit. The subsequent structured backbone must
> contain an explicitly stable low-order innovation/state-space model; ARX is
> only a baseline, and a small GRU/TCN may learn only a prospectively frozen
> residual. Exact current R_geo/Z_geo/Ip are re-centred every real cycle, but
> future actual current inside a planning rollout is propagated rather than
> read from future truth. Fresh grouped calibration, blind whole-prefix
> holdout and independent authority/recourse remain mandatory before control.
>
> **ID-2A duration/history architecture gate (2026-08-15):** model fitting no
> longer starts from a static response vector. The prospective development
> dataset retains exact actuator/readback history and every state for signed
> p01/p09 primitives held one, two or four issues in three whole causal
> contexts. Context families, not time steps, are the model-selection unit. A
> PASS first compares exact actuator/queue plus time-indexed nominal
> continuation and stable low-order latent/state-space response; a small
> GRU/TCN may learn only a residual and must improve every held-out context.
> Fresh grouped calibration and unopened whole-prefix holdout remain required
> before any uncertainty tube or controller use. The data identity, storage
> cap and claim boundary are frozen in
> `RGEO_ZGEO_1MS_ID2A_DURATION_HISTORY_DEVELOPMENT_DESIGN.md`.
>

> **Post-ID-1C duration/history amendment (2026-08-14):** a signed Card15
> direction is no longer represented by one four-effect mean vector. ID-1C
> found a deterministic, fully repeatable p09-minus state-12 boundary
> excursion between otherwise ordinary states 11, 13 and 14. The fixed odd
> persistent p01+p09 basis therefore failed, but the evidence positively
> supports explicit effect-age/history state. The next identification data
> design must retain the complete action-duration response and tail for each
> signed primitive, use matched baselines and whole-prefix grouping, and only
> then compare stable low-order latent/state-space dynamics with an optional
> small recurrent residual. Exact current R_geo/Z_geo/Ip, actuator/queue,
> uncertainty, Ip and later recourse requirements are unchanged. Static
> persistent-basis screening will not continue as an automatic direction
> ladder.
>
> **ID-1C exact-centred basis amendment (2026-08-14):** the next finite
> discriminator uses p01 plus a newly reconstructed p09 pair, both exactly
> centred on q0 in actual Card15 current coordinates and limited to 0.15 A
> designed components. It measures four persistent effects and gates the even
> pair midpoint as well as full-ray positive span. This tests whether the
> useful first-effect differential geometry survives persistence without the
> 0.05 A midpoint bias of the old full-amplitude p09 pair. A PASS still does
> not authorize model fitting; it only selects the basis for a fresh
> context/history/anchor campaign.

> **Post-ID-1B action-centre amendment (2026-08-14):** a numerically rank-two
> response set is not a usable two-axis basis when its positive cone omits a
> half-plane. ID-1B found that all six persistent q0-centred signed rays had
> positive R components and failed the frozen positive-span/support gates.
> The p03/p04/p07 q0-centred ladder therefore stops. This finite result does
> not prove absence of negative-R authority: q0 is not a hold command, and a
> future controller is expected to operate around an active time-varying
> nominal continuation. Before fitting dynamics, the next design audit must
> decide whether to add genuinely new action directions or identify
> two-sided residual authority around a prospectively frozen nominal centre.
> Controller-grade tubes and recourse still require separate fresh evidence;
> natural drift and rank may not substitute for them.

> **Post-ID-1A temporal-primitive amendment (2026-08-14):** a local action
> column may not average across a later issued action edge. With `issue+1`
> effect timing, an issue-10 pulse followed by issue-11 q0 return has only one
> pure probe-effect state. ID-1B holds the target unchanged through the full
> measurement window, keeps later return/tail states separate, and requires a
> positively spanning R/Z response cone plus minimum directional support.
> Numerical rank two is necessary but not sufficient. ID-1A remains a frozen
> clean design FAIL and is forbidden for fitting.

> **ID-1A prospective factorization amendment (2026-08-14):** before model
> selection, identical q0-centered p03/p07 signed probes are repeated across
> issue time, near-matched visible state/different history, and displaced
> cumulative-prefix contexts. This is a finite empirical factorization pilot,
> not a claim of perfect orthogonality or controller safety. Whole causal
> prefix families stay grouped. Only a PASS can open structured development
> fitting; calibration, holdout and control qualification remain fresh stages.

> **Post-ID-0R1 architecture amendment (2026-08-14):** current and past
> R_geo/Z_geo/Ip remain exact observations. Finite-memory truncation is no
> longer inferred from one terminal response ratio. The prospective backbone
> carries a stable low-order persistent/damped-oscillatory latent and validates
> full-horizon recursive prediction with a nonzero uncertainty floor. ID-0 and
> ID-0T1 stay design-only; their one source anchor cannot support LPV/local or
> recurrent model selection. A fresh ID-1A small-HFS context/anchor pilot must
> first separate issue time, controlled position and arrival history as far as
> the finite simulator envelope permits. This is identification, not
> controller-grade safety or recovery.

> **ID-0T1 architecture amendment (2026-08-14):** state32 does not certify
> literal finite-memory tail closure: p03-plus remains above the frozen ratio,
> and other arms show small delayed rebounds before their terminal PASS. The
> preferred architecture should therefore represent persistent/oscillatory
> low-order memory explicitly and judge adequacy over a whole terminal window,
> rather than assume an endpoint or a larger GRU erases history. This is a
> route recommendation, not authorization to fit a model. State40 and ID-1 are
> blocked pending review; exact actuator/queue, exact current R_geo/Z_geo/Ip,
> uncertainty and recovery requirements remain unchanged.
>
> **ID-0 evidence amendment / ID-0T1 gate (2026-08-14):** ID-0 established a
> repeatable source-local signed R/Z response set with rank 2, best two-ray
> condition `2.0870211406380474` and maximum angular gap
> `132.32694820821953 deg`, while respecting the exact actuator, boundary and
> Ip interfaces. It did not close the frozen state20 tail-ratio gate, so the
> data remain design evidence and the architecture may not select or train a
> dynamics model yet. The next finite discriminator repeats only the same
> early pulse-return histories through state32 and applies the unchanged tail
> criteria. PASS may lead only to small-HFS position/time/history
> factorization; FAIL triggers route review rather than a longer automatic
> ladder. The eventual model/controller architecture and final two-axis path
> goal are unchanged. The ID-0T1 config SHA-256 is
> `2b5137284435845587e6d93ed9f1cc9736e4bef43ded17da26c6e02cf5356df3`.
>
> **ID-0 prospective architecture gate (2026-08-14):** the first campaign
> under the TSC-only identification contract is frozen to two q0 baselines and
> actual plus/minus p03/p04/p07 pulse-return families at early and late q0
> contexts, with 20 resets and 400 maximum attempts. Its gates measure exact
> execution/raw identity, finite repeatability, full-vector signed signal,
> R/Z response-cone geometry, Ip cost and early tail closure. A PASS is only
> source-local development evidence and cannot skip position/history
> factorization, fresh calibration, controller-grade tubes or recourse. See
> `docs/codex/reports/RGEO_ZGEO_1MS_ID0_VECTOR_TAIL_DESIGN.md`.
>
> **Post-E1 architecture reset (2026-08-14):** the high-level exact-actuator,
> exact-current-observation, latent-history, uncertainty-aware rolling-control
> architecture remains. E1 and the single-p03 action-age ladder are parked.
> They are replaced by two explicitly different evidence contracts: finite
> TSC-only empirical identification may expose preregistered unknown simulator
> transitions, while every controller-grade action still requires a calibrated
> pre-action tube and qualified recourse. The next stage is a source-local
> matched-prefix signed vector/tail design, followed only after its gates by
> small-HFS position/time/history factorization and grouped model comparison.
> Exact current R/Z/Ip are recentered at every decision prefix; latent belief
> covers dynamics and future response, not measurement error. The preferred
> model order remains stable low-order/state-space plus contextual LPV/local
> scheduling, with a small recurrent residual only after fresh whole-family
> benefit. See `docs/codex/reports/RGEO_ZGEO_1MS_POST_E1_ROUTE_RESET.md`.
>
> **Simulator-exploration separation amendment (2026-08-14):** the strict
> pre-action transition-support rule remains mandatory for qualification and
> control claims, but no longer makes first digital-twin observation logically
> impossible. A separately frozen E1 identity exposes exactly one unknown
> issue16 -> state17 successor after exact replay to state16, then stops
> unconditionally. The realized transition is development-only, cannot
> self-qualify, and cannot enter model/expert/fixture/hold/controller evidence.
> Even an accepted result only triggers route review; it does not create an
> automatic p03 ladder. This preserves the final two-axis goal while separating
> exploration risk from controller safety qualification.

> **Exact observation and A4 support amendment (2026-08-14):** from the fixed
> 1100 ms takeover onward, the controller observes the current true, noiseless
> same-step paired-boundary `R_geo/Z_geo` and same-step `Ip` before every 1 ms
> action issue. Missing/invalid boundary data fails closed. All causal
> observations and controller-owned issued/quantized/applied/readback/queue
> history accumulated since takeover are available, although the model may
> compress them. This does not assert pre-1100 ms history, and the next/future
> state remains unknown before issue. The observer/belief is therefore for
> latent memory and future-response/model uncertainty, not current or past RZI
> measurement.
>
> The separate zero-TSC A4 support audit returned
> `ONE_MS_NR2R2C2AA4_LATE_STATE_CAUSAL_SUPPORT_FAIL_NO_TSC`: 16/32 transitions
> have direct support and the first gap is issue16 -> effect17, level2
> effect-age 15. A4 remains unimplemented/unrun. Exact state16 knowledge,
> margins and empirical stop thresholds are not a pre-action bound on state17.
> The subsequent E1 design above selected and froze the simulator-only
> empirical exploration branch. The A4 result itself still authorizes neither
> TSC nor controller/model work.

> **Post-C2aA3 route amendment (2026-08-14):** the final objective remains
> finite-domain two-axis relative/path/waypoint tracking; source hold is only
> a bootstrap step toward a qualified terminal/recoverable set. A2/A3 show
> that p03 is aligned with the
> source-drift correction and that cumulative `0.3 A/step` authority matters,
> but the qualified level2 R/Z response norm is only `5.07%` of q0's source-
> drift norm at state16.
> Scalar `delta R-delta Z` is henceforth only a source-drift diagnostic, not a
> two-axis authority claim. The already frozen A4 campaign is retained once,
> unchanged, as a late-tail plus hold discriminator, conditional on a separate
> zero-plant late-state support/margin gate. A safe scientific FAIL ends the
> single-p03 static dwell/level ladder; PASS still requires fresh Nominal-H1. In
> parallel, matched-prefix signed/cumulative vector authority and local
> recourse must qualify before transport, atlas or controller work. The
> structured causal-model, recovery-backed constrained-MPC and later shadow-
> adaptation architecture is unchanged. See
> `docs/codex/reports/RGEO_ZGEO_1MS_POST_C2AA3_DEEP_ROUTE_REVIEW.md`.

> **NR2R2C2aA4 prospective amendment (2026-08-14):** inside the finite
> q0/level1/level2 domain qualified by A3, the next discriminator holds the
> maximum p03 level continuously through 32 ms and applies the unchanged
> source short-hold gates. This is a direct authority bound for one persistent
> schedule, not a general proof over switching laws and not a controller.

> **NR2R2C2aA3 evidence amendment (2026-08-14):** two exact p03 level2
> replays passed the adjacent cumulative-domain gates. Total opposition
> averaged `0.74192 mm`; incremental level2-over-level1 opposition averaged
> `0.38599 mm`, with both signs positive at all 14 states. This supports one
> finite time-varying q0/level1/level2 C2a design. It does not establish hold,
> linear scaling, arbitrary cumulative range, recovery or a model/controller.

> **NR2R2C2aA3 prospective amendment (2026-08-14):** the user's cumulative
> `0.3 A/step` authority is now tested explicitly rather than keeping every
> target within q0+/-0.3 A. The first expansion is only one additional exact
> p03-minus level, repeated twice with a pre-result successor bound and
> incremental comparison against the frozen level1 path. This adjacent-level
> sentinel does not assume linear scaling or authorize a general cumulative
> action domain.

> **NR2R2C2aA2 evidence amendment (2026-08-14):** all three minus-sign
> directions completed safely and were positive at all 14 authority states,
> but none passed every frozen gate. P03-minus had the strongest persistent
> response (`0.35593 mm` mean, `0.52328 mm` maximum) and failed only the
> unchanged maximum gate. C2aA2 remains FAIL. The architecture therefore
> advances only to a separately frozen repeated cumulative-level safety and
> incremental-gain discriminator along p03-minus; this is not permission to
> lower C2aA2 gates or begin model/MPC work.

> **NR2R2C2aA2 prospective amendment (2026-08-14):** after p07-plus level2
> failed persistent authority, the next finite discriminator is frozen to
> three development-selected minus-sign directions inside componentwise
> `q0+/-0.3 A`. It retains the same persistent opposition and hard interface
> gates; it does not lower thresholds, fit a response model, move the command
> center beyond the independently supported cube, or authorize Nominal-H1.
> Any passing candidate still requires a separate fresh repeated validation.

> **NR2R2C2aA1 evidence amendment (2026-08-14):** a componentwise q0+/-0.3 A
> p07-plus level safely completed 64/64 authentic 1 ms advances and exact
> paired replay, but failed persistent authority. Mean q0-drift opposition was
> `0.00708 mm`, only 2/14 states were positive, and level2 was worse than
> level1 at all 14 measured states. This rejects that static direction, not
> cumulative-slew control or global reachability. The next discriminator must
> first compare a small prospectively frozen sign/direction family inside the
> already supported cube; it may not unlock hold/recovery/model/MPC stages.

> **NR2R2C1a evidence amendment (2026-08-14):** canonical-source full-prefix
> replay mechanics passed its finite 12-reset/136-advance envelope, while the
> 56.54 s worst complete branch rejects 1 ms online-Oracle use. Generated
> `sprsina` remained non-hash-identical, so snapshot restart is still a
> separate claim. C1a permits prospective C2a nominal active-hold design only;
> it supplies neither novel-action successor safety nor hold/recourse/model/
> controller evidence. See the tracked C1a result report.
>
> **Post-NR2R2B0 route amendment (2026-08-13):** the architecture below is
> retained. The immediate dependency chain is canonical-source full-prefix
> replay -> finite nominal active hold -> bounded-tube contingency -> minimal
> tail/response evidence -> recovery-backed context atlas. In parallel,
> independent `sprsina` semantics and finite snapshot/common-suffix behavior
> claims jointly bound only the faster snapshot-based moving-prefix route. B0's
> frozen `sprsina` byte-hash FAIL and q0 short-hold FAIL both remain; neither
> is a hidden-state theorem or proof that active hold is impossible. A tiny
> TSC-only discriminator may bootstrap only when each issued primitive has an
> independent one-step worst-case successor bound inside the frozen outer
> envelope; an outer envelope and immediate stop alone are insufficient.
> Transport/atlas/controller execution still requires bounded-tube active
> recourse. Before any controller, the legacy runner's generic
> `magaxis/rc/zc` R/Z path must be excluded; the control path must also refuse
> excess current/delta requests before the runner without relying on or
> triggering its silent clipping. Exact reasoning and authorization boundaries
> are recorded in
> `docs/codex/reports/RGEO_ZGEO_1MS_POST_NR2R2B0_DEEP_ROUTE_REVIEW.md`.

> **Post-NR2R1 implementation-order amendment (2026-08-13):** the main
> architecture below is retained, but NR2R1 showed that its execution order
> was too aggressive.  A single-start, 16 ms model bake-off did not implement
> the required operating-point/history coverage or explicit low-order memory.
> Before another model comparison, the route now requires contextual
> identifiability, independent drift/recovery baselines, repeated actions over
> position and arrival-history anchors, and a separate growing-prefix branch-
> replay qualification.  Within-run adaptation begins only in shadow mode and
> may update bounded low-dimensional belief/context/gain parameters, not deep
> weights.  The evidence and revised order are recorded in
> `docs/codex/reports/RGEO_ZGEO_1MS_POST_NR2R1_ARCHITECTURE_REASSESSMENT.md`.
> NR3 remains blocked.

> **Confirmed timing/action amendment (2026-08-13):** development restarts
> from NR0 with a 1 ms control period. For each of the 14 coils in TSC order,
> the hard per-step limit is the single-turn-current condition
> `|I_i[k+1] - I_i[k]| <= 0.3 A`. Equality is allowed; the architecture must
> not invent an undisclosed headroom reservation. TSC Card15 remains in
> kA-turn and must be converted using the explicit per-coil turn count. The
> old 10 ms / 3 A NR0--NR2 route remains historical and cannot qualify the
> new identity. No coordinate, Ip, queue/effect, Card15, safety, or evidence
> rule below is weakened by this amendment.

状态：**v1 已获用户确认；1 ms NR0 已通过，1 ms NR1 已前瞻冻结并获授权**

日期：2026-08-12

本轮权限：NR0 仓库接口与 synthetic 测试；没有改现有控制语义、部署、运行新
TSC、训练模型、测试 Oracle 或实现 MPC/RL。

2026-08-13 的 NR0 实现把本文件第 3/6/9 节落实为独立纯合同模块：显式成对
边界、限制器中面、Ip、命令、动作各阶段、queue、实际电流、缺测标记和证据
用途均 fail closed。该模块尚未接入环境或控制器；它不是 NR1 或真实闭环资格。

## 1. 路线切换的含义

用户已决定不再把旧 Stage4.2/R8 系列的“固定局部响应模型逐级修补直至
MPC 专家”作为当前主路线。旧路线在切换前的本地保存检查点是
`cbdf874`。这是一项**前瞻性的路线作废决定**，并不改写任何既有原始
结果：过去的 PASS/FAIL 仍只在各自冻结的有限合同内有效。

新路线允许从模型和控制架构层面重新开始，但应复用已经证明有价值的
基础设施：真实 TSC 执行、1100 ms restart、因果前缀审计、Card15 实际
动作边界、逐步 raw/snapshot/hash 证据和 Windows/server 验证流程。

旧 probe、sentinel 和审计轨迹不得因路线切换而追溯改名为专家数据或
学习数据。若以后训练，新数据必须在生成前获得独立的 learning/ID 身份。

## 2. 唯一最终目标

从固定 `1100 ms` 接管，在合理、有限的工作域内，使限制器位形等离子体的
几何中心安全、因果地大体跟随用户给出的 `R_geo/Z_geo` 指令。指令可为：

1. 相对当前位置的 `ΔR/ΔZ`；或
2. 分段光滑的 `R_geo_ref(t), Z_geo_ref(t)` 路径/waypoint 序列。

不要求零误差、全局最优、最快移动或无限工况下完美控制。移动时间可以
协商；旧路线的 250/270 ms 到达门不再约束新路线。未来一次命令若被接受，
应在执行前冻结可接受的时标，不能看结果后无限延长。

若用户只给终点，规划器可以选择安全几何路径和时间；若用户给了完整路径，
规划器只能按事先约定重定时，不能擅自改几何路径或 waypoint 顺序。

## 3. 输出量与 LFS/HFS 的确定定义

### 3.1 R_geo/Z_geo

我建议本项目把 `R_geo/Z_geo` 明确定义为同一条、同一时间步有效等离子体
边界的包围盒几何中心：

```text
R_geo = (min(R_boundary) + max(R_boundary)) / 2
Z_geo = (min(Z_boundary) + max(Z_boundary)) / 2
```

这是对用户所说“简单直接的几何中心”的独立工程建议，并非当前 TSC 已有的
一对唯一原生字段。用户发送配套的新对话开场词即表示接受这一定义；若用户
想要另一种几何中心公式，应在 NR0 开始前明确替换，而不能边实现边改变。

它不是磁轴 `xmag/zmag`，不是电流质心，也不是现有 `gfile.py` 中可回退到
磁轴的 pressure-weighted `rc/zc`。R、Z 必须来自同一边界和同一时间步；
边界缺失、非有限或无效时应 fail closed，不得分别拼接或静默回退。径向
原生 `RGEO` 可作为诊断量，但不得与另一种定义的 Z 混成受控坐标。

### 3.2 LFS/HFS

LFS/HFS 不是用户输入，不是要由 LSTM 推断的隐藏模式，也不是两个互不连通
的控制任务。按用户给定的确定几何规则：

```text
R_mid = (R_inner_limiter_midplane + R_outer_limiter_midplane) / 2
R_geo <  R_mid  -> HFS / 内侧区域
R_geo >= R_mid  -> LFS / 外侧区域
```

这是用户给定的几何标签规则，不另行推断接触状态。允许一条轨迹多次发生
LFS→HFS、HFS→LFS 和往返。控制模型可将
`R_geo - R_mid` 作为连续调度特征，并在中点附近使用预先冻结的平滑混合，
但这不创造第三种物理位形，历史状态也不能在跨越时重置。

### 3.3 Ip

`Ip` 不是用户命令维度，但也不能假定“加热会自动精确保持”而从模型中删除。
它应作为耦合观测/预测状态：跟随既有场景参考或允许带是软目标，独立硬安全
带不可交易。只有以后从真实 TSC 接口证明存在并足以解耦的独立 Ip 环，才可
进一步简化控制分配。

## 4. 对“每一步尝试后再决定”的专业定性

`t0` 执行一步、`t1` 读取新状态、再决定下一步，本身是闭环反馈或滚动时域
控制，并不自动等于 RL：

- 只重新计算动作而不更新模型/策略：反馈控制或 receding-horizon MPC；
- 用新转移更新局部动力学再规划：在线系统辨识 + adaptive MPC；
- 动作还显式权衡信息增益与跟踪收益：dual control/dual MPC；
- 从转移更新 policy/value 并优化多步累计奖励：online/model-based RL。

因此“当场训练一个局部专家”不是合适的工程名称。更准确的表述是：
**历史条件化的局部状态估计与在线系统辨识，再由约束规划器逐步决策**。

## 5. 推荐的总体架构

推荐的主干名称：

> **历史条件化、带不确定度的约束滚动控制**
>
> History-Conditioned Uncertainty-Aware Constrained Receding-Horizon Control

```text
用户终点/路径
      |
轨迹合同与 reference governor（路径保持、可行时标）
      |
因果 history observer / belief state
      |
+--------------------------------------+
| 主干：结构化概率模型 ensemble       |
| 可选：TSC 分支 Oracle/教师候选       |
+--------------------------------------+
      |
约束滚动规划：只选下一步实际可表示动作
      |
独立硬接口：Card15/电流/slew/queue/Ip/hold-abort
      |
TSC 执行一步 -> 新观测 -> 更新 belief -> 重复
```

主干是结构化历史模型和约束滚动控制。TSC Oracle 是很有价值、但必须先
资格化的可选工具：若成立，它可减少模型臆测并产生高质量教师决策；若不
成立，主干仍可独立发展。当前仓库没有 head-to-head 证据证明该主干必然
优于 outer RL；优先顺序来自本任务“参考已知、时间宽松、约束强、要求可
审计”的工程判断，不是文献已经给出的本项目结论。

### 5.1 可选工具：TSC 分支 Oracle / rolling shooting

本项目的目标 plant 当前就是 TSC，用户也不要求很短的壁钟时间。因此第一
候选不是让主轨迹承担随机探索，而是在同一因果前缀的克隆分支中评估多条
有限候选动作序列，再只在主干执行最佳序列的第一步。

如果将来不能直接保存任意时刻的完整 moving-state snapshot，可从认证的
1100 ms snapshot 重启，精确重放截至当前的 issued/quantized/applied 动作
前缀；只有重放前缀与主干一致的分支才可作为未来预测。这是未来资格条件，
不是本文件声称已经具备的能力。

Oracle 搜索应作用在**实际 Card15 后动作**或重新辨识的有限安全 primitive
上，而不是默认继承旧 3-SVD、4D basis 或连续 14 维高斯动作。候选算法可
比较 beam search、CEM、MPPI 或短时域直接 shooting；算法名称不是先验结论。

Oracle 的优势只属于同一 TSC 数字孪生。它不能被表述为真实装置的可部署性
或 sim-to-real 安全证明。

### 5.2 主干：历史条件化的结构化概率模型 + 约束 NMPC 候选

可扩展主控制器不再采用“当前 R/Z 对应一个固定局部 Jacobian”的假设，而是
维护一个由完整因果历史更新的 belief state，并输出多步预测分布。推荐起点：

1. 显式保留可知状态和执行器语义；
2. 用稳定的低阶状态空间记忆表示被动导体/涡流等慢动态；
3. 用小型 GRU 只学习剩余的非线性 observer/dynamics residual；
4. 用 bootstrap/probabilistic ensemble 表示模型分歧；
5. 由带不确定度的约束 NMPC 在模型分布上滚动规划，而不是让 RNN 直接发
   14 路线圈动作。

只有将来取得校准的多步误差边界、合适的约束收紧、terminal/recovery set
和递归可行性证据后，才可把它称为 robust/adaptive NMPC；ensemble 分歧
本身不构成鲁棒性或安全保证。

推荐的模型骨架是“精确 queue + 受稳定性约束的低阶显式记忆 + neural
residual”。一个 shared belief 贯穿整条轨迹；已知的 `R_geo-R_mid` gate 可
调度 H/L 局部 dynamics head，在窄过渡带连续混合并允许一个 interaction
residual。未来多步预测应按预测出的 `R_geo` 递推 gate，而非锁死当前标签。
该平滑只服务数值建模，不产生第三种位形。

推荐 GRU 只是合理首选，不是冻结答案。必须在相同的 whole-trajectory、
whole-history 隔离数据上，与显式有限窗/ARX/LPV/classical state-space、
causal TCN、LSTM 或小型 RSSM 公平比较，选择达到门槛的最简单模型。LSTM
的“记住历史”直觉是正确方向，但更多参数和 gate 并不自动得到正确物理
记忆。IMM 不作为核心，因为位形标签已知；S4/Mamba 等长序列模型也不作为
第一版，除非消融证明确有超长记忆且简单候选不能满足。

## 6. 历史如何进入模型

历史不是仅把若干帧 `R/Z` 塞入网络。自 1100 ms 接管后，完整因果历史由接口
保留；模型选择有限窗或压缩 belief 是表示选择，不表示其余历史不可见。每个
动作签发前，当前 `R_geo/Z_geo/Ip` 是无噪声真值输入，其测量协方差为零并保留
直接通路，不由 observer 重构。observer 只表征未观测慢记忆及未来动力学不确定
度；动作后的下一状态仍须等 TSC advance 后才能观测。每步的因果输入至少包括：

- `R_geo/Z_geo/Ip` 及有效性、时间戳和必要的差分量；
- 14 路实际线圈电流，以及部署时确实可取得的被动/结构电流；
- issued、serialized/量化后、applied/readback 动作，精确 delay FIFO 和
  action age；
- `dt`、自 1100 ms 起的时间、异常/缺测 mask；
- `R_geo-R_mid` 及由它确定的 HFS/LFS 调度特征。

未来参考只进入 planner，不进入 plant dynamics model，避免模型利用目标标签
伪造因果预测。future action/outcome、source/history ID、restart hash 和部署
时不可见的 TSC 隐状态也不得作为模型输入。wire/passive current 只有部署时
真实可得才可输入，否则最多作为离线 auxiliary label。模型的 recurrent
state 在跨越 `R_mid` 时连续保持。

1100 ms 也是记忆初始化问题：若未来接口可提供部署时真实可得的 1100 ms
以前因果窗口，就用它 burn-in；否则使用独立的 1100 ms 状态初始化器/集合
先验并保留较大初始不确定度，不能简单把 hidden state 清零后称作真实历史。

推荐的三种更新时间尺度：

- 每个控制步：更新可观测状态、queue 和 hidden belief；
- 单次运行内：首版只更新 hidden belief、精确 queue 和审计过的 ensemble/
  Bayesian weight，深网权重冻结；以后只有 effect window 已完成、innovation
  仍在校准域且辨识条件合格时，才可能开放投影约束下的低维 context/bias/
  gain；中点过渡带先禁止参数更新，在线 uncertainty floor 不得缩小；
- 运行之间：用合规数据离线重训、校准和版本化完整 world model。

因此新路线会“不断累积经验”，但不会在一条轨迹中从零反向传播出一个未经
验证的深度专家。

未来 world model 的验收不能只看 one-step teacher-forced MAE。输出至少应
包括 belief posterior、多个时域的 `ΔR_geo/ΔZ_geo/ΔIp` 分布、约束相关电流
辅助量和 disagreement/OOD 指标；训练与选择应看 action-conditioned free
rollout 及不确定度校准。数据按完整 1100 ms source/history/snapshot family
分组，所有 sibling branches 必须进入同一个 split，并把训练、校准和一次性
blind holdout 分开，禁止按 step 随机拆分造成历史泄漏。

## 7. RL、ILC 和直接 recurrent policy 的位置

“外层 RL 规划、内层自适应控制”可以借鉴，但不应成为第一版：

- 用户给完整路径时，高层可做的主要是调时标，确定性优化器通常更透明；
- 用户只给终点且路径选择复杂时，outer RL 才可能有额外价值；
- 内层 adaptive controller 和独立安全层仍是必需的，RL 不是安全来源。

未来最合理的 RL 用法，是把已合格 Oracle/MPC 的昂贵搜索摊销成冻结策略，
或只输出 waypoint、pace、有限 primitive/残差。reward-trained policy 本身
不构成安全证明；在本项目中仍须经过同一独立安全层。它必须在相同命令、
TSC 预算和同一安全层下证明可测收益；若 MPC 已能满足粗略跟踪，最终不使用
RL 是完全合格的结果。

鉴于本项目当前证据和审计要求，直接 recurrent policy 更适合作为 Oracle/
MPC 蒸馏后的快速 student，而不作为首个安全基线。经典 ILC 最适合高度重复
的初态和任务；虽有变参考等扩展，但本项目没有证据让它承担任意新轨迹，
因此只把它作为重复命令的 feedforward 增强器。

主动 online model-based RL/dual exploration 放在最后。若 Oracle 分支可以
在不污染主干的克隆中探索，就没有理由让主轨迹承担同样的辨识风险。

## 8. 路线优先级

| 优先级 | 候选 | 推荐角色 | 主要诚实边界 |
|---:|---|---|---|
| 1 | history-conditioned uncertainty-aware constrained NMPC | 可扩展主控制器 | 尚未取得 robust/recursive-feasibility 资格 |
| 2 | TSC branch Oracle + shooting/CEM/MPPI | 待资格化的可达性工具、教师，可能是慢速控制器 | 任意时刻分支、完整前缀和成本尚未资格化 |
| 3 | outer RL + inner adaptive controller | 有明确增益后才加入 | 可能不优于确定性规划，还增加验证负担 |
| 4 | recurrent student / ILC | 蒸馏加速或重复轨迹增强 | 不能独立承担 OOD 和硬安全 |
| 5 | online MBRL / dual control | 后期小幅信息动作 | 延迟、量化、错归因和主轨迹探索风险最高 |

当前最有希望的组合不是押注单个算法，而是：**以结构化历史模型和约束
NMPC 为主干；若 Oracle 资格通过，就用它直接询问 TSC、提供教师与审计；
RL 只竞争剩余的可测收益。**

## 9. 独立安全与成功定义

点动作投影只能限制瞬时动作，不能证明后续状态安全。未来安全层至少要独立
处理实际 Card15 可表示性、线圈绝对电流和 slew、动作 queue、Ip 硬带、有限
R_geo/Z_geo 工作域，以及 hold/减速/abort。接受一个动作还应保留一条已资格
化的 recovery continuation；预测分歧、OOD、无进展或求解超时应触发减速、
hold 或退到安全 waypoint。任何安全 stop 可算安全机制工作，但对应跟踪 case
仍是 FAIL，不能把“一直拒绝”算作成功。中点 corridor 任一侧若没有合格的
hold/recovery，就不得执行 crossing。

新路线成功只在前瞻冻结的有限工作域和轨迹类内声明，至少覆盖水平、垂直、
斜向、弯曲路径、hold、多 waypoint、两个方向跨 `R_mid` 和往返；分阶段从小
域扩展是工程顺序，不得把最终目标偷换成两个单侧控制器。

## 10. 后续阶段（本轮不执行）

下一对话建议一次只授权一个阶段：

1. **NR0 — 接口与实现合同**：把上述坐标、命令、因果历史、动作、Ip 和证据
   身份落实为代码级规格与测试；只做仓库工作，不运行新 TSC。
2. **NR1 — 安全基础与可选 Oracle 资格**：在用户另行授权后，先建立 hold/
   abort/recovery 和合规数据采集边界；再检查分支/前缀重放能否作为因果预测
   工具并测量成本，失败时不强行包装为 Oracle。
3. **NR2 — 有权限的数据与历史模型比较**：生成前冻结用途，按完整 history/
   trajectory 分组；比较简单模型、GRU、LSTM/TCN 等的多步预测和不确定度。
4. **NR3 — 约束滚动控制**：先慢速、小工作域、同侧和二维，再扩大到跨中点。
5. **NR4 — 连通工作域资格**：双向 crossing、往返、多 waypoint、不同历史；
   只声明实际通过的有限域。
6. **NR5 — 可选学习收益门**：比较 outer RL、蒸馏或有界在线适应；无实用
   收益就结束在非 RL 控制器。

任何阶段失败都必须区分接口/部署/数据/模型/规划器/真实闭环结果；不得用
学习算法掩盖不存在的物理 authority，也不得从同一 TSC Oracle 的成功外推
到真实装置。

为避免重新进入无限微阶段修补，出现以下任一情形应停止当前模型路线并重新
判断，而不是只扩大网络或继续加 probe：坐标/实际动作/effect timing 语义不
唯一；同等因果历史与动作仍有不可覆盖的响应冲突；whole-history blind
holdout 的多步区间系统性欠覆盖；安全 hold/recovery 不成立；在宽松时标下
高保真规划仍找不到合理小位移；复杂 recurrent 模型不显著优于简单因果基线。

## 11. 关键文献与独立判断依据

- Degrave et al., TCV 深度 RL 磁控制：训练在模拟器中完成，硬件部署为冻结
  策略，不是实机在线盲试。<https://www.nature.com/articles/s41586-021-04301-9>
- HL-3 先用历史日志离线训练 LSTM 动力学模型，再在该模型内训练 PPO；这
  支持历史建模，但不证明 LSTM 或 online RL 必然最优。
  <https://www.nature.com/articles/s42005-025-02302-y>
- TCV 实验 MPC 使用上层 MPC 优化内层磁控制参考，支持约束层级架构。
  <https://arxiv.org/abs/2506.20096>
- Learning-based MPC 综述。<https://doi.org/10.1146/annurev-control-090419-075625>
- Dual control 与 Bayesian RL 的探索—控制关系。
  <https://www.jmlr.org/papers/v17/15-162.html>
- DIII-D 展示了先从历史日志建模、再训练 model-based RL 的具体实例；这不
  是所有昂贵装置的普遍最优性证明。
  <https://proceedings.mlr.press/v211/char23a.html>
- PETS 在通用 benchmark 上给出 probabilistic ensemble + MPC 的样本效率
  证据，不是 tokamak 安全性证明。
  <https://proceedings.neurips.cc/paper/2018/hash/3de568f8597b94bda53149c7d7f5958c-Abstract.html>
- Predictive safety filter 的保证依赖明确的概率误差、约束与 terminal/
  recovery 假设，不是简单动作裁剪。
  <https://doi.org/10.1016/j.automatica.2021.109597>
- Tokamak 部分可观测性模拟研究显示具有差分/积分归纳偏置的简单历史模型
  可能比通用 recurrent/Transformer 更稳健；这不是本项目实证。
  <https://arxiv.org/abs/2307.05891>
- Robust adaptive MPC 理论可参考 Lu、Cannon 与 Koksal-Rivet；其有界参数
  等假设不能直接搬到 TSC 黑箱。<https://arxiv.org/abs/1911.00865>

## 12. 提案结论

1. 新问题不是“换一个更大的神经网络”，而是重新建立历史条件、实际动作
   语义明确、带不确定度和独立约束的滚动控制系统。
2. 用户关于历史很重要的直觉是正确的；专业实现应是 structured belief
   observer，GRU/LSTM 只是候选组件。
3. TSC 分支 Oracle 是值得尽早问清的可选工具，但本文件不声称它已通过，
   它失败也不阻断结构化历史模型主干。
4. 主控制器优先研究结构化概率模型 + 带不确定度的约束 NMPC；在满足额外
   理论和证据条件前不称其为 robust。
5. 外层 RL 可以借鉴，但必须后置并通过增益门；不做 RL 仍可完成最终任务。
6. 本文件提出方案并等待用户通过发送配套开场词确认；没有开始实现或实验。
