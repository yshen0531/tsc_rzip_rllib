from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

import numpy as np

Number = Union[int, float, np.number]
Row = Sequence[Optional[Number]]


def format_number(value: Number) -> str:
    """Format one TSC fixed-width numeric field.

    TSC input cards in this project use 10-character fields.  Scientific
    notation is safer than free-format decimals for restart generation.
    """
    formatted = f"{float(value):.3E}"
    if len(formatted) > 10:
        return formatted[:10]
    return formatted + " " * (10 - len(formatted))


def rows_to_lines(rows: Sequence[Row]) -> List[str]:
    lines: List[str] = []
    for row in rows:
        if not row:
            continue
        card = str(int(row[0])) if isinstance(row[0], (int, np.integer)) else str(row[0]).strip()
        line = f"{card:<10}"
        for val in row[1:]:
            line += " " * 10 if val is None else format_number(val)
        lines.append(line + "\n")
    return lines


def generate_restart_inputa_file(template_inputa: Union[str, Path], rows: Sequence[Row], output_path: Optional[Union[str, Path]] = None) -> Path:
    """Generate a compact restart ``inputa``.

    The output keeps the title, keeps card 00 with restart flag set to 1.0,
    inserts the provided rows, and ends at card 99.  This mirrors the legacy
    project behavior, but is intentionally standalone.
    """
    template_inputa = Path(template_inputa)
    output_path = Path(output_path) if output_path is not None else template_inputa

    if not template_inputa.exists():
        raise FileNotFoundError(f"inputa not found: {template_inputa}")

    lines = template_inputa.read_text().splitlines(keepends=True)
    if not lines:
        raise ValueError(f"inputa is empty: {template_inputa}")

    out: List[str] = [lines[0]]
    inserted = False

    for line in lines[1:]:
        card = line[:10].strip()
        if card == "00":
            parts = line.split()
            if len(parts) < 2:
                raise ValueError("card 00 has no numeric fields")
            parts[1] = "1.0"
            new_line = f"{'00':<10}" + "".join(format_number(float(p)) for p in parts[1:]) + "\n"
            out.append(new_line)
        elif card == "99":
            out.extend(rows_to_lines(rows))
            out.append(line if line.endswith("\n") else line + "\n")
            inserted = True
            break

    if not inserted:
        raise ValueError("card 99 not found in inputa")

    output_path.write_text("".join(out))
    return output_path


def read_card_first_values(inputa_path: Union[str, Path], card_ids: Iterable[int]) -> dict[int, float]:
    """Read the first numeric value after selected cards.

    Useful for keeping device-shape cards such as 90--95 unchanged between
    restart steps.
    """
    wanted = {f"{int(c):02}" for c in card_ids} | {str(int(c)) for c in card_ids}
    result: dict[int, float] = {}
    for line in Path(inputa_path).read_text().splitlines():
        card_raw = line[:10].strip()
        if card_raw in wanted:
            fields = line[10:].split()
            if fields:
                result[int(card_raw)] = float(fields[0])
    return result


def build_restart_rows(
    current_time_ms: int,
    dt_ms: int,
    current_currents_ka: np.ndarray,
    next_currents_ka: np.ndarray,
    shape_card_values: Optional[dict[int, float]] = None,
) -> list[list[Optional[float]]]:
    """Build restart rows for one TSC step.

    Card convention follows the legacy PID simulator:
      - card 11: restart target time;
      - card 18: current and next time;
      - card 15: current and next commands for the 14 active coils;
      - cards 90--95: hold shape/auxiliary parameters constant when present.
    """
    current_s = current_time_ms / 1000.0
    next_s = (current_time_ms + dt_ms) / 1000.0

    rows: list[list[Optional[float]]] = [
        [11, 29.0, 1.0, next_s],
        [18, None, current_s, next_s],
    ]
    for i, (i_now, i_next) in enumerate(zip(current_currents_ka, next_currents_ka), start=1):
        rows.append([15, float(i), float(i_now), float(i_next)])

    if shape_card_values:
        for card in sorted(shape_card_values):
            val = float(shape_card_values[card])
            rows.append([card, None, val, val])

    return rows
