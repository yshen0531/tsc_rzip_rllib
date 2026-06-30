#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_INTEROP_THREADS", "1")

import numpy as np

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.mpo.models import build_mode_matrix
from tsc_rzip_rllib.utils.config import deep_update, load_json


def expand_macros(obj: Any, macros: dict[str, str]) -> Any:
    if isinstance(obj, str):
        out = os.path.expandvars(obj)
        for k, v in macros.items():
            out = out.replace("{" + k + "}", str(v))
        return out
    if isinstance(obj, list):
        return [expand_macros(x, macros) for x in obj]
    if isinstance(obj, dict):
        return {k: expand_macros(v, macros) for k, v in obj.items()}
    return obj


def default_macros(run_id: str) -> dict[str, str]:
    tsc_all_root = os.environ.get("TSC_ALL_ROOT") or str(PROJECT_DIR.parent)
    return {
        "USER": os.environ.get("USER", "user"),
        "RUN_ID": str(run_id),
        "TSC_ALL_ROOT": str(Path(tsc_all_root).expanduser()),
        "PROJECT_DIR": str(PROJECT_DIR),
    }


def resolve_path_maybe_relative(path_text: str, *, base_dir: Path = PROJECT_DIR) -> Path:
    p = Path(str(path_text)).expanduser()
    if not p.is_absolute():
        p = base_dir / p
    return p


def resolve_tsc_config_file(train_cfg: dict[str, Any], *, out_dir: Path, macros: dict[str, str]) -> dict[str, Any]:
    cfg = json.loads(json.dumps(train_cfg))
    env_config_path = resolve_path_maybe_relative(expand_macros(str(cfg["env_config"]), macros))
    nested = expand_macros(load_json(env_config_path), macros)
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = out_dir / f"{env_config_path.stem}.mode_probe.{os.getpid()}.resolved.json"
    with open(resolved_path, "w", encoding="utf-8") as f:
        json.dump(nested, f, indent=2, ensure_ascii=False)
    cfg["env_config"] = str(resolved_path)
    return cfg


def load_cfg(config: Path, override: Path | None = None) -> dict[str, Any]:
    cfg = load_json(config)
    if override is not None:
        cfg = deep_update(cfg, load_json(override))
    run_id = str(cfg.get("run_name", config.stem))
    macros = default_macros(run_id)
    os.environ.setdefault("TSC_ALL_ROOT", macros["TSC_ALL_ROOT"])
    train_cfg_path = resolve_path_maybe_relative(expand_macros(str(cfg.get("train_config")), macros))
    train_cfg = expand_macros(load_json(train_cfg_path), macros)
    tmp_root = Path(os.environ.get("TMPDIR", "/tmp")) / f"mpo_mode_probe_resolved_{os.getpid()}"
    cfg["train_config_resolved"] = resolve_tsc_config_file(train_cfg, out_dir=tmp_root, macros=macros)
    return cfg


def force_stage(train_cfg: dict[str, Any], stage_name: str | None) -> dict[str, Any]:
    if not stage_name or stage_name == "default":
        return json.loads(json.dumps(train_cfg))
    cfg = json.loads(json.dumps(train_cfg))
    cur = cfg.get("curriculum", {}).get("env_attributes", {})
    stages = list(cur.get("stages", []))
    raw_stage_name = str(stage_name)
    aliases = {"final": "stage3", "strict": "stage3", "last": "stage3"}
    target = aliases.get(raw_stage_name, raw_stage_name)
    match = None
    for st in stages:
        name = str(st.get("name", ""))
        if target == name or name.startswith(target) or target in name:
            match = st
    if match is None and raw_stage_name in {"final", "strict", "last"} and stages:
        match = stages[-1]
    if match is None and stages:
        try:
            idx = int(raw_stage_name)
            if 0 <= idx < len(stages):
                match = stages[idx]
        except Exception:
            pass
    if match is None:
        available = [str(st.get("name", "")) for st in stages]
        raise ValueError(f"Cannot find eval stage {stage_name!r}; available stages={available}")
    cfg.setdefault("curriculum", {}).setdefault("env_attributes", {})["enabled"] = False
    cfg.setdefault("reward", {}).update(dict(match.get("env_params", {})))
    print(f"Probe stage fixed to: {match.get('name')}")
    return cfg

