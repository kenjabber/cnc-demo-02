"""Drawing the wires the draughtsman drew, and checking them against the netlist.

The cross-check is the point of this file. Connectivity on its own has no
redundancy -- a misread wire produces a plausible netlist and nothing
contradicts it, which is how C8 shorted the -15 V rail to ground unnoticed.
Transcribed geometry is a second, independent reading of the same drawing, so
the two can be made to disagree out loud.
"""

import copy

import pytest

from sd_schematic.model import GLOBAL_ORDER
from sd_schematic.placement import ClusterPlacer, ScanPlacer
from sd_schematic.route import (
    ScanRouter,
    _attach,
    crossing,
    on_segment,
    pin_geometry,
    split_at_touchpoints,
)
from sd_schematic.sections import WIRES
from sd_schematic.symbols import build_symbol_library
from sd_schematic.validate import check_scan_geometry

RAILS = frozenset(GLOBAL_ORDER)


@pytest.fixture(scope="module")
def scan_routed(design):
    placement = ScanPlacer(fallback=ClusterPlacer(supply_rails=RAILS)).place(design)
    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    router = ScanRouter(supply_rails=RAILS)
    nets, warnings = router.route(design, placement, sym_of)
    return placement, sym_of, router, nets, warnings


# --- the cross-check -------------------------------------------------------

def test_geometry_and_netlist_agree(design):
    assert check_scan_geometry(design) == []


def test_a_wire_to_the_wrong_pin_is_caught(design):
    """The C8 shape: the drawing runs a wire somewhere the netlist does not."""
    wires = copy.deepcopy(WIRES)
    wires["N_U9_OUT"] = [("U9A.1", "R104.2", wires["N_U9_OUT"][0][2])]
    errors = check_scan_geometry(design, wires=wires)
    assert any("netlist puts that pin on GND" in e for e in errors)


def test_a_pin_with_no_wire_is_caught(design):
    wires = copy.deepcopy(WIRES)
    wires["N_U9_SUM"] = [wires["N_U9_SUM"][0]]
    errors = check_scan_geometry(design, wires=wires)
    assert any("no run reaches R95.2" in e for e in errors)


def test_a_diagonal_run_is_caught(design):
    wires = copy.deepcopy(WIRES)
    wires["N_U9_OUT"] = [("U9A.1", "PWM.1", [(2304, 2587), (2392, 2600)])]
    assert any("diagonal" in e for e in check_scan_geometry(design, wires=wires))


def test_runs_that_do_not_join_up_are_caught(design):
    wires = copy.deepcopy(WIRES)
    runs = list(wires["N_XFMR_CT"])
    runs[1] = (runs[1][0], runs[1][1], [(9000, 9000), (9100, 9000)])
    wires["N_XFMR_CT"] = runs
    assert any("do not join up" in e for e in check_scan_geometry(design, wires=wires))


def test_an_unknown_net_is_caught(design):
    assert any("does not have" in e
               for e in check_scan_geometry(design, wires={"N_NOPE": []}))


# --- geometry helpers ------------------------------------------------------

def test_crossing_within_a_net_is_a_connection():
    assert crossing((0, 5, 10, 5), (5, 0, 5, 10)) == (5.0, 5.0)
    assert crossing((0, 5, 10, 5), (50, 0, 50, 10)) is None
    assert crossing((0, 5, 10, 5), (0, 7, 10, 7)) is None, "parallel never crosses"


def test_on_segment_is_strict_about_endpoints():
    assert on_segment((5, 0), (0, 0), (10, 0))
    assert not on_segment((0, 0), (0, 0), (10, 0)), "an endpoint is not interior"


def test_split_cuts_at_tees_and_crossings():
    """A run stopping part-way along another must become a real join."""
    spine = (0, 0, 0, 100)
    tee = (0, 50, 20, 50)
    wires = split_at_touchpoints([spine, tee])
    assert (0.0, 0.0, 0.0, 50.0) in wires and (0.0, 50.0, 0.0, 100.0) in wires

    cross = (-10, 30, 10, 30)
    wires = split_at_touchpoints([spine, cross])
    assert (0.0, 0.0, 0.0, 30.0) in wires, "crossing within a net splits too"


def test_attach_keeps_the_run_orthogonal():
    path = [(10.0, 0.0), (50.0, 0.0)]
    out = _attach(path, (10.0, 6.0))
    assert out[0] == (10.0, 6.0)
    for a, b in zip(out, out[1:]):
        assert a[0] == b[0] or a[1] == b[1], "the correction must not go diagonal"


def test_attach_is_a_no_op_when_already_aligned():
    path = [(10.0, 0.0), (50.0, 0.0)]
    assert _attach(path, (12.0, 0.0)) == [(12.0, 0.0), (50.0, 0.0)]


# --- the router ------------------------------------------------------------

def test_most_transcribed_nets_are_drawn_from_the_scan(scan_routed):
    """Coverage, not totality.

    A transcribed run is declined if it would lie along another net, exactly as
    the trunk router declines. Correct beats complete: an overlap shows a
    connection the netlist does not have.
    """
    _, _, router, _, _ = scan_routed
    assert set(router.from_scan) <= set(WIRES)
    assert len(router.from_scan) >= 12, "scan coverage has regressed"


