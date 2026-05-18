#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/run_train_native.sh" "${1:-configs/train_b81_96worker_100k.json}"
