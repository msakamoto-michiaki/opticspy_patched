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
#   First-order (paraxial) property reporting example for a multi-element lens:
#   EFL, BFL, OAL, image position, entrance/exit pupil.
# ------------------------------------------------------------

L = lens.Lens(lens_name="triplet", creator="tests_ray")
L.lens_info()

# Wavelengths (nm)
L.add_wavelength(wl=656.30)
L.add_wavelength(wl=546.10)
L.add_wavelength(wl=486.10)
L.list_wavelengths()

# Fields (deg)
L.add_field_YAN(angle=0)
L.add_field_YAN(angle=7)
L.add_field_YAN(angle=10)
L.list_fields()

# F-number (needed for paraxial refresh)
L.FNO = 5.0

# Prescription (as provided)
L.add_surface(number=1, radius=10000000, thickness=1000000, glass="air")
L.add_surface(number=2, radius=41.15909, thickness=6.097555,  glass="S-BSM18_ohara")
L.add_surface(number=3, radius=-957.83146, thickness=9.349584, glass="air")
L.add_surface(number=4, radius=-51.32104, thickness=2.032518,  glass="S-BAL12_ohara")
L.add_surface(number=5, radius=42.37768,  thickness=5.995929,  glass="air")
L.add_surface(number=6, radius=10000000, thickness=4.065037,   glass="air", STO=True)
L.add_surface(number=7, radius=247.44562, thickness=6.097555,  glass="S-BSM18_ohara")
L.add_surface(number=8, radius=-40.04016, thickness=85.593426, glass="air")
L.add_surface(number=9, radius=10000000, thickness=0,          glass="air")

# Compute paraxial quantities
L.refresh_paraxial()

print("\n--- First-order quantities ---")
print("EFL:", L.EFL)
print("EPD:", L.EPD)
print("EP thickness:", L.EP_thickness)

# The following methods print internal reports (kept for backward compatibility)
L.BFL()
L.OAL(2, 9)
L.image_position()
L.EP()
L.EX()

# Some scripts expect EP_position attribute; lens.py doesn't expose it consistently,
# so print what we have.
print("object_position:", L.object_position)
