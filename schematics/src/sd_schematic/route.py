"""How a net gets drawn once its parts are placed.

A router turns one net into a list of :class:`Segment` — a small intermediate
representation the serializer renders verbatim. Keeping it separate from the
XML means routing geometry can be tested without parsing a document, and means
a different routing strategy is a swap rather than a rewrite.

A strategy is anything with ``route(design, placement, sym_of) -> (dict, list)``
mapping net name to segments, plus warnings.
"""

STUB = 5.08

# Which way a pin's stub runs, by pin rotation.
STUB_DIR = {"R0": (-1, 0), "R180": (1, 0), "R90": (0, -1), "R270": (0, 1)}

ROT_STEPS = {"R0": 0, "R90": 1, "R180": 2, "R270": 3}


def rotate_offset(dx, dy, rot):
    """Turn a pin offset by an instance rotation. EAGLE turns anticlockwise."""
    for _ in range(ROT_STEPS[rot]):
        dx, dy = -dy, dx
    return dx, dy


def rotate_pin(pin_rot, instance_rot):
    return "R%d" % (((ROT_STEPS[pin_rot] + ROT_STEPS[instance_rot]) % 4) * 90)


class Segment:
    """One connected piece of a net.

    A net with every pin on the same sheet is usually one segment; a net split
    across sheets has one per sheet. ``labels`` carries cross-reference labels;
    ``supplies`` carries ground/rail symbol placements.
    """

    def __init__(self, sheet, wires=(), pinrefs=(), junctions=(), labels=(), supplies=()):
        self.sheet = sheet
        self.wires = list(wires)          # (x1, y1, x2, y2)
        self.pinrefs = list(pinrefs)      # (refdes, pin)
        self.junctions = list(junctions)  # (x, y)
        self.labels = list(labels)        # (x, y, rot)
        self.supplies = list(supplies)    # (rail, x, y, rot)


def pin_geometry(symbol, origin, pin, rot="R0"):
    """Return ``(px, py, ex, ey)``: the pin's connection point and stub end.

    ``rot`` is the instance rotation, which moves the pin and turns its stub
    with it. Ignoring it would put every wire on a rotated part in the wrong
    place while still looking self-consistent.
    """
    for entry in symbol["pins"]:
        pn, dx, dy, pin_rot = entry[0], entry[1], entry[2], entry[3]
        if pn == pin:
            dx, dy = rotate_offset(dx, dy, rot)
            cx, cy = origin[0] + dx, origin[1] + dy
            sx, sy = STUB_DIR[rotate_pin(pin_rot, rot)]
            return cx, cy, cx + sx * STUB, cy + sy * STUB
    return None


