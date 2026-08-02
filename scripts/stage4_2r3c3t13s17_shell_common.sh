#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${STAGE4_2R3C3T13S17_CONFIG:-$PROJECT_ROOT/configs/stage4_2r3c3t13s17_causal_multi_drift_belief_preflight.json}"
SOURCE_RUN="${STAGE4_2R3C3T13S17_SOURCE_RUN:-$PROJECT_ROOT/stage4_2r3c3t13s16_runs/stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165232}"
OUTPUT_DIR="${STAGE4_2R3C3T13S17_OUTPUT_DIR:-$PROJECT_ROOT/stage4_2r3c3t13s17_audits/stage4_2r3c3t13s17_causal_multi_drift_belief_preflight_20260802}"
COMMAND="${STAGE4_2R3C3T13S17_COMMAND:-prepare}"

export PROJECT_ROOT CONFIG SOURCE_RUN OUTPUT_DIR COMMAND
