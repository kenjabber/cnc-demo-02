"""Symbol geometry and library sharing."""

import pytest


from sd_schematic.symbols import build_symbol_library, make_symbol, signature, symbol_xml


def pin_names(pins):
    return [p[0] for p in pins]


def test_two_pin_parts_share_horizontal_terminals():
    for kind in ("R", "C", "CPOL", "D", "ZENER", "LED"):
        pins, body = make_symbol(kind, ["1", "2"])
        assert pin_names(pins) == ["1", "2"]
        assert [p[3] for p in pins] == ["R0", "R180"]
        assert body


def test_polarised_capacitor_is_marked():
    _, plain = make_symbol("C", ["1", "2"])
    _, polarised = make_symbol("CPOL", ["1", "2"])
    assert "+" in "".join(polarised)
    assert "+" not in "".join(plain)


def test_transistor_terminals_go_where_their_role_says():
    """Base left, collector top, emitter bottom -- whatever the pins are called."""
    pins, _ = make_symbol("NPN", ["12", "13", "14"],
                          {"c": "12", "b": "13", "e": "14"})
    at = {p[0]: p for p in pins}
    assert at["13"][1] < 0, "base on the left"
    assert at["12"][2] > 0, "collector on top"
    assert at["14"][2] < 0, "emitter on the bottom"


def test_fet_gate_goes_where_its_role_says_not_where_it_sits():
    """Q7 is declared S, D, E but the pin called E is the gate."""
    pins, _ = make_symbol("NMOS", ["S", "D", "E"], {"s": "S", "d": "D", "g": "E"})
    at = {p[0]: p for p in pins}
    assert at["E"][1] < 0, "gate on the left"
    assert at["D"][2] > 0 and at["S"][2] < 0


def test_amplifier_output_is_on_the_right():
    pins, _ = make_symbol("OPAMP", ["1", "2", "3"],
                          {"out": "1", "in-": "2", "in+": "3"})
    at = {p[0]: p for p in pins}
    assert at["1"][1] > 0, "output on the right"
    assert at["2"][1] < 0 and at["3"][1] < 0, "both inputs on the left"


def test_amplifier_rails_are_drawn_when_known():
    pins, _ = make_symbol("OPAMP", ["4", "5", "6", "7", "8"],
                          {"v-": "4", "in+": "5", "in-": "6", "out": "7", "v+": "8"})
    at = {p[0]: p for p in pins}
    assert at["8"][2] > 0 and at["4"][2] < 0
    assert at["8"][4] == "pwr" and at["4"][4] == "pwr"


def test_pot_has_a_wiper_on_top():
    pins, _ = make_symbol("POT", ["1", "2", "3"])
    assert pin_names(pins) == ["1", "2", "3"]
    assert pins[1][3] == "R270", "the wiper should point up"


def test_generic_symbol_runs_pins_down_one_side():
    """Small ICs keep every pin on the left, in order.

    Alternating sides by index parity is what made U6 unreadable.
    """
    pins, _ = make_symbol("IC", [str(i) for i in range(1, 9)])
    assert pin_names(pins) == [str(i) for i in range(1, 9)]
    assert all(p[1] < 0 for p in pins)
    ys = [p[2] for p in pins]
    assert ys == sorted(ys, reverse=True), "pins descend in declaration order"

    small, _ = make_symbol("IC", ["1", "2"])
    assert len(small) == 2


def test_wide_ic_spills_to_the_right_half_way():
    pins, _ = make_symbol("IC", [str(i) for i in range(1, 17)])
    left = [p for p in pins if p[1] < 0]
    right = [p for p in pins if p[1] > 0]
    assert len(left) == 8 and len(right) == 8
    assert pin_names(left) == [str(i) for i in range(1, 9)]


def test_connector_is_a_pin_strip():
    """J1 has 15 pins; alternating them left and right made it unreadable."""
    pins, _ = make_symbol("CONN", [str(i) for i in range(1, 16)])
    assert all(p[1] < 0 for p in pins)
    assert pin_names(pins) == [str(i) for i in range(1, 16)]


