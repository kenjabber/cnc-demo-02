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
# Taller than the grid placer's pitch: real symbols are bigger than the old
# featureless boxes, and J1's 15-pin strip is 35.6 mm on its own.
SHEET_ROW_H = 38.1
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
        # sheet key -> the scan-pixel to millimetre mapping used for that sheet,
        # so transcribed wire runs can be placed in the same frame as the parts.
        self.scan_transform = {}

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

    drawn_extents = False

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

    Order within a sheet comes from :meth:`order`; this base class uses refdes
    order, which is why the pages read as a parts bin even once they are the
    right size.
    """

    serpentine = False
    #: Size the variable-size symbols to how big the drawing makes them.
    drawn_extents = False

    def order(self, design, refs, sheet_key):
        """Return ``refs`` in the order they should fill the grid.

        May contain ``None``, which leaves a grid cell empty.
        """
        return sorted(refs, key=natural_key)

    def place(self, design):
        placement = Placement()
        assignment = sheet_assignment(design)
        frame = (0.0, 0.0, FRAME_W, FRAME_H, FRAME_COLS, FRAME_ROWS)

        for key in sheet_keys_in_order(assignment):
            title = SECTION_TITLE.get(key, key)
            sheet = placement.add_sheet(key, title, frame)
            sheet.text(SHEET_X0 - 12.7, TITLE_Y, "%s  --  %s" % (key, title), 3.048, 97)

            refs = [r for r, k in assignment.items() if k == key]
            for i, ref in enumerate(self.order(design, refs, key)):
                if ref is None:          # padding that keeps a chain on one row
                    continue
                col, row = i % SHEET_PER_ROW, i // SHEET_PER_ROW
                if self.serpentine and row % 2:
                    # Rows alternate direction, so a chain that wraps continues
                    # directly below where it left off instead of jumping the
                    # full width of the sheet back to the left margin.
                    col = SHEET_PER_ROW - 1 - col
                placement.put(ref,
                              SHEET_X0 + col * COL_W,
                              SHEET_Y0 - row * SHEET_ROW_H,
                              key)
        return placement


# --- connectivity-driven ordering ------------------------------------------
# Nets bigger than this are buses, not evidence that two parts sit next to each
# other. N_CL reaches nine pins and N_SUM ten; treating those as adjacency
# would pull half a sheet into one blob.
MAX_ADJACENCY_NET = 6


def signal_graph(design, refs, supply_rails, max_pins=MAX_ADJACENCY_NET):
    """Undirected adjacency between parts on one sheet.

    Power and ground are excluded — everything touches them, so they say
    nothing about who should sit beside whom.
    """
    on_sheet = set(refs)
    adjacency = {r: set() for r in refs}
    for name, pins in design.nets.items():
        if name in supply_rails or len(pins) > max_pins:
            continue
        members = sorted({r for r, _ in pins if r in on_sheet}, key=natural_key)
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                adjacency[a].add(b)
                adjacency[b].add(a)
    return adjacency


def _chain_order(adjacency, component):
    """Walk a component as a chain, starting from its most upstream end.

    Greedy: always step to the unvisited neighbour with the fewest unvisited
    neighbours of its own, which follows a chain to its end rather than
    wandering into the middle of it.
    """
    degree = {r: len(adjacency[r]) for r in component}
    ends = [r for r in component if degree[r] <= 1] or list(component)
    start = min(ends, key=natural_key)

    ordered, seen = [], set()
    stack = [start]
    while stack:
        ref = stack.pop()
        if ref in seen:
            continue
        seen.add(ref)
        ordered.append(ref)
        nxt = sorted((n for n in adjacency[ref] if n not in seen),
                     key=lambda r: (len([m for m in adjacency[r] if m not in seen]),
                                    natural_key(r)))
        stack.extend(reversed(nxt))
    return ordered


def components(adjacency):
    """Connected components, each chain-ordered. Biggest first, then by name."""
    seen, found = set(), []
    for ref in sorted(adjacency, key=natural_key):
        if ref in seen:
            continue
        stack, group = [ref], []
        while stack:
            r = stack.pop()
            if r in seen:
                continue
            seen.add(r)
            group.append(r)
            stack.extend(sorted(adjacency[r] - seen, key=natural_key))
        found.append(_chain_order(adjacency, set(group)))
    found.sort(key=lambda g: (-len(g), natural_key(g[0])))
    return found


class ClusterPlacer(SheetPlacer):
    """Order each sheet by its signal chains rather than by refdes.

    An op-amp and its feedback resistor end up side by side instead of rows
    apart, which is what lets the router draw a short wire instead of a long
    trunk. Placement and routing are one decision, not two.

    A chain is never split across a row break unless it is longer than the row,
    and rows run alternately left-to-right and right-to-left so a chain that
    does wrap continues directly below itself.
    """

    serpentine = True

    def __init__(self, supply_rails=frozenset()):
        self.supply_rails = frozenset(supply_rails)

    def order(self, design, refs, sheet_key):
        adjacency = signal_graph(design, refs, self.supply_rails)
        ordered, row_used = [], 0
        for group in components(adjacency):
            if (row_used and len(group) <= SHEET_PER_ROW
                    and row_used + len(group) > SHEET_PER_ROW):
                ordered.extend([None] * (SHEET_PER_ROW - row_used))   # pad the row
                row_used = 0
            ordered.extend(group)
            row_used = (row_used + len(group)) % SHEET_PER_ROW
        return ordered


# --- placement from the scan ------------------------------------------------
GRID = 2.54
SCAN_AREA = (SHEET_X0, 76.2, SHEET_X0 + (SHEET_PER_ROW - 1) * COL_W, SHEET_Y0)


def _snap(value):
    return round(value / GRID) * GRID


def fit_box(points, area, scale=None):
    """Map scan pixels into a sheet area, preserving aspect ratio.

    Scaling the axes independently would stretch the block and misrepresent
    the drawing, so the tighter of the two scales wins and the result is
    centred in the leftover space.

    Pass ``scale`` to fix the millimetres per scan pixel instead of fitting.
    That matters because pin offsets are derived from the same pixels at a
    fixed scale: if the two disagree, every pin sits a fraction of a
    millimetre off the wire drawn to it and the difference shows as a step.
    """
    x1, y1, x2, y2 = area
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    if scale is None:
        scale = min((x2 - x1) / span_x if span_x else float("inf"),
                    (y2 - y1) / span_y if span_y else float("inf"))
    if scale == float("inf"):
        scale = 1.0
    pad_x = ((x2 - x1) - span_x * scale) / 2.0
    pad_y = ((y2 - y1) - span_y * scale) / 2.0

    def convert(px, py):
        # Scan y increases downward; sheet y increases upward.
        return (x1 + pad_x + (px - min(xs)) * scale,
                y2 - pad_y - (py - min(ys)) * scale)
    return convert


class ScanPlacer(SheetPlacer):
    """Place parts where they sit on the original drawing, where that is known.

    Coverage is deliberately partial. A part with no scan position is placed by
    the wrapped strategy in rows beneath the mapped block, so coordinates can be
    transcribed one section at a time and the build never breaks in between —
    which is what makes a 263-part transcription tractable at all.

    Within-sheet fidelity is the goal. The relationships *between* blocks, and
    the long horizontal buses, cannot survive the split into nine sheets; the
    scan is still the reference for those.
    """

    drawn_extents = True

    def __init__(self, positions=None, fallback=None, area=SCAN_AREA):
        from .sections import POSITIONS

        self.positions = POSITIONS if positions is None else positions
        self.fallback = fallback or SheetPlacer()
        self.area = area

    def place(self, design):
        # Lay the wrapped strategy out first. A sheet with no usable scan data
        # then reuses its result verbatim, so "no coordinates yet" is exactly
        # the previous behaviour rather than an approximation of it.
        auto = self.fallback.place(design)

        placement = Placement()
        assignment = sheet_assignment(design)
        frame = (0.0, 0.0, FRAME_W, FRAME_H, FRAME_COLS, FRAME_ROWS)

        for key in sheet_keys_in_order(assignment):
            title = SECTION_TITLE.get(key, key)
            sheet = placement.add_sheet(key, title, frame)
            sheet.text(SHEET_X0 - 12.7, TITLE_Y, "%s  --  %s" % (key, title), 3.048, 97)

            refs = [r for r, k in assignment.items() if k == key]
            known = sorted((r for r in refs if r in self.positions), key=natural_key)

            if len(known) < 2:
                # One point defines no arrangement; do not pretend otherwise.
                for ref in auto.refs_on(key):
                    x, y = auto.coords[ref]
                    placement.put(ref, x, y, key, auto.rot.get(ref, "R0"))
                continue

            taken = set()
            from .sections import SCAN

            convert = fit_box([self.positions[r][:2] for r in known], self.area,
                              scale=SCAN.get("mm_per_px"))
            placement.scan_transform[key] = convert
            for ref in known:
                entry = self.positions[ref]
                # Deliberately not snapped to the grid. A pin's position is
                # derived from the same pixels as the wire drawn to it, so any
                # rounding here reappears as a step in every wire.
                x, y = convert(entry[0], entry[1])
                x, y = self._free(x, y, taken)
                placement.put(ref, x, y, key, entry[2] if len(entry) > 2 else "R0")

            self._centre_two_pin_parts(design, placement, known, convert)
            self._align_two_pin_parts(design, placement, known)

            unknown = [r for r in auto.refs_on(key) if r not in self.positions]
            if unknown:
                sheet.text(SHEET_X0 - 12.7, 60.96,
                           "below: no scan position yet, auto-placed", 2.54, 97)
            for i, ref in enumerate(unknown):
                col, row = i % SHEET_PER_ROW, i // SHEET_PER_ROW
                x, y = self._free(SHEET_X0 + col * COL_W, 50.8 - row * SHEET_ROW_H, taken)
                placement.put(ref, x, y, key)
        return placement

    #: Where a two-terminal symbol's pins sit, before rotation.
    TWO_PIN_SPAN = 7.62

    def _align_two_pin_parts(self, design, placement, known):
        """Slide a series part onto the wire end the drawing gives it.

        With one end traced -- R104's top, its other end going to ground --
        the part is shifted so that pin lands exactly on the traced point.
        Being 4 mm out put R104 hard up against the op-amp.
        """
        from .model import derive_pin_offsets
        from .route import rotate_offset

        offsets = derive_pin_offsets()
        for ref in known:
            part = design.parts[ref]
            if len(part["pins"]) != 2 or ref not in offsets:
                continue
            traced = offsets[ref]
            if len(traced) != 1:
                continue          # both ends traced: centring handles it
            (pin, target), = traced.items()
            span = -self.TWO_PIN_SPAN if pin == part["pins"][0] else self.TWO_PIN_SPAN
            ours = rotate_offset(span, 0.0, placement.rot.get(ref, "R0"))
            x, y = placement.coords[ref]
            placement.coords[ref] = (x + target[0] - ours[0],
                                     y + target[1] - ours[1])

    def _centre_two_pin_parts(self, design, placement, known, convert):
        """Sit a series part midway between the two pins it joins.

        The drawing's own spacing is uneven, and a fixed-size symbol in a gap
        that is not its own width exaggerates it -- R73 ended up hard against
        PWM with three times the clearance on the LOCK-OUT side.
        """
        from .model import derive_pin_offsets

        offsets = derive_pin_offsets()
        placed = set(known)

        def pin_x(ref, pin):
            entry = self.positions.get(ref)
            if entry is None or ref not in offsets or pin not in offsets[ref]:
                return None
            return convert(entry[0], entry[1])[0] + offsets[ref][pin][0]

        for ref in known:
            part = design.parts[ref]
            if len(part["pins"]) != 2 or placement.rot.get(ref, "R0") != "R0":
                continue
            neighbours = []
            for name, pins in design.nets.items():
                mine = [p for p in pins if p[0] == ref]
                others = [p for p in pins if p[0] != ref and p[0] in placed]
                if len(mine) == 1 and len(others) == 1:
                    x = pin_x(*others[0])
                    if x is not None:
                        neighbours.append(x)
            if len(neighbours) == 2:
                _, y = placement.coords[ref]
                placement.coords[ref] = (sum(neighbours) / 2.0, y)

    @staticmethod
    def _free(x, y, taken):
        """Nudge onto the nearest free grid point. Scan positions collide."""
        step = 0
        while (round(x, 3), round(y, 3)) in taken:
            step += 1
            x, y = x + GRID * (step % 3), y - GRID * ((step + 1) % 3)
        taken.add((round(x, 3), round(y, 3)))
        return x, y
