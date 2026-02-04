"""Filesystem helpers."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def chdir(path: str) -> Iterator[None]:
    """Temporarily change working directory."""
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)
