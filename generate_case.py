#!/usr/bin/env python3
"""Flat micro-ATX case for a 250 mm bed.

Motherboard lies on the floor (no metal screws). Cat on the left cheek,
phoenix on the right, both taken from the cross-stitch charts and punched
as a stitch grid: solid cells are the picture, open cells are the vents.
A grey backing sheet behind each art tile makes the black stitches read.

Fits: B560M, two DDR4 sticks, a dual-slot 1660 Super, Thermalright
Assassin X120 Refined SE, an ATX 650 W gold supply up to 180 mm long,
and five Arctic P12 Pro fans (two front intakes, two top exhausts,
one rear exhaust). The front carries the floral chart. The rear keeps
the plain square stitch.

Axes: X width, Y depth (front y=0, rear y=D, I/O at the rear), Z height.
Units mm. Origin is the outside of the front-left-bottom corner.
"""
import os, math, struct, itertools, zipfile
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
TILE_DIR = os.path.join(OUT, "flat_printable_parts")
PREV = os.path.join(OUT, "preview")
os.makedirs(TILE_DIR, exist_ok=True)
os.makedirs(PREV, exist_ok=True)
for f in os.listdir(TILE_DIR):
    os.remove(os.path.join(TILE_DIR, f))

MAX_TILE = 234.0          # cheek tiles reach ~233 mm; center those, thin brim only

# --------------------------------------------------------------------------
# stitch charts. row 0 is the top of the picture. True = stitch (solid).
CAT = np.load(os.path.join(OUT, "patterns", "cat.npy"))
PHX = np.load(os.path.join(OUT, "patterns", "phoenix.npy"))
FRONT_ART = np.load(os.path.join(OUT, "patterns", "front.npy")).astype(bool)
# join bars: these rows are forced solid so a seam can hide in them
CAT_STILE = (36, 37)          # through the branches, above the cat
PHX_STILE = (18, 19, 90, 91)  # above the wingtips and below the tail

def with_stile(mask, rows):
    m = mask.copy()
    for r in rows:
        m[r, :] = True
    return m

CAT_M = with_stile(CAT, CAT_STILE)
PHX_M = with_stile(PHX, PHX_STILE)

# --------------------------------------------------------------------------
# parts
T = 3.0
T_BOT = 4.0
FOOT = 15.0
MB_W, MB_D = 243.84, 243.84
PCB = 1.6
STANDOFF_H = 7.5          # floor top -> PCB underside (spec minimum is 6.35)
ML, MR = 18.0, 64.0       # left cheek margin, right cable gutter
PSU_BAY_L = 184.0         # accepts an ATX supply up to 180 mm long
PSU_W, PSU_H = 150.0, 86.0
CABLE_GAP = 22.0
REAR_GAP = 3.0
COOLER_H = 148.0          # Assassin X120 Refined SE
FAN = 120.0
FAN_T = 25.0
FAN_HOLE = 105.0          # P12 Pro screw spacing
WEB = 1.15                # plastic between stitch holes

CAT_PITCH = 3.00
PHX_PITCH = 2.85
CAT_HOLE = CAT_PITCH - WEB
PHX_HOLE = PHX_PITCH - WEB

# case size. height is set by the upright cat chart.
ART_MARGIN_Z = 8.0
H = ART_MARGIN_Z + CAT_M.shape[0] * CAT_PITCH + ART_MARGIN_Z
W = T + ML + MB_W + MR + T
D = T + PSU_BAY_L + CABLE_GAP + MB_D + REAR_GAP + T

ZB = FOOT + T_BOT                          # floor top
ZP_BOT = ZB + STANDOFF_H                   # PCB underside
ZP = ZP_BOT + PCB                          # PCB top
ZT = H - T                                 # ceiling underside

BX0 = T + ML
BX1 = BX0 + MB_W
YB_REAR = D - T - REAR_GAP
YB_FRONT = YB_REAR - MB_D

# mounting holes, mm from the PCB's slot-side edge and from its rear edge.
# microATX spec 1.2 holes B C F H J L M R S. Datum B is hole B.
HOLES = {
    "B": (30.48, 6.35),
    "C": (76.20, 6.35),
    "F": (233.68, 29.21),
    "R": (10.16, 161.29),
    "S": (30.48, 161.29),
    "H": (76.20, 161.29),
    "J": (233.68, 161.29),
    "L": (76.20, 233.68),
    "M": (233.68, 233.68),
}

# I/O aperture. Figure 4 of the spec, un-mirrored into component view:
# right edge of the cutout is 2.096 in (53.24 mm) to the slot side of hole B,
# and the cutout is 158.75 x 44.45. Bottom sits 3.81 mm below the PCB top.
# Component view: hole B is on the slot side of the cutout, 2.096 in (53.24 mm) away.
IO_X0 = BX0 + HOLES["B"][0] + 53.24
IO_X1 = IO_X0 + 158.75
IO_Z0 = ZP - 3.81
IO_Z1 = IO_Z0 + 44.45

# CPU is not standardized. This is a typical LGA1200 mATX socket, used for
# the cooler keep-out and the backplate pocket. Posts follow the real holes.
CPU_X = BX0 + 112.0
CPU_Y = YB_REAR - 86.0

# primary x16 is the slot nearest the I/O, on the slot-side half of the board.
# The rear opening is one wide window so a dual-slot bracket still fits if a
# particular B560M sits a few millimetres off this nominal.
SLOT_X = BX0 + 40.0
GPU_T = 42.0
GPU_ABOVE = 125.0

PSU_X1 = W - T - 8.0
PSU_X0 = PSU_X1 - PSU_W
PSU_Y0 = T + 2.0
PSU_Y1 = PSU_Y0 + 180.0

# --------------------------------------------------------------------------
AX = {"x": 0, "y": 1, "z": 2}
PLATE_AX = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}
# local print frame: thickness becomes Z, the two big axes become X Y
CYC = {"x": (1, 2, 0), "y": (2, 0, 1), "z": (0, 1, 2)}

def plate(rect, holes):
    """Rect minus holes, both as (a0, a1, b0, b1). Returns solid rectangles."""
    As = sorted({rect[0], rect[1], *[v for h in holes for v in (h[0], h[1])]})
    Bs = sorted({rect[2], rect[3], *[v for h in holes for v in (h[2], h[3])]})
    out = []
    for a0, a1 in zip(As, As[1:]):
        if a1 - a0 < 1e-6:
            continue
        run = None
        am = (a0 + a1) / 2
        for b0, b1 in zip(Bs, Bs[1:]):
            if b1 - b0 < 1e-6:
                continue
            bm = (b0 + b1) / 2
            in_hole = any(h[0] < am < h[1] and h[2] < bm < h[3] for h in holes)
            if not in_hole:
                run = [b0, b1] if run is None else [run[0], b1]
            elif run:
                out.append((a0, a1, run[0], run[1]))
                run = None
        if run:
            out.append((a0, a1, run[0], run[1]))
    return out

def mk(normal, n0, n1, r):
    ia, ib = PLATE_AX[normal]
    lo, hi = [0.0] * 3, [0.0] * 3
    lo[ia], hi[ia], lo[ib], hi[ib] = r[0], r[1], r[2], r[3]
    lo[AX[normal]], hi[AX[normal]] = n0, n1
    return (*lo, *hi)

