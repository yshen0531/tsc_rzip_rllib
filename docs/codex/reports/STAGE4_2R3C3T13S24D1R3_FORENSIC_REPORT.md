# Stage4.2R3c3T13S24D1R3 forensic report

Status: final zero-new-TSC causal split-return preflight result.

## Identity and evidence boundary

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition

prospective design checkpoint
  f05a632

scientific implementation checkpoint
  1ccd0e3

final package checkpoint
  93afef5

package revision
  r42r3c3t13s24d1r3_causal_split_return_preflight_v1

installed PACKAGE_MANIFEST.json SHA-256
  65591c63bd553219e87baeb6045c891156c6897731b29d70301ed670c16459e9

installed SHA256SUMS SHA-256
  56ce529ec90ad2cdc61a4d66ec5a47bec6b920d3352ca46878eea2e3fc6b4cf5

D1R3 config SHA-256
  358ca26ab1690f714b2690b58d5457204704d51bd9a7a183aec1c3936fb75e56

D1R3 implementation SHA-256
  f1d0877a0a901680319417de3148971be621962b1aff4fe25b600ba8bb7d8e18
```

The immutable D1R2 source run was:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r2_runs/
stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_20260803_160327_9e6bba2_v2
```

D1R3 authenticated its exact 54-file, 3,078,383-byte raw inventory digest
`eb4ac8c0e606ce0d8899f0a512b594877f59cc9424c0f6a87e3450bcd036cc83`,
the 54-spec digest, both D1R2 forensic outputs, complete rollout log, final
state/manifest/route, and all 18 selected restart snapshots.

The primary output and complete log were:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r3_audits/
stage4_2r3c3t13s24d1r3_causal_split_return_preflight_20260803_170619_93afef5

/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
stage4_2r3c3t13s24d1r3_offline_20260803_170619_93afef5.log
```

The complete log SHA-256 is
`d6c863bcee14b324122e5b0b4ed50db3d54a9187acd2fbf002598e26596a4fa3`.

## Validation and packaging incidents

The initial local implementation used a generic canonical-JSON inventory
digest instead of D1R2's frozen per-file `name\0size\0sha\n` digest. This was
found by source review before deployment and corrected before any D1R3 result
opened. It was a pre-execution reporting/authentication implementation bug;
it did not affect D1R2 raw or controller semantics.

The first installed-package verification then found that the old D1R2 package
inventory omitted the later committed retrospective audit source and its one
test. D1R3 never ran from that incomplete inventory. Package checkpoint
`93afef5` added both files and raised the exact inventory to 527 files.

Final validation was:

```text
local compileall / inventory JSON parse                    pass / 79 JSON
local focused tests                                             13 / 13
local empty-directory checksum deployment                     527 / 527
local complete discovery                     551 pass / 27 Windows-only errors
server staging package verification                            527 / 527
server installed focused tests                                  13 / 13
server installed complete tests                   945 / 945, one expected skip
```

All 27 local errors were the unchanged Windows absence of the Unix `resource`
module. The Linux virtual-environment suite had no corresponding failure.
Only `/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python` was used
on the server.

## Raw and replay result

The preregistered 54-controller causal replay completed twice in independent
new output directories. The four prospective output files were byte-identical
between runs:

```text
detailed SHA-256       812c8fccbe5246e7149bced28ec746b7c15c91e241f2feaeda9a6c9f8033909a
summary SHA-256        6c1edd1235d57560bbf5fd2b630f620dc8919045dbab70c3d67eac70969e17e5
manifest SHA-256       dc66a3dc9427468d8fea17bc892682a213322b58e18e89ac451d15fcf10cdb59
sentinel specs SHA-256 5c26680bc1483148a95cca9a06bb4eb546d01e385af6a907941d4b74b82a0d1a
```

An independent post-result server audit strictly parsed all 54 D1R2 raw files
and reconstructed the saved direct action, interpolation, Card15 fields,
Decimal telescope, identity map, and candidate table. Its SHA-256 is
`4325003dfd6d3bbcb5e0f89f605450bd274fb8466062b488b8edaf797dc164ae`.

```text
source raw strict parse / exact inventory                    54 / 54
causal controller replays                                    54 / 54
source action prefixes exactly reproduced                    54 / 54
source trace prefixes exactly reproduced                     54 / 54
unchanged full-success paths                                 45 / 45
unchanged structured-stop prefixes                            9 / 9
saved direct failure action/value reproduced                  9 / 9
split-start construction and all frozen gates                 9 / 9
candidate fresh D1R4 identities                               9 / 9
new raw / snapshots / Ray / gotsc / TSC / plant advance       all zero
```

For all nine split starts:

```text
direct cancellation increment                 0.2409719853--0.2787208138
interpolation alpha                            0.6278684308--0.7262254980
split-start increment                                      0.175 exactly
maximum split-start total normalized action                0.0349526712
maximum predicted current utilization                      0.38235
```

The localization remained exactly three sequence rows each for 6, 10, and
18: p5 q2 plus-first, p9 q1 minus-first, and p9 q1 plus-first. Every
intermediate was an exact 14-field Card15 target, differed from both issue
target and stored center, had no predicted saturation or clipping, and
satisfied exact Decimal telescoping net zero.

The final route is:

```text
CAUSAL_SPLIT_RETURN_PREFLIGHT_PASS_REAL_SENTINEL_REQUIRED
```

## Classification and limits

There was no runtime/environment, package/import after final deployment,
raw/snapshot corruption, source-identity, restart, causality, statistics, or
route-reporting error in the final D1R3 execution.

D1R3 establishes only a finite causal split-start construction on the nine
recorded state-18 failure states. It does not contain a plant advance after
the intermediate action and therefore does not validate the state-19 finish,
full-horizon event sequence, formal control, transport model, MPC, robustness,
or long hold. The 45 D1R2 completed trajectories are unchanged source
evidence, not new D1R3 control successes.

The immutable 250/270 ms arrival deadlines and 350/370 ms formal endpoints
were unchanged. No D1R2 or D1R3 trajectory is eligible for expert data.

## Next action

D1R3 authorizes only a separately preregistered Stage4.2R3c3T13S24D1R4
nine-case authentic real-TSC safety sentinel. D1R4 must apply the split start
at task step 18, advance the authentic plant exactly once, recompute the
causal underlying action at state 19, and finish to the exact stored center
within the unchanged 0.24 margin and all original gates. Only a clean 9/9
full-horizon result can authorize a new full replacement identification
campaign. Transition MPC, expert data, BC, DAgger, and RL remain blocked.

## Commands and honest non-execution statement

The executed workflow used project-venv `compileall`/`unittest`, direct
uncompressed `scp -r`, server `sha256sum`, `bash -n`, the installed package
verifier, server-venv complete tests, two foreground D1R3 launch invocations,
and an independent server-venv raw audit. D1R3 did not run Ray, `gotsc`, TSC,
an environment reset/step, a plant advance, a snapshot capture, an optimizer,
or any learning procedure. The D1R4 finish has not yet been run or claimed.
