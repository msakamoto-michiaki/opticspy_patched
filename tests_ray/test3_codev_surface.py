# -*- coding: utf-8 -*-
"""tests_ray/test3_codev_surface.py (Python 3)

Purpose
  Read a CODE V .seq file and build an opticspy Lens object.

Background (why this test needs normalization)
  - codev.readseq() passes glass tokens from the .seq file straight into
    Lens.add_surface(..., glass=...).
  - This opticspy snapshot expects non-air glass names as:
        "<glass>_<catalog>"
    where <catalog> is the lower-case folder name in the refractive index DB
    (e.g. schott, ohara).
  - The provided CODE V examples often use tokens like:
        "S-BSM18_OHARA" or "N-SF2_Schott"
    which must be normalized to:
        "S-BSM18_ohara" or "N-SF2_schott"

This test:
  1) loads the example .seq
  2) rewrites glass tokens into the required format
  3) calls codev.readseq() on the rewritten temp file
  4) prints a short summary of the parsed lens

Outputs
  - A normalized copy of the .seq is written to tests_ray/out/.
"""

from __future__ import annotations

import os
import re
import sys

# Ensure repo root (the directory containing the `opticspy/` package) is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(THIS_DIR, "out")
os.makedirs(OUT_DIR, exist_ok=True)

# Make output paths stable (relative to this file)
os.chdir(THIS_DIR)

from opticspy.ray_tracing import codev


def _find_seq_path() -> str:
    """Find the bundled CODE V triplet example."""
    candidates = [
        os.path.join(REPO_ROOT, "ex_CodeV", "triplet.seq"),
        os.path.join(REPO_ROOT, "opticspy", "ray_tracing", "CodeV_examples", "triplet.seq"),
        os.path.join(REPO_ROOT, "opticspy", "ray_tracing", "CodeV_examples", "triplet_stop", "triplet.seq"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError("Could not find triplet.seq in expected locations: " + ", ".join(candidates))


def _normalize_glass_token(token: str) -> str:
    """Normalize CODE V glass token to opticspy DB naming.

    Rules:
      - If token already contains an underscore, treat the suffix as catalog and lower it.
        Example: N-SF2_Schott -> N-SF2_schott
      - If no underscore and token looks like a Schott glass (N-xxx), append _schott.
      - Special-case BK7 -> N-BK7_schott (this DB provides N-BK7.yml).
      - Otherwise return the original token.
    """
    t = token.strip()
    if not t or t.lower() == "air":
        return "air"

    # Common pattern: GLASS_CATALOG (catalog is a folder name)
    if "_" in t:
        glass, cat = t.rsplit("_", 1)
        cat_l = cat.lower()
        if cat_l in {"schott", "ohara", "hoya", "sumita", "cdgm"}:
            return f"{glass}_{cat_l}"
        # If it was an underscore but not a known catalog, leave untouched
        return t

    # No catalog provided: heuristics
    if t.upper() == "BK7":
        return "N-BK7_schott"
    if t.upper().startswith("N-"):
        return f"{t}_schott"

    return t


def _normalize_seq_file(src_path: str, dst_path: str) -> None:
    """Rewrite a .seq file so that glass tokens match opticspy's DB convention."""
    out_lines: list[str] = []

    # CODE V surface lines look like: "S <radius> <thickness> <glass>" (glass is optional)
    # We'll normalize the 4th token only for lines starting with SO/S/SI.
    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                out_lines.append(line)
                continue

            parts = stripped.split()
            if parts and parts[0] in {"SO", "S", "SI"}:
                # Glass token exists when there are >=4 tokens
                if len(parts) >= 4:
                    parts[3] = _normalize_glass_token(parts[3])
                    # Rebuild line keeping original spacing simple (CODE V parser uses split())
                    out_lines.append(" ".join(parts) + "\n")
                    continue

            # Non-surface line or no glass token; keep as-is
            out_lines.append(line)

    with open(dst_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)


def main() -> int:
    src = _find_seq_path()
    dst = os.path.join(OUT_DIR, "triplet_normalized.seq")

    _normalize_seq_file(src, dst)
    print(f"[OK] Normalized seq written to: {dst}")

    # Build lens from normalized seq
    L = codev.readseq(dst)

    # codev.readseq() does not set FNO in this snapshot; keep it non-zero
    # in case downstream functions use it.
    if getattr(L, "FNO", 0) in (0, None):
        L.FNO = 5.0

    print("\nLens summary")
    print("  name:", getattr(L, "lens_name", "(unknown)"))
    print("  wavelengths:", getattr(L, "wavelength_list", []))
    print("  fields (YAN):", getattr(L, "field_angle_list", []))
    print("  surfaces:", len(getattr(L, "surface_list", [])))

    print("\nSurface list (number, radius, thickness, glass, STO)")
    for s in getattr(L, "surface_list", []):
        print(" ", s.number, s.radius, s.thickness, s.glass, getattr(s, "STO", False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
