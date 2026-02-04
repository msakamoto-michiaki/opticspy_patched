# -*- coding: utf-8 -*-
"""Shared ABCD utilities (reduced-angle: u = n*theta).

Both ``abcd_report_fixed.py`` and ``opticspy_abcd_layout_report_general.py``
use the reduced-angle ray vector:

    r = [y, u]^T,  where u = n * theta

This module centralizes the common paraxial math so the reported results
(cardinal points, BFL, etc.) stay identical across scripts.

Conventions
-----------
* Matrices map ``[y, u]`` at input to output.
* Light travels along +z.
* For air-to-air systems (n_in = n_out = 1), the standard reduced-angle
  relations are used:

    f'    = -1/C
    h     = (D - 1)/C
    h'    = (A - 1)/C
    BFL   = -A/C
    FFL   = -D/C

"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover
    _np = None


Matrix2 = List[List[float]]


# ----------------------------------------------------------------------------
# Pure-Python 2x2 utilities
# ----------------------------------------------------------------------------

def matmul(A: Matrix2, B: Matrix2) -> Matrix2:
    """Return A @ B for 2x2 matrices represented as nested lists."""
    return [
        [
            A[0][0] * B[0][0] + A[0][1] * B[1][0],
            A[0][0] * B[0][1] + A[0][1] * B[1][1],
        ],
        [
            A[1][0] * B[0][0] + A[1][1] * B[1][0],
            A[1][0] * B[0][1] + A[1][1] * B[1][1],
        ],
    ]


def identity() -> Matrix2:
    return [[1.0, 0.0], [0.0, 1.0]]


def T(t: float, n: float) -> Matrix2:
    """Translation matrix (reduced-angle)."""
    return [[1.0, float(t) / float(n)], [0.0, 1.0]]


def R(c: float, n1: float, n2: float) -> Matrix2:
    """Refraction matrix at a spherical surface (reduced-angle).

    Parameters
    ----------
    c : float
        Curvature (= 1/R).
    n1, n2 : float
        Refractive indices before/after the surface.
    """
    return [[1.0, 0.0], [-(float(n2) - float(n1)) * float(c), 1.0]]


def system_abcd(elements: Sequence[Dict[str, Any]]) -> Matrix2:
    """Accumulate a system matrix from an element list.

    Elements are dictionaries in one of these forms:

    * {'type': 'T', 't': ..., 'n': ...}
    * {'type': 'R', 'c': ..., 'n1': ..., 'n2': ...}

    The multiplication order matches the historical ``abcd_report_fixed.py``
    implementation (left-multiply each new element).
    """
    M = identity()
    for e in elements:
        if e.get("type") == "T":
            M = matmul(T(e["t"], e["n"]), M)
        elif e.get("type") == "R":
            M = matmul(R(e["c"], e["n1"], e["n2"]), M)
        else:
            raise ValueError(f"Unknown element type: {e!r}")
    return M


# ----------------------------------------------------------------------------
# Cardinals (air -> air)
# ----------------------------------------------------------------------------

def cardinals_air_air_tuple(A: float, B: float, C: float, D: float) -> Tuple[float, float, float, float]:
    """Return (f, H, H', BFL) for air->air systems."""
    if C == 0:
        raise ZeroDivisionError("C is zero; system has zero optical power.")
    f = -1.0 / C
    H = (D - 1.0) / C
    Hp = (A - 1.0) / C
    BFL = -A / C
    return f, H, Hp, BFL


def cardinals_air_air_full(A: float, B: float, C: float, D: float) -> Dict[str, float]:
    """Return a dict of common cardinal values for air->air systems."""
    f, H, Hp, BFL = cardinals_air_air_tuple(A, B, C, D)
    FFL = -D / C
    return {"fprime": f, "h": H, "hprime": Hp, "BFL": BFL, "FFL": FFL}


# ----------------------------------------------------------------------------
# Optional NumPy helpers
# ----------------------------------------------------------------------------

def translation_matrix_np(t: float, n: float):
    """NumPy version of translation matrix (if NumPy is available)."""
    if _np is None:
        raise ImportError("NumPy is not available")
    return _np.array([[1.0, float(t) / float(n)], [0.0, 1.0]], dtype=float)


def refraction_matrix_radius_np(Radius: float, n1: float, n2: float, flat_thresh: float = 1e12):
    """NumPy refraction matrix using radius, matching opticspy_abcd_layout_report_general."""
    if _np is None:
        raise ImportError("NumPy is not available")
    c = 0.0 if abs(Radius) > float(flat_thresh) else 1.0 / float(Radius)
    return _np.array([[1.0, 0.0], [-(float(n2) - float(n1)) * c, 1.0]], dtype=float)
