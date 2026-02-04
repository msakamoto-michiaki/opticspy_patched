"""Compatibility shim for opticspy snapshots expecting an external `unwrap` module.

Some versions of opticspy import `unwrap.unwrap` via `opticspy.phaseunwrap`.
The ray-tracing tests in this repository do not require phase unwrapping, but
importing the top-level `opticspy` package can fail if `unwrap` is missing.

This shim keeps those imports working. If you actually need phase unwrapping,
install a proper unwrap implementation.
"""

from __future__ import annotations

from typing import Any


def unwrap(*args: Any, **kwargs: Any):
    """Placeholder unwrap implementation.

    Raises:
        NotImplementedError: always, because this is only a stub.
    """

    raise NotImplementedError(
        "This repository includes a stub `unwrap` module only to satisfy imports. "
        "Install a real phase-unwrapping library if needed."
    )
