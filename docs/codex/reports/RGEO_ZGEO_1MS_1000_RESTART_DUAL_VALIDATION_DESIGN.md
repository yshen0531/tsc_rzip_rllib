# Fixed-1000-ms dual restart semantic validation

R2R2 is final as `ONE_MS_NR1000S0R2R2_INITIAL_RECONSTRUCTION_FAIL`: both full
0--1 s runs completed and reproduced R_geo/Z_geo/R_mid/Ip, 14-coil and 48-wire
state exactly, but their 58,727,036-byte `sprsoua` files had different hashes.
The exact-file gate remains failed and is not relaxed or relabeled PASS.

This R3 identity binds the failed result and both complete reconstruction
trees by path, size and SHA-256. It does no new full reconstruction. Instead,
each byte-distinct restart becomes a separate project-owned canonical source;
the checkpoint input and observable artifacts come from the authenticated
target source and only `sprsina` comes from the corresponding reconstruction.
Each source receives two fresh matched-hold one-ms replays. The four state-0
and four state-1 records must agree exactly in checked R/Z/Ip, 14 coil, 48 wire
and five semantic artifact hashes, with exact Card15, slew, internal clock and
hard-envelope gates. Maximum budget is four TSC calls with no retry.

PASS means only that these two finite byte-distinct restart representations
produce the same checked fresh restart semantics. It may select a canonical
source for a separately frozen interface campaign. It is not proof that every
restart byte is irrelevant, nor model, Authority, Recourse or control evidence.
