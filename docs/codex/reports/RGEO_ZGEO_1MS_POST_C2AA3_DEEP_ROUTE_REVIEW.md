# R_geo/Z_geo 1 ms post-C2aA3 deep route review

Date: 2026-08-14 Asia/Shanghai

Final documentation route:

```text
POST_C2AA3_DEEP_REVIEW_A4_SINGLE_CAMPAIGN_TAIL_GATE_AND_VECTOR_RECOURSE_REQUIRED
```

## 1. Scope and final goal

This local scientific and architecture review was read-only with respect to
code, compact evidence and the plant; it made documentation-only changes. It
wrote no controller or experiment code, accessed no server or server raw, ran
no TSC, fit or trained no predictive plant/controller model, and generated no
plant data. The least-squares number below is descriptive algebra, not model
fitting. The NR2R1 diagnostic holdout was not read.

The persistent project goal remains:

> Starting from the fixed 1100 ms takeover, under a 1 ms control period and
> the hard per-turn, per-coil limit `|I_i[k+1]-I_i[k]| <= 0.3 A`, qualify a
> causal rolling controller that uses the paired same-step valid-boundary
> bounding-box center `R_geo/Z_geo`, maintains history and uncertainty, and
> approximately follows user relative displacements, paths or waypoints in a
> prospectively declared finite domain. Ip remains a coupled observation plus
> soft-hold/hard-safety quantity. The system needs an independent hard
> interface and recovery layer. Zero error, global optimality and unlimited
> operating-domain perfection are not required.

Source hold is a bootstrap step toward a qualified terminal/recoverable set.
It is not itself such a set, is not the final goal, and must not replace
two-axis path following, bidirectional `R_mid` crossing or history continuity.

## 2. Evidence identity and recomputation

Only these tracked compact trajectory records were used for the numerical
recomputation:

| record | SHA-256 |
|---|---|
| `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c1a_result_20260814_778b454/q0_h32_r0.json` | `ee307442e0ce064fe043d51b722556a44a5be5bd5abeb848174901d2049788b7` |
| `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa2_result_20260814_8bd6964/p03_minus.json` | `358ec6b9f5e92b9d92abc8a9de642c99be4364e8779b253472a20b590bfe4dfc` |
| `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa2_result_20260814_8bd6964/p04_minus.json` | `f124d0b880d6e917e415787a6479c1645243c53c1a2923369d199e387f1252c6` |
| `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa2_result_20260814_8bd6964/p07_minus.json` | `3892ee7ccafbbb54b09fccf5dfd68cc62841f9829d0856cd3bf4fe7721f172d7` |
| `docs/codex/audits/rgeo_zgeo_1ms_nr2r2c2aa3_result_20260814_e01411d/p03_cumulative_level2_r0.json` | `7d4433d0ee5922909dad950b5f4b42ade86e282c54422d442cbac60ffa77a4c7` |

For state `k`, the descriptive response is

```text
delta_y_j[k] = y_candidate_j[k] - y_q0_j[k]
```

with `y=[R_geo,Z_geo,Ip]`. The common audit window is states 3--16;
R/Z below are expressed in mm. These are same-clock baseline differences,
not a fitted plant model or a causal decomposition theorem.

A4 schedule, gate and route semantics came from its tracked frozen config and
design report. Architecture conclusions also used the tracked current task,
status and architecture documents. This review recomputed compact state
records; it is not a new independent reparse of remote/raw TSC files. Raw
authenticity and paired-boundary integrity are inherited only from the
already recorded independent A2/A3 audits.

For reproducibility, let `D_j` be the 14-by-2 matrix whose rows are
`[delta R_j[k],delta Z_j[k]]` for `k=3..16`, in mm, and let
`bar_d_j=mean_k D_j[k,:]`. The descriptive mean matrix is
`M_RZ=[bar_d_p03,bar_d_p04,bar_d_p07]`. Conditions below use unnormalized
R/Z columns and `cond(M)=sigma_max(M)/sigma_min(M)`; per-state pair conditions
apply the same construction to the two response columns at that state.

## 3. What earlier choices got right and wrong

NR0 and NR1 remain necessary and correct: paired-boundary geometry, fail-
closed validity, exact Card15/readback/queue semantics, fixed 1100 ms source,
1 ms control and the user's cumulative `0.3 A/step` rule are not rolled back.
Canonical-source replay is useful for offline source shooting even though it
is too slow to be a 1 ms wall-clock Oracle.

The earliest substantive ordering error remains the original NR2 model
bake-off before q0 evolution, history/lag identifiability, position contrasts
and recovery had been established. That error has already been recorded.

A2/A3 made a valid correction: they showed that keeping every target inside
`q0 +/- 0.3 A` unnecessarily discarded the user's allowed cumulative slew.
Selecting p03 was also not a direction error for the source-hold bootstrap.
The new correction is narrower: a scalar drift-opposition projection and one
p03 family must not become the whole route to a two-axis controller.

