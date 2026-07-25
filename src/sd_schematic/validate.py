"""Structural validation of a generated EAGLE ``.sch``.

This checks the file is internally consistent -- it says nothing about whether
the transcription matches the scan. Run it after any hand edit to
``sections.py``.
"""

import math
import xml.etree.ElementTree as ET


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
    sheet = root.find(".//sheets/sheet")
    instances = {i.get("part"): i for i in sheet.findall("./instances/instance")}
    nets = sheet.findall("./nets/net")

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

    # 3. nets: pinrefs valid, wires land on the pin, no pin in two nets
    used = {}
    for net in nets:
        name = net.get("name")
        segments = net.findall("./segment")
        if len(segments) < 2:
            report.errors.append("net %s has %d segment(s)" % (name, len(segments)))
        for seg in segments:
            pinref = seg.find("./pinref")
            w = seg.find("./wire")
            if pinref is None:
                report.errors.append("net %s: segment without pinref" % name)
                continue
            part, pin = pinref.get("part"), pinref.get("pin")
            if part not in parts:
                report.errors.append("net %s: pinref to unknown part %s" % (name, part))
                continue
            pins = sym_pins(part)
            if pin not in pins:
                report.errors.append("net %s: %s has no pin %s (has %s)"
                                     % (name, part, pin, sorted(pins)))
                continue
            ix, iy = float(instances[part].get("x")), float(instances[part].get("y"))
            px, py = ix + pins[pin][0], iy + pins[pin][1]
            wx, wy = float(w.get("x1")), float(w.get("y1"))
            if math.hypot(wx - px, wy - py) > 1e-6:
                report.errors.append(
                    "net %s: wire for %s.%s starts at (%.3f,%.3f) not pin (%.3f,%.3f)"
                    % (name, part, pin, wx, wy, px, py))
            if w.get("layer") != "91":
                report.errors.append("net %s: wire not on layer 91" % name)
            label = seg.find("./label")
            if label is None or label.get("layer") != "95":
                report.errors.append("net %s: missing/mislayered label" % name)
            key = (part, pin)
            if key in used:
                report.errors.append("pin %s.%s appears in two nets: %s and %s"
                                     % (part, pin, used[key], name))
            used[key] = name

    # 4. dangling pins (informational -- these are the untraced cross-sheet runs)
    for pn in parts:
        for pin in sym_pins(pn):
            if (pn, pin) not in used:
                report.dangling.append("%s.%s" % (pn, pin))

    # 5. no two parts stacked on the same point
    seen = {}
    for pn, i in instances.items():
        key = (i.get("x"), i.get("y"))
        if key in seen:
            report.errors.append("instances %s and %s overlap at %s" % (seen[key], pn, key))
        seen[key] = pn

    report.counts = {
        "symbols": len(symbols),
        "devicesets": len(devsets),
        "parts": len(parts),
        "nets": len(nets),
        "pin connects": len(used),
    }
    return report
