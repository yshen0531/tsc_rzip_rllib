#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${STAGE4_2R3C3T13S18_CONFIG:-$PROJECT_ROOT/configs/stage4_2r3c3t13s18_pooled_causal_observer_preflight.json}"
SOURCE_RUN="${STAGE4_2R3C3T13S18_SOURCE_RUN:-$PROJECT_ROOT/stage4_2r3c3t13s16_runs/stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165232}"
S17_RUN="${STAGE4_2R3C3T13S18_S17_RUN:-$PROJECT_ROOT/stage4_2r3c3t13s17_audits/stage4_2r3c3t13s17_causal_multi_drift_belief_preflight_20260803_0f9ef6b}"
OUTPUT_DIR="${STAGE4_2R3C3T13S18_OUTPUT_DIR:-$PROJECT_ROOT/stage4_2r3c3t13s18_audits/stage4_2r3c3t13s18_pooled_causal_observer_preflight_20260803}"
COMMAND="${STAGE4_2R3C3T13S18_COMMAND:-prepare}"

export PROJECT_ROOT CONFIG SOURCE_RUN S17_RUN OUTPUT_DIR COMMAND
