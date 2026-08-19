# ID-2Z4R1 independent `side` reporting correction

Date: 2026-08-19

The immutable ID-2Z4R1 v3 campaign completed 12 resets and 1,290 verified
plant advances.  The primary result and the first independent audit agree on
all counters, 6,510 required artifacts, 76,678,587,048 bytes, inventory
digest, safe-stop status and zero capture candidates.  The first independent
audit nevertheless failed every checkpoint only on the derived string field
`side`.

The failure is reporting-only.  The independent raw parser reconstructed
`R_geo`, `R_mid`, limiter bounds and all physical values, but did not populate
`side`; the shared prefix comparator therefore compared `None` with the
primary/reference value `HFS`.  The repository contract defines `side` as
`HFS` when `R_geo < R_mid`, otherwise `LFS`.

The only authorized correction is to derive that string from independently
parsed raw `R_geo` and `R_mid`, give the corrected audit a new schema and a
new output file, and rerun zero-TSC raw recomputation.  It may not alter the
primary result, raw files, actions, thresholds, candidate matrix, scientific
route or any plant execution.  Any other mismatch keeps the audit failed.
