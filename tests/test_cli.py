"""End to end: the command line writes files that validate."""

import csv

from sd_schematic.cli import NETLIST_NAME, SCH_NAME, main
from sd_schematic.validate import validate_file


def test_build_then_validate(tmp_path, capsys):
    assert main(["build", "-o", str(tmp_path)]) == 0
    sch = tmp_path / SCH_NAME
    assert sch.exists() and sch.stat().st_size > 100_000
    assert validate_file(sch).ok

    assert main(["validate", "-o", str(tmp_path)]) == 0
    assert "STRUCTURAL VALIDATION PASSED" in capsys.readouterr().out


def test_default_command_builds_and_validates(tmp_path, capsys):
    assert main(["-o", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "wrote" in out
    assert "STRUCTURAL VALIDATION PASSED" in out


def test_creates_a_missing_output_directory(tmp_path):
    out = tmp_path / "new" / "nested"
    assert main(["build", "-o", str(out)]) == 0
    assert (out / SCH_NAME).exists()


def test_netlist_is_lf_terminated_and_sorted_by_size(tmp_path):
    main(["build", "-o", str(tmp_path)])
    raw = (tmp_path / NETLIST_NAME).read_bytes()
    assert b"\r\n" not in raw, "CRLF makes for noisy diffs"

    rows = list(csv.reader((tmp_path / NETLIST_NAME).read_text().splitlines()))
    assert rows[0] == ["net", "pins", "connections"]
    counts = [int(r[1]) for r in rows[1:]]
    assert counts == sorted(counts, reverse=True)
    assert rows[1][0] == "GND", "ground should be the biggest node on the sheet"

    for _, pins, conns in rows[1:]:
        assert len(conns.split()) == int(pins)


def test_netlist_agrees_with_the_schematic(tmp_path):
    main(["build", "-o", str(tmp_path)])
    rows = list(csv.reader((tmp_path / NETLIST_NAME).read_text().splitlines()))[1:]
    assert sum(int(r[1]) for r in rows) == validate_file(
        tmp_path / SCH_NAME).counts["pin connects"]
