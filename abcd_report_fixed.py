# abcd_report_fixed.py
#
# ABCD calculation using reduced-angle ray vector:
#     [ y ]
#     [ u ] ,  u = n * theta
#
# This is consistent with opticspy / first_order_tools.
# Cardinal points are computed so that results are
# numerically identical to [y, theta] formulation
# for air-to-air systems.

"""Legacy wrapper maintained for backward compatibility.

Historically this file contained a standalone implementation.
The implementation is now shared in :mod:`optics.abcd_common` so that
all scripts (including ``opticspy_abcd_layout_report_general.py``) report
identical results.
"""

from optics.abcd_common import (  # noqa: F401
    matmul,
    T,
    R,
    system_abcd,
    cardinals_air_air_tuple as cardinals_air_air,
)

