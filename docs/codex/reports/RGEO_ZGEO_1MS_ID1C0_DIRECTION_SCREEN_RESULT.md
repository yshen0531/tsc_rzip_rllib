# ID-1C0 consumed-development direction screen

Date: 2026-08-14 (Asia/Shanghai)

## Result

The server-side zero-TSC, zero-fit audit completed as

`ONE_MS_ID1C0_DIRECTION_SCREEN_PASS_FRESH_PERSISTENT_VALIDATION_REQUIRED`.

It authenticated 23 inputs (1,854,612 bytes; inventory digest
`d60600155c8261913580ac4962dced57bf4ea8e10d800c934c64a4bfe066e4a6`),
read only the already-consumed NR2R1 development records, the matched q0
baseline and the final ID-1B result, and did not read the old holdout. It ran
zero TSC/plant advances and fit or trained no model.

The result SHA-256 is
`4f89bd34555287b236d1c22a4bfb12883dd1b603cf4a49a46bfff63a174428db`.
The first server output used an incorrectly transcribed source-revision
argument and was preserved. The v2 result above differs only in that reporting
identity and binds the actual revision
`3986502f9d538021f2ef3e5fcd51b9cf82644ead`.

## Method and selected pair

For each development pair p00--p09, the audit used the maximal contiguous
first-event effect window before the next issued action edge. Plus and minus
were compared only after exact state-0/state-1 causal-prefix matching to the
q0 record. Candidate geometry used the complete actual plus/minus R/Z rays,
not sign labels or a forced odd model.

The selected two-direction candidate was p01+p09:

- R/Z rank: 2;
- response angles: `26.0504`, `107.1910`, `205.2523`, `287.3703` degrees;
- maximum angular gap: `98.6800382 deg`;
- minimum directional support: `0.0218296712 mm`;
- best two-ray condition: `2.0015232`;
- minimum ray norm: `0.0261165419 mm`;
- maximum absolute Ip response: `14.2429 A`.

P01 was an exact q0-centred half-amplitude four-effect dwell with negligible
pair-centre response. P09 supplied the complementary direction but its old
full-amplitude Card15 pair had a `0.05 A` midpoint bias and only one pure
effect state. Therefore the old targets are not reusable as a validated
persistent basis. The fresh stage must reconstruct an exact q0-centred
half-amplitude p09 pair and hold it unchanged through the same persistent
window as p01.

## Claim boundary

This is retrospective candidate screening over consumed development evidence.
It does not validate persistent p09 response, repeatability, a dynamics model,
transition tube, controller authority, hold, recovery or reachability. Its
only route is a separately frozen fresh persistent validation. Compact
evidence is tracked in
`docs/codex/audits/rgeo_zgeo_1ms_id1c0_direction_screen_20260814_3986502f/`.
