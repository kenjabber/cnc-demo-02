# SD1015 / SD1525 sheet 2 — Fusion Electronics schematic

Converted from **ServoDynamics_1525.pdf page 30**, Servo Dynamics drawing **1202 rev A,
sheet 2 of 2**, "SIMPLIFIED SCHEMATIC", drawn by Tong Tran 12-85.

See the [repo README](../README.md) for setup; everything below assumes the venv
is installed.

| file | what it is |
|---|---|
| `output/SD1015_SD1525_sheet2.sch` | EAGLE-XML schematic — open directly in Fusion Electronics |
| `output/netlist.csv` | flat netlist (net name, pin count, connections) for cross-checking |
| `src/sd_schematic/sections.py` | the transcribed source data, with audit notes inline |
| `src/sd_schematic/model.py` | merges the nine sections into one part and net list |
| `src/sd_schematic/eagle.py` | emits the `.sch` |
| `src/sd_schematic/validate.py` | structural checker (run after any edit) |
| `test-data/expected_netlist.csv` | golden netlist the suite checks the merge against |

**263 parts · 166 nets · 627 pin connections.**

## Opening it

In Fusion: *File → Open → From my computer*, pick the `.sch`. Or drop it in your
Fusion Electronics project. It carries its own embedded library (`sd1525`) so
nothing else needs installing.

## What you're getting, honestly

The source is a **1-bit 400 dpi scan** — no vector or text layer — so every
component and every wire was read visually. Nine overlapping sections were each
transcribed independently at high zoom, then merged, then audited against the
scan a second time. The audit found and corrected a real error (see below), which
is a fair indication that a small number of others may remain.

**Trust the local clusters; verify the long runs.** Component identity, and
connectivity within a functional block (op-amp feedback networks, the H-bridge,
the LED drivers, the diode clamp) are solid. The long horizontal buses that
sweep across the middle of the sheet are where any remaining errors will be.

### The layout is not the original

The sheet is split into **nine A3 pages, one per functional block**, each with a
frame so cross-reference labels resolve to a column/row. Ground and supply pins
carry **rail symbols**; other connections are still **net labels** rather than
routed wires. Same-named labels are electrically connected — standard EAGLE
practice, and Fusion honours it.

Within a page, parts are still ordered by reference designator rather than by
signal flow, so the pages are correct and browsable but do not look like the
1985 drawing. Keep the scan alongside it.

`--placement grid` regenerates the original single half-metre sheet with a label
on every pin, for comparison.

No component **values** are on the original — it's a simplified schematic showing
reference designators only. `>VALUE` therefore shows a note where there is one
and nothing otherwise; the part kind lives in the deviceset description.

### Pin roles

Which pin is a base and which is an output is recorded in `ROLES` in
`sections.py`, keyed by refdes. A pin already named `B`/`C`/`E` or `G`/`D`/`S`
supplies its own role and needs no entry, which leaves sixteen parts in the
table. There is deliberately **no positional fallback** — a part whose role
cannot be resolved warns rather than being guessed at, because guessing from
declaration order is what drew U1A's output on the left and put U4A's collector
in the base slot.

## Corrected during audit

### C8 — the −15 V rail was shorted to ground

`C8` was transcribed with its plates the other way round in `S1_input` than in
`S4_comp`. Because the merge is union-find over shared pins, those two readings
tied `N15` and `GND` into a single node: the −15 V rail vanished, and all 16 of
its pins — `U1B.4`, `U8B.4`, `U9A.4`, `J1.12`, `J4.3`, `D44.1`, the `R118`/`R119`
±15 V adjust divider — were reported as ground. `GND` was 84 pins because it had
swallowed a supply.

`S4_comp` is the correct reading. C8 is drawn with its "+" on the grounded plate,
which is right for a decoupler on a *negative* rail, and pin 1 is the "+" plate.
`S1_input` is corrected to match. `GND` is now 68 pins and `N15` exists.