def overlap(a, b, eps=0.05):
    return all(min(a[i + 3], b[i + 3]) - max(a[i], b[i]) > eps for i in range(3))

def clip_holes(holes, rect, min_size=0.4):
    out = []
    for h in holes:
        c = (max(h[0], rect[0]), min(h[1], rect[1]),
             max(h[2], rect[2]), min(h[3], rect[3]))
        if c[1] - c[0] > min_size and c[3] - c[2] > min_size:
            out.append(c)
    return out

def intervals_free(span, blocked, gap=0.4):
    """Cut positions that miss blocked intervals and keep every piece <= MAX_TILE."""
    lo, hi = span
    if hi - lo <= MAX_TILE:
        return []
    cuts = []
    cursor = lo
    # leave a few millimetres under the bed limit so a brim still fits
    limit = MAX_TILE - 8
    while hi - cursor > limit + 0.1:
        window_hi = min(hi - 28, cursor + limit)
        window_lo = cursor + 28
        trial = window_hi
        found = None
        while trial >= window_lo:
            if not any(a - gap < trial < b + gap for a, b in blocked):
                found = trial
                break
            trial -= 1.5
        if found is None:
            raise SystemExit(f"no seam fits in {span} after {cursor:.0f}, avoiding {blocked}")
        cuts.append(found)
        cursor = found
    return cuts

# --------------------------------------------------------------------------
comp = {}
comp["motherboard"] = [(BX0, YB_FRONT, ZP_BOT, BX1, YB_REAR, ZP)]
comp["io_ports"] = [(IO_X0 + 4, YB_REAR - 8, ZP, IO_X1 - 4, D - 1, ZP + 36)]
comp["ram"] = [
    (BX0 + 178, CPU_Y - 70, ZP, BX0 + 190, CPU_Y + 68, ZP + 34),
    (BX0 + 192, CPU_Y - 70, ZP, BX0 + 204, CPU_Y + 68, ZP + 34),
]
comp["cpu_socket"] = [(CPU_X - 20, CPU_Y - 20, ZP, CPU_X + 20, CPU_Y + 20, ZP + 8)]
# fin stack starts above the RAM. The 120 mm fan clips on the front of the
# stack and can be slid up, so it is not a hard solid.
comp["cpu_cooler"] = [(CPU_X - 62, CPU_Y - 26, ZP + 36,
                       CPU_X + 62, CPU_Y + 26, ZP + COOLER_H)]
comp["cpu_base"] = [(CPU_X - 24, CPU_Y - 24, ZP, CPU_X + 24, CPU_Y + 24, ZP + 36)]
comp["gpu"] = [(SLOT_X - GPU_T + 4, YB_REAR - 250, ZP + 2,
                SLOT_X + 8, D - T, ZP + GPU_ABOVE)]
comp["psu"] = [(PSU_X0, PSU_Y0, ZB, PSU_X1, PSU_Y1, ZB + PSU_H)]

# Five P12 mounts. The two extra fans are the upper front intake and the
# forward lid exhaust. A third fan on the front would land on the floral
# chart, so that one goes on the lid instead.
# Plane coords: front/rear are (x, z), lid is (x, y). Centers are 136 mm
# apart so a seam still fits between them.
fan_front_lo = (T + 78.0, ZB + 78.0)
fan_front_hi = (fan_front_lo[0], fan_front_lo[1] + 136.0)
fan_top_cpu = (CPU_X, CPU_Y)
fan_top_fwd = (CPU_X, CPU_Y - 140.0)
fan_rear_c = (BX0 + 175.0, IO_Z1 + 12 + FAN / 2)
comp["fans"] = [
    (fan_front_lo[0] - 60, T, fan_front_lo[1] - 60,
     fan_front_lo[0] + 60, T + FAN_T, fan_front_lo[1] + 60),
    (fan_front_hi[0] - 60, T, fan_front_hi[1] - 60,
     fan_front_hi[0] + 60, T + FAN_T, fan_front_hi[1] + 60),
    (fan_top_cpu[0] - 60, fan_top_cpu[1] - 60, ZT - FAN_T,
     fan_top_cpu[0] + 60, fan_top_cpu[1] + 60, ZT),
    (fan_top_fwd[0] - 60, fan_top_fwd[1] - 60, ZT - FAN_T,
     fan_top_fwd[0] + 60, fan_top_fwd[1] + 60, ZT),
    (fan_rear_c[0] - 60, D - T - FAN_T, fan_rear_c[1] - 60,
     fan_rear_c[0] + 60, D - T, fan_rear_c[1] + 60),
]
comp_boxes = [b for v in comp.values() for b in v]

# --------------------------------------------------------------------------
tiles, battens, extras = [], [], []
blockers = list(comp_boxes)

def add_tile(pid, normal, n0, n1, rect, holes):
    holes = clip_holes(holes, rect)
    rects = plate(rect, holes)
    boxes = [mk(normal, n0, n1, r) for r in rects]
    t = dict(id=pid, normal=normal, boxes=boxes, rect=rect)
    tiles.append(t)
    blockers.extend(boxes)
    return t

def add_boxes(pid, normal, boxes, kind="extra"):
    item = dict(id=pid, normal=normal, boxes=boxes, kind=kind)
    extras.append(item)
    blockers.extend(boxes)
    return item

def _clear_of_parts(box):
    return not any(overlap(box, c, eps=0.2) for c in comp_boxes)

def add_batten_rect(pid, normal, n0, n1, rect):
    """A glue strip. Long strips are split, and any piece that hits a part is dropped."""
    a0, a1, b0, b1 = rect
    long_a = (a1 - a0) >= (b1 - b0)
    length = (a1 - a0) if long_a else (b1 - b0)
    if length > 200:
        mid_a = (a0 + a1) / 2 if long_a else a1
        mid_b = (b0 + b1) / 2 if not long_a else b1
        add_batten_rect(pid + "a", normal, n0, n1,
                        (a0, mid_a if long_a else a1, b0, mid_b if not long_a else b1))
        add_batten_rect(pid + "b", normal, n0, n1,
                        (mid_a if long_a else a0, a1, mid_b if not long_a else b0, b1))
        return
    # nibble 12 mm off either end of the long axis wherever a part intrudes
    box = mk(normal, n0, n1, rect)
    if _clear_of_parts(box):
        battens.append(dict(id=pid, normal=normal, boxes=[box]))
        blockers.append(box)
        return
    if length < 28:
        return
    if long_a:
        add_batten_rect(pid + "a", normal, n0, n1, (a0, a0 + length / 2, b0, b1))
        add_batten_rect(pid + "b", normal, n0, n1, (a0 + length / 2, a1, b0, b1))
    else:
        add_batten_rect(pid + "a", normal, n0, n1, (a0, a1, b0, b0 + length / 2))
        add_batten_rect(pid + "b", normal, n0, n1, (a0, a1, b0 + length / 2, b1))

