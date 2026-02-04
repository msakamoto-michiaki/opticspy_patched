# -*- coding: utf-8 -*-
"""tests_ray compatibility runner (Python 3)

This file was updated to run under Python 3 and headless environments.
Outputs are written under tests_ray/out/.
"""

import os
import sys

# Ensure repo root (the directory containing the `opticspy/` package) is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Make output paths stable (relative to this file)
os.chdir(os.path.dirname(__file__))

# Headless-safe plotting
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from opticspy._plot_output import save_figure

from opticspy.ray_tracing import lens, analysis

# ------------------------------------------------------------
# Purpose:
#   Build triplet and generate a spot diagram (headless-safe).
# ------------------------------------------------------------

L = lens.Lens(lens_name="triplet", creator="tests_ray")
L.lens_info()

L.add_wavelength(wl=656.3)
L.add_wavelength(wl=546.1)
L.add_wavelength(wl=486.1)
L.list_wavelengths()

L.add_field_YAN(angle=0)
L.add_field_YAN(angle=7)
L.add_field_YAN(angle=10)
L.list_fields()

L.FNO = 5.0

L.add_surface(number=1, radius=10000000, thickness=5, glass="air")
L.add_surface(number=2, radius=16.87831, thickness=3.25, glass="N-SK16_schott")
L.add_surface(number=3, radius=247.02634, thickness=4.984142, glass="air")
L.add_surface(number=4, radius=-35.95718, thickness=1.25, glass="N-F2_schott", STO=True)
L.add_surface(number=5, radius=15.88615, thickness=6.099225, glass="air")
L.add_surface(number=6, radius=49.08083, thickness=3.25, glass="N-SK16_schott")
L.add_surface(number=7, radius=-27.62109, thickness=38.898042, glass="air")
L.add_surface(number=8, radius=100000000, thickness=0, glass="air")

L.refresh_paraxial()

field_plot = list(range(1, len(L.field_angle_list) + 1))
wave_plot = list(range(1, len(L.wavelength_list) + 1))
analysis.spotdiagram(L, field_plot, wave_plot, n=12, grid_type="grid")

# Rename the default spotdiagram output to avoid collisions across tests
OUT_DIR = os.path.join(os.path.dirname(__file__), "out")
_src = os.path.join(OUT_DIR, "opticspy_ray_tracing_analysis__spotdiagram.png")
_dst = os.path.join(OUT_DIR, "opticspy_ray_tracing_tests_test8_triplet__spotdiagram.png")
if os.path.exists(_src):
    os.replace(_src, _dst)
print(f"[OK] Saved: {_dst}")
