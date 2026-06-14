# B92 run notes

## Why B92

B91 moved R in the correct direction but plateaued: deterministic probe stayed near `R_error ~= -0.17 m`, while `Z_error ~= +0.04 m`.  B92 therefore does not push Z harder.  Instead, it makes radial recovery more explicit and directly discourages the saturated common-mode coefficients observed in B91.

## Success criteria for first B92 diagnostic

Useful signs:

- `eval_final_det_terminal_R_error > -0.13`
- `eval_final_det_terminal_Z_error < 0.10`
- `eval_final_det_extra_common_mode_coeff_abs_mean_last` drops clearly below the B91 saturated regime
- `eval_final_det_mode_coeff_mean/outer_pf_common_shape` and `/cs_common_flux` are not persistently near `±1`

If R improves to `-0.14 ~ -0.15` but Z rises to `0.10 ~ 0.14`, the direction is still useful; next step should soften common-mode penalty or restore a little Z pressure.

If R remains below `-0.16`, the common-mode/raw-action structure is still finding the inward local optimum; next step should use stronger mode coefficient limits or remove/replace the common modes for one diagnostic run.
