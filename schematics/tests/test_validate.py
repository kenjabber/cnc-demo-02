"""The structural checker, and that the generated sheet passes it."""

from sd_schematic.validate import validate_file, validate_string

# The seven wires that run off into the long cross-sheet buses and could not be
# traced to a terminal with confidence. They are left unconnected rather than
# guessed; see schematics/README_SD1525_schematic.md.
KNOWN_DANGLING = {"D12A.2", "D43.1", "R123.2", "R69.1", "R90.1", "R94.1", "U4D.7"}


def test_generated_sheet_passes(sch):
    report = validate_string(sch)
    assert report.ok, "\n".join(report.errors)


def test_counts_match_the_design(sch, design):
    report = validate_string(sch)
    assert report.counts["parts"] == len(design.parts)
    assert report.counts["nets"] == len(design.nets)
    assert report.counts["pin connects"] == design.pin_connections
    assert report.counts["symbols"] == report.counts["devicesets"]


def test_dangling_pins_are_exactly_the_known_ones(sch):
    report = validate_string(sch)
    assert set(report.dangling) == KNOWN_DANGLING


def test_summary_is_printable(sch):
    text = validate_string(sch).summary()
    assert "STRUCTURAL VALIDATION PASSED" in text
    assert "parts" in text


def test_wire_off_its_pin_is_caught(sch):
    """Nudge one net wire 1 mm and the geometry check must notice."""
    marker = '<wire x1="'
    i = sch.index(marker, sch.index("<nets>"))
    j = sch.index('"', i + len(marker))
    x = float(sch[i + len(marker):j])
    broken = sch[:i + len(marker)] + ("%.3f" % (x + 1.0)) + sch[j:]

    report = validate_string(broken)
    assert not report.ok
    assert any("no wire end at" in e for e in report.errors)


def test_missing_deviceset_is_caught(sch):
    broken = sch.replace('deviceset="DS_R_1"', 'deviceset="DS_NOPE"', 1)
    report = validate_string(broken)
    assert not report.ok
    assert any("missing deviceset" in e for e in report.errors)


def test_non_eagle_root_is_rejected():
    report = validate_string("<notEagle/>")
    assert not report.ok
    assert "expected <eagle>" in report.errors[0]


def test_validate_file_reads_from_disk(sch, tmp_path):
    path = tmp_path / "sheet.sch"
    path.write_text(sch)
    assert validate_file(path).ok
