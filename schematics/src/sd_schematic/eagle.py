"""Serialize a placed and routed design as EAGLE-XML that Autodesk Fusion
(Electronics) can open directly.

This module owns the document format and nothing else. Where each part sits is
decided by :mod:`sd_schematic.placement`, and how nets are drawn by
:mod:`sd_schematic.route`.
"""

import re
from xml.sax.saxutils import escape

from .geometry import LAYER_NETS, layers_xml, text, wire
from .model import NOTES
from .placement import GridPlacer
from .route import StubRouter
from .symbols import build_symbol_library, symbol_xml

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
<sheets>{sheets}</sheets>
</schematic></drawing></eagle>
"""

SHEET = """<sheet>
<plain>{plain}</plain>
<instances>{inst}</instances>
<busses/>
<nets>{nets}</nets>
</sheet>"""


def segment_xml(segment):
    """One ``<segment>``: wires, then pinrefs, then junctions, then labels."""
    out = []
    for (x1, y1, x2, y2) in segment.wires:
        out.append(wire(x1, y1, x2, y2, layer=LAYER_NETS, width="0.1524"))
    for (ref, pin) in segment.pinrefs:
        out.append('<pinref part="%s" gate="G$1" pin="%s"/>' % (ref, pin))
    for (x, y) in segment.junctions:
        out.append('<junction x="%.3f" y="%.3f"/>' % (x, y))
    for (x, y, rot) in segment.labels:
        out.append('<label x="%.3f" y="%.3f" size="1.27" layer="95" rot="%s" xref="yes"/>'
                   % (x, y, rot))
    return "<segment>%s</segment>" % "".join(out)


def library_xml(design, sym_of):
    """Return ``(devicesets, parts)`` XML, in part order."""
    devices, parts, seen = [], [], set()
    for ref, p in design.parts.items():
        ds = "DS_" + sym_of[ref]["name"]
        if ds not in seen:
            seen.add(ds)
            devices.append(
                '<deviceset name="%s" prefix="%s" uservalue="yes"><gates>'
                '<gate name="G$1" symbol="%s" x="0" y="0"/></gates>'
                '<devices><device name=""><technologies><technology name=""/>'
                '</technologies></device></devices></deviceset>'
                % (ds, re.sub(r"[^A-Za-z]", "", ref)[:3] or "X", sym_of[ref]["name"]))
        desc = NOTES.get(ref, "")
        value = (p["kind"] + ((" | " + desc) if desc else ""))[:250]
        parts.append('<part name="%s" library="sd1525" deviceset="%s" device="" value="%s"/>'
                     % (ref, ds, escape(value, {'"': "&quot;", "'": "&apos;"})))
    return "".join(devices), "".join(parts)


def render(design, placer=None, router=None):
    """Return ``(document, warnings)``.

    ``placer`` and ``router`` default to the original grid-and-stubs pair.
    """
    placer = placer or GridPlacer()
    router = router or StubRouter()

    symbols, sym_of = build_symbol_library(design.parts)
    placement = placer.place(design)
    routed, warnings = router.route(design, placement, sym_of)

    sheets = []
    for sheet in placement.sheets:
        plain = "".join(text(x, y, s, size, layer) for x, y, s, size, layer in sheet.texts)
        inst = "".join(
            '<instance part="%s" gate="G$1" x="%.3f" y="%.3f"/>'
            % (ref, placement.coords[ref][0], placement.coords[ref][1])
            for ref in placement.refs_on(sheet.key))

        nets = []
        for name, segments in routed.items():
            here = [s for s in segments if s.sheet == sheet.key]
            if here:
                nets.append('<net name="%s" class="0">%s</net>'
                            % (escape(name), "".join(segment_xml(s) for s in here)))
        sheets.append(SHEET.format(plain=plain, inst=inst, nets="".join(nets)))

    devices, parts = library_xml(design, sym_of)
    document = DOCUMENT.format(
        layers=layers_xml(),
        syms="".join(symbol_xml(s) for s in symbols.values()),
        devs=devices,
        parts=parts,
        sheets="".join(sheets))
    return document, warnings