def test_parts_with_the_same_signature_share_one_symbol():
    parts = {
        "R1": {"kind": "R", "pins": ["1", "2"], "section": "a"},
        "R2": {"kind": "R", "pins": ["1", "2"], "section": "a"},
        "U1": {"kind": "IC", "pins": ["1", "2", "3"], "section": "a"},
    }
    symbols, sym_of = build_symbol_library(parts)
    assert len(symbols) == 2
    assert sym_of["R1"] is sym_of["R2"]
    assert sym_of["U1"] is not sym_of["R1"]
    assert sym_of["R1"]["name"] == "R_1"


def test_signature_separates_different_pin_sets():
    a = {"kind": "IC", "pins": ["1", "2"]}
    b = {"kind": "IC", "pins": ["2", "1"]}
    assert signature(a) != signature(b)


def test_symbol_xml_carries_name_and_value_placeholders():
    symbols, _ = build_symbol_library({"R1": {"kind": "R", "pins": ["1", "2"], "section": "a"}})
    xml = symbol_xml(next(iter(symbols.values())))
    assert xml.startswith('<symbol name="R_1">')
    assert "&gt;NAME" in xml and "&gt;VALUE" in xml
    assert xml.count("<pin ") == 2


def test_real_design_reuses_symbols_heavily(design):
    symbols, _ = build_symbol_library(design.parts)
    assert len(symbols) < len(design.parts) / 4


def test_transformer_is_drawn_as_coupled_windings():
    """T3's primary is 1/2/3 with pin 2 the centre tap; 4-6 and 7-9 secondary."""
    windings = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
    pins, body = make_symbol("XFMR", [p for g in windings for p in g],
                             {"windings": windings})
    at = {p[0]: p for p in pins}
    assert all(at[p][1] < 0 for p in ("1", "2", "3")), "primary on the left"
    assert all(at[p][1] > 0 for p in ("4", "5", "6", "7", "8", "9")), "secondaries right"
    assert at["2"][2] == pytest.approx(0.0), "centre tap between its outer pins"
    assert at["1"][2] > at["2"][2] > at["3"][2], "pins run down the coil in order"
    assert at["6"][2] > at["7"][2], "the two secondaries do not overlap"
    assert 'curve=' in "".join(body), "coils, not straight lines"


def test_transformer_without_windings_still_draws():
    pins, _ = make_symbol("XFMR", ["1", "2"], {})
    assert len(pins) == 2


def test_named_block_puts_its_pins_by_direction():
    pins, _ = make_symbol("BLOCK", ["IN", "OUT"], {})
    at = {p[0]: p for p in pins}
    assert at["IN"][1] < 0 and at["IN"][4] == "in"
    assert at["OUT"][1] > 0 and at["OUT"][4] == "out"


def test_named_block_keeps_numbered_pins_on_the_left():
    pins, _ = make_symbol("BLOCK", ["1", "2", "3", "4"], {})
    assert all(p[1] < 0 for p in pins)
    assert pin_names(pins) == ["1", "2", "3", "4"]


def test_block_name_is_drawn_inside_the_box():
    """The original names these blocks rather than drawing them out."""
    from sd_schematic.symbols import symbol_xml

    block = {"name": "B_1", "kind": "BLOCK", "pins": [("1", -15.24, 0.0, "R0", "in")],
             "body": []}
    other = dict(block, kind="IC")
    assert '<text x="-10.160" y="-0.889"' in symbol_xml(block)
    assert '<text x="-5.080" y="9.000"' in symbol_xml(other)


def test_signature_survives_a_winding_map():
    """Role values may be nested lists; the symbol key must still hash."""
    a = {"kind": "XFMR", "pins": ["1", "2"], "roles": {"windings": [["1"], ["2"]]}}
    b = {"kind": "XFMR", "pins": ["1", "2"], "roles": {"windings": [["1", "2"]]}}
    assert signature(a) != signature(b)
    assert hash(signature(a))


def test_block_can_take_pins_out_of_the_top():
    """CLOCK's output leaves upward on the sheet.

    On the right, the traced run -- which heads straight up -- had to cut back
    through the box to reach its own pin.
    """
    pins, _ = make_symbol("BLOCK", ["1"], {"sides": {"top": ["1"]}})
    (pin,) = pins
    assert pin[2] > 0, "pin above the box"
    assert pin[3] == "R270", "stub runs upward"
    assert pin[4] == "out"


