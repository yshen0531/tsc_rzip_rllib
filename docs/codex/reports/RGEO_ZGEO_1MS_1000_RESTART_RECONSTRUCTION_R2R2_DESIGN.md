# Fixed-1000-ms restart reconstruction R2R2

R2R1 is final as `ONE_MS_NR1000S0R2R1_INITIAL_RECONSTRUCTION_FAIL`. Although
its contract and offline result froze 2700 seconds, `execute()` reloaded the
source config and passed its 180-second timeout to the real runner. The sole
call again ended at internal time 0.10253 s with stderr `TSC timeout after
180.0 s`. This is an implementation-path wiring FAIL, not a second test of
the intended R2R1 runtime budget or any plant/model/control property.

R2R2 applies the same frozen 2700-second value through one shared function in
both preflight and execution; a focused behavioral test verifies the loaded
runtime config becomes 2700 seconds. Inputs, hashes, Card00, clocks, two full
runs, two one-ms replays, four-call maximum, no retry and all scientific gates
are unchanged. PASS still authorizes only a new canonical-source interface.
