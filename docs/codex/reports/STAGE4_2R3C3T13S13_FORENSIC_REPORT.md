# Stage4.2R3c3T13S13 forensic report

## Result

Stage4.2R3c3T13S13 stopped prospectively at the training-model gate. Its
exact route is:

```text
RECURRENT_CAUSAL_SEQUENCE_TUBE_INSUFFICIENT_REDESIGN
```

This is a finite causal observer/response-center design failure. It is not a
runtime, TSC, restart, raw-corruption, actuator-execution, summary, controller,
MPC, or plant-unreachability result. Calibration and fresh holdout were never
opened.

## Revisions and remote evidence

```text
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel

executed package checkpoint before real TSC
  c6c81fd Fix T13S13 snapshot digest validation

final reporting/extraction checkpoint
  f220714 Correct T13S13 consumed q2 effect extraction

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s13_runs/
  stage4_2r3c3t13s13_recurrent_sequence_tube_identification_20260802_c6c81fd

remote compact audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s13_audits/
  stage4_2r3c3t13s13_recurrent_sequence_tube_identification_20260802_c6c81fd/
  stage4_2r3c3t13s13_server_audit.json
```

The immutable execution package digest is
`9c692de448350d1fa73e4857b925291f81580ff5239352b2bd33bfae1003059d`.
The final reporting package digest is
`7e95aef675c2b65384136c974f7aa7e6290d69a27b5dcdfda204b44cd0ba03ce`.
The compatibility record confirms unchanged config, controller revision,
probe primitive, context/spec digests, physical action semantics, and formal
timing, with all 408 raw files preserved.

## Execution and raw inventory

The complete design planned 1,088 new trajectories, but its phase gates
allowed only the training portion to run:

```text
consumed q1/q2 training raw                         136 / 136
new training baselines                              24 / 24
new training signed probes                         384 / 384
new raw actually executed                          408 / 408
equivalent training raw                            544 / 544
calibration raw                                      0 / 340
fresh-holdout raw                                    0 / 340
```

All 408 new raw JSON.GZ files remain on the server. Independent server
postprocessing parsed 408/408, found 408/408 `success=true`, no corruption,
and no runtime/environment error. Their inventory digest is
`90c30ca5caca89c7de03587432b0f6cd20d28f2270c9765a68869903fd6e67e7`
over 21,634,348 bytes.

Training execution recomputation passed 24/24 baselines and 384/384 probes.
Fresh controller/TSC process, exact restart, controller-trace causality,
Card15 application, cancellation, requested/applied zero net, current limits,
and forbidden-input checks all passed. Formal tracking passed 10/24 baseline
and 128/384 probe trajectories, but it was preregistered as diagnostic only
for identification rollouts and is not a control success or safety gate.

## Two semantics-preserving analysis hotfixes

The first training-baseline invocation completed all 24 real trajectories,
then reporting raised `KeyError: coil_currents_a`. The authenticated public
R3b state table intentionally omitted private coil/wire fields required by
the inherited restart audit. Checkpoint `baa8d64` rebuilt each complete state
from the exact authenticated R3b raw, required equality to every public field,
and changed no worker, controller, action, spec, or raw. Resume reused all
24/24 files and reran zero plant tasks.

The first `fit-training` invocation later stopped before model fitting at
`post-queue effect contract mismatch`. Exactly 32 authenticated T13S5 q2
delay-2 training probes retained the historical erroneous declared effect
states 3/17 although that campaign applied its wrapper after the delay queue.
Raw forensics found:

```text
affected q2 rows                                      32 / 32
issue / stale declared effect                 0/3 or 14/17
actual physical effect                         issue + 1
pre-effect R/Z maximum                               0.0 m
pre-effect Ip maximum                                0.0 A
pre-effect coil-current maximum                      0.0 A
nonzero current response at issue+1                 32 / 32
```

Checkpoint `f220714` accepts only the exact authenticated
`Stage4.2R3c3T13S5`, delay-2, `declared=issue+delay+1` legacy provenance,
requires exactly 32 such training rows, and otherwise fails closed. This
implements the already frozen T13S13 post-queue effect states 1/15; it does
not change experimental semantics. Local, empty-package, and installed-server
complete unittest discovery each passed 758 tests; the isolated package and
server each had one expected skip.

## Training-model failure

After the hotfix, extraction and all identification/interface gates passed:

```text
training contexts / response rows                    32 / 512
central signed groups                               256 / 256
target action symmetry                              256 / 256
observed current signal/symmetry                    256 / 256
pre-effect causality                                512 / 512
pre-action input-box containment                    512 / 512
history support / action support                    512 / 512
componentwise provisional-tube containment          512 / 512
post-effect measured-current model inputs              0
disjoint exact or near aliases                         0
legacy q2 effect provenance                          32 / 32
```

All 54 frozen ESN candidates were finite and eligible. The training-only
whole-source-pair CV winner was rank 8, `rho=0.35`, `leak=0.5`, and
`ridge=1e-4`, with interaction condition `1.0119`. Its CV maximum and mean
scaled center-relative errors were `0.991216` and `0.166437`. Refit on all
training rows passed the unchanged `<=0.10` center-error gate only 301/512;
the maximum was `0.964298`. Every one of the other support and tube gates
passed, so the 211 failures are exclusively response-center errors.

Failures occur in both hidden-history members, both windows, every direction,
and all 16 whole source pairs. The braking window passed 183/256, while the
transport window passed only 118/256. Increasing observer rank in a
post-result development diagnostic to 16--32 worsened whole-pair CV; simple
causal nearest-local-Jacobian interpolation also failed, and even a
12-neighbor retrospective oracle repaired only 473/512. These diagnostics
are route evidence, not a revised T13S13 result.

The structural limitation is causal observability: delay-2 transport issues
at task step zero, before any visible dynamic response can identify hidden
vessel/eddy-current history. Natural-history recurrence cannot create
information that has not yet been excited. A same-trajectory active
calibration must precede transport and must remain inside the immutable
arrival deadline.

## Evidence identities

```text
run manifest SHA-256
  82f5d3ce31af44cd451a57e72c5e534895c47f2563bf8fb9521a810f022a6df1
state SHA-256
  fb410c823047df89e131acb31bc5b60b226feff75e50f0c8d51d2b0f0069b48b
hotfix compatibility SHA-256
  c66514ee6550323a269b0d1dc8435a30b2576bfce21bc30f94691030934a4e16
training baseline gate SHA-256
  8ec80ccbb528bdc978ad233e70dc8b5414f40c197a94ffe6a008a6306606e464
training probe execution SHA-256
  40f70ae439838d1c608c55a54e09f1f3613abc0721bbe0b85c49f4e7bf1baaec
training model audit SHA-256
  89cbafb62601dbf156a8b0c8395a6b52bb0308987142638172150da826f4b9b8
server audit SHA-256
  b2cd6175190ec6c6a22752c8f7bd0462d696d3b59befd0bde695cfbd55f52b69
raw inventory audit SHA-256
  5fffe3b1eb0750e0f94c934716aa00fe81118b9a740814936ae55ffc3f74ca38
```

No model or final tube was frozen. No real MPC or control rollout ran. Probe
trajectories remain forbidden from expert data. Expert collection, BC,
DAgger, and bounded residual RL remain unauthorized.

## Next action

Stage4.2R3c3T13S14 is a prospective same-trajectory active-calibration
sentinel. It must prove that a fixed, causal, zero-net, current-safe early
excitation produces an informative deployable history and improves
whole-pair prediction before a full train/calibration/fresh-holdout campaign.
The formal 250/270 ms arrival and 350/370 ms hold contract remains unchanged.
