"""The rendered .sch: well-formed, complete, and reproducible."""

import xml.etree.ElementTree as ET

from sd_schematic import eagle
from sd_schematic.eagle import SUPPLY_RAILS
from sd_schematic.model import build_design
from sd_schematic.placement import SECTION_TITLE, GridPlacer, sheet_assignment
from sd_schematic.route import StubRouter
from sd_schematic.sections import SECTIONS
from sd_schematic.symbols import SUPPLY_PREFIX


def test_document_is_well_formed_eagle_xml(sch):
    root = ET.fromstring(sch)
    assert root.tag == "eagle"
    assert root.get("version") == "9.6.2"


def test_library_is_self_contained(sch):
    root = ET.fromstring(sch)
    lib = root.find(".//library")
    assert lib.get("name") == "sd1525"
    symbols = {s.get("name") for s in lib.findall("./symbols/symbol")}
    for ds in lib.findall("./devicesets/deviceset"):
        for gate in ds.findall("./gates/gate"):
            assert gate.get("symbol") in symbols


def real_parts(root):
    """Part names excluding the rail symbols, which are drawing decoration."""
    return [p.get("name") for p in root.findall(".//parts/part")
            if not (p.get("deviceset") or "").startswith(SUPPLY_PREFIX)]


def test_every_part_is_instantiated_once(sch, design):
    root = ET.fromstring(sch)
    parts = [p.get("name") for p in root.findall(".//parts/part")]
    instances = [i.get("part") for i in root.findall(".//instances/instance")]
    assert sorted(real_parts(root)) == sorted(design.parts)
    assert sorted(instances) == sorted(parts), "every part instantiated exactly once"


def test_nets_carry_every_pin_connection(sch, design):
    root = ET.fromstring(sch)
    real = set(real_parts(root))
    rendered = {(n.get("name"), pr.get("part"), pr.get("pin"))
                for n in root.findall(".//nets/net")
                for pr in n.findall(".//pinref")
                if pr.get("part") in real}
    expected = {(name, ref, pin)
                for name, pins in design.nets.items() for ref, pin in pins}
    assert rendered == expected


def test_net_stubs_are_on_the_right_layers(sch):
    """Every segment carries a wire; a label if it has one is on layer 95.

    A segment terminated by a rail symbol has no label at all -- that is the
    point of the rail symbols.
    """
    root = ET.fromstring(sch)
    for net in root.findall(".//nets/net"):
        for seg in net.findall("./segment"):
            assert seg.findall("./wire"), "segment with no wire"
            for w in seg.findall("./wire"):
                assert w.get("layer") == "91"
            for label in seg.findall("./label"):
                assert label.get("layer") == "95"


def test_notes_reach_the_part_value(sch):
    """>VALUE carries a note when there is one, and nothing when there is not.

    The original prints reference designators only, so a plain resistor has no
    value to show; it used to read "R", 111 times over.
    """
    root = ET.fromstring(sch)
    values = {p.get("name"): p.get("value") for p in root.findall(".//parts/part")}
    assert "the sheet prints R59 twice" in values["R59B"]
    assert not values["R1"]

    kinds = {d.get("name"): d.findtext("./description")
             for d in root.findall(".//devicesets/deviceset")}
    ds = {p.get("name"): p.get("deviceset") for p in root.findall(".//parts/part")}
    assert kinds[ds["R1"]] == "R"


def test_each_sheet_is_titled_and_framed(sch, design):
    root = ET.fromstring(sch)
    keys = set(sheet_assignment(design).values())
    plain = "".join(t.text or "" for t in root.findall(".//plain/text"))
    for key in keys:
        assert key in plain
        assert SECTION_TITLE[key] in plain

    sheets = root.findall(".//sheets/sheet")
    assert len(sheets) == len(keys)
    for sheet in sheets:
        frame = sheet.find("./plain/frame")
        assert frame is not None, "no frame -- xref labels would have nothing to point at"
        assert int(frame.get("columns")) > 0 and int(frame.get("rows")) > 0


def test_render_reports_no_missing_geometry(design):
    _, warnings = eagle.render(design)
    assert warnings == []


def test_output_is_reproducible():
    """Two independent builds must agree byte for byte.

    The generator used to iterate a set of pin names, which made the symbol
    pin order depend on the process hash seed.
    """
    first, _ = eagle.render(build_design(SECTIONS))
    second, _ = eagle.render(build_design(SECTIONS))
    assert first == second


def test_grid_placer_still_produces_one_sheet():
    """The original single-sheet layout stays available for comparison."""
    document, _ = eagle.render(build_design(SECTIONS),
                               placer=GridPlacer(), router=StubRouter())
    root = ET.fromstring(document)
    assert len(root.findall(".//sheets/sheet")) == 1
    assert root.find(".//sheets/sheet/plain/frame") is None


def test_supply_symbols_replace_the_rail_labels(sch, design):
    """Rail pins get a symbol, and no label."""
    root = ET.fromstring(sch)
    supply = {p.get("name") for p in root.findall(".//parts/part")
              if (p.get("deviceset") or "").startswith(SUPPLY_PREFIX)}
    expected = sum(len(design.nets[r]) for r in SUPPLY_RAILS if r in design.nets)
    assert len(supply) == expected

    for net in root.findall(".//nets/net"):
        if net.get("name") in SUPPLY_RAILS:
            assert net.findall(".//label") == [], "%s still uses labels" % net.get("name")

    labels = len(root.findall(".//nets/net//label"))
    assert labels == design.pin_connections - expected
