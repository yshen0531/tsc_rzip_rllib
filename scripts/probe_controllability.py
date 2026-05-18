#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Keep every probe worker single-threaded. Parallelism is across scenarios.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("BLIS_NUM_THREADS", "1")
os.environ.setdefault("RAYON_NUM_THREADS", "1")
os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tsc_rzip_rllib.core.coil_order import TSC_COIL_NAMES, TSC_NAME_TO_INDEX
from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.utils.config import deep_update, load_json
from train_rllib_sac import prepare_train_config

SCALAR_TYPES = (int, float, str, bool, np.integer, np.floating, np.bool_)


@dataclass(frozen=True)
class Scenario:
    name: str
    kind: str
    pulse_steps: int
    amplitude: float
    sign: int
    coil: str = ""
    coil_index: int = -1
    pair: str = ""
    mode: str = ""


def slugify(text: str, max_len: int = 100) -> str:
    text = re.sub(r"[^A-Za-z0-9_.=-]+", "_", str(text)).strip("_")
    return text[:max_len]


def parse_int_list(text: str) -> list[int]:
    return [int(x.strip()) for x in str(text).split(",") if x.strip()]


def parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in str(text).split(",") if x.strip()]


def is_scalar(v: Any) -> bool:
    return isinstance(v, SCALAR_TYPES)


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        out = float(v)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def load_merged_json(path: Path, override_path: Path | None = None) -> dict[str, Any]:
    cfg = load_json(path)
    if override_path is not None:
        cfg = deep_update(cfg, load_json(override_path))
    return cfg


