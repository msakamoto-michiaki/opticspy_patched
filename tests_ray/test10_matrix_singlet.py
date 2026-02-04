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

from opticspy.ray_tracing import lens

# ------------------------------------------------------------
# Purpose:
#   First-order (paraxial) quantities for a simple singlet.
# ------------------------------------------------------------

L = lens.Lens(lens_name="singlet", creator="tests_ray")
L.lens_info()

L.add_wavelength(wl=500.0)
L.list_wavelengths()

L.add_field_YAN(angle=0)
L.add_field_YAN(angle=7)
L.add_field_YAN(angle=10)
L.list_fields()

L.FNO = 5.0

L.add_surface(number=1, radius=10000000,  thickness=5,        glass="air")
L.add_surface(number=2, radius=50.0,      thickness=5.0,      glass="N-BK7_schott", STO=True)
L.add_surface(number=3, radius=1175.71107, thickness=96.572831, glass="air")
L.add_surface(number=4, radius=100000000, thickness=0,        glass="air")

L.refresh_paraxial()

print("EFL:", L.EFL)
L.OAL(2, 3)
