# Fixed-1000 NR1 interface R4R1

R4 is final after ten advances. Hold replay was exact. Pattern A returned from
an issued 0.30000 A target with a 0.30001 A actual-current change on coil 11,
so the frozen observed-current hard gate stopped the rollout. This is an
excitation-margin failure, not effect physics or restart failure.

R4R1 uses a new identity and keeps the hard limit at 0.3 A. Its pattern
constructor is limited to 0.299 A, leaving 1 mA prospective readback reserve.
All six rollouts, target signs, matched-hold effect, exact return, replay and
safety gates are unchanged. R4 rows remain interface evidence only and are
not reused as R4R1 outcomes. PASS qualifies only the fixed-1000 one-ms
interface.
