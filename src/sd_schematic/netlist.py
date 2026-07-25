"""Flat netlist export, for cross-checking the schematic against the scan."""

import csv
import io

HEADER = ["net", "pins", "connections"]


def rows(design):
    """Nets biggest-first; ties keep the order they were transcribed in."""
    ordered = sorted(design.nets.items(), key=lambda kv: -len(kv[1]))
    return [[name, len(pins), " ".join(sorted("%s.%s" % p for p in pins))]
            for name, pins in ordered]


def render(design):
    """Return the netlist as a CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows(design))
    return buf.getvalue()
