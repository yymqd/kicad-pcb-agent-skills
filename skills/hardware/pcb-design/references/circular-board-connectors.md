# Circular Board Edge Connectors (Ø≤20mm)

> Technique verified on the 520nm 80mA laser driver (Ø14mm, 23 components, 2026-06-06).

## Problem
Standard pin headers (PH2.0, PH2.54) are too large for sub-20mm circular boards. A 1×4 PH2.0 header is ~10×5mm — up to 35% of the total board area on a Ø14mm board.

## Solution: TestPoint_Pad_D1.5mm

KiCad's `TestPoint.pretty` library provides bare circular copper pads (no plastic body) that serve as wire-soldering terminals:

```python
tp1 = place(board, "TestPoint.pretty", "TestPoint_Pad_D1.5mm",
            "TP1", "VIN", 7.0, 1.5)   # at top of board
tp2 = place(board, "TestPoint.pretty", "TestPoint_Pad_D1.5mm",
            "TP2", "GND", 7.0, 12.5)  # at bottom
```

### Advantages
| Factor | Pin Header | TestPoint Pad |
|:-------|:-----------|:--------------|
| Area per pin | ~12mm² | ~1.8mm² |
| Height | 5-8mm | <0.5mm (copper only) |
| Cost | ¥0.3-1/pin | included in PCB |
| Soldering | needs connector | direct wire solder |

### Layout Pattern (ø14mm board)
```
         TP1(VIN) @ top
             |
    TP3(TTL) ─┼─ TP4(LD_OUT)
  @ left      |      @ right
             |
         TP2(GND) @ bottom
```

Place test points at the board edge (±0.5mm from Edge.Cuts circle) so wires can exit radially. Each 1.5mm pad can handle AWG24-30 wire.

### Wire Soldering Guide
1. Tin the test point with solder
2. Strip 2mm of wire insulation, tin the wire
3. Touch wire to pad, apply iron for 2-3 seconds
4. Inspect for cold joints (the pad is plated, no solder mask on top)

### Limitations
- Not suitable for repeated plug/unplug cycles (use a connector instead)
- Vibration-sensitive applications need strain relief (glue wire to board)
- Current rating: ~1A continuous per pad (enough for 80mA LD driver)

## KiCad Library Path
```
/usr/share/kicad/footprints/TestPoint.pretty/
  TestPoint_Pad_D1.0mm.kicad_mod
  TestPoint_Pad_D1.5mm.kicad_mod    ← recommended for Ø14mm boards
  TestPoint_Pad_D2.0mm.kicad_mod    ← for heavier wire
  TestPoint_Pad_D3.0mm.kicad_mod
```
