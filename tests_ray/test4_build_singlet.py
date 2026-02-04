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
#   Build a simple singlet Lens using glass database and run a spot diagram.
#   This validates: Lens construction -> glass lookup -> paraxial refresh -> spot tracing.
# ------------------------------------------------------------

L = lens.Lens(lens_name="singlet", creator="tests_ray")

# Wavelengths (nm)
L.add_wavelength(wl=656.30)
L.add_wavelength(wl=587.60)
L.add_wavelength(wl=486.10)

# Fields (deg) using the current API name
L.add_field_YAN(angle=0)
L.add_field_YAN(angle=5)

# F-number required by refresh_paraxial()
L.FNO = 5.0

# Surfaces (glass name format: NAME_CATALOG, e.g., BK7_SCHOTT)
L.add_surface(number=1, radius=10000000, thickness=5,  glass="air")
L.add_surface(number=2, radius=50,       thickness=5,  glass="N-BK7_schott", STO=True)
L.add_surface(number=3, radius=1175.71,  thickness=50, glass="air")
L.add_surface(number=4, radius=10000000, thickness=0,  glass="air")

L.lens_info()
L.list_wavelengths()
L.list_fields()

# Update paraxial quantities (EP, etc.)
L.refresh_paraxial()

# Spot diagram for all fields/wavelengths
field_plot = list(range(1, len(L.field_angle_list) + 1))
wave_plot = list(range(1, len(L.wavelength_list) + 1))
analysis.spotdiagram(L, field_plot, wave_plot, n=12, grid_type="grid")

# Rename the default spotdiagram output to avoid collisions across tests
OUT_DIR = os.path.join(os.path.dirname(__file__), "out")
_src = os.path.join(OUT_DIR, "opticspy_ray_tracing_analysis__spotdiagram.png")
_dst = os.path.join(OUT_DIR, "opticspy_ray_tracing_tests_test4_build_singlet__spotdiagram.png")
if os.path.exists(_src):
    os.replace(_src, _dst)
print(f"[OK] Saved: {_dst}")
