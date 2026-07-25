"""Symbol geometry.

One symbol is shared by every part with the same (kind, pin-signature), so the
generated library stays small. Coordinates are millimetres on a 2.54 mm grid.
"""

from collections import OrderedDict, defaultdict
from xml.sax.saxutils import escape

from .geometry import LAYER_NAMES, LAYER_VALUES, circle, poly, rect, text, wire

# Kinds drawn with the standard two horizontal terminals.
TWO_PIN = {"R", "C", "CPOL", "D", "ZENER", "LED"}
# Kinds drawn as a three-terminal transistor.
TRANSISTOR = {"NPN", "PNP", "NMOS", "JFET"}

PIN_STUB = 2.54


def make_symbol(kind, pins):
    """Return ``(pinlist, body)`` for a part kind.

    ``pinlist`` is ``[(name, x, y, rot), ...]``; ``body`` is a list of XML
    fragments drawing the outline.
    """
    body, out = [], []
    if kind in TWO_PIN:
        out = [("1", -7.62, 0.0, "R0"), ("2", 7.62, 0.0, "R180")]
        if kind == "R":
            body.append(rect(-5.08, -1.27, 5.08, 1.27))
            body.append(wire(-7.62, 0, -5.08, 0))
            body.append(wire(5.08, 0, 7.62, 0))
        elif kind in ("C", "CPOL"):
            body.append(wire(-7.62, 0, -1.27, 0))
            body.append(wire(1.27, 0, 7.62, 0))
            body.append(wire(-1.27, -2.54, -1.27, 2.54))
            body.append(wire(1.27, -2.54, 1.27, 2.54))
            if kind == "CPOL":
                body.append(text(-3.81, 1.27, "+", 1.27))
        else:  # D / ZENER / LED  (pin1 = anode, pin2 = cathode)
            body.append(wire(-7.62, 0, -1.27, 0))
            body.append(wire(1.27, 0, 7.62, 0))
            body.append(poly([(-1.27, -2.54), (-1.27, 2.54), (1.27, 0)]))
            body.append(wire(1.27, -2.54, 1.27, 2.54))
            if kind == "ZENER":
                body.append(wire(1.27, 2.54, 2.54, 2.54))
                body.append(wire(1.27, -2.54, 0.0, -2.54))
            if kind == "LED":
                body.append(wire(1.27, 2.54, 3.81, 5.08))
                body.append(wire(2.54, 2.54, 5.08, 5.08))
    elif kind == "POT":
        out = [("1", -7.62, 0.0, "R0"), ("2", 0.0, 7.62, "R270"), ("3", 7.62, 0.0, "R180")]
        body.append(rect(-5.08, -1.27, 5.08, 1.27))
        body.append(wire(-7.62, 0, -5.08, 0))
        body.append(wire(5.08, 0, 7.62, 0))
        body.append(wire(0, 7.62, 0, 2.54))
        body.append(poly([(-1.27, 2.54), (1.27, 2.54), (0, 1.27)]))
    elif kind in TRANSISTOR:
        out = [(pins[0], -7.62, 0.0, "R0"),
               (pins[1], 2.54, 7.62, "R270"),
               (pins[2], 2.54, -7.62, "R90")]
        body.append(wire(-7.62, 0, -1.27, 0))
        body.append(wire(-1.27, -3.81, -1.27, 3.81))
        body.append(wire(-1.27, 1.905, 2.54, 3.81))
        body.append(wire(2.54, 3.81, 2.54, 7.62))
        body.append(wire(-1.27, -1.905, 2.54, -3.81))
        body.append(wire(2.54, -3.81, 2.54, -7.62))
        body.append(circle(0.635, 0, 5.08))
    else:
        # generic rectangle: pins alternate down the left and right sides
        n = len(pins)
        rows = (n + 1) // 2
        h = max(rows * 2.54 + 2.54, 7.62)
        w = 15.24
        body.append(rect(-w / 2, -h / 2, w / 2, h / 2))
        for i, pn in enumerate(pins):
            row = i // 2
            y = h / 2 - 2.54 - row * 2.54
            if i % 2 == 0:
                out.append((pn, -w / 2 - PIN_STUB, y, "R0"))
            else:
                out.append((pn, w / 2 + PIN_STUB, y, "R180"))
    return out, body


def signature(part):
    """The key that decides whether two parts can share a symbol."""
    return (part["kind"], tuple(part["pins"]))


def build_symbol_library(parts):
    """Return ``(symbols, sym_of)``.

    ``symbols`` maps signature -> symbol dict; ``sym_of`` maps refdes -> that
    same dict, so a part can find its geometry in one lookup.
    """
    symbols = OrderedDict()
    sym_of = {}
    kind_count = defaultdict(int)
    for ref, p in parts.items():
        key = signature(p)
        if key not in symbols:
            pinlist, body = make_symbol(p["kind"], p["pins"])
            kind_count[p["kind"]] += 1
            name = "%s_%d" % (p["kind"], kind_count[p["kind"]])
            symbols[key] = {"name": name, "pins": pinlist, "body": body, "kind": p["kind"]}
        sym_of[ref] = symbols[key]
    return symbols, sym_of


def symbol_xml(symbol):
    """Render one ``<symbol>`` element."""
    pins = "".join(
        '<pin name="%s" x="%.3f" y="%.3f" visible="pin" length="short" direction="pas" rot="%s"/>'
        % (escape(pn), px, py, rot) for (pn, px, py, rot) in symbol["pins"])
    return '<symbol name="%s">%s%s%s%s</symbol>' % (
        symbol["name"], "".join(symbol["body"]),
        text(-5.08, 9.0, ">NAME", 1.778, LAYER_NAMES),
        text(-5.08, -11.0, ">VALUE", 1.778, LAYER_VALUES),
        pins)
