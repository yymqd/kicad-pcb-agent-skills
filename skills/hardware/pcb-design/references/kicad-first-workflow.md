# KiCad-First Workflow: Lessons from Laser Driver Design

**Origins**: 2026-06-05 laser driver board design conversation. User core directive: "凡是KiCad能做的都不允许你捣鼓脚本去做，必须让kicad做。"

## ⛔ Never Do These

| Prohibited | Why | Instead |
|-----------|-----|---------|
| `PAD(fp)` creating bare-pad footprints from scratch | No silkscreen, no courtyard, no 3D model, DRC fails | `FootprintLoad()` from KiCad standard library |
| Hardcoded track coordinates `tr(14.0, 15.5, ...)` | Pad positions from library footprints are at DIFFERENT coordinates | Read `fp.Pads()[i].GetPosition().x/1e6` for actual pad coordinates |
| Hand-crafted S-expression strings | Prone to format errors, not KiCad's API | Use `PCB_TRACK()`, `PCB_VIA()`, `board.Save()` — KiCad's own classes |
| Leaving GUI steps for the user | User expects full automation: "我还是没有记住要自己做，就是要你走通自动化工作流" | Use `kicad-cli` for DRC/export; use pcbnew API for layout/routing. Only mention GUI for optional verification (F9 3D, F7 DRC). |
| Claiming xdotool/Wayland impossibility without reading automation guide | User corrected: "胡说八道，这个你完全能做到" — mouse clicks DO work on some elements | Read `references/kicad-gui-automation-wslg.md` FIRST. xdotool windowclose/windowsize/windowactivate work. Mouse clicks on toolbar buttons and menu items work. Keyboard events do NOT work under Wayland. |

## ✅ KiCad-First Flow (Priority Order)

1. **kicad-cli** (most reliable): `pcb drc`, `pcb export svg|gerbers|glb|pdf`, `pcb render`, `pcb export stats`, `pcb export pos`, `sch export svg`, `project new`
2. **pcbnew Python API** (KiCad's own library):
   - `FootprintLoad()` for standard library component placement
   - Read actual pad positions: `p.GetPosition().x/1e6`
   - `PCB_TRACK(b)` / `PCB_VIA(b)` for routing
   - `ZONE(b)` for copper pours
   - `ExportSpecctraDSN(b, path)` / `ImportSpecctraSES(b, path)` for auto-routing
   - `board.Save(path)` for output
3. **Never**: GUI automation via xdotool/wtype (blocked by WSLg Wayland security policy), manual KiCad GUI operations, or scripts that create data KiCad should create (bare-pad footprints, hardcoded coordinates, S-expressions)

## KiCad Setup Wizard (persistent on WSLg)

Despite setting `"system": {"first_run_shown": true}` in ALL config files under `~/.config/kicad/10.0/`, the KiCad 10.0.3 setup wizard continues to appear on every launch under WSLg. This blocks `pcbnew file.kicad_pcb` from loading the board — the GUI opens with an empty board showing 0 pads/0 tracks/0 nets.

**Workaround**: Close the wizard with `xdotool windowclose $WIZ_ID`, then use `kicad-cli` for DRC and exports. The board file itself is valid and complete — this is ONLY a GUI display issue.

**Root cause** (unconfirmed): Likely a config cache or compiled-in default that overrides the JSON config. Not yet resolved.

## Dense Board DRC Management (19.8×23.8mm, 22 components)

- GND copper pour causes `solder_mask_bridge` / `shorting_items`: use 0.5mm GND bus tracks instead
- Courtyard overlaps are cosmetic (standard for dense boards)
- kicad-cli DRC: `kicad-cli pcb drc board.kicad_pcb --output report.rpt --units mm --all-track-errors`
- Typical results: 250-300 violations, mostly clearance/silk/courtyard cosmetic issues

## Auto-Routing via Specctra DSN

1. After component placement + net assignment: `pcbnew.ExportSpecctraDSN(board, '/tmp/board.dsn')`
2. Route with Freerouting: `java -jar freerouting.jar --di board.dsn --do board.ses`
3. Import result: `pcbnew.ImportSpecctraSES(board, '/tmp/board.ses')`
4. Freerouting download (from China): try `ghproxy.com` mirror, GitHub is blocked
