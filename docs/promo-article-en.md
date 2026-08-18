# Let AI Design Your PCB — KiCad PCB Agent Skills Is Now Open Source!

> **In one sentence:** Describe your circuit in natural language, and an AI Agent handles the entire flow — schematic → layout → routing → DRC verification → Gerber export.

## 🎯 What Is This

A collection of **KiCad PCB design automation skills for AI Agents (Hermes Agent)**. It turns requests like *"I want a 520nm laser diode constant-current driver, Ø14mm double-sided board"* into PCB files ready to send to JLCPCB.

The core value isn't just "AI generates a PCB file" — it's a **reusable engineering methodology**:

- **Three-pipeline phase switching**: Design (kcaa multi-layer PNS routing) → Verification (kicad-cli DRC) → Export (Gerber/drill/3D)
- **Mandatory audit discipline**: every step is independently re-verified; you don't proceed until the audit passes
- **Real battle-tested lessons**: B.Cu SVG color invisibility, silkscreen text milled off the board, SPICE simulation traps, Freerouting rescues on dense boards... all hard-won experience

## 🏗️ Three-Pipeline Architecture

```
Design phase (Phase 0-4)  → Pipeline C (kcaa): multi-layer PNS autorouting (A* + auto vias)
                            Pipeline B (mixelpixx): single-layer routing + JLCPCB integration
Verification phase (Phase 5) → Pipeline A (kicad-cli): authoritative DRC
Export phase (Phase 6)    → Pipeline A (kicad-cli): Gerber / drill / 3D render
```

**Core principle: switch pipelines by phase — never mix them.**

## 📦 6 Skills Included

| Skill | Responsibility |
|---|---|
| `pcb-design` | Umbrella master Skill: full flow requirements → selection → schematic → layout → routing → verification → export |
| `kicad-export-reporting` | SVG routing maps / 3D renders / Word design reports (incl. SVG color fixes) |
| `kicad-ngspice-quick-sim` | SPICE via KiCad's bundled ngspice.dll (DC/AC/sweep) |
| `pcb-autorouting` | Freerouting autorouting (DSN → Freerouting → SES) |
| `pcb-silk-text-audit` | Silkscreen text bounds audit (bbox r_max, not center point) |
| `hermes-kicad-workflow` | Skill packaging/migration to a new machine |

## 🔧 Proven on Real Projects

This is not a paper design — it has run on actual hardware:

- **520nm laser diode constant-current driver** (Ø14mm double-sided, 21 components)
- Manual routing repeatedly hit shorting/crossing dead-ends → Freerouting solved it in one pass (**shorting=0, crossing=0, unconnected=0, score 994.78**)
- DRC fully passed (JLC 0.1mm fabrication standard)
- Complete deliverables: 15-chapter Word design report + Gerber + drill + 3D renders + routing maps

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/yymqd/kicad-pcb-agent-skills.git
# 2. Install into Hermes
mkdir -p ~/.hermes/skills/hardware
cp -r kicad-pcb-agent-skills/skills/hardware/* ~/.hermes/skills/hardware/
# 3. Start chatting
hermes  # then say: "help me design a XX circuit"
```

Requires KiCad 10.0+ (Windows or WSL). See `docs/environment-setup.md` for pipeline installation.

## 🤝 Contribute Together

This is the **open-source collaboration edition**: all paths are anonymized to placeholders, so anyone can adapt it to their own environment.

Welcome to:
- Submit your tested new case studies (format in CONTRIBUTING.md)
- Adapt for different KiCad versions (7/8/9/10 differences are the biggest pitfall)
- Report pipeline issues (label A/B/C)

**License: MIT**

---

*Project: https://github.com/yymqd/kicad-pcb-agent-skills*
*Mirror (China): https://cnb.cool/cnb-qdu/kicad-pcb-agent-skills*
