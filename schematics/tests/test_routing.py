"""Wire routing.

Geometry that looks plausible and is wrong is the failure mode here: wires that
reach a pin without touching it, a branch with no junction dot, or two nets
lying along each other so the sheet shows a connection the netlist does not
have. These tests are the reason to trust the drawn wires.
"""

from collections import defaultdict

import pytest

from sd_schematic.model import GLOBAL_ORDER
from sd_schematic.placement import ClusterPlacer
from sd_schematic.route import Segment, StubRouter, TrunkRouter, pin_geometry
from sd_schematic.symbols import build_symbol_library

RAILS = frozenset(GLOBAL_ORDER)


@pytest.fixture(scope="module")
def routed(design):
    placement = ClusterPlacer(supply_rails=RAILS).place(design)
    _, sym_of = build_symbol_library(design.parts)
    router = TrunkRouter(supply_rails=RAILS)
    nets, warnings = router.route(design, placement, sym_of)
    return placement, sym_of, router, nets, warnings


def at(x, y):
    return (round(x, 3), round(y, 3))


def graph(segment):
    """Endpoint adjacency of a segment's wires."""
    adjacency = defaultdict(set)
    for x1, y1, x2, y2 in segment.wires:
        a, b = at(x1, y1), at(x2, y2)
        if a != b:
            adjacency[a].add(b)
            adjacency[b].add(a)
    return adjacency


