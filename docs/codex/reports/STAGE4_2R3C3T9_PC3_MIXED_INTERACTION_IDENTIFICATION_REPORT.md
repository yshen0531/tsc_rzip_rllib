# Stage4.2R3c3T9 PC3 and mixed-interaction identification report

## Result

Stage4.2R3c3T9 completed all 224 authentic restart TSC identification tasks.
The preregistered identification gates passed, but the separate linear-route
gate failed in every context:

```text
raw / strict parse / unique identity                      224/224
execution / exact restart / causal trace                  224/224
extended-baseline prefix exact                              32/32
standalone PC3 central symmetry                             32/32
PC3 matched-history response                                16/16
mixed-factorial response available                          32/32
mixed-contrast matched-history response                     16/16
selected nine-basis rank / condition <= 25                  32/32
maximum selected condition                               23.155208
maximum current utilization                                0.3904
runtime / restart / causal / solver / forbidden errors           0

mixed velocity ratio <= 0.10                                 2/32
PC3 background modulation <= 0.10                            0/32
linear route                                                 0/32
```

The scientific conclusion is therefore:

```text
identification experiment                              PASS
fixed linear/separable nine-basis route                FAIL
next model class                       interaction-aware required
R3c4 implementation authorization                         no
```

The measured interaction is reproducible enough to pass the preregistered
matched-history gate and too large to discard. The next stage must retain the
stress-by-PC3 Walsh mixed contrast and the observed dependence of the PC3
main effect on the stress background.

## Exact revisions and paths

```text
local branch
  codex/stage4_2r3c3t9-mixed-interaction-preflight

real-identification implementation commit
  15e7033

Ray-worker/reporting hotfix commit
  b489acc

pre-final forensic checkpoint
  9527ad8

package revision
  r42r3c3t9_pc3_mixed_interaction_identification_v1h1

controller revision
  pc3_mixed_interaction_probe_v42r3c3t9_v1

runtime package fingerprint
  3c3dbdb4b736f19c95e4d510c182b1c4986957fe98d7294a5decccd723d4802f
```

Remote evidence:

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

real run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t9_runs/
  stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005

real log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090158.log

server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t9_audits/
  stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005/
  stage4_2r3c3t9_server_audit.json

postprocess log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t9_server_postprocess_20260731_2012.log
```

## Runtime and reporting incident separation

The first package-v1 run is preserved separately at:

```text
stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_083514_15e7033
```

All 224 of its raw files are structured startup failures with empty
trajectories and empty controller traces. Fresh Ray workers instantiated the
inherited T6 worker before receiving the driver-process T9 contract. The
original summarizer then attempted to reshape an empty requested-action
array. This is a Ray-worker runtime adapter defect plus a reporting
robustness defect. It produced no TSC trajectory and no plant, restart, or
control conclusion.

Commit `b489acc` installs the same frozen T9 contract inside every worker and
turns empty traces into finite structured failures. It does not change the
controller action policy, experiment IDs, task matrix, probe schedules,
physical action semantics, or acceptance gates. Because the first run had no
TSC trajectories, v1h1 correctly used a new run rather than resuming it.

The v1h1 run has:

```text
runtime/environment errors                                  0
package/import/deployment errors                             0
raw/snapshot corruption                                      0
statistics/reporting errors                                  0
```

The main log contains 222 lines and no Traceback, Exception, Ray actor
failure, fatal marker, or error marker. Its SHA-256 is:

```text
614ab4eb9587f8f932a86015ff5f08e728bc593d1e8db425ea63e95b97ae4c34
```

A later SSH outage occurred after 128 results had been observed. The server
run continued without intervention and completed 224/224. No rerun, resume,
kill, or cleanup was issued during the outage. A local multi-source `scp`
later hit its tool timeout after copying 14/18 compact files; only the four
missing files were copied afterward, and all 18 hashes match the server.
Neither incident changes the experiment result.

## Raw, snapshot, and package integrity

The server-side postprocessor read all large evidence in place. A separate
strict-JSON pass then reopened all 224 gzip files and found:

```text
strictly decoded raw                                      224/224
success / completed                                       224/224
unique experiment IDs                                     224/224
Stage4.2R3c3T9 identity                                   224/224
51-state trajectory / 50-row controller trace             224/224
48 wire currents in every recorded state              11424/11424
abnormal trajectory rows                                         0
solver-failure rows                                              0
forbidden controller-input rows                                  0
```

The independent audit authenticated exact filenames, specs, resolved config,
manifest, preflight, source paths, T7 bank, package fingerprint, and 8/8
unique restart snapshots. Reported summary and raw recomputation are exactly
equal.

Load-bearing hashes:

```text
candidate preflight
  9a37168cce679df7deeb242bceb996c11f41bf9e589459e27386ece45f41e560

manifest
  5211ed99ebb659d59ffcf87f23c95ea409df0e25158bab5158fe21ba07db6dde

