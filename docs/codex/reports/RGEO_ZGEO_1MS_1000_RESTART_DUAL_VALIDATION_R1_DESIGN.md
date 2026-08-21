# Fixed-1000 dual restart validation R3R1

R3 consumed one TSC call and is final as
`ONE_MS_NR1000S0R3_RESTART_EXECUTION_FAIL`. Its raw successor reached exactly
1.001 s with the requested q0 Card15 command, finite R/Z/Ip and no abnormal
state. The failing check compared saved source actual coil current with the
next actual readback and found 8 A. That is not the issued-action slew: the
issued q0 target equals the live active Card15 command exactly.

R3R1 is a new identity. It changes only this evaluator coordinate. Before
each call, issued slew is checked from the live active Card15 command to the
issued target and must be at most 0.3 A. The source-to-successor actual-current
delta is retained as descriptive restart bias and is never renamed a command
or safety bound. State1 must still pass return code, abnormal, exact Card15,
1.000--1.001 s internal clock and the unchanged hard state envelope.

Two fresh one-step q0 replays are required from each of the two byte-distinct
R2R2 restart payloads. All four state0/state1 R/Z/R_mid/Ip, 14-coil and
48-wire values and the checked artifacts must agree exactly within the frozen
tolerances. Maximum budget is four TSC calls with no retry. Any failure stops
without a model or control claim. PASS qualifies only one canonical 1000 ms
restart semantics and opens a separately frozen 1000 ms NR1 interface stage.
