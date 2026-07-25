"""Placement from scan coordinates.

The property that makes a 263-part transcription tractable is that coverage can
be partial: coordinates go in one block at a time, and every intermediate state
still builds and still places every part. These tests exist mostly to protect
that, because it is the thing a later refactor would quietly break.
"""

import pytest

from sd_schematic.model import GLOBAL_ORDER
from sd_schematic.placement import (
    SCAN_AREA,
    ClusterPlacer,
    ScanPlacer,
    SheetPlacer,
    fit_box,
    sheet_assignment,
)
from sd_schematic.sections import POSITIONS, SCAN, SECTIONS
from test_placement import check_placement_invariants, symbol_extent

RAILS = frozenset(GLOBAL_ORDER)


def test_no_positions_falls_back_entirely(design):
    """With nothing transcribed, the result is exactly the auto-placement."""
    auto = ClusterPlacer(supply_rails=RAILS).place(design)
    scan = ScanPlacer(positions={},
                      fallback=ClusterPlacer(supply_rails=RAILS)).place(design)
    assert scan.coords == auto.coords
    assert scan.sheet_of == auto.sheet_of


def test_holds_the_invariants(design):
    check_placement_invariants(design, ScanPlacer().place(design))


def test_is_deterministic(design):
    a, b = ScanPlacer().place(design), ScanPlacer().place(design)
    assert a.coords == b.coords
    assert list(a.coords) == list(b.coords)


def test_relative_arrangement_survives_the_mapping(design):
    """A block should keep the shape the draughtsman gave it."""
    placement = ScanPlacer().place(design)
    for a, b in (("PWM", "LOCKOUT"), ("R94", "PWM"), ("LOCKOUT", "DRIVER1")):
        assert POSITIONS[a][0] < POSITIONS[b][0]
        assert placement.coords[a][0] < placement.coords[b][0], "%s..%s" % (a, b)
    # scan y grows downward, sheet y grows upward
    assert POSITIONS["R94"][1] < POSITIONS["CLOCK"][1]
    assert placement.coords["R94"][1] > placement.coords["CLOCK"][1]


def test_parts_without_a_position_are_still_placed(design):
    """Partial coverage is the whole point; nothing may be dropped."""
    placement = ScanPlacer().place(design)
    positioned = set(POSITIONS)
    assert positioned & set(design.parts), "fixture sanity: some are known"
    for ref in design.parts:
        assert ref in placement.coords
    unknown = [r for r in design.parts if r not in positioned]
    assert unknown, "fixture sanity: coverage is still partial"


def test_known_and_unknown_do_not_collide(design):
    """Auto-placed parts sit below the mapped block, not on top of it."""
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    placement = ScanPlacer(fallback=ClusterPlacer(supply_rails=RAILS)).place(design)
    for sheet in placement.sheets:
        boxes = []
        for ref in placement.refs_on(sheet.key):
            x, y = placement.coords[ref]
            hw, hh = symbol_extent(sym_of[ref])
            boxes.append((ref, x - hw, y - hh, x + hw, y + hh))
        for i, (ra, ax1, ay1, ax2, ay2) in enumerate(boxes):
            for rb, bx1, by1, bx2, by2 in boxes[i + 1:]:
                assert not (ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2), \
                    "%s and %s overlap on %s" % (ra, rb, sheet.key)


def test_a_sheet_with_one_known_part_falls_back_wholesale(design):
    """One point defines no arrangement, so do not pretend it does."""
    single = {"PWM": POSITIONS["PWM"]}
    placement = ScanPlacer(positions=single, fallback=SheetPlacer()).place(design)
    auto = SheetPlacer().place(design)
    assert placement.coords == auto.coords


def test_positions_name_parts_that_exist(design):
    for ref in POSITIONS:
        assert ref in design.parts, "POSITIONS names unknown part %s" % ref


