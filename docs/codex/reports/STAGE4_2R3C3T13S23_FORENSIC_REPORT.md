# Stage4.2R3c3T13S23 forensic report

## Result

Stage4.2R3c3T13S23 completed twice with byte-identical outputs. It is a clean
action-schedule-design FAIL:

```text
SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_FAIL_SCHEDULE_REDESIGN
```

S23 executed no Ray task, `gotsc`, TSC, controller, plant step, or snapshot
operation. It therefore makes no real closed-loop, restart-robustness, plant
reachability, or MPC conclusion and does not authorize S24.

## Code and deployment identity

```text
local branch
  codex/stage4_2r3c3t13s23-sequential-preflight
implementation/deployment commit
  7aab947 Implement S23 sequential lattice preflight
config SHA-256
  b16c0a77394805d2a9274b08b1e009a82d563ac48852c016c8444c41e777732a
audit-tool SHA-256
  8e08309b27606397308dfaa19d1695727c4dfaeb94616bcd7549f8dcf3c3c288
preregistered-design SHA-256
  f155bf6010164247e3a6bf47137523f40efe500c191a04a9c884b971fce2482c
PACKAGE_MANIFEST.json SHA-256
  72ad0288d2ed22dec8cba7a82a80a15008970a1b48cd985713977f3cadf3fd4d
SHA256SUMS SHA-256
  c9b3deaa4e85d9ef3dba2728a9a5373a222d4b47230a51df786e307b6d2b55c2
declared package files
  447
```

Three preregistration inconsistencies were corrected before implementation,
deployment, or any S23 computation, in commits `226e0ea`, `1f20cbe`, and
`90b2a57`: the inherited incremental-action limit is `0.25`, the four columns
use the exact S21 active-calibration QR order, and the exact-Card15 search
radius is `16`. No S23 result was available when those corrections were made.

## Server paths and validation

```text
staging package
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s23_7aab947
canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
primary output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s23_audits/
  stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight_20260803_091116
independent output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s23_audits/
  stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight_independent_20260803_091545
primary log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight_20260803_091116.log
```

Local focused tests passed `8/8`. Local complete discovery ran 520 tests;
the only 27 errors were the repository's already-known Windows-only imports
of Unix `resource`, with no S23 failure. The empty-directory deployment
simulation verified all 447 files and passed `8/8` focused tests. Both the
server staging tree and installed canonical tree passed package verification.
Their complete server-virtualenv suites each passed 887 tests with one
expected skip. Installed validation hashes are:

```text
staging complete-test log
  f6fa5c798edf9e121dd65e0e5a3dcfd284a36b77edf90b02d88b07c0ea8ef595
installed package-verification log
  1ddf052facaca5a66243744c8a72af4b9f061466945036f295a4cb51b8006170
installed complete-test log
  2ad7a894311c223e313261bd946bd496c235d14021497cbf3bc6555a13c540ed
```

All server Python commands used
`$HOME/tsc_all/tsc_simulation/venv_simu/bin/python`; no global Python or
package installation was used.

## Source authentication and output inventory

S23 read the immutable completed S21 run and final S22 audit in place:

```text
S21 run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s21_runs/
  stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353
S22 audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s22_audits/
  stage4_2r3c3t13s22_full_horizon_affine_authority_20260803_080437
```

It authenticated all 360 S21 raw files and reproduced 40/40 baseline and
320/320 measured-probe formal metrics. The reproduced formal pass counts
remain 16/40 and 99/320. No source raw file was copied or modified.

The primary output contains exactly three strict JSON files:

```text
detailed rows     3,840 events, 10,858,675 bytes
SHA-256
  ca8c8cab25a3a09a6b7b673ff9bda2e0461733afc3f1dbb207b407aae7a47ee9
summary           1,798 bytes
SHA-256
  5188d583baf977e145eb5d33680b87d4ff901155bd8dd5ba3c662503dfeb50ab
manifest          751 bytes
SHA-256
  fb18b72b4064641500f14f727a863f7f385155296fd29d12eb98b82a63adb003
provenance digest
  039928be13c0b3cebd49ac2f9f95b0a7a5fa3c4129b68f21bb6cbb39d23be176
```

The independent invocation used a new output path and reproduced all three
hashes byte for byte. The 10.86 MB detailed file remains on the server; only
the compact summary, manifest, and logs were downloaded.

## Gate recomputation and failure localization

The non-failing gates were:

```text
finite issue/cancel constructions                         7680 / 7680
fixed rank-4 basis contexts                                  40 / 40
exact target reproduction                                  3840 / 3840
exact stored-center cancellation target                    3840 / 3840
exact zero target-field jump net                            3840 / 3840
central-sign Decimal target symmetry                        1280 / 1280
global rank-16 and condition contexts                          40 / 40
slot rank-4 and condition blocks                             160 / 160
late-slot novelty contexts                                     40 / 40
maximum global normalized condition                     1.6539378019
maximum slot normalized condition                       1.1695106354
minimum late-column residual                            0.9428090416
maximum total normalized action                        0.3366666667
maximum predicted current utilization                         0.3917
```

Issue construction passed only 1,920/3,840. Independent row-level
recomputation exactly reproduced every saved issue gate:

```text
sign, active magnitude, coordinate-error pass              3840 / 3840
desired/applied cosine >= 0.98                              2880 / 3840
off-basis residual <= 0.10                                  1920 / 3840
issue incremental action <= 0.25                            3840 / 3840
issue total action/current/finite/reproduction              3840 / 3840
only off-basis failed                                        960 rows
cosine and off-basis both failed                             960 rows
maximum off-basis residual                              0.2682996784
minimum desired/applied cosine                          0.9567402699
maximum issue incremental action                       0.0944439202
```

The failure pattern is structural, not context-specific: every one of the 40
contexts passed 48/96 issue rows, every slot passed 480/960, and the same
dense Hadamard sign families failed in every context. Thus a different
history, partition, or baseline state does not explain the failure.

Cancellation passed 3,720/3,840. All 120 failures were solely the unchanged
`0.25` incremental-action cap at slot 3. They were confined to five
contexts, 24 rows per context. Exact center return, exact zero target jump,
total action, current utilization, and finite checks were 3,840/3,840. The
maximum cancellation incremental action was `0.3106592894`; no cancellation
saturation, clipping, or target-exactness defect occurred.

## Scientific classification and next route

There was no runtime/environment, import/deployment, raw/snapshot,
authentication, statistics, reporting, restart, solver, controller, or plant
failure. The frozen simultaneous four-direction Hadamard schedule is not a
valid exact-Card15 sequential excitation under its own unchanged geometry and
incremental-action gates.

S24 remains vetoed. The next work is a new-identity, zero-TSC schedule
redesign. It may change the amplitude, coordinate sparsity, sequence matrix,
or knot locations prospectively, but may not relabel S23, relax S23's observed
gates, change formal timing, or make a plant/MPC claim. A candidate must be
frozen and independently revalidated before it can authorize any new real
identification campaign. Expert data, BC, DAgger, and bounded residual RL
remain prohibited.