def reachable(adjacency):
    if not adjacency:
        return set()
    start = next(iter(adjacency))
    seen, stack = {start}, [start]
    while stack:
        for nxt in adjacency[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def test_nothing_is_lost(design, routed):
    _, _, _, nets, warnings = routed
    assert warnings == []
    total = sum(len(s.pinrefs) for segs in nets.values() for s in segs)
    assert total == design.pin_connections == 627
    for name, pins in design.nets.items():
        drawn = {p for s in nets[name] for p in s.pinrefs}
        assert drawn == set(pins), name


def test_every_segment_is_one_connected_piece(routed):
    """Wires that look right but do not meet are the classic router bug."""
    _, _, _, nets, _ = routed
    for name, segments in nets.items():
        for segment in segments:
            adjacency = graph(segment)
            assert len(reachable(adjacency)) == len(adjacency), name


def test_every_pin_touches_its_own_wires(routed):
    placement, sym_of, _, nets, _ = routed
    for name, segments in nets.items():
        for segment in segments:
            points = reachable(graph(segment))
            for ref, pin in segment.pinrefs:
                px, py, _, _ = pin_geometry(sym_of[ref], placement.coords[ref], pin)
                assert at(px, py) in points, "%s: %s.%s floats" % (name, ref, pin)


def test_no_two_nets_lie_along_each_other(routed):
    """Crossings are fine and expected. Overlaps are a short that isn't real."""
    _, _, _, nets, _ = routed
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
                    if na == nb:
                        continue
                    assert not b1 < a2 - 1e-6, \
                        "%s and %s overlap on %s at %.2f" % (na, nb, sheet, coord)


def test_junctions_sit_where_three_wires_meet(routed):
    """A branch without a dot reads as a crossing, which is the opposite."""
    _, _, _, nets, _ = routed
    for name, segments in nets.items():
        for segment in segments:
            degree = defaultdict(int)
            for x1, y1, x2, y2 in segment.wires:
                if at(x1, y1) != at(x2, y2):
                    degree[at(x1, y1)] += 1
                    degree[at(x2, y2)] += 1
            branches = {p for p, d in degree.items() if d >= 3}
            drawn = {at(x, y) for x, y in segment.junctions}
            assert drawn == branches, "%s: junctions %s, branches %s" % (
                name, sorted(drawn), sorted(branches))


def test_supply_pins_get_a_symbol_not_a_label(design, routed):
    _, _, _, nets, _ = routed
    for rail in RAILS:
        if rail not in design.nets:
            continue
        for segment in nets[rail]:
            assert segment.supplies
            assert not segment.labels


def test_declined_nets_still_get_drawn(design, routed):
    """A net the router gives up on falls back to labels, never disappears."""
    _, _, router, nets, _ = routed
    for name in set(router.declined):
        drawn = {p for s in nets[name] for p in s.pinrefs}
        assert drawn == set(design.nets[name])
        assert all(s.labels for s in nets[name] if s.pinrefs)


def test_most_connections_are_drawn_as_wires(design, routed):
    """The point of the phase. Guard the coverage so it cannot silently rot."""
    _, _, _, nets, _ = routed
    labels = sum(len(s.labels) for segs in nets.values() for s in segs)
    assert labels < 220, "%d labels -- routing coverage has regressed" % labels


def test_declining_is_bounded(routed):
    _, _, router, _, _ = routed
    assert len(set(router.declined)) <= 60


def test_router_is_deterministic(design):
    placement = ClusterPlacer(supply_rails=RAILS).place(design)
    _, sym_of = build_symbol_library(design.parts)
    runs = []
    for _ in range(2):
        nets, _ = TrunkRouter(supply_rails=RAILS).route(design, placement, sym_of)
        runs.append({n: [(s.sheet, s.wires, s.junctions) for s in segs]
                     for n, segs in nets.items()})
    assert runs[0] == runs[1]


def test_overlap_check_rejects_a_real_overlap():
    router = TrunkRouter()
    occupancy = ({}, {})
    first = Segment("s", wires=[(0, 0, 10, 0)], pinrefs=[("R1", "1")])
    router._occupy(first, occupancy, owner=("R1", "1"))

    along = Segment("s", wires=[(5, 0, 15, 0)], pinrefs=[("R2", "1")])
    assert router._would_overlap(along, occupancy)

    crossing = Segment("s", wires=[(5, -5, 5, 5)], pinrefs=[("R2", "1")])
    assert not router._would_overlap(crossing, occupancy), "crossings are allowed"

    touching = Segment("s", wires=[(10, 0, 20, 0)], pinrefs=[("R2", "1")])
    assert not router._would_overlap(touching, occupancy), "meeting end to end is fine"


def test_stub_router_still_available(design):
    """The all-labels routing stays reachable as the comparison baseline."""
    placement = ClusterPlacer(supply_rails=RAILS).place(design)
    _, sym_of = build_symbol_library(design.parts)
    nets, _ = StubRouter().route(design, placement, sym_of)
    labels = sum(len(s.labels) for segs in nets.values() for s in segs)
    assert labels == design.pin_connections


def on_wire(px, py, wire, eps=1e-6):
    x1, y1, x2, y2 = wire
    if abs(y1 - y2) < eps and abs(py - y1) < eps:
        return min(x1, x2) - eps <= px <= max(x1, x2) + eps
    if abs(x1 - x2) < eps and abs(px - x1) < eps:
        return min(y1, y2) - eps <= py <= max(y1, y2) + eps
    return False


def test_every_label_sits_on_its_own_wire(routed):
    """A label off the wire is not attached to the net.

    They were placed 0.635 mm above the wire end, which reads in Fusion as a
    loose piece of text rather than a connection.
    """
    _, _, _, nets, _ = routed
    for name, segments in nets.items():
        for segment in segments:
            for lx, ly, _ in segment.labels:
                assert any(on_wire(lx, ly, w) for w in segment.wires), \
                    "%s: label at (%.2f, %.2f) touches no wire" % (name, lx, ly)


def test_a_rail_cluster_joins_on_one_spine(design):
    """Stepping from pin to pin puts a dog-leg under the symbol."""
    from sd_schematic.placement import ScanPlacer
    from sd_schematic.route import ScanRouter
    from sd_schematic.symbols import build_symbol_library

    placement = ScanPlacer(fallback=ClusterPlacer(supply_rails=RAILS)).place(design)
    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    nets, _ = ScanRouter(supply_rails=RAILS).route(design, placement, sym_of)

    for segment in nets["P15"]:
        if len(segment.pinrefs) < 2:
            continue
        verticals = {round(w[0], 3) for w in segment.wires
                     if abs(w[0] - w[2]) < 1e-6 and abs(w[1] - w[3]) > 1e-6}
        assert len(verticals) == 1, "cluster uses %d verticals, not one spine" % len(verticals)
