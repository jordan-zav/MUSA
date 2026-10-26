"""Optional accelerated conservative line partition; same Python fallback."""
import math
import sys
import numpy as np

try:
    from numba import njit
except ImportError:
    def njit(**kwargs):
        return lambda function: function


def primitive_arrays(lines):
    from .network import _iter_line_parts
    coordinates = [np.asarray(part.coords)[:, :2] for geometry in lines
                   for part in _iter_line_parts(geometry)]
    if not coordinates:
        return np.empty((0,2)), np.empty((0,2))
    return (np.concatenate([c[:-1] for c in coordinates]),
            np.concatenate([c[1:] for c in coordinates]))


@njit(cache=not getattr(sys,"frozen",False))
def primitive_masses(starts, ends, eps, ox, oy):
    result = {(0,0): 0.0}
    del result[(0,0)]
    for i in range(len(starts)):
        ax, ay = starts[i,0], starts[i,1]
        bx, by = ends[i,0], ends[i,1]
        dx, dy = bx-ax, by-ay
        length = math.sqrt(dx*dx+dy*dy)
        if length <= 0:
            continue
        ix, iy = math.floor((ax-ox)/eps), math.floor((ay-oy)/eps)
        jx, jy = math.floor((bx-ox)/eps), math.floor((by-oy)/eps)
        if ix == jx and iy == jy:
            key = (ix,iy)
            result[key] = result.get(key,0.)+length
            continue
        capacity = abs(jx-ix)+abs(jy-iy)+2
        cuts = np.empty(capacity)
        cuts[0], cuts[1] = 0., 1.
        count = 2
        for axis in range(2):
            a, b, origin, delta = (ax,bx,ox,dx) if axis == 0 else (ay,by,oy,dy)
            if delta == 0:
                continue
            low = math.floor((min(a,b)-origin)/eps)+1
            high = math.ceil((max(a,b)-origin)/eps)
            for grid in range(low,high):
                t = (origin+grid*eps-a)/delta
                if 0 < t < 1:
                    cuts[count] = t
                    count += 1
        ordered = np.sort(cuts[:count])
        magnitude = max(1.,abs(ax),abs(ay),abs(bx),abs(by),abs(ox),abs(oy),eps)
        tolerance = min(.25,8*np.spacing(magnitude)/length)
        previous = 0.
        for t in ordered:
            if t <= previous+tolerance or (t < 1. and t >= 1.-tolerance):
                continue
            midpoint = .5*(t+previous)
            key = (math.floor((ax+midpoint*dx-ox)/eps), math.floor((ay+midpoint*dy-oy)/eps))
            result[key] = result.get(key,0.)+length*(t-previous)
            previous = t
    return result


def line_masses(lines, eps, origin):
    if not np.isfinite(eps) or eps <= 0:
        raise ValueError('Cell size must be positive and finite.')
    starts, ends = primitive_arrays(lines)
    return dict(primitive_masses(starts,ends,float(eps),float(origin[0]),float(origin[1])))


@njit(cache=not getattr(sys,"frozen",False))
def bounded_mass_values(starts,ends,eps,ox,oy,upper_x,upper_y):
    """Keep the bounded reduction compiled; avoid Python boxing every cell."""
    masses=primitive_masses(starts,ends,eps,ox,oy)
    bounded={(0,0):0.0}
    del bounded[(0,0)]
    for (ix,iy),value in masses.items():
        key=(min(ix,upper_x),min(iy,upper_y))
        bounded[key]=bounded.get(key,0.)+value
    values=np.empty(len(bounded))
    i=0
    for value in bounded.values():
        values[i]=value
        i+=1
    return values
