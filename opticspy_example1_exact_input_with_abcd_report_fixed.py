
# -*- coding: utf-8 -*-
"""Example 1（あなたが提示した入力）を opticspy で再現し、
同じ入力から nd(587.6nm) 屈折率で ABCD を再計算して

- f'
- 主平面 H, H'
- 像面（処方像面 z9） vs ABCD 後焦点面（z8 + BFL）

を表示します。

さらに trace.trace_draw_ray() → draw.draw_system() の流れでレイアウト図も保存します。

※ Colab などで /mnt/data が無い場合でも落ちないように、出力先フォルダを自動作成します。
"""

import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ====== 設定（必要ならここだけ変えてOK） ======
OPTICSPY_ROOT = os.environ.get("OPTICSPY_ROOT", "/mnt/data/opticspy_work/opticspy-master")
OUT_PNG = os.environ.get("OUT_PNG", "opticspy_example1_exact_input_with_abcd_report.png")

WL_NM = [587.6, 656.3, 486.1]  # d/C/F (nm) : nd uses 587.6nm

# ---- import local opticspy ----
if OPTICSPY_ROOT not in sys.path:
    sys.path.insert(0, OPTICSPY_ROOT)

try:
    import unwrap  # noqa: F401
except Exception:
    pass

from opticspy.ray_tracing import lens, trace, draw, glass_funcs

