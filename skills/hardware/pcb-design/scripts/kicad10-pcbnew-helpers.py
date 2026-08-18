#!/usr/bin/env python3
"""
KiCad 10.0.3 pcbnew Helper Functions
Reusable boilerplate for generating PCBs programmatically.
Usage: copy into your design script, or import directly.

All functions use KiCad 10 API (int layer IDs, PAD(fp) parent, LSET.AddLayerSet).
"""
import pcbnew
from pcbnew import (
    BOARD, FOOTPRINT, PCB_TRACK, PCB_SHAPE, PAD,
    NETINFO_ITEM, VECTOR2I, FromMM, SHAPE_T_RECT,
)

# ══ Net Setup ══

def create_nets(board, names):
    """Register nets on board. Returns dict {name: NETINFO_ITEM}."""
    nets = {}
    for name in names:
        item = NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    return nets

# ══ Footprint Helpers ══

def add_smd_pad(fp, num, x_mm, y_mm, w_mm, h_mm, net,
                shape=pcbnew.PAD_SHAPE_RECT):
    """Add SMD pad to footprint. x,y relative to footprint center."""
    p = PAD(fp)
    p.SetNumber(str(num))
    p.SetShape(shape)
    p.SetSize(VECTOR2I(FromMM(w_mm), FromMM(h_mm)))
    p.SetPosition(VECTOR2I(FromMM(x_mm), FromMM(y_mm)))
    p.SetLayerSet(pcbnew.LSET.FrontMask())
    p.SetNet(net)
    fp.Add(p)

def add_tht_pad(fp, num, x_mm, y_mm, dia_mm, drill_mm, net):
    """Add through-hole pad. Use for connectors and mounting holes."""
    p = PAD(fp)
    p.SetNumber(str(num))
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(VECTOR2I(FromMM(dia_mm), FromMM(dia_mm)))
    p.SetDrillSize(VECTOR2I(FromMM(drill_mm), FromMM(drill_mm)))
    p.SetPosition(VECTOR2I(FromMM(x_mm), FromMM(y_mm)))
    ls = pcbnew.LSET.AllCuMask()
    ls.AddLayerSet(pcbnew.LSET.AllTechMask())
    p.SetLayerSet(ls)
    p.SetNet(net)
    fp.Add(p)

# ══ Component Patterns ══

def add_0603(board, ref, val, cx_mm, cy_mm, net1, net2, nets,
             rotation_deg=0):
    """Add 0603 resistor/capacitor footprint.
    rotation_deg: rotation in degrees. KiCad 10 uses EDA_ANGLE, not FromDegrees()."""
    from pcbnew import EDA_ANGLE
    fp = FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetLayer(pcbnew.F_Cu)
    fp.SetPosition(VECTOR2I(FromMM(cx_mm), FromMM(cy_mm)))
    if rotation_deg:
        fp.SetOrientation(EDA_ANGLE(rotation_deg, 1))  # 1 = DEGREES_T
    pad_pitch = 0.75
    add_smd_pad(fp, 1, -pad_pitch, 0, 1.2, 0.7, nets[net1])
    add_smd_pad(fp, 2, pad_pitch, 0, 1.2, 0.7, nets[net2])
    board.Add(fp)
    return fp

def add_connector(board, ref, val, cx_mm, cy_mm, pins, nets,
                  pitch=2.0, pad_w=1.5, pad_h=2.5):
    """Add SMD connector footprint (PH2.0 or ZH1.5 series).
    pins: list of [(net_name, ref_des), ...]"""
    fp = FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetLayer(pcbnew.F_Cu)
    fp.SetPosition(VECTOR2I(FromMM(cx_mm), FromMM(cy_mm)))
    npins = len(pins)
    for i, (net_name, refn) in enumerate(pins):
        px = -(npins * pitch) / 2 + i * pitch + pitch / 2
        add_smd_pad(fp, refn, px, 0, pad_w, pad_h,
                    nets[net_name], pcbnew.PAD_SHAPE_ROUNDRECT)
    board.Add(fp)
    return fp

def add_sot23_3(board, ref, val, cx_mm, cy_mm, pin_nets, nets,
                rotation_deg=0):
    """SOT-23-3 (3-pin, e.g. MOSFET).
    pin_nets: [(net_name, x_offset, y_offset), ...]
    Pitch=0.95mm, row half-height=0.475mm.
    rotation_deg: rotation in degrees. KiCad 10 uses EDA_ANGLE."""
    from pcbnew import EDA_ANGLE
    fp = FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetLayer(pcbnew.F_Cu)
    fp.SetPosition(VECTOR2I(FromMM(cx_mm), FromMM(cy_mm)))
    if rotation_deg:
        fp.SetOrientation(EDA_ANGLE(rotation_deg, 1))
    sp = 0.95
    for i, (n, dx, dy) in enumerate(pin_nets):
        add_smd_pad(fp, str(i+1), dx*sp, dy*sp, 0.6, 0.5, nets[n])
    board.Add(fp)
    return fp

# ══ Board Outline & Mounting Holes ══

def add_board_outline(board, w_mm, h_mm):
    """Add rectangular board outline on Edge.Cuts layer."""
    edge = PCB_SHAPE(board)
    edge.SetShape(SHAPE_T_RECT)
    edge.SetStart(VECTOR2I(FromMM(0), FromMM(0)))
    edge.SetEnd(VECTOR2I(FromMM(w_mm), FromMM(h_mm)))
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetWidth(FromMM(0.15))
    board.Add(edge)

def add_mounting_holes(board, w_mm, h_mm, hole_dia_mm, spacing_x, spacing_y):
    """Add 4× mounting THT pads at corners."""
    margin_x = (w_mm - spacing_x) / 2
    margin_y = (h_mm - spacing_y) / 2
    from pcbnew import NETINFO_ITEM
    no_net = NETINFO_ITEM(board, "")
    board.Add(no_net)
    for dx, dy in [(0,0), (1,0), (0,1), (1,1)]:
        hx = margin_x + dx * spacing_x
        hy = margin_y + dy * spacing_y
        fh = FOOTPRINT(board)
        fh.SetReference(f"MT{dx}{dy}")
        fh.SetValue("MOUNT")
        fh.SetLayer(pcbnew.F_Cu)
        fh.SetPosition(VECTOR2I(FromMM(hx), FromMM(hy)))
        add_tht_pad(fh, "1", 0, 0, hole_dia_mm, hole_dia_mm, no_net)
        board.Add(fh)

# ══ Tracks ══

def add_track(board, x1, y1, x2, y2, net, layer=pcbnew.F_Cu, width=0.3):
    """Add a track segment between two points."""
    tr = PCB_TRACK(board)
    tr.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
    tr.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
    tr.SetWidth(FromMM(width))
    tr.SetLayer(layer)
    tr.SetNet(net)
    board.Add(tr)

# ══ Save & Verify ══

def verify_nets_in_sexpr(pcb_path, net_names):
    """Count net occurrences in S-expression file."""
    with open(pcb_path, 'r') as f:
        content = f.read()
    for name in net_names:
        count = content.count(f'(net "{name}")')
        print(f"  Net '{name}': {count}")
    return content
