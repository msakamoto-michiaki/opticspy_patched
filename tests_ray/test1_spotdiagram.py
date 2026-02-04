# -*- coding: utf-8 -*-
"""tests_ray/test1_spotdiagram.py (Python 3, headless-safe)

Build a simple air -> N-BK7 -> air system and generate a spot diagram.

Notes on glass names for this opticspy snapshot:
- Non-air glass must be given as "<glass>_<catalog>".
- The catalog folder names are lowercase (e.g. "schott", "ohara").
- For Schott BK7, the database provides "N-BK7.yml", so use "N-BK7_schott".

Notes on outputs:
- opticspy.ray_tracing.analysis.spotdiagram() always saves to:
    out/opticspy_ray_tracing_analysis__spotdiagram.png
  To avoid filename collisions across tests, we rename the output per test.
"""

import os
import sys
import types

# Ensure repo root (the directory containing the `opticspy/` package) is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Make output paths stable (relative to this file)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(THIS_DIR)
OUT_DIR = os.path.join(THIS_DIR, "out")
os.makedirs(OUT_DIR, exist_ok=True)

# Headless-safe plotting
import matplotlib
matplotlib.use("Agg")  # must be set before pyplot import

# If 'unwrap' is missing, create a dummy module so opticspy imports don't fail
try:
    import unwrap  # noqa: F401
except Exception:
    dummy = types.ModuleType("unwrap")

    def _dummy_unwrap(*args, **kwargs):
        raise NotImplementedError("unwrap module is not available in this environment.")

    dummy.unwrap = _dummy_unwrap
    sys.modules["unwrap"] = dummy

from opticspy.ray_tracing.lens import Lens
from opticspy.ray_tracing import analysis


def _rename_spotdiagram_output(basename: str) -> str:
    """Rename the default spotdiagram output to a test-specific filename."""
    src = os.path.join(OUT_DIR, "opticspy_ray_tracing_analysis__spotdiagram.png")
    dst = os.path.join(OUT_DIR, f"{basename}__spotdiagram.png")
    if os.path.exists(src):
        try:
            os.replace(src, dst)
        except Exception:
            try:
                os.remove(dst)
            except Exception:
                pass
            os.rename(src, dst)
    return dst


def main() -> int:
    # Representative wavelengths (nm); middle element is treated as design wavelength
    wavelengths_nm = [656.3, 587.6, 486.1]

    # Build lens
    L = Lens(lens_name="test1_spotdiagram", creator="tests_ray")

    # F-number is required by refresh_paraxial / pupil-related calculations
    L.FNO = 5.0

    # Wavelengths
    for wl in wavelengths_nm:
        L.add_wavelength(wl)

    # Fields (YAN: field angles in degrees)
    # Keep >=2 fields because spotdiagram normalizes against the last field
    field_angles_deg = [0.0, 5.0]
    for ang in field_angles_deg:
        L.add_field_YAN(ang)

    # Surfaces
    # Convention: 'glass' is the medium AFTER the surface.
    L.add_surface(number=1, radius=1.0e7, thickness=10.0, glass="air")
    L.add_surface(number=2, radius=20.0, thickness=40.0, glass="N-BK7_schott", STO=True)
    L.add_surface(number=3, radius=1.0e7, thickness=0.0, glass="air")

    # Update paraxial quantities
    L.refresh_paraxial()

    field_plot = list(range(1, len(field_angles_deg) + 1))
    wave_plot = list(range(1, len(wavelengths_nm) + 1))

    analysis.spotdiagram(L, field_plot=field_plot, wave_plot=wave_plot, n=12, grid_type="grid")

    saved = _rename_spotdiagram_output("opticspy_ray_tracing_tests_test1_spotdiagram")
    print(f"[OK] Saved: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
