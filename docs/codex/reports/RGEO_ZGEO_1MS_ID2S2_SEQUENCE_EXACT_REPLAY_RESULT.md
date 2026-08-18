# ID-2S2 exact sequence replay result

## Verdict

ID-2S2 completed the four prospectively frozen fresh TSC replays and the
independent server-side raw audit. The final route is:

`ONE_MS_ID2S2_SEQUENCE_EXACT_REPLAY_PASS_SHOOTING_DESIGN_ONLY`

This is a finite exact-replay PASS for four source-local f03 two-arm action
streams. It is not a probabilistic tube, model, authority, hold, recovery,
controller, MPC, transport, crossing, or reachability result.

## Identity and execution

- design revision: `1ce85b681e455ade192908899a8065129fe7b7fd`
- implementation revision: `90d698034ba340315d5a2f51201febbeb4af58a4`
- config SHA-256:
  `43bbf436be27a5950a802cf99f10f63b40315f5e05e9d98c692af621d3c64afe`
- primary result SHA-256:
  `a8145350d674b9f649e492e029c3d06899f936fe531482f4e939e95bc5298b5d`
- independent raw audit SHA-256:
  `74ae028e44c72417c26623326a0e4c91233438a329ea26c625cd7a9a5ffc118d`
- resets / TSC calls / verified advances: `4 / 136 / 136`
- retained states: `140`
- required artifacts: `700`, `8,245,009,360 bytes`
- raw inventory digest:
  `2736338ad6482f479604060a7a19a65a3286add107202ef5840e367e210ba654`
- server validation before TSC: focused `10/10`; complete one-ms suite
  `297/297`

The first focused test attempt stopped before TSC because the generated
template described issue zero relative to q0 while the authentic S1 compact
recorded the measured `1e-5 A` source-to-q0 settling slew. The hotfix retained
that authentic derived field and continued to require every Card15/action
field to match. No TSC was run under the earlier implementation.

## Independent replay evidence

For every one of the four sequences:

- the matched f03 prefix passed;
- all R_geo/Z_geo/R_mid values, Ip, 14 coil currents, and 48 wire currents
  matched the S1 compact with maximum difference exactly zero;
- all paired R_geo/Z_geo/Ip response samples matched with maximum difference
  exactly zero;
- the complete measured sequence metric object was exactly reproduced.

The independently recomputed inventory, counters, metric object, verdict and
route all matched the primary result with no failures. `sprsina` remained a
diagnostic artifact rather than a byte-identity gate, consistent with the
frozen restart semantics.

The repeated measured geometry therefore remains:

- minimum progress over sixteen target directions: `0.037377 mm`;
- mean progress: `0.269098563 mm`;
- maximum angular gap: `134.432693 deg`;
- maximum absolute paired Ip response: `43.0516 A`.

Exact digital-twin replay at this one prefix and four action streams does not
estimate stochastic variation or establish a controller-grade transition
tube. Both S1 and S2 trajectories retain zero fitting, calibration, holdout,
expert-data, and RL weight.

## Route decision

The finite action response is deterministic enough to justify designing a
bounded canonical-source sequence-shooting discriminator. The next design
must use absolute tracking/hold utility and time-resolved constraint margins,
not the failed isolated-pulse additive heuristic. It must preregister a small
candidate set, preserve exact Card15/current/boundary/Ip gates, and keep any
new TSC identity distinct from model training and controller qualification.
