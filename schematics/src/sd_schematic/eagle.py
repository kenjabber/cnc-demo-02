"""Serialize a placed and routed design as EAGLE-XML that Autodesk Fusion
(Electronics) can open directly.

This module owns the document format and nothing else. Where each part sits is
decided by :mod:`sd_schematic.placement`, and how nets are drawn by
:mod:`sd_schematic.route`.
"""

import re
from xml.sax.saxutils import escape

from .geometry import LAYER_NETS, layers_xml, text, wire
from .model import GLOBAL_ORDER, NOTES
from .placement import ClusterPlacer
from .route import TrunkRouter
from .symbols import (
    SUPPLY_STYLE,
    build_symbol_library,
    supply_symbol_name,
    supply_symbol_xml,
    symbol_xml,
)

# Nets drawn as rail symbols rather than as scattered labels.
SUPPLY_RAILS = frozenset(GLOBAL_ORDER)

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


def segment_xml(segment, supply_names):
    """One ``<segment>``: wires, then pinrefs, then junctions, then labels.

    ``supply_names`` maps a supply placement to the instance name assigned for
    it, so the rail symbol joins the net through a pinref like any other part.
    """
    out = []
    for (x1, y1, x2, y2) in segment.wires:
        out.append(wire(x1, y1, x2, y2, layer=LAYER_NETS, width="0.1524"))
    for (ref, pin) in segment.pinrefs:
        out.append('<pinref part="%s" gate="G$1" pin="%s"/>' % (ref, pin))
    for i, (rail, _, _, _) in enumerate(segment.supplies):
        out.append('<pinref part="%s" gate="G$1" pin="%s"/>'
                   % (supply_names[(id(segment), i)], rail))
    for (x, y) in segment.junctions:
        out.append('<junction x="%.3f" y="%.3f"/>' % (x, y))
    for (x, y, rot) in segment.labels:
        out.append('<label x="%.3f" y="%.3f" size="1.27" layer="95" rot="%s" xref="yes"/>'
                   % (x, y, rot))
    return "<segment>%s</segment>" % "".join(out)


def name_supplies(routed):
    """Assign an instance name to every rail symbol the router asked for.

    Walks nets and segments in order so the names are stable across builds.
    Returns ``(supply_names, instances)`` where ``instances`` is
    ``[(name, rail, x, y, rot, sheet), ...]``.
    """
    supply_names, instances = {}, []
    counts = {}
    for segments in routed.values():
        for segment in segments:
            for i, (rail, x, y, rot) in enumerate(segment.supplies):
                counts[rail] = counts.get(rail, 0) + 1
                inst = "%s%d" % (rail, counts[rail])
                supply_names[(id(segment), i)] = inst
                instances.append((inst, rail, x, y, rot, segment.sheet))
    return supply_names, instances


def supply_deviceset_xml(rail):
    return ('<deviceset name="%s" prefix="%s" uservalue="no"><gates>'
            '<gate name="G$1" symbol="%s" x="0" y="0" addlevel="request"/></gates>'
            '<devices><device name=""><technologies><technology name=""/>'
            '</technologies></device></devices></deviceset>'
            % (supply_symbol_name(rail), rail, supply_symbol_name(rail)))


def library_xml(design, sym_of, supply_instances):
    """Return ``(devicesets, parts)`` XML, in part order then supply order."""
    devices, parts, seen = [], [], set()
    for ref, p in design.parts.items():
        ds = "DS_" + sym_of[ref]["name"]
        if ds not in seen:
            seen.add(ds)
            devices.append(
                '<deviceset name="%s" prefix="%s" uservalue="yes">'
                '<description>%s</description><gates>'
                '<gate name="G$1" symbol="%s" x="0" y="0"/></gates>'
                '<devices><device name=""><technologies><technology name=""/>'
                '</technologies></device></devices></deviceset>'
                % (ds, re.sub(r"[^A-Za-z]", "", ref)[:3] or "X",
                   escape(p["kind"]), sym_of[ref]["name"]))
        # The original is a simplified schematic with reference designators and
        # no values, so >VALUE carries only a note where there is one. Printing
        # the kind put a literal "R" under all 111 resistors.
        value = NOTES.get(ref, "")[:250]
        parts.append('<part name="%s" library="sd1525" deviceset="%s" device="" value="%s"/>'
                     % (ref, ds, escape(value, {'"': "&quot;", "'": "&apos;"})))

    for rail in sorted({r for _, r, _, _, _, _ in supply_instances}):
        devices.append(supply_deviceset_xml(rail))
    for inst, rail, _, _, _, _ in supply_instances:
        parts.append('<part name="%s" library="sd1525" deviceset="%s" device=""/>'
                     % (inst, supply_symbol_name(rail)))

    return "".join(devices), "".join(parts)


def frame_xml(frame):
    x1, y1, x2, y2, cols, rows = frame
    return ('<frame x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" columns="%d" rows="%d" '
            'border-left="yes" border-top="yes" border-right="yes" border-bottom="yes" '
            'layer="94"/>' % (x1, y1, x2, y2, cols, rows))


def render(design, placer=None, router=None):
    """Return ``(document, warnings)``.

    Defaults to one sheet per functional section, ordered by signal chain,
    with rail symbols for the supplies and real wires where they can be routed.
    Pass ``GridPlacer()`` and a bare ``StubRouter()`` for the original
    single-sheet, all-labels output.
    """
    placer = placer or ClusterPlacer(supply_rails=SUPPLY_RAILS)
    router = router or TrunkRouter(supply_rails=SUPPLY_RAILS)

    symbols, sym_of = build_symbol_library(
        design.parts, drawn_extents=getattr(placer, "drawn_extents", False))
    placement = placer.place(design)
    routed, warnings = router.route(design, placement, sym_of)
    supply_names, supply_instances = name_supplies(routed)

    sheets = []
    for sheet in placement.sheets:
        plain = frame_xml(sheet.frame) if sheet.frame else ""
        plain += "".join(text(x, y, s, size, layer) for x, y, s, size, layer in sheet.texts)

        inst = "".join(
            '<instance part="%s" gate="G$1" x="%.3f" y="%.3f"%s/>'
            % (ref, placement.coords[ref][0], placement.coords[ref][1],
               '' if placement.rot.get(ref, "R0") == "R0"
               else ' rot="%s"' % placement.rot[ref])
            for ref in placement.refs_on(sheet.key))
        inst += "".join(
            '<instance part="%s" gate="G$1" x="%.3f" y="%.3f" rot="%s"/>' % (name, x, y, rot)
            for name, _, x, y, rot, key in supply_instances if key == sheet.key)

        nets = []
        for name, segments in routed.items():
            here = [s for s in segments if s.sheet == sheet.key]
            if here:
                nets.append('<net name="%s" class="0">%s</net>'
                            % (escape(name),
                               "".join(segment_xml(s, supply_names) for s in here)))
        sheets.append(SHEET.format(plain=plain, inst=inst, nets="".join(nets)))

    devices, parts = library_xml(design, sym_of, supply_instances)
    document = DOCUMENT.format(
        layers=layers_xml(),
        syms=("".join(symbol_xml(s) for s in symbols.values())
              + "".join(supply_symbol_xml(r) for r in sorted(SUPPLY_STYLE)
                        if any(rail == r for _, rail, _, _, _, _ in supply_instances))),
        devs=devices,
        parts=parts,
        sheets="".join(sheets))
    return document, warnings
