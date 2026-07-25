"""The merge: parts collected, cross-section nets stitched, parts placed."""

import pytest

from sd_schematic.model import (
    PER_ROW,
    ShortedRailsError,
    build_design,
    build_nets,
    build_parts,
    natural_key,
    net_name,
)

# Totals for the sheet as transcribed. They move only when sections.py changes,
# and when they do the change should be a deliberate one.
EXPECTED_PARTS = 263
EXPECTED_NETS = 166
EXPECTED_PIN_CONNECTIONS = 627


def test_totals(design):
    assert len(design.parts) == EXPECTED_PARTS
    assert len(design.nets) == EXPECTED_NETS
    assert design.pin_connections == EXPECTED_PIN_CONNECTIONS


def test_extra_parts_are_declared(design):
    # R35B is the second part the drawing prints as "R35"; it appears only in
    # other sections' nets, so without EXTRA_PARTS its connections are dropped.
    assert design.parts["R35B"]["section"] == "extra"
    # R91 and R13 are listed as extras too, but a section does declare them --
    # the first declaration wins, so they keep their real section.
    assert design.parts["R91"]["section"] == "S7_moddemod"
    assert design.parts["R13"]["section"] == "S2_avamp"


def test_ground_is_stitched_across_sections(design):
    """Every section declares its own GND; they must merge into one node."""
    gnd = design.nets["GND"]
    sections = {design.parts[ref]["section"] for ref, _ in gnd}
    assert len(sections) > 5
    assert len(gnd) > 50


def test_supply_rails_stay_distinct(design):
    """GND, P15 and N15 are separate nodes.

    C8 was once transcribed with its plates swapped between S1_input and
    S4_comp, which merged N15 into GND and silently deleted the -15 V rail --
    all 16 of its pins reported as ground. build_nets now refuses to build a
    design where two rails merge; this pins the outcome.
    """
    for rail in ("GND", "P15", "N15"):
        assert rail in design.nets, "%s is missing -- merged into another rail?" % rail
    assert len(design.nets["N15"]) == 16
    assert ("U1B", "4") in design.nets["N15"]
    assert ("C8", "2") in design.nets["N15"]
    assert ("C8", "1") in design.nets["GND"]


def test_merging_two_rails_is_an_error():
    """The guard fires rather than silently swallowing a rail."""
    sections = {
        "A": {"parts": [("C1", "CPOL", None), ("U1", "IC", ["4", "8"])],
              "nets": [("N15", ["U1.4", "C1.1"]), ("GND", ["C1.2"])]},
        "B": {"parts": [],
              "nets": [("N15", ["C1.2"]), ("GND", ["C1.1"])]},
    }
    parts = build_parts(sections, extra_parts=[])
    with pytest.raises(ShortedRailsError, match="GND \\+ N15"):
        build_nets(sections, parts)


def test_chassis_merges_two_sections(design):
    # S1 has R36.2, S9 has RGF.1 -- both named CHASSIS, so they are one node.
    assert set(design.nets["CHASSIS"]) == {("R36", "2"), ("RGF", "1")}


def test_every_net_has_at_least_two_pins(design):
    for name, pins in design.nets.items():
        assert len(pins) >= 2, "%s is a single-pin net" % name


def test_single_pin_nets_are_reported_not_silently_dropped(design):
    """The seven untraced cross-sheet runs are known; four surface as warnings."""
    assert len(design.warnings) == 4
    assert all("single-pin net" in w for w in design.warnings)


def test_two_pin_parts_are_normalised(design):
    for ref, p in design.parts.items():
        if p["kind"] in ("R", "C", "CPOL", "D", "ZENER", "LED"):
            assert p["pins"] == ["1", "2"], ref


def test_net_name_prefers_power_and_ground():
    assert net_name({"N_FOO", "GND"}) == "GND"
    assert net_name({"N_FOO", "P15"}) == "P15"
    # GND outranks P15 when a node somehow carries both
    assert net_name({"P15", "GND"}) == "GND"
    # otherwise the lowest N_ name wins
    assert net_name({"N_ZED", "N_ABC"}) == "N_ABC"
    assert net_name({"WEIRD"}) == "WEIRD"


def test_natural_key_orders_numerically():
    assert sorted(["R10", "R9", "R100"], key=natural_key) == ["R9", "R10", "R100"]
    assert sorted(["14", "2", "10"], key=natural_key) == ["2", "10", "14"]


def test_stitch_marker_merges_two_sections():
    sections = {
        "A": {"parts": [("R1", "R", None), ("R2", "R", None)],
              "nets": [("N_X", ["R1.1", "R2.1"])]},
        "B": {"parts": [("R3", "R", None)],
              "nets": [("N_Y", ["R3.1", "N_X"])]},
    }
    parts = build_parts(sections, extra_parts=[])
    nets, warnings = build_nets(sections, parts)
    assert warnings == []
    assert len(nets) == 1
    (name, pins), = nets.items()
    assert name == "N_X"                     # lowest N_ name of the merged node
    assert pins == [("R1", "1"), ("R2", "1"), ("R3", "1")]


def test_pin_discovery_order_is_deterministic():
    """A pin seen only in a net still lands on its part in a stable position.

    Pins are picked up net by net, and sorted within each net -- so U1 gets
    pin 14 (from N_A) before pin 2 (from N_B). What matters is that repeated
    builds agree; iterating the raw set made this depend on the hash seed.
    """
    sections = {
        "A": {"parts": [("U1", "IC", None), ("R1", "R", None), ("R2", "R", None)],
              "nets": [("N_A", ["U1.14", "U1.7", "R1.1"]), ("N_B", ["U1.2", "R2.1"])]},
    }
    runs = []
    for _ in range(2):
        parts = build_parts(sections, extra_parts=[])
        build_nets(sections, parts)
        runs.append(parts["U1"]["pins"])
    assert runs[0] == runs[1] == ["7", "14", "2"]


def test_placement_grid_wraps_and_never_overlaps(design):
    positions = list(design.placement.values())
    assert len(positions) == len(set(positions)), "two parts share a point"
    assert len(design.placement) == len(design.parts)

    # each section's band is a PER_ROW-wide grid
    for sname, _, _ in design.bands:
        refs = [r for r, p in design.parts.items() if p["section"] == sname]
        xs = {design.placement[r][0] for r in refs}
        assert len(xs) <= PER_ROW


def test_build_design_does_not_mutate_the_source_sections():
    from sd_schematic.sections import SECTIONS

    before = {k: (len(v["parts"]), len(v["nets"])) for k, v in SECTIONS.items()}
    build_design(SECTIONS)
    after = {k: (len(v["parts"]), len(v["nets"])) for k, v in SECTIONS.items()}
    assert before == after
