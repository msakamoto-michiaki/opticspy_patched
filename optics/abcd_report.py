# -*- coding: utf-8 -*-
"""ABCD (paraxial) report core utilities.

This module is the *minimal* core that tests can import.

Design goals
------------
- No printing / CLI helpers.
- No matplotlib hacks or file saving.
- Optional opticspy Lens builder is provided, but drawing should be done by the caller.

Conventions
-----------
ABCD uses the **reduced-angle** ray vector:

    ray = [y, u]^T,  u = n * theta

This matches opticspy's first-order tooling.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .abcd_common import cardinals_air_air_full as _cardinals_air_air_full


# -----------------------------------------------------------------------------
# opticspy import (lazy path injection)
# -----------------------------------------------------------------------------
def ensure_opticspy_importable(opticspy_root: Optional[str] = None) -> None:
    """Ensure local opticspy is importable by putting OPTICSPY_ROOT on sys.path."""
    root = opticspy_root or os.environ.get("OPTICSPY_ROOT", "/mnt/data/opticspy_work/opticspy-master")
    if root and root not in sys.path:
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
    - Surface *i* stores the medium **after** the surface in ``glass``.
      (So refraction at surface i uses glass of i-1 -> glass of i.)
    - ``stop`` is kept for compatibility when building an opticspy Lens.
    """

    num: int
    R: float
    t: float
    glass: str
    stop: bool = False


@dataclass(frozen=True)
class ReportConfig:
    """Configuration for ABCD report computation."""

    prescription: List[SurfaceSpec]
    wavelengths_nm: List[float]  # middle index used for n(λ)

    # ABCD computation range
    start_surface: int = 2
    end_surface: int = 8  # typically last refracting surface

    # Image plane specification:
    image_surface: Optional[int] = None  # prescribed image plane vertex (surface number)
    image_z_abs: Optional[float] = None  # absolute z override

    # Image plane selection mode (for magnification / Newton checks):
    # - 'recipe'  : use z(image_surface) unless image_z_abs is provided
    # - 'paraxial': use paraxial focus plane z_end + BFL (=-A/C)
    # - 'absolute': use image_z_abs as absolute z
    image_mode: str = "recipe"

    # Conjugate specification (finite conjugates):
    # object_distance_mm is the absolute z of the object plane with
    # z(reference_surface vertex)=0. Typically object is on the left so z<0.
    # None means infinity (angular input; no Newton check).
    object_distance_mm: Optional[float] = None
    object_medium: str = "air"

    # Medium between end_surface and image plane (usually air)
    image_medium: str = "air"

    # Coordinate reference for absolute z: z(reference_surface vertex)=0
    reference_surface: int = 2

    # Optional opticspy root override (used for glass index lookup)
    opticspy_root: Optional[str] = None


# -----------------------------------------------------------------------------
# Paraxial math utilities (ray vector [y, u], u = n*theta)
# -----------------------------------------------------------------------------
def translation_matrix(t: float, n: float) -> np.ndarray:
    """Translation matrix for reduced-angle ray vector u=n*theta."""

    return np.array([[1.0, t / n], [0.0, 1.0]], dtype=float)


def refraction_matrix(R: float, n1: float, n2: float) -> np.ndarray:
    """Refraction matrix for reduced-angle ray vector u=n*theta."""

    c = 0.0 if abs(R) > 1e12 else 1.0 / float(R)
    return np.array([[1.0, 0.0], [-(n2 - n1) * c, 1.0]], dtype=float)


def get_refractive_index_nm(
    glass_name: str,
    wavelengths_nm: Sequence[float],
    opticspy_root: Optional[str] = None,
) -> float:
    """Return refractive index at the *middle* wavelength for given glass."""

    if glass_name.lower() == "air":
        return 1.0
    ensure_opticspy_importable(opticspy_root)
    from opticspy.ray_tracing import glass_funcs  # type: ignore

    idx_list = glass_funcs.glass2indexlist(list(wavelengths_nm), glass_name)
    mid = int(len(idx_list) / 2)
    return float(idx_list[mid])