def _ensure_dir_for_file(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and (not os.path.exists(d)):
        os.makedirs(d, exist_ok=True)

def n_d(glass_name: str) -> float:
    if glass_name.lower() == "air":
        return 1.0
    idx_list = glass_funcs.glass2indexlist(WL_NM, glass_name)
    return float(idx_list[int(len(idx_list)/2)])

def T(t: float):
    return np.array([[1.0, t],
                     [0.0, 1.0]], dtype=float)

def R_surf(R: float, n1: float, n2: float):
    c = 0.0 if abs(R) > 1e12 else 1.0/float(R)
    # ray vector [y, theta]
    return np.array([[1.0, 0.0],
                     [(n1 - n2)*c/n2, n1/n2]], dtype=float)

def abcd_from_prescription(surfaces, start_surface=2, end_surface=8):
    # Returns matrix to just AFTER end_surface.
    M = np.eye(2)
    for i in range(start_surface, end_surface+1):
        s_i = surfaces[i-1]
        s_im1 = surfaces[i-2]
        n_left = n_d(s_im1["glass"])
        n_right = n_d(s_i["glass"])
        M = R_surf(s_i["R"], n_left, n_right) @ M
        if i < end_surface:
            M = T(s_i["t"]) @ M
    return M

def cardinals_air_air(A,B,C,D):
    fprime = -1.0/C
    h  = (D - 1.0)/C         # from surface2 vertex (z=0) to H
    hprime = (A - 1.0)/C     # distance from surface8 vertex to H' (to the left)
    BFL = -A/C               # from surface8 vertex to back focus (to the right)
    return fprime, h, hprime, BFL

def prescription_dicts():
    # exactly your pasted Example1 input
    return [
        dict(num=1, R=10000000.0,  t=1000000.0,   glass="air",           stop=False),
        dict(num=2, R=41.15909,    t=6.097555,    glass="S-BSM18_ohara", stop=False),
        dict(num=3, R=-957.83146,  t=9.349584,    glass="air",           stop=False),
        dict(num=4, R=-51.32104,   t=2.032518,    glass="N-SF2_schott",  stop=False),
        dict(num=5, R=42.37768,    t=5.995929,    glass="air",           stop=False),
        dict(num=6, R=10000000.0,  t=4.065037,    glass="air",           stop=True),
        dict(num=7, R=247.44562,   t=6.097555,    glass="S-BSM18_ohara", stop=False),
        dict(num=8, R=-40.04016,   t=85.593426,   glass="air",           stop=False),
        dict(num=9, R=10000000.0,  t=0.0,         glass="air",           stop=False),
    ]

def z_vertices_from_surface2(surfaces):
    # z(surface2)=0
    z = {2: 0.0}
    cur = 0.0
    for s in range(2, 9):  # add t_s to reach vertex s+1
        cur += float(surfaces[s-1]["t"])
        z[s+1] = cur
    return z

def report_abcd():
    surfaces = prescription_dicts()
    M = abcd_from_prescription(surfaces, start_surface=2, end_surface=8)
    A,B,C,D = float(M[0,0]), float(M[0,1]), float(M[1,0]), float(M[1,1])

    fprime, h, hprime, BFL = cardinals_air_air(A,B,C,D)

    z = z_vertices_from_surface2(surfaces)
    z8 = z[8]
    z9 = z[9]  # prescribed image plane vertex

    zH  = h
    zHp = z8 - hprime
    z_img_abcd = z8 + BFL

    print("========================================================================")
    print("Paraxial (ABCD) results for Example 1 (air -> air), using nd indices")
    print("Ray vector: [y, theta]^T, distances in mm, light travels +z (left to right).")
    print("========================================================================\n")
    print("System matrix to last refracting surface (just after surface 8):")
    print("  A={:.10f}, B={:.8f}".format(A,B))
    print("  C={:.12f}, D={:.10f}\n".format(C,D))

    # include translation to image plane
    M_img = T(surfaces[7]["t"]) @ M
    A2,B2,C2,D2 = float(M_img[0,0]), float(M_img[0,1]), float(M_img[1,0]), float(M_img[1,1])
    print("System matrix to image plane (including surface8 -> image translation):")
    print("  A={:.10e}, B={:.7f}".format(A2,B2))
    print("  C={:.12f}, D={:.10f}\n".format(C2,D2))

    print("Effective focal length (EFL):")
    print("  f' = -1/C = {:.8f} mm\n".format(fprime))

    print("Principal planes (absolute z, with z(surface2 vertex)=0):")
    print("  H  position z(H)  = {:.8f} mm".format(zH))
    print("  H' position z(H') = {:.8f} mm\n".format(zHp))

    print("Image plane check (prescription vs ABCD back focal plane):")
    print("  Prescribed image plane z (surface9) = {:.8f} mm".format(z9))
    print("  ABCD back focal plane z (z8 + BFL)  = {:.8f} mm".format(z_img_abcd))
    print("  Difference (ABCD - prescribed)      = {:.8e} mm".format(z_img_abcd - z9))
    print("\nNOTE: この差が 0 にならない場合、処方の像面距離(t8=85.593426)が")
    print("      ndのパラキシャル後焦点距離(BFL)と一致していない、という意味です。")
    print("      パラキシャル焦点に合わせたいなら、t8 を BFL に置き換えると一致します。")
    print("========================================================================")

def build_lens_for_drawing():
    L = lens.Lens(lens_name="Triplet", creator="XF")
    L.surface_list = []  # safety for this snapshot
    L.FNO = 5
    L.wavelength_list = WL_NM[:]

    L.add_field_YAN(angle=0)
    L.add_field_YAN(angle=14)
    L.add_field_YAN(angle=20)

    L.add_surface(number=1, radius=10000000, thickness=1000000, glass='air', output=False)
    L.add_surface(number=2, radius=41.15909,  thickness=6.097555,  glass='S-BSM18_ohara', output=False)
    L.add_surface(number=3, radius=-957.83146, thickness=9.349584, glass='air', output=False)
    L.add_surface(number=4, radius=-51.32104, thickness=2.032518, glass='N-SF2_schott', output=False)
    L.add_surface(number=5, radius=42.37768,  thickness=5.995929,  glass='air', output=False)
    L.add_surface(number=6, radius=10000000, thickness=4.065037,  glass='air', STO=True, output=False)
    L.add_surface(number=7, radius=247.44562, thickness=6.097555, glass='S-BSM18_ohara', output=False)
    L.add_surface(number=8, radius=-40.04016, thickness=85.593426, glass='air', output=False)
    L.add_surface(number=9, radius=10000000, thickness=0,        glass='air', output=False)

    L.refresh_paraxial()
    return L

def save_layout_png(L, out_png):
    _ensure_dir_for_file(out_png)

    # tutorial flow
    _ = trace.trace_draw_ray(L)

    _old_show = plt.show
    def _save_show(*args, **kwargs):
        plt.savefig(out_png, dpi=200, bbox_inches="tight")
        plt.close("all")
    plt.show = _save_show
    try:
        draw.draw_system(L)
    finally:
        plt.show = _old_show

def main():
    report_abcd()
    L = build_lens_for_drawing()
    save_layout_png(L, OUT_PNG)
    print("\nSaved layout PNG ->", os.path.abspath(OUT_PNG))

if __name__ == "__main__":
    main()