class TrunkRouter:
    """Draw real wires: a horizontal trunk per net, with a drop to each pin.

    Nets are routed one sheet at a time. A net whose pins all sit in one row of
    the placement grid gets a trunk in the channel below that row; one spanning
    two neighbouring rows gets a trunk in the channel between them. Anything
    wider is declined and falls back to labels — a router that always succeeds
    is a router that draws nonsense.

    Trunk heights come from a left-edge channel assignment: nets in a channel
    are taken in order of their leftmost point and given the lowest track whose
    occupied span does not overlap. Two trunks therefore never lie on top of
    one another, which is the failure a reader cannot recover from. Crossings
    are fine and expected; overlaps are not.
    """

    #: Tracks available in one channel, as offsets below the upper row's centre.
    #: Deliberately odd multiples of 1.27 mm. Pin escapes always land on an even
    #: multiple, so a trunk can never come to rest along one and be mistaken for
    #: a connection to it.
    TRACKS = (-16.51, -19.05, -21.59)

    def __init__(self, supply_rails=frozenset(), row_height=38.1, col_width=43.18):
        self.supply_rails = frozenset(supply_rails)
        self.row_height = row_height
        self.col_width = col_width
        self.declined = []

    # -- geometry helpers --------------------------------------------------
    def _row_of(self, y):
        """Grid row index. Rows are evenly pitched, so rounding recovers it."""
        return round(-y / self.row_height)

    def _escapes(self, pins, placement, sym_of):
        """``[(ref, pin, px, py, ex, ey, vertical)]`` for one sheet's pins."""
        out = []
        for ref, pin in pins:
            geo = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                placement.rot.get(ref, "R0"))
            if geo is None:
                return None
            px, py, ex, ey = geo
            out.append((ref, pin, px, py, ex, ey, abs(ey - py) > abs(ex - px)))
        return out

    def _drop_x(self, escape, placement):
        """Where a pin's vertical drop runs.

        A pin escaping sideways drops straight from its escape point, which
        already sits in the gap between symbols. A pin escaping up or down has
        to jog clear of its own part first, or the drop would run through it.
        """
        ref, _, px, py, ex, ey, vertical = escape
        if not vertical:
            return ex
        # Jog towards the side the pin points, so a part's upward and downward
        # pins -- a transistor's collector and emitter, on different nets --
        # never claim the same drop line.
        side = 1.0 if ey > py else -1.0
        return placement.coords[ref][0] + side * self.col_width / 2.0

    # -- occupancy ---------------------------------------------------------
    # Two wires may cross; they may not lie along each other. An overlap reads
    # as a connection that is not in the netlist, and nothing downstream can
    # recover from it. Rather than trying to prove the geometry never produces
    # one, the router checks each net before committing it and declines the net
    # if it would. A few more labels is a cheap price for the guarantee.
    @staticmethod
    def _spans(segment):
        horizontal, vertical = [], []
        for x1, y1, x2, y2 in segment.wires:
            if abs(y1 - y2) < 1e-6 and abs(x1 - x2) > 1e-6:
                horizontal.append((round(y1, 3), min(x1, x2), max(x1, x2)))
            elif abs(x1 - x2) < 1e-6 and abs(y1 - y2) > 1e-6:
                vertical.append((round(x1, 3), min(y1, y2), max(y1, y2)))
        return horizontal, vertical

    def _would_overlap(self, segment, occupancy):
        horizontal, vertical = self._spans(segment)
        own = set(segment.pinrefs)
        for axis, spans in ((0, horizontal), (1, vertical)):
            taken = occupancy[axis]
            for coord, a, b in spans:
                for c, d, owner in taken.get(coord, ()):
                    if owner in own:
                        continue          # a pin's own escape is not a conflict
                    if a < d - 1e-6 and c < b - 1e-6:
                        return True
        return False

    def _occupy(self, segment, occupancy, owner=None):
        horizontal, vertical = self._spans(segment)
        for axis, spans in ((0, horizontal), (1, vertical)):
            for coord, a, b in spans:
                occupancy[axis].setdefault(coord, []).append((a, b, owner))

    def _reserve_escapes(self, design, placement, sym_of, occupancy):
        """Book every pin's own 5 mm stub before routing anything.

        Those stubs are drawn whether or not the net around them routes, so a
        trunk that runs along one is an overlap even though nothing had been
        committed there yet. Reserving them up front is what makes the
        no-overlap guarantee hold for the declined nets too.
        """
        for ref, pins in ((r, design.parts[r]["pins"]) for r in placement.coords):
            sheet = placement.sheet_of[ref]
            seen = occupancy.setdefault(sheet, ({}, {}))
            for pin in pins:
                geo = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                placement.rot.get(ref, "R0"))
                if geo is None:
                    continue
                px, py, ex, ey = geo
                stub = Segment(sheet=sheet, wires=[(px, py, ex, ey)])
                self._occupy(stub, seen, owner=(ref, pin))

    # -- the router --------------------------------------------------------
    def route(self, design, placement, sym_of):
        routed = {}
        warnings = []
        self.declined = []
        channels = {}          # (sheet, row) -> [ (track_y, [(x1, x2), ...]) ]
        occupancy = {}         # sheet -> ({y: spans}, {x: spans})
        self._reserve_escapes(design, placement, sym_of, occupancy)

        for name, pinrefs in design.nets.items():
            segments = []
            for sheet in sorted({placement.sheet_of[r] for r, _ in pinrefs}):
                here = [(r, p) for r, p in pinrefs if placement.sheet_of[r] == sheet]
                crosses = len(here) < len(pinrefs)
                seen = occupancy.setdefault(sheet, ({}, {}))

                if name in self.supply_rails:
                    stubs = self._stubs(name, here, placement, sym_of, warnings, rail=True)
                    for stub in stubs:
                        self._occupy(stub, seen)
                    segments.extend(stubs)
                    continue

                piece = None
                for candidate in self._candidates(sheet, here, placement, sym_of,
                                                  channels, label=crosses):
                    if not self._would_overlap(candidate, seen):
                        piece = candidate
                        break
                if piece is None:
                    stubs = self._stubs(name, here, placement, sym_of, warnings)
                    for stub in stubs:
                        self._occupy(stub, seen)
                    segments.extend(stubs)
                else:
                    self._occupy(piece, seen)
                    segments.append(piece)
            if segments:
                routed[name] = segments
        return routed, warnings

    def _stubs(self, name, pinrefs, placement, sym_of, warnings, rail=False):
        """Fall back to the original stub-and-label for these pins."""
        if not rail:
            self.declined.append(name)
        out = []
        for ref, pin in pinrefs:
            geo = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                placement.rot.get(ref, "R0"))
            if geo is None:
                warnings.append("no geometry %s.%s" % (ref, pin))
                continue
            cx, cy, ex, ey = geo
            segment = Segment(sheet=placement.sheet_of[ref],
                              wires=[(cx, cy, ex, ey)], pinrefs=[(ref, pin)])
            if rail:
                segment.supplies.append((name, ex, ey, "R0"))
            else:
                segment.labels.append((ex, ey + 0.635, "R0"))
            out.append(segment)
        return out

    def _candidates(self, sheet, pinrefs, placement, sym_of, channels, label):
        """Routings to try, in order of preference.

        A two-pin net is an L, which is both shorter and cheaper in channel
        space than a trunk. Either pin can carry the horizontal leg, so both
        orders are offered — the first that does not collide wins, which is how
        pins sharing an escape line, as every connector pin does, get resolved.
        """
        if len(pinrefs) == 2:
            escapes = self._escapes(pinrefs, placement, sym_of)
            if escapes:
                for a, b in (escapes, escapes[::-1]):
                    elbow = self._elbow(sheet, a, b, placement, label)
                    if elbow is not None:
                        yield elbow
        trunk = self._route_piece(sheet, pinrefs, placement, sym_of, channels, label)
        if trunk is not None:
            yield trunk

    def _elbow(self, sheet, a, b, placement, label):
        """A two-pin net: horizontal at ``a``'s level, vertical down ``b``'s."""
        (aref, apin, apx, apy, aex, aey, avert) = a
        (bref, bpin, bpx, bpy, bex, bey, bvert) = b
        if avert and abs(aey - bey) > 1e-6:
            return None                      # a's leg would run back over its part
        drop_x = self._drop_x(b, placement) if bvert else bex

        segment = Segment(sheet=sheet, pinrefs=[(aref, apin), (bref, bpin)])
        if avert:
            segment.wires.append((apx, apy, aex, aey))
        elif abs(drop_x - apx) > 1e-6:
            # One wire from the pin to the turn, rather than the escape stub
            # plus a leg back over it. When the turn lies behind the escape,
            # emitting both draws a T at the pin that is only the wire
            # doubling back on itself.
            segment.wires.append((apx, apy, drop_x, apy))
        segment.wires.append((bpx, bpy, bex, bey))
        if bvert:
            segment.wires.append((bex, bey, drop_x, bey))
        if avert and abs(aex - drop_x) > 1e-6:
            segment.wires.append((aex, aey, drop_x, aey))
        if abs(aey - bey) > 1e-6:
            segment.wires.append((drop_x, aey, drop_x, bey))
        if not segment.wires:
            return None
        if label:
            segment.labels.append((aex, aey + 0.635, "R0"))
        return segment

    def _route_piece(self, sheet, pinrefs, placement, sym_of, channels, label):
        if len(pinrefs) < 2:
            return None
        escapes = self._escapes(pinrefs, placement, sym_of)
        if escapes is None:
            return None

        rows = {self._row_of(placement.coords[r][1]) for r, _ in pinrefs}
        if len(rows) == 1:
            channel_row = min(rows)
        elif len(rows) == 2 and max(rows) - min(rows) == 1:
            channel_row = min(rows)          # the channel between them
        else:
            return None

        drops = {}
        for escape in escapes:
            x = self._drop_x(escape, placement)
            drops.setdefault(round(x, 3), []).append(escape)
        if len(drops) < 2:
            return None

        xs = sorted(drops)
        row_y = placement.coords[pinrefs[0][0]][1]
        row_y += (self._row_of(row_y) - channel_row) * self.row_height
        track = self._claim_track(channels, (sheet, channel_row), xs[0], xs[-1], row_y)
        if track is None:
            return None

        segment = Segment(sheet=sheet)
        for x in xs:
            landings = []
            for (ref, pin, px, py, ex, ey, vertical) in drops[x]:
                segment.wires.append((px, py, ex, ey))         # the pin's own escape
                if vertical:
                    segment.wires.append((ex, ey, x, ey))      # jog clear of the part
                segment.pinrefs.append((ref, pin))
                landings.append(round(ey, 3))

            # One drop line per x, cut at every landing so the joins are real
            # ends rather than a wire passing through a pin.
            stops = sorted(set(landings) | {round(track, 3)})
            for a, b in zip(stops, stops[1:]):
                segment.wires.append((x, a, x, b))
            for y in stops[1:-1]:
                segment.junctions.append((x, y))               # T where a pin joins

        for a, b in zip(xs, xs[1:]):
            segment.wires.append((a, track, b, track))
        # The trunk meets a drop at every interior x, and at the ends only if a
        # pin also lands there rather than the drop simply turning the corner.
        for x in xs[1:-1]:
            segment.junctions.append((x, round(track, 3)))
        if label:
            segment.labels.append((xs[0], track + 0.635, "R0"))
        return segment

    def _claim_track(self, channels, key, x1, x2, row_y):
        """Lowest track in this channel whose span does not overlap ours."""
        tracks = channels.setdefault(key, [(row_y + off, []) for off in self.TRACKS])
        for track_y, spans in tracks:
            if all(x2 <= a or b <= x1 for a, b in spans):
                spans.append((x1, x2))
                return track_y
        return None


