"""The rendered .sch: well-formed, complete, and reproducible."""

import xml.etree.ElementTree as ET

from sd_schematic import eagle
from sd_schematic.model import build_design
from sd_schematic.placement import SECTION_TITLE, GridPlacer
from sd_schematic.sections import SECTIONS


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


def test_every_part_is_instantiated_once(sch, design):
    root = ET.fromstring(sch)
    parts = [p.get("name") for p in root.findall(".//parts/part")]
    instances = [i.get("part") for i in root.findall(".//instances/instance")]
    assert sorted(parts) == sorted(design.parts)
    assert sorted(instances) == sorted(parts)


def test_nets_carry_every_pin_connection(sch, design):
    root = ET.fromstring(sch)
    rendered = {(n.get("name"), pr.get("part"), pr.get("pin"))
                for n in root.findall(".//nets/net")
                for pr in n.findall(".//pinref")}
    expected = {(name, ref, pin)
                for name, pins in design.nets.items() for ref, pin in pins}
    assert rendered == expected


def test_net_stubs_are_labelled_on_the_right_layers(sch):
    root = ET.fromstring(sch)
    for net in root.findall(".//nets/net"):
        for seg in net.findall("./segment"):
            assert seg.find("./wire").get("layer") == "91"
            assert seg.find("./label").get("layer") == "95"


def test_notes_reach_the_part_value(sch):
    root = ET.fromstring(sch)
    values = {p.get("name"): p.get("value") for p in root.findall(".//parts/part")}
    assert "the sheet prints R59 twice" in values["R59B"]
    assert values["R1"] == "R"


def test_section_headings_are_drawn(sch, design):
    root = ET.fromstring(sch)
    plain = "".join(t.text or "" for t in root.findall(".//plain/text"))
    for sname in {p["section"] for p in design.parts.values()}:
        assert sname in plain
        assert SECTION_TITLE[sname] in plain


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


def test_one_sheet_per_placement_sheet(sch):
    """The serializer emits exactly the sheets the placer asked for."""
    root = ET.fromstring(sch)
    sheets = root.findall(".//sheets/sheet")
    assert len(sheets) == len(GridPlacer().place(build_design(SECTIONS)).sheets)