raw inventory digest
  e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2

run inventory digest
  9abdb31f7dd37503c57832c07d951e71a677a31d99f430dfe2a8908fc6e73660

server audit
  05547765ca5e1282e58b0d33e454b0a2a4dd87ee16e85146261650510ebd05f8

snapshot audit
  6c156b354307255893c30a5e08510880d7ab15a6484d20c9b09209ab8d344495
```

Only compact audit/result/log files were downloaded. Raw JSON.GZ,
trajectories, snapshots, and wire-current trees remain on the server.

## Identification gates

The maximum observed errors remain within their frozen thresholds:

```text
metric                                      maximum       threshold
standalone even velocity RMSE              0.001573       0.004 m/s
standalone even position RMSE              0.000137       0.0005 m
standalone even Ip RMSE                     2.802477      20 A

PC3 history velocity RMSE                  0.001885       0.006 m/s
PC3 history position RMSE                  0.000292       0.001 m
PC3 history Ip RMSE                         3.426778      40 A

mixed history velocity RMSE                0.000970       0.006 m/s
mixed history position RMSE                0.000087       0.001 m
mixed history Ip RMSE                       1.605151      40 A

selected nine-basis condition              23.155208      25
current utilization                         0.390400       0.55
```

All 32 selected response matrices have rank nine. Their condition numbers
range from `7.6641605` to `23.1552081`.

These results establish a clean finite development-set identification. They
do not establish a reliable restart MPC or independent hidden-history
closed-loop robustness.

## Why the linear route fails

The linear route required both ratios to be at most `0.10` in every context.
The measured ranges are:

```text
metric                                      pass count       range
mixed velocity / main-effect norm               2/32        0.0716--0.3003
PC3 background modulation                       0/32        0.1810--1.0799
both conditions                                  0/32
```

The failure is not a rank or current-limit artifact. It remains after exact
restart, exact schedule execution, central symmetry, matched-history
agreement, and acceptable nine-column conditioning. In particular, even the
smallest PC3-background modulation is 81% above the allowed ratio, and the
largest is more than ten times the threshold.

Therefore a bank that treats PC3 as one fixed response column independent of
the simultaneous stress schedule is scientifically invalid for these
combined actions. The measured Walsh mixed term and background-dependent PC3
main effect must remain explicit. This is a real model-class/route failure,
not a defect in the T9 identification design.

## Formal control interpretation

Formal tracking passed `104/224`, but the config preregistered it as a
diagnostic-only field for signed identification probes. The 500 ms horizon
does not move the 250/270 ms arrival deadlines or the 350/370 ms formal hold
endpoints and is not an independent long-hold test.

T9 did not execute a new MPC candidate. Its probe trajectories are forbidden
from expert datasets. Accordingly:

```text
real plant restart fidelity                         passed for 224 probes
real closed-loop R3c4 result                        not run
reliable MPC expert                                 not validated
formal controller improvement                       not claimed
```

## Validation and commands executed

Before the real run:

```text
Python compile / all JSON parse                              PASS
focused T9 tests                                           13/13
complete local tests                                      596/596
package and checksum inventory                            210/210
empty-directory deployment simulation                    596/596
server shell/package/import validation                       PASS
complete server tests                                     596/596
offline frozen-spec audit                                 224/224
offline raw / plant advance                                   0/0
```

The real server launcher used the existing virtualenv, Ray capacity 128,
the exact v1h1 run directory, and `--resume` only to reuse the already passed
offline preparation in that same new run. It did not reuse v1 failed raw.

After completion, the commands and outcomes were:

```text
PID/raw/state/log read-only inspection       PID exited, raw 224, outputs present
run_stage4_2r3c3t9_server_postprocess.sh     exit 0, raw/snapshot audit PASS
server strict gzip JSON scan                 224/224, no corruption
server per-context metric expansion          identification PASS, linear 0/32
direct scp of compact evidence               18/18 hashes exact after partial retry
local strict compact JSON parse              16/16 JSON files PASS
local summary/audit invariant checks         PASS
```

No new TSC controller stage, R3c4 run, BC, DAgger, residual RL, independent
unseen history, unseen target, continuous actuator/plant variation, noise,
disturbance recovery, or independent long hold was run.

## Next action

The next stage is a new, prospectively frozen interaction-aware offline model
audit. It must:

1. authenticate the exact T9 raw/audit/config/source chain;
2. represent the four factorial outcomes with explicit stress, PC3, and
   stress-by-PC3 Walsh terms rather than discarding the mixed term;
3. represent or bound the measured PC3 background modulation;
4. keep coefficients, current limits, causal information, and formal timing
   unchanged;
5. require an unchanged-contract optimistic feasibility result before any
   R3c4 implementation;
6. execute no real TSC unless a later prospective design proves that the
   measured factorial data are insufficient.

R3c4, BC, DAgger, and bounded residual RL remain unauthorized.
