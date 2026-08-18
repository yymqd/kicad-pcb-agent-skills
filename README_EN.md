# KiCad PCB Agent Skills

**English | [中文](README.md)**

A collection of **KiCad PCB design automation skills for AI Agents (Hermes Agent)** — turning natural-language requirements into production-ready PCB files.

> This repository is the open-source collaboration edition of an "AI-driven PCB design workflow". Core experience comes from real projects (Ø14mm double-sided laser driver, etc.), hardened through failures and fixes, and packaged as **Hermes Agent Skills**.

## 🎯 Core Architecture: Three Pipelines

```
┌──────────────────────────────────────────────────────────┐
│              pcb-design (umbrella master Skill)          │
│   Entry point · Mandatory rules · Phase 0-9 gates · 19+ refs │
└──────────────────┬───────────────────────────────────────┘
                   │ routed by phase
   ┌───────────────┼───────────────────┐
   ▼               ▼                   ▼
┌────────┐   ┌──────────────┐   ┌───────────────┐
│Pipeline C    │Pipeline B    │   │Pipeline A     │
│kcaa     │   │mixelpixx     │   │kicad-cli      │
│(MCP)    │   │(MCP)         │   │(CLI+pcbnew)   │
│Design   │   │Design        │   │Verify/Export  │
│Multi-layer PNS │Single-layer+JLCPCB │DRC/Gerber/3D │
└────────┘   └──────────────┘   └───────┬───────┘
                                        │ artifacts
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
             ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
             │ kicad-export │   │ pcb-         │   │ pcb-         │
             │ -reporting   │   │ autorouting  │   │ silk-text-   │
             │ Graphics/Docs│   │ Freerouting  │   │ audit        │
             └──────────────┘   └──────────────┘   └──────────────┘
             ┌──────────────┐   ┌──────────────┐
             │ kicad-       │   │ hermes-      │
             │ ngspice-     │   │ kicad-       │
             │ quick-sim    │   │ workflow     │
             │ SPICE sim    │   │ packaging    │
             └──────────────┘   └──────────────┘
```

**Core principle: switch pipelines by phase — never mix them at the same time.**

| Phase | Pipeline | Notes |
|---|---|---|
| Design (Phase 0-4) | C (kcaa) preferred | Multi-layer routing → must use C; single-layer → B/C; JLCPCB → must use B |
| Verification (Phase 5) | A (kicad-cli) | Authoritative DRC; B/C DRC is incomplete |
| Export (Phase 6) | A (kicad-cli) | Gerber/drill/3D; C cannot export drill files |

## 📦 Included Skills

| Skill | Responsibility |
|---|---|
| `pcb-design` | Umbrella master Skill: requirements → selection → schematic → layout → routing → verification → export |
| `kicad-export-reporting` | SVG routing maps / 3D renders / Word design reports (incl. SVG color fixes) |
| `kicad-ngspice-quick-sim` | SPICE via KiCad's bundled ngspice.dll (DC/AC/sweep) |
| `pcb-autorouting` | Freerouting autorouting (DSN → Freerouting → SES) |
| `pcb-silk-text-audit` | Silkscreen text bounds audit (bbox r_max, not center point) |
| `hermes-kicad-workflow` | Skill packaging/migration to a new machine |

## 🚀 Installation

```bash
# 1. Clone
git clone https://github.com/yymqd/kicad-pcb-agent-skills.git
# 2. Copy into Hermes skills directory
mkdir -p ~/.hermes/skills/hardware
cp -r kicad-pcb-agent-skills/skills/hardware/* ~/.hermes/skills/hardware/
# 3. Restart Hermes or run /reload-skills
hermes skills list | grep -E "(kicad|pcb)"
```

## ⚙️ Environment Adaptation

All paths in this repo are anonymized as placeholders (`<KICAD_DIR>`, `<D_DRIVE>`, `<PROJECT_DIR>`, etc.). Replace them according to your environment before use. See [docs/environment-setup.md](docs/environment-setup.md).

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first, and state the pipeline (A/B/C) your change belongs to in the PR description.

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

**Mirror (China):** https://cnb.cool/cnb-qdu/kicad-pcb-agent-skills
