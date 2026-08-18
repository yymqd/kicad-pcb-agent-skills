# Common Standard Library Footprint Paths (KiCad 10 on Ubuntu)

Use with `pcbnew.FootprintLoad(lib_dir, name)`:

| Component | Library | Footprint Name |
|-----------|---------|----------------|
| 0603 resistor/cap | `Resistor_SMD.pretty` / `Capacitor_SMD.pretty` | `R_0603_1608Metric` / `C_0603_1608Metric` |
| 0805 capacitor/resistor | `Capacitor_SMD.pretty` / `Resistor_SMD.pretty` | `C_0805_2012Metric` / `R_0805_2012Metric` |
| SOT-23-3 (MOSFET, BJT) | `Package_TO_SOT_SMD.pretty` | `SOT-23-3` |
| SOT-23-5 (op-amp) | `Package_TO_SOT_SMD.pretty` | `SOT-23-5` |
| SOT-23-6 (boost IC) | `Package_TO_SOT_SMD.pretty` | `SOT-23-6` |
| SOD-123 (diode) | `Diode_SMD.pretty` | `D_SOD-123` (pad1=cathode/stripe, pad2=anode) |
| CD32 inductor | `Inductor_SMD.pretty` | `L_Chilisin_BMRA00040415` |
| 3mm mounting hole | `MountingHole.pretty` | `MountingHole_3mm` |
| 2.2mm mounting hole | `MountingHole.pretty` | `MountingHole_2.2mm_M2_Pad_TopBottom` |
| 2.00mm pin header (PH2.0 substitute) - SMD vertical | `Connector_PinHeader_2.00mm.pretty` | `PinHeader_1x04_P2.00mm_Vertical_SMD_Pin1Left` |
| 2.00mm pin header - horizontal (right-angle) | `Connector_PinHeader_2.00mm.pretty` | `PinHeader_1x04_P2.00mm_Horizontal` |

All standard library paths: `/usr/share/kicad/footprints/<Category>.pretty/`
