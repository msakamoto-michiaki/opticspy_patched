"""test2_2.py

example2（F/5 Double Gauss）に対応するテスト。

機能:
  (1) example2 と同一の処方を test1_1 形式（SurfaceSpec/ReportConfig）で定義
  (2) draw_system / grid_generator / spotdiagram / Ray_fan を実行（example2相当）
  (3) test1_1 と同じ Fixed-style ABCD / Principal plane report を表示（#Extract & print）
  (4) First-order comparison (opticspy vs ABCD direct) を表示

注:
  - example2 は .seq 入力ではないため、.seq<->yaml 相互変換は行わない。
  - opticspy の BFL() は "最後の厚み"（処方BFL）であり、ABCD由来の -A/C とは別。
"""

import os

from optics.abcd_report import (
    SurfaceSpec,
    ReportConfig,
    compute_report,
    build_opticspy_lens,
    first_order_like_opticspy,
    compute_abcd_from_prescription,
    efl_from_abcd,
    oal_from_prescription,
)

from utils.plotting import setup_matplotlib_headless, rename_fixed_png, rename_latest_spotdiagram

# -------------------------------------------------
# Prescription (same as example2)
# -------------------------------------------------
prescription = [
    SurfaceSpec(1,  10000000.0, 10000000.0, "air"),
    SurfaceSpec(2,  56.20238,   8.75,       "N-SSK2_schott"),
    SurfaceSpec(3,  152.28580,  0.5,        "air"),
    SurfaceSpec(4,  37.68262,   12.5,       "N-SK2_schott"),
    SurfaceSpec(5,  10000000.0, 3.8,        "F5_schott"),
    SurfaceSpec(6,  24.23130,   16.369445,  "air"),
    SurfaceSpec(7,  10000000.0, 13.747957,  "air", True),  # STOP
    SurfaceSpec(8,  -28.37731,  3.8,        "F5_schott"),
    SurfaceSpec(9,  100000000.0, 11.0,      "N-SK16_schott"),
    SurfaceSpec(10, -37.92546,  0.5,        "air"),
    SurfaceSpec(11, 177.41176,  7.0,        "N-SK16_schott"),
    SurfaceSpec(12, -79.41143,  61.487536,  "air"),
    SurfaceSpec(13, 100000000.0, 0.0,       "air"),  # image plane
]

# -------------------------------------------------
# Report configuration
# -------------------------------------------------
cfg = ReportConfig(
    image_mode="paraxial",
    object_distance_mm=-500.0,
    prescription=prescription,
    wavelengths_nm=[656.3, 587.6, 486.1],
    start_surface=2,
    end_surface=12,
    image_surface=13,
    reference_surface=2,
    opticspy_root=None,
)

# -------------------------------------------------
# Compute report
# -------------------------------------------------
rep = compute_report(cfg)

# -------------------------------------------------
# Draw / analyses (caller-side, similar to example2)
# -------------------------------------------------
outdir = os.path.join("out", "examples", "test2_2")
os.makedirs(outdir, exist_ok=True)
setup_matplotlib_headless()

field_angles_deg = [0, 10, 14]
fno = 5.0

L = build_opticspy_lens(
    prescription=prescription,
    wavelengths_nm=cfg.wavelengths_nm,
    field_angles_deg=field_angles_deg,
    fno=fno,
    opticspy_root=cfg.opticspy_root,
    lens_name="Doublegauss",
    creator="test2_2",
)

# Finite conjugate mode: set opticspy object position (used by image_position)
L.object_position = float(cfg.object_distance_mm)

from opticspy.ray_tracing import first_order_tools as fot  # noqa: E402

# -------------------------------------------------
# First-order comparisons (opticspy vs our ABCD direct)
# (do this *before* importing draw/analysis modules to keep startup responsive)
# -------------------------------------------------
import io
import contextlib


def _quiet_call(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*args, **kwargs)


# opticspy first-order (ground truth for comparison)
opt_efl_full = _quiet_call(fot.EFL, L, cfg.start_surface, cfg.end_surface)
opt_efl_23 = _quiet_call(fot.EFL, L, 2, 3)
opt_bfl_recipe = _quiet_call(fot.BFL, L)
opt_img_pos = _quiet_call(fot.image_position, L)
opt_ep = _quiet_call(fot.EP, L)
opt_ex = _quiet_call(fot.EX, L)
opt_oal_27 = _quiet_call(fot.OAL, L, 2, 7)

# our ABCD direct (same formulas as opticspy) from cfg
our = first_order_like_opticspy(cfg, object_distance=L.object_position)
M23 = compute_abcd_from_prescription(cfg.prescription, cfg.wavelengths_nm, 2, 3, opticspy_root=cfg.opticspy_root)
C23 = float(M23[1, 0])
our_efl_23 = efl_from_abcd(C23)
our_oal_27 = oal_from_prescription(cfg.prescription, 2, 7)

print("\n============================================")
print(" First-order comparison (opticspy vs ABCD direct)")
print("============================================")
print(f"EFY full (2..{cfg.end_surface})  opticspy={opt_efl_full:.9f}  ours={our['efl']:.9f}  Δ={opt_efl_full-our['efl']:+.3e}")
print(f"EFY part (2..3)                 opticspy={opt_efl_23:.9f}  ours={our_efl_23:.9f}  Δ={opt_efl_23-our_efl_23:+.3e}")
print(f"BFL recipe (last thickness)      opticspy={opt_bfl_recipe:.9f}  ours={our['bfl_recipe']:.9f}  Δ={opt_bfl_recipe-our['bfl_recipe']:+.3e}")
print(f"BFL paraxial (-A/C)              opticspy=   (not provided)  ours={our['bfl_parax']:.9f}")
print(f"image_position                  opticspy={opt_img_pos:.9f}  ours={our['image_position']:.9f}  Δ={opt_img_pos-our['image_position']:+.3e}")
print(f"EP (entrance pupil pos)         opticspy={opt_ep:.9f}  ours={our['ep']:.9f}  Δ={opt_ep-our['ep']:+.3e}")
print(f"EX (exit pupil pos)             opticspy={opt_ex:.9f}  ours={our['ex']:.9f}  Δ={opt_ex-our['ex']:+.3e}")
print(f"OAL (2..7)                      opticspy={opt_oal_27:.9f}  ours={our_oal_27:.9f}  Δ={opt_oal_27-our_oal_27:+.3e}")


