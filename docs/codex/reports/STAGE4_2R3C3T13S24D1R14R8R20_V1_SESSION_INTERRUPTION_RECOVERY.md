# Stage4.2R3c3T13S24D1R14R8R20 v1 session-interruption recovery

Frozen before inspecting any R8R20 physical trajectory outcome.

## Scope and immutable evidence

The deployed R8R20 implementation/package checkpoint remains `98c67c5` and
the frozen direct-Boolean-cube design remains `f13e88a`.  No controller,
configuration, task specification, Card15 action, safety gate, scientific
gate, or formal-timing rule is changed by this recovery decision.

The v1 run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r20_runs/
stage4_2r3c3t13s24d1r14r8r20_direct_boolean_cube_completion_authority_sentinel_20260808_98c67c5_v1
```

Its offline primary, offline independent, and safety authorization completed.
The safety launcher then started one R8R20 driver, its dedicated Ray session,
and all 24 frozen safety `gotsc` tasks.  The controlling local SSH cell was
incorrectly terminated after a monitoring probe checked the wrong raw path
and before the newly starting remote processes were observed.  The remote
actors completed their plant work, but the interrupted driver exited before
persisting any task result.

The authenticated pre-outcome facts are:

```text
v1 safety specifications launched                 24
v1 completed gotsc subprocesses observed           24
v1 raw/safety/*.json.gz files                        0
v1 raw/qualification/*.json.gz files                 0
v1 stage_state phase_status          safety_authorized
v1 stage_state new_raw_count                         0
v1 stage_state real_tsc_executed                 false
v1 stage_state formal_outcomes_opened            false
v1 safety_execution.json                         absent
v1 safety_raw_primary.json                       absent
```

The 24 dedicated `/tmp/tsc_workspace/stage42r8r20_safety_*` directories are
preserved.  They contain final TSC workspaces but not the complete per-step
Python trajectory and controller trace required by the frozen raw schema.
They therefore cannot be promoted into scientific raw or used to infer a
control outcome.

This is a launch/session and result-persistence failure.  It is not a TSC
solver conclusion, a restart conclusion, a raw-integrity conclusion, a
controller-design result, an MPC result, a formal-control result, or a plant
reachability result.

## Frozen recovery rule

The v1 run is permanently incomplete and may not be resumed, finalized,
audited as a scientific campaign, used for model fitting, or used for expert
or learning data.  Its run directory and the 24 dedicated workspaces must be
preserved as incident evidence.  No v1 physical outcome may be opened or
used to change the R8R20 design.

One clean replacement run with suffix `_v2` is authorized under these exact
conditions:

1. use the already deployed `98c67c5` package without source changes;
2. use the exact frozen 96 R8R20 specifications and their existing digest;
3. retain the original 24-safety then 72-qualification split;
4. retain every frozen safety, execution, raw, independent-reproduction,
   direct-repair, complete-cube-oracle, and formal-timing gate;
5. count at most 96 physical trajectories in v2 and never reuse v1 raw or
   workspace files;
6. write launcher output to a server-side log and detach it from the SSH
   transport before monitoring by exact PID;
7. preserve all v2 trajectories as forbidden from expert and learning data.

The replacement is an infrastructure recovery before outcomes, not a gate
amendment or a second look at failed science.  The v2 scientific result must
stand on its own and must report the v1 incident separately.
