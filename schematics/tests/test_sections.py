"""The transcribed data is hand-edited, so guard its shape."""

import re

from sd_schematic.model import EXTRA_PARTS
from sd_schematic.placement import SECTION_ORDER
from sd_schematic.sections import SECTIONS

REFDES = re.compile(r"^[A-Z][A-Z0-9_]*$")


def test_every_section_is_laid_out():
    """A section with no entry in SECTION_ORDER would be silently unplaced."""
    assert set(SECTIONS) <= set(SECTION_ORDER)


def test_sections_have_parts_and_nets():
    for name, sec in SECTIONS.items():
        assert sec["parts"], "%s declares no parts" % name
        assert sec["nets"], "%s declares no nets" % name


def test_part_declarations_are_well_formed():
    for name, sec in SECTIONS.items():
        for ref, kind, pins in sec["parts"]:
            assert REFDES.match(ref), "%s: bad refdes %r" % (name, ref)
            assert kind and kind.isupper(), "%s: bad kind %r on %s" % (name, kind, ref)
            assert pins is None or (pins and all(pins)), "%s: bad pin list on %s" % (name, ref)


def test_no_duplicate_pins_within_a_net():
    for name, sec in SECTIONS.items():
        for net, conns in sec["nets"]:
            assert len(conns) == len(set(conns)), "%s/%s repeats a connection" % (name, net)


def test_every_pin_reference_names_a_declared_part():
    """A typo'd refdes in a net is silently dropped by the merge, so catch it here."""
    declared = {ref for sec in SECTIONS.values() for ref, _, _ in sec["parts"]}
    declared |= {ref for ref, _, _ in EXTRA_PARTS}

    unknown = set()
    for sec in SECTIONS.values():
        for _, conns in sec["nets"]:
            for c in conns:
                if "." in c:
                    unknown.add(c.rsplit(".", 1)[0])
    assert unknown - declared == set()
