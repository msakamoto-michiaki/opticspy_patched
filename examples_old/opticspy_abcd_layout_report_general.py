# -*- coding: utf-8 -*-
"""汎用 ABCD レポート & opticspy レイアウト描画ユーティリティ

目的:
- 任意の処方（surface list）・任意の start/end 面・任意の像面位置に対して
  - ABCD 行列（paraxial）
  - f'（EFL）
  - 主平面 H, H'
  - 像面（処方像面 vs ABCD 後焦点面）比較
  を同じ形式で表示する。

- さらに opticspy の trace.trace_draw_ray() → draw.draw_system() で
  layout-style 図を保存できる（任意）。

前提:
- opticspy はローカルに存在（例: 添付zipを展開したフォルダ）
- 環境変数 OPTICSPY_ROOT で opticspy ルートを指定可能

使い方（Example 1 相当）:
    python opticspy_abcd_layout_report_general.py

カスタム使用:
- 下の `example1_config()` をコピーして prescription / fields / wavelengths / start/end / image_surface を変更
- `run_report_and_optional_plot(cfg)` を呼ぶ

重要:
- 本スクリプトの AB​CD は opticspy の first_order_tools と同じ
  reduced-angle 形式 [y, u]^T（u = n*theta）で統一している。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


# -----------------------------------------------------------------------------
# opticspy import (lazy path injection)
# -----------------------------------------------------------------------------
def ensure_opticspy_importable(opticspy_root: Optional[str] = None) -> None:
    """Ensure local opticspy is importable by putting OPTICSPY_ROOT on sys.path."""
    root = opticspy_root or os.environ.get("OPTICSPY_ROOT", "/mnt/data/opticspy_work/opticspy-master")
    if root not in sys.path:
        sys.path.insert(0, root)
    # unwrap dependency safety (some opticspy snapshots expect it)
    try:
        import unwrap  # noqa: F401
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Data model
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class SurfaceSpec:
    """A surface in an optical prescription.

    Conventions (opticspy-compatible):
    - Surface i has:
        R_i : radius [mm]
        t_i : thickness to next surface vertex [mm]
        glass_i : medium AFTER surface i (e.g. 'air', 'S-BSM18_ohara', ...)
        stop_i : True if this surface is stop (STO)
    """
    num: int
    R: float
    t: float
    glass: str
    stop: bool = False


@dataclass(frozen=True)
class ReportConfig:
    """Configuration for ABCD report & optional drawing."""
    prescription: List[SurfaceSpec]
    field_angles_deg: List[float]
    wavelengths_nm: List[float]  # middle index used for n(λ)
    fno: float = 5.0

    # ABCD computation range
    start_surface: int = 2
    end_surface: int = 8  # typically last refracting surface

    # Image plane specification:
    image_surface: Optional[int] = None  # prescribed image plane vertex (surface number)
    image_z_abs: Optional[float] = None  # absolute z override

    # Coordinate reference for absolute z: z(reference_surface vertex)=0
    reference_surface: int = 2

    # Optional layout drawing (opticspy)
    draw_layout: bool = True
    out_png: str = "layout.png"

    # Optional opticspy root override
    opticspy_root: Optional[str] = None


# -----------------------------------------------------------------------------
# Paraxial math utilities (ray vector [y, u], u = n*theta)  <-- FIXED
# -----------------------------------------------------------------------------
def translation_matrix(t: float, n: float) -> np.ndarray:
    """Translation matrix for reduced-angle ray vector u=n*theta."""
    return np.array([[1.0, t / n],
                     [0.0, 1.0]], dtype=float)


def refraction_matrix(R: float, n1: float, n2: float) -> np.ndarray:
    """Refraction matrix for reduced-angle ray vector u=n*theta."""
    c = 0.0 if abs(R) > 1e12 else 1.0 / float(R)
    return np.array([[1.0, 0.0],
                     [-(n2 - n1) * c, 1.0]], dtype=float)


def get_refractive_index_nm(glass_name: str, wavelengths_nm: Sequence[float]) -> float:
    """Return refractive index at the *middle* wavelength for given glass."""
    if glass_name.lower() == "air":
        return 1.0
    ensure_opticspy_importable()  # so glass_funcs import works
    from opticspy.ray_tracing import glass_funcs  # type: ignore
    idx_list = glass_funcs.glass2indexlist(list(wavelengths_nm), glass_name)
    mid = int(len(idx_list) / 2)
    return float(idx_list[mid])


def compute_abcd_from_prescription(
    prescription: Sequence[SurfaceSpec],
    wavelengths_nm: Sequence[float],
    start_surface: int,
    end_surface: int,
) -> np.ndarray:
    """Compute ABCD matrix to just AFTER end_surface.

    reduced-angle convention:
      ray = [y, u]^T, u = n*theta

    Propagation:
      for i = start..end:
        - refraction at surface i : n_left (after i-1) -> n_right (after i)
        - if i < end: translate by thickness t_i in medium n_right
    """
    s = {sp.num: sp for sp in prescription}

    M = np.eye(2, dtype=float)
    for i in range(start_surface, end_surface + 1):
        if i not in s or (i - 1) not in s:
            raise ValueError(f"Surface {i} or {i-1} not found in prescription.")

        n_left = get_refractive_index_nm(s[i - 1].glass, wavelengths_nm)
        n_right = get_refractive_index_nm(s[i].glass, wavelengths_nm)

        M = refraction_matrix(s[i].R, n_left, n_right) @ M
        if i < end_surface:
            M = translation_matrix(s[i].t, n_right) @ M
    return M


def cardinals_air_air(A: float, B: float, C: float, D: float) -> Dict[str, float]:
    """Cardinal points for air->air system (reduced-angle ABCD)."""
    fprime = -1.0 / C
    h = (D - 1.0) / C
    hprime = (A - 1.0) / C
    bfl = -A / C
    ffl = -D / C
    return {"fprime": fprime, "h": h, "hprime": hprime, "BFL": bfl, "FFL": ffl}


def z_vertices_absolute(
    prescription: Sequence[SurfaceSpec],
    reference_surface: int = 2
) -> Dict[int, float]:
    """Return absolute z of each surface vertex with z(reference_surface vertex)=0."""
    s = {sp.num: sp for sp in prescription}
    if reference_surface not in s:
        raise ValueError(f"reference_surface={reference_surface} not in prescription.")

    z: Dict[int, float] = {reference_surface: 0.0}
    cur = 0.0
    max_num = max(s.keys())
    for i in range(reference_surface, max_num):
        if i not in s:
            break
        cur += float(s[i].t)
        z[i + 1] = cur
    return z


# -----------------------------------------------------------------------------
# Reporting
# -----------------------------------------------------------------------------
def compute_report(cfg: ReportConfig) -> Dict[str, Any]:
    M = compute_abcd_from_prescription(cfg.prescription, cfg.wavelengths_nm, cfg.start_surface, cfg.end_surface)
    A, B, C, D = float(M[0, 0]), float(M[0, 1]), float(M[1, 0]), float(M[1, 1])
    card = cardinals_air_air(A, B, C, D)

    z = z_vertices_absolute(cfg.prescription, cfg.reference_surface)
    z_end = z.get(cfg.end_surface)
    if z_end is None:
        raise ValueError("Could not compute z for end_surface; check numbering and reference_surface.")

    zH = card["h"]
    zHp = z_end - card["hprime"]
    z_img_abcd = z_end + card["BFL"]

    # prescribed image plane
    z_img_prescribed: Optional[float] = None
    if cfg.image_surface is not None:
        z_img_prescribed = z.get(cfg.image_surface)
        if z_img_prescribed is None:
            raise ValueError(f"image_surface={cfg.image_surface} not in computed z vertices.")
    if cfg.image_z_abs is not None:
        z_img_prescribed = float(cfg.image_z_abs)

    # matrix to image plane (if surface specified)
    M_to_img = None
    if cfg.image_surface is not None and cfg.image_surface in z:
        dz = z[cfg.image_surface] - z_end
        # reduced-angle translation uses n of medium after end_surface
        s = {sp.num: sp for sp in cfg.prescription}
        n_after_end = get_refractive_index_nm(s[cfg.end_surface].glass, cfg.wavelengths_nm)
        M_to_img = translation_matrix(dz, n_after_end) @ M

    return {
        "ABCD": {"A": A, "B": B, "C": C, "D": D},
        "cardinals": card,
        "z": z,
        "zH": zH,
        "zHp": zHp,
        "z_end": z_end,
        "z_img_prescribed": z_img_prescribed,
        "z_img_abcd": z_img_abcd,
        "M_to_img": M_to_img,
        "cfg": cfg,
    }


def print_report(rep: Dict[str, Any]) -> None:
    cfg: ReportConfig = rep["cfg"]
    A = rep["ABCD"]["A"]; B = rep["ABCD"]["B"]; C = rep["ABCD"]["C"]; D = rep["ABCD"]["D"]
    fprime = rep["cardinals"]["fprime"]
    zH = rep["zH"]; zHp = rep["zHp"]
    z_img_prescribed = rep["z_img_prescribed"]
    z_img_abcd = rep["z_img_abcd"]
    M_to_img = rep["M_to_img"]

    print("========================================================================")
    print("Paraxial (ABCD) results (air -> air), using middle-wavelength indices")
    print("Ray vector: [y, u]^T where u = n*theta  (reduced angle).") 
    print("Distances in mm, light travels +z (left to right).") 
    print("========================================================================\n")

    print(f"System matrix to last refracting surface (just after surface {cfg.end_surface}):")
    print(f"  A={A:.10f}, B={B:.8f}")
    print(f"  C={C:.12f}, D={D:.10f}\n")

    if M_to_img is not None:
        A2, B2, C2, D2 = float(M_to_img[0, 0]), float(M_to_img[0, 1]), float(M_to_img[1, 0]), float(M_to_img[1, 1])
        print("System matrix to image plane (including end_surface -> image translation):")
        print(f"  A={A2:.10e}, B={B2:.7f}")
        print(f"  C={C2:.12f}, D={D2:.10f}\n")

    print("Effective focal length (EFL):")
    print(f"  f' = -1/C = {fprime:.8f} mm\n")

    print(f"Principal planes (absolute z, with z(surface{cfg.reference_surface} vertex)=0):")
    print(f"  H  position z(H)  = {zH:.8f} mm")
    print(f"  H' position z(H') = {zHp:.8f} mm\n")

    print("Image plane check (prescription vs ABCD back focal plane):")
    if z_img_prescribed is None:
        print("  Prescribed image plane: (not specified)")
    else:
        print(f"  Prescribed image plane z = {z_img_prescribed:.8f} mm")
        print(f"  Difference (ABCD - prescribed)      = {(z_img_abcd - z_img_prescribed):.8e} mm")
    print(f"  ABCD back focal plane z  = {z_img_abcd:.8f} mm")

    print("\nNOTE: 差が 0 にならない場合、処方の像面位置がパラキシャル後焦点面(BFL)と") 
    print("      一致していないことを意味します。像面をパラキシャル焦点に合わせたいなら") 
    print("      像面位置を z_end + BFL に設定してください。")
    print("========================================================================")


# -----------------------------------------------------------------------------
# opticspy build + plot
# -----------------------------------------------------------------------------
def build_opticspy_lens(cfg: ReportConfig):
    ensure_opticspy_importable(cfg.opticspy_root)
    from opticspy.ray_tracing import lens  # type: ignore

    L = lens.Lens(lens_name="Custom", creator="opticspy_abcd_report")
    # Some opticspy snapshots share this list; clear for safety.
    L.surface_list = []

    L.FNO = cfg.fno
    L.wavelength_list = list(cfg.wavelengths_nm)

    for ang in cfg.field_angles_deg:
        L.add_field_YAN(angle=float(ang))

    for sp in cfg.prescription:
        L.add_surface(
            number=int(sp.num),
            radius=float(sp.R),
            thickness=float(sp.t),
            glass=sp.glass,
            STO=bool(sp.stop),
            output=False,
        )

    L.refresh_paraxial()
    return L


def draw_layout_png(cfg: ReportConfig) -> str:
    ensure_opticspy_importable(cfg.opticspy_root)
    from opticspy.ray_tracing import trace, draw  # type: ignore

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_png = cfg.out_png
    out_dir = os.path.dirname(os.path.abspath(out_png))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    L = build_opticspy_lens(cfg)

    _ = trace.trace_draw_ray(L)

    old_show = plt.show

    def _save_show(*args, **kwargs):
        plt.savefig(out_png, dpi=200, bbox_inches="tight")
        plt.close("all")

    plt.show = _save_show
    try:
        draw.draw_system(L)
    finally:
        plt.show = old_show

    return os.path.abspath(out_png)


# -----------------------------------------------------------------------------
# Orchestrator
# -----------------------------------------------------------------------------
def run_report_and_optional_plot(cfg: ReportConfig) -> Dict[str, Any]:
    rep = compute_report(cfg)
    print_report(rep)
    if cfg.draw_layout:
        out = draw_layout_png(cfg)
        print(f"\nSaved layout PNG -> {out}")
    return rep


# -----------------------------------------------------------------------------
# Example configuration (Example 1 as pasted by you)
# -----------------------------------------------------------------------------
def example1_config(out_png: str = "example1_layout.png") -> ReportConfig:
    prescription = [
        SurfaceSpec(1, 10000000.0, 1000000.0, "air", False),
        SurfaceSpec(2, 41.15909,   6.097555,  "S-BSM18_ohara", False),
        SurfaceSpec(3, -957.83146, 9.349584,  "air", False),
        SurfaceSpec(4, -51.32104,  2.032518,  "N-SF2_schott", False),
        SurfaceSpec(5, 42.37768,   5.995929,  "air", False),
        SurfaceSpec(6, 10000000.0, 4.065037,  "air", True),   # STOP
        SurfaceSpec(7, 247.44562,  6.097555,  "S-BSM18_ohara", False),
        SurfaceSpec(8, -40.04016,  85.593426, "air", False),
        SurfaceSpec(9, 10000000.0, 0.0,       "air", False),  # image plane
    ]
    return ReportConfig(
        prescription=prescription,
        field_angles_deg=[0, 14, 20],
        wavelengths_nm=[587.6, 656.3, 486.1],
        fno=5.0,
        start_surface=2,
        end_surface=8,
        image_surface=9,
        image_z_abs=None,
        reference_surface=2,
        draw_layout=True,
        out_png=out_png,
        opticspy_root=None,
    )


def main():
    cfg = example1_config(out_png=os.environ.get("OUT_PNG", "example1_layout_general.png"))
    run_report_and_optional_plot(cfg)


if __name__ == "__main__":
    main()
