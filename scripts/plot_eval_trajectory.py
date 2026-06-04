#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plot deterministic eval trajectories for selected MPO checkpoints.

Example:
  python scripts/plot_eval_trajectory.py \
    --csv75 eval_results/b86_iter_000075_final_det.csv \
    --csv100 eval_results/b86_iter_000100_final_det.csv \
    --outdir eval_results/b86_trajectory_compare_iter75_100 \
    --target-r 0.75 \
    --target-z 0.0 \
    --target-ip 29779.724 \
    --dt-ms 1

Outputs:
  trajectory_merged.csv
  trajectory_summary.csv
  trajectory_errors.png
  trajectory_actuals.png
  trajectory_normalized_score.png
  trajectory_action_vessel.png
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


DEFAULT_R_TOL_REF = 0.05
DEFAULT_Z_TOL_REF = 0.05
DEFAULT_IP_TOL_REF = 3000.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--csv75", type=str, required=True, help="CSV path for iter_000075 eval trajectory.")
    p.add_argument("--csv100", type=str, required=True, help="CSV path for iter_000100 eval trajectory.")
    p.add_argument("--outdir", type=str, required=True, help="Output directory.")
    p.add_argument("--target-r", type=float, default=0.75)
    p.add_argument("--target-z", type=float, default=0.0)
    p.add_argument("--target-ip", type=float, default=29779.724)
    p.add_argument("--dt-ms", type=float, default=1.0)

    # References used only for normalized plotting / scoring.
    p.add_argument("--r-ref", type=float, default=DEFAULT_R_TOL_REF)
    p.add_argument("--z-ref", type=float, default=DEFAULT_Z_TOL_REF)
    p.add_argument("--ip-ref", type=float, default=DEFAULT_IP_TOL_REF)

    # Mark approximate final-stage reach deadline if useful.
    p.add_argument("--reach-deadline-step", type=int, default=100)
    p.add_argument("--hold-start-step", type=int, default=120)

    return p.parse_args()


def require_columns(df: pd.DataFrame, path: Path) -> None:
    required = ["step", "R_error", "Z_error", "Ip_error"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}. Existing columns: {list(df.columns)}")


def load_one(path: str, label: str, args: argparse.Namespace) -> pd.DataFrame:
    f = Path(path)
    if not f.exists():
        raise FileNotFoundError(f"Missing input file: {f}")

    df = pd.read_csv(f)
    require_columns(df, f)

    # Usually eval deterministic has only episode 0, but keep robust.
    if "episode" in df.columns:
        df = df[df["episode"] == df["episode"].min()].copy()

    df = df.sort_values("step").reset_index(drop=True)
    df["checkpoint"] = label
    df["time_ms"] = df["step"].astype(float) * args.dt_ms

    # Actual reconstructed values.
    df["R"] = args.target_r + df["R_error"]
    df["Z"] = args.target_z + df["Z_error"]
    df["Ip"] = args.target_ip + df["Ip_error"]

    # Normalized absolute errors and a balanced score.
    df["R_abs_norm"] = df["R_error"].abs() / args.r_ref
    df["Z_abs_norm"] = df["Z_error"].abs() / args.z_ref
    df["Ip_abs_norm"] = df["Ip_error"].abs() / args.ip_ref
    df["max_abs_norm_error"] = df[["R_abs_norm", "Z_abs_norm", "Ip_abs_norm"]].max(axis=1)
    df["sum_abs_norm_error"] = df["R_abs_norm"] + df["Z_abs_norm"] + df["Ip_abs_norm"]

    if "mean_abs_action" not in df.columns:
        df["mean_abs_action"] = np.nan
    if "max_abs_action" not in df.columns:
        df["max_abs_action"] = np.nan
    if "vessel_current_total_a" not in df.columns:
        df["vessel_current_total_a"] = np.nan
    if "vessel_current_abs_sum_a" not in df.columns:
        df["vessel_current_abs_sum_a"] = np.nan

    return df