class StubRouter:
    """A stub at every pin, terminated by a label or by a rail symbol.

    Nothing is joined to anything: correctness comes from same-name label
    matching, which EAGLE honours. With ``supply_rails`` empty this is the
    original behaviour — all 627 connections drawn as loose ends.

    Naming a net in ``supply_rails`` swaps its label for a ground or supply
    symbol. That is what removes the 68 scattered ``GND`` labels and the 36
    ``P15`` ones, and it costs no routing at all.
    """

    def __init__(self, supply_rails=frozenset()):
        self.supply_rails = frozenset(supply_rails)

    def route(self, design, placement, sym_of):
        routed, warnings = {}, []
        for name, pinrefs in design.nets.items():
            is_rail = name in self.supply_rails
            segments = []
            for ref, pin in pinrefs:
                geo = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                placement.rot.get(ref, "R0"))
                if geo is None:
                    warnings.append("no geometry %s.%s" % (ref, pin))
                    continue
                cx, cy, ex, ey = geo
                segment = Segment(
                    sheet=placement.sheet_of[ref],
                    wires=[(cx, cy, ex, ey)],
                    pinrefs=[(ref, pin)])
                if is_rail:
                    segment.supplies.append((name, ex, ey, "R0"))
                else:
                    segment.labels.append((ex, ey + 0.635, "R0"))
                segments.append(segment)
            if segments:
                routed[name] = segments
        return routed, warnings