def test_declined_transcriptions_say_so(scan_routed):
    _, _, router, _, warnings = scan_routed
    for name in set(WIRES) - set(router.from_scan):
        assert any(name in w for w in warnings), "%s declined silently" % name


def test_scan_wires_never_lie_along_another_net(design, scan_routed):
    """The guarantee the trunk router makes, which this router skipped.

    ScanRouter drew straight over other nets until it was made to check --
    twelve overlapping pairs on sheet 8, which reads as a wrong hookup.
    """
    from collections import defaultdict

    _, _, _, nets, _ = scan_routed
    per_sheet = defaultdict(lambda: (defaultdict(list), defaultdict(list)))
    for name, segments in nets.items():
        for segment in segments:
            horizontal, vertical = per_sheet[segment.sheet]
            for x1, y1, x2, y2 in segment.wires:
                if abs(y1 - y2) < 1e-6 and abs(x1 - x2) > 1e-6:
                    horizontal[round(y1, 3)].append((min(x1, x2), max(x1, x2), name))
                elif abs(x1 - x2) < 1e-6 and abs(y1 - y2) > 1e-6:
                    vertical[round(x1, 3)].append((min(y1, y2), max(y1, y2), name))
    for sheet, axes in per_sheet.items():
        for axis in axes:
            for coord, spans in axis.items():
                spans.sort()
                for (a1, a2, na), (b1, b2, nb) in zip(spans, spans[1:]):
                    if na != nb:
                        assert not b1 < a2 - 1e-6, \
                            "%s and %s overlap on %s at %.2f" % (na, nb, sheet, coord)


def test_scan_drawn_nets_reach_all_their_pins(design, scan_routed):
    placement, sym_of, router, nets, _ = scan_routed
    for name in router.from_scan:
        (segment,) = nets[name]
        assert set(segment.pinrefs) == set(design.nets[name])
        points = set()
        for x1, y1, x2, y2 in segment.wires:
            points.add((round(x1, 3), round(y1, 3)))
            points.add((round(x2, 3), round(y2, 3)))
        for ref, pin in segment.pinrefs:
            px, py, _, _ = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                        placement.rot.get(ref, "R0"))
            assert (round(px, 3), round(py, 3)) in points, "%s: %s.%s" % (name, ref, pin)


def test_a_scan_drawn_branch_gets_its_junction(scan_routed):
    """Where three wires meet in a transcribed net, a dot is drawn."""
    _, _, router, nets, _ = scan_routed
    dotted = 0
    for name in router.from_scan:
        for segment in nets[name]:
            dotted += len(segment.junctions)
    assert dotted >= 1


def test_scan_wires_are_orthogonal(scan_routed):
    _, _, router, nets, _ = scan_routed
    for name in router.from_scan:
        (segment,) = nets[name]
        for x1, y1, x2, y2 in segment.wires:
            assert abs(x1 - x2) < 1e-6 or abs(y1 - y2) < 1e-6, name


def test_untranscribed_nets_still_route(design, scan_routed):
    """Everything outside the transcribed block keeps working."""
    _, _, _, nets, _ = scan_routed
    total = sum(len(s.pinrefs) for segs in nets.values() for s in segs)
    assert total == design.pin_connections


def test_router_is_deterministic(design):
    placement = ScanPlacer(fallback=ClusterPlacer(supply_rails=RAILS)).place(design)
    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    runs = []
    for _ in range(2):
        nets, _ = ScanRouter(supply_rails=RAILS).route(design, placement, sym_of)
        runs.append({n: [(s.sheet, s.wires, s.junctions) for s in segs]
                     for n, segs in nets.items()})
    assert runs[0] == runs[1]


# --- rotation --------------------------------------------------------------

def test_rotation_moves_the_pin_and_turns_its_stub():
    symbol = {"pins": [("1", -7.62, 0.0, "R0", "pas"), ("2", 7.62, 0.0, "R180", "pas")]}
    flat = pin_geometry(symbol, (0.0, 0.0), "1")
    assert flat == pytest.approx((-7.62, 0.0, -12.7, 0.0))

    # R270 stands the part up with pin 1 at the top, stub running upward.
    upright = pin_geometry(symbol, (0.0, 0.0), "1", "R270")
    assert upright[:2] == pytest.approx((0.0, 7.62))
    assert upright[3] > upright[1], "the stub must turn with the pin"


def test_rotated_parts_are_emitted_with_their_rotation(design):
    from sd_schematic import eagle

    document, _ = eagle.render(
        design,
        placer=ScanPlacer(fallback=ClusterPlacer(supply_rails=RAILS)),
        router=ScanRouter(supply_rails=RAILS))
    assert 'part="R104" gate="G$1" x=' in document
    marker = document[document.index('part="R104" gate="G$1" x='):]
    assert 'rot="R270"' in marker[:marker.index("/>")]