def build_train_cfg(
    *,
    config_path: Path,
    override_path: Path | None,
    train_override_path: Path | None,
    out_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rllib_cfg = load_merged_json(config_path, override_path)
    run_dir = out_dir / "resolved_runtime"
    run_dir.mkdir(parents=True, exist_ok=True)
    train_cfg = prepare_train_config(
        project_dir=PROJECT_DIR,
        run_dir=run_dir,
        rllib_cfg=rllib_cfg,
        train_override=train_override_path,
    )
    return rllib_cfg, train_cfg


def make_env(train_cfg: dict[str, Any], *, seed: int, worker_id: str) -> RllibTscRzipEnv:
    env_config = {
        "backend": "native",
        "seed": int(seed),
        "train_config": train_cfg,
        "run_id": "probe_controllability",
        "worker_id": worker_id,
        "finite_guard": {
            "enabled": True,
            "nonfinite_penalty": -10000.0,
            "terminate_on_nonfinite": True,
        },
    }
    return RllibTscRzipEnv(env_config)


def zero_action() -> np.ndarray:
    return np.zeros(14, dtype=np.float32)


def scenario_action(s: Scenario, step_idx: int) -> np.ndarray:
    a = zero_action()
    if s.kind == "zero":
        return a
    if step_idx >= int(s.pulse_steps):
        return a
    amp = float(s.amplitude) * float(s.sign)
    if s.kind == "individual":
        a[s.coil_index] = amp
        return a
    if s.kind == "pair":
        upper, lower = s.pair.split("/", 1)
        iu = TSC_NAME_TO_INDEX[upper]
        il = TSC_NAME_TO_INDEX[lower]
        if s.mode == "symmetric":
            a[iu] = amp
            a[il] = amp
        elif s.mode == "antisymmetric":
            a[iu] = amp
            a[il] = -amp
        else:
            raise ValueError(f"bad pair mode: {s.mode}")
        return a
    raise ValueError(f"unknown scenario kind: {s.kind}")


def make_scenarios(
    *, pulse_steps_list: list[int], amplitudes: list[float], include_individual: bool, include_pairs: bool
) -> list[Scenario]:
    scenarios: list[Scenario] = [Scenario("zero_action", "zero", 0, 0.0, 0)]
    if include_individual:
        for pulse in pulse_steps_list:
            for amp in amplitudes:
                for i, coil in enumerate(TSC_COIL_NAMES):
                    for sign in (+1, -1):
                        scenarios.append(
                            Scenario(
                                name=f"individual_{coil}_{'plus' if sign > 0 else 'minus'}_amp{amp:g}_{pulse}ms",
                                kind="individual",
                                pulse_steps=int(pulse),
                                amplitude=float(amp),
                                sign=int(sign),
                                coil=coil,
                                coil_index=i,
                            )
                        )
    if include_pairs:
        pairs = ["CS1U/CS1L", "CS2U/CS2L", "CS3U/CS3L", "CS4U/CS4L", "PF2U/PF2L", "PF3U/PF3L", "PF4U/PF4L"]
        for pulse in pulse_steps_list:
            for amp in amplitudes:
                for pair in pairs:
                    for mode in ("symmetric", "antisymmetric"):
                        for sign in (+1, -1):
                            scenarios.append(
                                Scenario(
                                    name=f"pair_{pair.replace('/', '-')}_{mode}_{'plus' if sign > 0 else 'minus'}_amp{amp:g}_{pulse}ms",
                                    kind="pair",
                                    pulse_steps=int(pulse),
                                    amplitude=float(amp),
                                    sign=int(sign),
                                    pair=pair,
                                    mode=mode,
                                )
                            )
    return scenarios


def extract_row(
    *, scenario: Scenario, step: int, action: np.ndarray, reward: float, terminated: bool, truncated: bool, info: dict[str, Any]
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scenario": scenario.name,
        "kind": scenario.kind,
        "pulse_steps": int(scenario.pulse_steps),
        "amplitude": float(scenario.amplitude),
        "sign": int(scenario.sign),
        "coil": scenario.coil,
        "coil_index": int(scenario.coil_index),
        "pair": scenario.pair,
        "mode": scenario.mode,
        "step": int(step),
        "reward": float(reward),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "action_mean_abs": float(np.mean(np.abs(action))),
        "action_max_abs": float(np.max(np.abs(action))),
    }
    for i, name in enumerate(TSC_COIL_NAMES):
        row[f"action_{name}"] = float(action[i])
    for k, v in info.items():
        if is_scalar(v):
            row[k] = v.item() if hasattr(v, "item") else v
    return row


def run_scenario_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Top-level worker function for ProcessPoolExecutor."""
    scenario = Scenario(**payload["scenario"])
    train_cfg = payload["train_cfg"]
    seed = int(payload["seed"])
    horizon_steps = int(payload["horizon_steps"])
    verbose = bool(payload.get("verbose", False))

    # Ensure child process also stays single-threaded.
    for name in [
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
        "TORCH_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS", "RAYON_NUM_THREADS",
    ]:
        os.environ[name] = "1"

    rows: list[dict[str, Any]] = []
    worker_id = f"probe_{slugify(scenario.name, 80)}_pid{os.getpid()}"
    env = None
    try:
        env = make_env(train_cfg, seed=seed, worker_id=worker_id)
        _, info = env.reset(seed=seed)
        rows.append(
            extract_row(scenario=scenario, step=0, action=zero_action(), reward=0.0, terminated=False, truncated=False, info=info)
        )
        for t in range(horizon_steps):
            action = scenario_action(scenario, t)
            _, reward, terminated, truncated, info = env.step(action)
            rows.append(
                extract_row(
                    scenario=scenario,
                    step=t + 1,
                    action=action,
                    reward=float(reward),
                    terminated=bool(terminated),
                    truncated=bool(truncated),
                    info=info,
                )
            )
            if terminated or truncated:
                if verbose:
                    print(f"{scenario.name} ended early at step {t + 1}", flush=True)
                break
        return {"ok": True, "scenario": scenario.name, "rows": rows, "error": ""}
    except Exception:
        return {"ok": False, "scenario": scenario.name, "rows": rows, "error": traceback.format_exc()}
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass


def weighted_score_from_row(row: pd.Series, weights: dict[str, float]) -> float:
    er = safe_float(row.get("R_error_norm", 0.0))
    ez = safe_float(row.get("Z_error_norm", 0.0))
    ei = safe_float(row.get("Ip_error_norm", 0.0))
    return float(math.sqrt(weights["R"] * er * er + weights["Z"] * ez * ez + weights["Ip"] * ei * ei))


def nearest_row(df: pd.DataFrame, scenario: str, step: int) -> pd.Series | None:
    sub = df[df["scenario"] == scenario]
    if sub.empty:
        return None
    exact = sub[sub["step"] == step]
    if not exact.empty:
        return exact.iloc[-1]
    before = sub[sub["step"] <= step]
    if not before.empty:
        return before.iloc[-1]
    return sub.iloc[0]


def summarize_rollouts(df: pd.DataFrame, *, response_steps: list[int], weights: dict[str, float], reach_tols: dict[str, float]) -> pd.DataFrame:
    zero_name = "zero_action"
    zero_rows = {step: nearest_row(df, zero_name, step) for step in response_steps}
    summary_rows: list[dict[str, Any]] = []
    for scenario, sub in df.groupby("scenario", sort=False):
        first = sub.iloc[0]
        last = sub.iloc[-1]
        s0 = weighted_score_from_row(first, weights)
        sf = weighted_score_from_row(last, weights)
        meta: dict[str, Any] = {
            "scenario": scenario,
            "kind": str(first.get("kind", "")),
            "pulse_steps": int(first.get("pulse_steps", 0)),
            "amplitude": float(first.get("amplitude", 0.0)),
            "sign": int(first.get("sign", 0)),
            "coil": str(first.get("coil", "")),
            "coil_index": int(first.get("coil_index", -1)),
            "pair": str(first.get("pair", "")),
            "mode": str(first.get("mode", "")),
            "n_rows": int(len(sub)),
            "final_step": int(last.get("step", -1)),
            "terminated": bool(last.get("terminated", False)),
            "truncated": bool(last.get("truncated", False)),
            "done_reason": str(last.get("done_reason", "")),
            "initial_score": s0,
            "final_score": sf,
            "score_improvement_final_vs_initial": s0 - sf,
            "final_R_error": safe_float(last.get("R_error", 0.0)),
            "final_Z_error": safe_float(last.get("Z_error", 0.0)),
            "final_Ip_error": safe_float(last.get("Ip_error", 0.0)),
            "final_velocity_norm": safe_float(last.get("velocity_norm", 0.0)),
            "final_vessel_current_total_a": safe_float(last.get("vessel_current_total_a", 0.0)),
            "final_vessel_current_abs_sum_a": safe_float(last.get("vessel_current_abs_sum_a", 0.0)),
            "final_action_mean_abs": safe_float(last.get("action_mean_abs", 0.0)),
            "max_abs_R_error": float(np.nanmax(np.abs(sub.get("R_error", pd.Series([np.nan])).to_numpy(dtype=float)))),
            "max_abs_Z_error": float(np.nanmax(np.abs(sub.get("Z_error", pd.Series([np.nan])).to_numpy(dtype=float)))),
            "max_abs_Ip_error": float(np.nanmax(np.abs(sub.get("Ip_error", pd.Series([np.nan])).to_numpy(dtype=float)))),
            "max_velocity_norm": float(np.nanmax(sub.get("velocity_norm", pd.Series([np.nan])).to_numpy(dtype=float))),
            "max_vessel_current_abs_sum_a": float(np.nanmax(sub.get("vessel_current_abs_sum_a", pd.Series([np.nan])).to_numpy(dtype=float))),
            "max_current_util": float(np.nanmax(sub.get("current_util_max", pd.Series([np.nan])).to_numpy(dtype=float))),
        }
        for step in response_steps:
            row = nearest_row(df, scenario, step)
            if row is None:
                continue
            score = weighted_score_from_row(row, weights)
            zero_row = zero_rows.get(step)
            zero_score = weighted_score_from_row(zero_row, weights) if zero_row is not None else math.nan
            prefix = f"at_{step}"
            meta.update(
                {
                    f"{prefix}_score": score,
                    f"{prefix}_score_improvement_vs_initial": s0 - score,
                    f"{prefix}_score_improvement_vs_zero": zero_score - score if math.isfinite(zero_score) else math.nan,
                    f"{prefix}_R_error": safe_float(row.get("R_error", 0.0)),
                    f"{prefix}_Z_error": safe_float(row.get("Z_error", 0.0)),
                    f"{prefix}_Ip_error": safe_float(row.get("Ip_error", 0.0)),
                    f"{prefix}_velocity_norm": safe_float(row.get("velocity_norm", 0.0)),
                    f"{prefix}_vessel_current_total_a": safe_float(row.get("vessel_current_total_a", 0.0)),
                    f"{prefix}_vessel_current_abs_sum_a": safe_float(row.get("vessel_current_abs_sum_a", 0.0)),
                    f"{prefix}_current_util_max": safe_float(row.get("current_util_max", 0.0)),
                    f"{prefix}_better_than_zero": bool(score < zero_score) if math.isfinite(zero_score) else False,
                    f"{prefix}_strict_reached": bool(
                        abs(safe_float(row.get("R_error", 1.0e99))) <= reach_tols["R"]
                        and abs(safe_float(row.get("Z_error", 1.0e99))) <= reach_tols["Z"]
                        and abs(safe_float(row.get("Ip_error", 1.0e99))) <= reach_tols["Ip"]
                        and safe_float(row.get("velocity_norm", 1.0e99)) <= reach_tols["velocity"]
                    ),
                }
            )
            for var in ("R", "Z", "Ip", "R_error", "Z_error", "Ip_error"):
                if zero_row is not None and var in row and var in zero_row:
                    meta[f"{prefix}_delta_{var}_vs_zero"] = safe_float(row.get(var, 0.0)) - safe_float(zero_row.get(var, 0.0))
        summary_rows.append(meta)
    return pd.DataFrame(summary_rows)


def build_response_matrix(summary: pd.DataFrame, *, response_step: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if summary.empty:
        return pd.DataFrame()
    individual = summary[summary["kind"] == "individual"]
    for pulse in sorted(individual["pulse_steps"].dropna().unique()):
        for amp in sorted(individual[individual["pulse_steps"] == pulse]["amplitude"].dropna().unique()):
            for coil in TSC_COIL_NAMES:
                sub = individual[(individual["pulse_steps"] == pulse) & (individual["amplitude"] == amp) & (individual["coil"] == coil)]
                if sub.empty:
                    continue
                plus = sub[sub["sign"] == 1]
                minus = sub[sub["sign"] == -1]
                if plus.empty or minus.empty:
                    continue
                p = plus.iloc[0]
                m = minus.iloc[0]
                row: dict[str, Any] = {
                    "pulse_steps": int(pulse),
                    "amplitude": float(amp),
                    "coil": coil,
                    "coil_index": int(p.get("coil_index", -1)),
                    "response_step": int(response_step),
                }
                for var in ("R", "Z", "Ip", "R_error", "Z_error", "Ip_error"):
                    col = f"at_{response_step}_delta_{var}_vs_zero"
                    if col in p and col in m:
                        row[f"central_d{var}_per_action"] = (safe_float(p[col]) - safe_float(m[col])) / (2.0 * float(amp))
                        row[f"plus_d{var}_vs_zero"] = safe_float(p[col])
                        row[f"minus_d{var}_vs_zero"] = safe_float(m[col])
                score_col = f"at_{response_step}_score_improvement_vs_zero"
                if score_col in p and score_col in m:
                    row["plus_score_improvement_vs_zero"] = safe_float(p[score_col], math.nan)
                    row["minus_score_improvement_vs_zero"] = safe_float(m[score_col], math.nan)
                    row["best_signed_score_improvement_vs_zero"] = max(
                        safe_float(p[score_col], -math.inf), safe_float(m[score_col], -math.inf)
                    )
                    row["best_sign_for_score"] = 1 if safe_float(p[score_col], -math.inf) >= safe_float(m[score_col], -math.inf) else -1
                rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["pulse_steps", "amplitude", "coil_index"])
    return out


def plot_zero_rollout(df: pd.DataFrame, out_dir: Path) -> None:
    zero = df[df["scenario"] == "zero_action"].copy()
    if zero.empty:
        return
    x = zero["step"].to_numpy(dtype=float)
    for ycols, ylabel, fname in [
        (["R_error", "Z_error"], "R/Z error [m]", "zero_rz_error.png"),
        (["Ip_error"], "Ip error [A]", "zero_ip_error.png"),
        (["velocity_norm"], "velocity norm", "zero_velocity_norm.png"),
        (["vessel_current_total_a", "vessel_current_abs_sum_a"], "vessel current [A]", "zero_vessel_current.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 5))
        for col in ycols:
            if col in zero:
                ax.plot(x, zero[col].to_numpy(dtype=float), label=col)
        ax.axvline(100, linestyle="--", linewidth=1, label="100 ms")
        ax.set_xlabel("step [1 ms]")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / fname, dpi=160)
        plt.close(fig)


def plot_response_heatmaps(response: pd.DataFrame, out_dir: Path, response_step: int) -> None:
    if response.empty:
        return
    for pulse in sorted(response["pulse_steps"].unique()):
        sub = response[response["pulse_steps"] == pulse].sort_values("coil_index")
        labels = sub["coil"].tolist()
        metrics = [
            ("central_dR_error_per_action", "dR_error/action [m]"),
            ("central_dZ_error_per_action", "dZ_error/action [m]"),
            ("central_dIp_error_per_action", "dIp_error/action [A]"),
            ("best_signed_score_improvement_vs_zero", "best score improvement vs zero"),
        ]
        for col, title in metrics:
            if col not in sub:
                continue
            values = sub[col].to_numpy(dtype=float)[None, :]
            fig, ax = plt.subplots(figsize=(12, 2.8))
            im = ax.imshow(values, aspect="auto")
            ax.set_yticks([0])
            ax.set_yticklabels([f"pulse={pulse} ms"])
            ax.set_xticks(np.arange(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")
            ax.set_title(f"{title} at step {response_step}")
            fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
            fig.tight_layout()
            fig.savefig(out_dir / f"response_{col}_{pulse}ms_at{response_step}.png", dpi=160)
            plt.close(fig)


def print_key_findings(summary: pd.DataFrame, response: pd.DataFrame, response_step: int, top_k: int) -> None:
    print("\n========== zero-action baseline ==========")
    zero = summary[summary["scenario"] == "zero_action"]
    if not zero.empty:
        z = zero.iloc[0]
        for col in [
            f"at_{response_step}_R_error", f"at_{response_step}_Z_error", f"at_{response_step}_Ip_error",
            f"at_{response_step}_score", "final_R_error", "final_Z_error", "final_Ip_error", "final_score",
            "final_vessel_current_abs_sum_a",
        ]:
            if col in z:
                print(f"{col:38s}: {z[col]}")
    if response.empty:
        return
    print(f"\n========== top {top_k} signed probes by score improvement at {response_step} ms ==========")
    signed_rows = []
    for _, row in response.iterrows():
        for sign_name, sign in [("plus", 1), ("minus", -1)]:
            signed_rows.append(
                {
                    "coil": row["coil"],
                    "pulse_steps": row["pulse_steps"],
                    "sign": sign,
                    "score_improvement_vs_zero": row.get(f"{sign_name}_score_improvement_vs_zero", np.nan),
                    "dR_error_vs_zero": row.get(f"{sign_name}_dR_error_vs_zero", np.nan),
                    "dZ_error_vs_zero": row.get(f"{sign_name}_dZ_error_vs_zero", np.nan),
                    "dIp_error_vs_zero": row.get(f"{sign_name}_dIp_error_vs_zero", np.nan),
                }
            )
    signed_df = pd.DataFrame(signed_rows).sort_values("score_improvement_vs_zero", ascending=False)
    with pd.option_context("display.max_rows", top_k, "display.width", 180):
        print(signed_df.head(top_k).to_string(index=False))
    print(f"\n========== strongest central finite-difference responses at {response_step} ms ==========")
    for col in ["central_dR_error_per_action", "central_dZ_error_per_action", "central_dIp_error_per_action"]:
        if col not in response:
            continue
        tmp = response.copy()
        tmp["abs_response"] = np.abs(tmp[col].to_numpy(dtype=float))
        tmp = tmp.sort_values("abs_response", ascending=False)
        print(f"\n{col}:")
        with pd.option_context("display.max_rows", min(top_k, 14), "display.width", 180):
            print(tmp[["coil", "pulse_steps", col]].head(min(top_k, 14)).to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run zero-action and fixed-action response probes on native TSC env.")
    parser.add_argument("--config", default="configs/rllib_sac.json")
    parser.add_argument("--override", default=None)
    parser.add_argument("--train-override", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--horizon-steps", type=int, default=250)
    parser.add_argument("--response-steps", default="20,50,100,150,250")
    parser.add_argument("--response-step", type=int, default=100)
    parser.add_argument("--pulse-steps", default="20,50,100")
    parser.add_argument("--amplitudes", default="1.0")
    parser.add_argument("--skip-individual", action="store_true")
    parser.add_argument("--include-pairs", action="store_true")
    parser.add_argument("--num-workers", type=int, default=1, help="Number of probe scenarios to run concurrently. Start with 8 or 16.")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_DIR / config_path
    override_path = Path(args.override) if args.override else None
    if override_path is not None and not override_path.is_absolute():
        override_path = PROJECT_DIR / override_path
    train_override_path = Path(args.train_override) if args.train_override else None
    if train_override_path is not None and not train_override_path.is_absolute():
        train_override_path = PROJECT_DIR / train_override_path

    if args.out_dir is None:
        out_dir = PROJECT_DIR / "probe_results" / f"controllability_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = PROJECT_DIR / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    response_steps = sorted(set(parse_int_list(args.response_steps) + [int(args.response_step)]))
    pulse_steps_list = parse_int_list(args.pulse_steps)
    amplitudes = parse_float_list(args.amplitudes)

    _, train_cfg = build_train_cfg(
        config_path=config_path,
        override_path=override_path,
        train_override_path=train_override_path,
        out_dir=out_dir,
    )

    reward_cfg = train_cfg.get("reward", {})
    weights = {"R": float(reward_cfg.get("w_r", 1.0)), "Z": float(reward_cfg.get("w_z", 1.0)), "Ip": float(reward_cfg.get("w_ip", 1.0))}
    reach_tols = {
        "R": float(reward_cfg.get("reach_success_r_tol", 0.008)),
        "Z": float(reward_cfg.get("reach_success_z_tol", 0.008)),
        "Ip": float(reward_cfg.get("reach_success_ip_tol", 800.0)),
        "velocity": float(reward_cfg.get("reach_success_velocity_norm_max", 0.8)),
    }

    scenarios = make_scenarios(
        pulse_steps_list=pulse_steps_list,
        amplitudes=amplitudes,
        include_individual=not args.skip_individual,
        include_pairs=bool(args.include_pairs),
    )

    metadata = {
        "config": str(config_path), "override": str(override_path) if override_path else None,
        "train_override": str(train_override_path) if train_override_path else None,
        "out_dir": str(out_dir), "seed": int(args.seed), "horizon_steps": int(args.horizon_steps),
        "response_steps": response_steps, "response_step": int(args.response_step),
        "pulse_steps": pulse_steps_list, "amplitudes": amplitudes,
        "include_individual": not args.skip_individual, "include_pairs": bool(args.include_pairs),
        "num_workers": int(args.num_workers), "weights": weights, "reach_tols": reach_tols,
        "num_scenarios": len(scenarios), "coil_order": TSC_COIL_NAMES,
    }
    (out_dir / "probe_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "scenarios.json").write_text(json.dumps([asdict(s) for s in scenarios], indent=2, ensure_ascii=False), encoding="utf-8")

    print("========== TSC controllability probe ==========")
    print(f"project_dir       = {PROJECT_DIR}")
    print(f"out_dir           = {out_dir}")
    print(f"seed              = {args.seed}")
    print(f"horizon_steps     = {args.horizon_steps}")
    print(f"response_steps    = {response_steps}")
    print(f"pulse_steps       = {pulse_steps_list}")
    print(f"amplitudes        = {amplitudes}")
    print(f"num_scenarios     = {len(scenarios)}")
    print(f"num_workers       = {args.num_workers}")
    print(f"include_pairs     = {args.include_pairs}")
    print("TSC action order  = " + ", ".join(TSC_COIL_NAMES))
    print("===============================================")

    tasks = [
        {"scenario": asdict(s), "train_cfg": train_cfg, "seed": int(args.seed), "horizon_steps": int(args.horizon_steps), "verbose": bool(args.verbose)}
        for s in scenarios
    ]

    all_rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    num_workers = max(1, int(args.num_workers))

    if num_workers == 1:
        for i, task in enumerate(tasks, start=1):
            print(f"[{i:04d}/{len(tasks):04d}] {task['scenario']['name']}", flush=True)
            result = run_scenario_worker(task)
            if result["ok"]:
                all_rows.extend(result["rows"])
            else:
                failures.append({"scenario": result["scenario"], "error": result["error"]})
                print(f"FAILED {result['scenario']}\n{result['error']}", flush=True)
    else:
        print(f"Running scenarios in parallel with ProcessPoolExecutor(max_workers={num_workers})", flush=True)
        with ProcessPoolExecutor(max_workers=num_workers) as ex:
            future_to_name = {ex.submit(run_scenario_worker, task): task["scenario"]["name"] for task in tasks}
            done_count = 0
            for fut in as_completed(future_to_name):
                name = future_to_name[fut]
                done_count += 1
                try:
                    result = fut.result()
                except Exception:
                    result = {"ok": False, "scenario": name, "rows": [], "error": traceback.format_exc()}
                if result["ok"]:
                    all_rows.extend(result["rows"])
                    print(f"[{done_count:04d}/{len(tasks):04d}] done {name}", flush=True)
                else:
                    failures.append({"scenario": result["scenario"], "error": result["error"]})
                    print(f"[{done_count:04d}/{len(tasks):04d}] FAILED {name}\n{result['error']}", flush=True)

    failures_path = out_dir / "failures.json"
    failures_path.write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")
    if failures:
        print(f"WARNING: {len(failures)} scenarios failed. See {failures_path}")

    rollouts = pd.DataFrame(all_rows)
    rollouts_path = out_dir / "rollouts.csv"
    rollouts.to_csv(rollouts_path, index=False)

    if rollouts.empty:
        raise RuntimeError("No rollout rows were produced. Check failures.json and logs.")

    summary = summarize_rollouts(rollouts, response_steps=response_steps, weights=weights, reach_tols=reach_tols)
    summary_path = out_dir / "summary.csv"
    summary.to_csv(summary_path, index=False)

    response = build_response_matrix(summary, response_step=int(args.response_step))
    response_path = out_dir / "response_matrix.csv"
    response.to_csv(response_path, index=False)

    if not args.no_plots:
        plot_zero_rollout(rollouts, out_dir)
        plot_response_heatmaps(response, out_dir, int(args.response_step))

    print_key_findings(summary, response, int(args.response_step), int(args.top_k))
    print("\nSaved:")
    print(f"  {rollouts_path}")
    print(f"  {summary_path}")
    print(f"  {response_path}")
    print(f"  {out_dir / 'probe_metadata.json'}")
    print(f"  {failures_path}")
    if not args.no_plots:
        print(f"  plots: {out_dir}/*.png")


if __name__ == "__main__":
    main()
