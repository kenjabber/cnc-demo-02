"""Placement strategies.

These invariants are deliberately strategy-agnostic: any placer added later
should be able to run through :func:`check_placement_invariants` unchanged.
"""

from sd_schematic.model import GLOBAL_ORDER
from sd_schematic.placement import (
    PER_ROW,
    SHEET_MARGIN,
    ClusterPlacer,
    GridPlacer,
    SheetPlacer,
    components,
    natural_key,
    sheet_assignment,
    signal_graph,
)
from sd_schematic.route import pin_geometry


def check_placement_invariants(design, placement):
    """Hold for every strategy, whatever geometry it chooses."""
    assert set(placement.coords) == set(design.parts), "every part placed exactly once"

    keys = {s.key for s in placement.sheets}

    # Overlap only matters within a page: two parts on different sheets may
    # legitimately sit at the same coordinate.
    for key in keys:
        refs = placement.refs_on(key)
        positions = [placement.coords[r] for r in refs]
        assert len(positions) == len(set(positions)), "two parts overlap on sheet %s" % key

    assert keys, "at least one sheet"
    for ref, key in placement.sheet_of.items():
        assert key in keys, "%s is on unknown sheet %r" % (ref, key)

    placed = sum(len(placement.refs_on(s.key)) for s in placement.sheets)
    assert placed == len(design.parts), "parts must not be lost or duplicated across sheets"


def test_grid_placer_holds_the_invariants(design):
    check_placement_invariants(design, GridPlacer().place(design))


def test_sheet_placer_holds_the_invariants(design):
    check_placement_invariants(design, SheetPlacer().place(design))


def test_sheet_placer_gives_every_section_its_own_framed_sheet(design):
    placement = SheetPlacer().place(design)
    keys = set(sheet_assignment(design).values())
    assert {s.key for s in placement.sheets} == keys
    for sheet in placement.sheets:
        assert sheet.frame is not None
        assert sheet.texts, "%s has no title" % sheet.key


def test_r35b_is_filed_with_the_block_it_belongs_to(design):
    """It is the drawing's second "R35" -- the current-limit pot return.

    Its declaring section is the EXTRA_PARTS catch-all, which would put it on a
    MISC sheet of one part. SHEET_OF files it next to R31 instead.
    """
    assert design.parts["R35B"]["section"] == "extra"
    assert SheetPlacer().place(design).sheet_of["R35B"] == "S4_comp"
    assert "extra" not in {s.key for s in SheetPlacer().place(design).sheets}


def test_everything_sits_inside_its_frame(design):
    """Parts must clear the frame border, not merely fall inside the page."""
    placement = SheetPlacer().place(design)
    for sheet in placement.sheets:
        x1, y1, x2, y2, _, _ = sheet.frame
        for ref in placement.refs_on(sheet.key):
            x, y = placement.coords[ref]
            assert x1 + SHEET_MARGIN <= x <= x2 - SHEET_MARGIN, "%s x=%.1f" % (ref, x)
            assert y1 + SHEET_MARGIN <= y <= y2 - SHEET_MARGIN, "%s y=%.1f" % (ref, y)


def test_grid_placer_wraps_at_per_row(design):
    placement = GridPlacer().place(design)
    for sname in {p["section"] for p in design.parts.values()}:
        refs = [r for r, p in design.parts.items() if p["section"] == sname]
        xs = {placement.coords[r][0] for r in refs}
        assert len(xs) <= PER_ROW


def test_grid_placer_is_deterministic(design):
    a = GridPlacer().place(design)
    b = GridPlacer().place(design)
    assert a.coords == b.coords
    assert list(a.coords) == list(b.coords), "iteration order matters for XML output"


def test_grid_placer_draws_a_heading_per_section(design):
    placement = GridPlacer().place(design)
    (sheet,) = placement.sheets
    sections = {p["section"] for p in design.parts.values()}
    assert len(sheet.texts) == len(sections)
    drawn = " ".join(t[2] for t in sheet.texts)
    for sname in sections:
        assert sname in drawn


def test_natural_key_orders_numerically():
    assert sorted(["R10", "R9", "R100"], key=natural_key) == ["R9", "R10", "R100"]


def symbol_extent(symbol):
    """Half-width and half-height of a symbol, from its pin envelope."""
    xs = [e[1] for e in symbol["pins"]]
    ys = [e[2] for e in symbol["pins"]]
    return max(abs(min(xs)), abs(max(xs))), max(abs(min(ys)), abs(max(ys)))


