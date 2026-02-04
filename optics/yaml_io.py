# -*- coding: utf-8 -*-
"""YAML I/O for SurfaceSpec, ReportConfig, SeqConditions, SeqDocument.

Uses yaml.safe_load / safe_dump and converts dataclasses to plain dicts.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from optics.abcd_report import SurfaceSpec, ReportConfig
from optics.seq_convert import SeqConditions, SeqDocument


def _surface_spec_to_data(sp: SurfaceSpec) -> Dict[str, Any]:
    return {"num": sp.num, "R": sp.R, "t": sp.t, "glass": sp.glass, "stop": sp.stop}


def _surface_spec_from_data(d: Dict[str, Any]) -> SurfaceSpec:
    return SurfaceSpec(
        num=int(d["num"]),
        R=float(d["R"]),
        t=float(d["t"]),
        glass=str(d.get("glass", "air")),
        stop=bool(d.get("stop", False)),
    )


def surface_specs_to_data(specs: List[SurfaceSpec]) -> List[Dict[str, Any]]:
    return [_surface_spec_to_data(s) for s in specs]


def surface_specs_from_data(data: List[Dict[str, Any]]) -> List[SurfaceSpec]:
    return [_surface_spec_from_data(d) for d in data]


def report_config_to_data(cfg: ReportConfig) -> Dict[str, Any]:
    return {
        "prescription": surface_specs_to_data(cfg.prescription),
        "wavelengths_nm": list(cfg.wavelengths_nm),
        "start_surface": cfg.start_surface,
        "end_surface": cfg.end_surface,
        "image_surface": cfg.image_surface,
        "image_z_abs": cfg.image_z_abs,
        "image_mode": cfg.image_mode,
        "object_distance_mm": cfg.object_distance_mm,
        "object_medium": cfg.object_medium,
        "image_medium": cfg.image_medium,
        "reference_surface": cfg.reference_surface,
        "opticspy_root": cfg.opticspy_root,
    }


def report_config_from_data(d: Dict[str, Any]) -> ReportConfig:
    return ReportConfig(
        prescription=surface_specs_from_data(d["prescription"]),
        wavelengths_nm=list(d.get("wavelengths_nm", [])),
        start_surface=int(d.get("start_surface", 2)),
        end_surface=int(d.get("end_surface", 0)),
        image_surface=d.get("image_surface", None),
        image_z_abs=d.get("image_z_abs", None),
        image_mode=str(d.get("image_mode", "recipe")),
        object_distance_mm=d.get("object_distance_mm", None),
        object_medium=str(d.get("object_medium", "air")),
        image_medium=str(d.get("image_medium", "air")),
        reference_surface=int(d.get("reference_surface", 2)),
        opticspy_root=d.get("opticspy_root", None),
    )


def seq_conditions_to_data(cond: SeqConditions) -> Dict[str, Any]:
    return {
        "title": cond.title,
        "dim": cond.dim,
        "wavelengths": list(cond.wavelengths),
        "ref": cond.ref,
        "wtw": list(cond.wtw),
        "wtf": list(cond.wtf),
        "epd": cond.epd,
        "xan_deg": list(cond.xan_deg),
        "yan_deg": list(cond.yan_deg),
        "fno": cond.fno,
        "na": cond.na,
        "nao": cond.nao,
        "vux": list(cond.vux),
        "vlx": list(cond.vlx),
        "vuy": list(cond.vuy),
        "vly": list(cond.vly),
        "ca": cond.ca,
        "pim": cond.pim,
        "go": cond.go,
        "ini": cond.ini,
        "global_preamble": list(cond.global_preamble),
        "global_between": {int(k): list(v) for k, v in cond.global_between.items()},
        "global_postamble": list(cond.global_postamble),
        "surface_cmds": {int(k): list(v) for k, v in cond.surface_cmds.items()},
        "plane_surfaces": list(cond.plane_surfaces),
        "extras": dict(cond.extras),
    }


def seq_conditions_from_data(d: Dict[str, Any]) -> SeqConditions:
    cond = SeqConditions()
    cond.title = str(d.get("title", ""))
    cond.dim = d.get("dim", None)
    cond.wavelengths = list(d.get("wavelengths", []))
    cond.ref = d.get("ref", None)
    cond.wtw = list(d.get("wtw", []))
    cond.wtf = list(d.get("wtf", []))
    cond.epd = d.get("epd", None)
    cond.xan_deg = list(d.get("xan_deg", []))
    cond.yan_deg = list(d.get("yan_deg", []))
    cond.fno = d.get("fno", None)
    cond.na = d.get("na", None)
    cond.nao = d.get("nao", None)
    cond.vux = list(d.get("vux", []))
    cond.vlx = list(d.get("vlx", []))
    cond.vuy = list(d.get("vuy", []))
    cond.vly = list(d.get("vly", []))
    cond.ca = bool(d.get("ca", False))
    cond.pim = bool(d.get("pim", False))
    cond.go = bool(d.get("go", False))
    cond.ini = d.get("ini", None)
    cond.global_preamble = list(d.get("global_preamble", []))
    cond.global_between = {int(k): list(v) for k, v in (d.get("global_between", {}) or {}).items()}
    cond.global_postamble = list(d.get("global_postamble", []))
    cond.surface_cmds = {int(k): list(v) for k, v in (d.get("surface_cmds", {}) or {}).items()}
    cond.plane_surfaces = list(d.get("plane_surfaces", []))
    cond.extras = dict(d.get("extras", {}))
    return cond


def seq_document_to_data(doc: SeqDocument) -> Dict[str, Any]:
    return {
        "prescription": surface_specs_to_data(doc.prescription),
        "conditions": seq_conditions_to_data(doc.conditions),
    }


def seq_document_from_data(d: Dict[str, Any]) -> SeqDocument:
    from optics.seq_convert import SeqDocument  # avoid circular import issues
    return SeqDocument(
        prescription=surface_specs_from_data(d["prescription"]),
        conditions=seq_conditions_from_data(d["conditions"]),
    )


def _dump_yaml(path: Union[str, Path], data: Any) -> None:
    p = Path(path)
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _load_yaml(path: Union[str, Path]) -> Any:
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8"))


# Public APIs
def dump_surface_specs(path: Union[str, Path], specs: List[SurfaceSpec]) -> None:
    _dump_yaml(path, surface_specs_to_data(specs))


def load_surface_specs(path: Union[str, Path]) -> List[SurfaceSpec]:
    return surface_specs_from_data(_load_yaml(path))


def dump_report_config(path: Union[str, Path], cfg: ReportConfig) -> None:
    _dump_yaml(path, report_config_to_data(cfg))


def load_report_config(path: Union[str, Path]) -> ReportConfig:
    return report_config_from_data(_load_yaml(path))


def dump_seq_conditions(path: Union[str, Path], cond: SeqConditions) -> None:
    _dump_yaml(path, seq_conditions_to_data(cond))


def load_seq_conditions(path: Union[str, Path]) -> SeqConditions:
    return seq_conditions_from_data(_load_yaml(path))


def dump_seq_document(path: Union[str, Path], doc: SeqDocument) -> None:
    _dump_yaml(path, seq_document_to_data(doc))


def load_seq_document(path: Union[str, Path]) -> SeqDocument:
    return seq_document_from_data(_load_yaml(path))