def first_zero_crossing_step(y: np.ndarray, step: np.ndarray) -> float:
    if len(y) < 2:
        return np.nan
    s = np.sign(y)
    for i in range(1, len(y)):
        if s[i] == 0:
            return float(step[i])
        if s[i - 1] == 0:
            return float(step[i - 1])
        if s[i] != s[i - 1]:
            return float(step[i])
    return np.nan


def first_step_after_best_grows(
    score: np.ndarray,
    step: np.ndarray,
    rel_growth: float = 0.25,
    abs_growth: float = 0.5,
) -> float:
    """
    Find first step after the best score where score has grown enough.
    This is a simple marker for '开始偏离/变坏'.
    """
    if len(score) == 0:
        return np.nan
    i_best = int(np.nanargmin(score))
    best = float(score[i_best])
    threshold = best * (1.0 + rel_growth) + abs_growth
    for j in range(i_best + 1, len(score)):
        if score[j] > threshold:
            return float(step[j])
    return np.nan


def summarize_one(df: pd.DataFrame, label: str) -> Dict[str, float | str]:
    step = df["step"].to_numpy(dtype=float)

    out: Dict[str, float | str] = {"checkpoint": label}
    out["n_steps"] = int(len(df))
    out["final_step"] = float(step[-1])

    for name in ["R_error", "Z_error", "Ip_error"]:
        y = df[name].to_numpy(dtype=float)
        abs_y = np.abs(y)
        i_best = int(np.nanargmin(abs_y))
        i_max = int(np.nanargmax(abs_y))

        out[f"{name}_start"] = float(y[0])
        out[f"{name}_final"] = float(y[-1])
        out[f"{name}_best_abs"] = float(abs_y[i_best])
        out[f"{name}_best_abs_step"] = float(step[i_best])
        out[f"{name}_max_abs"] = float(abs_y[i_max])
        out[f"{name}_max_abs_step"] = float(step[i_max])
        out[f"{name}_zero_cross_step"] = first_zero_crossing_step(y, step)

    score = df["sum_abs_norm_error"].to_numpy(dtype=float)
    i_score = int(np.nanargmin(score))
    out["score_best"] = float(score[i_score])
    out["score_best_step"] = float(step[i_score])
    out["score_final"] = float(score[-1])
    out["score_diverge_step_after_best"] = first_step_after_best_grows(score, step)

    max_score = df["max_abs_norm_error"].to_numpy(dtype=float)
    i_max_score = int(np.nanargmin(max_score))
    out["max_norm_error_best"] = float(max_score[i_max_score])
    out["max_norm_error_best_step"] = float(step[i_max_score])
    out["max_norm_error_final"] = float(max_score[-1])

    out["mean_abs_action_final"] = float(df["mean_abs_action"].iloc[-1])
    out["mean_abs_action_mean"] = float(df["mean_abs_action"].mean())
    out["max_abs_action_final"] = float(df["max_abs_action"].iloc[-1])
    out["vessel_total_final_a"] = float(df["vessel_current_total_a"].iloc[-1])
    out["vessel_abs_sum_final_a"] = float(df["vessel_current_abs_sum_a"].iloc[-1])

    return out


def add_stage_lines(ax: plt.Axes, args: argparse.Namespace) -> None:
    ax.axvline(args.reach_deadline_step * args.dt_ms, linestyle="--", linewidth=1.0)
    ax.axvline(args.hold_start_step * args.dt_ms, linestyle=":", linewidth=1.0)