def fan_opening(cx, cy, radius=55.0):
    """Horizontal slots inside a circle, plus four screw holes. Plane coords."""
    holes = []
    y = -48.0
    while y < 48.0:
        half = math.sqrt(max(0.0, radius ** 2 - (y + 2.2) ** 2))
        if half > 10:
            holes.append((cx - half + 1.5, cx + half - 1.5, cy + y, cy + y + 4.4))
        y += 8.0
    s = FAN_HOLE / 2
    for sx, sy in ((-s, -s), (s, -s), (-s, s), (s, s)):
        holes.append((cx + sx - 2.4, cx + sx + 2.4, cy + sy - 2.4, cy + sy + 2.4))
    return holes

def geo_holes(rect, avoid, pitch=9.0, size=3.3, margin=8.0):
    """Small square vents, the quiet pattern around the animals and on the lid."""
    holes = []
    a = rect[0] + margin
    while a < rect[1] - margin:
        b = rect[2] + margin
        while b < rect[3] - margin:
            h = (a - size / 2, a + size / 2, b - size / 2, b + size / 2)
            if h[0] > rect[0] + 4 and h[2] > rect[2] + 4 and h[1] < rect[1] - 4 and h[3] < rect[3] - 4:
                if not any(h[0] < av[1] and av[0] < h[1] and h[2] < av[3] and av[2] < h[3] for av in avoid):
                    holes.append(h)
            b += pitch
        a += pitch
    return holes

def art_holes(mask, pitch, hole, x0, z_top):
    """Open cells of a chart. Row 0 sits at z_top and grows downward."""
    rows, cols = mask.shape
    inset = (pitch - hole) / 2.0
    holes = []
    for r in range(rows):
        z1 = z_top - r * pitch
        z0 = z1 - pitch
        for c in range(cols):
            if mask[r, c]:
                continue
            holes.append((x0 + c * pitch + inset, x0 + c * pitch + pitch - inset,
                          z0 + inset, z1 - inset))
    return holes

def rect_hit(h, blocked):
    return any(h[0] < b[1] and b[0] < h[1] and h[2] < b[3] and b[2] < h[3] for b in blocked)

# --------------------------------------------------------------------------
# sides. each cheek is split so every tile fits the bed. the animal is upright
# on the rear tile; the seam hides in a solid stitch row.
def build_side(name, mask, pitch, hole, stile_rows, x_outer_is_zero):
    rows, cols = mask.shape
    art_w = cols * pitch
    art_h = rows * pitch
    z_top = H - ART_MARGIN_Z
    z_bot = z_top - art_h
    # both the front tile and the rear tile have to fit the bed
    rear_len = min(MAX_TILE - 1.0, max(art_w + 12.0, D - (MAX_TILE - 1.0)))
    if art_w + 8 > rear_len:
        raise SystemExit(f"{name} art {art_w:.0f} mm does not fit a {rear_len:.0f} mm tile")
    y_seam = D - rear_len
    art_x0 = y_seam + (rear_len - art_w) / 2          # "x" here is case Y
    # horizontal seams through the middle of each stile pair
    seams_z = []
    bands = []
    # stile_rows comes in pairs (upper row, lower row) of a join
    pairs = list(zip(stile_rows[0::2], stile_rows[1::2]))
    # walk top to bottom
    prev = z_top
    # also the panel itself runs 0..H, art is inset
    cut_zs = []
    for ra, rb in pairs:
        # boundary between ra and rb is the joint, ra is the upper row
        z_joint = z_top - (ra + 1) * pitch
        cut_zs.append(z_joint)
    cut_zs = sorted(cut_zs, reverse=True)
    # vertical (Y) pieces: front pattern, rear art
    y_pieces = [(0.0, y_seam, False), (y_seam, D, True)]
    z_edges = [H] + cut_zs + [0.0]
    n0, n1 = (0.0, T) if x_outer_is_zero else (W - T, W)
    art_keep = []
    made = []
    for yi, (ya, yb, is_art) in enumerate(y_pieces):
        for zi in range(len(z_edges) - 1):
            za, zb = z_edges[zi], z_edges[zi + 1]   # za > zb
            rect = (ya, yb, zb, za)
            holes = []
            if is_art:
                # cells whose z-span sits inside this tile, plus a 5 mm solid border
                inset_rect = (ya + 3.5, yb - 3.5, zb + 3.5, za - 3.5)
                holes = [h for h in art_holes(mask, pitch, hole, art_x0, z_top)
                         if h[0] >= inset_rect[0] and h[1] <= inset_rect[1]
                         and h[2] >= inset_rect[2] and h[3] <= inset_rect[3]]
                art_keep.append((art_x0 - 2, art_x0 + art_w + 2, z_bot - 2, z_top + 2))
            else:
                holes = geo_holes(rect, avoid=[])
            # keep a solid strip along every cut so the batten has glue area
            pid = f"{name}_{yi}{zi}"
            add_tile(pid, "x", n0, n1, rect, holes)
            made.append((pid, rect, is_art))
    # battens on the inside
    if x_outer_is_zero:
        bn0, bn1 = T, T + 3.0
    else:
        bn0, bn1 = W - T - 3.0, W - T
    add_batten_rect(f"{name}_batten_y", "x", bn0, bn1,
                    (y_seam - 4, y_seam + 4, 20, H - 20))
    for zc in cut_zs:
        add_batten_rect(f"{name}_batten_z{int(zc)}", "x", bn0, bn1,
                        (y_seam + 6, D - 8, zc - 3.5, zc + 3.5))
    return dict(art_x0=art_x0, art_w=art_w, z_top=z_top, z_bot=z_bot,
                y_seam=y_seam, cut_zs=cut_zs, rear_len=rear_len)

print("building left cheek (cat)...")
left = build_side("left", CAT_M, CAT_PITCH, CAT_HOLE, CAT_STILE, True)
print("building right cheek (phoenix)...")
right = build_side("right", PHX_M, PHX_PITCH, PHX_HOLE, PHX_STILE, False)

# --------------------------------------------------------------------------
# remaining shell
def emit_split(name, normal, n0, n1, rect, holes, blocked_a, blocked_b):
    cuts_a = intervals_free((rect[0], rect[1]), blocked_a)
    cuts_b = intervals_free((rect[2], rect[3]), blocked_b)
    a_edges = [rect[0], *cuts_a, rect[1]]
    b_edges = [rect[2], *cuts_b, rect[3]]
    for i in range(len(a_edges) - 1):
        for j in range(len(b_edges) - 1):
            sub = (a_edges[i], a_edges[i + 1], b_edges[j], b_edges[j + 1])
            add_tile(f"{name}_{i}{j}", normal, n0, n1, sub, holes)
    return cuts_a, cuts_b

# bottom: two slabs so the CPU pocket, clip channels and post sockets are recesses
# rather than holes through to the desk. PSU intake slots go through both.
psu_vent = []
yy = PSU_Y0 + 16
while yy < PSU_Y1 - 16:
    psu_vent.append((PSU_X0 + 12, PSU_X1 - 12, yy, yy + 6))
    yy += 14

cpu_pocket = (CPU_X - 55, CPU_X + 55, CPU_Y - 55, CPU_Y + 55)

