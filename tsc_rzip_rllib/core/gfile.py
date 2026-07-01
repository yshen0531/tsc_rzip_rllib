from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np


def _parse_fixed_width_floats(line: str, width: int = 16) -> list[float]:
    vals: list[float] = []
    for i in range(0, len(line.rstrip("\n")), width):
        token = line[i:i + width].strip()
        if not token:
            continue
        try:
            vals.append(float(token))
        except ValueError:
            # TSC/GEQDSK occasionally writes compact forms such as 1.23-123.
            m = re.match(r"^([+-]?\d*\.\d+)([+-]\d+)$", token)
            if not m:
                return []
            vals.append(float(m.group(1) + "E" + m.group(2)))
    return vals


def parse_gfile(path: str | Path) -> Dict[str, Any]:
    """Parse the GEQDSK subset needed for RZIP control and diagnostics.

    Important GEQDSK convention used by TSC/EFIT-style files:
    after qpsi there is usually an integer line ``nbbbs limitr``.
    ``nbbbs`` is the number of plasma-boundary outline points; ``limitr`` is
    the number of limiter/wall outline points.

    Older versions of this project exposed the first outline as ``xplot/zplot``
    and called the count ``nlimiter``.  That was numerically useful but
    semantically confusing.  This parser now exposes explicit aliases:
    ``boundary_R/boundary_Z`` for the plasma boundary and
    ``limiter_R/limiter_Z`` for the limiter/wall trace, while preserving
    ``xplot/zplot`` and ``rwall/zwall`` for backward compatibility.
    """
    path = Path(path)
    lines = path.read_text(errors="ignore").splitlines()
    if not lines:
        raise ValueError(f"empty gfile: {path}")

    header = lines[0].split()
    idum, nx, nz = map(int, header[-3:])
    name = " ".join(header[:-3])

    rows: list[list[float | int]] = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        # GEQDSK float lines are normally 16-character wide, five values/line.
        # Do not misread integer count lines as floats.
        vals = _parse_fixed_width_floats(line, width=16) if ("." in line or "E" in line or "e" in line) else []
        if vals:
            rows.append(vals)
            continue
        # Integer-count lines, e.g. nlimiter/nwall.
        ints = []
        ok = True
        for i in range(0, len(line.rstrip("\n")), 5):
            tok = line[i:i + 5].strip()
            if tok:
                try:
                    ints.append(int(tok))
                except ValueError:
                    ok = False
                    break
        if ok and ints:
            rows.append(ints)

    if len(rows) < 4:
        raise ValueError(f"not enough numeric rows in gfile: {path}")

    rdim, zdim, xplas, ccon, zmid = map(float, rows[0][:5])
    xmag, zmag, psimin, psilim, bcentr = map(float, rows[1][:5])
    zip_ = float(rows[2][0])

    idx = 4

    def take(n: int) -> tuple[np.ndarray, int]:
        nonlocal idx
        out: list[float] = []
        while len(out) < n and idx < len(rows):
            out.extend(float(x) for x in rows[idx])
            idx += 1
        if len(out) < n:
            raise ValueError(f"gfile ended while reading {n} values")
        return np.asarray(out[:n], dtype=float), idx

    fpol, _ = take(nx)
    pres, _ = take(nx)
    ffprim, _ = take(nx)
    pprime, _ = take(nx)
    psi_flat, _ = take(nx * nz)
    psiaux = psi_flat.reshape((nz, nx))
    qpsi, _ = take(nx)

    # GEQDSK standard: nbbbs is the number of boundary points and limitr is
    # the number of limiter/wall points.  Keep old aliases below for
    # compatibility with plotting code, but do not confuse the two traces.
    nbbbs = limitr = 0
    boundary_R = boundary_Z = limiter_R = limiter_Z = np.array([])
    xplot = zplot = rwall = zwall = np.array([])
    if idx < len(rows) and len(rows[idx]) >= 2:
        nbbbs, limitr = int(rows[idx][0]), int(rows[idx][1])
        idx += 1
        if nbbbs > 0:
            bnd, _ = take(nbbbs * 2)
            bnd = bnd.reshape((nbbbs, 2))
            boundary_R, boundary_Z = bnd[:, 0], bnd[:, 1]
            # Backward-compatible historical aliases.
            xplot, zplot = boundary_R, boundary_Z
        if limitr > 0:
            lim, _ = take(limitr * 2)
            lim = lim.reshape((limitr, 2))
            limiter_R, limiter_Z = lim[:, 0], lim[:, 1]
            # Backward-compatible historical aliases.
            rwall, zwall = limiter_R, limiter_Z

    r = np.linspace(ccon, ccon + rdim, nx)
    z = np.linspace(zmid - zdim / 2.0, zmid + zdim / 2.0, nz)
    rr, zz = np.meshgrid(r, z)

    # A robust centroid fallback for visualization.  The legacy code computes
    # ajphi by reconstructing plasma current density; for the RL environment we
    # only need a direct TSC state.  xmag/zmag are always available; rc/zc use a
    # simple pressure-weighted centroid when possible and fall back to xmag/zmag.
    if pres.size == nx and np.nanmax(np.abs(pres)) > 0:
        # Approximate flux-surface weights on the grid from normalized psi.
        denom = psilim - psimin
        psin = np.clip((psiaux - psimin) / denom, 0.0, 1.0) if abs(denom) > 1e-12 else np.zeros_like(psiaux)
        weights = np.maximum(1.0 - psin, 0.0)
        if np.sum(weights) > 0:
            rc = float(np.sum(rr * weights) / np.sum(weights))
            zc = float(np.sum(zz * weights) / np.sum(weights))
        else:
            rc, zc = float(xmag), float(zmag)
    else:
        rc, zc = float(xmag), float(zmag)

    return {
        "name": name,
        "idum": idum,
        "nx": nx,
        "nz": nz,
        "rdim": rdim,
        "zdim": zdim,
        "xplas": xplas,
        "ccon": ccon,
        "zmid": zmid,
        "xmag": float(xmag),
        "zmag": float(zmag),
        "rc": rc,
        "zc": zc,
        "psimin": float(psimin),
        "psilim": float(psilim),
        "bcentr": float(bcentr),
        "ip": float(zip_),
        "fpol": fpol,
        "pres": pres,
        "ffprim": ffprim,
        "pprime": pprime,
        "psiaux": psiaux,
        "qpsi": qpsi,
        "r": r,
        "z": z,
        "rr": rr,
        "zz": zz,
        # Explicit GEQDSK names.
        "nbbbs": nbbbs,
        "limitr": limitr,
        "boundary_R": boundary_R,
        "boundary_Z": boundary_Z,
        "limiter_R": limiter_R,
        "limiter_Z": limiter_Z,

        # Backward-compatible aliases used by older plotting/env code.
        "nlimiter": nbbbs,
        "nwall": limitr,
        "xplot": xplot,
        "zplot": zplot,
        "rwall": rwall,
        "zwall": zwall,
    }


def read_coil_currents_csv(path: str | Path) -> np.ndarray:
    """Return 14 coil currents in the CSV order used by TSC output, in kA."""
    import pandas as pd

    df = pd.read_csv(path)
    # The uploaded files use columns: i, xcoil, zcoil, ccoil(ka)
    col = [c for c in df.columns if "ccoil" in c.lower()]
    if not col:
        raise ValueError(f"ccoil column not found in {path}")
    return df[col[0]].to_numpy(dtype=float)
