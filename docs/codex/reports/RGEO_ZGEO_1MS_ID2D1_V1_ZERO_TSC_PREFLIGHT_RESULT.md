# R_geo/Z_geo 1 ms ID-2D1 v1 zero-TSC preflight result

Date: 2026-08-17 Asia/Shanghai

Implementation revision: `1ba484eb99ebd9653606ef49b74b2002690a0b44`.

The server passed `bash -n` and Python compilation, then stopped during the
focused test suite before the full regression suite, offline preflight, TSC
reset or plant advance. Six focused tests passed and the frozen lag-support
test failed: the 768 by 48 three-coordinate lag-16 virtual-action matrix had
rank 42 rather than the required 48.

Read-only zero-plant factorization showed:

- p04/p07 together at lag 16: shape `768 x 32`, rank 32, condition
  `14.73875049`, minimum singular value `0.58861302`;
- separate p09 event channel at lag 10: shape `768 x 10`, rank 10,
  condition 1, minimum singular value `1.41421356`;
- p09 forced to lag 16: rank 10/16;
- combined forced lag-16 matrix: rank 42/48.

The cause is structural: the frozen p09 event is issued at step 22 and only
ten subsequent transition origins exist through issue 31.  ID-2D1 v1 is
therefore final as `ZERO_TSC_LAG_SUPPORT_DESIGN_FAIL`; it ran zero TSC, zero
reset, zero `gotsc` and zero plant advance.  The rank-48 gate is not weakened
or reinterpreted as a PASS.

The corrected R1 identity keeps the physical campaign unchanged but aligns
the support claim with the prospective architecture: p04/p07 remain a smooth
lag-16 block requiring rank 32, while p09 remains a separately modelled
event channel requiring rank 10 over its ten genuinely observed ages.