# clip channels, in the top 2 mm of the floor. long, so a clip can slide.
clip_channels = [
    # left edge, front half of the board, opens toward the cheek
    (BX0 - 16, BX0 - 1.5, YB_FRONT + 18, YB_FRONT + 78),
    # right gutter, rear half, clear of the 24-pin area
    (BX1 + 1.5, BX1 + 18, YB_REAR - 110, YB_REAR - 40),
    # front edge of the board, two spans with a gap in the middle
    (BX0 + 30, BX0 + 100, YB_FRONT - 16, YB_FRONT - 1.5),
    (BX0 + 130, BX0 + 210, YB_FRONT - 16, YB_FRONT - 1.5),
]
post_pockets = []
for hx, hy in HOLES.values():
    cx, cy = BX0 + hx, YB_REAR - hy
    post_pockets.append((cx - 4.3, cx + 4.3, cy - 4.3, cy + 4.3))

bot_rect = (T, W - T, T, D - T)
# seams may cross the CPU pocket (the batten is under the floor). They may not
# cross a post socket or slice a PSU intake slot.
blocked_x = [(p[0] - 4, p[1] + 4) for p in post_pockets]
blocked_x += [(PSU_X0 + 8, PSU_X1 - 8)]
blocked_y = [(p[2] - 4, p[3] + 4) for p in post_pockets]
blocked_y += [(h[2] - 1, h[3] + 1) for h in psu_vent]

lower_holes = psu_vent
upper_holes = psu_vent + [cpu_pocket] + clip_channels + post_pockets
print("building floor...")
_, _ = emit_split("bottom_lo", "z", FOOT, FOOT + 2.0, bot_rect, lower_holes, blocked_x, blocked_y)
cuts_bx, cuts_by = emit_split("bottom_hi", "z", FOOT + 2.0, ZB, bot_rect, upper_holes, blocked_x, blocked_y)
for x in cuts_bx:
    add_batten_rect(f"bottom_batten_x{int(x)}", "z", FOOT - 3.0, FOOT,
                    (x - 6, x + 6, T + 14, D - T - 14))
for y in cuts_by:
    add_batten_rect(f"bottom_batten_y{int(y)}", "z", FOOT - 3.0, FOOT,
                    (T + 14, W - T - 14, y - 6, y + 6))

# top: two exhausts. The square stitch stays here; the floral chart is the front.
top_rect = (T, W - T, T, D - T)
top_fans = (fan_top_cpu, fan_top_fwd)
top_holes = []
for c in top_fans:
    top_holes += fan_opening(c[0], c[1])
top_avoid = [(c[0] - 68, c[0] + 68, c[1] - 68, c[1] + 68) for c in top_fans]
top_holes += geo_holes(top_rect, avoid=top_avoid)
blocked_top_x = [(c[0] - 68, c[0] + 68) for c in top_fans]
blocked_top_y = [(c[1] - 68, c[1] + 68) for c in top_fans]
print("building lid...")
cuts_tx, cuts_ty = emit_split("top", "z", ZT, H, top_rect, top_holes, blocked_top_x, blocked_top_y)
for x in cuts_tx:
    add_batten_rect(f"top_batten_x{int(x)}", "z", ZT - 3, ZT, (x - 6, x + 6, T + 16, D - T - 16))
for y in cuts_ty:
    add_batten_rect(f"top_batten_y{int(y)}", "z", ZT - 3, ZT, (T + 16, W - T - 16, y - 6, y + 6))

# front. The floral chart is cropped to its center medallion and scaled so the
# whole framed design sits in the open rectangle right of the fans and above
# the supply, with a solid margin on every side. The power button moves up
# above the fans so it does not cut the chart. Seams are placed by hand:
# the vertical seam stays in the gap between the fans and the supply, the
# left horizontal seam sits between the two fans, and the right horizontal
# seam sits just above the supply, under the chart.
INSCRIPTION = "To my beloved sister"
# solid plaque under the lower fan, clear of its screw holes (those sit at z ~45)
plaque = (22.0, 142.0, 17.0, 38.0)

def italic_runs(rect, text, px=0.40):
    """Ink of an italic line, as rectangles in the plaque plane. Row 0 is up."""
    from PIL import Image, ImageDraw, ImageFont
    x0, x1, z0, z1 = rect
    pad = 2.6
    max_w = int((x1 - x0 - 2 * pad) / px)
    max_h = int((z1 - z0 - 2 * pad) / px)
    font_path = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
    best = None
    lo, hi = 10, 120
    while lo <= hi:
        size = (lo + hi) // 2
        font = ImageFont.truetype(font_path, size)
        im = Image.new("L", (max_w + 8, max_h + 8), 0)
        ImageDraw.Draw(im).text((2, 2), text, font=font, fill=255)
        arr = np.array(im) > 140
        ys, xs = np.where(arr)
        if len(xs) == 0:
            lo = size + 1
            continue
        w = int(xs.max() - xs.min() + 1)
        h = int(ys.max() - ys.min() + 1)
        if w <= max_w and h <= max_h:
            best = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            lo = size + 1
        else:
            hi = size - 1
    if best is None:
        raise SystemExit("inscription does not fit the plaque")
    ink = best
    # one pixel of growth keeps the thin italic strokes open enough for a 0.4 mm nozzle
    p = np.pad(ink, 1, constant_values=False)
    grown = np.zeros_like(ink)
    for dy in range(3):
        for dx in range(3):
            grown |= p[dy:dy + ink.shape[0], dx:dx + ink.shape[1]]
    ink = grown
    rows, cols = ink.shape
    ox = x0 + ((x1 - x0) - cols * px) / 2
    z_top = z1 - ((z1 - z0) - rows * px) / 2
    holes = []
    for r in range(rows):
        c = 0
        while c < cols:
            if not ink[r, c]:
                c += 1
                continue
            c0 = c
            while c < cols and ink[r, c]:
                c += 1
            holes.append((ox + c0 * px, ox + c * px, z_top - (r + 1) * px, z_top - r * px))
    return holes

# The whole medallion, including its own border row. Centered in the 91 chart.
_crop_n = 63
_crop_o = (FRONT_ART.shape[0] - _crop_n) // 2
front_mask = FRONT_ART[_crop_o:_crop_o + _crop_n, _crop_o:_crop_o + _crop_n]

x_seam = 147.0
z_seam_left = (fan_front_lo[1] + fan_front_hi[1]) / 2
z_seam_right = ZB + PSU_H + 11.0
# square available inside the upper-right tile, 4 mm off every cut
win = (x_seam + 4.0, (W - T) - 4.0, z_seam_right + 4.0, H - 4.0)
side = min(win[1] - win[0], win[3] - win[2]) - 2.0
FRONT_PITCH = side / front_mask.shape[1]
FRONT_HOLE = FRONT_PITCH - WEB
art_w = front_mask.shape[1] * FRONT_PITCH
art_h = front_mask.shape[0] * FRONT_PITCH
front_x0 = win[0] + ((win[1] - win[0]) - art_w) / 2
front_z_top = win[3] - ((win[3] - win[2]) - art_h) / 2

front_rect = (T, W - T, FOOT, H)
psu_cx = (PSU_X0 + PSU_X1) / 2
psu_cz = ZB + PSU_H / 2
# above the upper fan, on the solid strip over the intakes
btn_x, btn_z = fan_front_hi[0] - 16.0, H - 18.0
front_func = []
for c in (fan_front_lo, fan_front_hi):
    front_func += fan_opening(c[0], c[1])
