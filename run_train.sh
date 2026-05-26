#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/run_train_native.sh" "${1:-configs/train_b83_192worker_5m.json}"
