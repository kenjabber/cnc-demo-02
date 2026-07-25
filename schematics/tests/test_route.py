"""Routing strategies and the segment IR."""

import pytest

from sd_schematic.placement import GridPlacer
from sd_schematic.route import StubRouter, pin_geometry
from sd_schematic.symbols import build_symbol_library


def route_design(design):
    placement = GridPlacer().place(design)
    _, sym_of = build_symbol_library(design.parts)
    routed, warnings = StubRouter().route(design, placement, sym_of)
    return placement, routed, warnings


def test_pin_geometry_places_the_stub_off_the_pin():
    symbol = {"pins": [("1", -7.62, 0.0, "R0"), ("2", 7.62, 0.0, "R180")]}
    assert pin_geometry(symbol, (0.0, 0.0), "1") == pytest.approx((-7.62, 0.0, -12.7, 0.0))
    assert pin_geometry(symbol, (10.0, 5.0), "2") == pytest.approx((17.62, 5.0, 22.7, 5.0))
    assert pin_geometry(symbol, (0.0, 0.0), "99") is None


def test_stub_router_covers_every_pin_connection(design):
    _, routed, warnings = route_design(design)
    assert warnings == []
    assert set(routed) == set(design.nets)
    total = sum(len(s.pinrefs) for segs in routed.values() for s in segs)
    assert total == design.pin_connections


def test_stub_router_emits_one_segment_per_pin(design):
    _, routed, _ = route_design(design)
    for name, segments in routed.items():
        for s in segments:
            assert len(s.pinrefs) == 1
            assert len(s.wires) == 1
            assert len(s.labels) == 1
            assert s.junctions == []


def test_every_stub_starts_on_its_pin(design):
    """The wire must begin exactly at the pin's connection point."""
    placement, routed, _ = route_design(design)
    _, sym_of = build_symbol_library(design.parts)
    for segments in routed.values():
        for s in segments:
            (ref, pin), = s.pinrefs
            px, py, _, _ = pin_geometry(sym_of[ref], placement.coords[ref], pin)
            x1, y1, _, _ = s.wires[0]
            assert (x1, y1) == pytest.approx((px, py))


def test_segments_are_assigned_to_a_real_sheet(design):
    placement, routed, _ = route_design(design)
    keys = {s.key for s in placement.sheets}
    for segments in routed.values():
        for s in segments:
            assert s.sheet in keys