## 4. Vector evidence hidden by the scalar opposition metric

The A2 state-3--16 mean responses are:

| action | mean delta R | mean delta Z | mean delta Ip | state-16 delta R/Z |
|---|---:|---:|---:|---:|
| p03-minus | +0.172736 mm | -0.183195 mm | +34.792 A | +0.218550 / -0.304729 mm |
| p04-minus | +0.160338 mm | -0.026464 mm | +51.235 A | +0.166098 / -0.061563 mm |
| p07-minus | +0.192981 mm | +0.033198 mm | +25.636 A | +0.260692 / +0.052144 mm |

Mean R/Z angles are `37.31 deg` for p03--p04, `56.44 deg` for p03--p07 and
`19.13 deg` for p04--p07. The descriptive 2-by-3 mean matrix has condition
number `2.143`. The p03+p07 pair is the best-conditioned R/Z pair under this
unnormalized descriptive construction: mean condition number `1.968`, with
per-state values `1.76--4.53`.

This is evidence of geometric separation, not qualified controllability.
The action histories are not fully matched, only one sign is represented,
combination/superposition was not tested, amplitudes are small, and no
position/history robustness exists. In particular, p07-minus has positive
scalar `delta R-delta Z` but its positive `delta Z` worsens the positive q0 Z
drift. Future authority gates must therefore use the full
`[delta R,delta Z,delta Ip]` vector, per-axis margins and a declared scaling;
scalar opposition remains only a source-drift diagnostic.

## 5. What A3 proves about cumulative action

The state-3--16 mean p03 responses are:

```text
level1 total              = (+0.172736, -0.183195, +34.792 A)
second 0.3 A increment    = (+0.182314, -0.203678, +36.103 A)
level2 total              = (+0.355050, -0.386873, +70.895 A)
```

On R/Z, define `D_1` from the p03 level1 comparator and `D_inc` from level2
minus level1 over states3--16. The descriptive scalar is
`g=<D_1,D_inc>_F/||D_1||_F^2=1.056`; the quoted `11.99%` is
`||D_inc-D_1||_F/||D_1||_F`. The per-state direction difference averages
`3.21 deg` and is at most `10.05 deg`. This is finite evidence of an
approximately proportional, slightly stronger second increment for one
source and one fixed schedule comparison. It is not a matched-state
differential Jacobian, nor a monotonicity, linearity or no-saturation theorem
beyond level2 or state16.

The q0 mean source drift in the same window is `(-5.852,+7.056) mm`.
p03 level2 is almost aligned with the required correction, but its mean norm
is only `5.73%` of the q0 drift norm. At state16:

```text
q0 source displacement          = (-9.484037,+11.876919) mm
level2 response relative to q0  = (+0.440586,-0.632120) mm
actual level2 source offset     = (-9.043451,+11.244798) mm
```

The response is about `3.7 deg` from the required correction direction but
cancels only `4.65%` of R and `5.32%` of Z at that state. The observed issue
is authority magnitude and duration, not the p03 correction direction.

## 6. A4 decision: retain once, change the expectation, forbid a ladder

A4 is not proved impossible. A3 removes level2 after issue step15, so it does
not measure persistent level2 over states17--32. No monotonicity, Lipschitz or
tail theorem permits replacing that missing observation with extrapolation.

The prior probability of a source short-hold PASS is nevertheless low. At
q0 state24 the source displacement is `(-13.657659,+17.619540) mm`; entering
the per-axis 5 mm gate would require at least a same-clock correction of
`(+8.657659,-12.619540) mm`. That is far larger than the state16 measured
level2 response, and the actual level2 trajectory is still moving away from
source near state16. This is a value-of-information judgment, not a formal
upper bound or a reported plant FAIL.

The frozen A4 identity, sequence and gates remain unchanged and unrun. It is
retained as one campaign with two preregistered replays of a bounded long-
dwell-tail plus hold discriminator. If interface, support, safety and
repeatability gates all pass, those 64 advances measure this one exact 32 ms
constant-level2 late-tail question; they do not close other histories,
amplitudes or longer horizons. The documentation must not call the
states17--32 time/history region already supported: A3 observes and qualifies
this exact source/prefix response only through state16; A4 prospectively tests
a new late state/history region.
Its `2 mm / 2 mm / 100 A` successor values are empirical stop thresholds, not
a theorem about unseen successors.

Consequently A4 is only the next implementation candidate, not an execution
authorization from this review. Before a real plant advance, a separate zero-
plant support gate must accept the prospectively frozen finite-simulator
empirical envelope, verify the state16 and per-step inner-to-outer margin, and
prove stop-before-next-advance behavior. If that gate cannot support every
late issue/effect state under the project's finite-sentinel standard, A4
remains blocked. A stop threshold observed after an unsupported successor is
not by itself pre-action safety evidence.

