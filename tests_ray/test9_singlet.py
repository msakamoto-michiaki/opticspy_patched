# -*- coding: utf-8 -*-
"""tests_ray/test9_singlet.py (Python 3, headless-safe)

Purpose:
  Build a singlet and generate a spot diagram.

Notes:
  - opticspy.ray_tracing.analysis.spotdiagram() normalizes by the *last* field angle.
    If only an on-axis field (0 deg) exists, it divides by zero.
    Therefore we always add at least one non-zero field.
  - analysis.spotdiagram() always saves to: out/opticspy_ray_tracing_analysis__spotdiagram.png
    To avoid filename collisions across tests, we rename the output per test.
"""

import os
import sys

# Ensure repo root (the directory containing the `opticspy/` package) is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Make output paths stable (relative to this file)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(THIS_DIR)

# Headless-safe plotting
import matplotlib
matplotlib.use("Agg")

from opticspy.ray_tracing import lens, analysis

OUT_DIR = os.path.join(THIS_DIR, "out")
os.makedirs(OUT_DIR, exist_ok=True)


def _rename_spotdiagram_output(basename: str) -> str:
    """Rename the default spotdiagram output to a test-specific filename."""
    src = os.path.join(OUT_DIR, "opticspy_ray_tracing_analysis__spotdiagram.png")
    dst = os.path.join(OUT_DIR, f"{basename}__spotdiagram.png")
    if os.path.exists(src):
        # If dst exists, overwrite it to keep re-runs deterministic.
        try:
            os.replace(src, dst)
        except Exception:
            # Fallback: remove then rename
            try:
                os.remove(dst)
            except Exception:
                pass
            os.rename(src, dst)
    return dst


# ------------------------------------------------------------
# Build lens
# ------------------------------------------------------------
L = lens.Lens(lens_name="singlet", creator="tests_ray")
L.lens_info()

L.add_wavelength(wl=500.0)
L.list_wavelengths()

# Add at least one non-zero field to avoid ZeroDivisionError in analysis.spotdiagram
L.add_field_YAN(angle=0)
L.add_field_YAN(angle=5)
L.list_fields()

L.FNO = 5.0

L.add_surface(number=1, radius=10000000, thickness=10, glass="air")
L.add_surface(number=2, radius=50, thickness=5, glass="N-BK7_schott", STO=True)
L.add_surface(number=3, radius=1175.71, thickness=96.672, glass="air")
L.add_surface(number=4, radius=10000000, thickness=0, glass="air")

L.refresh_paraxial()

field_plot = list(range(1, len(L.field_angle_list) + 1))
wave_plot = list(range(1, len(L.wavelength_list) + 1))
analysis.spotdiagram(L, field_plot, wave_plot, n=12, grid_type="grid")

saved = _rename_spotdiagram_output("opticspy_ray_tracing_tests_test9_singlet")
print(f"[OK] Saved: {saved}")
