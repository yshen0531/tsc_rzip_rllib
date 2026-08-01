# Stage4.2R3c3T13S1 implementation validation

## Status

This record is post-implementation and pre-server-execution. It does not
contain a T13S1 scientific result.

```text
branch       codex/stage4_2r3c3t13s1-transition-sentinel
commit       898b559ba5d2f716f4e2e255f9a570b87af3bbb2
real TSC     not run
raw count    0
scientific verdict NOT_RUN
```

The user authorized continued execution through the prerequisites for RL on
2026-08-01. That authority does not weaken any T13S1 gate and does not
authorize BC, DAgger, or residual RL before the complete roadmap gates.

## Implemented identity

```text
stage                 Stage4.2R3c3T13S1
campaign              restart_issue_time_single_step_transition_sentinel_v1
controller wrapper    single_step_transition_probe_v42r3c3t13s1_v1
underlying controller authenticated_visible_manifold_phase_mpc_v42r3c1
package               r42r3c3t13s1_minimal_transition_sentinel_v1
expected rollouts     52
```

The implementation has a new config, source, package, run, raw, audit, state,
and log identity. It does not resume or overwrite T11 raw.

## Scientific implementation guards

The controller wrapper removes the complete probe schedule, probe identity,
campaign identity, pair/history identity, source raw identity, and snapshot
identity before constructing the underlying R3c1 controller. The wrapper
retains the frozen schedule privately and applies only the current issue-step
increment after the causal R3c1 solver has produced its baseline correction.

Every authentic rollout is required to record and pass:

- a fresh controller actor and fresh TSC process;
- exact full snapshot restart and a 50-row causal trace;
- the exact two-issue adjacent inverse schedule and exact zero requested and
  applied net;
- no future measurement, hidden wire current, history label, source action,
  source result, or future probe schedule in the underlying controller;
- no scheduler mismatch, modal normalization, current-limit rescaling, or
  solver failure;
- the `1e-6 A` command mode-subspace gate and `0.55` current-utilization gate;
- four exact R3c1 formal-prefix reproductions, including the frozen two PASS
  and two FAIL margins;
- all preregistered signal, symmetry, pre-effect, matched-history, rank, and
  normalized-condition gates recomputed from raw trajectories.

Probe trajectories remain forbidden from expert datasets.

## Source hashes

```text
79cebd0ff36d43de6f4a4fce42cbab925ddc201d3cde00ab79e0aad22fba78ad  configs/stage4_2r3c3t13s1_minimal_transition_sentinel_500ms.json
685769f931cc6cb695ea534aa285b28c3932384a34df7c32ed5589d7543ebd38  tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s1_minimal_transition_sentinel.py
0823d3cb3f9774e15704498e5dea0d2b538fd8627b4549fb586e83c5a01b2f83  scripts/stage4_2r3c3t13s1_server_postprocess.py
59f352bd55766bafb289e777ba165952c7e2ddf0c8e9c841316b03cc2da5457e  PACKAGE_MANIFEST.json
3ceb2b90932461571cb236fd6d776dab7f3ee4c0c0d5acd96e340de46f6ca8bc  SHA256SUMS
```

The package declares 267 unique, sorted source files and contains the full
import closure plus the exact T13S1 launch, stop, verify, and server-audit
entry points.

## Local validation completed

```text
focused T13S1 unit tests                         7 / 7 PASS
complete repository unit tests                639 / 639 PASS
Python compileall                                  PASS
all configs/*.json parse                           PASS
manifest inventory 267/267 unique and sorted       PASS
SHA256SUMS 267/267                                  PASS
empty-directory direct-copy file count              268
empty-directory checksum verification              PASS
empty-directory isolated T13S1 import/self-test     PASS
empty-directory compileall                          PASS
```

The first system-Python full-test invocation reported only Windows import
environment errors: 27 tests could not import Unix `resource`; after loading
the repository's existing Windows compatibility fixture, one remaining test
could not import `gymnasium`. The formal full run used the repository-local
virtual environment, loaded the compatibility fixture, and passed 639/639.
These were local test-harness/environment errors, not code, runtime, TSC,
restart, reporting, or control results.

The local `bash` command maps to WSL but no WSL distribution is installed,
so local Bash syntax execution was not available. Exact `bash -n` for all
declared shell scripts is mandatory on the Linux server before any offline
audit or real TSC launch.

## Resume and evidence behavior

Automatic resume accepts only an exact manifest, control-spec digest, and
full deployed package fingerprint. A complete valid raw member is read and
preserved; only missing or invalid members can be scheduled. Any later
semantics-preserving runtime/report hotfix must be separately audited before
the compatibility contract can be changed.

The independent server postprocessor reads all 52 raw JSON.GZ files on the
server, verifies filenames/specs/snapshots/package/manifest, recomputes the
complete summary without writing into raw, and emits compact inventories and
route evidence. Large raw is not scheduled for local download.

## Classification and next action

```text
runtime/environment result        NOT_RUN
deployment/package server result  NOT_RUN
raw/snapshot integrity result      NOT_RUN
statistics/reporting comparison   NOT_RUN
scientific sentinel result         NOT_RUN
real control conclusion            none
```

Next, deploy the exact direct-copy package, run server path/Bash/package/
import/compile/full-test checks, run the zero-plant-step 52-spec offline
audit, and start the authentic campaign only if every pre-run gate passes.