def compute_abcd_from_prescription(
    prescription: Sequence[SurfaceSpec],
    wavelengths_nm: Sequence[float],
    start_surface: int,
    end_surface: int,
    opticspy_root: Optional[str] = None,
) -> np.ndarray:
    """Compute ABCD matrix to just AFTER end_surface.

    reduced-angle convention:
        ray = [y, u]^T, u = n*theta

    Propagation:
        for i = start..end:
          - refraction at surface i: n_left (after i-1) -> n_right (after i)
          - if i < end: translate by thickness t_i in medium n_right
    """

    s = {sp.num: sp for sp in prescription}
    M = np.eye(2, dtype=float)

    for i in range(start_surface, end_surface + 1):
        if i not in s or (i - 1) not in s:
            raise ValueError(f"Surface {i} or {i-1} not found in prescription.")

        n_left = get_refractive_index_nm(s[i - 1].glass, wavelengths_nm, opticspy_root)
        n_right = get_refractive_index_nm(s[i].glass, wavelengths_nm, opticspy_root)

        M = refraction_matrix(s[i].R, n_left, n_right) @ M
        if i < end_surface:
            M = translation_matrix(s[i].t, n_right) @ M

    return M


def cardinals_air_air(A: float, B: float, C: float, D: float) -> Dict[str, float]:
    """Cardinal points for air->air system (reduced-angle ABCD)."""

    return _cardinals_air_air_full(A, B, C, D)


def z_vertices_absolute(prescription: Sequence[SurfaceSpec], reference_surface: int = 2) -> Dict[int, float]:
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


