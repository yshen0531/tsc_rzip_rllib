# Stage3.3 Target-Conditioned Nominal Library and Receding-Horizon MPC

- Verdict: **TARGET_CONDITIONED_LIBRARY_INCOMPLETE_MPC_NOT_VALIDATED**
- Configured targets: 20
- Tracking-pass library entries: 14
- Mandatory target passes: 5/10
- Target library confirmed: False
- Selected MPC scale: None
- MPC calibration pass: False
- MPC holdout pass: False
- MPC confirmation pass: False

## What this stage proves

Stage3.3 first builds separate real-TSC 250 ms nominal sequences for multiple R/Z/Ip targets. It then runs a bounded least-squares receding-horizon controller that resolves at every 10 ms step and applies only the first correction.

## What this stage does not prove

The campaign does not change the simulator restart state.  Action injections are not equivalent to genuine initial-state variation. Plant-parameter, hidden vessel/eddy-current state, measurement-noise, and delay robustness remain untested. The final controller must ultimately handle all of those effects; residual RL remains bounded and secondary.

## Target library

| Task | Mandatory | Tracking pass | Signed margin | Sustained box [mm] | Ip hold RMS [A] |
|---|---:|---:|---:|---:|---:|
| nominal | 1 | 1 | 0.03198 | 29.041 | 149.0 |
| R_p5mm | 1 | 1 | 0.00224 | 29.933 | 150.1 |
| R_p10mm | 1 | 0 | -0.09555 | 32.867 | 158.2 |
| R_m5mm | 0 | 1 | 0.03198 | 29.041 | 149.0 |
| R_m10mm | 0 | 1 | 0.03198 | 29.041 | 149.0 |
| Z_m2mm | 1 | 1 | 0.00534 | 29.840 | 144.8 |
| Z_m5mm | 1 | 0 | -0.07069 | 32.121 | 139.6 |
| Z_m10mm | 1 | 0 | -0.21514 | 36.310 | 137.6 |
| Z_p2mm | 0 | 1 | 0.09865 | 27.041 | 149.0 |
| Z_p5mm | 0 | 1 | 0.16527 | 25.042 | 151.6 |
| Z_p10mm | 0 | 1 | 0.21272 | 23.618 | 155.0 |
| RZ_p5_m5mm | 1 | 0 | -0.07181 | 32.154 | 138.3 |
| RZ_p10_m10mm | 1 | 0 | -0.22047 | 36.614 | 140.2 |
| RZ_m5_m5mm | 0 | 0 | -0.06916 | 32.036 | 138.5 |
| RZ_m5_p5mm | 0 | 1 | 0.19865 | 24.041 | 149.0 |
| RZ_p5_p5mm | 0 | 1 | 0.05355 | 28.394 | 154.4 |
| Ip_m500A | 0 | 1 | 0.03198 | 29.041 | 638.1 |
| Ip_p500A | 0 | 1 | 0.03198 | 29.041 | 370.4 |
| Ip_m1000A | 1 | 1 | 0.03198 | 29.041 | 1136.7 |
| Ip_p1000A | 1 | 1 | 0.03198 | 29.041 | 867.3 |

## Final task

The project objective is not a finite library or one MPC test envelope.  It is a causal robust controller across initial states, targets, plant uncertainty, hidden dynamic state, noise, and delay.  The intended architecture remains nominal + causal MPC/feedback + bounded residual RL.
