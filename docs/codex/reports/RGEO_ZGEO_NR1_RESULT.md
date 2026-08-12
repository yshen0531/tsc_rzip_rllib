# R_geo/Z_geo NR1 result

Final route: `FIXED_1100MS_PREFIX_REPLAY_QUALIFIED`

NR1 completed its prospectively frozen safety and fixed-prefix replay
qualification on 2026-08-13 Asia/Shanghai from implementation checkpoint
`c56a72a`.

## Result

The server offline gate passed before any plant advance. It authenticated the
fixed 1100 ms source signal as:

```text
R_geo = 0.708635102 m
Z_geo = 0.035241343 m
R_mid = 0.7919 m
Ip    = 31286.4059 A
side  = HFS
```

The maximum frozen quantized target increment was `0.2 A`, below the unchanged
`3 A/step` configured slew. The four authorized TSC rollouts then completed:

```text
rollouts                         4/4
plant advances                 32/32
primary raw state records      36/36
independent Card15 checks      32/32
independent safety checks      36/36
TSC campaign wall time       462.572410909 s
```

Both the center-hold primary/replay and the small nonzero reversible-pulse
primary/replay comparisons passed. Primary parsed comparisons and an
independent raw-directory audit both found maximum replay difference exactly
zero for boundary-box `R_geo/Z_geo/R_mid`, `Ip`, all 14 coil-current
readbacks, and the full parsed wire-current vector.

The records were prospectively marked `intended_use=interface_validation`.
They are forbidden from expert or model-fitting data.

## Integrity and execution notes

The exact server-installed new-source SHA-256 values were:

```text
a9d1acc6985a881155c07565cdc471ca3e23dbe3ee05b8ee969c941382cdcb1f  scripts/rgeo_zgeo_nr1_qualification.py
b71ed08d84d5a290dfc5410ea2f624d5b6fb62a5c6d9beecdd8500ec20bd1a77  scripts/rgeo_zgeo_nr1_independent.py
77d72e15d2a4141988244294c1aa31e6e92336e873abe29af23249556c2a9664  tests/test_rgeo_zgeo_nr1.py
012fda2be48c1916d499be4ea0d5e5d257c013db458a538b53341088dcf7bd46  tsc_rzip_rllib/control/__init__.py
032bd16cc7d3b7b55f907f1f23d7a0f0140058e4b53ec3f697608476ab776403  tsc_rzip_rllib/control/rgeo_zgeo_contract.py
d54ff5bb992f2144bf0db60f36ec905069608cddc722520bfc4595c428796eee  tsc_rzip_rllib/control/rgeo_zgeo_nr1.py
```

Primary qualification report SHA-256:
`a5d4b68fc122767be59e338b77e6a857be8fb2ca199ca2cb39b551b70b3d30a7`.
Independent audit SHA-256:
`63ab61165d5d45cfb7c579a7452ae3b5c063dfd243d05deded1cd774a50a3f65`.

Three initial staging attempts failed before offline execution because the
test invocation first treated an absolute path as a module and then imported
the installed package ahead of the partial staging package. The corrected
complete staging package passed 5/5 focused tests, public import, compile, and
offline preflight. These were deployment-validation command errors, not TSC,
interface, or model results; they produced zero plant advances.

The PowerShell-to-stdin launch transported a trailing CR into the requested
output-directory argument. The unique immutable run directory therefore has
one literal trailing carriage-return byte in its name. The primary execution
used that directory consistently. The first independent-audit shell wrapper
accidentally appended a second CR and failed before writing; a fixed LF script
then selected the unique original directory and completed the audit. No raw
was renamed, overwritten, deleted, resumed, or rerun. This is a launch/path
reporting defect, not an action, raw, replay, safety, or TSC defect.

## Claim boundary and next stage

NR1 demonstrates deterministic replay only by restarting at the fixed source
and executing either of two exact eight-action prefixes. It does not qualify
branching from arbitrary causal histories, snapshot restoration, search
quality, prediction beyond those prefixes, control authority, trajectory
tracking, deployment, a teacher, MPC, or RL.

NR2 may now compare explicit queue plus low-order memory and recurrent/
convolutional residual model classes under a new prospective data split. NR1
raw cannot be used for fitting. No NR2 TSC may run until its finite work
domain, excitation/holdout identities, safety stops, model metrics, and stop
routes are frozen.
