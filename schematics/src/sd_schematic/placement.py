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


class Sheet:
    """One drawn page: a key, a title, and free text drawn on it."""

    def __init__(self, key, title=""):
        self.key = key
        self.title = title
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

    def add_sheet(self, key, title=""):
        sheet = Sheet(key, title)
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
