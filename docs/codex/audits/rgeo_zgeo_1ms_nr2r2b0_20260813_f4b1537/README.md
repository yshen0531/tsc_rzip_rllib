# NR2R2B0 source q0-baseline evidence

Final frozen route:

```text
ONE_MS_NR2R2B0_BASELINE_REPEATABILITY_FAIL_STOP
```

Source/package revision: `f4b1537`.

Remote identities:

```text
project  /home/yangshen0711/tsc_all/tsc_rzip_rllib
run      artifacts/nr2r2b0_run_f4b1537_v1
log      logs/nr2r2b0_run_f4b1537_v1.log
PID      3393675 (exited after final result)
```

The zero-TSC offline gate passed with a maximum source-to-q0 single-turn
change of `1e-5 A`, q0-to-q0 change `0 A`, and zero plant advances.  The real
campaign then completed the exact frozen maximum: 6 independent resets, 32
q0 issues each, 192 authentic advances and 198 raw state directories.

Primary and independent raw audits agree on the frozen FAIL route.  The
failure is specifically the preregistered cross-reset exact artifact-hash
gate: `sprsina` differs across all six resets at every successor state.
`inputa`, `geqdsk`, `coil_currents.csv` and `wire_currents.csv` are
byte-identical at every matching state.  R/Z/Ip, 14 actual coil currents, 48
wire-current components and Card15 fields also have exactly zero cross-reset
difference.

This does not permit post-result relaxation of the B0 gate.  It distinguishes
a frozen artifact/restart-identity repeatability failure from physical-output
repeatability evidence.

Separately, q0 decisively failed the prospectively frozen short-hold
criterion:

```text
maximum |R-R0|                         17.6012950 mm
maximum |Z-Z0|                         23.4419245 mm
maximum |Ip-Ip0|                        335.7230 A
terminal states                         24 through 32
terminal maximum |Delta R|/step          0.617677 mm
terminal maximum |Delta Z|/step          0.805788 mm
terminal net |Delta R|                    3.943637 mm
terminal net |Delta Z|                    5.822385 mm
```

Thus q0 is neither a qualified hold nor a recovery continuation.  No model,
controller, optimizer, Oracle branch, expert data or adaptive update ran.

The complete server raw remains in place.  The compact inventory authenticated
all 990 required files across 198 states, totaling 11,660,798,952 bytes, with
ordered inventory SHA-256:

```text
c8a8de054f3cd5af9e731d46f56beb4601ee13d6176ff3029e608479076f3789
```

Downloaded compact evidence hashes:

```text
PRIMARY_RESULT.json
ed4aff78c7d5b231841d114ced259774d43cea44bab35b2456ca16ff32588595

INDEPENDENT_AUDIT.json
c2428464e97fafca794549ecbabab4e48997343764a834fc505adcf9548ec086

COMPACT_EVIDENCE.json
3f95504d2b329f9b3e5dd937b221749351678ddade77ca10ee4add8474548bb6

OFFLINE_PREFLIGHT.json
b6cd36efff19149d384f0a24c98c77609b289abb4b722f95e32d60377952bef1

RUN.log
ed4aff78c7d5b231841d114ced259774d43cea44bab35b2456ca16ff32588595
```

The log equals the primary result because the runner emitted its final JSON
after all raw and result files were written.

The next stage is not authorized.  It requires an explicit architecture
decision for active source hold/recovery and, independently, a prospective
audit of which `sprsina` fields encode benign reset/run identity versus
load-bearing restart state.  No new atlas/probe/model TSC may run first.
