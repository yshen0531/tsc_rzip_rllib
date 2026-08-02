# Stage4.2R3c3T13S14 forensic report

## Result

Stage4.2R3c3T13S14 completed all 144 authentic trajectories. Its exact final
route is:

```text
ACTIVE_CALIBRATION_SENTINEL_FAIL_REDESIGN
```

This is a finite same-trajectory active-calibration observer/response-model
design failure. It is not a runtime, TSC, restart, raw-corruption, actuator,
summary, plant-restart, controller, MPC, or plant-unreachability result.

## Revisions and remote evidence

```text
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel

preregistered design and implementation
  e7768bc Correct T13S14 preregistered event counts
  0d2c4ae Implement T13S14 active calibration sentinel

execution/reporting corrections
  9da4727 Repair exact S14 calibration lattice counts
  d4393ee Repair exact S14 response lattice counts
  d206ae5 Ignore TSC wallclock fields in S14 prefix audit
  7b73c33 Serialize unavailable S14 candidate diagnostics

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s14_runs/
  stage4_2r3c3t13s14_active_calibration_sentinel_20260802_113348
```

The immutable raw-execution package digest before the two reporting-only
corrections is
`6c24faaf799fe61a7a6be0e169098b1523884c5b821c76e69704de697b3fa855`.
The final reporting package digest is
`9e5f36072a34f87742b8617f2e3a9abe89317ba231fbba71b4aadf3f48407746`.
The config SHA-256 is
`8f39b2417ca8b36e4849986eb126356507ffde0a466386b1effd3812e3d9fa17`.

## Execution and raw inventory

Independent server-side recomputation found:

```text
calibrated baseline raw                              16 / 16
signed response raw                                128 / 128
all raw parsed/successful                          144 / 144
fresh controller and TSC process                   144 / 144
exact initial plant restart                        144 / 144
causal controller/phase traces                     144 / 144
pre-response semantic prefix equality              128 / 128
calibration pulse pairs                            576 / 576
calibration issue/cancel events                   1152 / 1152
calibration plus response zero-net groups          704 / 704
response issue/cancel events                        256 / 256
runtime/environment errors                                   0
restart failures                                              0
causality failures                                            0
actuator/zero-net failures                                    0
raw corruption                                                0
```

The raw inventory contains 144 JSON.GZ files and 7,843,596 bytes. Its digest
is `9c395e3b3affa9309888737d7d6bfc789b35a09c21a0b744c97c7c28643e9db8`.
Maximum current utilization was `0.3924`, below the frozen `0.55` limit.

Formal control was diagnostic only for this identification experiment. It
passed 4/16 baselines and 32/128 response trajectories. Exactly the two p9/q1
pairs passed all 18 of their baseline/response variants; every other pair
passed 0/18. This is not a controller success claim, and the 250/270 ms
arrival and 350/370 ms hold contract was not changed.

## Four code/reporting corrections

The first baseline attempt completed 13/16. Three remaining tasks failed
before trajectory state zero because floating Card15 centers did not admit
the initially rounded exact central-symmetry count. Checkpoint `9da4727`
selects the nearest exact integer count without changing the direction,
sign, multiplier order, config, gate, or formal timing. The 13 successful raw
were preserved and only the three zero-plant-advance failures were rerun.

After 16/16 baselines, the zero-TSC response-lattice audit passed 104/128 for
the same count-rounding reason. Checkpoint `d4393ee` scopes the same exact
integer repair only to response issue/cancel selection. It changed no raw and
performed no plant advance. The recomputed lattice passed 128/128 before the
response campaign opened.

All 128 real response tasks then succeeded, but the first report said 0/128
because it compared complete state dictionaries and included
`gotsc_subprocess_s` and `step_total_s`. Raw forensics found zero semantic
state mismatches, zero action-prefix mismatches, and exactly 2,560 differences
in those two wall-clock fields. Checkpoint `d206ae5` excludes only those
nonphysical timing fields. It reran zero raw and recomputed 128/128.

The first finalization later raised strict-JSON `ValueError` at
`$.candidates[54].maximum_error` because a structurally ineligible kernel
candidate used `inf` for an unavailable diagnostic. Checkpoint `7b73c33`
serializes unavailable diagnostics as JSON `null`; eligibility and every
scientific gate remain unchanged. A fourth audited resume preserved all 144
raw and added zero plant advances. Server package verification passed 336/336
hashes, 14/14 focused tests, and 772/772 full tests with one expected skip.