def compute_report(cfg: ReportConfig) -> Dict[str, Any]:
    """Compute ABCD + cardinal points + absolute-z bookkeeping."""

    M = compute_abcd_from_prescription(
        cfg.prescription,
        cfg.wavelengths_nm,
        cfg.start_surface,
        cfg.end_surface,
        opticspy_root=cfg.opticspy_root,
    )
    A, B, C, D = float(M[0, 0]), float(M[0, 1]), float(M[1, 0]), float(M[1, 1])
    card = cardinals_air_air(A, B, C, D)

    z = z_vertices_absolute(cfg.prescription, cfg.reference_surface)
    z_start = z.get(cfg.start_surface)
    if z_start is None:
        raise ValueError("Could not compute z for start_surface; check numbering and reference_surface.")

    z_end = z.get(cfg.end_surface)
    if z_end is None:
        raise ValueError("Could not compute z for end_surface; check numbering and reference_surface.")

    # Absolute principal planes (absolute z, referenced to reference_surface vertex)
    # Cardinal points are expressed relative to the lens matrix input/output reference planes.
    # h is measured from start_surface vertex; hprime is measured from end_surface vertex.
    zH = float(z_start + card["h"])  # H absolute z
    zHp = float(z_end - card["hprime"])  # H' absolute z
    z_img_abcd = float(z_end + card["BFL"])  # paraxial focus plane for infinity (air->air)

    # Paraxial image plane for *finite conjugates* (Plan B):
    # if object_distance_mm is set, choose z such that Bs=0 for object plane -> image plane
    n_o = get_refractive_index_nm(cfg.object_medium, cfg.wavelengths_nm, cfg.opticspy_root)
    n_i = get_refractive_index_nm(cfg.image_medium, cfg.wavelengths_nm, cfg.opticspy_root)
    if cfg.object_distance_mm is None:
        z_img_paraxial = float(z_img_abcd)
    else:
        # Reduced distance Lo from object plane to start_surface vertex
        d_o = float(z_start) - float(cfg.object_distance_mm)
        L_o = d_o / float(n_o)
        # Solve Li from Bs=0: Bs=(A*Lo+B) + (C*Lo+D)*Li = 0
        denom = (float(C) * float(L_o) + float(D))
        if denom == 0:
            z_img_paraxial = float('nan')
        else:
            L_i = - (float(A) * float(L_o) + float(B)) / denom
            d_i = float(L_i) * float(n_i)
            z_img_paraxial = float(z_end + d_i)

    # Determine a prescribed/selected image plane z (absolute)
    # - recipe: use image_surface vertex unless image_z_abs override
    # - paraxial: use z_img_abcd
    # - absolute: use image_z_abs
    img_surface_default = cfg.image_surface or max(sp.num for sp in cfg.prescription)
    z_img_recipe: Optional[float] = None
    if img_surface_default in z:
        z_img_recipe = float(z[img_surface_default])

    mode = str(cfg.image_mode or "recipe").lower()
    if mode not in {"recipe", "paraxial", "absolute"}:
        raise ValueError(f"Unsupported image_mode={cfg.image_mode!r}. Use 'recipe'|'paraxial'|'absolute'.")

    z_img_selected: Optional[float]
    if mode == "paraxial":
        z_img_selected = z_img_paraxial
    elif mode == "absolute":
        if cfg.image_z_abs is None:
            raise ValueError("image_mode='absolute' requires image_z_abs to be set")
        z_img_selected = float(cfg.image_z_abs)
    else:  # recipe
        z_img_selected = float(cfg.image_z_abs) if cfg.image_z_abs is not None else z_img_recipe

    # For backward-compatibility with existing logs:
    z_img_prescribed = z_img_selected

    # matrix to image plane (if an absolute image z is known)
    M_to_img = None
    if z_img_selected is not None:
        dz = float(z_img_selected - z_end)
        s = {sp.num: sp for sp in cfg.prescription}
        n_after_end = get_refractive_index_nm(s[cfg.end_surface].glass, cfg.wavelengths_nm, cfg.opticspy_root)
        M_to_img = translation_matrix(dz, n_after_end) @ M

    # System matrix (object plane -> image plane) for magnification/Newton checks.
    system_matrix = compute_system_matrix(cfg, A=A, B=B, C=C, D=D, z_end=z_end, z_img=z_img_selected)
    magnifications = compute_magnifications(cfg, system_matrix)
    newton_check = compute_newton_check(cfg, card, z_end=z_end, zH=zH, zHp=zHp, z_img=z_img_selected)

    return {
        "ABCD": {"A": A, "B": B, "C": C, "D": D},
        "cardinals": card,
        "z": z,
        "zH": zH,
        "zHp": zHp,
        "z_end": z_end,
        "z_img_prescribed": z_img_prescribed,
        "z_img_recipe": z_img_recipe,
        "z_img_mode": mode,
        "z_img_abcd": z_img_abcd,
        "z_img_paraxial": z_img_paraxial,
        "M_to_img": M_to_img,
        "system_matrix": system_matrix,
        "magnifications": magnifications,
        "newton_check": newton_check,
        "cfg": cfg,
    }


