"""Symbol geometry.

One symbol is shared by every part with the same (kind, pin-signature), so the
generated library stays small. Coordinates are millimetres on a 2.54 mm grid.
"""

from collections import OrderedDict, defaultdict
from xml.sax.saxutils import escape

from .geometry import LAYER_NAMES, LAYER_VALUES, circle, poly, rect, text, wire

# Kinds drawn with the standard two horizontal terminals.
TWO_PIN = {"R", "C", "CPOL", "D", "ZENER", "LED"}

BIPOLAR = {"NPN", "PNP"}
FET = {"NMOS", "JFET"}
TRANSISTOR = BIPOLAR | FET
AMPLIFIER = {"OPAMP", "COMP"}

# Roles each kind needs before it can be drawn correctly.
REQUIRED_ROLES = {
    "OPAMP": ("out", "in-", "in+"),
    "COMP":  ("out", "in-", "in+"),
    "NPN":   ("b", "c", "e"),
    "PNP":   ("b", "c", "e"),
    "NMOS":  ("g", "d", "s"),
    "JFET":  ("g", "d", "s"),
}

PIN_STUB = 2.54

# Pin electrical types. EAGLE only uses these for ERC, but "sup" on a rail and
# "out" on an amplifier output are what stop Fusion reporting the whole sheet
# as floating passives.
DIR_PAS, DIR_IN, DIR_OUT, DIR_PWR = "pas", "in", "out", "pwr"


def _arrowhead(x1, y1, x2, y2, at=0.62, size=1.4, reverse=False):
    """Two barbs forming an open arrowhead along a segment."""
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / length, dy / length
    if reverse:
        ux, uy = -ux, -uy
        at = 1.0 - at
    tx, ty = x1 + dx * at, y1 + dy * at
    bx, by = tx - ux * size, ty - uy * size
    px, py = -uy * size * 0.42, ux * size * 0.42
    return wire(tx, ty, bx + px, by + py) + wire(tx, ty, bx - px, by - py)