def scalar(info: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(info.get(key, default))
    except Exception:
        return float(default)


def main() -> None:
    ap = argparse.ArgumentParser(description="Open-loop sign test for MPO physics action modes.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="eval_results/b90_mode_sign_probe.csv")
    ap.add_argument("--eval-stage", default="stage0")
    ap.add_argument("--steps", type=int, default=80)
    ap.add_argument("--action-scale", type=float, default=0.35)
    ap.add_argument("--seed", type=int, default=54321)
    ap.add_argument("--modes", default="", help="Comma-separated mode names to test; empty means all modes.")
    ap.add_argument("--override", default=None)
    args = ap.parse_args()

    cfg = load_cfg(Path(args.config), Path(args.override) if args.override else None)
    train_cfg = force_stage(cfg["train_config_resolved"], args.eval_stage)
    env_cfg = {
        "backend": cfg.get("env", {}).get("backend", "native"),
        "train_config": train_cfg,
        "seed": int(args.seed),
        "worker_index": 0,
        "vector_index": 0,
        "num_workers_for_curriculum": 1,
        "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
    }
    env = RllibTscRzipEnv(env_cfg)
    action_dim = int(np.prod(env.action_space.shape))
    mode_names, mode_matrix = build_mode_matrix(action_dim, cfg.get("model", {}).get("physics_blend", {}))
    mode_matrix_np = mode_matrix.cpu().numpy()
    selected = [x.strip() for x in str(args.modes).split(",") if x.strip()]
    selected_set = set(selected)

    rows: list[dict[str, Any]] = []
    try:
        for i, name in enumerate(mode_names):
            if selected_set and name not in selected_set:
                continue
            base = np.clip(mode_matrix_np[i], -1.0, 1.0).astype(np.float32)
            for sign in [+1.0, -1.0]:
                obs, info0 = env.reset(seed=int(args.seed))
                init = dict(info0 or {})
                action = np.clip(sign * float(args.action_scale) * base, -1.0, 1.0).astype(np.float32)
                total = 0.0
                last_info = init
                terminated = False
                truncated = False
                nstep = 0
                for step in range(int(args.steps)):
                    _obs, reward, terminated, truncated, info = env.step(action)
                    total += float(reward)
                    last_info = dict(info or {})
                    nstep = step + 1
                    if bool(terminated or truncated):
                        break
                rows.append({
                    "mode": name,
                    "sign": int(sign),
                    "steps": int(nstep),
                    "action_scale": float(args.action_scale),
                    "terminated": bool(terminated),
                    "truncated": bool(truncated),
                    "return": float(total),
                    "init_R_error": scalar(init, "R_error"),
                    "init_Z_error": scalar(init, "Z_error"),
                    "init_Ip_error": scalar(init, "Ip_error"),
                    "final_R_error": scalar(last_info, "R_error", scalar(last_info, "terminal_R_error")),
                    "final_Z_error": scalar(last_info, "Z_error", scalar(last_info, "terminal_Z_error")),
                    "final_Ip_error": scalar(last_info, "Ip_error", scalar(last_info, "terminal_Ip_error")),
                    "delta_R_error": scalar(last_info, "R_error", scalar(last_info, "terminal_R_error")) - scalar(init, "R_error"),
                    "delta_Z_error": scalar(last_info, "Z_error", scalar(last_info, "terminal_Z_error")) - scalar(init, "Z_error"),
                    "delta_Ip_error": scalar(last_info, "Ip_error", scalar(last_info, "terminal_Ip_error")) - scalar(init, "Ip_error"),
                    "mean_abs_action": float(np.mean(np.abs(action))),
                    "max_abs_action": float(np.max(np.abs(action))),
                })
    finally:
        env.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["mode"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved mode sign probe CSV: {out}")


if __name__ == "__main__":
    main()
