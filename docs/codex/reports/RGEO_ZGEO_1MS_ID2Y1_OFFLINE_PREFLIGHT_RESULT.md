# ID-2Y1 offline preflight result

ID-2Y1 was rejected before reset, `gotsc`, plant advance or raw creation.  The
server passed 6/7 focused structural tests; the only failure was the frozen
95 A absolute-current-headroom gate.  Exact zero-plant enumeration found:

| branch | minimum absolute-current headroom | limiting coil |
|---|---:|---:|
| p03L64 + p04m6 | 97.0 A | 13 |
| p03L64 + p04m12 | 95.2 A | 13 |
| p03L64 + p04m12 + p07p4 | 94.0 A | 13 |
| p03L64 + p04m16 + p07p4 | 92.8 A | 13 |

The two failing branches are not run and the 95 A gate is not weakened after
the result.  ID-2Y1 is final as an offline excitation/action-matrix design
FAIL with zero TSC.  No plant, hold, model or controller conclusion exists.

ID-2Y1R1 uses a separate identity.  It retains the two passing branches and
replaces only the rejected combinations by p04m6+p07p4 (95.8 A) and
p04m8+p07p4 (95.2 A).  All other timing, safety, terminal and data-use rules
remain unchanged.

