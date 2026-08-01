# Stage4.2R3c3T13S3 quantized causal tube interface report

## Result

The frozen T13S3 outcome is:

```text
INTERFACE_COMPLETE_HOLDOUT_REQUIRED
```

T13S3 implemented and validated the required software boundary. It did not
fit a plant model, run a controller, start Ray or `gotsc`, execute TSC, or
take a plant step. It therefore has no real control, restart, or robustness
result.

## Exact revision and paths

```text
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel
implementation commit
  37e391361b7d397b90bd2f2747918084bf443e0a
remote staging
  /home/yangshen0711/tsc_software/
  stage4_2r3c3t13s3_quantized_tube_37e3913
remote installed project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
remote validation log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
  stage4_2r3c3t13s3_server_validation_37e3913.log
validation-log SHA-256
  f70598458c08aee524298bb402789c7097b66203e50cc9332a2b5942ce15dfc5
```

The deployed source hashes are recorded in the adjacent machine-readable
audit. All five deployed files matched their local SHA-256 values exactly.

## Implemented contracts

The exact Card15 primitive now performs the source-defined current/slew and
action clipping, TSC-order turn conversion, ten-character `.3E`
serialization, and text round-trip. Its next-readback nominal subtracts the
T13S2R1 development bias:

```text
[2, 2, 2, 2, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0]
  * 1e-6 kA-turn
```

The nominal carries T13S2R1 report hash
`62b28bec07bde398cfec6b4aaf42899960e63a8761ce19316f83e8c929903c87`.
Every coil retains at least one output-grid unit of prospective uncertainty;
the development bias is not represented as a universal constant.

The causal observer state is immutable and stores only current-run numeric
measurements, issued commands, the authenticated numeric queue, causally
available controller state, hypothesis/tube state, and provenance. Restart
velocity is explicitly `unknown_interval`; one causal difference changes it
to `finite_difference` with a nonzero interval. Pair/history/prefix,
wire/vessel current, source action/result/current, future information,
schedule, and nearest-R17-phase fields fail closed, as do unknown extras.

The set-valued transition interface evaluates every supplied affine
hypothesis, propagates additive interval uncertainty, unions all hypothesis
tubes, and reports measured/interpolation/extrapolation support without
changing the formal task clock. Empty or unsupported hypothesis queries fail
closed. The output fixes both:

```text
point_model_certified          false
robust_controller_authorized   false
```

## Validation

```text
local focused tests                         15 / 15 PASS
local isolated direct-copy tests            15 / 15 PASS
local compileall                                      PASS
local JSON parse                         2,648 files PASS
server isolated source hashes               10 / 10 PASS
server isolated focused tests                15 / 15 PASS
frozen predeployment package hashes        269 / 269 PASS
server installed focused tests               15 / 15 PASS
server installed complete tests             654 / 654 PASS
server expected skips                                  1
server non-run-tree JSON parse               189 files PASS
TSC/plant steps                                        0
```

The local complete suite executed 287 tests but had 27 import errors because
Windows does not provide the POSIX `resource` module. No T13S3 test failed.
The authoritative Linux complete suite passed 654/654 with one expected
skip. A post-validation process audit found no remaining Python, Ray,
`gotsc`, or TSC process; the three transient `pgrep -f` matches written in
the log were matches against the validation command text itself.

## Scientific classification

There was no runtime/environment, packaging/import, raw/snapshot,
statistics/reporting, or interface-implementation error. There was also no
new raw trajectory and no real controller result. This stage neither repairs
T13S1 nor validates a point predictor, observer, hidden-history robustness,
or MPC feasibility.

The only authorized continuation is a separately frozen, minimal,
lattice-aligned transition holdout using independent real TSC trajectories.
The formal 250/270 ms arrival and 350/370 ms hold endpoints remain unchanged.
Probe/holdout trajectories remain forbidden from expert datasets; real MPC,
R3c4, BC, DAgger, and bounded residual RL remain blocked.
