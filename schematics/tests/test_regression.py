"""Golden-file guard on the electrical content.

The rest of the suite checks the generator is internally consistent. This one
checks it still produces the *same circuit* as the transcription that was
audited against the scan -- so an accidental edit to sections.py, or a change
in how nets merge, shows up as a diff rather than passing quietly.

If you deliberately corrected a connection, regenerate the fixture:

    .venv/bin/python -m sd_schematic build
    cp schematics/output/netlist.csv schematics/test-data/expected_netlist.csv

and make the diff part of the same commit, so the change is reviewable.
"""

from pathlib import Path

from sd_schematic import netlist

EXPECTED = Path(__file__).resolve().parents[1] / "test-data" / "expected_netlist.csv"


def test_netlist_matches_the_audited_transcription(design):
    assert netlist.render(design) == EXPECTED.read_text()