class ScanRouter:
    """Draw the wires the draughtsman drew, from transcribed polylines.

    This is not a router guiding itself by scan data — it is the scan data
    *replacing* the router. Where a net's runs have been transcribed and all
    its parts placed from the scan, the drawn wires are the original's, bends
    and all. Everything else falls through to the wrapped strategy, so this is
    incremental in exactly the way the coordinate transcription is.

    The one real complication is that the generated symbols are not the 1985
    symbols: a transcribed run ends up *near* its pin rather than on it. Each
    run is reconciled onto the real pin, keeping the direction the run was
    heading so the correction shows up as a short elbow rather than a diagonal.
    """

    def __init__(self, supply_rails=frozenset(), wires=None, fallback=None):
        from .sections import WIRES

        self.wires = WIRES if wires is None else wires
        self.supply_rails = frozenset(supply_rails)
        self.fallback = fallback or TrunkRouter(supply_rails=supply_rails)
        self.declined = []
        self.from_scan = []

    def route(self, design, placement, sym_of):
        routed, warnings = self.fallback.route(design, placement, sym_of)
        self.declined = list(getattr(self.fallback, "declined", []))
        self.from_scan = []

        for name, runs in self.wires.items():
            if name not in design.nets or name in self.supply_rails:
                continue
            segment = self._draw(name, runs, design, placement, sym_of, warnings)
            if segment is not None:
                routed[name] = [segment]
                self.from_scan.append(name)
                if name in self.declined:
                    self.declined.remove(name)
        return routed, warnings

    def _draw(self, name, runs, design, placement, sym_of, warnings):
        sheets = {placement.sheet_of[r] for r, _ in design.nets[name]}
        if len(sheets) != 1:
            return None                       # cross-sheet: keep the labels
        sheet = sheets.pop()
        convert = placement.scan_transform.get(sheet)
        if convert is None:
            return None

        segment = Segment(sheet=sheet)
        reached = set()
        for start, end, points in runs:
            path = [convert(x, y) for x, y in points]
            for endpoint, index in ((start, 0), (end, -1)):
                if endpoint is None:
                    continue
                ref, pin = endpoint.rsplit(".", 1)
                geo = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                   placement.rot.get(ref, "R0"))
                if geo is None:
                    warnings.append("%s: no geometry for %s" % (name, endpoint))
                    return None
                target = (geo[0], geo[1])
                if index == 0:
                    path = _attach(path, target)
                else:
                    path = _attach(path[::-1], target)[::-1]
                reached.add((ref, pin))

        if reached != set(design.nets[name]):
            missing = sorted(set(design.nets[name]) - reached)
            warnings.append("%s: transcribed runs miss %s"
                            % (name, ", ".join("%s.%s" % m for m in missing)))
            return None

        for start, end, points in runs:
            path = [convert(x, y) for x, y in points]
            for endpoint, index in ((start, 0), (end, -1)):
                if endpoint is None:
                    continue
                ref, pin = endpoint.rsplit(".", 1)
                geo = pin_geometry(sym_of[ref], placement.coords[ref], pin,
                                   placement.rot.get(ref, "R0"))
                target = (geo[0], geo[1])
                path = (_attach(path, target) if index == 0
                        else _attach(path[::-1], target)[::-1])
            for a, b in zip(path, path[1:]):
                if a != b:
                    segment.wires.append((a[0], a[1], b[0], b[1]))

        segment.pinrefs.extend(sorted(reached))
        segment.wires = split_at_touchpoints(segment.wires)
        segment.junctions.extend(_branch_points(segment.wires))
        return segment


