"""Length-conserving partition of straight primitives into half-open cells."""
import numpy as np

from .network import _iter_line_parts


def line_cell_segments(lines, eps, origin):
    """Yield (cell, length, east-based axial angle), each length exactly once.

    Split at grid crossings, assign by the midpoint. A coincident grid edge
    belongs to the cell on its positive side. No geometric buffering/snapping.
    """
    if not np.isfinite(eps) or eps <= 0:
        raise ValueError('Cell size must be positive and finite.')
    origin = np.asarray(origin, dtype=float)
    for geometry in lines:
        for line in _iter_line_parts(geometry):
            coords = np.asarray(line.coords)[:, :2]
            starts, ends = coords[:-1], coords[1:]
            deltas = ends-starts
            lengths = np.linalg.norm(deltas, axis=1)
            start_cells = np.floor((starts-origin)/eps).astype(int)
            end_cells = np.floor((ends-origin)/eps).astype(int)
            interior = np.all(start_cells == end_cells, axis=1)
            angles = np.degrees(np.arctan2(deltas[:,1], deltas[:,0])) % 180
            for i in range(len(starts)):
                length = float(lengths[i])
                if length == 0:
                    continue
                angle = float(angles[i])
                if interior[i]:
                    cell = start_cells[i]
                    yield (int(cell[0]), int(cell[1])), length, angle
                    continue
                a, delta = starts[i], deltas[i]
                b = ends[i]
                cuts = [0., 1.]
                for axis in (0, 1):
                    if delta[axis] == 0:
                        continue
                    low, high = sorted(((a[axis]-origin[axis])/eps,
                                        (b[axis]-origin[axis])/eps))
                    grid = np.arange(np.floor(low)+1, np.ceil(high))
                    t = (origin[axis]+grid*eps-a[axis])/delta[axis]
                    cuts.extend(t[(t > 0) & (t < 1)])
                cuts = np.unique(cuts)
                # At a grid corner the x/y crossing parameters may differ by
                # a few floating-point ulps. Counting the sliver between them
                # creates a fictitious occupied cell, disastrous for q=0 log p.
                # Coalesce only below coordinate precision, conserving length.
                magnitude = max(1., float(np.max(np.abs(coords))),
                                float(np.max(np.abs(origin))), float(eps))
                tolerance = min(.25, 8*np.spacing(magnitude)/length)
                internal = cuts[(cuts > tolerance) & (cuts < 1-tolerance)]
                if len(internal):
                    internal = internal[np.r_[True, np.diff(internal) > tolerance]]
                cuts = np.r_[0., internal, 1.]
                mids = a + ((cuts[:-1]+cuts[1:])/2)[:, None]*delta
                cells = np.floor((mids-origin)/eps).astype(int)
                for cell, fraction in zip(cells, np.diff(cuts)):
                    yield (int(cell[0]), int(cell[1])), length*float(fraction), angle
