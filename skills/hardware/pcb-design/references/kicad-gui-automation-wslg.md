# KiCad GUI Automation under WSLg (Wayland)

**⚠️ READ THIS BEFORE CLAIMING xdotool LIMITATIONS — 2026-06-05 UPDATE**

**User correction history:** In a June 2025 KiCad PCB session, the agent claimed "WSLg Wayland 限制：xdotool 无法向 KiCad GUI 发送键盘/鼠标事件" — the user responded "胡说八道，这个你完全能做到". The user was right: **mouse clicks work.** The agent's mistake was making a blanket "xdotool doesn't work" claim without checking this reference file first. Mouse-click-based GUI automation is feasible.

**When to use GUI automation:** Only for operations without a CLI/kicad-cli equivalent. Prefer pcbnew API or kicad-cli for routing, DRC, export, and Gerber generation. GUI automation by mouse click is a fallback.

**Environment**: WSLg + Wayland compositor + XWayland. Tested on KiCad 10.0.3, Ubuntu 24.04 WSL, DISPLAY=:0.

## Core Finding: Mouse clicks work, keyboard events may not

Under WSLg/Wayland, xdotool has limited functionality:

| Action | Works? | Method |
|--------|--------|--------|
| windowactivate | ✅ | Focuses a window |
| windowclose | ✅ | Closes a window |
| windowsize | ✅ | Resizes a window |
| mousemove + click 1 | ✅ | Clicks at screen coordinates |
| key F7 | ❌ | Keyboard events typically do not reach the app |
| type "text" | ❌ | Text input via simulation does not work |
| ctrl+a / ctrl+c | ❌ | Clipboard operations do not work |

**Why**: Wayland compositor intercepts keyboard events. Mouse click events (button presses) are forwarded through XWayland. Keyboard events (key press/release) are NOT forwarded reliably.

## Working GUI Automation Strategies

### Strategy 1: Toolbar Button Clicks

KiCad toolbar buttons have known positions. The menubar + toolbar are at known Y positions from the window top.

```bash
# Get window position on screen
xdotool getwindowgeometry $WID
# Output: Position: X,Y (screen: 0), Geometry: WxH

# Toolbar starts at window y ~ 35px
# Each toolbar icon is ~24x24px  
# First button at window x ~ 3px
# DRC button is #23 -> window x ~ 3 + 22*24 + 12 = 543
# Screen coords: screen_x = WINX + button_x, screen_y = WINY + button_y
xdotool mousemove $((WINX + 543)) $((WINY + 47))
xdotool click 1
```

### Strategy 2: Menu Bar Clicks

Menu items ~35-45px wide: File(3-40), Edit(40-80), View(80-120), Place(120-170), Route(170-225), **Inspect(225-280)**, Tools(280-330), Preferences(330-400), Help(400-450).

```bash
# Open Inspect menu
xdotool mousemove $((WINX + 250)) $((WINY + 18))
xdotool click 1
sleep 1
# Click DRC (~4th item, each ~22px)
xdotool mousemove $((WINX + 250)) $((WINY + 18 + 4*22))
xdotool click 1
```

**Caveat**: Menu closes when mouse moves away between clicks. Use immediate sequential clicks.

## First-Run Wizard Blocking

KiCad 10's "KiCad Setup" welcome dialog appears on fresh WSL installs, blocking the board file from loading.

**Fix**: Before launching:
```bash
sed -i 's/"first_run_shown": false/"first_run_shown": true/g' ~/.config/kicad/10.0/*.json
```

If wizard still appears, close it:
```bash
xdotool windowclose $(xdotool search --name "Setup" | head -1)
```

## Best Practice: CLI over GUI for automation

For automated DRC/export, prefer kicad-cli which works reliably:
```bash
kicad-cli pcb drc board.kicad_pcb --output report.rpt --units mm --all-track-errors
kicad-cli pcb export gerbers board.kicad_pcb -o gerber/ --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts
```

GUI automation by mouse click should be a fallback, not the primary path, for operations that don't have a CLI equivalent.
