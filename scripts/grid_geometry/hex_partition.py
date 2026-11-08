"""Experimental length-conserving partition of straight segments into a hexagonal grid.

Pointy-top hexagons. Centres: i*(a,0) + j*(a/2, a*sqrt(3)/2), a = centre spacing.
Every hexagon edge lies on a line n_k . p = m * a/2 with n_k at 0, 60, 120 degrees,
so cutting each segment at all those lines and assigning each piece by the
nearest centre of its midpoint is an exact partition (pieces never straddle an edge).
Cell size is given as the equal-area square side eps: area = eps**2.
"""
import math
import numpy as np
from numba import njit

SQ3 = math.sqrt(3.0)


def spacing_from_eps(eps):
    # hexagon area = (sqrt(3)/2) a^2 = eps^2
    return eps * math.sqrt(2.0 / SQ3)


@njit(cache=True)
def _nearest(x, y, a):
    jf = 2.0 * y / (a * SQ3)
    if_ = x / a - jf / 2.0
    X, Z = if_, jf
    Y = -X - Z
    rx, ry, rz = round(X), round(Y), round(Z)
    dx, dy, dz = abs(rx - X), abs(ry - Y), abs(rz - Z)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy <= dz:
        rz = -rx - ry
    return int(rx), int(rz)


@njit(cache=True)
def hex_masses(starts, ends, a, ox, oy):
    result = {(0, 0): 0.0}
    del result[(0, 0)]
    nx = (1.0, 0.5, -0.5)
    ny = (0.0, SQ3 / 2.0, SQ3 / 2.0)
    half = a / 2.0
    for i in range(len(starts)):
        ax, ay = starts[i, 0] - ox, starts[i, 1] - oy
        bx, by = ends[i, 0] - ox, ends[i, 1] - oy
        dx, dy = bx - ax, by - ay
        length = math.sqrt(dx * dx + dy * dy)
        if length <= 0:
            continue
        cap = 2
        for k in range(3):
            pa = nx[k] * ax + ny[k] * ay
            pb = nx[k] * bx + ny[k] * by
            cap += int(abs(pb - pa) / half) + 2
        cuts = np.empty(cap)
        cuts[0], cuts[1] = 0.0, 1.0
        n = 2
        for k in range(3):
            pa = nx[k] * ax + ny[k] * ay
            pb = nx[k] * bx + ny[k] * by
            d = pb - pa
            if d == 0:
                continue
            low = math.floor(min(pa, pb) / half) + 1
            high = math.ceil(max(pa, pb) / half)
            for m in range(low, high):
                t = (m * half - pa) / d
                if 0 < t < 1:
                    cuts[n] = t
                    n += 1
        ordered = np.sort(cuts[:n])
        mag = max(1.0, abs(ax), abs(ay), abs(bx), abs(by), a)
        tol = min(0.25, 8 * np.spacing(mag) / length)
        prev = 0.0
        for t in ordered:
            if t <= prev + tol or (t < 1.0 and t >= 1.0 - tol):
                continue
            mid = 0.5 * (t + prev)
            key = _nearest(ax + mid * dx, ay + mid * dy, a)
            result[key] = result.get(key, 0.0) + length * (t - prev)
            prev = t
    return result
