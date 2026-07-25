"""How a net gets drawn once its parts are placed.

A router turns one net into a list of :class:`Segment` — a small intermediate
representation the serializer renders verbatim. Keeping it separate from the
XML means routing geometry can be tested without parsing a document, and means
a different routing strategy is a swap rather than a rewrite.

A strategy is anything with ``route(design, placement, sym_of) -> (dict, list)``
mapping net name to segments, plus warnings.
"""

STUB = 5.08

# Which way a pin's stub runs, by pin rotation.
STUB_DIR = {"R0": (-1, 0), "R180": (1, 0), "R90": (0, -1), "R270": (0, 1)}


class Segment:
    """One connected piece of a net.

    A net with every pin on the same sheet is usually one segment; a net split
    across sheets has one per sheet. ``labels`` carries cross-reference labels;
    ``supplies`` carries ground/rail symbol placements.
    """

    def __init__(self, sheet, wires=(), pinrefs=(), junctions=(), labels=(), supplies=()):
        self.sheet = sheet
        self.wires = list(wires)          # (x1, y1, x2, y2)
        self.pinrefs = list(pinrefs)      # (refdes, pin)
        self.junctions = list(junctions)  # (x, y)
        self.labels = list(labels)        # (x, y, rot)
        self.supplies = list(supplies)    # (rail, x, y, rot)


def pin_geometry(symbol, origin, pin):
    """Return ``(px, py, ex, ey)``: the pin's connection point and stub end."""
    for (pn, dx, dy, rot) in symbol["pins"]:
        if pn == pin:
            cx, cy = origin[0] + dx, origin[1] + dy
            sx, sy = STUB_DIR[rot]
            return cx, cy, cx + sx * STUB, cy + sy * STUB
    return None


class StubRouter:
    """A stub and a cross-reference label at every pin — nothing is joined.

    The original strategy. Correct, because same-named labels are electrically
    connected in EAGLE, but it means all 627 connections are drawn as loose
    ends. Kept as the fallback for nets a real router declines.
    """

    def route(self, design, placement, sym_of):
        routed, warnings = {}, []
        for name, pinrefs in design.nets.items():
            segments = []
            for ref, pin in pinrefs:
                geo = pin_geometry(sym_of[ref], placement.coords[ref], pin)
                if geo is None:
                    warnings.append("no geometry %s.%s" % (ref, pin))
                    continue
                cx, cy, ex, ey = geo
                segments.append(Segment(
                    sheet=placement.sheet_of[ref],
                    wires=[(cx, cy, ex, ey)],
                    pinrefs=[(ref, pin)],
                    labels=[(ex, ey + 0.635, "R0")]))
            if segments:
                routed[name] = segments
        return routed, warnings