`build_nets` now raises `ShortedRailsError` if any two names in `GLOBAL_ORDER`
ever merge again, because the failure mode is silent — the smaller rail just
disappears.

### The ECC node

My first merge tied ten points together as one "ECC" node. Re-tracing at high
zoom showed the vertical carrying TP7 (x≈1803) *crosses* the U9 pin-7 output run
(y≈1722) with no junction dot. The node is now split correctly:

- `N_ECC` — U9 pin 7, R41 (F.E.T. clamp gate), D36 anode
- `N_TP7` — TP7, R95
- `N_MODIN` — C43, T1 pin 1
- `N_R64A_R80A_TOP` — R64A/R80A tops only
- R94 is on its own third vertical

## Duplicate reference designators (in the original drawing)

The 1985 drawing prints some designators twice. Suffixed here so they stay distinct:

| in this file | printed on drawing | where |
|---|---|---|
| `R59` / `R59B` | both "R59" | jumper X / R57–R58 divider |
| `R60` / `R60B` | both "R60" | jumper Y / balance-pot series element |
| `R35` / `R35B` | both "R35" | tach network (Rt) / current-limit pot return |
| `R137` | "R137" | +15 V decoupling at the driver centre tap — **not** R157; R157 is the series element in the J5 pin 10/11 motor lead |
| `D78A`–`D78D` | "D78" | the four legs of the bridge |
| `RGF`, `FGF` | *(none)* | the 10 Ω 12 W chassis resistor and fuse for ground-fault detection |

## Unresolved — 7 dangling pins

These wires run off into the long cross-sheet buses and could not be traced to a
terminal with confidence. They are left unconnected rather than guessed:

`D12A.2` · `D43.1` · `R123.2` · `R69.1` · `R90.1` · `R94.1` · `U4D.7`

## Junctions worth your own eyes

1. **Ground symbol near R151 / SURGE DETECTOR** (sheet ≈4932, 1581–1645). Its stem
   dead-ends in mid-air above the wiper wire and crosses it with no dot. Read
   literally that's *no connection*, which is almost certainly a drafting slip.
   Left disconnected. This is the single most suspect junction on the sheet.
2. **R156 in series in the +DC bus** — so J5 pins 1/2 are *not* the same node as the
   Q9/Q14 collectors. Verified twice, but unusual enough to be worth a meter check.
3. **R157 in series in the motor lead** — same situation on the J5 pin 10/11 side.
4. **U4 sections** are drawn as bare transistor symbols with IC pin numbers. The
   emitter arrowheads on sections A and C are blotted; all four are assumed NPN by
   symmetry with sections B and D, where the arrows are legible.
5. **D9, D10, D11, D12A, D44** are drawn with hooked cathode bars (zener style)
   where D1/D2/D3 etc. have straight bars. Typed as zeners on that basis.
6. **U7** behaves as a hex inverter/buffer (13→12, 11→10, 5→6, 3→4, V+ on 14,
   ground on 7), not a quad comparator.
7. **C8 polarity** is drawn with its "+" on the grounded plate — recorded as drawn.

## Regenerating

```bash
.venv/bin/python -m sd_schematic
```

Edit `src/sd_schematic/sections.py` to fix any connection you find wrong; the
generator and the structural checker will pick it up. Validation verifies that
every net wire lands exactly on its pin, every pin belongs to exactly one net,
and every part resolves to a symbol.

Then run the tests:

```bash
.venv/bin/python -m pytest schematics
```

Several of them pin the totals (263 parts, 166 nets, 627 pin connections) and
the seven known dangling pins, and `test_regression.py` diffs the whole netlist
against `test-data/expected_netlist.csv`. A deliberate change to `sections.py`
means updating those expectations in the same commit, so the change to the
circuit is visible in review:

```bash
.venv/bin/python -m sd_schematic build
cp schematics/output/netlist.csv schematics/test-data/expected_netlist.csv
```

The output is reproducible: the same `sections.py` always produces the same
bytes, so a diff on the `.sch` shows only what you actually changed.
