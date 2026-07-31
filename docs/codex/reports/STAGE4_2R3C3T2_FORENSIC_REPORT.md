# Stage4.2R3c3T2 forensic report

Date: 2026-07-30/31 (Asia/Shanghai)

## 1. Result

Stage4.2R3c3T2 passed its preregistered **identification** gates after
independent server-side recomputation from all 160 raw JSON.GZ results.

This is not a real MPC-control pass. Only 70/160 identification trajectories
satisfied the unchanged formal tracking contract; the preregistered design
made signed-probe formal tracking diagnostic-only. T2 authorizes an
authenticated six-basis optimistic-feasibility audit, not R3c4 execution,
expert-data generation, BC, DAgger, or residual RL.

## 2. Exact revisions and paths

Local branch:

```text
codex/stage4_2r3c3t2-held-transport
```

Real-run package checkpoint:

```text
cf5209ef5947044170e87f047d04e9fafd7ced8c
r42r3c3t2_post_contract_held_transport_identification_v2h1
post_contract_neutralized_held_transport_probe_v42r3c3t2_v2
```

Post-run report/resume hardening checkpoint:

```text
c1502e4d135fe6a4b7cea1ade56477933ca37ea9
r42r3c3t2_post_contract_held_transport_identification_v2h2
```

The H2 revision changes no task, controller, schedule, amplitude, physical
action, formal gate, or acceptance threshold. It fixes only formal-prefix
summary input and completed-run resume handling.

Valid server run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t2_runs/
stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_225902
```

Real-run log:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_230023.log
```

Independent server audit:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t2_audits/
stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_225902/
stage4_2r3c3t2_server_audit.json
```

Compact local evidence:

```text
docs/codex/audits/stage4_2r3c3t2_result_20260730_225902/
```

No raw trajectories, snapshots, or environment-variant trees were downloaded.
They remain on the server and were processed there.

## 3. Fingerprints

Authenticated H1 runtime values:

```text
run manifest SHA-256
  e1ebc16282fec2cd426a2f3f05f3a8b61be39546d3bf481acb7eea3f9370ed33

runtime package fingerprint digest
  5544b0fe4bc50e03d4dc83183f846c9315db353dcb17c7179371f8fe1b046011

raw inventory digest
  e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f

independent server-audit SHA-256
  e96f9538f5878ac745424d783e8f57c5ff41d61220b7d22ea66bfb1a08107d9c
```

The raw digest was identical before summary recovery, after summary recovery,
and in the independent postprocessor.

H2 local package values:

```text
3843382ca8eeb1276ee0143d904992b846f916891cfd340f981bac63ebc4a169  PACKAGE_MANIFEST.json
892911f20811c1afc09b0a9f62ba2f17736e4f25c772a9a47f22ebceff452c4e  SHA256SUMS
08c5845f882af8b7b5f12fe96fa8a1e792ceefa8446b0a5c80ea51b7adb7ce61  configs/stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_500ms.json
9d9cd4983d0c29ab49ba9a24b4f5483fda5320accbad31ae0cdb5cb37d07b6a4  tsc_rzip_rllib/diagnostics/stage4_2r3c3t2_post_contract_neutralized_held_transport_identification.py
```

## 4. Raw inventory and corruption checks

```text
expected identities                              160
raw JSON.GZ                                      160
unique experiment IDs                           160
completed / success                             160/160
trajectory/controller lengths                   51/50 for all 160
nonempty failure reasons                        0
stage/controller/spec identity exact            160/160
raw parse complete                              true
manifest compatibility                          true
runtime/audit package compatibility             true
reported summary exact on recomputation         true
raw and manifest integrity                      true
```

The audit contains a per-file raw inventory and a complete run inventory with
sizes and SHA-256 hashes. No raw or snapshot corruption was found.

## 5. Recomputed identification result

```text
execution gate                                  160/160
extended-baseline formal prefix exact             32/32
runtime/environment errors                             0
plant-restart-fidelity failures                        0
controller-causality failures                          0
forbidden controller inputs                            0
solver failures                                        0

central symmetry                                 64/64
matched hidden history                           32/32
transport rank/condition                         32/32
combined six-basis rank/condition                32/32
maximum selected transport condition          3.947918
maximum combined condition                   22.893801
maximum current utilization                     0.3904
allowed current utilization                       0.55

