"""Command line entry point: ``python -m sd_schematic``."""

import argparse
import sys
from pathlib import Path

from . import netlist as netlist_mod
from .eagle import SUPPLY_RAILS
from .eagle import render as render_sch
from .model import build_design
from .placement import ClusterPlacer, GridPlacer, SheetPlacer
from .route import StubRouter
from .sections import SECTIONS
from .validate import validate_file, validate_string

SCH_NAME = "SD1015_SD1525_sheet2.sch"
NETLIST_NAME = "netlist.csv"

# This file is schematics/src/sd_schematic/cli.py, so parents[2] is schematics/.
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "output"


PLACERS = {
    "chains": lambda: ClusterPlacer(supply_rails=SUPPLY_RAILS),
    "sheets": SheetPlacer,
    "grid": GridPlacer,
}


def _routers(placement_style):
    """The grid baseline keeps the original all-labels routing."""
    if placement_style == "grid":
        return StubRouter()
    return StubRouter(supply_rails=SUPPLY_RAILS)


def build(out_dir, placement="chains"):
    """Generate the ``.sch`` and netlist. Returns the paths written."""
    design = build_design(SECTIONS)
    document, warnings = render_sch(design,
                                    placer=PLACERS[placement](),
                                    router=_routers(placement))

    for w in design.warnings + warnings:
        print("WARN", w, file=sys.stderr)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sch_path = out_dir / SCH_NAME
    netlist_path = out_dir / NETLIST_NAME
    sch_path.write_text(document)
    netlist_path.write_text(netlist_mod.render(design))

    print("parts    :", len(design.parts))
    print("nets     :", len(design.nets))
    print("pinrefs  :", design.pin_connections)
    print("wrote    :", sch_path, sch_path.stat().st_size, "bytes")
    print("wrote    :", netlist_path)
    return sch_path, netlist_path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sd_schematic", description=__doc__)
    parser.add_argument("command", nargs="?", default="all",
                        choices=["build", "validate", "all"],
                        help="build the .sch, validate an existing one, or both (default)")
    parser.add_argument("-o", "--out-dir", default=DEFAULT_OUT_DIR,
                        help="where the generated files go (default: %(default)s)")
    parser.add_argument("-p", "--placement", default="chains", choices=sorted(PLACERS),
                        help="chains: one A3 sheet per functional block, parts ordered "
                             "by signal chain. sheets: the same, ordered by refdes. "
                             "grid: the original single half-metre sheet with a label "
                             "on every pin (default: %(default)s)")
    args = parser.parse_args(argv)

    if args.command == "validate":
        report = validate_file(Path(args.out_dir) / SCH_NAME)
    else:
        sch_path, _ = build(args.out_dir, args.placement)
        if args.command == "build":
            return 0
        print()
        report = validate_string(sch_path.read_text())

    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
