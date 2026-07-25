"""Merge the nine transcribed sections into one part list and one net list.

The sections were each read independently off the scan, so the same node often
appears in two of them under different local names. Nets are therefore merged
with a union-find over both net names and pin references: a bare name inside a
net's connection list is a *stitch marker* joining that net to the same-named
net in another section.
"""

import re
from collections import OrderedDict, defaultdict

from .symbols import REQUIRED_ROLES, TWO_PIN

# Parts that appear in a section's nets but whose declaration lives elsewhere,
# or that need declaring outright.
EXTRA_PARTS = [
    ("R35B", "R", None),   # printed "R35" at the bottom of current-limit pot R31
                           # (the sheet also prints R35/Rt in the tach network)
    ("R91",  "R", None),
    ("R13",  "R", None),
]

# Human-readable notes carried into the .sch as part descriptions.
NOTES = {
    "R59B": 'printed "R59" - divider with R57/R58; the sheet prints R59 twice',
    "R60B": 'printed "R60" - balance-pot series element; the sheet prints R60 twice',
    "R35B": 'printed "R35" - current-limit pot return; the sheet prints R35 twice',
    "R137": 'printed "R137" (not R157) - +15 V decoupling to the driver centre tap',
    "R157": "series element in the J5 pin 10/11 motor lead",
    "D78A": "one leg of the D78 bridge", "D78B": "one leg of the D78 bridge",
    "D78C": "one leg of the D78 bridge", "D78D": "one leg of the D78 bridge",
    "RGF":  "10 ohm 12 W chassis resistor, ground-fault detection (no refdes on drawing)",
    "FGF":  "fuse, ground-fault detection (no refdes on drawing)",
    "JMP1": "A/B jumper - selects differential (B) or single-ended (A) input",
    "U1A": "U1 section, pins 1/2/3 - DIFF. AMPLIFIER",
    "U1B": "U1 section, pins 4/5/6/7/8",
    "U2B": "U2 section - A.V. AMPLIFIER",
    "U9B": "U9 section - ECC",
    "S1":  "RESET BUTTON (momentary)",
}

# Preferred names when a merged node carries several: power and ground first.
GLOBAL_ORDER = ["GND", "BUSCOM", "CHASSIS", "P15", "N15", "P100"]

class Design:
    """The merged design: what is connected to what.

    This is the electrical truth and nothing else — no geometry. Where parts
    sit is :mod:`sd_schematic.placement`; how nets are drawn is
    :mod:`sd_schematic.route`. Keeping them apart is what lets the layout be
    reworked while ``netlist.csv`` stays byte-identical.

    Attributes
    ----------
    parts : OrderedDict
        refdes -> ``{"kind", "pins", "section"}``.
    nets : OrderedDict
        net name -> sorted ``[(refdes, pin), ...]``, two or more entries.
    warnings : list of str
        Single-pin nets dropped during the merge.
    """

    def __init__(self, parts, nets, warnings):
        self.parts = parts
        self.nets = nets
        self.warnings = warnings

    @property
    def pin_connections(self):
        return sum(len(v) for v in self.nets.values())


def build_parts(sections, extra_parts=EXTRA_PARTS):
    """Collect every part declaration, first section wins on a repeat."""
    parts = OrderedDict()

    def add(ref, kind, pins, section):
        if ref in parts:
            existing = parts[ref]
            for pin in pins or ():
                if pin not in existing["pins"]:
                    existing["pins"].append(pin)
            return
        parts[ref] = {"kind": kind, "pins": list(pins) if pins else [], "section": section}

    for sname, sec in sections.items():
        for ref, kind, pins in sec["parts"]:
            add(ref, kind, pins, sname)
    for ref, kind, pins in extra_parts:
        add(ref, kind, pins, "extra")
    return parts


class _UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, a):
        self.parent.setdefault(a, a)
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def net_name(names):
    """Pick the canonical name for a merged node."""
    for g in GLOBAL_ORDER:
        if g in names:
            return g
    real = sorted(n for n in names if n.startswith("N_"))
    return real[0] if real else sorted(names)[0]


class ShortedRailsError(Exception):
    """Two supply rails merged into one node — the transcription contradicts itself."""


def _check_rails_distinct(groups):
    """The names in GLOBAL_ORDER are separate rails and must stay separate.

    They merge when one pin is transcribed onto different rails in two
    sections, and the result is silent: the smaller rail simply disappears
    into the larger one. That is how the -15 V rail was lost to GND for a
    while — see the C8 audit note in sections.py. Fail the build instead.
    """
    for g in groups.values():
        rails = sorted(set(g["names"]) & set(GLOBAL_ORDER))
        if len(rails) > 1:
            raise ShortedRailsError(
                "%s merged into one node. A pin is transcribed onto two "
                "different rails; check the pins these nets share." % " + ".join(rails))