At the shared state16, the observed level2 path has about `40.96 mm R` and
`38.76 mm Z` margin to the 50 mm outer source envelope. Every future issue
must still be refused before advance unless the current state is inside the
25 mm inner envelope, leaving 25 mm geometric reserve to the outer envelope;
the runner must stop before any following advance after an abnormal successor
or empirical-bound breach. These margins explain the finite-simulator support
case to be audited, but do not turn the 2 mm empirical threshold into a global
plant bound.

Routing is frozen before A4 execution:

- A4 PASS still requires an independent fresh Nominal-H1 validation.
- A safe scientific FAIL ends the single-p03 static dwell/level ladder. There
  will be no A5 that merely adds another static p03 level or longer dwell.
- Any interface, causal-support, repeatability or safety failure stops for
  diagnosis under its own route. It is not a scientific p03 authority FAIL
  and does not authorize nominal/vector redesign execution.
- A4 cannot authorize recovery, transport, atlas, model fitting, MPC or
  learning under either result.

Ending that ladder is a prospective program/value-of-information decision,
not a physical inference that every higher p03 level, longer dwell or
switching law is impossible. The original A4 identity, gate values and route
tokens are unchanged.

## 7. Corrected parallel route

The route is no longer a serial claim that p03 hold alone unlocks the project:

```text
nominal track                                  vector/recourse track
--------------                                 ---------------------
one unchanged A4 tail/hold discriminator       matched-prefix vector audit/design
  PASS -> fresh Nominal-H1                     signed + cumulative R/Z/Ip authority
  FAIL -> time-varying nominal redesign        response-cone and Ip-margin gates
                 \                             /
             qualified nominal path + local-authority/
                        recourse-design evidence
                                   |
                    bounded-tube Recourse-L1 qualification
                                   |
             small recovery-backed multi-position/history HFS atlas
                                   |
       structured stable-memory/LPV model -> static recovery-backed MPC
                                   |
          shadow adaptation -> adapter sentinel -> optional dual probing
```

The vector track must use matched issue timing/history and independent q0
baselines. Existing evidence keeps p03 and complementary candidates such as
p04/p07 available for prospective selection, but A1's adverse p07-plus result
forbids preselecting p03+p07 from minus-side geometry alone. Gates need
response SNR, singular values/condition, two-sided response cone,
cumulative-level support, Ip cost, exact Card15/current/slew and whole effect
windows. Numerical rank alone is insufficient. No vector TSC may execute
until each primitive has pre-action successor support and adequate outer
margin under a separately frozen design.

The join is an AND gate: fresh Nominal-H1 evidence and qualified two-sided
vector authority with residual action margin are both required before
Recourse-L1 may be designed and qualified. If A4 safely fails, a time-varying
nominal redesign may use only already supported action/time/history cells;
new signed, cumulative or vector cells cannot generate their own safety
support inside the nominal search.

Nominal-H1 and bounded recourse remain different claims. A nominal path at
the edge of an action cell does not supply residual recovery authority.
Recourse-L1 requires a policy/tree over a prospectively declared
state/current/history tube, hard constraints throughout and arrival into a
smaller qualified terminal set. Neither branch search nor a successful
nominal sequence proves its own safety.

Atlas transport remains blocked until nominal and Recourse-L1 evidence join.
The entire transition tube and every successor must remain under already
qualified recourse coverage before transport issue. Later anchors need
provisional recourse before transport issue,
matched-position/different-history and matched-time/different-position
contrasts, and continuous belief across `R_mid`. The first HFS domain is only
an admission stage, not a reduction of the final crossing/return goal.

## 8. Model and online-learning judgment

No more advanced model is currently justified. The present bottleneck is
physical response geometry, authority magnitude, causal support and recovery,
not neural capacity. The main candidate remains exact actuator/queue plus a
stable low-order causal observer/state-space or LPV/local-mixture model, with
a small recurrent residual only if fresh whole-history evidence earns it.

The user's probe-learn-probe intuition remains important, but the first safe
form is bounded low-dimensional adaptive control, not online deep-network or
RL training. Every 1 ms step updates belief. Run-time parameter adaptation may
later update only prospectively fixed bias/gain/time-constant/mixture
coordinates under excitation, innovation, projection and uncertainty-floor
gates. It starts in shadow mode on fresh frozen-controller histories, then a
separate in-loop sentinel. Dedicated probing is last; current-probe safety is
proved using the pre-probe uncertainty set while assuming zero information
gain.

## 9. Current authorization boundary

This review completes the zero-new-TSC vector/value-of-information audit and
records the route correction. It does not implement or execute A4. The next
implementation candidate remains the unchanged A4 campaign with two frozen
replays, conditional on the separate zero-plant support gate above. A safe
scientific A4 FAIL routes to prospective time-varying nominal plus vector/
recourse design rather than another p03 static escalation. In parallel, only
a separately prospective matched-prefix vector-authority design may be
written.

No controller/model code, server deployment, TSC, training, fit, atlas,
Nominal-H1 claim, Recourse-L1 claim, MPC, adaptation or RL is authorized by
this documentation result.
