"""Render a :class:`~sd_schematic.model.Design` as EAGLE-XML that Autodesk
Fusion (Electronics) can open directly.

Nets are drawn as a short stub off each pin carrying a cross-referenced label
rather than as routed wires. Same-named labels are electrically connected --
standard EAGLE practice, and what makes a 165-net sheet browsable at all.
"""

import re
from xml.sax.saxutils import escape

from .geometry import LAYER_INFO, LAYER_NETS, layers_xml, text, wire
from .model import NOTES
from .symbols import build_symbol_library, symbol_xml

STUB = 5.08

# Which way a pin's stub runs, by pin rotation.
_STUB_DIR = {"R0": (-1, 0), "R180": (1, 0), "R90": (0, -1), "R270": (0, 1)}

DOCUMENT = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="9.6.2">
<drawing>
<settings><setting alwaysvectorfont="no"/><setting verticaltext="up"/></settings>
<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="no"
 altdistance="0.01" altunitdist="inch" altunit="inch"/>
<layers>{layers}</layers>
<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">
<libraries><library name="sd1525"><packages/><symbols>{syms}</symbols>
<devicesets>{devs}</devicesets></library></libraries>
<attributes/><variantdefs/>
<classes><class number="0" name="" width="0" drill="0"/></classes>
<parts>{parts}</parts>
<sheets><sheet>
<plain>{plain}</plain>
<instances>{inst}</instances>
<busses/>
<nets>{nets}</nets>
</sheet></sheets>
</schematic></drawing></eagle>
"""


def pin_geometry(symbol, origin, pin):
    """Return ``(px, py, ex, ey)``: the pin's connection point and stub end."""
    for (pn, dx, dy, rot) in symbol["pins"]:
        if pn == pin:
            cx, cy = origin[0] + dx, origin[1] + dy
            sx, sy = _STUB_DIR[rot]
            return cx, cy, cx + sx * STUB, cy + sy * STUB
    return None


def render(design):
    """Return the complete ``.sch`` document as a string."""
    symbols, sym_of = build_symbol_library(design.parts)

    plain = [text(0, y, "%s  --  %s" % (sname, title), 3.048, LAYER_INFO)
             for sname, title, y in design.bands]
    instances = ['<instance part="%s" gate="G$1" x="%.3f" y="%.3f"/>'
                 % (ref, design.placement[ref][0], design.placement[ref][1])
                 for ref in design.placement]

    net_xml, warnings = [], []
    for name, pinrefs in design.nets.items():
        segments = []
        for ref, pin in pinrefs:
            geo = pin_geometry(sym_of[ref], design.placement[ref], pin)
            if geo is None:
                warnings.append("no geometry %s.%s" % (ref, pin))
                continue
            cx, cy, ex, ey = geo
            segments.append(
                '<segment>%s<pinref part="%s" gate="G$1" pin="%s"/>'
                '<label x="%.3f" y="%.3f" size="1.27" layer="95" rot="R0" xref="yes"/>'
                '</segment>' % (wire(cx, cy, ex, ey, layer=LAYER_NETS, width="0.1524"),
                                ref, pin, ex, ey + 0.635))
        if segments:
            net_xml.append('<net name="%s" class="0">%s</net>'
                           % (escape(name), "".join(segments)))

    device_xml, part_xml = [], []
    seen = set()
    for ref, p in design.parts.items():
        ds = "DS_" + sym_of[ref]["name"]
        if ds not in seen:
            seen.add(ds)
            device_xml.append(
                '<deviceset name="%s" prefix="%s" uservalue="yes"><gates>'
                '<gate name="G$1" symbol="%s" x="0" y="0"/></gates>'
                '<devices><device name=""><technologies><technology name=""/>'
                '</technologies></device></devices></deviceset>'
                % (ds, re.sub(r"[^A-Za-z]", "", ref)[:3] or "X", sym_of[ref]["name"]))
        desc = NOTES.get(ref, "")
        value = (p["kind"] + ((" | " + desc) if desc else ""))[:250]
        part_xml.append('<part name="%s" library="sd1525" deviceset="%s" device="" value="%s"/>'
                        % (ref, ds, escape(value, {'"': "&quot;", "'": "&apos;"})))

    document = DOCUMENT.format(
        layers=layers_xml(),
        syms="".join(symbol_xml(s) for s in symbols.values()),
        devs="".join(device_xml),
        parts="".join(part_xml),
        plain="".join(plain),
        inst="".join(instances),
        nets="".join(net_xml))
    return document, warnings
