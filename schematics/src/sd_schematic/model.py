"""Merge the nine transcribed sections into one part list and one net list.

The sections were each read independently off the scan, so the same node often
appears in two of them under different local names. Nets are therefore merged
with a union-find over both net names and pin references: a bare name inside a
net's connection list is a *stitch marker* joining that net to the same-named
net in another section.
"""

import re
from collections import OrderedDict, defaultdict

from .symbols import TWO_PIN

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

# Section layout order and titles for the placement grid.
SECTION_ORDER = ["S1_input", "S4_comp", "S2_avamp", "S3_basedrive", "S7_moddemod",
                 "S5_supply", "S6_fault", "S8_pwmdrv", "S9_output", "extra"]
SECTION_TITLE = {
    "S1_input":     "INPUT / DIFF AMPLIFIER / SIG-AUX-TACH POTS",
    "S4_comp":      "COMPENSATION, CLAMP, CURRENT LIMIT, BALANCE",
    "S2_avamp":     "A.V. AMPLIFIER / RMS TIMER",
    "S3_basedrive": "J1 LOGIC INPUTS / U4 DRIVE",
    "S7_moddemod":  "TEMP SENSE, RESET LATCH, T1/T2 MOD-DEMOD",
    "S5_supply":    "BUS & +/-15 V SENSE, OVER-VOLT / SURGE DETECT",
    "S6_fault":     "U6/U5 FAULT LOGIC & LED ASSY",
    "S8_pwmdrv":    "PWM / CLOCK / LOCK-OUT / DRIVERS",
    "S9_output":    "OUTPUT H-BRIDGE, D78, J5, GROUND-FAULT SENSE",
    "extra":        "MISC",
}

COL_W, ROW_H, PER_ROW = 43.18, 33.02, 12


class Design:
    """The merged design: parts, nets, and where each part sits on the sheet.

    Attributes
    ----------
    parts : OrderedDict
        refdes -> ``{"kind", "pins", "section"}``.
    nets : OrderedDict
        net name -> sorted ``[(refdes, pin), ...]``, two or more entries.
    placement : dict
        refdes -> ``(x, y)`` in millimetres.
    warnings : list of str
        Single-pin nets dropped during the merge.
    """

    def __init__(self, parts, nets, placement, warnings):
        self.parts = parts
        self.nets = nets
        self.placement = placement
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


def place_parts(parts):
    """Lay parts out on a functional grid, one band per section.

    Returns ``(placement, section_bands)`` where each band is
    ``(section_name, title, y)`` for the heading text.
    """
    placement = {}
    bands = []
    y_cursor = 0.0
    for sname in SECTION_ORDER:
        refs = [r for r, p in parts.items() if p["section"] == sname]
        if not refs:
            continue
        refs.sort(key=natural_key)
        bands.append((sname, SECTION_TITLE[sname], y_cursor + 12.7))
        for i, ref in enumerate(refs):
            col, row = i % PER_ROW, i // PER_ROW
            placement[ref] = (col * COL_W, y_cursor - row * ROW_H)
        y_cursor -= ((len(refs) + PER_ROW - 1) // PER_ROW) * ROW_H + 25.4
    return placement, bands


def build_design(sections):
    """Full pipeline: sections in, a placed and merged :class:`Design` out."""
    parts = build_parts(sections)
    nets, warnings = build_nets(sections, parts)
    placement, bands = place_parts(parts)
    design = Design(parts, nets, placement, warnings)
    design.bands = bands
    return design