def build_nets(sections, parts):
    """Merge the per-section nets. Mutates ``parts`` to add pins seen only here.

    Returns ``(nets, warnings)``. A node reaching only one pin is not a net; it
    is reported as a warning and dropped, which is how the seven known dangling
    pins fall out.
    """
    raw_nets = []
    for sec in sections.values():
        for name, conns in sec["nets"]:
            raw_nets.append((name, conns))

    uf = _UnionFind()
    for name, conns in raw_nets:
        key = "NET:" + name
        uf.find(key)
        for c in conns:
            if "." not in c:          # a bare name used as a stitch marker
                uf.union(key, "NET:" + c)
            else:
                uf.union(key, "PIN:" + c)

    groups = defaultdict(lambda: {"names": set(), "pins": set()})
    for name, conns in raw_nets:
        g = groups[uf.find("NET:" + name)]
        g["names"].add(name)
        for c in conns:
            if "." in c:
                g["pins"].add(c)
            else:
                g["names"].add(c)

    _check_rails_distinct(groups)

    nets = OrderedDict()
    warnings = []
    for g in groups.values():
        nm = net_name(g["names"])
        pins = set()
        # sorted, not raw set order: a pin discovered here rather than declared
        # gets appended to its part, and that order fixes the symbol's pin
        # layout. Iterating the set directly makes the output depend on the
        # process hash seed, so two runs disagree.
        for p in sorted(g["pins"], key=natural_key):
            ref, pin = p.rsplit(".", 1)
            if ref in parts:
                pins.add((ref, pin))
                if pin not in parts[ref]["pins"]:
                    parts[ref]["pins"].append(pin)
        if len(pins) >= 2:
            base, i = nm, 1
            while nm in nets:
                i += 1
                nm = "%s_%d" % (base, i)
            nets[nm] = sorted(pins)
        elif pins:
            warnings.append("single-pin net %s: %s" % (nm, sorted(pins)))

    # every part needs at least one pin, and two-terminal parts always have 1/2
    for p in parts.values():
        if not p["pins"]:
            p["pins"] = ["1", "2"]
        if p["kind"] in TWO_PIN:
            p["pins"] = ["1", "2"]

    return nets, warnings


def natural_key(name):
    """R9 before R10, pin 2 before pin 10: letters first, then the number."""
    return (re.sub(r"\d+", "", name), int(re.sub(r"\D", "", name) or 0))


def derive_pin_offsets(positions=None, wires=None, scale=None):
    """Where each pin sits on its part, read from the traced wires.

    A run records both its endpoint and the pin that endpoint lands on, so the
    pin's offset from its part's centre is already in the data -- no separate
    transcription needed. Spacing a block's pins evenly instead is a guess, and
    a wrong one: it left every wire into PWM and LOCK-OUT with a few
    millimetres of step in it, because the drawing does not space them evenly.

    Returns ``{refdes: {pin: (dx_mm, dy_mm)}}``.
    """
    from .sections import POSITIONS, SCAN, WIRES

    positions = POSITIONS if positions is None else positions
    wires = WIRES if wires is None else wires
    scale = SCAN["mm_per_px"] if scale is None else scale

    offsets = {}
    for runs in wires.values():
        for start, end, points in runs:
            for endpoint, point in ((start, points[0]), (end, points[-1])):
                if endpoint is None:
                    continue
                ref, pin = endpoint.rsplit(".", 1)
                if ref not in positions:
                    continue
                px, py = positions[ref][0], positions[ref][1]
                # Scan y counts downward, sheet y upward.
                offsets.setdefault(ref, {})[pin] = (
                    round((point[0] - px) * scale, 3),
                    round((py - point[1]) * scale, 3))
    return offsets


def resolve_roles(parts, roles_table=None, name_map=None):
    """Attach a role map to every part, and report the ones that come up short.

    Order is: the explicit table, then the pin's own name (a pin called ``B``
    is the base), then nothing. There is deliberately no positional fallback —
    guessing a role from a pin's position in the declaration is what drew
    U1A's output on the left and put U4A's collector in the base slot.
    """
    from .sections import (
        BLOCK_SIDES,
        EXTENTS,
        ROLE_FROM_PIN_NAME,
        ROLES,
        SCAN,
        WINDINGS,
    )

    roles_table = ROLES if roles_table is None else roles_table
    name_map = ROLE_FROM_PIN_NAME if name_map is None else name_map

    pin_offsets = derive_pin_offsets()
    warnings = []
    for ref, part in parts.items():
        declared = set(part["pins"])
        resolved = {}
        for role, pin in roles_table.get(ref, {}).items():
            if pin not in declared:
                warnings.append("%s: role %r names pin %r, which it does not have"
                                % (ref, role, pin))
                continue
            resolved[role] = pin
        # Inference only fills gaps. A pin the table already spoke for keeps
        # that role and gets no second one -- Q7's "E" is its gate, and must
        # not also be claimed as an emitter.
        claimed = set(resolved.values())
        for pin in part["pins"]:
            role = name_map.get(pin)
            if role and role not in resolved and pin not in claimed:
                resolved[role] = pin
                claimed.add(pin)
        if ref in WINDINGS:
            resolved["windings"] = [list(g) for g in WINDINGS[ref]]
        if ref in BLOCK_SIDES:
            resolved["sides"] = {k: list(v) for k, v in BLOCK_SIDES[ref].items()}
        if ref in pin_offsets:
            resolved["pin_offsets"] = dict(pin_offsets[ref])
        if ref in EXTENTS:
            scale = SCAN["mm_per_px"]
            resolved["extent"] = (round(EXTENTS[ref][0] * scale, 3),
                                  round(EXTENTS[ref][1] * scale, 3))
        part["roles"] = resolved

        needed = REQUIRED_ROLES.get(part["kind"])
        if needed and not all(r in resolved for r in needed):
            missing = [r for r in needed if r not in resolved]
            warnings.append("%s (%s) has no %s -- it cannot be drawn correctly"
                            % (ref, part["kind"], "/".join(missing)))
    return warnings


def build_design(sections):
    """Full pipeline: sections in, one merged :class:`Design` out."""
    parts = build_parts(sections)
    nets, warnings = build_nets(sections, parts)
    warnings += resolve_roles(parts)
    return Design(parts, nets, warnings)
