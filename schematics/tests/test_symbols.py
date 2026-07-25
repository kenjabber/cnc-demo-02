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


def test_transistor_keeps_the_declared_pin_names():
    pins, _ = make_symbol("NPN", ["B", "C", "E"])
    assert pin_names(pins) == ["B", "C", "E"]
    assert len(pins) == 3


def test_pot_has_a_wiper_on_top():
    pins, _ = make_symbol("POT", ["1", "2", "3"])
    assert pin_names(pins) == ["1", "2", "3"]
    assert pins[1][3] == "R270", "the wiper should point up"


def test_generic_symbol_alternates_sides_and_grows():
    pins, _ = make_symbol("IC", [str(i) for i in range(1, 9)])
    assert pin_names(pins) == [str(i) for i in range(1, 9)]
    left = [p for i, p in enumerate(pins) if i % 2 == 0]
    right = [p for i, p in enumerate(pins) if i % 2 == 1]
    assert all(p[1] < 0 for p in left)
    assert all(p[1] > 0 for p in right)

    small, _ = make_symbol("IC", ["1", "2"])
    assert len(small) == 2


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
