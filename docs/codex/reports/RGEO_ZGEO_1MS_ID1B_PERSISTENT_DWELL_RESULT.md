# ID-1B persistent-dwell signed geometry result

Date: 2026-08-14 (Asia/Shanghai)

## Final verdict

ID-1B completed its complete preregistered real-TSC matrix and is final as

`ONE_MS_ID1B_PERSISTENT_POSITIVE_SPAN_FAIL_DIRECTION_REDESIGN`.

Execution, exact actuator/timing, boundary, current, Ip, raw inventory,
repeatability, per-arm signal, Ip cost and numerical R/Z rank all passed. The
scientific positive-span gate failed. This is a finite source/late-q0/action-
history identification-design result. It is not a runtime, deployment, raw,
model, controller, MPC, recovery, global-authority or reachability failure.

`basis_selection_data_eligible=false` and `model_fit_data_eligible=false`.
No predictive model or controller was fit or trained.

## Identity and execution evidence

- Frozen config SHA-256:
  `3ceef849a801a5a027cc39144a4e3210a325a2e2d45e611fadd2f20369c3d1ae`.
- Plant implementation revision:
  `bd1b580276e8bdf37160d8d9fa028d250b96a4d7`.
- Initial package manifest revision: `4d7a3a55`; manifest SHA-256:
  `85aa30bbae39f3362d2da9b42dd94bd6204ae4f3418c79251f5328816bd8d886`.
- Audit-only fix revision: `666c8e065ffbd089d8d3fa9e5be40aff0167620a`.
- Audit-hotfix package revision: `6b920f4e`; manifest SHA-256:
  `1a999dee9d9c7c38231f4c036c22a074786263883b15e8d566022824889bcd7a`.
- Remote run directory:
  `/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id1b_runs_20260814_bd1b5802`.
- Completed: 14/14 resets, 336/336 advance attempts, 336/336 `gotsc`
  calls and 336/336 verified successors; 350 retained states.
- Raw inventory: 1,750 required files, 20,612,523,400 bytes, digest
  `31170185118b0c8d5698db80bd9f3862823602b95247216a42479ac657a0975d`.
- Primary result SHA-256:
  `54ed170bc628237d6d7b8828f6dc3c77b06e549f064a63ae4281af9aea0d0db8`.
- Final independent audit SHA-256:
  `4eb32fd6021f8d30c20103ada2530c444d73ad7c38707441f77f7e227c6c6791`.

All seven replay pairs reproduced R/Z/Rmid, Ip, all 14 coil currents and all
48 wire currents with maximum recorded difference zero.

## Scientific result

The mean responses over pure persistent effect states 11--14, relative to
the matched q0 baseline, were:

| Card15 arm | dR (mm) | dZ (mm) | dIp (A) |
|---|---:|---:|---:|
| p03 plus | +0.087115 | -0.019747 | -31.595 |
| p03 minus | +0.115629 | -0.074228 | +30.432 |
| p04 plus | +0.086273 | -0.091179 | -43.443 |
| p04 minus | +0.117586 | +0.002013 | +42.430 |
| p07 plus | +0.091999 | -0.109045 | -25.483 |
| p07 minus | +0.111979 | +0.020619 | +24.409 |

All signed arms had measurable signal and acceptable Ip response. The six
R/Z columns had numerical rank two, and the best-conditioned pair was p07
plus/minus with condition `1.8089786595722026`. Nevertheless, every mean R
component was positive. The maximum angular gap was
`299.72069139587876 deg`, above the frozen 175-degree cap, and minimum
directional support was `-0.089323963 mm`, below the required `+0.005 mm`.
Thus rank two did not supply a positively spanning local response cone.

This does not prove that TSC lacks negative-R authority. It rejects only the
six measured q0-centred persistent response rays in this exact source/time/
history cell as a controller basis. In particular, a time-varying active
nominal command may change the appropriate linearization centre; that
hypothesis remains untested.

## Independent audit correction

The first independent audit was preserved and failed only 14 compact-action
checks. It reconstructed issue 0 from retained state-0 `inputa`, but that
file contains the outgoing q0 command after the runner rewrites it. The
authentic pre-issue source command differs from q0 by the known `1e-5 A`
settling. This was an audit reconstruction/reporting defect, not a plant or
action defect.

Revision `666c8e06` changed only the independent reconstruction to use the
authenticated pre-issue source command. No TSC was rerun. The final
independent raw audit passed with zero failures, reproduced the raw inventory
exactly, reproduced the same scientific FAIL route, and differed from the
primary metrics by at most `6.776263578034403e-21`.

## Route decision

The p03/p04/p07 q0-centred persistent ladder stops here. The next stage is a
zero-new-TSC direction/centre design audit. It must distinguish:

1. absolute response rays around q0;
2. deviations around a prospective nonzero, time-varying nominal command;
3. true two-sided residual authority needed for later bounded-tube recourse.

No new model fitting, calibration, holdout, transport, MPC or controller run
is authorized by ID-1B. A future TSC discriminator must use a new prospective
identity, declare its data role before execution, and must not treat rank two
or the natural q0 drift as a substitute for bidirectional residual authority.

Compact evidence is tracked in
`docs/codex/audits/rgeo_zgeo_1ms_id1b_result_20260814_bd1b5802/`.
