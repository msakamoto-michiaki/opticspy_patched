"""Project-level utilities (headless plotting, output management).

This package is intentionally lightweight and has no dependency on opticspy.
"""

from .plotting import (
    setup_matplotlib_headless,
    ShowToSavefig,
    rename_latest_spotdiagram,
    ensure_dir,
)

from .paths import chdir

from .codev_io import find_seq_path
