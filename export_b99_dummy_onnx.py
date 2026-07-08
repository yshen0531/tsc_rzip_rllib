#!/usr/bin/env python3
"""
Export a dummy B99/B99.x recurrent policy to ONNX for deployment-side I/O testing.

Purpose
-------
This is NOT a trained controller.  It is a deterministic dummy-weight model that
keeps the deployment interface stable:

Inputs:
  obs   : float32[B, 53]
  h_in  : float32[1, B, 128]
  c_in  : float32[1, B, 128]

Outputs:
  action_norm     : float32[B, 14], normalized policy action in [-1, 1]
  delta_current_a : float32[B, 14], per-step coil current delta in A, action_norm * 3.0
  h_out           : float32[1, B, 128]
  c_out           : float32[1, B, 128]

The model contains an LSTM so the future trained recurrent policy can keep a
similar step-by-step inference contract.  All LSTM/input weights are zeroed;
the action head bias is set so zero-state inference returns the known test vector.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
import torch.nn as nn


OBS_DIM = 53
ACTION_DIM = 14
HIDDEN_SIZE = 128
NUM_LAYERS = 1
MAX_DELTA_CURRENT_A = 3.0  # 0.3 A/ms * 10 ms

COIL_ORDER: List[str] = [
    "CS1U", "CS1L", "CS2U", "CS2L", "CS3U", "CS3L", "CS4U", "CS4L",
    "PF2U", "PF2L", "PF3U", "PF3L", "PF4U", "PF4L",
]

# Chosen to make deployment-side output-order tests obvious.
TEST_ACTION_NORM = np.array(
    [[-0.70, -0.60, -0.50, -0.40, -0.30, -0.20, -0.10,
       0.10,  0.20,  0.30,  0.40,  0.50,  0.60,  0.70]],
    dtype=np.float32,
)


def atanh_np(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    x = np.clip(x, -0.999999, 0.999999)
    return 0.5 * np.log((1.0 + x) / (1.0 - x))


class B99DummyRecurrentPolicy(nn.Module):
    def __init__(
        self,
        obs_dim: int = OBS_DIM,
        action_dim: int = ACTION_DIM,
        hidden_size: int = HIDDEN_SIZE,
        max_delta_current_a: float = MAX_DELTA_CURRENT_A,
        test_action_norm: np.ndarray = TEST_ACTION_NORM,
    ) -> None:
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.hidden_size = int(hidden_size)
        self.lstm = nn.LSTM(
            input_size=self.obs_dim,
            hidden_size=self.hidden_size,
            num_layers=NUM_LAYERS,
            batch_first=True,
        )
        self.action_head = nn.Linear(self.hidden_size, self.action_dim)
        self.register_buffer(
            "max_delta_current_a",
            torch.tensor(float(max_delta_current_a), dtype=torch.float32),
        )
        self._init_dummy_weights(test_action_norm)

    def _init_dummy_weights(self, test_action_norm: np.ndarray) -> None:
        # Zero everything, then set action bias. With zero h/c states, h_out/c_out
        # are zero and action is exactly tanh(action_head.bias).
        for p in self.parameters():
            nn.init.zeros_(p)
        bias = torch.tensor(atanh_np(test_action_norm.reshape(-1)), dtype=torch.float32)
        with torch.no_grad():
            self.action_head.bias.copy_(bias)

    def forward(
        self,
        obs: torch.Tensor,
        h_in: torch.Tensor,
        c_in: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        # obs: [B, 53]
        x = obs.unsqueeze(1)  # [B, T=1, 53]
        y, (h_out, c_out) = self.lstm(x, (h_in, c_in))
        logits = self.action_head(y[:, -1, :])
        action_norm = torch.tanh(logits)
        delta_current_a = action_norm * self.max_delta_current_a
        return action_norm, delta_current_a, h_out, c_out


def make_test_vectors(batch: int = 1) -> Dict[str, np.ndarray]:
    obs = np.zeros((batch, OBS_DIM), dtype=np.float32)
    h0 = np.zeros((NUM_LAYERS, batch, HIDDEN_SIZE), dtype=np.float32)
    c0 = np.zeros((NUM_LAYERS, batch, HIDDEN_SIZE), dtype=np.float32)
    action = np.repeat(TEST_ACTION_NORM, batch, axis=0).astype(np.float32)
    delta = action * np.float32(MAX_DELTA_CURRENT_A)
    h1 = np.zeros_like(h0)
    c1 = np.zeros_like(c0)
    return {
        "obs": obs,
        "h_in": h0,
        "c_in": c0,
        "expected_action_norm": action,
        "expected_delta_current_a": delta,
        "expected_h_out": h1,
        "expected_c_out": c1,
    }


def write_test_files(out_dir: Path, batch: int = 1) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    vectors = make_test_vectors(batch=batch)
    np.savez(out_dir / "b99_dummy_test_vectors.npz", **vectors)

    spec = {
        "model_kind": "B99 dummy recurrent policy ONNX I/O test model",
        "note": "Dummy weights only. This is not a trained controller.",
        "obs_dim": OBS_DIM,
        "action_dim": ACTION_DIM,
        "hidden_size": HIDDEN_SIZE,
        "num_layers": NUM_LAYERS,
        "max_delta_current_a": MAX_DELTA_CURRENT_A,
        "coil_order": COIL_ORDER,
        "inputs": [
            {"name": "obs", "dtype": "float32", "shape": ["batch", OBS_DIM], "description": "B99 policy observation vector. Dummy model ignores values; real model must use training obs order."},
            {"name": "h_in", "dtype": "float32", "shape": [NUM_LAYERS, "batch", HIDDEN_SIZE], "description": "LSTM hidden state input. Use zeros at episode start."},
            {"name": "c_in", "dtype": "float32", "shape": [NUM_LAYERS, "batch", HIDDEN_SIZE], "description": "LSTM cell state input. Use zeros at episode start."},
        ],
        "outputs": [
            {"name": "action_norm", "dtype": "float32", "shape": ["batch", ACTION_DIM], "description": "Normalized action in [-1, 1], coil order below."},
            {"name": "delta_current_a", "dtype": "float32", "shape": ["batch", ACTION_DIM], "description": "Per-step current increment in A = action_norm * 3.0."},
            {"name": "h_out", "dtype": "float32", "shape": [NUM_LAYERS, "batch", HIDDEN_SIZE], "description": "Next LSTM hidden state."},
            {"name": "c_out", "dtype": "float32", "shape": [NUM_LAYERS, "batch", HIDDEN_SIZE], "description": "Next LSTM cell state."},
        ],
        "test_case_zero_state_batch1": {
            "input_shapes": {k: list(v.shape) for k, v in vectors.items() if k in {"obs", "h_in", "c_in"}},
            "expected_action_norm": vectors["expected_action_norm"].tolist(),
            "expected_delta_current_a": vectors["expected_delta_current_a"].tolist(),
            "expected_h_out": "all zeros, shape [1, batch, 128]",
            "expected_c_out": "all zeros, shape [1, batch, 128]",
            "tolerance": "absolute error <= 1e-5",
        },
        "output_channel_mapping": [
            {"index": i, "coil": name, "expected_action_norm": float(TEST_ACTION_NORM[0, i]), "expected_delta_current_a": float(TEST_ACTION_NORM[0, i] * MAX_DELTA_CURRENT_A)}
            for i, name in enumerate(COIL_ORDER)
        ],
    }
    with open(out_dir / "b99_dummy_io_spec.json", "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)


def export_onnx(out_path: Path, opset: int = 17, batch: int = 1) -> None:
    model = B99DummyRecurrentPolicy().eval()
    vectors = make_test_vectors(batch=batch)
    obs = torch.from_numpy(vectors["obs"])
    h_in = torch.from_numpy(vectors["h_in"])
    c_in = torch.from_numpy(vectors["c_in"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        (obs, h_in, c_in),
        str(out_path),
        export_params=True,
        opset_version=opset,
        do_constant_folding=True,
        input_names=["obs", "h_in", "c_in"],
        output_names=["action_norm", "delta_current_a", "h_out", "c_out"],
        dynamic_axes={
            "obs": {0: "batch"},
            "h_in": {1: "batch"},
            "c_in": {1: "batch"},
            "action_norm": {0: "batch"},
            "delta_current_a": {0: "batch"},
            "h_out": {1: "batch"},
            "c_out": {1: "batch"},
        },
    )


def validate_with_onnxruntime(onnx_path: Path, test_npz: Path) -> None:
    try:
        import onnxruntime as ort
    except Exception as exc:
        print(f"[warn] onnxruntime not installed, skip runtime validation: {exc}")
        return
    data = np.load(test_npz)
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    outputs = sess.run(
        ["action_norm", "delta_current_a", "h_out", "c_out"],
        {"obs": data["obs"], "h_in": data["h_in"], "c_in": data["c_in"]},
    )
    names = ["expected_action_norm", "expected_delta_current_a", "expected_h_out", "expected_c_out"]
    for arr, exp_name in zip(outputs, names):
        exp = data[exp_name]
        max_err = float(np.max(np.abs(arr - exp)))
        print(f"validate {exp_name}: max_abs_err={max_err:.8g}")
        if max_err > 1e-5:
            raise RuntimeError(f"Validation failed for {exp_name}: max_err={max_err}")
    print("ONNX Runtime validation passed.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("b99_dummy_policy.onnx"), help="ONNX output path")
    ap.add_argument("--test-dir", type=Path, default=Path("b99_dummy_onnx_test"), help="Directory for test vectors/spec")
    ap.add_argument("--opset", type=int, default=17)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--validate", action="store_true", help="Run onnxruntime validation if installed")
    args = ap.parse_args()

    write_test_files(args.test_dir, batch=args.batch)
    export_onnx(args.out, opset=args.opset, batch=args.batch)
    print(f"Wrote ONNX: {args.out}")
    print(f"Wrote test vectors: {args.test_dir / 'b99_dummy_test_vectors.npz'}")
    print(f"Wrote I/O spec: {args.test_dir / 'b99_dummy_io_spec.json'}")
    if args.validate:
        validate_with_onnxruntime(args.out, args.test_dir / "b99_dummy_test_vectors.npz")


if __name__ == "__main__":
    main()