formal tracking diagnostic                       70/160
formal tracking failures                         90/160
formal tracking is an acceptance gate              false
certified identification pass                       true
```

The 500 ms observation horizon remains an identification tail, not a relaxed
arrival deadline or an independent long-hold validation.

## 6. Error classification

### 6.1 Runtime/configuration error

The preserved first v2 attempt is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t2_runs/
stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_20260730_222433
```

It inherited the 35/37-step episode limit. Eleven saved rows ended as
structured `environment truncated before T2 horizon` failures, with zero
valid 51-state trajectories. The exact process was stopped through the stage
stop script. This attempt was neither resumed nor counted as scientific
evidence. H1 restored the prospectively frozen 50-step environment and
payload horizon without changing controller semantics.

### 6.2 Statistics/reporting errors

After the valid run completed all 160 real TSC tasks, the runtime summary sent
the full 50-step result to the inherited frozen 35/37-step R8 evaluator. It
raised:

```text
ValueError: unexpected R8 queue-tail horizon 50; expected 35
```

The first zero-task recovery then exposed a second report/resume bug:
`run_offline_probe_audit` required an empty raw directory even for
`--resume`, so a completed authenticated run was rejected solely because its
160 raw files existed.

Both faults occurred after valid real TSC completion. Neither changed plant
state, controller actions, task identity, or raw data. The external wrapper:

```text
docs/codex/audit_tools/stage4_2r3c3t2_summary_resume_hotfix.py
SHA-256 0b391f976ca3717a94d5934bac8197d8107c80be52e84e3b7071e511efecd5bd
```

authenticated the exact H1 manifest, cached initial offline audit, all 160
raw identities and 51/50 lengths, and zero pending TSC tasks. It truncated a
deep copy only for the frozen formal evaluator and safely rebuilt the
summary. No `gotsc` process was launched. The independent postprocessor then
recomputed the result from raw and matched the reported summary exactly.

H2 makes those two fixes part of the normal source and tests.

### 6.3 Design defects

No preregistered T2 identification gate failed. Therefore T2 did not expose a
held-transport identification-design failure.

This does not establish that the six-basis bank can repair all failed formal
contexts. That is the next, separate optimistic-feasibility gate.

### 6.4 Real control and plant-restart conclusions

Plant restart fidelity and causal execution were clean for all 160
identification tasks. This confirms that the probes were executed from the
authenticated restart contexts.

It does not establish successful restarted MPC regulation. The signed probe
trajectories intentionally perturb the controller and only 70/160 meet the
formal tracking diagnostic. No R3c4 controller has been implemented or run.

## 7. Validation actually run

Before the real H1 campaign:

```text
changed-Python compile
all ordinary JSON parse
focused and complete repository tests (548/548 at H1)
import closure
170 checksum rows and package manifest
172-file empty-directory direct-copy simulation
staging package, shell syntax, import and focused tests
canonical server package, shell syntax, import/compile and full tests
160-spec offline controller audit with raw=0 and plant advance=0
```

After the result and H2 hardening:

```text
Python compileall                              pass
ordinary JSON parse                         1460 files, pass
checksum verification                         170/170
package/import closure                        172 files
focused T2 tests                               11/11
complete repository tests                     549/549
empty-directory direct-copy validation        172 files, pass
external wrapper compile/prefix tests          pass
server wrapper compile and SHA checks          pass
raw-only authentication                       160/160
independent server postprocessor               pass
```

Transport used direct `ssh`/`scp` file transfer only. No local compression or
extraction was performed.

Not run:

- H2 was not deployed over the H1 canonical source before the H1 audit,
  because doing so would invalidate runtime package-fingerprint comparison.
- No real TSC task was rerun for either report bug.
- No six-basis feasibility audit, R3c4 controller, noise, continuous
  parameter, disturbance, or long-hold experiment is claimed here.

## 8. Frozen result and next action

Freeze T2 as:

```text
Stage4.2R3c3T2 held-transport identification: certified pass
raw inventory: 160 authenticated server-only JSON.GZ
development/identification data only
not expert data
not a real MPC-control pass
```

Next, build an authenticated combined response bank on the server from the
exact R3c3 four-basis bank plus the T2 two held-transport responses. Run the
unchanged optimistic formal-feasibility audit for all 32 contexts with
coefficients constrained to `[-1, 1]`, unchanged timing, and zero baseline
regressions. Do not implement or launch R3c4 unless it is 32/32.

