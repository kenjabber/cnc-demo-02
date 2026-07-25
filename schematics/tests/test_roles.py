"""Pin roles.

Roles used to be inferred from a pin's position in its declaration, which is
right only when the transcription happened to list the pins in canonical order.
It did not: U1A's output was drawn on the left, U4A's collector sat in the base
slot, and Q7's grounded source occupied its gate position. Seven of thirteen
transistors were wrong.

These tests exist so that cannot come back quietly.
"""

import pytest

from sd_schematic.model import build_parts, resolve_roles
from sd_schematic.sections import ROLE_FROM_PIN_NAME, ROLES, SECTIONS
from sd_schematic.symbols import REQUIRED_ROLES, build_symbol_library


def test_every_role_requiring_part_resolves(design):
    """The one that matters: no part of a role-requiring kind is left guessing."""
    unresolved = []
    for ref, part in design.parts.items():
        needed = REQUIRED_ROLES.get(part["kind"])
        if needed and not all(r in part["roles"] for r in needed):
            unresolved.append("%s (%s)" % (ref, part["kind"]))
    assert unresolved == []


def test_no_role_warnings(design):
    assert [w for w in design.warnings if "role" in w or "cannot be drawn" in w] == []


def test_roles_table_names_real_parts_and_real_pins(design):
    for ref, roles in ROLES.items():
        assert ref in design.parts, "ROLES names unknown part %s" % ref
        declared = set(design.parts[ref]["pins"])
        for role, pin in roles.items():
            assert pin in declared, "%s: role %s -> pin %s, which it lacks" % (ref, role, pin)
            assert role in {"out", "in-", "in+", "v+", "v-", "b", "c", "e", "g", "d", "s"}


def test_a_role_never_maps_two_pins_to_the_same_terminal():
    for ref, roles in ROLES.items():
        pins = list(roles.values())
        assert len(pins) == len(set(pins)), "%s reuses a pin for two roles" % ref


def test_pin_names_supply_their_own_roles():
    """A pin called B is the base; those parts need no table entry."""
    parts = build_parts({"A": {"parts": [("Q99", "NPN", ["B", "C", "E"])], "nets": []}},
                        extra_parts=[])
    assert resolve_roles(parts, roles_table={}) == []
    assert parts["Q99"]["roles"] == {"b": "B", "c": "C", "e": "E"}


def test_the_table_beats_the_pin_name():
    """Q7's pin "E" is its gate, whatever the letter suggests."""
    parts = build_parts({"A": {"parts": [("Q7", "NMOS", ["S", "D", "E"])], "nets": []}},
                        extra_parts=[])
    resolve_roles(parts, roles_table={"Q7": {"s": "S", "d": "D", "g": "E"}})
    assert parts["Q7"]["roles"]["g"] == "E"
    assert "e" not in parts["Q7"]["roles"]


def test_missing_roles_are_reported_not_guessed():
    """No positional fallback: an unresolvable part warns instead of guessing."""
    parts = build_parts({"A": {"parts": [("U99", "OPAMP", ["1", "2", "3"])], "nets": []}},
                        extra_parts=[])
    warnings = resolve_roles(parts, roles_table={}, name_map={})
    assert any("cannot be drawn correctly" in w for w in warnings)
    assert parts["U99"]["roles"] == {}


def test_a_role_pointing_at_a_missing_pin_is_reported():
    parts = build_parts({"A": {"parts": [("Q1", "NPN", ["B", "C", "E"])], "nets": []}},
                        extra_parts=[])
    warnings = resolve_roles(parts, roles_table={"Q1": {"b": "NOPE"}})
    assert any("does not have" in w for w in warnings)


@pytest.mark.parametrize("ref", ["U1A", "U2A", "U2B", "U2C", "U3", "U8A", "U8B", "U9A", "U9B"])
def test_amplifier_outputs_land_on_the_right(design, ref):
    _, sym_of = build_symbol_library(design.parts)
    roles = design.parts[ref]["roles"]
    at = {e[0]: e for e in sym_of[ref]["pins"]}
    assert at[roles["out"]][1] > 0, "%s output is not on the right" % ref
    assert at[roles["in-"]][1] < 0 and at[roles["in+"]][1] < 0


@pytest.mark.parametrize("ref", ["Q2", "U4A", "U4B", "U4C", "U4D", "Q5",
                                 "Q9", "Q11", "Q12", "Q14"])
def test_bipolar_terminals_land_correctly(design, ref):
    _, sym_of = build_symbol_library(design.parts)
    roles = design.parts[ref]["roles"]
    at = {e[0]: e for e in sym_of[ref]["pins"]}
    assert at[roles["b"]][1] < 0, "%s base is not on the left" % ref
    assert at[roles["c"]][2] > 0, "%s collector is not on top" % ref
    assert at[roles["e"]][2] < 0, "%s emitter is not on the bottom" % ref


@pytest.mark.parametrize("ref", ["Q1", "Q6", "Q7"])
def test_fet_terminals_land_correctly(design, ref):
    _, sym_of = build_symbol_library(design.parts)
    roles = design.parts[ref]["roles"]
    at = {e[0]: e for e in sym_of[ref]["pins"]}
    assert at[roles["g"]][1] < 0, "%s gate is not on the left" % ref
    assert at[roles["d"]][2] > 0 and at[roles["s"]][2] < 0


def test_role_from_pin_name_covers_both_conventions():
    assert set(ROLE_FROM_PIN_NAME) == {"B", "C", "E", "G", "D", "S"}


def test_sections_still_declares_every_roled_part():
    declared = {ref for sec in SECTIONS.values() for ref, _, _ in sec["parts"]}
    assert set(ROLES) <= declared
