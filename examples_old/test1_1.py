# test1_1.py
#
# Test using opticspy_abcd_layout_report_general.py
# (no opticspy first_order_tools, no assumed ABCD)

from opticspy_abcd_layout_report_general import (
    SurfaceSpec,
    ReportConfig,
    compute_report,
)

# -------------------------------------------------
# Prescription (same as example1)
# -------------------------------------------------
prescription = [
    SurfaceSpec(1, 10000000.0, 1000000.0, "air"),
    SurfaceSpec(2, 41.15909,   6.097555,  "S-BSM18_ohara"),
    SurfaceSpec(3, -957.83146, 9.349584,  "air"),
    SurfaceSpec(4, -51.32104,  2.032518,  "N-SF2_schott"),
    SurfaceSpec(5, 42.37768,   5.995929,  "air"),
    SurfaceSpec(6, 10000000.0, 4.065037,  "air", True),  # STOP
    SurfaceSpec(7, 247.44562,  6.097555,  "S-BSM18_ohara"),
    SurfaceSpec(8, -40.04016,  85.593426, "air"),
    SurfaceSpec(9, 10000000.0, 0.0,       "air"),       # image plane
]

# -------------------------------------------------
# Report configuration
# -------------------------------------------------
cfg = ReportConfig(
    prescription=prescription,
    field_angles_deg=[0, 14, 20],
    wavelengths_nm=[656.3, 587.6, 486.1],
    fno=5.0,
    start_surface=2,
    end_surface=8,
    image_surface=9,
    reference_surface=2,
    draw_layout=False,   # testでは描画しない
)

# -------------------------------------------------
# Compute report
# -------------------------------------------------
rep = compute_report(cfg)

# -------------------------------------------------
# Extract & print (same numbers as example1_1.py)
# -------------------------------------------------
A = rep["ABCD"]["A"]
B = rep["ABCD"]["B"]
C = rep["ABCD"]["C"]
D = rep["ABCD"]["D"]

card = rep["cardinals"]

print("============================================")
print(" Fixed-style ABCD / Principal plane report ")
print(" (reduced-angle [y, theta], nd = 587.6 nm)")
print("============================================")
print("start surface: 2")
print("end surface: 8")

print(f"A = {A:.9f}")
print(f"B = {B:.9f}")
print(f"C = {C:.9f}")
print(f"D = {D:.9f}")

print("\n--- Cardinal points ---")
print(f"f'  = {card['fprime']:.6f} mm")
print(f"H   = {rep['zH']:.6f} mm  (from surface 2 vertex)")
print(f"H'  = {rep['zHp']:.6f} mm (from surface 8 vertex)")
print(f"BFL = {card['BFL']:.6f} mm")

print("\n--- Image plane check ---")
print(f"z8           = {rep['z'][8]:.6f}")
print(f"z9 (recipe)  = {rep['z_img_prescribed']:.6f}")
print(f"z8 + BFL     = {rep['z_img_abcd']:.6f}")
print(f"Δz           = {(rep['z_img_prescribed'] - rep['z_img_abcd']):.9e} mm")
