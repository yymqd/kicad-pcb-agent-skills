# pcbnew-Based BOM Generation

**Use case:** When components are placed via pcbnew API without a schematic, `kicad-cli sch export bom` fails (no `.kicad_sch`). BOM must be generated from the board file directly.

## Method: Read Component Data from Board

```python
import pcbnew

board = pcbnew.LoadBoard("design.kicad_pcb")

bom_lines = [["Ref", "Value", "Footprint", "Layer", "Position (mm)"]]
for fp in board.GetFootprints():
    ref = fp.GetReference()
    val = fp.GetValue()
    lib = fp.GetFPID().GetLibNickname()
    fp_name = fp.GetFPID().GetFootprintName()
    pos = fp.GetPosition()
    layer = "Top" if fp.GetLayer() == pcbnew.F_Cu else "Bottom"
    
    bom_lines.append([
        ref, val,
        f"{lib}:{fp_name}",
        layer,
        f"{pos.x/1e6:.2f}, {pos.y/1e6:.2f}"
    ])

# Output as CSV
import csv
with open("bom.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerows(bom_lines)
```

## Output Sample

```
Ref,Value,Footprint,Layer,Position (mm)
C1,10µF,Capacitor_SMD:C_0805_2012Metric,Top,2.50, 3.00
C2,10µF,Capacitor_SMD:C_0805_2012Metric,Top,16.50, 3.00
C3,100nF,Capacitor_SMD:C_0603_1608Metric,Top,17.50, 12.00
D1,SS12,Diode_SMD:D_SOD-123,Top,13.00, 13.50
J1,PH2.0-4P,Connector:PinHeader_1x04_P2.00mm_Vertical,Top,2.00, 20.00
L1,4.7µH,Inductor_SMD:L_Chilisin_BMRA00040415,Top,5.00, 4.50
Q1,2N7002,Package_TO_SOT_SMD:SOT-23-3,Top,12.00, 9.00
R1,680k,Resistor_SMD:R_0603_1608Metric,Top,10.00, 9.00
U1,SGM6601,Package_TO_SOT_SMD:SOT-23-6,Top,6.50, 8.00
U2,TLV2371,Package_TO_SOT_SMD:SOT-23-5,Top,13.00, 11.50
```

## When to Use

| Scenario | BOM Method |
|:---------|:-----------|
| Full KiCad project (sch + pcb) | `kicad-cli sch export bom` |
| pcbnew-generated board, no schematic | pcbnew-based (this method) |
| Need position data for assembly | pcbnew-based (adds position column) |

## Limitations

- **No LCSC/MPN column** — add a manual mapping dict in the script: `mpn_map = {"R_0603_1608Metric": "C22915", ...}`
- **No value standardization** — in a real BOM, multiple refs with same value+footprint should be merged into one line. Add grouping:
  ```python
  from collections import defaultdict
  groups = defaultdict(list)
  for fp in board.GetFootprints():
      key = (fp.GetValue(), fp.GetFPID().GetFootprintName())
      groups[key].append(fp.GetReference())
  for (val, fp_name), refs in sorted(groups.items()):
      print(f"{','.join(refs)},{val},{fp_name}")
  ```