def make_symbol(kind, pins, roles=None):
    """Return ``(pinlist, body)`` for a part kind.

    ``pinlist`` is ``[(name, x, y, rot, direction), ...]``; ``body`` is a list
    of XML fragments drawing the outline. ``roles`` maps a role name to a pin
    name and is what decides which terminal goes where — a part drawn from pin
    order alone comes out wrong whenever the transcription numbered its pins
    rather than naming them.
    """
    roles = roles or {}
    body, out = [], []

    if kind in TWO_PIN:
        out = [("1", -7.62, 0.0, "R0", DIR_PAS), ("2", 7.62, 0.0, "R180", DIR_PAS)]
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
        out = [("1", -7.62, 0.0, "R0", DIR_PAS),
               ("2", 0.0, 7.62, "R270", DIR_PAS),
               ("3", 7.62, 0.0, "R180", DIR_PAS)]
        body.append(rect(-5.08, -1.27, 5.08, 1.27))
        body.append(wire(-7.62, 0, -5.08, 0))
        body.append(wire(5.08, 0, 7.62, 0))
        body.append(wire(0, 7.62, 0, 2.54))
        body.append(poly([(-1.27, 2.54), (1.27, 2.54), (0, 1.27)]))

    elif kind in AMPLIFIER:
        # Triangle: inputs left, output right. Inverting input on top, which is
        # where a reader expects it when the feedback resistor runs over the top.
        out = [(roles["in-"], -10.16, 2.54, "R0", DIR_IN),
               (roles["in+"], -10.16, -2.54, "R0", DIR_IN),
               (roles["out"], 10.16, 0.0, "R180", DIR_OUT)]
        body.append(poly([(-7.62, -6.35), (-7.62, 6.35), (7.62, 0)]))
        body.append(wire(-10.16, 2.54, -7.62, 2.54))
        body.append(wire(-10.16, -2.54, -7.62, -2.54))
        body.append(wire(7.62, 0, 10.16, 0))
        body.append(text(-6.6, 1.4, "-", 1.778))
        body.append(text(-6.9, -3.6, "+", 1.778))
        if "v+" in roles:
            out.append((roles["v+"], 0.0, 7.62, "R270", DIR_PWR))
            body.append(wire(0, 5.08, 0, 3.175))
        if "v-" in roles:
            out.append((roles["v-"], 0.0, -7.62, "R90", DIR_PWR))
            body.append(wire(0, -5.08, 0, -3.175))
        for pin in pins:
            if pin not in {p[0] for p in out}:
                out.append((pin, -10.16, -6.35, "R0", DIR_PAS))

    elif kind in BIPOLAR:
        # Base left, collector top, emitter bottom -- by role, never by order.
        out = [(roles["b"], -10.16, 0.0, "R0", DIR_IN),
               (roles["c"], 0.0, 10.16, "R270", DIR_PAS),
               (roles["e"], 0.0, -10.16, "R90", DIR_PAS)]
        body.append(wire(-10.16, 0, -5.08, 0))
        body.append(wire(-5.08, -3.81, -5.08, 3.81))
        body.append(wire(-5.08, 1.905, 0, 3.81))
        body.append(wire(0, 3.81, 0, 7.62))
        body.append(wire(-5.08, -1.905, 0, -3.81))
        body.append(wire(0, -3.81, 0, -7.62))
        # NPN points out of the device, PNP into it.
        body.append(_arrowhead(-5.08, -1.905, 0, -3.81, reverse=(kind == "PNP")))

    elif kind in FET:
        out = [(roles["g"], -10.16, 0.0, "R0", DIR_IN),
               (roles["d"], 0.0, 10.16, "R270", DIR_PAS),
               (roles["s"], 0.0, -10.16, "R90", DIR_PAS)]
        body.append(wire(0, 2.8575, 0, 7.62))
        body.append(wire(0, -2.8575, 0, -7.62))
        body.append(wire(-3.81, 2.8575, 0, 2.8575))
        body.append(wire(-3.81, -2.8575, 0, -2.8575))
        if kind == "NMOS":
            body.append(wire(-10.16, 0, -6.35, 0))
            body.append(wire(-6.35, -3.81, -6.35, 3.81))          # gate, insulated
            body.append(wire(-3.81, 1.905, -3.81, 3.81))          # channel, in three
            body.append(wire(-3.81, -0.9525, -3.81, 0.9525))
            body.append(wire(-3.81, -3.81, -3.81, -1.905))
            body.append(wire(-3.81, 0, 0, 0))                     # substrate to source
            body.append(_arrowhead(0, 0, -3.81, 0))
            body.append(wire(0, 0, 0, -2.8575))
        else:  # JFET: gate arrow straight into a continuous channel
            body.append(wire(-10.16, 0, -3.81, 0))
            body.append(_arrowhead(-10.16, 0, -3.81, 0, at=0.86))
            body.append(wire(-3.81, -3.81, -3.81, 3.81))

    elif kind == "CONN":
        # A pin strip: pins straight down the left in natural order, which is
        # how a connector is read. Alternating left/right made J1 unusable.
        n = len(pins)
        h = n * 2.54 + 2.54
        top = h / 2 - 2.54
        body.append(rect(-5.08, -h / 2, 5.08, h / 2))
        for i, pn in enumerate(pins):
            y = top - i * 2.54
            out.append((pn, -7.62, y, "R0", DIR_PAS))
            body.append(rect(-4.318, y - 0.635, -3.048, y + 0.635))

    elif kind == "TP":
        out = [(pins[0], -7.62, 0.0, "R0", DIR_PAS)]
        body.append(wire(-7.62, 0, -3.81, 0))
        body.append(circle(1.27, -2.54, 0))
        for pin in pins[1:]:
            out.append((pin, -7.62, -2.54, "R0", DIR_PAS))

    else:
        # Generic box -- ICs and the drawing's named function blocks. Pins run
        # down the left in natural order, spilling to the right only when there
        # are more than can fit, rather than alternating sides by index parity.
        n = len(pins)
        left = pins if n <= 10 else pins[:(n + 1) // 2]
        right = [] if n <= 10 else pins[(n + 1) // 2:]
        rows = max(len(left), len(right))
        h = max(rows * 2.54 + 2.54, 7.62)
        w = 20.32
        top = h / 2 - 2.54
        body.append(rect(-w / 2, -h / 2, w / 2, h / 2))
        for i, pn in enumerate(left):
            out.append((pn, -w / 2 - PIN_STUB, top - i * 2.54, "R0", DIR_PAS))
        for i, pn in enumerate(right):
            out.append((pn, w / 2 + PIN_STUB, top - i * 2.54, "R180", DIR_PAS))

    return out, body


def signature(part):
    """The key that decides whether two parts can share a symbol.

    Roles are part of it: two parts with identical pin names but different
    roles are different symbols, and must not be collapsed into one.
    """
    roles = part.get("roles") or {}
    return (part["kind"], tuple(part["pins"]), tuple(sorted(roles.items())))


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
            pinlist, body = make_symbol(p["kind"], p["pins"], p.get("roles"))
            kind_count[p["kind"]] += 1
            name = "%s_%d" % (p["kind"], kind_count[p["kind"]])
            symbols[key] = {"name": name, "pins": pinlist, "body": body, "kind": p["kind"]}
        sym_of[ref] = symbols[key]
    return symbols, sym_of


def symbol_xml(symbol):
    """Render one ``<symbol>`` element."""
    pins = "".join(
        '<pin name="%s" x="%.3f" y="%.3f" visible="pin" length="short" '
        'direction="%s" rot="%s"/>' % (escape(pn), px, py, direction, rot)
        for (pn, px, py, rot, direction) in symbol["pins"])
    return '<symbol name="%s">%s%s%s%s</symbol>' % (
        symbol["name"], "".join(symbol["body"]),
        text(-5.08, 9.0, ">NAME", 1.778, LAYER_NAMES),
        text(-5.08, -11.0, ">VALUE", 1.778, LAYER_VALUES),
        pins)


# --------------------------------------------------------------- supplies ---
# Ground and rail symbols. Drawing 139 of these instead of scattering 139
# cross-reference labels is what stops the sheet reading as a wall of text.
#
# The pin sits at the symbol origin with length="point", so an instance is
# placed exactly at the wire end it terminates — no offset arithmetic — and
# direction="sup" is what makes Fusion treat the node as a rail rather than a
# floating passive.

SUPPLY_PREFIX = "SUPPLY_"

# rail -> (glyph direction, visible text). "down" hangs below the wire end,
# "up" sits above it. Keeping each rail's direction fixed reads far better
# than rotating per pin.
SUPPLY_STYLE = {
    "GND":     ("down", "GND"),
    "BUSCOM":  ("down", "BUS COMMON"),
    "CHASSIS": ("down", "CHASSIS"),
    "N15":     ("down", "-15V"),
    "P15":     ("up",   "+15V"),
    "P100":    ("up",   "+100V"),
}


def supply_symbol_name(rail):
    return SUPPLY_PREFIX + rail


def make_supply_symbol(rail):
    """Return ``(pins, body)`` for one rail's symbol."""
    direction, _ = SUPPLY_STYLE[rail]
    body = []
    if direction == "down":
        body.append(wire(0, 0, 0, -2.54))
        if rail == "CHASSIS":
            # chassis: one bar with three hatch strokes
            body.append(wire(-2.54, -2.54, 2.54, -2.54))
            for x in (-1.778, 0.0, 1.778):
                body.append(wire(x, -2.54, x - 1.016, -4.064))
        else:
            body.append(wire(-2.54, -2.54, 2.54, -2.54))
            body.append(wire(-1.524, -3.81, 1.524, -3.81))
            body.append(wire(-0.508, -5.08, 0.508, -5.08))
        label_y = -8.0
    else:
        body.append(wire(0, 0, 0, 2.54))
        body.append(wire(-2.54, 2.54, 2.54, 2.54))
        body.append(wire(-2.54, 2.54, 0, 5.08))
        body.append(wire(2.54, 2.54, 0, 5.08))
        label_y = 6.0
    pins = [(rail, 0.0, 0.0, "R90" if direction == "down" else "R270")]
    return pins, body, label_y


def supply_symbol_xml(rail):
    """Render one supply ``<symbol>``."""
    pins, body, label_y = make_supply_symbol(rail)
    _, caption = SUPPLY_STYLE[rail]
    pin_xml = "".join(
        '<pin name="%s" x="%.3f" y="%.3f" visible="off" length="point" '
        'direction="sup" rot="%s"/>' % (escape(pn), px, py, rot)
        for (pn, px, py, rot) in pins)
    return '<symbol name="%s">%s%s%s</symbol>' % (
        supply_symbol_name(rail), "".join(body),
        text(-4.0, label_y, caption, 1.524, LAYER_VALUES), pin_xml)
