# CNC Demo 2

CNC demonstration configs and G-code, plus a generator that rebuilds the Servo
Dynamics SD1015 / SD1525 drive schematic from transcribed source data.

## Layout

```
schematics/           the schematic generator — see its own README
  src/sd_schematic/     the package
  tests/                pytest suite
  test-data/            golden fixture the suite checks against
  output/               generated .sch and netlist
docs/                 source PDFs and photos
configs/, nc_files/   CNC configuration files and G-code
```

## Getting started

Open this folder in VS Code, then run the **Set up venv** task (or the command
below), pick `.venv/bin/python` as the interpreter, and press **F5** to run
*Schematic: build + validate*. Tests show up in the Testing panel;
`Cmd+Shift+B` runs the generator as the default build task.

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -e './schematics[test]'
```

From a shell:

```bash
.venv/bin/python -m sd_schematic
```

That writes `schematics/output/SD1015_SD1525_sheet2.sch` and
`schematics/output/netlist.csv`, then structurally validates the result.
`build` and `validate` run either half on its own, and `-o DIR` sends the output
somewhere else.

## Tests

```bash
.venv/bin/python -m pytest schematics
```

The suite guards the transcribed data's shape, the net merge, the symbol
library, the emitted XML, and the structural checker. Output is byte-for-byte
reproducible, and a test enforces that.

## The schematic

See [schematics/README.md](schematics/README.md) for what the drawing is, how
far to trust it, and which junctions still want a meter check.
