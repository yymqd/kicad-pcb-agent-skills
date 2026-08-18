# KiCad CLI DRC + Specctra DSN Auto-Routing

## kicad-cli pcb drc

KiCad 10 CLI has a native DRC command (not GUI-only).

### Basic Usage
```bash
kicad-cli pcb drc board.kicad_pcb --output drc_report.rpt --units mm --all-track-errors
```

### All Options
```
pcb drc [--help] [--output OUTPUT_FILE] [--define-var KEY=VALUE]...
         [--format FORMAT] [--all-track-errors] [--schematic-parity]
         [--units UNITS] [--severity-all] [--severity-error]
         [--severity-warning] [--severity-exclusions]
         [--exit-code-violations] [--refill-zones] [--save-board]
         INPUT_FILE
```

| Option | Purpose |
|--------|---------|
| `--output FILE` | Report output path |
| `--format report` | Text report (default) |
| `--format json` | JSON format (machine-readable) |
| `--all-track-errors` | Report all errors per track (not just first) |
| `--units mm|in|mils` | Measurement units |
| `--severity-error` | Report only errors |
| `--severity-all` | Report errors + warnings |
| `--severity-warning` | Report only warnings |
| `--exit-code-violations` | Return nonzero exit if violations found |
| `--refill-zones` | Refill copper zones before checking |
| `--save-board` | Save board after DRC (requires --refill-zones) |
| `--schematic-parity` | Cross-check PCB against schematic |

### Interpretation of Common Violations

| Violation | Likely Cause | Fix |
|-----------|-------------|-----|
| `solder_mask_bridge` | GND copper pour touches non-GND pad | Adjust zone clearance or shrink pour area |
| `shorting_items` | Track crosses pad of different net | Move track or use B.Cu via |
| `clearance` | Track too close to pad/track | Increase spacing or narrow track |
| `unconnected_items` | Track endpoint not on pad center | Use actual pad coordinates |
| `courtyards_overlap` | Component courtyard boxes overlap | Accepted in dense boards (<20mm) |
| `hole_clearance` | Mounting hole too close to component | Move component or hole |
| `track_dangling` | Track end not connected | Route to pad or delete orphan segment |

## Specctra DSN/SES Auto-Routing

KiCad supports the industry-standard Specctra auto-router interface.

### Workflow

1. **Place components** (via pcbnew FootprintLoad + manual positioning)
2. **Assign nets** (SetNet on each pad)
3. **Export DSN** (holds component positions + net connectivity):
   ```python
   import pcbnow
   board = pcbnew.LoadBoard("board.kicad_pcb")
   pcbnew.ExportSpecctraDSN(board, "/tmp/board.dsn")
   ```
4. **Run auto-router** (e.g., Freerouting):
   ```bash
   java -jar freerouting-1.9.0.jar --di /tmp/board.dsn --do /tmp/board.ses
   ```
5. **Import SES** (routed result):
   ```python
   pcbnew.ImportSpecctraSES(board, "/tmp/board.ses")
   board.Save("board.kicad_pcb")
   ```

### Freerouting Installation

```bash
# Download JAR (use GitHub proxy in China)
wget https://ghproxy.com/https://github.com/freerouting/freerouting/releases/download/v1.9.0/freerouting-1.9.0.jar

# Requires Java
sudo apt-get install -y default-jre

# Run
java -jar freerouting-1.9.0.jar --di board.dsn --do board.ses
```
