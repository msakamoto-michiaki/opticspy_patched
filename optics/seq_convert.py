# -*- coding: utf-8 -*-
"""CODE V .seq <-> (SurfaceSpec, ReportConfig) conversion utilities.

This module implements a *round-trippable enough* subset for the .seq files found in ex_CodeV/.

Key design points
- Surface definitions live in SurfaceSpec.
- Global (non-surface) .seq commands live in SeqConditions.
- ReportConfig is allowed to evolve (e.g., image_mode/object_distance_mm) without
  affecting surface parsing; SeqConditions remains the home for .seq global commands.
- Lines that are not surface definitions (SO/S/SI/STO) are stored in SeqConditions.
- Surface-adjacent commands (e.g., CCY/THC/CIR/EDG) are stored in SeqConditions.surface_cmds
  keyed by the surface number they follow.
- Global commands are stored in SeqConditions.global_* with simple position tracking:
  preamble (before first surface), between (after surface k), postamble (after last surface).

The writer outputs a canonical .seq that re-parses to the same prescription + key conditions.
It is not intended to preserve exact whitespace or quoting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import re

from optics.abcd_report import SurfaceSpec, ReportConfig


# -----------------------------------------------------------------------------
# Data model for .seq conditions / metadata (does not "dirty" SurfaceSpec/ReportConfig)
# -----------------------------------------------------------------------------
@dataclass
class SeqConditions:
    title: str = ""
    dim: Optional[str] = None  # e.g. "M"
    wavelengths: List[float] = field(default_factory=list)  # as written in seq
    ref: Optional[int] = None
    wtw: List[float] = field(default_factory=list)
    wtf: List[float] = field(default_factory=list)

    epd: Optional[float] = None
    xan_deg: List[float] = field(default_factory=list)
    yan_deg: List[float] = field(default_factory=list)

    fno: Optional[float] = None
    na: Optional[float] = None
    nao: Optional[float] = None

    vux: List[float] = field(default_factory=list)
    vlx: List[float] = field(default_factory=list)
    vuy: List[float] = field(default_factory=list)
    vly: List[float] = field(default_factory=list)

    # frequently used single-word commands
    ca: bool = False
    pim: bool = False
    go: bool = False
    ini: Optional[str] = None  # keep raw argument portion, e.g. "'ORA'"

    # Unknown / extra global commands to round-trip.
    global_preamble: List[str] = field(default_factory=list)
    global_between: Dict[int, List[str]] = field(default_factory=dict)
    global_postamble: List[str] = field(default_factory=list)

    # Surface-adjacent commands to round-trip (CCY/THC/CIR/EDG/...)
    surface_cmds: Dict[int, List[str]] = field(default_factory=dict)

    # Records plane surfaces where input R token was exactly 0 (to write R=0 back)
    plane_surfaces: List[int] = field(default_factory=list)

    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeqDocument:
    prescription: List[SurfaceSpec]
    conditions: SeqConditions


# -----------------------------------------------------------------------------
# Parsing helpers
# -----------------------------------------------------------------------------
_SURFACE_KEYS = ("SO", "S", "SI")
_STOP_KEY = "STO"

# Commands that are typically written *after* a surface line and conceptually belong to that surface.
_SURFACE_ADJ_KEYS = {
    "CCY", "THC", "CIR", "EDG", "CUY", "CUX", "CVY", "CVX", "RED"
}

# Commands that we parse into structured fields in SeqConditions.
_KNOWN_GLOBAL_PREFIXES = {
    "RDM", "LEN", "TITLE", "DIM", "WL", "REF", "WTW", "WTF", "EPD", "XAN", "YAN",
    "VUX", "VLX", "VUY", "VLY", "FNO", "NA", "NAO", "INI", "CA", "PIM", "GO", "DER"
}


def _split_semicolon_commands(line: str) -> List[str]:
    # CODE V uses ';' to chain commands. We split but keep each segment as its own command string.
    parts = [p.strip() for p in line.split(";")]
    return [p for p in parts if p]


def _join_ampersand_continuations(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].rstrip("\n")
        # join while endswith '&'
        while cur.rstrip().endswith("&") and i + 1 < len(lines):
            cur = cur.rstrip()
            cur = cur[:-1]  # drop '&'
            nxt = lines[i + 1].strip("\n")
            cur = f"{cur} {nxt.strip()}"
            i += 1
        out.append(cur)
        i += 1
    return out


def _parse_float_list(tokens: Sequence[str]) -> List[float]:
    out: List[float] = []
    for t in tokens:
        if not t:
            continue
        out.append(float(t))
    return out


def _parse_title_arg(rest: str) -> str:
    # TITLE '....' or TITLE "...". Keep inside quotes if present.
    rest = rest.strip()
    if (rest.startswith("'") and rest.endswith("'")) or (rest.startswith('"') and rest.endswith('"')):
        return rest[1:-1]
    return rest


def _normalize_glass(glass: Optional[str]) -> str:
    if not glass:
        return "air"
    g = glass.strip()
    return "air" if g == "" else g


def parse_seq_text(text: str) -> SeqDocument:
    raw_lines = text.splitlines()
    lines = _join_ampersand_continuations(raw_lines)

    cond = SeqConditions()
    prescription: List[SurfaceSpec] = []
    last_surface_num: Optional[int] = None

    # position tracking for global commands
    seen_any_surface = False

    def _add_global_cmd(cmd: str) -> None:
        nonlocal last_surface_num, seen_any_surface
        if not seen_any_surface:
            cond.global_preamble.append(cmd)
        elif last_surface_num is not None:
            cond.global_between.setdefault(last_surface_num, []).append(cmd)
        else:
            cond.global_postamble.append(cmd)

    for line0 in lines:
        line0 = line0.strip()
        if not line0:
            continue

        # split ';' chained commands into segments
        segments = _split_semicolon_commands(line0)

        for seg in segments:
            if not seg:
                continue
            tokens = seg.split()
            if not tokens:
                continue
            key = tokens[0].upper()

            # surface definitions
            if key in _SURFACE_KEYS:
                seen_any_surface = True
                # expected: KEY R t [glass]
                if len(tokens) < 3:
                    raise ValueError(f"Surface line too short: {seg}")
                R_raw = float(tokens[1])
                t = float(tokens[2])
                glass = _normalize_glass(tokens[3] if len(tokens) >= 4 else None)

                num = len(prescription) + 1
                is_plane = (R_raw == 0.0)
                if is_plane:
                    cond.plane_surfaces.append(num)
                    R = 10000000.0
                else:
                    R = R_raw

                sp = SurfaceSpec(num=num, R=R, t=t, glass=glass, stop=False)
                prescription.append(sp)
                last_surface_num = num
                continue

            # STOP
            if key == _STOP_KEY:
                if last_surface_num is None:
                    raise ValueError("STO encountered before any surface.")
                # mark stop on the last surface
                sp = prescription[-1]
                prescription[-1] = SurfaceSpec(sp.num, sp.R, sp.t, sp.glass, True)
                # keep a record as surface command for round-trip
                cond.surface_cmds.setdefault(last_surface_num, []).append("STO")
                continue

            # surface-adjacent commands (associate with last surface if any)
            if key in _SURFACE_ADJ_KEYS and last_surface_num is not None:
                cond.surface_cmds.setdefault(last_surface_num, []).append(seg)
                continue

            # known global commands -> structured fields where possible
            if key == "TITLE":
                cond.title = _parse_title_arg(seg[len(tokens[0]):].strip())
                continue
            if key == "DIM":
                cond.dim = tokens[1] if len(tokens) >= 2 else None
                continue
            if key == "WL":
                cond.wavelengths = _parse_float_list(tokens[1:])
                continue
            if key == "REF":
                cond.ref = int(float(tokens[1])) if len(tokens) >= 2 else None
                continue
            if key == "WTW":
                cond.wtw = _parse_float_list(tokens[1:])
                continue
            if key == "WTF":
                cond.wtf = _parse_float_list(tokens[1:])
                continue
            if key == "EPD":
                cond.epd = float(tokens[1]) if len(tokens) >= 2 else None
                continue
            if key == "XAN":
                cond.xan_deg = _parse_float_list(tokens[1:])
                continue
            if key == "YAN":
                cond.yan_deg = _parse_float_list(tokens[1:])
                continue
            if key == "FNO":
                cond.fno = float(tokens[1]) if len(tokens) >= 2 else None
                continue
            if key == "NA":
                cond.na = float(tokens[1]) if len(tokens) >= 2 else None
                continue
            if key == "NAO":
                cond.nao = float(tokens[1]) if len(tokens) >= 2 else None
                continue
            if key == "VUX":
                cond.vux = _parse_float_list(tokens[1:])
                continue
            if key == "VLX":
                cond.vlx = _parse_float_list(tokens[1:])
                continue
            if key == "VUY":
                cond.vuy = _parse_float_list(tokens[1:])
                continue
            if key == "VLY":
                cond.vly = _parse_float_list(tokens[1:])
                continue
            if key == "INI":
                cond.ini = seg[len(tokens[0]):].strip()
                continue
            if key == "CA":
                cond.ca = True
                continue
            if key == "PIM":
                cond.pim = True
                # keep command position
                _add_global_cmd("PIM")
                continue
            if key == "GO":
                cond.go = True
                _add_global_cmd("GO")
                continue

            # DER, RDM, LEN etc: keep as global command (positioned)
            if key in _KNOWN_GLOBAL_PREFIXES:
                _add_global_cmd(seg)
            else:
                # completely unknown -> keep as global command
                _add_global_cmd(seg)

    return SeqDocument(prescription=prescription, conditions=cond)


def parse_seq_file(path: Union[str, Path]) -> SeqDocument:
    p = Path(path)
    return parse_seq_text(p.read_text(encoding="utf-8", errors="ignore"))


# -----------------------------------------------------------------------------
# Writing helpers (.seq writer)
# -----------------------------------------------------------------------------
def _fmt_float(x: float) -> str:
    # Keep a compact representation but avoid scientific notation for common values
    # (CODE V accepts scientific, but readability matters)
    if x == 0.0:
        return "0."
    s = f"{x:.17g}"
    return s


def _write_global_line(key: str, values: Sequence[Any]) -> str:
    if not values:
        return key
    return key + " " + " ".join(str(v) for v in values)


def seq_text_from_document(doc: SeqDocument) -> str:
    cond = doc.conditions
    lines: List[str] = []

    # preamble commands we don't regenerate (unknown/global), keep first
    for cmd in cond.global_preamble:
        lines.append(cmd)

    # canonical header (regenerated from structured fields if present)
    if cond.title:
        lines.append(f"TITLE '{cond.title}'")
    if cond.epd is not None:
        lines.append(_write_global_line("EPD", [_fmt_float(cond.epd)]))
    if cond.dim:
        lines.append(_write_global_line("DIM", [cond.dim]))
    if cond.wavelengths:
        lines.append("WL " + " ".join(_fmt_float(w) for w in cond.wavelengths))
    if cond.ref is not None:
        lines.append(_write_global_line("REF", [cond.ref]))
    if cond.wtw:
        lines.append("WTW " + " ".join(_fmt_float(w) for w in cond.wtw))
    if cond.ini:
        lines.append(f"INI {cond.ini}")
    if cond.ca:
        lines.append("CA")
    if cond.xan_deg:
        lines.append("XAN " + " ".join(_fmt_float(v) for v in cond.xan_deg))
    if cond.yan_deg:
        lines.append("YAN " + " ".join(_fmt_float(v) for v in cond.yan_deg))
    if cond.vux:
        lines.append("VUX " + " ".join(_fmt_float(v) for v in cond.vux))
    if cond.vlx:
        lines.append("VLX " + " ".join(_fmt_float(v) for v in cond.vlx))
    if cond.vuy:
        lines.append("VUY " + " ".join(_fmt_float(v) for v in cond.vuy))
    if cond.vly:
        lines.append("VLY " + " ".join(_fmt_float(v) for v in cond.vly))
    if cond.wtf:
        lines.append("WTF " + " ".join(_fmt_float(v) for v in cond.wtf))
    if cond.fno is not None:
        lines.append(_write_global_line("FNO", [_fmt_float(cond.fno)]))
    if cond.na is not None:
        lines.append(_write_global_line("NA", [_fmt_float(cond.na)]))
    if cond.nao is not None:
        lines.append(_write_global_line("NAO", [_fmt_float(cond.nao)]))

    # surfaces
    for sp in doc.prescription:
        key = "S"
        if sp.num == 1:
            key = "SO"
        elif sp.num == doc.prescription[-1].num:
            key = "SI"

        # plane surfaces written as R=0 if known
        R_out = 0.0 if sp.num in set(cond.plane_surfaces) else sp.R
        glass_out = sp.glass
        if glass_out.lower() == "air":
            # CODE V often omits glass for air; omit for compactness
            line = f"{key} {_fmt_float(R_out)} {_fmt_float(sp.t)}"
        else:
            line = f"{key} {_fmt_float(R_out)} {_fmt_float(sp.t)} {glass_out}"
        lines.append(line)

        # surface-adjacent commands
        for cmd in cond.surface_cmds.get(sp.num, []):
            if cmd.upper() == "STO":
                lines.append("  STO")
            else:
                lines.append("  " + cmd)

        # positioned global commands after this surface
        for cmd in cond.global_between.get(sp.num, []):
            lines.append("  " + cmd)

    # postamble
    for cmd in cond.global_postamble:
        lines.append(cmd)

    if cond.go and "GO" not in cond.global_postamble:
        # ensure GO exists if it was present but position lost
        lines.append("GO")

    return "\n".join(lines) + "\n"


def write_seq_file(doc: SeqDocument, path: Union[str, Path]) -> None:
    p = Path(path)
    p.write_text(seq_text_from_document(doc), encoding="utf-8")


# -----------------------------------------------------------------------------
# Helpers: build ReportConfig + drawing parameters
# -----------------------------------------------------------------------------
def build_report_config_from_seq(doc: SeqDocument, *, opticspy_root: Optional[str] = None) -> ReportConfig:
    """Default mapping: SO is surface 1, SI is last surface."""
    n = len(doc.prescription)
    if n < 2:
        raise ValueError("Need at least SO and SI surfaces.")
    return ReportConfig(
        prescription=doc.prescription,
        wavelengths_nm=list(doc.conditions.wavelengths),
        start_surface=2,
        end_surface=n - 1,
        image_surface=n,
        reference_surface=2,
        opticspy_root=opticspy_root,
    )


def pick_field_angles_deg(cond: SeqConditions) -> List[float]:
    if cond.yan_deg:
        return list(cond.yan_deg)
    if cond.xan_deg:
        return list(cond.xan_deg)
    return [0.0]


def pick_fno(cond: SeqConditions, *, fallback_fno: float = 5.0) -> float:
    if cond.fno is not None:
        return float(cond.fno)
    return float(fallback_fno)