def test_symbols_do_not_collide_on_a_sheet(design):
    """Bounding boxes, not just centres.

    Real device symbols are bigger than the featureless boxes they replaced --
    J1's pin strip alone is 35.6 mm tall -- so "no two parts share a point" is
    no longer enough to know the sheet is legible.
    """
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts)
    placement = SheetPlacer().place(design)

    for sheet in placement.sheets:
        boxes = []
        for ref in placement.refs_on(sheet.key):
            x, y = placement.coords[ref]
            hw, hh = symbol_extent(sym_of[ref])
            boxes.append((ref, x - hw, y - hh, x + hw, y + hh))
        for i, (ra, ax1, ay1, ax2, ay2) in enumerate(boxes):
            for rb, bx1, by1, bx2, by2 in boxes[i + 1:]:
                overlap = ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2
                assert not overlap, "%s and %s overlap on %s" % (ra, rb, sheet.key)


# --- connectivity-driven ordering ------------------------------------------

RAILS = frozenset(GLOBAL_ORDER)


def cluster():
    return ClusterPlacer(supply_rails=RAILS)


def net_span(design, placement, sym_of):
    """Total Manhattan bounding-box span of every same-sheet signal net.

    The objective the placer exists to reduce. Power nets are excluded: they
    reach everywhere and would swamp the measurement.
    """
    total = 0.0
    for name, pins in design.nets.items():
        if name in RAILS:
            continue
        points = []
        for ref, pin in pins:
            geo = pin_geometry(sym_of[ref], placement.coords[ref], pin)
            if geo:
                points.append((placement.sheet_of[ref], geo[0], geo[1]))
        for sheet in {p[0] for p in points}:
            here = [p for p in points if p[0] == sheet]
            if len(here) < 2:
                continue
            xs = [p[1] for p in here]
            ys = [p[2] for p in here]
            total += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return total


def test_cluster_placer_holds_the_invariants(design):
    check_placement_invariants(design, cluster().place(design))


def test_cluster_placer_is_deterministic(design):
    a, b = cluster().place(design), cluster().place(design)
    assert a.coords == b.coords
    assert list(a.coords) == list(b.coords)


def test_cluster_placement_shortens_the_wiring(design):
    """The whole point. Guard the gain so a refactor cannot quietly undo it."""
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts)
    by_refdes = net_span(design, SheetPlacer().place(design), sym_of)
    by_chain = net_span(design, cluster().place(design), sym_of)
    assert by_chain < by_refdes * 0.65, "%.0f mm vs %.0f mm" % (by_chain, by_refdes)


def test_cluster_placer_keeps_symbols_apart(design):
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts)
    placement = cluster().place(design)
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


class FakeDesign:
    def __init__(self, nets):
        self.nets = nets


def test_power_nets_are_not_treated_as_adjacency():
    """Everything touches ground; it says nothing about who sits where.

    A small rail is the case that matters -- a big one is already dropped by
    the size filter, so excluding rails has to be its own rule.
    """
    fake = FakeDesign({"CHASSIS": [("R1", "2"), ("R2", "1")],
                       "N_SIG": [("R2", "2"), ("R3", "1")]})
    refs = ["R1", "R2", "R3"]

    counted = signal_graph(fake, refs, supply_rails=frozenset())
    assert counted["R1"] == {"R2"}, "sanity: it would be an edge if not excluded"

    ignored = signal_graph(fake, refs, supply_rails=frozenset(["CHASSIS"]))
    assert ignored["R1"] == set()
    assert ignored["R2"] == {"R3"}, "signal nets still count"


def test_big_nets_are_not_treated_as_adjacency(design):
    """N_SUM reaches ten pins -- that is a bus, not a pair of neighbours."""
    refs = [r for r, k in sheet_assignment(design).items() if k == "S1_input"]
    adjacency = signal_graph(design, refs, RAILS, max_pins=6)
    sums = {r for r, _ in design.nets["N_SUM"] if r in set(refs)}
    for a in sums:
        assert not (sums - {a}) <= adjacency[a], "N_SUM was treated as a clique"


def test_a_simple_chain_comes_out_in_order():
    adjacency = {"R1": {"R2"}, "R2": {"R1", "R3"}, "R3": {"R2", "R4"},
                 "R4": {"R3"}, "R9": set()}
    groups = components(adjacency)
    assert groups[0] == ["R1", "R2", "R3", "R4"]
    assert groups[1] == ["R9"]


def test_components_come_out_biggest_first():
    adjacency = {"A1": {"A2"}, "A2": {"A1"}, "B1": {"B2"}, "B2": {"B1", "B3"},
                 "B3": {"B2"}}
    assert [len(g) for g in components(adjacency)] == [3, 2]
