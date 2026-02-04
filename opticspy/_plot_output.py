# -*- coding: utf-8 -*-
"""Utilities for headless-friendly plotting.

This project often runs under the non-GUI 'Agg' backend, where `plt.show()` and
`fig.canvas.set_window_title(...)` are either undesirable or unsupported.
Use these helpers to save figures to ./out/ deterministically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

def set_window_title(fig: Any, title: str) -> None:
    """Set a figure window title when a GUI canvas/manager exists."""
    try:
        mng = getattr(getattr(fig, "canvas", None), "manager", None)
        if mng is not None and hasattr(mng, "set_window_title"):
            mng.set_window_title(title)
    except Exception:
        # Headless backends (e.g., Agg) or older Matplotlib versions.
        pass

def save_figure(plt_like: Any, filename: str, outdir: str = "out", dpi: int = 150, close: bool = True) -> str:
    """Save the current figure from a pyplot-like module to outdir/filename.

    Parameters
    ----------
    plt_like:
        Usually `matplotlib.pyplot` (often imported as `plt` or `__plt__`).
    filename:
        Output filename (e.g., 'opticspy_ray_tracing_analysis__spotdiagram.png').
    outdir:
        Output directory relative to current working directory.
    dpi:
        DPI for the saved image.
    close:
        Close the figure after saving to avoid accumulating many figures.
    """
    Path(outdir).mkdir(parents=True, exist_ok=True)
    fig = plt_like.gcf()
    path = Path(outdir) / filename
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    if close:
        try:
            plt_like.close(fig)
        except Exception:
            pass
    print(f"saved: {path}")
    return str(path)