front_func.append((psu_cx - 28, psu_cx + 28, psu_cz - 8, psu_cz + 22))
for sx, sz in ((-64, -32), (64, -32), (-64, 32), (64, 32)):
    front_func.append((psu_cx + sx - 2.4, psu_cx + sx + 2.4,
                       psu_cz + sz - 4.5, psu_cz + sz + 4.5))
front_func.append((btn_x - 8.2, btn_x + 8.2, btn_z - 8.2, btn_z + 8.2))
front_func.append((btn_x + 16.0, btn_x + 21.0, btn_z - 2.5, btn_z + 2.5))
front_func.append(plaque)
front_chart = art_holes(front_mask, FRONT_PITCH, FRONT_HOLE, front_x0, front_z_top)
print("building front...")
# four tiles. The chart lives entirely in the upper-right one.
front_tiles = [
    ((T, x_seam, FOOT, z_seam_left), "00"),
    ((T, x_seam, z_seam_left, H), "01"),
    ((x_seam, W - T, FOOT, z_seam_right), "10"),
    ((x_seam, W - T, z_seam_right, H), "11"),
]
for sub, tag in front_tiles:
    inset = (sub[0] + 3.5, sub[1] - 3.5, sub[2] + 3.5, sub[3] - 3.5)
    local = [h for h in front_chart
             if h[0] >= inset[0] and h[1] <= inset[1]
             and h[2] >= inset[2] and h[3] <= inset[3]]
    add_tile(f"front_{tag}", "y", 0, T, sub, front_func + local)
add_batten_rect("front_batten_x", "y", T, T + 3, (x_seam - 5, x_seam + 5, FOOT + 12, H - 12))
add_batten_rect("front_batten_z_left", "y", T, T + 3,
                (T + 10, x_seam - 8, z_seam_left - 5, z_seam_left + 5))
add_batten_rect("front_batten_z_right", "y", T, T + 3,
                (x_seam + 8, W - T - 10, z_seam_right - 5, z_seam_right + 5))

# one piece: 0.8 mm engraved face (letters missing) over a solid back, so the
# line is recessed and does not pierce the panel. Prints face-down.
ENGRAVE = 0.8
letter_holes = italic_runs(plaque, INSCRIPTION)
face = [mk("y", 0.0, ENGRAVE, r) for r in plate(plaque, letter_holes)]
backer = [mk("y", ENGRAVE, T, plaque)]
add_boxes("inscription", "y", face + backer, kind="inscription")

# rear: I/O, GPU window, exhaust fan
rear_rect = (T, W - T, FOOT, H)
slot_window = (BX0 + 6, IO_X0 - 8, ZP - 6, ZP + GPU_ABOVE + 4)
# Outer 1.2 mm carries the real I/O cutout (an ATX shield clips onto 0.94-1.32 mm).
# The inner 1.8 mm is opened 8 mm larger, so the clip edge is only 1.2 mm thick.
io_exact = (IO_X0, IO_X1, IO_Z0, IO_Z1)
io_relief = (IO_X0 - 8, IO_X1 + 8, IO_Z0 - 8, IO_Z1 + 8)
rear_common = fan_opening(fan_rear_c[0], fan_rear_c[1])
rear_common += geo_holes(rear_rect, avoid=[
    (slot_window[0] - 4, slot_window[1] + 4, slot_window[2] - 4, slot_window[3] + 4),
    (io_relief[0] - 2, io_relief[1] + 2, io_relief[2] - 2, io_relief[3] + 2),
    (fan_rear_c[0] - 68, fan_rear_c[0] + 68, fan_rear_c[1] - 68, fan_rear_c[1] + 68),
])
rear_block_x = [(slot_window[0] - 2, slot_window[1] + 2), (IO_X0 - 2, IO_X1 + 2),
                (fan_rear_c[0] - 62, fan_rear_c[0] + 62)]
rear_block_z = [(slot_window[2] - 2, slot_window[3] + 2), (IO_Z0 - 2, IO_Z1 + 2),
                (fan_rear_c[1] - 62, fan_rear_c[1] + 62)]
print("building rear...")
emit_split("rear_out", "y", D - 1.2, D, rear_rect,
           [slot_window, io_exact] + rear_common, rear_block_x, rear_block_z)
cuts_rx, cuts_rz = emit_split(
    "rear_in", "y", D - T, D - 1.2, rear_rect,
    [slot_window, io_relief] + rear_common, rear_block_x, rear_block_z)
for x in cuts_rx:
    add_batten_rect(f"rear_batten_x{int(x)}", "y", D - T - 3, D - T, (x - 6, x + 6, FOOT + 12, H - 12))
for z in cuts_rz:
    add_batten_rect(f"rear_batten_z{int(z)}", "y", D - T - 3, D - T, (T + 12, W - T - 12, z - 6, z + 6))

# corner rails, inside, split so each is printable
for (cx, cy, tag) in (
        (T, T, "fl"), (W - T - 8, T, "fr"),
        (T, D - T - 8, "rl"), (W - T - 8, D - T - 8, "rr")):
    z0 = FOOT
    k = 0
    while z0 < H - 12:
        z1 = min(z0 + 200, H - 4)
        add_boxes(f"corner_{tag}_{k}", "z", [(cx, cy, z0, cx + 8, cy + 8, z1)], kind="corner")
        z0 = z1
        k += 1

# feet
foot_xy = [(12, 12), (W - 40, 12), (12, D - 40), (W - 40, D - 40),
           (PSU_X0 + 8, 12), (PSU_X1 - 36, 12)]
for i, (x, y) in enumerate(foot_xy):
    add_boxes(f"foot_{i}", "z", [(x, y, 0, x + 28, y + 28, FOOT)], kind="foot")

# --------------------------------------------------------------------------
# grey backings, one per art tile, 3.5 mm behind the cheek
def backing_for(name, info, mask, pitch, x_inside_grow):
    """x_inside_grow is +1 on the left cheek (backing at +x) and -1 on the right."""
    rows, cols = mask.shape
    z_top = info["z_top"]
    boundaries = [z_top] + sorted(info["cut_zs"], reverse=True) + [info["z_bot"]]
    # pair boundaries with the rows they cover
    row_edges = [0]
    for ra, rb in zip(PHX_STILE[0::2] if name == "right" else CAT_STILE[0::2],
                      PHX_STILE[1::2] if name == "right" else CAT_STILE[1::2]):
        row_edges.append(rb)          # lower stile row starts the next band
    row_edges.append(rows)
    y0 = info["art_x0"]
    y1 = y0 + info["art_w"]
    sign = 1 if x_inside_grow > 0 else -1
    x_face = T if sign > 0 else W - T
    x0 = x_face + sign * 3.5
    x1 = x0 + sign * 1.8
    if x0 > x1:
        x0, x1 = x1, x0
    for bi in range(len(boundaries) - 1):
        za, zb = boundaries[bi], boundaries[bi + 1]
        r0, r1 = row_edges[bi], row_edges[bi + 1]
        # horizontal slots through the backing, interrupted by a solid frame
        rect = (y0 + 3, y1 - 3, zb + 3, za - 3)
        if rect[1] - rect[0] < 20 or rect[3] - rect[2] < 16:
            continue
        slots = []
        z = rect[2] + 7
        while z < rect[3] - 7:
            slots.append((rect[0] + 8, rect[1] - 8, z, z + 5))
            z += 11
        boxes = [mk("x", x0, x1, r) for r in plate(rect, slots)]
        add_boxes(f"backing_{name}_{bi}", "x", boxes, kind="backing")

