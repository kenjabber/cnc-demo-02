"""The merge: parts collected, cross-section nets stitched, parts placed."""

from sd_schematic.model import (
    PER_ROW,
    build_design,
    build_nets,
    build_parts,
    natural_key,
    net_name,
)

# Totals for the sheet as transcribed. They move only when sections.py changes,
# and when they do the change should be a deliberate one.
EXPECTED_PARTS = 263
EXPECTED_NETS = 165
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
