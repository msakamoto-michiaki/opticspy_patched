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

# -------------------------------------------------
# 2x2 matrix utilities
# -------------------------------------------------
def matmul(A, B):
    return [
        [
            A[0][0]*B[0][0] + A[0][1]*B[1][0],
            A[0][0]*B[0][1] + A[0][1]*B[1][1],
        ],
        [
            A[1][0]*B[0][0] + A[1][1]*B[1][0],
            A[1][0]*B[0][1] + A[1][1]*B[1][1],
        ],
    ]

# -------------------------------------------------
# ABCD elements (reduced angle u = nθ)
# -------------------------------------------------
def T(t, n):
    # translation
    return [
        [1.0, t/n],
        [0.0, 1.0],
    ]

def R(c, n1, n2):
    # refraction at spherical surface
    return [
        [1.0, 0.0],
        [-(n2 - n1)*c, 1.0],
    ]

# -------------------------------------------------
# Build system ABCD
# -------------------------------------------------
def system_abcd(elements):
    """
    elements: list of dict
      {'type':'T', 't':..., 'n':...}
      {'type':'R', 'c':..., 'n1':..., 'n2':...}
    """
    M = [[1.0, 0.0], [0.0, 1.0]]
    for e in elements:
        if e['type'] == 'T':
            M = matmul(T(e['t'], e['n']), M)
        elif e['type'] == 'R':
            M = matmul(R(e['c'], e['n1'], e['n2']), M)
    return M

# -------------------------------------------------
# Cardinal points (air → air)
# -------------------------------------------------
def cardinals_air_air(A, B, C, D):
    f   = -1.0 / C
    H   = (D - 1.0) / C
    Hp  = (A - 1.0) / C
    BFL = -A / C
    return f, H, Hp, BFL