backing_for("left", left, CAT_M, CAT_PITCH, +1)
backing_for("right", right, PHX_M, PHX_PITCH, -1)

# grey sheet behind the front chart, so the black stitches read.
# Slotted, and cut away where a fan or the supply sits.
front_art_rect = (front_x0, front_x0 + front_mask.shape[1] * FRONT_PITCH,
                  front_z_top - front_mask.shape[0] * FRONT_PITCH, front_z_top)
fx0, fx1 = max(front_art_rect[0], T + 14), min(front_art_rect[1], W - T - 14)
fz0, fz1 = max(front_art_rect[2], FOOT + 14), min(front_art_rect[3], H - 14)
back_cuts_x = []
cursor = fx0
while fx1 - cursor > 210:
    back_cuts_x.append(cursor + 200)
    cursor += 200
back_cuts_z = []
cursor = fz0
while fz1 - cursor > 210:
    back_cuts_z.append(cursor + 200)
    cursor += 200
bx_edges = [fx0, *back_cuts_x, fx1]
bz_edges = [fz0, *back_cuts_z, fz1]
fan_cut = [(c[0] - 68, c[0] + 68, c[1] - 68, c[1] + 68) for c in (fan_front_lo, fan_front_hi)]
fan_cut.append((PSU_X0 - 2, PSU_X1 + 2, ZB - 2, ZB + PSU_H + 4))
bi = 0
for i in range(len(bx_edges) - 1):
    for j in range(len(bz_edges) - 1):
        rect = (bx_edges[i] + 2, bx_edges[i + 1] - 2, bz_edges[j] + 2, bz_edges[j + 1] - 2)
        if rect[1] - rect[0] < 24 or rect[3] - rect[2] < 24:
            continue
        slots = []
        z = rect[2] + 7
        while z < rect[3] - 7:
            slots.append((rect[0] + 6, rect[1] - 6, z, z + 5))
            z += 11
        # plate() treats every hole edge as a grid line, so holes must be clipped
        # to this piece or the sheet grows out to the fan cutouts.
        holes = clip_holes(slots + fan_cut, rect)
        boxes = [mk("y", T + 3.5, T + 5.3, r) for r in plate(rect, holes)]
        if boxes:
            add_boxes(f"backing_front_{bi}", "y", boxes, kind="backing")
            bi += 1

# --------------------------------------------------------------------------
# printed hardware that needs no metal screws
def post_local_boxes():
    """Support post. Base press-fits a floor socket. Stem is the 7.5 mm standoff.
    A 2.6 mm hole takes the locating pin, or an M3 if you later want a screw."""
    return [
        (0.2, 0.2, 0.0, 8.0, 8.0, 2.6),          # base
        (0.7, 0.7, 2.6, 7.5, 7.5, 2.6 + 7.5),    # stem
        # hole is the missing center of the stem: build the stem as 4 walls
    ]

def post_boxes_world(cx, cy):
    """World boxes for one post. Stem top is the PCB underside."""
    base_top = ZB + 0.6
    stem_top = ZP_BOT
    return [
        (cx - 3.9, cy - 3.9, ZB - 2.0, cx + 3.9, cy + 3.9, base_top),
        (cx - 3.4, cy - 3.4, base_top, cx - 1.2, cy + 3.4, stem_top),
        (cx + 1.2, cy - 3.4, base_top, cx + 3.4, cy + 3.4, stem_top),
        (cx - 1.2, cy - 3.4, base_top, cx + 1.2, cy - 1.2, stem_top),
        (cx - 1.2, cy + 1.2, base_top, cx + 1.2, cy + 3.4, stem_top),
    ]

def pin_local():
    # head on the bed, shaft up. shaft fits through a 3.2 mm PCB hole.
    return [
        (0, 0, 0, 10, 10, 2.0),
        (4.0, 4.0, 2.0, 6.0, 6.0, 2.0 + 1.6 + 3.2),
    ]

def clip_local():
    """Slider + riser + lip. Print it on the slider face.
    The lip reaches 4 mm over the PCB edge once the slider is in its channel."""
    return [
        (0, 0, 0, 18, 8, 2.0),                  # slider
        (14, 0, 0, 18, 8, 12.6),                # riser
        (18, 1.0, 9.6, 22.5, 7.0, 12.0),        # lip, just above a 1.6 mm PCB
    ]

# local STLs for the loose hardware
hardware_local = {
    "standoff_post_x9": [
        (0.2, 0.2, 0, 8.0, 8.0, 2.6),
        (0.6, 0.6, 2.6, 2.8, 7.4, 10.1),
        (5.2, 0.6, 2.6, 7.4, 7.4, 10.1),
        (2.8, 0.6, 2.6, 5.2, 2.8, 10.1),
        (2.8, 5.2, 2.6, 5.2, 7.4, 10.1),
    ],
    # glues to the floor at the two inner bottom corners of the supply,
    # so it cannot slide toward the board. Cables exit above the stops.
    "psu_corner_stop_x2": [(0, 0, 0, 22, 12, 16)],
    "locating_pin_x9": pin_local(),
    "edge_clip_x4": clip_local(),
    "gpu_pad_6mm": [(0, 0, 0, 22, 14, 6)],
    "gpu_pad_8mm": [(0, 0, 0, 22, 14, 8)],
    "gpu_pad_10mm": [(0, 0, 0, 22, 14, 10)],
    "slot_cover_x2": [(0, 0, 0, 16, 120, 2.0), (0, 0, 2.0, 16, 8, 4.5), (0, 112, 2.0, 16, 120, 4.5)],
}

# posts in the assembly, so the fit check sees them
for hole_name, (hx, hy) in HOLES.items():
    add_boxes(f"post_{hole_name}", "z", post_boxes_world(BX0 + hx, YB_REAR - hy), kind="post")

# --------------------------------------------------------------------------
# verification
def local_boxes(normal, boxes):
    ia, ib, ic = CYC[normal]
    bs = [(b[ia], b[ib], b[ic], b[ia + 3], b[ib + 3], b[ic + 3]) for b in boxes]
    mn = [min(b[k] for b in bs) for k in range(3)]
    return [(b[0] - mn[0], b[1] - mn[1], b[2] - mn[2],
             b[3] - mn[0], b[4] - mn[1], b[5] - mn[2]) for b in bs]

def extents(boxes):
    return [max(b[k + 3] for b in boxes) - min(b[k] for b in boxes) for k in range(3)]

def vol(boxes):
    return sum(max(0, b[3] - b[0]) * max(0, b[4] - b[1]) * max(0, b[5] - b[2]) for b in boxes)

problems = []
foot_sizes = {}

all_items = []
for t in tiles:
    all_items.append(t)
