# R_geo/Z_geo 1 ms NR0 interface-contract result

Date: 2026-08-13 Asia/Shanghai

## Scope and identity

This is repository-only NR0 under contract `rgeo-zgeo-1ms-nr0-v1`.
It defines data and validation interfaces only. It ran no server command,
TSC, plant step, snapshot, Oracle branch, fitting/training, controller, MPC,
RL, or data generation and did not read server raw as a fixture.

The branch was created from tracked-clean `ad4302b`; historical preservation
checkpoint `cbdf874` was verified to exist. The previous 10 ms / 3 A route
is immutable and is not rescaled or reused as new-route evidence.

## Exact contract

```text
takeover time                                  1100 ms
control period                                    1 ms
coil count/order                                14 / TSC
current semantic                         single-turn A
hard per-step constraint             |I_i[k+1]-I_i[k]| <= 0.3 A
equivalent maximum slew                         0.3 A/ms = 300 A/s
+0.3 A and -0.3 A endpoints                    allowed
larger magnitude                         fail closed
Card15 unit                                  kA-turn
implicit clipping or hidden reserve              none
```

`R_geo` and `Z_geo` retain the accepted fail-closed definition from one
paired plasma boundary at one time step:

```text
R_geo = (min(boundary_R) + max(boundary_R)) / 2
Z_geo = (min(boundary_Z) + max(boundary_Z)) / 2
R_mid = (R_inner_limiter_midplane + R_outer_limiter_midplane) / 2
side  = HFS if R_geo < R_mid else LFS
```

Missing, unpaired, unequal-length, non-finite or degenerate boundary data,
abnormal state, invalid limiter geometry, and state/gfile Ip disagreement
fail closed. Magnetic-axis, pressure-centroid, alias and split-source
fallbacks are not accepted. Ip remains observed and safety-relevant but is
not a user command.

The new wrapper requires exact one-millisecond timestamps, continuous belief
identity across every `R_mid` crossing, explicit issued/serialized/quantized/
queued/applied/readback stages, a same-frame causal current baseline for each
issued target, `<=0.3 A` issued-target delta, and `<=0.3 A` consecutive
observed-current delta. It rejects a 10 ms history rather than converting it.

## Changed files

```text
tsc_rzip_rllib/control/rgeo_zgeo_1ms_contract.py
tsc_rzip_rllib/control/__init__.py
tests/test_rgeo_zgeo_1ms_contract.py
docs/codex/CURRENT_TASK.md
docs/codex/CURRENT_STATUS.md
docs/codex/TOKAMAK_RL_PROJECT_CONTEXT.md
docs/codex/RGEO_ZGEO_NEW_CONTROL_ARCHITECTURE.md
docs/codex/reports/RGEO_ZGEO_1MS_NR0_RESULT.md
```

## Qualification boundary

NR0 does not prove that the installed server/TSC accepts or faithfully
advances a 1 ms restart step, that every Card15 center has a useful nonzero
representable `<=0.3 A` move, that queue/effect latency in milliseconds is
qualified at the new period, or that a safe finite work domain/controller
exists. These are prospective restarted-NR1 and later questions. NR0 PASS
does not authorize them.

Final test counts, commit and remote branch are appended only after focused
and complete local validation pass.

## Local validation

All validation used the repository project virtual environment.

```text
compileall new module and test                         PASS
new NR0 plus adjacent old NR0/NR1/NR2 tests          31/31
complete unittest discovery with tracked Win shim 1671/1671
git diff --check                                       PASS
```

The virtual environment does not contain `pytest`; its attempted entry point
stopped before collection with `No module named pytest`. No package was
installed. The complete suite was therefore executed through standard-library
`unittest` after loading the repository-tracked `tests/conftest.py` Windows
`resource` compatibility shim. It finished with zero failures and zero errors.

The implementation commit and pushed remote branch are reported by the final
handoff, since a commit cannot contain its own Git object identifier.
