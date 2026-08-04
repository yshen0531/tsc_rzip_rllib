# Stage4.2R3c3T13S24D1R14R6 final forensic report

## Result

Stage4.2R3c3T13S24D1R14R6 completed all 48 prospectively frozen authentic
TSC trajectories. Primary postprocessing and a structurally separate
server-side raw/snapshot audit both support:

```text
DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED
```

This is a finite identification-safety and response-geometry PASS. It is not
a transition-model, MPC, formal-control, robustness, long-hold, expert-data,
BC, DAgger, or RL PASS. All R6 probe trajectories are forbidden from expert
datasets. Formal tracking passed 12/48 and is diagnostic only.

## Exact code and package identity

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
design and R5 record checkpoint
  307fdbb
implementation / authentication-hotfix checkpoint
  f0c864a
deployed package checkpoint
  1e62c2c
package revision
  r42r3c3t13s24d1r14r6_direction0_replacement_v2_r1a_auth_hotfix
package fingerprint digest
  0c6fb0228d5861e19b40f0ceca30bf9dbe32b726790c3f5009a9737c250d0931
PACKAGE_MANIFEST.json SHA-256
  228fd6028c2484debbcfbb24ed61e45c0590895c0c9aab9c65116ddd308a270f
SHA256SUMS SHA-256
  efc0b6ca5fa24c6d9f51d3483db19506d54712f6d01b66e6b353ed466a4eecb0
```

The first official offline invocation stopped before a stage directory,
raw file, controller, Ray actor, `gotsc`, TSC, or plant step. Its source
authentication incorrectly compared the older R1A matrix digest with the R5
candidate digest. Checkpoint `f0c864a` separated those two independently
authenticated facts and added a regression test. It changed no spec, action,
controller semantics, threshold, timing, source raw, or experiment identity.
The accepted campaign therefore used a fresh run directory under the final
package.

## Remote evidence

```text
installed source
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
staging source
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r14r6_1e62c2c_v2
accepted run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r6_runs/
  stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_20260804_1e62c2c_v2
offline log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
  stage4_2r3c3t13s24d1r14r6_offline_20260804_1e62c2c_v2.log
run log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r6_run_20260804_162602.log
postprocess log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/
  stage4_2r3c3t13s24d1r14r6_postprocess_20260804_1e62c2c_v2.log
```

The rejected authentication-only parent remains separately preserved as
`stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_20260804_1583ffd_v1`.
It contains no scientific result.

## Raw, snapshot, manifest, and log evidence

```text
expected / strict raw / safety / full horizon       48 / 48 / 48 / 48
raw bytes                                                1,509,679
raw inventory digest
  c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83
primary final SHA-256
  5c9669818249e8146b6f63d6e50e54f482cb27e64a809fb857bdf64ed617f016
independent final SHA-256
  a705aa669aaafd9b6708d6915655498f3f4f443ab37683eaa5ae5a8902ae9b1f
stage manifest SHA-256
  24ba49efa425aba83af2344df686b17c5ba37af90f21110275ac898514badf5c
stage state SHA-256
  ef3da5335aa7e8ae8328ae89c4552b961438f5daf92a021562a8f4e6b350de81
```

All eight restart snapshots were independently authenticated. Large raw,
full primary/independent JSON, specifications, snapshots, and postprocess
output remain server-side. Only compact evidence was copied directly to:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r6_20260804_1e62c2c/
```

The compact manifest SHA-256 is
`24ceeac1503db1c8db07fe18358b5ebb477a6d00291cee3ea1fee1e9cab9a7c9`.
An initial compact-manifest command used an outdated current-utilization
field name and failed before writing output. The corrected read-only command
used the actual result schema. This was a postprocessing field-adaptation
error with no effect on raw, official results, or experiment semantics.

## Independently recomputed execution gates

