# Stage4.2R3c3T13S2 quantized-actuation and causal-observability report

## 1. Result

Stage4.2R3c3T13S2 completed one read-only audit of all 52 immutable T13S1
raw files. It ran zero controller, Ray, `gotsc`, TSC, or plant steps.

The exact Card15 target-current reconstruction did not equal the subsequent
TSC `coil_currents.csv` readback at the frozen `1e-9 A` gate:

```text
transitions                                      2,600 / 2,600
coil components                                36,400 / 36,400
exact components                               13,000 / 36,400
within 1e-9 A                                  13,000 / 36,400
maximum absolute residual A          1.0000000003174137e-5
RMS residual A                       4.016644437379113e-6
clipped components                                      0
active-action zero-effect components                  264
primary route             ACTUATOR_MAPPING_IMPLEMENTATION_GAP
```

This is not a runtime, packaging, raw, restart, statistics, reporting,
plant-control, or real-MPC failure. It identifies an omitted target-to-TSC-
readback layer in the actuator model. The T13S2 gate is not weakened and the
T13S2 output remains a FAIL at that exact-reconstruction question.

## 2. Exact identities

```text
branch
  codex/stage4_2r3c3t13s1-transition-sentinel
T13S1 closure and T13S2 design
  854c9ae
T13S2 implementation
  626f635
T13S2R1 prospective design
  c926dad
T13S2R1 implementation
  ae4241b
```

Remote T13S2 output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s2_audits/
stage4_2r3c3t13s2_quantized_observability_20260801_626f635

report
  9ef183d20f3354d11bb70c2324bade6829879f00c05dd96b99c1312bcfd53d58
manifest
  564569ec948399792d2db49c4d5742e70a2b20c9ad48efaad7eda34f95f096dd
```

Remote T13S2R1 output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s2r1_audits/
stage4_2r3c3t13s2r1_readback_residual_forensics_20260801_ae4241b

report
  62b28bec07bde398cfec6b4aaf42899960e63a8761ce19316f83e8c929903c87
manifest
  adf0cc73a6bc9b05a6dbe7a9fdae09b80346fe54a41a4723fb9cfce0d0bf2edf
```

Both compact output pairs were copied directly and uncompressed into the
matching `docs/codex/audits/` directories. Their JSON parses and hashes match
the server. All 52 raw files remain server-side.

## 3. Causal-observability result

T13S2 formed 48 issue records using only formal task step, numeric target,
current/past R/Z/Ip, causal velocity or explicit unknown initial velocity,
measured coil currents, prior current-run actions, authenticated queue state,
and finite development actuator setting. Pair/history/prefix labels and wire,
source, future measurement, and future schedule inputs were excluded from
the causal feature.

```text
issue records                                            48
exact causal-feature collision groups                     8
same feature plus same applied-current-path groups         0
exact observational alias groups                           0
matched-history causal-feature exact matches             0 / 24
matched-history finite clean separations                24 / 24
causal route                          FINITE_CLEAN_SEPARATION_ONLY
```

The eight feature collisions all received different realized current paths,
so they do not prove hidden-state aliasing. Conversely, the absence of an
exact alias in four clean development contexts does not certify an observer.
The matched-history scaled clean-state differences were nonzero, with:

```text
scaled R/Z/Ip L2                        0.01084 -- 0.18875
scaled velocity L2                      0.00000 -- 0.52796
coil-current L2 A                       0.00000 -- 2.41927
prior-action L2                         0.00000 -- 1.25840
forbidden wire-current RMS A            0.03656 -- 3.52712
```

The wire values are offline diagnostics only. Finite clean separability does
not validate independent histories, arbitrary restart states, measurement
noise, or continuous actuator parameters. Unresolved latent effects must
remain set-valued.

The separated first-effect layers reproduced the preceding forensic result:

```text
numeric decision symmetry                         24 / 24
observed current symmetry                          0 / 24
immediate plant symmetry                           3 / 24
```

## 4. T13S2R1 residual forensics

T13S2R1 preserved the T13S2 FAIL and expressed the target-to-readback
residual in `1e-6 kA-turn` output-grid units. The residual was constant per
coil across all 2,600 transitions. Using only the four baseline runs gave:

```text
baseline components                                 2,800
constant per coil                                      yes
calibrated units in TSC order
  [2, 2, 2, 2, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0]
maximum integer-grid residual          1.1870724625495654e-8
```

The fixed 14-coil bias then predicted every signed-probe readback without
using the signed-probe data for calibration:

```text
signed-probe components                            33,600
within unchanged 1e-9 A                           33,600
exact floating equality                           26,850
maximum residual A                    2.842170943040401e-14
RMS residual A                       6.599555857889406e-15
route                    FIXED_DEVELOPMENT_READBACK_BIAS_IDENTIFIED
```

This is a retrospective split inside the already inspected T13S1
development set, not an independent scientific holdout. The fixed bias may
be used only as a traced nominal actuator term. A nonzero uncertainty set is
still mandatory.

## 5. Validation and error classification

Local validation actually run:

```text
Python compile                                             PASS
T13S2 direct focused tests                              6 / 6 PASS
T13S2R1 direct focused tests                            3 / 3 PASS
Windows complete unittest
  272 tests reached; 27 Linux-only imports failed on missing resource
  classification: local platform limitation, not a test PASS
local pytest
  NOT RUN: neither local Python environment contains pytest
```

Server validation actually run:

```text
exact T13S1 package checksum verification                 PASS
declared shell bash -n                                    PASS
package Python/JSON/scientific guards                     PASS
T13S2 py_compile and direct tests                      6 / 6 PASS
T13S2R1 py_compile and direct tests                    3 / 3 PASS
complete canonical unittest                      639 PASS, 1 skipped
```

| Class | Result |
|---|---|
| runtime/environment | zero |
| package/import on server | zero |
| raw/snapshot corruption | zero |
| statistics/reporting | zero |
| T13S2 actuator model completeness | FAIL: readback layer omitted |
| T13S2R1 finite development readback structure | fixed per-coil bias identified |
| exact observational alias | none in the finite clean set |
| observer/history/noise extrapolation | not validated |
| plant transition predictor | not validated |
| real MPC | not tested |

## 6. Frozen next route

The required next interface is `QUANTIZED_MULTI_HYPOTHESIS_TUBE`:

- exact Card15 target-current serialization;
- traced fixed development readback bias as a nominal term;
- nonzero actuator/readback uncertainty bounds;
- causal observer state with unknown restart velocity;
- exact issued-command queue;
- multiple plant/hidden-history hypotheses or an additive response tube;
- no point-model certification from T13S1/T13S2.

Formal timing remains 250/270 ms arrival and 350/370 ms hold. No T11 bank,
R3c4, real MPC campaign, expert dataset, BC, DAgger, or bounded residual RL
is authorized by these audits.
