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

from opticspy.ray_tracing import lens, trace, draw

# Patch pyplot.show so draw.draw_system() doesn't block; instead save to tests_ray/out/
def _save_and_close(filename: str):
    save_figure(plt, filename, outdir="out")
    plt.close("all")


from opticspy.ray_tracing import analysis, field as field_mod  # noqa: F401  (kept for parity)

# ------------------------------------------------------------
# Purpose:
#   Cooke-triplet-like example:
#     - refresh paraxial
#     - trace rays for drawing
#     - trace one specific ray and print per-surface ray data
#     - save layout drawing (headless-safe)
# ------------------------------------------------------------

plt.show = lambda *a, **k: _save_and_close("opticspy_ray_tracing_tests_test14_cooke__layout.png")

L = lens.Lens(lens_name="triplet", creator="tests_ray")
L.FNO = 3.0
L.lens_info()

L.add_wavelength(wl=656.30)
L.add_wavelength(wl=546.10)
L.add_wavelength(wl=486.10)

L.add_field_YAN(angle=0)
L.add_field_YAN(angle=14)
L.add_field_YAN(angle=20)

L.add_surface(number=1, radius=10000000, thickness=1000000, glass="air")
L.add_surface(number=2, radius=16.87831, thickness=3.25,     glass="N-SK16_schott")
L.add_surface(number=3, radius=247.02634, thickness=4.984142, glass="air")
L.add_surface(number=4, radius=10000000, thickness=0,        glass="air", STO=True)
L.add_surface(number=5, radius=-35.95718, thickness=1.25,    glass="N-F2_schott")
L.add_surface(number=6, radius=15.88615, thickness=6.099225, glass="air")
L.add_surface(number=7, radius=49.08083, thickness=3.25,     glass="N-SK16_schott")
L.add_surface(number=8, radius=-27.62109, thickness=38.898042, glass="air")
L.add_surface(number=9, radius=10000000, thickness=0,        glass="air")

L.refresh_paraxial()
trace.trace_draw_ray(L)

# Trace one marginal ray at the max field, middle wavelength
trace.trace_one_ray(
    L,
    field_num=3,
    wave_num=2,
    ray=[0, -1],
    start=0,
    end=0,
    output=True,
    output_list=["X", "Y", "Z", "K", "L", "M"],
)

draw.draw_system(L)