def test_positions_lie_inside_the_scan(design):
    width, height = SCAN["size_px"]
    for ref, entry in POSITIONS.items():
        assert 0 <= entry[0] <= width, "%s x=%d" % (ref, entry[0])
        assert 0 <= entry[1] <= height, "%s y=%d" % (ref, entry[1])
        if len(entry) > 2:
            assert entry[2] in ("R0", "R90", "R180", "R270"), ref


def test_rotation_reaches_the_placement(design):
    """R104 and the two electrolytics stand on end above their grounds."""
    placement = ScanPlacer().place(design)
    assert placement.rot["R104"] == "R270"
    assert placement.rot["C56"] == "R270"
    assert placement.rot["R73"] == "R0"


def test_positions_belong_to_one_sheet_so_far(design):
    """The example block is S8_pwmdrv; a stray entry elsewhere is a typo."""
    assignment = sheet_assignment(design)
    assert {assignment[r] for r in POSITIONS} == {"S8_pwmdrv"}


def test_fit_box_preserves_aspect_ratio():
    """Stretching the axes independently would misrepresent the drawing."""
    points = [(0, 0), (100, 50)]
    convert = fit_box(points, (0.0, 0.0, 200.0, 200.0))
    (x1, y1), (x2, y2) = convert(0, 0), convert(100, 50)
    assert abs(x2 - x1) == pytest.approx(200.0)
    assert abs(y2 - y1) == pytest.approx(100.0), "y must not stretch to fill"


def test_fit_box_flips_the_y_axis():
    convert = fit_box([(0, 0), (10, 10)], (0.0, 0.0, 100.0, 100.0))
    top = convert(0, 0)         # top of the scan
    bottom = convert(0, 10)     # further down the scan
    assert top[1] > bottom[1], "scan y grows downward, sheet y upward"


def test_fit_box_survives_a_degenerate_span():
    convert = fit_box([(5, 5), (5, 5)], SCAN_AREA)
    assert convert(5, 5) is not None


def test_wire_runs_name_real_pins(design):
    from sd_schematic.sections import WIRES

    for net, runs in WIRES.items():
        assert net in design.nets, "WIRES names unknown net %s" % net
        for start, end, points in runs:
            assert len(points) >= 2, "%s: a run needs two points" % net
            for endpoint in (start, end):
                if endpoint is None:
                    continue
                ref, pin = endpoint.rsplit(".", 1)
                assert ref in design.parts, "%s: unknown part %s" % (net, ref)
                assert pin in design.parts[ref]["pins"], "%s: %s has no pin %s" % (
                    net, ref, pin)


def test_wire_runs_are_orthogonal(design):
    """The drawing is drafted on horizontals and verticals; keep it that way."""
    from sd_schematic.sections import WIRES

    for net, runs in WIRES.items():
        for _, _, points in runs:
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                assert x1 == x2 or y1 == y2, "%s: diagonal run %s->%s" % (
                    net, (x1, y1), (x2, y2))


def test_a_series_part_with_one_traced_end_lands_on_it(design):
    """R104's top is traced; its other end goes to ground.

    Four millimetres out put it hard up against the op-amp.
    """
    from sd_schematic.model import derive_pin_offsets
    from sd_schematic.route import pin_geometry
    from sd_schematic.symbols import build_symbol_library

    placement = ScanPlacer(fallback=ClusterPlacer(supply_rails=RAILS)).place(design)
    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)

    traced = derive_pin_offsets()["R104"]
    assert len(traced) == 1, "fixture sanity: R104 has one traced end"
    (pin, _), = traced.items()
    px, py, _, _ = pin_geometry(sym_of["R104"], placement.coords["R104"], pin,
                                placement.rot.get("R104", "R0"))
    # The wire drawn to it must start exactly there.
    from sd_schematic.route import ScanRouter

    nets, _ = ScanRouter(supply_rails=RAILS).route(design, placement, sym_of)
    ends = set()
    for segment in nets["N_U9_NONINV"]:
        for x1, y1, x2, y2 in segment.wires:
            ends |= {(round(x1, 3), round(y1, 3)), (round(x2, 3), round(y2, 3))}
    assert (round(px, 3), round(py, 3)) in ends
