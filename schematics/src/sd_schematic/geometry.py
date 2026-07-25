"""EAGLE-XML drawing primitives.

Every symbol body is built from these; they emit the raw XML fragments that
land inside a ``<symbol>`` element.
"""

from xml.sax.saxutils import escape

# EAGLE layer numbers used by the generator.
LAYER_NETS = 91
LAYER_SYMBOLS = 94
LAYER_NAMES = 95
LAYER_VALUES = 96
LAYER_INFO = 97

LAYERS = [
    (91, "Nets", 2),
    (92, "Busses", 1),
    (93, "Pins", 2),
    (94, "Symbols", 4),
    (95, "Names", 7),
    (96, "Values", 7),
    (97, "Info", 7),
    (98, "Guide", 6),
]


def wire(x1, y1, x2, y2, layer=LAYER_SYMBOLS, width=0.254):
    return '<wire x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" width="%s" layer="%d"/>' % (
        x1, y1, x2, y2, width, layer)


def arc(x1, y1, x2, y2, curve, layer=LAYER_SYMBOLS, width=0.254):
    """A curved wire. EAGLE takes the bulge as a signed sweep in degrees."""
    return ('<wire x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" width="%s" '
            'curve="%.1f" layer="%d"/>' % (x1, y1, x2, y2, width, curve, layer))


def rect(x1, y1, x2, y2):
    return "".join([wire(x1, y1, x2, y1), wire(x2, y1, x2, y2),
                    wire(x2, y2, x1, y2), wire(x1, y2, x1, y1)])


def poly(pts):
    s = ""
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        s += wire(a[0], a[1], b[0], b[1])
    return s


def circle(r, cx, cy):
    return '<circle x="%.3f" y="%.3f" radius="%.3f" width="0.254" layer="94"/>' % (cx, cy, r)


def text(x, y, s, size=1.778, layer=LAYER_SYMBOLS):
    return '<text x="%.3f" y="%.3f" size="%.3f" layer="%d">%s</text>' % (
        x, y, size, layer, escape(s))


def layers_xml():
    return "".join(
        '<layer number="%d" name="%s" color="%d" fill="1" visible="yes" active="yes"/>'
        % (n, nm, c) for n, nm, c in LAYERS)
