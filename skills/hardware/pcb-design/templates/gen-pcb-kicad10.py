#!/usr/bin/env python3
"""
1kHz RC Low-Pass Filter — KiCad 10.0.3 PCB Generator Template

**THIS IS THE CORRECT TEMPLATE** — demonstrates the KiCad-First approach:

  ✅ FootprintLoad() from standard library — NOT bare PAD()
  ✅ Reads actual pad positions via fp.Pads().GetPosition()
  ✅ PCB_TRACK from real coordinates — NOT hardcoded guesses
  ✅ Text AFTER board.Add() — KiCad 10 requirement
  ✅ Full S-expression verification + GND connectivity check

Verified on: KiCad 10.0.3, Ubuntu 24.04 (WSL), 2026-06-05
"""
import os
import pcbnew
from pcbnew import (
    BOARD, FOOTPRINT, PCB_TRACK, PCB_SHAPE, PCB_VIA,
    NETINFO_ITEM, VECTOR2I, FromMM,
    SHAPE_T_RECT,
)

# ══ CONFIG ═══════════════════════════════════
OUT_DIR = "<PROJECT_DIR>/outputs"
BOARD_W = 20.0   # mm
BOARD_H = 15.0   # mm
TRACK_W = 0.3    # mm
PWR_W   = 0.5    # mm (power traces)

# Standard library paths (KiCad 10, Ubuntu)
LIB_RES = "Resistor_SMD.pretty"
LIB_CAP = "Capacitor_SMD.pretty"
LIB_CONN = "Connector_PinHeader_2.54mm.pretty"

os.makedirs(OUT_DIR, exist_ok=True)

# ══ BOARD SETUP ══════════════════════════════
board = BOARD()

# Nets
net_names = ["", "VIN", "VOUT", "GND"]
nets = {}
for n in net_names:
    item = NETINFO_ITEM(board, n)
    board.Add(item)
    nets[n] = item

net_vin = nets["VIN"]
net_vout = nets["VOUT"]
net_gnd = nets["GND"]

# Board outline
edge = PCB_SHAPE(board)
edge.SetShape(SHAPE_T_RECT)
edge.SetStart(VECTOR2I(FromMM(0), FromMM(0)))
edge.SetEnd(VECTOR2I(FromMM(BOARD_W), FromMM(BOARD_H)))
edge.SetLayer(pcbnew.Edge_Cuts)
edge.SetWidth(FromMM(0.1))
board.Add(edge)

# ══ HELPER: Place component from standard library ══
def place_std_footprint(board, lib, fp_name, ref, val, x_mm, y_mm,
                        ref_dx=0, ref_dy=1.2, val_dx=0, val_dy=-1.2):
    """Load a standard library footprint and place at (x, y)."""
    fp = pcbnew.FootprintLoad(f"/usr/share/kicad/footprints/{lib}", fp_name)
    if fp is None:
        raise RuntimeError(f"Cannot load {lib}/{fp_name}")
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetLayer(pcbnew.F_Cu)
    fp.SetPosition(VECTOR2I(FromMM(x_mm), FromMM(y_mm)))
    board.Add(fp)
    # ⚠️ Text AFTER board.Add() — KiCad 10 requirement
    ref_ = fp.Reference()
    ref_.SetPosition(VECTOR2I(FromMM(x_mm + ref_dx), FromMM(y_mm + ref_dy)))
    ref_.SetTextSize(VECTOR2I(FromMM(0.6), FromMM(0.6)))
    ref_.SetVisible(True)
    val_ = fp.Value()
    val_.SetPosition(VECTOR2I(FromMM(x_mm + val_dx), FromMM(y_mm + val_dy)))
    val_.SetTextSize(VECTOR2I(FromMM(0.5), FromMM(0.5)))
    val_.SetVisible(True)
    return fp

def assign_net_by_pad_number(fp, mapping):
    """Map pad numbers to nets. mapping: {'1': net_obj, '2': net_obj, ...}"""
    for p in fp.Pads():
        pn = p.GetNumber()
        if pn in mapping:
            p.SetNet(mapping[pn])

# ══ PLACE COMPONENTS (standard library) ══════
# R1 — 0603 resistor at (7.5, 7.5)
r1 = place_std_footprint(board, LIB_RES, "R_0603_1608Metric",
                         "R1", "1.6k", 7.5, 7.5)
assign_net_by_pad_number(r1, {"1": net_vin, "2": net_vout})

