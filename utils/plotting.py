"""Matplotlib helpers to make scripts deterministic in headless environments.

Key features
- Force a non-GUI backend (Agg) when possible.
- Redirect plt.show() calls (often used inside opticspy) to savefig().
- Avoid filename collisions by using sequential numbering.
- Provide a helper to rename opticspy's fixed spotdiagram output.

These utilities are designed to be called *before* importing modules that
import matplotlib.pyplot.
"""

from __future__ import annotations

import os
import time
from contextlib import ContextDecorator
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

def ensure_dir(path: str | Path) -> str:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def setup_matplotlib_headless() -> None:
    """Best-effort switch to a headless backend.

    Safe to call multiple times. If pyplot is already imported, backend may not change.
    """
    try:
        import matplotlib
        # If user already set MPLBACKEND, respect it.
        if os.environ.get("MPLBACKEND") is None:
            os.environ["MPLBACKEND"] = "Agg"
        # Try to set backend early.
        try:
            matplotlib.use("Agg", force=False)
        except Exception:
            pass
    except Exception:
        # matplotlib not installed or other import issue
        return


@dataclass
class ShowToSavefig(ContextDecorator):
    """Context manager to replace plt.show() with plt.savefig() into out_dir.

    Typical usage:
        setup_matplotlib_headless()
        with ShowToSavefig(out_dir="out/examples/example1", prefix="example1"):
            draw.draw_system(L)  # internally calls plt.show(); will save instead.

    Files saved as: <out_dir>/<prefix>__fig0001.png, ...
    """

    out_dir: str
    prefix: str = "figure"
    dpi: int = 200
    bbox_inches: str = "tight"

    _orig_show: Optional[object] = None
    _counter: int = 0

    def __post_init__(self) -> None:
        ensure_dir(self.out_dir)

    def __enter__(self):
        setup_matplotlib_headless()
        import matplotlib.pyplot as plt

        self._orig_show = plt.show

        def _save_and_close(*args, **kwargs):
            self._counter += 1
            fname = f"{self.prefix}__fig{self._counter:04d}.png"
            outpath = Path(self.out_dir) / fname
            plt.savefig(outpath, dpi=self.dpi, bbox_inches=self.bbox_inches)
            plt.close("all")

        plt.show = _save_and_close
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            import matplotlib.pyplot as plt
            if self._orig_show is not None:
                plt.show = self._orig_show
        except Exception:
            pass
        return False


def rename_latest_spotdiagram(out_dir: str | Path, tag: str, *, keep_original: bool = False) -> str:
    """Rename opticspy fixed-name spotdiagram output to a unique name.

    opticspy.ray_tracing.analysis.spotdiagram() saves to:
        out/opticspy_ray_tracing_analysis__spotdiagram.png

    This helper renames it to:
        <out_dir>/opticspy_ray_tracing_<tag>__spotdiagram_<YYYYmmdd_HHMMSS>.png

    Return the new path as string, or "" if source doesn't exist.

    Notes:
    - Call this *after* spotdiagram() returns.
    - If keep_original=True, it will copy instead of rename.
    """
    out_dir = Path(out_dir)
    ensure_dir(out_dir)

    src = out_dir / "opticspy_ray_tracing_analysis__spotdiagram.png"
    if not src.exists():
        # Some scripts run with CWD elsewhere (analysis writes relative to CWD/out).
        # If user passes an absolute out_dir but CWD differs, try that common relative path.
        alt = Path("out") / "opticspy_ray_tracing_analysis__spotdiagram.png"
        if alt.exists():
            src = alt
        else:
            return ""

    ts = time.strftime("%Y%m%d_%H%M%S")
    dst = out_dir / f"opticspy_ray_tracing_{tag}__spotdiagram_{ts}.png"

    if keep_original:
        import shutil
        shutil.copy2(src, dst)
    else:
        src.replace(dst)

    return str(dst)

def rename_fixed_png(src_path: str, outdir: str, tag: str) -> str:
    """
    固定名で生成されたPNGを、tag+timestamp付きで outdir に移動・改名する。
    戻り値: 新しいパス（失敗時は ""）
    """
    os.makedirs(outdir, exist_ok=True)
    if not os.path.exists(src_path):
        return ""
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(src_path)
    name, ext = os.path.splitext(base)
    dst = os.path.join(outdir, f"{tag}__{name}__{ts}{ext}")
    os.replace(src_path, dst)
    return dst