def compute_system_matrix(
    cfg: ReportConfig,
    *,
    A: Optional[float] = None,
    B: Optional[float] = None,
    C: Optional[float] = None,
    D: Optional[float] = None,
    z_end: Optional[float] = None,
    z_img: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute system matrix M_sys = T_i @ M_lens @ T_o.

    The lens matrix M_lens is taken from start_surface..end_surface.
    Object plane is at z_o = cfg.object_distance_mm (absolute z with z(ref)=0).
    Image plane is chosen by cfg.image_mode and z_img (if provided).

    Returns a dict with:
      - A_s,B_s,C_s,D_s
      - L_o,L_i (reduced distances)
      - n_o,n_i
      - z_o,z_i,z_end
    """

    # Lens matrix
    if A is None or B is None or C is None or D is None:
        M = compute_abcd_from_prescription(
            cfg.prescription,
            cfg.wavelengths_nm,
            cfg.start_surface,
            cfg.end_surface,
            opticspy_root=cfg.opticspy_root,
        )
        A, B, C, D = float(M[0, 0]), float(M[0, 1]), float(M[1, 0]), float(M[1, 1])

    M_lens = np.array([[float(A), float(B)], [float(C), float(D)]], dtype=float)

    # Indices (at reference wavelength)
    n_o = get_refractive_index_nm(cfg.object_medium, cfg.wavelengths_nm, cfg.opticspy_root)
    n_i = get_refractive_index_nm(cfg.image_medium, cfg.wavelengths_nm, cfg.opticspy_root)

    # Object reduced distance: object plane -> start_surface vertex
    z_o = cfg.object_distance_mm
    z = z_vertices_absolute(cfg.prescription, cfg.reference_surface)
    z_start = float(z[cfg.start_surface])
    if z_o is None:
        L_o = 0.0  # infinity: angular input; keep identity for T_o
    else:
        d_o = float(z_start) - float(z_o)
        L_o = d_o / float(n_o)

    # Image reduced distance
    if z_end is None:
        z_end = float(z[cfg.end_surface])
    if z_img is None:
        # Reconstruct selected image plane based on config
        z = z_vertices_absolute(cfg.prescription, cfg.reference_surface)
        img_surface_default = cfg.image_surface or max(sp.num for sp in cfg.prescription)
        z_recipe = float(z[img_surface_default]) if img_surface_default in z else None
        mode = str(cfg.image_mode or "recipe").lower()
        if mode == "paraxial":
            # Infinity: use BFL=-A/C. Finite conjugate: solve image plane such that Bs=0.
            if cfg.object_distance_mm is None:
                card = cardinals_air_air(float(A), float(B), float(C), float(D))
                z_img = float(z_end + card["BFL"])
            else:
                # Solve Li from Bs=0 using reduced distances
                denom = (float(C) * float(L_o) + float(D))
                if denom == 0:
                    z_img = float('nan')
                else:
                    Li = - (float(A) * float(L_o) + float(B)) / denom
                    z_img = float(z_end + float(Li) * float(n_i))
        elif mode == "absolute":
            if cfg.image_z_abs is None:
                raise ValueError("image_mode='absolute' requires image_z_abs")
            z_img = float(cfg.image_z_abs)
        else:
            z_img = float(cfg.image_z_abs) if cfg.image_z_abs is not None else z_recipe

    if z_img is None:
        # Unknown image plane: treat as end vertex (no image translation)
        L_i = 0.0
        z_i = None
    else:
        d_i = float(z_img) - float(z_end)
        L_i = d_i / float(n_i)
        z_i = float(z_img)

    T_o = translation_matrix(float(L_o) * float(n_o), float(n_o))  # equals [[1,Lo],[0,1]]
    T_i = translation_matrix(float(L_i) * float(n_i), float(n_i))  # equals [[1,Li],[0,1]]

    # Note: translation_matrix expects physical t and n; we pass t=Lo*n to get Lo.
    M_sys = T_i @ M_lens @ T_o
    A_s, B_s, C_s, D_s = float(M_sys[0, 0]), float(M_sys[0, 1]), float(M_sys[1, 0]), float(M_sys[1, 1])

    return {
        "A_s": A_s,
        "B_s": B_s,
        "C_s": C_s,
        "D_s": D_s,
        "L_o": float(L_o),
        "L_i": float(L_i),
        "n_o": float(n_o),
        "n_i": float(n_i),
        "z_o": None if z_o is None else float(z_o),
        "z_i": z_i,
        "z_end": float(z_end),
        "image_mode": str(cfg.image_mode or "recipe").lower(),
    }


def compute_magnifications(cfg: ReportConfig, system_matrix: Dict[str, Any]) -> Dict[str, float]:
    """Compute magnification set from system matrix.

    Definitions (Plan B):
      beta  = A_s  (lateral magnification when B_s≈0)
      alpha = beta (explicit; for rotationally symmetric paraxial systems)
      gamma_u = D_s
      gamma_theta = (n_o/n_i) * D_s
      longitudinal_mag = beta^2 * (n_i/n_o)
      focus_indicator_B = B_s
    """

    A_s = float(system_matrix["A_s"])
    B_s = float(system_matrix["B_s"])
    D_s = float(system_matrix["D_s"])
    n_o = float(system_matrix.get("n_o", 1.0))
    n_i = float(system_matrix.get("n_i", 1.0))

    beta = A_s
    alpha = beta
    gamma_u = D_s
    gamma_theta = (n_o / n_i) * D_s if n_i != 0 else float("nan")
    longitudinal_mag = (beta * beta) * (n_i / n_o) if n_o != 0 else float("nan")

    return {
        "beta": float(beta),
        "alpha": float(alpha),
        "gamma_u": float(gamma_u),
        "gamma_theta": float(gamma_theta),
        "longitudinal_mag": float(longitudinal_mag),
        "focus_indicator_B": float(B_s),
    }


def compute_newton_check(
    cfg: ReportConfig,
    cardinals: Dict[str, float],
    *,
    z_end: float,
    zH: float,
    zHp: float,
    z_img: Optional[float],
) -> Optional[Dict[str, float]]:
    """Newton relation check x*x' ?= f^2.

    Definitions:
      z_F  = z_H  - f
      z_F' = z_H' + f
      x  = z_F - z_o     (positive toward object side)
      x' = z_i - z_F'    (positive toward image side)

    Only computed when cfg.object_distance_mm is not None and z_img is known.
    """

    if cfg.object_distance_mm is None:
        return None
    if z_img is None:
        return None

    f = float(cardinals["fprime"])
    z_F = float(zH - f)
    z_Fp = float(zHp + f)
    z_o = float(cfg.object_distance_mm)
    z_i = float(z_img)

    x = float(z_F - z_o)
    xprime = float(z_i - z_Fp)
    x_xprime = float(x * xprime)
    f2 = float(f * f)
    rel_err = float((x_xprime - f2) / f2) if f2 != 0 else float("nan")

    return {
        "z_o": z_o,
        "z_i": z_i,
        "z_F": z_F,
        "z_Fp": z_Fp,
        "x": x,
        "xprime": xprime,
        "f": f,
        "x_xprime": x_xprime,
        "f2": f2,
        "rel_err": rel_err,
    }


# -----------------------------------------------------------------------------
# First-order quantities comparable to opticspy.ray_tracing.first_order_tools
# -----------------------------------------------------------------------------
def efl_from_abcd(C: float) -> float:
    """Rear focal length (EFL) from reduced-angle ABCD.

    Matches opticspy first_order_tools.EFL():
        EFL = -1/C
    """

    if C == 0:
        raise ZeroDivisionError("C is zero; system has infinite focal length.")
    return -1.0 / float(C)


def bfl_paraxial_from_abcd(A: float, C: float) -> float:
    """Paraxial back focal length (from last vertex to paraxial focus).

    For reduced-angle ABCD (air->air), opticspy's cardinal computation uses:
        BFL = -A/C
    """

    if C == 0:
        raise ZeroDivisionError("C is zero; BFL undefined.")
    return -float(A) / float(C)


def image_position_from_abcd(A: float, C: float, object_distance: float) -> float:
    """Paraxial image position following opticspy's image_position() formula.

    opticspy first_order_tools.image_position() uses:
        z  = Lens.object_position
        f  = -1/C
        fp = -1/C   (note: opticspy sets fp equal to f)
        Fp = -A/C
        zp = f*fp/z
        image_position = Fp + zp

    This is primarily intended for *comparisons* with opticspy.
    """

    if C == 0:
        raise ZeroDivisionError("C is zero; image position undefined.")
    z = float(object_distance)
    f = -1.0 / float(C)
    fp = -1.0 / float(C)
    Fp = -float(A) / float(C)
    if z == 0:
        raise ZeroDivisionError("object_distance is zero; image position undefined.")
    zp = (f * fp) / z
    return Fp + zp


def bfl_recipe_from_prescription(prescription: Sequence[SurfaceSpec], image_surface: int) -> float:
    """"Recipe" BFL matching opticspy BFL(): thickness of surface just before image.

    opticspy first_order_tools.BFL() returns:
        Lens.surface_list[-2].thickness

    With numbering 1..N where N is image surface, this corresponds to surface N-1 thickness.
    """

    s = {sp.num: sp for sp in prescription}
    if (image_surface - 1) not in s:
        raise ValueError(f"surface {image_surface-1} not found; cannot compute recipe BFL")
    return float(s[image_surface - 1].t)


def oal_from_prescription(prescription: Sequence[SurfaceSpec], start_surface: int, end_surface: int) -> float:
    """Overall axial length matching opticspy OAL(start,end).

    opticspy first_order_tools.OAL() does:
        OAL = sum thickness of surfaces [start .. end-1]
    where start/end are surface numbers.
    """

    s = {sp.num: sp for sp in prescription}
    total = 0.0
    for i in range(int(start_surface), int(end_surface)):
        if i not in s:
            raise ValueError(f"surface {i} not found; cannot compute OAL")
        total += float(s[i].t)
    return total


def stop_surface_number(prescription: Sequence[SurfaceSpec]) -> Optional[int]:
    """Return the stop surface number if present."""

    for sp in prescription:
        if sp.stop:
            return int(sp.num)
    return None


def entrance_pupil_position_from_prescription(
    prescription: Sequence[SurfaceSpec],
    wavelengths_nm: Sequence[float],
    *,
    stop_surface: Optional[int] = None,
    opticspy_root: Optional[str] = None,
) -> float:
    """Entrance pupil position (EP) matching opticspy first_order_tools.EP().

    - Finds stop surface (SurfaceSpec.stop) unless explicitly provided.
    - Uses ABCD from surface 2 to stop_surface-1.
    - Uses t_stop as thickness of surface stop_surface-1 (distance into stop).
    """

    s = {sp.num: sp for sp in prescription}
    n = int(stop_surface) if stop_surface is not None else stop_surface_number(prescription)
    if n is None:
        raise ValueError("No stop surface found in prescription.")

    if n == 2:
        return 0.0

    if (n - 1) not in s:
        raise ValueError(f"surface {n-1} not found; cannot compute EP")
    t_stop = float(s[n - 1].t)

    A, B, C, D = (0.0, 0.0, 0.0, 0.0)
    M = compute_abcd_from_prescription(
        prescription,
        wavelengths_nm,
        start_surface=2,
        end_surface=n - 1,
        opticspy_root=opticspy_root,
    )
    A, B, C, D = float(M[0, 0]), float(M[0, 1]), float(M[1, 0]), float(M[1, 1])

    if C == 0:
        raise ZeroDivisionError("C is zero; EP undefined.")

    phi = -C
    P = (D - 1.0) / C
    Pp = (1.0 - A) / C
    lp = t_stop - Pp
    l = 1.0 / (1.0 / lp - phi)
    EP = l + P
    return float(EP)


def exit_pupil_position_from_prescription(
    prescription: Sequence[SurfaceSpec],
    wavelengths_nm: Sequence[float],
    *,
    stop_surface: Optional[int] = None,
    opticspy_root: Optional[str] = None,
) -> float:
    """Exit pupil position (EX) matching opticspy first_order_tools.EX()."""

    s = {sp.num: sp for sp in prescription}
    n = int(stop_surface) if stop_surface is not None else stop_surface_number(prescription)
    if n is None:
        raise ValueError("No stop surface found in prescription.")

    max_num = max(s.keys())
    last_refracting = max_num - 1  # exclude SI image plane

    # opticspy: if stop at last (before image), EX = 0
    if n == last_refracting:
        return 0.0

    if n not in s:
        raise ValueError(f"stop surface {n} not found; cannot compute EX")
    t_stop = float(s[n].t)

    M = compute_abcd_from_prescription(
        prescription,
        wavelengths_nm,
        start_surface=n + 1,
        end_surface=last_refracting,
        opticspy_root=opticspy_root,
    )
    A, B, C, D = float(M[0, 0]), float(M[0, 1]), float(M[1, 0]), float(M[1, 1])

    if C == 0:
        raise ZeroDivisionError("C is zero; EX undefined.")

    phi = -C
    P = (D - 1.0) / C
    Pp = (1.0 - A) / C
    l = -(t_stop + P)
    lp = 1.0 / (1.0 / l + phi)
    EX = lp + Pp
    return float(EX)


def first_order_like_opticspy(cfg: ReportConfig, *, object_distance: float = -1000000.0) -> Dict[str, float]:
    """Compute first-order quantities using the same formulas as opticspy tools.

    Returns a dict with keys:
      - efl_full: EFY()
      - efl_part: EFY(start,end) if requested separately by caller
      - bfl_recipe: BFL() (recipe thickness)
      - bfl_parax: -A/C for start..end_surface
      - image_position: image_position()
      - ep: EP()
      - ex: EX()

    Note: EP/EX require a stop surface.
    """

    M = compute_abcd_from_prescription(
        cfg.prescription,
        cfg.wavelengths_nm,
        cfg.start_surface,
        cfg.end_surface,
        opticspy_root=cfg.opticspy_root,
    )
    A, B, C, D = float(M[0, 0]), float(M[0, 1]), float(M[1, 0]), float(M[1, 1])

    image_surface = cfg.image_surface or max(sp.num for sp in cfg.prescription)

    out: Dict[str, float] = {
        "efl": efl_from_abcd(C),
        "bfl_parax": bfl_paraxial_from_abcd(A, C),
        "image_position": image_position_from_abcd(A, C, object_distance),
        "bfl_recipe": bfl_recipe_from_prescription(cfg.prescription, image_surface),
    }

    # EP/EX depend on stop
    out["ep"] = entrance_pupil_position_from_prescription(
        cfg.prescription, cfg.wavelengths_nm, opticspy_root=cfg.opticspy_root
    )
    out["ex"] = exit_pupil_position_from_prescription(
        cfg.prescription, cfg.wavelengths_nm, opticspy_root=cfg.opticspy_root
    )

    return out


# -----------------------------------------------------------------------------
# Optional: build opticspy Lens for drawing (caller does the drawing/saving)
# -----------------------------------------------------------------------------
def build_opticspy_lens(
    prescription: Sequence[SurfaceSpec],
    wavelengths_nm: Sequence[float],
    field_angles_deg: Sequence[float],
    fno: float,
    *,
    opticspy_root: Optional[str] = None,
    lens_name: str = "Custom",
    creator: str = "abcd_report",
):
    """Create an opticspy Lens from the given prescription.

    This function is intentionally light: it returns the Lens instance.
    Use opticspy's own trace/draw/analysis modules in the caller.
    """

    ensure_opticspy_importable(opticspy_root)
    from opticspy.ray_tracing import lens  # type: ignore

    L = lens.Lens(lens_name=lens_name, creator=creator)
    # Some opticspy snapshots share this list; clear for safety.
    L.surface_list = []
    L.FNO = float(fno)
    L.wavelength_list = list(wavelengths_nm)

    for ang in field_angles_deg:
        L.add_field_YAN(angle=float(ang))

    for sp in prescription:
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
