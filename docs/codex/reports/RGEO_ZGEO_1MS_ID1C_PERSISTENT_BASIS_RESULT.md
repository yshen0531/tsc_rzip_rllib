# ID-1C exact-centred persistent basis result

Date: 2026-08-14 (Asia/Shanghai)

## Final classification

ID-1C completed its complete frozen matrix and is final as
`ONE_MS_ID1C_SIGNAL_SYMMETRY_OR_IP_FAIL_REDESIGN`.

This is a clean finite scientific/design FAIL. It is not a runtime, TSC,
Card15, boundary, current, raw-integrity, repeatability, model, controller,
MPC, recovery, closed-loop or global-reachability failure.

The primary compact result is
`docs/codex/audits/rgeo_zgeo_1ms_id1c_result_20260814_9401377d/result.json`
(SHA-256 `7e6bf6d535c1f4b880301c56c952f58820c354339467618ce39055946dc0a359`).
The independent raw recomputation is `independent_audit.json` in the same
directory (SHA-256
`92a19f62ab9a452b5d7deba29a1b47dd96dc2701321eee88789e89b44f408aef`).

## Execution and evidence identity

- implementation revision: `9401377d179632a73cc2cf035e5b95691e0ab308`;
- frozen config SHA-256:
  `1fd3026aafba240027fec5c6f5fca575ccfcf9afe75221ca4bc61660cc1f7e08`;
- remote run:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id1c_runs_20260814_9401377d`;
- 10/10 resets, 180/180 one-ms advance attempts, 180/180 `gotsc` calls,
  180/180 verified successors and 190 states;
- 950/950 required raw artifacts, 11,189,655,560 bytes, inventory SHA-256
  `a4ee5ade9db3131afa320ba59747fa6d9909c52837700636a5ed2f35be30c611`;
- independent audit PASS with maximum primary-metric difference
  `1.36e-20`;
- all five replay pairs were exactly repeatable in checked R/Z/Ip, 14 coil
  currents and 48 wire currents.

The first launch attempt stopped before Python or TSC because the installed
launcher lacked its executable bit (`rc=126`). It created no run directory
and consumed no plant advance. After setting only that file mode and passing
server `bash -n`, the same frozen identity was launched once. The launcher
also contained an UTF-8 BOM, so Bash reported the first shebang as an unknown
command before executing line 2 (`set -euo pipefail`) and the unchanged
Python campaign. This packaging/text-format defect did not alter the payload
hashes, config, actions or raw run, but the launcher encoding must be repaired
before a future stage. The v1 and v2 remote log SHA-256 values are respectively
`ae3fc417fc24823c2d5c8b662a8f2e9de31157bb9c404e09268f2556777ee22a`
and `54e0e819d49ad2fc7992475c369e3ff5a8bb14352e70d2aae45be17422f00e5d`.

## Frozen scientific gates

Signal, Ip and numerical rank passed. The actual four-ray response set had
rank two and best pair condition `2.7639959282`. It nevertheless failed both
the pair-even and positive-span requirements:

- p01 odd R/Z norm: `0.0271662 mm`;
- p01 even R/Z norm: `0.0000362 mm`;
- exact-centred half-p09 odd R/Z norm: `0.101755 mm`;
- exact-centred half-p09 even R/Z norm: `0.109626 mm`, versus the frozen
  `0.005 mm` cap;
- maximum angular gap: `180.150886 deg`, versus `175 deg`;
- minimum directional support: `0.0000948 mm`, versus `0.005 mm`.

The failure is concentrated rather than a broad loss of signal. Relative to
the same-clock q0 baseline, p09-minus produced the following R/Z responses:

| effect state | dR (mm) | dZ (mm) |
| --- | ---: | ---: |
| 11 | -0.022375 | -0.013578 |
| 12 | +0.742786 | -0.409532 |
| 13 | -0.065249 | -0.052510 |
| 14 | -0.076495 | -0.069262 |

The state-12 excursion repeated byte-for-byte in both p09-minus rollouts and
then returned to the ordinary response scale at state 13. A read-only raw
GEQDSK forensic found 278 paired boundary points at every checked state, with
unchanged state-12 extrema indices `(Rmin,Rmax,Zmin,Zmax)=(2,137,217,65)`.
Relative to q0, the p09-minus state-12 outline moved coherently by as much as
`3.442143 mm` in R and `3.878439 mm` in Z; it was not a single boundary-point
outlier or an R/Z splice. `xmag/zmag` changed only at the sub-micrometre scale
and were not used for R_geo/Z_geo.

## What this does and does not establish

ID-1C directly rejects treating p01+p09 as one fixed, odd, four-effect mean
response basis at this source/time/history. It does not reject p01, p09 as a
one-step primitive, a duration-conditioned primitive library, nonlinear
history-conditioned dynamics, two-axis controllability, or eventual path
tracking. The deterministic state-12 event is positive evidence that effect
age and causal history must remain explicit.

The preregistered result keeps `basis_selection_data_eligible=false` and
`model_fit_data_eligible=false`. Neither ID-1C nor older ID-0/ID-1A/ID-1B data
may be retroactively used as the next model's fit, calibration or holdout
records.

## Recommended route adjustment

Stop the static persistent-basis ladder. A new action direction should not be
accepted merely because its four-state mean is rank two or nearly odd.

The next prospective data stage should instead be a fit-eligible,
duration/history-conditioned primitive campaign:

1. preserve exact actuator/queue semantics, exact current R_geo/Z_geo/Ip and
   full post-1100-ms causal history;
2. use a small predeclared library of actual signed Card15 primitives, with
   one-, two- and four-issue durations and exact q0 returns;
3. include same-clock q0 baselines and repeat complete prefix families;
4. measure every effect state and tail instead of collapsing a primitive to
   one mean vector;
5. group siblings by complete prefix/history in development, calibration and
   unopened holdout splits;
6. first establish source-local duration/history response support, then add
   matched-time/different-position and matched-position/different-arrival-
   history anchors in a small HFS connected domain.

Only after those records exist should the route compare an exact actuator and
time-indexed nominal continuation plus stable low-order latent/state-space
model against the same backbone with a small GRU/TCN residual. Current R/Z/Ip
remain noiseless observations; latent belief represents passive memory and
future-response/model uncertainty. Controller-grade tubes, terminal recourse,
transport, crossing and closed-loop MPC remain separate later qualifications.

## Current operational blocker

The server had about 42 GB free before ID-1C and about 31 GB free afterwards;
the immutable ID-1C raw tree occupies 11 GB. A scientifically useful fresh
duration/history/anchor campaign plus later calibration/holdout cannot be
completed safely in the remaining space without a separately approved storage
or retention action. No raw tree should be deleted, overwritten or silently
compressed to make room.
