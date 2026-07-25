"""Structural validation of a generated EAGLE ``.sch``.

This checks the file is internally consistent -- it says nothing about whether
the transcription matches the scan. Run it after any hand edit to
``sections.py``.
"""

import math
import xml.etree.ElementTree as ET
from collections import defaultdict

from .route import rotate_offset
from .symbols import SUPPLY_PREFIX


class Report:
    """Outcome of a validation run."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.dangling = []
        self.counts = {}

    @property
    def ok(self):
        return not self.errors

    def summary(self):
        lines = ["%-13s: %d" % (k, v) for k, v in self.counts.items()]
        lines.append("%-13s: %d" % ("dangling pins", len(self.dangling)))
        if self.dangling:
            lines.append("    " + ", ".join(sorted(self.dangling)))
        for w in self.warnings:
            lines.append("WARN  - " + w)
        if self.errors:
            lines.append("ERRORS (%d)" % len(self.errors))
            lines.extend("  - " + e for e in self.errors[:60])
        else:
            lines.append("STRUCTURAL VALIDATION PASSED")
        return "\n".join(lines)


def validate_string(xml_text):
    """Validate a ``.sch`` document held in memory."""
    return _validate(ET.fromstring(xml_text))


def validate_file(path):
    """Validate a ``.sch`` on disk."""
    return _validate(ET.parse(str(path)).getroot())


def _validate(root):
    report = Report()
    if root.tag != "eagle":
        report.errors.append("root element is <%s>, expected <eagle>" % root.tag)
        return report

    lib = root.find(".//library")
    symbols = {s.get("name"): s for s in lib.findall("./symbols/symbol")}
    devsets = {d.get("name"): d for d in lib.findall("./devicesets/deviceset")}
    parts = {p.get("name"): p for p in root.findall(".//parts/part")}
    sheets = root.findall(".//sheets/sheet")
    if not sheets:
        report.errors.append("document has no sheets")
        return report

    # Rail symbols are a drawing decoration, not part of the transcribed
    # design, so they are counted separately and kept out of "pin connects" --
    # otherwise the totals stop meaning what the netlist says.
    supply = {n for n, p in parts.items()
              if (p.get("deviceset") or "").startswith(SUPPLY_PREFIX)}

    instances, sheet_of = {}, {}
    for idx, sheet in enumerate(sheets):
        for i in sheet.findall("./instances/instance"):
            name = i.get("part")
            if name in instances:
                report.errors.append("instance %s appears on two sheets" % name)
            instances[name] = i
            sheet_of[name] = idx
    nets = [(idx, n) for idx, sheet in enumerate(sheets)
            for n in sheet.findall("./nets/net")]

    # 1. every part resolves to a deviceset, and every gate to a symbol
    for pn, p in parts.items():
        ds = devsets.get(p.get("deviceset"))
        if ds is None:
            report.errors.append("part %s references missing deviceset %s"
                                 % (pn, p.get("deviceset")))
            continue
        for g in ds.findall("./gates/gate"):
            if g.get("symbol") not in symbols:
                report.errors.append("deviceset %s gate -> missing symbol %s"
                                     % (ds.get("name"), g.get("symbol")))

    # 2. every part instantiated exactly once
    for pn in parts:
        if pn not in instances:
            report.errors.append("part %s has no instance" % pn)
    for i in instances:
        if i not in parts:
            report.errors.append("instance %s has no part" % i)

    def sym_pins(part):
        """Pin name -> (x, y, rot). Empty if the part does not resolve -- that
        is already reported above, and the caller should not blow up on it."""
        ds = devsets.get(parts[part].get("deviceset"))
        gate = ds.find("./gates/gate") if ds is not None else None
        symbol = symbols.get(gate.get("symbol")) if gate is not None else None
        if symbol is None:
            return {}
        return {p.get("name"): (float(p.get("x")), float(p.get("y")), p.get("rot", "R0"))
                for p in symbol.findall("./pin")}

    # 3. nets: pinrefs valid, every wire end reachable, no pin in two nets
    used, supply_connects = {}, 0
    net_pins = defaultdict(set)
    for sheet_idx, net in nets:
        name = net.get("name")
        for seg in net.findall("./segment"):
            pinrefs = seg.findall("./pinref")
            wires = seg.findall("./wire")
            if not pinrefs:
                report.errors.append("net %s: segment without pinref" % name)
                continue
            if not wires:
                report.errors.append("net %s: segment without wire" % name)
                continue
            for w in wires:
                if w.get("layer") != "91":
                    report.errors.append("net %s: wire not on layer 91" % name)
            ends = {(round(float(w.get(a)), 6), round(float(w.get(b)), 6))
                    for w in wires for a, b in (("x1", "y1"), ("x2", "y2"))}

            for pinref in pinrefs:
                part, pin = pinref.get("part"), pinref.get("pin")
                if part not in parts:
                    report.errors.append("net %s: pinref to unknown part %s" % (name, part))
                    continue
                if sheet_of.get(part) != sheet_idx:
                    report.errors.append("net %s: %s is drawn on another sheet" % (name, part))
                    continue
                pins = sym_pins(part)
                if pin not in pins:
                    report.errors.append("net %s: %s has no pin %s (has %s)"
                                         % (name, part, pin, sorted(pins)))
                    continue
                instance = instances[part]
                ix, iy = float(instance.get("x")), float(instance.get("y"))
                # The instance rotation turns the pin offset with it. Reading
                # the offset raw put every pin of a rotated part in the wrong
                # place -- which is what this check exists to notice.
                dx, dy = rotate_offset(pins[pin][0], pins[pin][1],
                                       instance.get("rot", "R0"))
                px, py = ix + dx, iy + dy
                if not any(math.hypot(ex - px, ey - py) <= 1e-6 for ex, ey in ends):
                    report.errors.append(
                        "net %s: no wire end at %s.%s (%.3f,%.3f)" % (name, part, pin, px, py))

                key = (part, pin)
                if key in used:
                    report.errors.append("pin %s.%s appears in two nets: %s and %s"
                                         % (part, pin, used[key], name))
                used[key] = name
                if part in supply:
                    supply_connects += 1
                else:
                    net_pins[name].add(key)

    # every net must reach at least two real pins, counting across sheets
    for name, pins in net_pins.items():
        if len(pins) < 2:
            report.errors.append("net %s reaches %d pin(s)" % (name, len(pins)))

    # 4. dangling pins (informational -- these are the untraced cross-sheet runs)
    for pn in parts:
        if pn in supply:
            continue
        for pin in sym_pins(pn):
            if (pn, pin) not in used:
                report.dangling.append("%s.%s" % (pn, pin))

    # 5. no two parts stacked on the same point
    seen = {}
    for pn, i in instances.items():
        if pn in supply:
            continue
        key = (sheet_of[pn], i.get("x"), i.get("y"))
        if key in seen:
            report.errors.append("instances %s and %s overlap at %s" % (seen[key], pn, key))
        seen[key] = pn

    report.counts = {
        "sheets": len(sheets),
        "symbols": len(symbols),
        "devicesets": len(devsets),
        "parts": len(parts) - len(supply),
        "supply symbols": len(supply),
        "nets": len({n.get("name") for _, n in nets}),
        "pin connects": len(used) - supply_connects,
        "labels": sum(len(n.findall(".//label")) for _, n in nets),
    }
    return report


# --------------------------------------------------- geometry cross-check ---
def check_scan_geometry(design, wires=None, positions=None):
    """Compare transcribed wire geometry against the merged netlist.

    This is the reason to transcribe geometry at all, beyond looking like the
    original. Connectivity on its own has no redundancy: a misread wire yields
    a plausible netlist and nothing contradicts it, which is exactly how C8
    shorted the -15 V rail to ground and went unnoticed. Wire runs are a second,
    independent reading of the same drawing. Where the two disagree, one of them
    is wrong, and you have found a transcription error instead of a layout
    preference.

    Returns a list of error strings; empty means the two records agree.
    """
    from .sections import POSITIONS, WIRES

    wires = WIRES if wires is None else wires
    positions = POSITIONS if positions is None else positions
    errors = []

    owner = {}
    for net, runs in wires.items():
        if net not in design.nets:
            errors.append("geometry names net %s, which the netlist does not have" % net)
            continue
        expected = set(design.nets[net])
        reached = set()

        for start, end, points in runs:
            if len(points) < 2:
                errors.append("%s: a run needs at least two points" % net)
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                if x1 != x2 and y1 != y2:
                    errors.append("%s: run is diagonal at (%d,%d)" % (net, x1, y1))
            for endpoint in (start, end):
                if endpoint is None:
                    continue
                ref, pin = endpoint.rsplit(".", 1)
                if ref not in design.parts:
                    errors.append("%s: run ends on unknown part %s" % (net, ref))
                    continue
                if pin not in design.parts[ref]["pins"]:
                    errors.append("%s: %s has no pin %s" % (net, ref, pin))
                    continue
                if (ref, pin) not in expected:
                    # The disagreement worth having: the drawing runs a wire
                    # from this pin, the netlist puts the pin somewhere else.
                    errors.append(
                        "%s: geometry runs a wire to %s, but the netlist puts "
                        "that pin on %s" % (net, endpoint, _net_of(design, ref, pin)))
                    continue
                if owner.get((ref, pin), net) != net:
                    errors.append("%s: %s is also drawn on %s"
                                  % (net, endpoint, owner[(ref, pin)]))
                owner[(ref, pin)] = net
                reached.add((ref, pin))

        transcribed = {p for p in expected if p[0] in positions}
        if transcribed and reached != transcribed:
            missing = sorted(transcribed - reached)
            if missing:
                errors.append("%s: no run reaches %s"
                              % (net, ", ".join("%s.%s" % m for m in missing)))

        if not _runs_are_connected(runs):
            errors.append("%s: its runs do not join up" % net)

    return errors


def _net_of(design, ref, pin):
    for name, pins in design.nets.items():
        if (ref, pin) in pins:
            return name
    return "no net"


def _touches(a, b):
    """Do two runs of the same net meet?

    At a shared point, in a T part-way along, or at a crossing — within one net
    all three are connections.
    """
    from .route import crossing, on_segment

    pa = [tuple(p) for p in a]
    pb = [tuple(p) for p in b]
    if set(pa) & set(pb):
        return True
    for points, other in ((pa, pb), (pb, pa)):
        for point in points:
            for u, v in zip(other, other[1:]):
                if on_segment(point, u, v):
                    return True
    for u1, v1 in zip(pa, pa[1:]):
        for u2, v2 in zip(pb, pb[1:]):
            if crossing((u1[0], u1[1], v1[0], v1[1]),
                        (u2[0], u2[1], v2[0], v2[1])) is not None:
                return True
    return False


def _runs_are_connected(runs):
    """Every run must reach the others. A lone run is trivially fine."""
    if len(runs) < 2:
        return True
    paths = [pts for _, _, pts in runs]
    seen, stack = {0}, [0]
    while stack:
        i = stack.pop()
        for j, other in enumerate(paths):
            if j not in seen and _touches(paths[i], other):
                seen.add(j)
                stack.append(j)
    return len(seen) == len(runs)