def _attach(points, target, eps=1e-6):
    """Bring a run's first point onto ``target``, keeping it orthogonal."""
    if len(points) < 2:
        return [target]
    p0, p1 = points[0], points[1]
    if abs(p0[1] - p1[1]) < eps:            # the run starts out horizontal
        elbow = (target[0], p1[1])
    else:                                   # ... or vertical
        elbow = (p1[0], target[1])
    out = [target]
    if abs(elbow[0] - target[0]) > eps or abs(elbow[1] - target[1]) > eps:
        out.append(elbow)
    return out + list(points[1:])


def on_segment(point, a, b, eps=1e-6):
    """Is ``point`` strictly inside the axis-aligned segment ``a``-``b``?"""
    if abs(a[0] - b[0]) < eps and abs(point[0] - a[0]) < eps:
        return min(a[1], b[1]) + eps < point[1] < max(a[1], b[1]) - eps
    if abs(a[1] - b[1]) < eps and abs(point[1] - a[1]) < eps:
        return min(a[0], b[0]) + eps < point[0] < max(a[0], b[0]) - eps
    return False


def crossing(w1, w2, eps=1e-6):
    """Where an axis-aligned horizontal and vertical wire cross, if they do.

    Between two nets a crossing means nothing. Within one net it is a
    connection, and one that needs a dot — reading a crossing as no-connection
    when it should be a junction is the single most common way to misread a
    hand-drafted schematic, and this drawing does it to itself in places.
    """
    horizontal = vertical = None
    for a, b in ((w1, w2), (w2, w1)):
        if abs(a[1] - a[3]) < eps and abs(b[0] - b[2]) < eps:
            horizontal, vertical = a, b
            break
    if horizontal is None:
        return None
    y, x = horizontal[1], vertical[0]
    if (min(horizontal[0], horizontal[2]) - eps < x < max(horizontal[0], horizontal[2]) + eps
            and min(vertical[1], vertical[3]) - eps < y < max(vertical[1], vertical[3]) + eps):
        return (round(x, 3), round(y, 3))
    return None


