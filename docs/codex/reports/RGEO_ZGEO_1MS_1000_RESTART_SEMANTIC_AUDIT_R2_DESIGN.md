# Fixed-1000 restart semantic audit R3R2

R3R1 completed all four one-ms holds. Every rollout passed its execution,
command, clock and hard-envelope checks; issued slew was 0 A and the observed
source-to-successor actual-current bias was consistently 8 A. Cross-run
R/Z/R_mid/Ip, 14-coil and 48-wire semantics were exact. The frozen whole-file
artifact gate failed because state1 `outputa` records wall-clock launch time
and CPU timing.

R3R2 is zero TSC and does not alter R3R1. It independently reparses all eight
raw states. `inputa`, `geqdsk`, coil and wire files must be byte-exact. Outputa
normalization is limited to exactly one version wall-clock line and exactly
one CPU timing line per file; every remaining byte must agree. Any other
difference fails. PASS qualifies only canonical fixed-1000 restart semantics
and authorizes a separately frozen fresh NR1 interface campaign.
