"""Fair causal plasma-dynamics candidates for the frozen 1 ms NR2."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np
import torch
from torch import nn

PLASMA_DIM = 3
CURRENT_DIM = 14
ACTION_DIM = 14
FRAME_DIM = PLASMA_DIM + CURRENT_DIM + ACTION_DIM + 2
HISTORY_STEPS = 8
POINT_SCALES = np.asarray([0.0015, 0.0015, 150.0], dtype=float)
SEEDS = (1701, 1702, 1703, 1704, 1705)


def q0_readback_bias(
    source_readback: Sequence[Any], q0_command: Sequence[Any]
) -> tuple[Any, ...]:
    """Return the non-fitted readback offset in the exact q0 coordinate."""
    if len(source_readback) != CURRENT_DIM or len(q0_command) != CURRENT_DIM:
        raise ValueError("q0 readback bias requires fourteen coils")
    return tuple(readback - command for readback, command in zip(source_readback, q0_command))


@dataclass(frozen=True)
class Normalizer:
    frame_mean: tuple[float, ...]
    frame_scale: tuple[float, ...]

    @classmethod
    def fit(cls, trajectories: Sequence[dict[str, Any]]) -> "Normalizer":
        rows = np.asarray([frame for row in trajectories for frame in row["frames"]], dtype=float)
        scale = np.maximum(rows.std(axis=0), np.asarray([1e-6,1e-6,1.0]+[1e-4]*28+[1e-6,1e-6]))
        return cls(tuple(rows.mean(axis=0)), tuple(scale))

    def encode(self, frame: np.ndarray) -> np.ndarray:
        return (np.asarray(frame)-np.asarray(self.frame_mean))/np.asarray(self.frame_scale)

    def to_dict(self) -> dict[str, Any]:
        return {"frame_mean":list(self.frame_mean),"frame_scale":list(self.frame_scale)}

    @classmethod
    def from_dict(cls,payload:dict[str,Any])->"Normalizer":
        return cls(tuple(payload["frame_mean"]),tuple(payload["frame_scale"]))


def history_feature(history: Sequence[np.ndarray], normalizer: Normalizer) -> np.ndarray:
    selected=list(history[-HISTORY_STEPS:])
    if not selected: raise ValueError("causal history is empty")
    while len(selected)<HISTORY_STEPS: selected.insert(0,selected[0])
    return np.concatenate([normalizer.encode(value) for value in selected])


@dataclass
class ARXModel:
    normalizer: Normalizer
    coefficient: np.ndarray

    def predict_delta(self,history:Sequence[np.ndarray])->np.ndarray:
        return np.concatenate(([1.0],history_feature(history,self.normalizer)))@self.coefficient*POINT_SCALES


def fit_arx(trajectories:Sequence[dict[str,Any]],normalizer:Normalizer,ridge:float,indices:Sequence[int]|None=None)->ARXModel:
    rows=[]; targets=[]; selected=range(len(trajectories)) if indices is None else indices
    for index in selected:
        history=[]; trajectory=trajectories[index]
        for step,frame in enumerate(trajectory["frames"]):
            history.append(np.asarray(frame)); rows.append(np.concatenate(([1.0],history_feature(history,normalizer))))
            targets.append((np.asarray(trajectory["plasma"])[step+1]-np.asarray(trajectory["plasma"])[step])/POINT_SCALES)
    design=np.asarray(rows); target=np.asarray(targets); penalty=np.eye(design.shape[1])*ridge; penalty[0,0]=0
    coefficient=np.linalg.lstsq(design.T@design+penalty,design.T@target,rcond=None)[0]
    return ARXModel(normalizer,coefficient)


class RecurrentResidual(nn.Module):
    def __init__(self,kind:str,width:int):
        super().__init__(); self.sequence=nn.GRU(FRAME_DIM,width,batch_first=True) if kind=="gru" else nn.LSTM(FRAME_DIM,width,batch_first=True); self.head=nn.Linear(width,PLASMA_DIM)
    def forward(self,values:torch.Tensor)->torch.Tensor: return self.head(self.sequence(values)[0])


class CausalTCNResidual(nn.Module):
    def __init__(self,width:int):
        super().__init__(); self.c1=nn.Conv1d(FRAME_DIM,width,2); self.c2=nn.Conv1d(width,width,2,dilation=2); self.head=nn.Linear(width,PLASMA_DIM)
    def forward(self,values:torch.Tensor)->torch.Tensor:
        x=values.transpose(1,2); x=torch.tanh(self.c1(torch.nn.functional.pad(x,(1,0)))); x=torch.tanh(self.c2(torch.nn.functional.pad(x,(2,0)))); return self.head(x.transpose(1,2))


def build_residual(kind:str,width:int)->nn.Module: return CausalTCNResidual(width) if kind=="tcn" else RecurrentResidual(kind,width)
def parameter_count(model:nn.Module)->int: return sum(value.numel() for value in model.parameters())


def fit_residual(kind:str,width:int,trajectories:Sequence[dict[str,Any]],normalizer:Normalizer,base:ARXModel,seed:int,max_epochs:int=2000,patience:int=200)->nn.Module:
    inputs=[]; targets=[]
    for trajectory in trajectories:
        history=[]; row_inputs=[]; row_targets=[]; plasma=np.asarray(trajectory["plasma"])
        for step,frame in enumerate(trajectory["frames"]):
            history.append(np.asarray(frame)); row_inputs.append(normalizer.encode(frame)); actual=plasma[step+1]-plasma[step]; row_targets.append((actual-base.predict_delta(history))/POINT_SCALES)
        inputs.append(row_inputs); targets.append(row_targets)
    torch.manual_seed(seed); torch.use_deterministic_algorithms(True); model=build_residual(kind,width)
    if parameter_count(model)>10_000: raise ValueError("residual candidate exceeds 10,000 parameters")
    x=torch.tensor(np.asarray(inputs),dtype=torch.float32); y=torch.tensor(np.asarray(targets),dtype=torch.float32); optimizer=torch.optim.Adam(model.parameters(),lr=1e-3); best=math.inf; best_state=None; stale=0
    for _ in range(max_epochs):
        optimizer.zero_grad(); loss=torch.mean((model(x)-y)**2); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); optimizer.step(); value=float(loss.detach())
        if value<best-1e-8: best=value; best_state={k:v.detach().clone() for k,v in model.state_dict().items()}; stale=0
        else: stale+=1
        if stale>=patience: break
    if best_state is None: raise RuntimeError("residual fit produced no finite state")
    model.load_state_dict(best_state); model.eval(); return model


def residual_delta(model:nn.Module,history:Sequence[np.ndarray],normalizer:Normalizer)->np.ndarray:
    values=np.asarray([[normalizer.encode(frame) for frame in history]],dtype=np.float32)
    with torch.no_grad(): output=model(torch.tensor(values))[0,-1].numpy().astype(float)
    return output*POINT_SCALES


def recursive_rollout(base:ARXModel,residual:nn.Module|None,trajectory:dict[str,Any],normalizer:Normalizer)->np.ndarray:
    plasma=np.asarray(trajectory["plasma"][0],dtype=float).copy(); output=[plasma.copy()]; history=[]; r_mid=float(trajectory["r_mid_m"])
    for step in range(16):
        frame=np.concatenate((plasma,np.asarray(trajectory["currents"])[step],np.asarray(trajectory["command_deltas"])[step],[step/16.0,plasma[0]-r_mid])); history.append(frame)
        delta=base.predict_delta(history)
        if residual is not None: delta=delta+residual_delta(residual,history,normalizer)
        plasma=plasma+delta; output.append(plasma.copy())
    return np.asarray(output)