These corrections separate two preaction execution bugs from two pure
statistics/reporting bugs. None changes successful controller actions or the
scientific experiment identity.

## Identification and model result

The excitation/interface gates all passed:

```text
signed response groups                               64 / 64
target-field central symmetry                        64 / 64
observed-current signal and symmetry                 64 / 64
development signal                                   64 / 64
pre-effect causality                                128 / 128
input-box containment                              128 / 128
distinct active-calibration history signatures        8 / 8
```

All 54 ESN candidates were structurally eligible, but none passed whole-pair
CV. The best maximum-error candidate used `rho=0.65`, `leak=1.0`, observer
rank 4, and ridge `1e-4`. Its condition was `1.03399`, but it passed the
center gate only 36/128, tube containment 119/128, and the joint gate 36/128.
Its maximum and mean scaled center-relative errors were `1.18137` and
`0.286426` against the frozen `<=0.10` requirement. Directional center passes
were:

```text
mode0_without_coil8                                  1 / 32
mode0_coil8_component                               23 / 32
mode1                                                0 / 32
mode2                                               12 / 32
```

The failures are nearly symmetric between response signs and both hidden
history members. They are response-center/model failures, not central
symmetry or stochastic-noise failures.

All 12 frozen kernel candidates failed their structural condition gate in all
96 folds. Their finite regularized conditions ranged from approximately
`2.29049e5` to `1.02884e10`, far above 30. Consequently no model was selected
and no controller or MPC artifact was produced.

## Retrospective redesign diagnostics

The following server-side analyses reuse the failed S14 data. They are route
diagnostics only, not validation and not a revised S14 result.

* A 63-candidate wider-ridge kernel sweep made 13 candidates numerically
  eligible but produced zero model passes. The best maximum error remained
  approximately 1.00; the best stable broad kernel passed at most 34/128
  center rows.
* Thirty direct raw-history PCA-by-action models were all well conditioned
  but produced zero passes. The best variant passed 52/128 center rows with
  maximum error approximately 1.02.
* A forbidden same-pair-other-history oracle passed only 93/128; a forbidden
  same-regime-other-prefix oracle passed 87/128. A legal nearest-causal-history
  rule also peaked at 93/128. These are not deployable solutions.
* A same-regime, other-pair, two-history response box contained 0/128. An
  all-other-pair box contained only 86/128, although all widths stayed below
  the physical caps.
* Uniform residual-tube expansion gave 125/128 containment with 128/128 caps
  at multiplier 4. Multiplier 8 reached 128/128 containment but only 16/128
  caps. No tested set-valued candidate passed both.
* A direct within-trajectory fit failed 0/128. Forensics showed why: the
  eight S14 calibration deviations and the eight later response deviations
  each span rank eight relative to their moving controller centers. Eight
  observations therefore cannot isolate a fixed four-dimensional response
  basis plus natural drift.

Together these results rule out a mere ridge, encoder, nearest-neighbor, or
uniform-tube fix. The S14 sequence replans each direction around a changing
Card15 center, so the supposed four-direction calibration is not a fixed
four-dimensional input experiment.

## Evidence identities

```text
manifest
  4159ecd6a8b00aabbae5708a6b052240f83ac2cfc7deb179ed0ae9da6d245163
state
  e42e9295852590d20db67610e6d54692038240122f0ec08acdecad612b5bd5b5
baseline gate
  af41f0d9b9f81f2a0590fb087ca24e646da82f6176a90d2c2a5c1d674fdb4f93
probe execution
  956e81c6ae7f5b9a260d2be9dcdaa44a97d60587f75a56816859b7a6193eb585
final model audit
  1fcabd6e37efdde8723c50b4f490538c555a334d46563289de36cae7b8767a5b
final result
  9ddaa6f89b38843cfc4aa00ff9ae2297986cfedcbff6b5bad7f89b948e1fe941
independent postprocess
  2a8bae98da9d189e8a7f1a35c1f461229b691fd08cbca3d38bb9c0e136b6aade
finalize reporting hotfix audit
  383dfdd3739391fa014abffbfd025ca4160ba3dfa11cf658e2d21c67cd5ab187
```

Probe trajectories remain forbidden from expert data. Expert collection,
BC, DAgger, and bounded residual RL remain unauthorized.

## Next action

Stage4.2R3c3T13S15 must freeze each trajectory's four physical calibration
increments at its initial visible state, apply explicit signed pairs relative
to the contemporaneous baseline center, and estimate the local response from
that trajectory alone. This removes S14's moving-center rank inflation while
keeping the calibration at eight steps and preserving the formal timing.
