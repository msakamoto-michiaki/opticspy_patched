# -*- coding: utf-8 -*-
"""Round-trip tests for .seq <-> dataclasses and YAML I/O.

Run:
    python tests_seq_roundtrip.py

This test:
- parses petzval.seq and microscope.seq into SeqDocument
- writes them back to a temporary .seq text and re-parses
- checks prescription + key conditions match
- checks YAML round-trip for SurfaceSpec list, ReportConfig, SeqConditions, SeqDocument
"""

from __future__ import annotations

from pathlib import Path
import os
import tempfile

from optics.seq_convert import (
    parse_seq_file,
    seq_text_from_document,
    parse_seq_text,
    build_report_config_from_seq,
)
from optics.yaml_io import (
    dump_surface_specs, load_surface_specs,
    dump_report_config, load_report_config,
    dump_seq_conditions, load_seq_conditions,
    dump_seq_document, load_seq_document,
)

HERE = Path(__file__).resolve().parent
EX = HERE / "ex_CodeV"


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(msg or f"Not equal:\n{a}\n!=\n{b}")


def simplify_prescription(p):
    return [(s.num, float(s.R), float(s.t), s.glass, bool(s.stop)) for s in p]


def simplify_conditions(c):
    return {
        "title": c.title,
        "dim": c.dim,
        "wavelengths": list(c.wavelengths),
        "ref": c.ref,
        "wtw": list(c.wtw),
        "wtf": list(c.wtf),
        "epd": c.epd,
        "xan": list(c.xan_deg),
        "yan": list(c.yan_deg),
        "fno": c.fno,
        "na": c.na,
        "nao": c.nao,
        "vux": list(c.vux),
        "vlx": list(c.vlx),
        "vuy": list(c.vuy),
        "vly": list(c.vly),
        "ca": c.ca,
        "pim": c.pim,
        "go": c.go,
        "ini": c.ini,
        "plane_surfaces": list(c.plane_surfaces),
    }


def _yaml_roundtrip(doc1, cfg1, path: Path, td: Path) -> None:
    """Write YAML artifacts under td and validate load->equal."""
    sp_yaml = td / "specs.yaml"
    dump_surface_specs(sp_yaml, doc1.prescription)
    specs2 = load_surface_specs(sp_yaml)
    assert_equal(
        simplify_prescription(doc1.prescription),
        simplify_prescription(specs2),
        f"SurfaceSpec YAML mismatch for {path.name}",
    )

    cfg_yaml = td / "cfg.yaml"
    dump_report_config(cfg_yaml, cfg1)
    cfg_loaded = load_report_config(cfg_yaml)
    assert_equal(
        (cfg1.start_surface, cfg1.end_surface, cfg1.image_surface, cfg1.reference_surface),
        (cfg_loaded.start_surface, cfg_loaded.end_surface, cfg_loaded.image_surface, cfg_loaded.reference_surface),
        f"ReportConfig YAML mismatch for {path.name}",
    )

    cond_yaml = td / "cond.yaml"
    dump_seq_conditions(cond_yaml, doc1.conditions)
    cond_loaded = load_seq_conditions(cond_yaml)
    assert_equal(
        simplify_conditions(doc1.conditions),
        simplify_conditions(cond_loaded),
        f"SeqConditions YAML mismatch for {path.name}",
    )

    doc_yaml = td / "doc.yaml"
    dump_seq_document(doc_yaml, doc1)
    doc_loaded = load_seq_document(doc_yaml)
    assert_equal(
        simplify_prescription(doc1.prescription),
        simplify_prescription(doc_loaded.prescription),
        f"SeqDocument YAML prescription mismatch for {path.name}",
    )
    assert_equal(
        simplify_conditions(doc1.conditions),
        simplify_conditions(doc_loaded.conditions),
        f"SeqDocument YAML conditions mismatch for {path.name}",
    )


def roundtrip_seq(path: Path):
    doc1 = parse_seq_file(path)
    text2 = seq_text_from_document(doc1)
    doc2 = parse_seq_text(text2)

    assert_equal(simplify_prescription(doc1.prescription), simplify_prescription(doc2.prescription),
                 f"Prescription mismatch after roundtrip for {path.name}")
    assert_equal(simplify_conditions(doc1.conditions), simplify_conditions(doc2.conditions),
                 f"Conditions mismatch after roundtrip for {path.name}")

    # ReportConfig derived should also be stable
    cfg1 = build_report_config_from_seq(doc1)
    cfg2 = build_report_config_from_seq(doc2)
    assert_equal((cfg1.start_surface, cfg1.end_surface, cfg1.image_surface, cfg1.reference_surface),
                 (cfg2.start_surface, cfg2.end_surface, cfg2.image_surface, cfg2.reference_surface),
                 f"ReportConfig mismatch for {path.name}")

    # YAML roundtrip
    keep_yaml = os.environ.get("KEEP_YAML", "0") == "1"
    if keep_yaml:
        out_base = Path(os.environ.get("YAML_DIR", "out_yaml"))
        td = out_base / path.stem
        td.mkdir(parents=True, exist_ok=True)
        _yaml_roundtrip(doc1, cfg1, path, td)
    else:
        with tempfile.TemporaryDirectory() as _td:
            td = Path(_td)
            _yaml_roundtrip(doc1, cfg1, path, td)



def main():
    keep_yaml = os.environ.get("KEEP_YAML", "0") == "1"
    if keep_yaml:
        out_base = Path(os.environ.get("YAML_DIR", "out_yaml")).resolve()
        print(f"[KEEP_YAML=1] YAML will be kept under: {out_base}")
    for name in ["petzval.seq", "microscope.seq"]:
        p = EX / name
        roundtrip_seq(p)
        print(f"[OK] {name}")
    print("[ALL TESTS PASSED]")


if __name__ == "__main__":
    main()
