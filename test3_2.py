"""test3_2.py

example3（petzval.seq）に対応するテスト。

機能:
  (1) .seq を読み込み test1_1 形式（SurfaceSpec/ReportConfig/SeqConditions）に変換
  (2) YAML で保存
  (3) YAML を読み込み直して復元（確認用）
  (4) draw_system / grid_generator / spotdiagram / Ray_fan を実行（example3相当）
  (5) test1_1 と同じ Fixed-style ABCD / Principal plane report を表示
"""

import os

from optics.abcd_report import (
    compute_report,
    build_opticspy_lens,
    first_order_like_opticspy,
    compute_abcd_from_prescription,
    efl_from_abcd,
    oal_from_prescription,
)
from optics.seq_convert import (
    parse_seq_file,
    build_report_config_from_seq,
    pick_field_angles_deg,
    pick_fno,
)
from optics.yaml_io import (
    dump_seq_document,
    dump_surface_specs,
    dump_seq_conditions,
    dump_report_config,
    load_seq_document,
    load_report_config,
)
from utils.plotting import setup_matplotlib_headless, rename_fixed_png, rename_latest_spotdiagram

# -------------------------------------------------
# Setup
# -------------------------------------------------
setup_matplotlib_headless()

outdir = os.path.join("out", "examples", "test3_2")
yamldir = os.path.join(outdir, "yaml")
os.makedirs(yamldir, exist_ok=True)

# -------------------------------------------------
# (1) Parse .seq -> test1_1 style objects
# -------------------------------------------------
seq_path = os.path.join("ex_CodeV", "petzval.seq")
doc = parse_seq_file(seq_path)

from dataclasses import replace

cfg0 = build_report_config_from_seq(doc)
# Finite conjugate test mode (Plan B): set object plane and use paraxial image plane (Bs=0)
cfg = replace(
    cfg0,
    object_distance_mm=-500.0,
    image_mode="paraxial",
)
# example3 は FNO をスクリプト側で 2 に上書きしていたので fallback=2.0
field_angles_deg = pick_field_angles_deg(doc.conditions)
fno = pick_fno(doc.conditions, fallback_fno=2.0)

# -------------------------------------------------
# (2) Save YAML
# -------------------------------------------------
dump_seq_document(os.path.join(yamldir, "petzval.doc.yaml"), doc)
dump_surface_specs(os.path.join(yamldir, "petzval.specs.yaml"), doc.prescription)
dump_seq_conditions(os.path.join(yamldir, "petzval.cond.yaml"), doc.conditions)
dump_report_config(os.path.join(yamldir, "petzval.cfg.yaml"), cfg)

# -------------------------------------------------
# (3) Load YAML back (sanity / confirmation)
# -------------------------------------------------
doc2 = load_seq_document(os.path.join(yamldir, "petzval.doc.yaml"))
cfg2 = load_report_config(os.path.join(yamldir, "petzval.cfg.yaml"))
print(f"[YAML reload] surfaces: {len(doc.prescription)} -> {len(doc2.prescription)}")
print(f"[YAML reload] WL: {doc.conditions.wavelengths} -> {doc2.conditions.wavelengths}")

# -------------------------------------------------
# ABCD report (computed from cfg2)
# -------------------------------------------------
rep = compute_report(cfg2)

# -------------------------------------------------
# (4) Draw / analyses (example3 相当)
# -------------------------------------------------
L = build_opticspy_lens(
    prescription=cfg2.prescription,
    wavelengths_nm=cfg2.wavelengths_nm,
    field_angles_deg=field_angles_deg,
    fno=fno,
    opticspy_root=cfg2.opticspy_root,
    lens_name="Petzval",
    creator="test3_2",
)

# Finite conjugate mode: set opticspy object position (used by image_position)
L.object_position = float(cfg2.object_distance_mm)

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
opt_efl_full = _quiet_call(fot.EFL, L, cfg2.start_surface, cfg2.end_surface)
opt_efl_23 = _quiet_call(fot.EFL, L, 2, 3)
opt_bfl_recipe = _quiet_call(fot.BFL, L)
opt_img_pos = _quiet_call(fot.image_position, L)
opt_ep = _quiet_call(fot.EP, L)
opt_ex = _quiet_call(fot.EX, L)
opt_oal_27 = _quiet_call(fot.OAL, L, 2, 7)

# our ABCD direct (same formulas as opticspy) from cfg2
our = first_order_like_opticspy(cfg2, object_distance=L.object_position)
M23 = compute_abcd_from_prescription(cfg2.prescription, cfg2.wavelengths_nm, 2, 3, opticspy_root=cfg2.opticspy_root)
C23 = float(M23[1, 0])
our_efl_23 = efl_from_abcd(C23)
our_oal_27 = oal_from_prescription(cfg2.prescription, 2, 7)

print("\n============================================")
print(" First-order comparison (opticspy vs ABCD direct)")
print("============================================")
print(f"EFY full (2..{cfg2.end_surface})  opticspy={opt_efl_full:.9f}  ours={our['efl']:.9f}  Δ={opt_efl_full-our['efl']:+.3e}")
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
    tag="test3_2_",
)

# ---- circular ----
field.grid_generator(6, grid_type="circular", output=1)
rename_fixed_png(
    "out/opticspy_ray_tracing_field__grid_generator.png",
    outdir,
    tag="test3_2_circular_n6",
)
analysis.spotdiagram(L, [1, 2, 3], [1, 2, 3], n=6, grid_type="circular")
rename_latest_spotdiagram(outdir, tag="test3_2_spot_circular_n6")

# ---- ray fan ----
analysis.Ray_fan(L, [1, 2, 3], [1, 2, 3])
rename_fixed_png(
    "out/opticspy_ray_tracing_analysis__Ray_fan.png",
    outdir,
    tag="test3_2_",
)

# -------------------------------------------------
# (5) Extract/Print (same format as test1_1)
# -------------------------------------------------
A = rep["ABCD"]["A"]
B = rep["ABCD"]["B"]
C = rep["ABCD"]["C"]
D = rep["ABCD"]["D"]
card = rep["cardinals"]

# middle wavelength for label
wls = cfg2.wavelengths_nm
nd = wls[len(wls) // 2] if wls else float("nan")

print("============================================")
print(" Fixed-style ABCD / Principal plane report ")
print(f" (reduced-angle [y, u], nd = {nd} nm)")
print("============================================")
print(f"start surface: {cfg2.start_surface}")
print(f"end surface: {cfg2.end_surface}")

print(f"A = {A:.9f}")
print(f"B = {B:.9f}")
print(f"C = {C:.9f}")
print(f"D = {D:.9f}")

print("\n--- Cardinal points ---")
print(f"f'  = {card['fprime']:.6f} mm")
print(f"H   = {rep['zH']:.6f} mm  (from surface {cfg2.reference_surface} vertex)")
print(f"H'  = {rep['zHp']:.6f} mm (from surface {cfg2.end_surface} vertex)")
print(f"BFL = {card['BFL']:.6f} mm")

print("\n--- Image plane check ---")
z_end = rep["z"].get(cfg2.end_surface)
print(f"z{cfg2.end_surface}           = {z_end:.6f}")
if rep.get("z_img_prescribed") is not None:
    print(f"z{cfg2.image_surface} (recipe)  = {rep['z_img_prescribed']:.6f}")
print(f"z{cfg2.end_surface} + BFL     = {rep['z_img_abcd']:.6f}")
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