for b in battens:
    all_items.append(b)
for e in extras:
    all_items.append(e)

for it in all_items:
    if not it["boxes"]:
        problems.append(f"{it['id']} is empty")
        continue
    e = extents(local_boxes(it["normal"], it["boxes"]))
    foot_sizes[it["id"]] = e
    if max(e[0], e[1]) > MAX_TILE + 0.5:
        problems.append(f"{it['id']} footprint {e[0]:.0f}x{e[1]:.0f} exceeds {MAX_TILE:.0f}")

for it in tiles + battens:
    for b in it["boxes"]:
        for n, c in ((n, c) for n, vs in comp.items() for c in vs):
            if n in ("motherboard",) and it["id"].startswith("post"):
                continue
            if overlap(b, c):
                problems.append(f"{it['id']} overlaps {n}")
                break

# hardware footprints
for name, boxes in hardware_local.items():
    e = extents(boxes)
    foot_sizes[name] = e
    if max(e[0], e[1]) > MAX_TILE:
        problems.append(f"{name} footprint {e[0]:.0f}x{e[1]:.0f}")

# cooler vs ceiling, gpu vs front fan, psu vs board
cooler_top = ZP + COOLER_H
fan_bot = ZT - FAN_T
if cooler_top > fan_bot - 4:
    problems.append(f"cooler top {cooler_top:.0f} meets top fan at {fan_bot:.0f}")
if PSU_Y1 > YB_FRONT - 8:
    problems.append("PSU bay runs into the motherboard")
if IO_X1 > BX1 + 2 or IO_X0 < BX0:
    problems.append("I/O aperture misses the board")
if slot_window[1] > IO_X0 - 4:
    problems.append("GPU window runs into the I/O aperture")
for i, a in enumerate(comp["fans"]):
    for b in comp["fans"][i + 1:]:
        if overlap(a, b, eps=1.0):
            problems.append("two case fans occupy the same space")
    if a[0] < -1 or a[3] > W + 1 or a[1] < -1 or a[4] > D + 1 or a[2] < 0 or a[5] > H + 1:
        problems.append("a case fan hangs outside the shell")

# --------------------------------------------------------------------------
QUADS = [([0, 3, 2, 1], (0, 0, -1)), ([4, 5, 6, 7], (0, 0, 1)),
         ([0, 1, 5, 4], (0, -1, 0)), ([2, 3, 7, 6], (0, 1, 0)),
         ([1, 2, 6, 5], (1, 0, 0)), ([3, 0, 4, 7], (-1, 0, 0))]

def corners(b):
    x0, y0, z0, x1, y1, z1 = b
    return np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                     [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)

