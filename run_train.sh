#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/run_train_native.sh" "${1:-configs/train_b82_96worker_2m.json}"
