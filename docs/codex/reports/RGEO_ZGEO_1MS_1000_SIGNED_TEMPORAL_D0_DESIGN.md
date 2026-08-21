# Fixed-1000 signed temporal D0 design

D0 is the first action-response campaign in the new fixed-1000 lineage. It
uses the independently audited B0 q0 path as its matched baseline and does not
read any fixed-1100 response trajectory.

Two input coordinates are defined from the physical up/down coil pairing in
TSC order. The even coordinate changes each upper/lower pair in the same
direction; the odd coordinate changes each pair oppositely. They are tested
with both signs. Each target is constructed by exact Card15 quantization from
the current 1000-ms q0 center with a requested 0.15 A single-turn amplitude,
held for four issues, returned exactly to q0, and followed through state40.
The four signed actions are tested at issues 8, 10 and 24. Positive even and
odd issue-24 paths receive one integrity replay each.

The fixed budget is 14 resets and at most 560 advance attempts, with no
retry. All twelve primary signed paths are prospectively development-fit
eligible; the two replays have zero fit weight. Calibration and holdout remain
unopened. Every step retains the 0.3 A hard command/readback limit, limiter,
absolute-current, 50 mm R/Z and 10% Ip fail-closed envelope.

Scientific PASS requires nontrivial h4/h8 response for both signed axes at
all phases, signed-pair separation, and a well-conditioned two-axis odd
response matrix at h4 or h8 in every phase. Single-frame hybrid peaks cannot
substitute for persistent h4/h8 signal. PASS authorizes only bounded model and
Authority design. It is not hold, capture, recovery, Recourse or feedback.