def write_stl(path, boxes):
    tris = []
    for b in boxes:
        c = corners(b)
        for idx, n in QUADS:
            q = c[idx]
            tris.append((n, q[0], q[1], q[2]))
            tris.append((n, q[0], q[2], q[3]))
    with open(path, "wb") as f:
        f.write(b"stitch matx case part (mm)".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for n, a, b_, c_ in tris:
            f.write(struct.pack("<12fH", *n, *a, *b_, *c_, 0))

def export():
    for it in all_items:
        write_stl(os.path.join(TILE_DIR, it["id"] + ".stl"),
                  local_boxes(it["normal"], it["boxes"]))
    for name, boxes in hardware_local.items():
        write_stl(os.path.join(TILE_DIR, name + ".stl"), boxes)
    with zipfile.ZipFile(os.path.join(OUT, "flat_case_printable_parts.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(TILE_DIR)):
            z.write(os.path.join(TILE_DIR, fn), fn)
    shell = [b for it in tiles + battens + [e for e in extras if e.get("kind") != "backing"] for b in it["boxes"]]
    # keep the shell STL to the structural panels, feet, corners, posts
    structural = []
    for it in tiles + battens + extras:
        if it.get("kind") in ("backing",):
            continue
        structural.extend(it["boxes"])
    write_stl(os.path.join(OUT, "flat_case_assembly_shell.stl"), structural)
    write_stl(os.path.join(OUT, "flat_case_assembly_with_parts.stl"), structural + comp_boxes)

def report():
    names = {"tiles": tiles, "battens": battens, "extras": extras}
    plastic = sum(vol(it["boxes"]) for it in tiles + battens + extras)
    plastic += 9 * vol(hardware_local["standoff_post_x9"])
    plastic += 9 * vol(hardware_local["locating_pin_x9"])
    plastic += 4 * vol(hardware_local["edge_clip_x4"])
    gpu_max = (D - T) - (T + FAN_T + 8)
    print(f"Outer: {W:.0f} W x {D:.0f} D x {H:.0f} H mm  ({W*D*H/1e6:.1f} L)")
    print(f"Tiles {len(tiles)}, battens {len(battens)}, other {len(extras)}")
    print(f"Plastic ~{plastic/1000:.0f} cm3 -> ~{plastic/1000*1.27:.0f} g black/grey PETG if solid")
    mx = max(foot_sizes.items(), key=lambda kv: max(kv[1][0], kv[1][1]))
    print(f"Largest footprint {mx[0]} {mx[1][0]:.0f} x {mx[1][1]:.0f} mm")
    print(f"Board underside z {ZP_BOT:.1f}; PCB top {ZP:.1f}; floor top {ZB:.0f}")
    print(f"Cooler top {ZP+COOLER_H:.0f}; top-fan underside {ZT-FAN_T:.0f}; ceiling {ZT:.0f}")
    print(f"GPU clearance from rear bracket to front fan: {gpu_max:.0f} mm")
    print(f"PSU bay: {PSU_W:.0f} wide x {PSU_BAY_L-6:.0f} long x {PSU_H:.0f} tall, fan down, AC at the front")
    print(f"I/O opening z {IO_Z0:.1f}-{IO_Z1:.1f}, x {IO_X0:.1f}-{IO_X1:.1f}")
    print(f"Stitch holes: cat {CAT_HOLE:.2f} mm, phoenix {PHX_HOLE:.2f} mm, "
          f"front {FRONT_HOLE:.2f} mm, web {WEB:.2f} mm")
    print(f"Fans: front intakes at z {fan_front_lo[1]:.0f} and {fan_front_hi[1]:.0f}, "
          f"lid exhausts at y {fan_top_fwd[1]:.0f} and {fan_top_cpu[1]:.0f}, "
          f"rear exhaust at z {fan_rear_c[1]:.0f}")
    print(f"Front chart {front_mask.shape[1]} cells at {FRONT_PITCH:.2f} mm, "
          f"x {front_x0:.0f}-{front_x0+art_w:.0f}, z {front_z_top-art_h:.0f}-{front_z_top:.0f}")
    print("Problems:", problems if problems else "none")

# --------------------------------------------------------------------------
def render():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    # face rasters: paint every box, so the stitch holes are the unpainted cells
    def raster(path, u_axis, v_axis, boxes, u_lim, v_lim, extras_xy=(), title=""):
        ppm = 3
        wu = int((u_lim[1] - u_lim[0]) * ppm) + 1
        hv = int((v_lim[1] - v_lim[0]) * ppm) + 1
        img = np.full((hv, wu, 3), 236, np.uint8)
        def paint(b, color):
            u0, u1 = b[u_axis], b[u_axis + 3]
            v0, v1 = b[v_axis], b[v_axis + 3]
            c0 = int((u0 - u_lim[0]) * ppm)
            c1 = int((u1 - u_lim[0]) * ppm)
            r1 = int((v_lim[1] - v0) * ppm)
            r0 = int((v_lim[1] - v1) * ppm)
            c0, c1 = max(0, c0), min(wu, c1)
            r0, r1 = max(0, r0), min(hv, r1)
            if c1 > c0 and r1 > r0:
                img[r0:r1, c0:c1] = color
        for b in boxes:
            paint(b, (28, 28, 32))
        for b, col in extras_xy:
            paint(b, col)
        plt.imsave(path, img)

    shell_boxes = [b for it in tiles for b in it["boxes"]]
    left_boxes = [b for b in shell_boxes if b[3] <= T + 0.2]
    right_boxes = [b for b in shell_boxes if b[0] >= W - T - 0.2]
    # outside skin only, so the recessed inscription stays visible
    front_boxes = [b for b in shell_boxes if b[1] <= 0.05]
    front_boxes += [b for e in extras if e["id"] == "inscription"
                    for b in e["boxes"] if b[1] <= 0.05]
    rear_boxes = [b for b in shell_boxes if b[1] >= D - T - 0.2]
    top_boxes = [b for b in shell_boxes if b[2] >= ZT - 0.2]
    bot_boxes = [b for b in shell_boxes if b[5] <= ZB + 0.2]

    raster(os.path.join(PREV, "side_left_cat.png"), 1, 2, left_boxes, (0, D), (0, H))
    raster(os.path.join(PREV, "side_right_phoenix.png"), 1, 2, right_boxes, (0, D), (0, H))
    raster(os.path.join(PREV, "front.png"), 0, 2, front_boxes, (0, W), (0, H))
    raster(os.path.join(PREV, "rear.png"), 0, 2, rear_boxes, (0, W), (0, H))
    raster(os.path.join(PREV, "top.png"), 0, 1, top_boxes, (0, W), (0, D))
    # floor, with the parts drawn on top
    part_cols = []
    for n, col in (("motherboard", (40, 120, 70)), ("psu", (40, 40, 46)),
                   ("gpu", (150, 40, 40)), ("cpu_cooler", (180, 180, 186)),
                   ("ram", (40, 40, 140)), ("fans", (20, 20, 20))):
        for b in comp[n]:
            part_cols.append((b, col))
    raster(os.path.join(PREV, "floor_plan.png"), 0, 1, bot_boxes, (0, W), (0, D), part_cols)

    # 3D overview, panels as their outer plates so it stays readable
    light = np.array([-0.4, -0.6, 0.7]); light /= np.linalg.norm(light)

    def panel_plate(it):
        r = it["rect"]
        return mk(it["normal"], *{
            "x": (0, T) if it["boxes"][0][0] < W / 2 else (W - T, W),
            "y": (0, T) if it["boxes"][0][1] < D / 2 else (D - T, D),
            "z": (it["boxes"][0][2], it["boxes"][0][5]),
        }.get(it["normal"], (0, T)), r) if False else None

    fig = plt.figure(figsize=(14, 10), dpi=120)
    views = [("Front-left", 20, -125), ("Rear-right", 18, 55),
             ("Top, lid off", 90, -90), ("Front", 8, -90)]
    cols = {"gpu": (0.55, 0.12, 0.12), "motherboard": (0.12, 0.42, 0.22),
            "psu": (0.18, 0.18, 0.2), "fans": (0.08, 0.08, 0.08),
            "cpu_cooler": (0.75, 0.75, 0.78), "cpu_base": (0.6, 0.6, 0.62),
            "ram": (0.2, 0.2, 0.55), "cpu_socket": (0.8, 0.8, 0.8),
            "io_ports": (0.55, 0.55, 0.6)}
    hide = {"Top, lid off": {"top"}, "Front": set(), "Front-left": set(), "Rear-right": set()}
    for i, (title, elev, az) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        polys, fcs = [], []
        skip = hide[title]
        for it in tiles:
            key = it["id"].split("_")[0]
            if key in skip or it["id"].startswith("top") and "top" in skip:
                continue
            # one plate per tile, from its real boxes' bounds
            bb = [min(b[k] for b in it["boxes"]) for k in range(3)] + \
                 [max(b[k + 3] for b in it["boxes"]) for k in range(3)]
            cnr = corners(bb)
            shade = 0.22 if "left" in it["id"] or "right" in it["id"] else 0.30
            for idx, n in QUADS:
                sh = 0.55 + 0.45 * max(0.0, float(np.dot(n, light)))
                polys.append(cnr[idx])
                fcs.append((shade * sh, shade * sh, shade * sh + 0.02, 0.35))
        for n, vs in comp.items():
            if title == "Top, lid off" and n == "io_ports":
                pass
            for b in vs:
                cnr = corners(b)
                for idx, nrm in QUADS:
                    sh = 0.55 + 0.45 * max(0.0, float(np.dot(nrm, light)))
                    polys.append(cnr[idx])
                    base = cols[n]
                    fcs.append(tuple(min(1, v * sh) for v in base) + (0.95,))
        ax.add_collection3d(Poly3DCollection(polys, facecolors=fcs, edgecolors=(0, 0, 0, 0.05), linewidths=0.1))
        ax.set_xlim(0, W); ax.set_ylim(0, D); ax.set_zlim(0, H)
        ax.set_box_aspect((W, D, H)); ax.view_init(elev=elev, azim=az); ax.set_axis_off()
        ax.set_title(title, fontsize=11)
    fig.suptitle(f"Flat micro-ATX  {W:.0f} x {D:.0f} x {H:.0f} mm   cat left, phoenix right", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(PREV, "overview.png"))
    plt.close()

    # stitch previews at the print cell size, seam rows marked
    def save_chart(mask, stile, path, title):
        show = np.where(mask, 0, 255).astype(np.uint8)
        rgb = np.stack([show, show, show], axis=-1)
        for r in stile:
            rgb[r, :, :] = (40, 90, 220)  # the solid join bar
        big = rgb.repeat(8, 0).repeat(8, 1)
        plt.figure(figsize=(big.shape[1] / 80, big.shape[0] / 80), dpi=80)
        plt.imshow(big, interpolation="nearest")
        plt.axis("off")
        plt.title(title, fontsize=11)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
    save_chart(CAT_M, CAT_STILE, os.path.join(PREV, "chart_cat.png"),
               "Left cheek: cat. Blue rows are the solid join.")
    save_chart(PHX_M, PHX_STILE, os.path.join(PREV, "chart_phoenix.png"),
               "Right cheek: phoenix. Blue rows are the solid joins.")
    save_chart(front_mask, (), os.path.join(PREV, "chart_front.png"),
               "Front panel: the floral medallion, framed in the open area.")

def main():
    report()
    print("exporting STL...")
    export()
    print("rendering...")
    render()
    nstl = len([f for f in os.listdir(TILE_DIR) if f.endswith(".stl")])
    print(f"{nstl} STL files, zip written")
    if problems:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