```text
exact source prefix / R4 issue-state reproduction       48 / 48 each
exact scheduled issue / causal stored-center cancel     48 / 48 each
finite trajectories / action safety                     48 / 48 each
forbidden trace / runtime / plant errors                   0 / 0 / 0
maximum issue incremental and total action       0.17481481481481495
maximum cancel increment                        0.17481481481481495
maximum issue / cancel predicted current          0.3799 / 0.37955
minimum desired/applied-current cosine           0.9982037391026385
maximum relative off-basis residual             0.05794563546539851
formal tracking diagnostic                               12 / 48
```

No solver, saturation, clipping, restart, causality, raw, snapshot, action,
or report discrepancy was found in the accepted run.

## Response geometry

R6 supplied only the 48 replacement direction-0 columns at issue steps 14,
18, and 22. The final bank combines those with the immutable R2 issue-step-10
columns and R4 directions 1--3:

```text
R2 issue step 10, directions 0--3                      64
R4 issue steps 14/18/22, directions 1--3             144
R6 issue steps 14/18/22, replacement direction 0      48
combined signed responses                              256
```

The frozen geometry gates passed:

```text
R6 direction-0 signal                                 48 / 48
combined signal                                      256 / 256
rank four                                              64 / 64
condition <= 20                                        64 / 64
R6 / combined issue antipodality                       24 / 24, 128 / 128
minimum R6 direction-0 peak                    0.006806000000025847
minimum combined direction peak                0.0051890000000165415
maximum combined condition                    12.121012187090825
```

The old R4 failure context
`p9_q2_a0p750_gap4_settle4 / minus_first / issue 18 / sign +` now has peak
`0.006806000000025847`; both signs pass. R6 therefore repairs the identified
local direction-0 signal deficit without changing the other three columns.
It does not, by itself, validate a predictive model or feedback policy.

## Error and scientific classification

```text
runtime/environment error in accepted run                no
packaging/import/deployment error in accepted run        no
pre-execution source-authentication code bug             yes; zero TSC/raw
raw/snapshot corruption                                  no
official summary/statistics error                        no
compact helper field-adaptation error                    yes; no output/raw change
controller/action safety failure                         no
authentic plant restart or causal execution failure      no
response-geometry design failure                         no in the frozen finite bank
real MPC / closed-loop control conclusion                none; not run
```

The real conclusion is limited to authentic restart, causal finite probe
execution, safe cancellation, and a signal-bearing conditioned finite
response bank across these eight clean-source contexts and four fixed issue
times. It does not cover unseen initial states/targets, continuous actuator
variation, plant/Jacobian error, measurement noise, disturbance recovery, or
independent long hold.

## Validation and commands actually run

Using only the repository-local Windows virtual environment and the existing
server virtual environment, the work performed JSON parsing, compileall,
focused tests, complete tests, import closure, manifest/checksum validation,
an empty-directory direct-copy deployment simulation, server `bash -n`,
installed package verification, server compile/import/focused tests, a
zero-TSC source/spec preflight, 48 fresh Ray/`gotsc`/TSC rollouts, primary
postprocessing, and separate server-side raw/snapshot forensics.

Focused tests passed 10/10 and the complete suite passed 1,118/1,118 with the
established Windows POSIX `resource` compatibility stub. The unshimmed
Windows discovery first collected 750 tests and produced 27 import errors
because the Unix `resource` module is unavailable; this is an environment
collection issue, not a repository test failure. The 589-file empty deploy,
staging deploy, and installed server package passed all hashes and declared
shell/import checks.

No global Python, local archive operation, server Git/network dependency,
model fit, MPC, expert-data collection, BC, DAgger, RL, robustness campaign,
or long-hold experiment ran.

## Frozen conclusion and next action

R6 and its 48 raw trajectories are immutable. Its PASS authorizes only a
separately preregistered, zero-new-TSC causal transition-model fit and
whole-history held validation over the authenticated finite response bank.
That model must predict deconfounded response increments rather than repeat
D1R11/D1R12's failed absolute future closed-loop trajectory target. It must
keep sign and issue time explicit, use only causally visible context at
decision time, exclude pair/history labels and all hidden/future/source
outcomes, and pass an independently implemented replay before any MPC design
or fresh controller execution is authorized.

