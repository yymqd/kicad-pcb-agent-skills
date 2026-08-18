# KiCad PCB Agent Skills

一套面向 **AI Agent（Hermes Agent）** 的 KiCad PCB 设计自动化技能集，把自然语言需求转化为可生产的 PCB 文件。

> 本仓库是「AI 驱动 PCB 设计工作流」的开源协作版。核心经验来自真实项目（Ø14mm 双面板激光驱动等）的踩坑与修复，通过 **Hermes Agent Skill** 格式固化。

## 🎯 核心架构：三条管线

```
┌──────────────────────────────────────────────────────────┐
│                 pcb-design（伞形主 Skill）                │
│   触发入口 · 强制铁律 · Phase 0-9 门控 · 19+ 参考资料     │
└──────────────────┬───────────────────────────────────────┘
                   │ 按阶段路由
   ┌───────────────┼───────────────────┐
   ▼               ▼                   ▼
┌────────┐   ┌──────────────┐   ┌───────────────┐
│管线 C  │   │管线 B        │   │管线 A         │
│kcaa    │   │mixelpixx     │   │kicad-cli      │
│(MCP)   │   │(MCP)         │   │(CLI+pcbnew)   │
│设计    │   │设计          │   │验证/导出      │
│多层PNS │   │单层+JLCPCB   │   │DRC/Gerber/3D  │
└────────┘   └──────────────┘   └───────┬───────┘
                                        │ 产出物
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
             ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
             │ kicad-export │   │ pcb-         │   │ pcb-         │
             │ -reporting   │   │ autorouting  │   │ silk-text-   │
             │ 图形/文档    │   │ Freerouting  │   │ audit        │
             └──────────────┘   └──────────────┘   └──────────────┘
             ┌──────────────┐   ┌──────────────┐
             │ kicad-       │   │ hermes-      │
             │ ngspice-     │   │ kicad-       │
             │ quick-sim    │   │ workflow     │
             │ SPICE仿真    │   │ 迁移打包     │
             └──────────────┘   └──────────────┘
```

**核心原则：按阶段切换，同一时刻不混用。**

| 阶段 | 管线 | 说明 |
|---|---|---|
| 设计（Phase 0-4） | C (kcaa) 首选 | 多层布线→必须 C；单层→B/C；JLCPCB→必须 B |
| 验证（Phase 5） | A (kicad-cli) | DRC 权威检查，B/C 的 DRC 不完整 |
| 导出（Phase 6） | A (kicad-cli) | Gerber/钻孔/3D，C 不支持钻孔 |

## 📦 包含的 Skills

| Skill | 职责 |
|---|---|
| `pcb-design` | 伞形主 Skill：需求→选型→原理图→布局→布线→验证→导出全流程 |
| `kicad-export-reporting` | SVG 走线图 / 3D 渲染 / Word 设计报告（含 SVG 颜色修复） |
| `kicad-ngspice-quick-sim` | 用 KiCad 自带 ngspice.dll 跑 SPICE（DC/AC/扫描） |
| `pcb-autorouting` | Freerouting 自动布线（DSN→Freerouting→SES） |
| `pcb-silk-text-audit` | 丝印文字板内验证（包围盒 r_max，非中心点） |
| `hermes-kicad-workflow` | 技能打包/迁移到新机器 |
## 🚀 安装

```bash
# 1. 克隆仓库
git clone https://github.com/yymqd/kicad-pcb-agent-skills.git
# 2. 复制到 Hermes skills 目录
mkdir -p ~/.hermes/skills/hardware
cp -r kicad-pcb-agent-skills/skills/hardware/* ~/.hermes/skills/hardware/
# 3. 重启 Hermes 或执行 /reload-skills
hermes skills list | grep -E "(kicad|pcb)"
```

## ⚙️ 环境适配

仓库内所有路径已匿名化为占位符（`<KICAD_DIR>`、`<D_DRIVE>`、`<PROJECT_DIR>` 等），使用前请根据你的环境替换。参见 [docs/environment-setup.md](docs/environment-setup.md)。

## 🤝 贡献

欢迎完善这个工作流！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，提交 PR 时注明改动归属的管线（A/B/C）。

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)
