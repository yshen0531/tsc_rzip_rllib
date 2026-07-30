# CURRENT_TASK.md — Stage4.2R1 final-result forensics and continuation

## 1. Task statement

The Stage4.2R1 / R1a server run has completed. The uncompressed final log and full uncompressed run results have already been downloaded into this repository.

Your first job is to analyze the real local evidence. Do not immediately rerun the server. Do not assume the final verdict is correct. Do not assume plant restart passed or failed.

Use the exact local files that exist now.

## 2. Expected current code identity

Expected conceptual stage:

```text
Stage4.2R1 authentic TSC plant-state restart action replay
```

Expected latest hotfix behavior:

```text
R1a capture-failure finite-summary handling
```

Likely package revision:

```text
r42r1a_capture_failure_finite_summary_v2
```

Verify the actual package/manifest/state revision. Do not trust this expected value if the local files say otherwise.

## 3. Source baseline

Formal source expert:

```text
Stage4.1R17
```

Frozen formal timing:

```text
slew=1.0/1.1: arrive by 250 ms, hold through 350 ms
slew=0.9:     arrive by 270 ms, hold through 370 ms
```

Frozen finite source composition:

```text
14 unchanged source paths
4 R17 one-sided braking paths
delay=1 braking magnitude 6×
delay=2 braking magnitude 7×
18/18 finite static-grid formal pass
```

Do not use R10/R11 late-arrival horizons as the formal source contract.

## 4. R1 experiment design to verify

Expected capture matrix:

```text
2 targets × 3 delays × 3 slew scales = 18 capture tasks
```

Expected restart matrix if capture passes:

```text
18 fresh TSC restart suffix tasks
```

Expected checkpoint:

```text
elapsed checkpoint = 200 ms
source start folder = 1100 ms
snapshot folder time = 1300 ms
```

Expected snapshot required files may include:

```text
inputa
sprsina
geqdsk
outputa
coil_currents.csv
wire_currents.csv
```

Verify against actual code/config, not this summary.

R1 isolates plant state:

```text
plant snapshot + action suffix replay
```

R1 intentionally does not restore:

```text
observer
integrator
pending command queue
controller checkpoint
```

## 5. Mandatory phase A — repository and evidence inventory

Before edits:

```powershell
git status --short
git branch --show-current
git log -1 --oneline
```

Locate and record:

- current Stage4.2R1 code files;
- `PACKAGE_MANIFEST.json`;
- `SHA256SUMS`;
- final R1/R1a log;
- initial failure log if retained;
- full R1 run directory;
- R17 source run directory;
- all state, manifest, resolved config, results, summary, CSV, verdict files;
- all raw JSON/JSON.GZ;
- all snapshot directories/files.

Create:

```text
docs/codex/reports/STAGE4_2R1_FORENSIC_REPORT.md
artifacts/codex_audits/stage4_2r1_inventory.json
artifacts/codex_audits/stage4_2r1_capture_audit.csv
artifacts/codex_audits/stage4_2r1_restart_audit.csv
artifacts/codex_audits/stage4_2r1_snapshot_audit.csv
```

Do not alter scientific code until this phase is complete.

## 6. Mandatory phase B — capture audit

Programmatically inspect all expected capture specs and raw files.

For each expected capture case, report:

- target;
- delay;
- slew;
- experiment ID;
- raw file path;
- parse status;
- `success`;
- failure reason;
- exception stage;
- traceback presence;
- trajectory state/action count;
- source trajectory state/action count;
- shape comparability;
- maximum visible difference, or structured mismatch reason;
- action equality;
- formal metric result;
- snapshot path;
- snapshot manifest presence;
- snapshot required-file completeness;
- each file size and SHA-256;
- snapshot manifest digest validity;
- coil-current vector shape and equality;
- full wire-current vector shape and equality;
- snapshot time/index alignment.

Classify every failed/incomplete capture into one exact category:

```text
environment reset
action replay
snapshot request not triggered
snapshot export exception
required snapshot file missing
snapshot file hash mismatch
coil vector mismatch
wire vector missing/shape mismatch/value mismatch
capture trajectory truncated
source/capture state-index mismatch
formal contract failure
other, with evidence
```

