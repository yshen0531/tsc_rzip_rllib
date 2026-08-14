# ID-0T1 independent-audit timing hotfix

Date: 2026-08-14 Asia/Shanghai

Plant implementation revision: `18788cf46eb029821169ae252fa2429bb50e5759`

Reporting-only hotfix revision: `273427f97e9a3e96a12c9084491f416daba6274a`

## Frozen raw and primary result

The one authorized ID-0T1 campaign completed all eight rollouts and all 256
plant advances. Its raw is immutable and must not be rerun for this hotfix.
The primary result SHA-256 is
`a5e64d304c9b6cc5716047aee2d81d873e650a364390c2cb2705b26f86bc0d0d`.
It reports execution, raw inventory and compact-prefix identity PASS, followed
by the frozen state32 scientific route
`ONE_MS_ID0T1_STATE32_TAIL_INSUFFICIENT_ROUTE_REVIEW`.

The first independent audit SHA-256 is
`4343c64eb03ab8052b759c92e9c93083b72c62c80e67f915131afad4db006083`.
It parsed all 264 raw states but reported every prefix comparison as failed.
That audit remains preserved as a reporting FAIL and is not overwritten.

## Confirmed audit bug

The primary compact captures each state's `inputa` hash and active command
before issuing the next action. The retained raw state directory is later
rewritten with that state's outgoing `inputa`. The first auditor compared the
post-rewrite raw hash with the pre-rewrite compact hash. It also used raw
state1100's outgoing q0 command as the previous command for issue0, changing
the authentic source-to-q0 maximum delta from `1e-5 A` to zero.

This is a time-coordinate/reporting error. It is not a Card15, queue, plant,
geometry, Ip, coil, wire, raw-corruption or scientific-tail result. The
primary new compact prefixes match both ID-0 compact repeats exactly. The
first independent audit's reported geometry, Ip, 14-coil and 48-wire maxima
were all zero; only `ACTION_STREAM` and rewritten `inputa` hashes failed.

## Hotfix semantics

The independent auditor now:

1. verifies each raw outgoing `inputa` directly against the frozen Card15
   action for that state;
2. reconstructs issue0's previous command from the unique frozen pre-issue
   source command in all fourteen ID-0 reference compacts;
3. compares prewrite-compatible geometry, Ip, coil, wire and the remaining
   semantic artifact hashes against ID-0;
4. writes a new `independent_audit_hotfix.json` and refuses to overwrite the
   original failed audit.

No controller, action, threshold, raw file, primary metric or scientific gate
changes. The hotfix is allowed to recompute only the existing raw and cannot
run TSC, reset the plant or generate a new trajectory.