from opticspy.ray_tracing import trace, draw, field, analysis  # noqa: E402

# Layout
_ = trace.trace_draw_ray(L)
draw.draw_system(L)
rename_fixed_png(
    "out/opticspy_ray_tracing_draw__draw_system.png",
    outdir,
    tag="test2_2_",
)

# ---- grid ----
field.grid_generator(12, grid_type="grid", output=1)
rename_fixed_png(
    "out/opticspy_ray_tracing_field__grid_generator.png",
    outdir,
    tag="test2_2_grid_n12",
)
analysis.spotdiagram(L, [1, 2, 3], [1, 2, 3], n=12, grid_type="grid")
rename_latest_spotdiagram(outdir, tag="test2_2_spot_grid_n12")

# ---- ray fan ----
analysis.Ray_fan(L, [1, 2, 3], [1, 2, 3])
rename_fixed_png(
    "out/opticspy_ray_tracing_analysis__Ray_fan.png",
    outdir,
    tag="test2_2_",
)

# -------------------------------------------------
# Extract & print (same style as test3_1)
# -------------------------------------------------
A = rep["ABCD"]["A"]
B = rep["ABCD"]["B"]
C = rep["ABCD"]["C"]
D = rep["ABCD"]["D"]
card = rep["cardinals"]

# middle wavelength for label
wls = cfg.wavelengths_nm
nd = wls[len(wls) // 2] if wls else float("nan")

print("============================================")
print(" Fixed-style ABCD / Principal plane report ")
print(f" (reduced-angle [y, u], nd = {nd} nm)")
print("============================================")
print(f"start surface: {cfg.start_surface}")
print(f"end surface: {cfg.end_surface}")

print(f"A = {A:.9f}")
print(f"B = {B:.9f}")
print(f"C = {C:.9f}")
print(f"D = {D:.9f}")

print("\n--- Cardinal points ---")
print(f"f'  = {card['fprime']:.6f} mm")
print(f"H   = {rep['zH']:.6f} mm  (from surface {cfg.reference_surface} vertex)")
print(f"H'  = {rep['zHp']:.6f} mm (from surface {cfg.end_surface} vertex)")
print(f"BFL = {card['BFL']:.6f} mm")

print("\n--- Image plane check ---")
z_end = rep["z"].get(cfg.end_surface)
print(f"z{cfg.end_surface}           = {z_end:.6f}")
if rep.get("z_img_prescribed") is not None:
    print(f"z{cfg.image_surface} (recipe)  = {rep['z_img_prescribed']:.6f}")
print(f"z{cfg.end_surface} + BFL     = {rep['z_img_abcd']:.6f}")
if rep.get("z_img_prescribed") is not None:
    print(f"Δz           = {(rep['z_img_prescribed'] - rep['z_img_abcd']):.9e} mm")

# -------------------------------------------------
# Magnification & Newton relation (Plan B)
# -------------------------------------------------
if rep.get("system_matrix") is not None:
    sm = rep["system_matrix"]
    mags = rep.get("magnifications") or {}
    newt = rep.get("newton_check")

    print("\n--- System matrix (object→image) ---")
    print(f"image_mode = {sm.get('image_mode')}")
    print(f"A_s = {sm['A_s']:.9f}")
    print(f"B_s = {sm['B_s']:.9f}")
    print(f"C_s = {sm['C_s']:.9f}")
    print(f"D_s = {sm['D_s']:.9f}")
    if sm.get("L_o") is not None:
        print(f"L_o = {sm['L_o']:.9f}  (reduced distance)")
    if sm.get("L_i") is not None:
        print(f"L_i = {sm['L_i']:.9f}  (reduced distance)")
    if sm.get("z_i") is not None:
        print(f"z_i = {sm['z_i']:.6f} mm")

    if mags:
        print("\n--- Magnifications (Plan B) ---")
        print(f"beta (lateral)        = {mags['beta']:.9f}")
        print(f"alpha (==beta)        = {mags['alpha']:.9f}")
        print(f"gamma_u (u-mag)       = {mags['gamma_u']:.9f}")
        print(f"gamma_theta (theta)   = {mags['gamma_theta']:.9f}")
        print(f"longitudinal_mag      = {mags['longitudinal_mag']:.9f}")
        print(f"focus_indicator_B (Bs)= {mags['focus_indicator_B']:.9e}")

    if newt is not None:
        print("\n--- Newton relation check ---")
        print(f"z_o   = {newt['z_o']:.6f} mm")
        print(f"z_i   = {newt['z_i']:.6f} mm")
        print(f"z_F   = {newt['z_F']:.6f} mm")
        print(f"z_F'  = {newt['z_Fp']:.6f} mm")
        print(f"x     = {newt['x']:.6f} mm")
        print(f"x'    = {newt['xprime']:.6f} mm")
        print(f"x*x'  = {newt['x_xprime']:.9e}")
        print(f"f^2   = {newt['f2']:.9e}")
        print(f"relerr= {newt['rel_err']:.3e}")