def split_at_touchpoints(wires, eps=1e-6):
    """Cut every wire where another wire's end lands on it.

    A run that stops part-way along another -- the centre-tap spine, where each
    driver's tap meets it in a T -- shares no endpoint with it until the longer
    wire is split there. Without this the join is invisible: no junction dot is
    drawn, and the segment looks disconnected to every check downstream.
    """
    ends = set()
    for x1, y1, x2, y2 in wires:
        ends.add((round(x1, 3), round(y1, 3)))
        ends.add((round(x2, 3), round(y2, 3)))
    # All these wires belong to one net, so a crossing between them is a
    # connection and gets cut in as well.
    for i, first in enumerate(wires):
        for second in wires[i + 1:]:
            point = crossing(first, second, eps)
            if point is not None:
                ends.add(point)

    out = []
    for x1, y1, x2, y2 in wires:
        a, b = (round(x1, 3), round(y1, 3)), (round(x2, 3), round(y2, 3))
        if a == b:
            continue
        inner = sorted((p for p in ends if on_segment(p, a, b, eps)),
                       key=lambda p: abs(p[0] - a[0]) + abs(p[1] - a[1]))
        chain = [a] + inner + [b]
        for u, v in zip(chain, chain[1:]):
            if u != v:
                out.append((u[0], u[1], v[0], v[1]))
    return out


def _branch_points(wires, eps=1e-6):
    """Points where three or more wire ends meet, and so need a dot."""
    degree = {}
    for x1, y1, x2, y2 in wires:
        a, b = (round(x1, 3), round(y1, 3)), (round(x2, 3), round(y2, 3))
        if a == b:
            continue
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    return [p for p, d in sorted(degree.items()) if d >= 3]
