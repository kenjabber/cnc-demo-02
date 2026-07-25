"""Placement strategies.

These invariants are deliberately strategy-agnostic: any placer added later
should be able to run through :func:`check_placement_invariants` unchanged.
"""

from sd_schematic.placement import PER_ROW, GridPlacer, natural_key


def check_placement_invariants(design, placement):
    """Hold for every strategy, whatever geometry it chooses."""
    assert set(placement.coords) == set(design.parts), "every part placed exactly once"

    positions = list(placement.coords.values())
    assert len(positions) == len(set(positions)), "two parts share a point"

    keys = {s.key for s in placement.sheets}
    assert keys, "at least one sheet"
    for ref, key in placement.sheet_of.items():
        assert key in keys, "%s is on unknown sheet %r" % (ref, key)

    placed = sum(len(placement.refs_on(s.key)) for s in placement.sheets)
    assert placed == len(design.parts), "parts must not be lost or duplicated across sheets"


def test_grid_placer_holds_the_invariants(design):
    check_placement_invariants(design, GridPlacer().place(design))


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
