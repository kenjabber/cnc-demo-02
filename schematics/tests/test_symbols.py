"""Symbol geometry and library sharing."""

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