def plot_errors(merged: pd.DataFrame, outdir: Path, args: argparse.Namespace) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

    specs = [
        ("R_error", "R error [m]", args.r_ref),
        ("Z_error", "Z error [m]", args.z_ref),
        ("Ip_error", "Ip error [A]", args.ip_ref),
    ]

    for ax, (col, ylabel, ref) in zip(axes, specs):
        for label, g in merged.groupby("checkpoint"):
            ax.plot(g["time_ms"], g[col], label=label)
        ax.axhline(0.0, linewidth=1.0)
        ax.axhline(ref, linestyle="--", linewidth=0.8)
        ax.axhline(-ref, linestyle="--", linewidth=0.8)
        add_stage_lines(ax, args)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[0].legend(loc="best")
    axes[-1].set_xlabel("time [ms]")
    fig.suptitle("B86 deterministic final eval: R/Z/Ip errors")
    fig.tight_layout()
    fig.savefig(outdir / "trajectory_errors.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_actuals(merged: pd.DataFrame, outdir: Path, args: argparse.Namespace) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

    specs = [
        ("R", "R [m]", args.target_r),
        ("Z", "Z [m]", args.target_z),
        ("Ip", "Ip [A]", args.target_ip),
    ]

    for ax, (col, ylabel, target) in zip(axes, specs):
        for label, g in merged.groupby("checkpoint"):
            ax.plot(g["time_ms"], g[col], label=label)
        ax.axhline(target, linewidth=1.0)
        add_stage_lines(ax, args)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[0].legend(loc="best")
    axes[-1].set_xlabel("time [ms]")
    fig.suptitle("B86 deterministic final eval: actual R/Z/Ip")
    fig.tight_layout()
    fig.savefig(outdir / "trajectory_actuals.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_normalized_score(merged: pd.DataFrame, outdir: Path, args: argparse.Namespace) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))

    for label, g in merged.groupby("checkpoint"):
        ax.plot(g["time_ms"], g["sum_abs_norm_error"], label=f"{label}: sum")
        ax.plot(g["time_ms"], g["max_abs_norm_error"], linestyle="--", label=f"{label}: max")

    add_stage_lines(ax, args)
    ax.set_xlabel("time [ms]")
    ax.set_ylabel("normalized error score")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_title("Normalized error score: sum and max of |R|, |Z|, |Ip|")
    fig.tight_layout()
    fig.savefig(outdir / "trajectory_normalized_score.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_action_vessel(merged: pd.DataFrame, outdir: Path, args: argparse.Namespace) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)

    specs = [
        ("mean_abs_action", "mean |action|"),
        ("max_abs_action", "max |action|"),
        ("vessel_current_total_a", "vessel signed total [A]"),
        ("vessel_current_abs_sum_a", "vessel abs sum [A]"),
    ]

    for ax, (col, ylabel) in zip(axes, specs):
        for label, g in merged.groupby("checkpoint"):
            ax.plot(g["time_ms"], g[col], label=label)
        add_stage_lines(ax, args)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[0].legend(loc="best")
    axes[-1].set_xlabel("time [ms]")
    fig.suptitle("B86 deterministic final eval: action and vessel current")
    fig.tight_layout()
    fig.savefig(outdir / "trajectory_action_vessel.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df75 = load_one(args.csv75, "iter_000075", args)
    df100 = load_one(args.csv100, "iter_000100", args)

    merged = pd.concat([df75, df100], ignore_index=True)
    merged.to_csv(outdir / "trajectory_merged.csv", index=False)

    summary_rows: List[Dict[str, float | str]] = [
        summarize_one(df75, "iter_000075"),
        summarize_one(df100, "iter_000100"),
    ]
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(outdir / "trajectory_summary.csv", index=False)

    plot_errors(merged, outdir, args)
    plot_actuals(merged, outdir, args)
    plot_normalized_score(merged, outdir, args)
    plot_action_vessel(merged, outdir, args)

    print(f"[OK] Saved outputs to: {outdir}")
    print(f"  - {outdir / 'trajectory_merged.csv'}")
    print(f"  - {outdir / 'trajectory_summary.csv'}")
    print(f"  - {outdir / 'trajectory_errors.png'}")
    print(f"  - {outdir / 'trajectory_actuals.png'}")
    print(f"  - {outdir / 'trajectory_normalized_score.png'}")
    print(f"  - {outdir / 'trajectory_action_vessel.png'}")


if __name__ == "__main__":
    main()