def test_traced_pins_sit_where_their_wire_expects_them(design, scan_routed):
    """A pin derived from the wire drawn to it must land exactly on it.

    Anything else shows up as a step in the wire, and rounding part positions
    onto a 2.54 mm grid was enough to put one into every run.

    Only the size-variable kinds take their pin positions from the tracing --
    a resistor keeps its standard shape, and a millimetre along its own axis
    costs nothing because it is a longer lead, not a bend.
    """
    placement, sym_of, _, _, _ = scan_routed
    from sd_schematic.model import derive_pin_offsets

    checked = 0
    for ref, pins in derive_pin_offsets().items():
        if design.parts[ref]["kind"] not in ("BLOCK", "XFMR"):
            continue
        ox, oy = placement.coords[ref]
        for pin, (dx, dy) in pins.items():
            px, py, _, _ = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                        placement.rot.get(ref, "R0"))
            # The derived offset fixes the axis across the wire; the other is
            # left on the box edge, so only one has to line up.
            assert min(abs(px - ox - dx), abs(py - oy - dy)) < 0.01, \
                "%s.%s drifted from its traced position" % (ref, pin)
            checked += 1
    assert checked >= 20, "fixture sanity: expected many traced pins"


def test_transcribed_runs_stay_straight(scan_routed):
    """Most traced runs are a single straight wire; none should be fussy.

    Every extra segment is a bend the draughtsman did not draw, put there by
    reconciling a pin onto a wire that missed it.
    """
    _, _, router, nets, _ = scan_routed
    total = sum(len(s.wires) for n in router.from_scan for s in nets[n])
    assert total <= 34, "%d segments -- wires have grown bends again" % total

    straight = sum(1 for n in router.from_scan
                   if sum(len(s.wires) for s in nets[n]) == 1)
    assert straight >= 10, "only %d runs are a single wire" % straight


def test_scan_placement_is_not_grid_snapped(design):
    """Snapping would reintroduce the sub-millimetre steps."""
    placement = ScanPlacer(fallback=ClusterPlacer(supply_rails=RAILS)).place(design)
    from sd_schematic.sections import POSITIONS

    offgrid = [r for r in POSITIONS
               if abs(placement.coords[r][0] / 2.54
                      - round(placement.coords[r][0] / 2.54)) > 1e-6]
    assert offgrid, "positions look snapped to the grid again"


def test_series_parts_sit_midway_between_their_neighbours(design, scan_routed):
    """R73 was hard against PWM with three times the clearance the other side."""
    placement, sym_of, _, _, _ = scan_routed

    def at(ref, pin):
        return pin_geometry(sym_of[ref], placement.coords[ref], pin,
                            placement.rot.get(ref, "R0"))[0]

    for part, before, after in (("R73", ("PWM", "3"), ("LOCKOUT", "1")),
                                ("R76", ("PWM", "4"), ("LOCKOUT", "2"))):
        left = at(part, "1") - at(*before)
        right = at(*after) - at(part, "2")
        assert abs(left - right) < 0.5, "%s: %.2f vs %.2f" % (part, left, right)
        assert left > 2.0, "%s is crowding its neighbour" % part


def test_a_rail_feeding_neighbouring_pins_draws_one_symbol(design, scan_routed):
    """C56 and R137 share a +15 V node on the drawing, not two supplies."""
    _, _, _, nets, _ = scan_routed
    merged = [s for s in nets["P15"]
              if s.sheet == "S8_pwmdrv" and len(s.pinrefs) > 1]
    assert merged, "the two +15 V pins are still drawn separately"
    for segment in merged:
        assert len(segment.supplies) == 1
        assert {p[0] for p in segment.pinrefs} == {"C56", "R137"}


def test_every_rail_segment_has_exactly_one_symbol(scan_routed):
    _, _, _, nets, _ = scan_routed
    for rail in RAILS:
        for segment in nets.get(rail, []):
            assert len(segment.supplies) == 1
            assert not segment.labels


def test_the_centre_tap_spine_is_clear_of_the_driver_pins(scan_routed):
    """A branch stub 0.76 mm long puts the junction dot on top of the pin."""
    placement, sym_of, _, nets, _ = scan_routed
    (segment,) = nets["N_XFMR_CT"]
    spine = [w for w in segment.wires if abs(w[0] - w[2]) < 1e-6]
    assert spine
    x = spine[0][0]
    for ref in ("DRIVER1", "DRIVER2"):
        px = pin_geometry(sym_of[ref], placement.coords[ref], "3",
                          placement.rot.get(ref, "R0"))[0]
        assert abs(px - x) > 4.0, "%s.3 sits on the spine" % ref


def test_the_op_amp_inputs_meet_their_wires(design, scan_routed):
    """R104's wire ran down past U9A's own pin and back up to reach it."""
    _, _, router, nets, _ = scan_routed
    assert "N_U9_NONINV" in router.from_scan
    (segment,) = nets["N_U9_NONINV"]
    assert len(segment.wires) <= 2, "the wire is still doubling back"
