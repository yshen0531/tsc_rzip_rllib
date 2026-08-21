# Fixed-1000 B1 mixed-history blind result

B1 completed all `12/12` authentic rollouts and `576/576` verified advances
at revision `6646d54feec1de1fe3d3c939d81ef2e3b0be904b`. Ten unopened mixed-history
rows and two zero-weight replays were evaluated without refitting or widening
V0.

Both composed histories passed. `even_plus -> odd_minus` and
`even_minus -> odd_plus` each achieved `24/24` frozen-set component
containment. Maximum directional ranking regret was `0.001699 mm / 0`, and
h8 weakest-best progress was `0.277947 / 0.276302 mm`. Best h4
condition/sigma-min were `1.52094 / 0.211643 mm` and
`1.56119 / 0.205992 mm`.

The independent raw audit rebuilt all 588 states, 576 actions and 564 later
observed-slew transitions and reproduced the result. Both critical replays
were exact. Primary and independent SHA-256 are
`e003bfadef4d149498ebef2970bf5d0e429b76b238400ac09ed29527e63b1985` and
`40b7a402499ebf6a27ac72b7111903ab2d7adf9a7d4a2fbb1b42ae86a213f789`.

The final routes are
`ONE_MS_NR1000B1_FIXED_V0_MIXED_HISTORY_BLIND_PASS_AUTHORITY_DESIGN_ONLY` and
`ONE_MS_NR1000B1_INDEPENDENT_PASS`. This is a finite fixed-model blind PASS,
not Authority, capture, Recourse, feedback or path tracking. It closes the
current model-evidence sequence and authorizes only an independently frozen
Authority/feedback design.