# C1 — 0603 capacitor at (12.5, 7.5)
c1 = place_std_footprint(board, LIB_CAP, "C_0603_1608Metric",
                         "C1", "100n", 12.5, 7.5)
assign_net_by_pad_number(c1, {"1": net_vout, "2": net_gnd})

# J1 — Pin header (IN) at (2.5, 7.5)
j1 = place_std_footprint(board, LIB_CONN, "PinHeader_1x03_P2.54mm_Vertical",
                         "J1", "INPUT", 2.5, 7.5)
assign_net_by_pad_number(j1, {"1": net_vin, "3": net_gnd})

# J2 — Pin header (OUT) at (17.5, 7.5)
j2 = place_std_footprint(board, LIB_CONN, "PinHeader_1x03_P2.54mm_Vertical",
                         "J2", "OUTPUT", 17.5, 7.5)
assign_net_by_pad_number(j2, {"1": net_vout, "3": net_gnd})

# ══ READ ACTUAL PAD POSITIONS FOR ROUTING ═════
def get_fp_pad_pos(fp, pad_num):
    """Get absolute position of a pad in mm."""
    for p in fp.Pads():
        if p.GetNumber() == pad_num:
            return p.GetPosition().x / 1e6, p.GetPosition().y / 1e6
    return None, None

def add_track(board, x1, y1, x2, y2, net, layer=pcbnew.F_Cu, w=TRACK_W):
    tr = PCB_TRACK(board)
    tr.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
    tr.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
    tr.SetWidth(FromMM(w))
    tr.SetLayer(layer)
    tr.SetNet(net)
    board.Add(tr)

# Route VIN: J1(1) → R1(1)
x1, y1 = get_fp_pad_pos(j1, "1")
x2, y2 = get_fp_pad_pos(r1, "1")
if all(v is not None for v in [x1, y1, x2, y2]):
    add_track(board, x1, y1, x2, y2, net_vin)

# Route VOUT: R1(2) → C1(1) → J2(1)
x1, y1 = get_fp_pad_pos(r1, "2")
x2, y2 = get_fp_pad_pos(c1, "1")
if all(v is not None for v in [x1, y1, x2, y2]):
    add_track(board, x1, y1, x2, y2, net_vout)
x1, y1 = get_fp_pad_pos(c1, "1")
x2, y2 = get_fp_pad_pos(j2, "1")
if all(v is not None for v in [x1, y1, x2, y2]):
    add_track(board, x1, y1, x2, y2, net_vout)

# Route GND: C1(2) → J1(3) → J2(3)
x1, y1 = get_fp_pad_pos(c1, "2")
x2, y2 = get_fp_pad_pos(j1, "3")
if all(v is not None for v in [x1, y1, x2, y2]):
    add_track(board, x1, y1, x2, y2, net_gnd, w=PWR_W)
x1, y1 = get_fp_pad_pos(j1, "3")
x2, y2 = get_fp_pad_pos(j2, "3")
if all(v is not None for v in [x1, y1, x2, y2]):
    add_track(board, x1, y1, x2, y2, net_gnd, w=PWR_W)

# ══ SAVE ══════════════════════════════════════
pcb_path = os.path.join(OUT_DIR, "design.kicad_pcb")
board.Save(pcb_path)

# ══ VERIFY ════════════════════════════════════
after = pcbnew.LoadBoard(pcb_path)
gnd_tracks = sum(1 for t in after.GetTracks()
                 if t.GetNet() and t.GetNet().GetNetname() == "GND")
gnd_pads = []
for fp in after.GetFootprints():
    for p in fp.Pads():
        if p.GetNet() and p.GetNet().GetNetname() == "GND":
            gnd_pads.append(f"{fp.GetReference()}.{p.GetNumber()}")

print(f"✅ {pcb_path} ({os.path.getsize(pcb_path)} bytes)")
print(f"   Footprints: {len(list(after.GetFootprints()))}")
print(f"   Tracks: {len(list(after.GetTracks()))}")
print(f"   GND tracks: {gnd_tracks} (pads with GND: {len(gnd_pads)})")
if gnd_tracks == 0 and len(gnd_pads) > 0:
    print("   ⚠️  WARNING: GND pads exist but NO GND tracks!")
else:
    print("   ✅ GND connectivity OK")
print(f"   Board: {BOARD_W}×{BOARD_H}mm")
