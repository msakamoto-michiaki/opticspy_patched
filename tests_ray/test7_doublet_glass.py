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
#   Build doublet and generate a spot diagram (headless-safe).
# ------------------------------------------------------------

L = lens.Lens(lens_name="doublet", creator="tests_ray")
L.lens_info()

L.add_wavelength(wl=656.3)
L.add_wavelength(wl=546.1)
L.add_wavelength(wl=486.1)
L.list_wavelengths()

L.add_field_YAN(angle=0)
L.add_field_YAN(angle=2)
L.add_field_YAN(angle=3)
L.list_fields()

L.FNO = 5.0

L.add_surface(number=1, radius=10000000, thickness=0, glass="air")
L.add_surface(number=2, radius=61.07222, thickness=10.345634, glass="S-BSM18_ohara", STO=True)
L.add_surface(number=3, radius=-42.17543, thickness=2.35128, glass="SF1_schott")
L.add_surface(number=4, radius=-316.13853, thickness=92.451433, glass="air")
L.add_surface(number=5, radius=10000000, thickness=0, glass="air")

L.refresh_paraxial()

field_plot = list(range(1, len(L.field_angle_list) + 1))
wave_plot = list(range(1, len(L.wavelength_list) + 1))
analysis.spotdiagram(L, field_plot, wave_plot, n=12, grid_type="grid")

# Rename the default spotdiagram output to avoid collisions across tests
OUT_DIR = os.path.join(os.path.dirname(__file__), "out")
_src = os.path.join(OUT_DIR, "opticspy_ray_tracing_analysis__spotdiagram.png")
_dst = os.path.join(OUT_DIR, "opticspy_ray_tracing_tests_test7_doublet_glass__spotdiagram.png")
if os.path.exists(_src):
    os.replace(_src, _dst)
print(f"[OK] Saved: {_dst}")