Do not let a summary-level `null`, `inf`, or generic failure reason replace raw diagnosis.

## 7. Mandatory phase C — restart audit

Determine whether restart suffix tasks actually ran.

If they ran, inspect each case:

- fresh TSC environment/process identity;
- snapshot source;
- restart raw parse/success;
- restart initial state versus continuous source checkpoint;
- R/Z/Ip difference;
- 14-coil vector difference;
- full wire-current vector difference;
- vessel aggregate difference;
- action-suffix index alignment;
- source suffix and restart suffix lengths;
- duplicate or missing checkpoint state;
- per-step suffix differences;
- formal metric after prefix/suffix recombination.

Independently verify prefix/suffix reconstruction:

```text
source prefix before checkpoint
+
restart suffix beginning at the correct checkpoint state
```

There must be no duplicate state and no missing control interval.

If restart tasks did not run, say `not_run`, identify the exact prerequisite gate that stopped them, and do not label restart fidelity as failed.

## 8. Mandatory phase D — separate scientific conclusions

Report separately:

```text
capture_instrumentation_fidelity
snapshot_integrity
plant_restart_initial_state_fidelity
plant_restart_suffix_fidelity
formal_contract_preservation
```

A possible valid result is:

```text
snapshot/restart not bit-exact but formal contract preserved
```

That is not the same as exact restart fidelity.

Another possible result is:

```text
capture failed before restart
```

That is not evidence about restart behavior.

## 9. Classification required in the report

Use these headings:

1. Runtime/environment errors.
2. Packaging/deployment/import errors.
3. Raw/snapshot integrity errors.
4. Statistics/reporting bugs.
5. Experimental-design flaws.
6. Real plant-restart conclusions.
7. What can be frozen.
8. What remains unvalidated.
9. Next step tied to the final task.

## 10. Decision and implementation rule

After the evidence report:

### Case A — summary/report-only bug

If physical capture/restart raw is valid and only the summary/reporting code is wrong:

- patch locally;
- preserve successful raw;
- add real-interface regression tests;
- keep experiment IDs/controller semantics unchanged;
- prove `resume=1` compatibility;
- deploy directly;
- resume the same remote run;
- download and re-audit final results.

### Case B — snapshot/capture implementation bug

If snapshot export or capture indexing is wrong:

- fix the minimum proven cause;
- keep the R17 expert and formal timing unchanged;
- decide whether old successful captures are scientifically reusable;
- rerun only failed/incompatible captures;
- do not run restart until capture is authenticated.

### Case C — authentic plant restart failure

If capture and snapshot are valid but fresh restart diverges:

- do not modify the controller;
- isolate the smallest reproducible plant-state restart mismatch;
- compare `sprsina`, coil vector, full wire vector, and first fresh step;
- create a focused restart-diagnostic stage rather than adding controller complexity.

### Case D — authentic plant restart success

If plant restart is authenticated and the formal contract is preserved:

- freeze R1;
- implement Stage4.2R2 for complete controller-state checkpoint/replay;
- include observer history, integrator, previous correction, pending delay queue, and trusted calibration token;
- first require exact replay of the same source;
- only afterward test matched-visible/different-hidden-history cases.

If there is no genuine route choice, implement the next complete standalone code tree and run the full local → server → download → analysis loop.

## 11. Server execution authorization

Codex may use:

```text
ssh tsc-airgap
scp
sftp
```

It may operate remotely only inside:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib
```

It may source:

```text
/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/activate
```

It must not modify the virtualenv or simulation installation.

It may use `/home/yangshen0711/tsc_software` only as a clearly identified staging directory, never as the project directory.

No local or server archive operations.

## 12. Required final response for this task

Return:

1. concise executive conclusion;
2. complete evidence-based classification;
3. exact files changed;
4. local tests run;
5. server validation/run commands actually executed;
6. exact remote run/log path;
7. expected/actual task counts;
8. links/paths to audit artifacts;
9. whether true `gotsc` was executed;
10. next-stage rationale;
11. current relation to the final task.

Do not end with vague suggestions. If no user decision is needed, execute the evidence-backed next step.
