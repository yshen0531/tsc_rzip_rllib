#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def recursive_find(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            out = recursive_find(v, key)
            if out is not None:
                return out
    elif isinstance(obj, list):
        for v in obj:
            out = recursive_find(v, key)
            if out is not None:
                return out
    return None


def walk_nonfinite(obj: Any, prefix: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_nonfinite(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_nonfinite(v, f"{prefix}[{i}]")
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            yield prefix, obj


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/analyze_rllib_run.py ray_results/<run_dir>")
        raise SystemExit(2)

    run_dir = Path(sys.argv[1])
    path = run_dir / "train_results.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)

    print("run_dir:", run_dir)
    print("results:", path)
    rows = []
    last_steps = None
    nonfinite_keys: dict[str, int] = {}

    for i, line in enumerate(path.read_text().splitlines(), start=1):
        obj = json.loads(line)
        env_steps = (
            recursive_find(obj, "num_env_steps_sampled_lifetime")
            or recursive_find(obj, "num_env_steps_sampled")
            or recursive_find(obj, "env_steps_sampled")
            or 0
        )
        ret = recursive_find(obj, "episode_return_mean") or recursive_find(obj, "episode_reward_mean")
        length = recursive_find(obj, "episode_len_mean") or recursive_find(obj, "episode_length_mean")
        delta = None if last_steps is None else env_steps - last_steps
        last_steps = env_steps
        bad = list(walk_nonfinite(obj))
        for k, _ in bad:
            nonfinite_keys[k] = nonfinite_keys.get(k, 0) + 1
        rows.append((i, env_steps, delta, ret, length, len(bad)))

    print("\nIterations:")
    print("iter | env_steps | delta | return_mean | len_mean | nonfinite_fields")
    print("-" * 78)
    for row in rows:
        print(f"{row[0]:4d} | {row[1]:9.0f} | {str(row[2]):>5} | {str(row[3]):>11} | {str(row[4]):>8} | {row[5]:16d}")

    print("\nNonfinite summary:")
    print("total_nonfinite_fields:", sum(nonfinite_keys.values()))
    for k, n in sorted(nonfinite_keys.items(), key=lambda x: (-x[1], x[0]))[:80]:
        print(f"{n:4d}  {k}")


if __name__ == "__main__":
    main()
