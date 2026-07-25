"""Where each part sits, and on which sheet.

Placement is deliberately separate from the electrical model: the same
:class:`~sd_schematic.model.Design` can be laid out by different strategies
without the netlist changing. That separation is what lets scan coordinates
arrive later as one more strategy rather than a rewrite.

A strategy is anything with ``place(design) -> Placement``.
"""

from .model import natural_key

# Section layout order and titles.
SECTION_ORDER = ["S1_input", "S4_comp", "S2_avamp", "S3_basedrive", "S7_moddemod",
                 "S5_supply", "S6_fault", "S8_pwmdrv", "S9_output", "extra"]
SECTION_TITLE = {
    "S1_input":     "INPUT / DIFF AMPLIFIER / SIG-AUX-TACH POTS",
    "S4_comp":      "COMPENSATION, CLAMP, CURRENT LIMIT, BALANCE",
    "S2_avamp":     "A.V. AMPLIFIER / RMS TIMER",
    "S3_basedrive": "J1 LOGIC INPUTS / U4 DRIVE",
    "S7_moddemod":  "TEMP SENSE, RESET LATCH, T1/T2 MOD-DEMOD",
    "S5_supply":    "BUS & +/-15 V SENSE, OVER-VOLT / SURGE DETECT",
    "S6_fault":     "U6/U5 FAULT LOGIC & LED ASSY",
    "S8_pwmdrv":    "PWM / CLOCK / LOCK-OUT / DRIVERS",
    "S9_output":    "OUTPUT H-BRIDGE, D78, J5, GROUND-FAULT SENSE",
    "extra":        "MISC",
}

COL_W, ROW_H, PER_ROW = 43.18, 33.02, 12

MAIN_SHEET = "main"

# --- one sheet per section -------------------------------------------------
# A3 landscape, the EAGLE stock frame size. Eight columns of parts fit inside
# it at the 43.18 mm pitch; twelve did not, which is why the single sheet grew
# to half a metre wide.
FRAME_W, FRAME_H = 387.35, 271.78
FRAME_COLS, FRAME_ROWS = 8, 5
SHEET_PER_ROW = 8
# Inset far enough that a left-hand pin stub (12.7 mm) and the rail symbol that
# may terminate it clear the frame border and its column labels.
SHEET_X0, SHEET_Y0 = 33.02, 236.22
TITLE_Y = 252.0
SHEET_MARGIN = 12.7

# Parts whose pins reach into a section other than the one that declared them.
# Without an override a part lands on the sheet of whichever section happened
# to declare it first, which is not always where it belongs.
SHEET_OF = {
    # R35B is the drawing's second "R35" -- the current-limit pot return. It
    # belongs beside R31 in the compensation block, not in a MISC drawer.
    "R35B": "S4_comp",
}


def sheet_assignment(design):
    """refdes -> sheet key. Section membership, with :data:`SHEET_OF` on top."""
    return {ref: SHEET_OF.get(ref, p["section"]) for ref, p in design.parts.items()}


def sheet_keys_in_order(assignment):
    """Sheet keys in :data:`SECTION_ORDER`, then anything unexpected."""
    used = set(assignment.values())
    keys = [k for k in SECTION_ORDER if k in used]
    return keys + sorted(used - set(keys))


class Sheet:
    """One drawn page: a key, a title, free text, and an optional frame.

    ``frame`` is ``(x1, y1, x2, y2, columns, rows)``. It matters for more than
    decoration: the document sets ``xreflabel="%F%N/%S.%C%R"``, so without a
    frame there are no column/row references and a cross-reference label has
    nothing to point at.
    """

    def __init__(self, key, title="", frame=None):
        self.key = key
        self.title = title
        self.frame = frame
        self.texts = []          # (x, y, string, size, layer)

    def text(self, x, y, s, size, layer):
        self.texts.append((x, y, s, size, layer))


class Placement:
    """The result of a placement strategy.

    Attributes
    ----------
    coords : dict
        refdes -> ``(x, y)`` in millimetres.
    rot : dict
        refdes -> EAGLE rotation string. Everything is ``R0`` today.
    sheet_of : dict
        refdes -> sheet key.
    sheets : list of :class:`Sheet`
        In drawing order. Every value of ``sheet_of`` names one of these.
    """

    def __init__(self):
        self.coords = {}
        self.rot = {}
        self.sheet_of = {}
        self.sheets = []

    def add_sheet(self, key, title="", frame=None):
        sheet = Sheet(key, title, frame)
        self.sheets.append(sheet)
        return sheet

    def put(self, ref, x, y, sheet_key, rot="R0"):
        self.coords[ref] = (x, y)
        self.rot[ref] = rot
        self.sheet_of[ref] = sheet_key

    def refs_on(self, sheet_key):
        """Refdes placed on one sheet, in placement order."""
        return [r for r in self.coords if self.sheet_of[r] == sheet_key]


class GridPlacer:
    """One horizontal band per functional section, parts sorted by refdes.

    The original strategy. Electrical adjacency has no influence on position,
    which is why the output reads as a parts bin rather than a schematic — but
    it is deterministic and it stays as the baseline other strategies are
    diffed against.
    """

    def place(self, design):
        placement = Placement()
        sheet = placement.add_sheet(MAIN_SHEET)

        y_cursor = 0.0
        for sname in SECTION_ORDER:
            refs = [r for r, p in design.parts.items() if p["section"] == sname]
            if not refs:
                continue
            refs.sort(key=natural_key)
            sheet.text(0, y_cursor + 12.7,
                       "%s  --  %s" % (sname, SECTION_TITLE[sname]), 3.048, 97)
            for i, ref in enumerate(refs):
                col, row = i % PER_ROW, i // PER_ROW
                placement.put(ref, col * COL_W, y_cursor - row * ROW_H, MAIN_SHEET)
            y_cursor -= ((len(refs) + PER_ROW - 1) // PER_ROW) * ROW_H + 25.4

        return placement


class SheetPlacer:
    """One A3 sheet per functional section, parts on a grid within it.

    The arrangement inside a sheet is still refdes order — that is Phase 3's
    job. What this buys on its own is that 263 parts stop sharing one half-metre
    page, and that each sheet gets a frame so cross-references resolve.
    """

    def place(self, design):
        placement = Placement()
        assignment = sheet_assignment(design)
        frame = (0.0, 0.0, FRAME_W, FRAME_H, FRAME_COLS, FRAME_ROWS)

        for key in sheet_keys_in_order(assignment):
            title = SECTION_TITLE.get(key, key)
            sheet = placement.add_sheet(key, title, frame)
            sheet.text(SHEET_X0 - 12.7, TITLE_Y, "%s  --  %s" % (key, title), 3.048, 97)

            refs = sorted((r for r, k in assignment.items() if k == key), key=natural_key)
            for i, ref in enumerate(refs):
                col, row = i % SHEET_PER_ROW, i // SHEET_PER_ROW
                placement.put(ref,
                              SHEET_X0 + col * COL_W,
                              SHEET_Y0 - row * ROW_H,
                              key)
        return placement