def test_block_bottom_and_top_are_spread_along_the_edge():
    pins, _ = make_symbol("BLOCK", ["1", "2", "3", "4"],
                          {"sides": {"left": ["1"], "right": ["2"],
                                     "bottom": ["3", "4"]}})
    at = {p[0]: p for p in pins}
    assert at["3"][2] < 0 and at["4"][2] < 0
    assert at["3"][0] != at["4"][0], "bottom pins must not stack on one point"
    assert at["3"][3] == "R90", "stub runs downward"


def test_clock_takes_its_output_off_the_top(design):
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    (pin,) = sym_of["CLOCK"]["pins"]
    assert pin[2] > 0 and pin[3] == "R270"


def test_transformer_windings_are_centred_on_the_core(design):
    """Both secondaries must sit against the core, not hang past its end."""
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    symbol = sym_of["T4"]
    right = [e for e in symbol["pins"] if e[1] > 0]
    left = [e for e in symbol["pins"] if e[1] < 0]
    assert len(right) == 6 and len(left) == 3

    # Symmetric about the core on both sides.
    for side in (right, left):
        ys = [e[2] for e in side]
        assert abs(max(ys) + min(ys)) < 1e-6, "winding stack is off-centre"

    # And the core is long enough to reach the outermost pin.
    reach = max(abs(e[2]) for e in symbol["pins"])
    core = [f for f in symbol["body"] if 'x1="-0.635"' in f]
    assert core, "no core drawn"
    ends = [float(v) for v in
            __import__("re").findall(r'y[12]="(-?[\d.]+)"', core[0])]
    assert max(ends) >= reach, "core stops short of the top winding"


def test_amplifier_inputs_are_inset_from_the_vertices(design):
    """Sized to just cover its pins, the triangle puts them on its corners.

    Anything joining an input then appears to hang off the corner of the
    symbol -- which is what R104 looked like.
    """
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    symbol = sym_of["U9A"]
    roles = design.parts["U9A"]["roles"]
    at = {e[0]: e for e in symbol["pins"]}

    corner = max(abs(float(v)) for frag in symbol["body"]
                 for v in __import__("re").findall(r'y[12]="(-?[\d.]+)"', frag))
    for role in ("in-", "in+"):
        assert abs(at[roles[role]][2]) < corner - 2.0, \
            "%s sits on the triangle's vertex" % role


def test_amplifier_rail_leads_reach_the_body(design):
    """A supply lead that stops beside the triangle is drawn floating."""
    import re

    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    symbol = sym_of["U9A"]
    roles = design.parts["U9A"]["roles"]
    at = {e[0]: e for e in symbol["pins"]}

    verticals = []
    for frag in symbol["body"]:
        for x1, y1, x2, y2 in re.findall(
                r'x1="(-?[\d.]+)" y1="(-?[\d.]+)" x2="(-?[\d.]+)" y2="(-?[\d.]+)"', frag):
            if abs(float(x1) - float(x2)) < 1e-6:
                verticals.append((float(x1), float(y1), float(y2)))

    for role in ("v+", "v-"):
        pin = at[roles[role]]
        assert any(abs(vx - pin[1]) < 1e-6 for vx, _, _ in verticals), \
            "%s has no lead at its own x" % role


def test_a_block_is_the_width_the_drawing_gives_it(design):
    """A 25.4 mm floor swallowed the DRIVER pins, which sit 6.8 mm out."""
    import re

    from sd_schematic.sections import EXTENTS, SCAN
    from sd_schematic.symbols import build_symbol_library

    _, sym_of = build_symbol_library(design.parts, drawn_extents=True)
    for ref in ("DRIVER1", "DRIVER2", "PWM", "LOCKOUT"):
        symbol = sym_of[ref]
        xs = [abs(float(v)) for frag in symbol["body"]
              for v in re.findall(r'x[12]="(-?[\d.]+)"', frag)]
        drawn = EXTENTS[ref][0] * SCAN["mm_per_px"] / 2
        # The drawn half-width, widened only if a pin would fall outside it.
        assert drawn - 0.05 <= max(xs) <= drawn + 1.0, \
            "%s: box half-width %.2f, drawn %.2f" % (ref, max(xs), drawn)
        for pin in symbol["pins"]:
            assert abs(pin[1]) <= max(xs) + 0.01, "%s.%s is outside its box" % (ref, pin[0])
