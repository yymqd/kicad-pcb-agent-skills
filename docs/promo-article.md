# 让 AI 帮你画 PCB —— KiCad PCB Agent Skills 开源了！

> 一句话：**用自然语言描述电路需求，AI Agent 自动完成原理图 → 布局 → 布线 → DRC 验证 → Gerber 导出全流程。**

## 🎯 这是什么

一套面向 AI Agent（Hermes Agent）的 **KiCad PCB 设计自动化技能集**，把"我想做一个 520nm 激光二极管恒流驱动，Ø14mm 双面板"这样的需求，变成可直接发嘉立创打样的 PCB 文件。

核心不是"AI 生成一个 PCB 文件"这么简单，而是沉淀了一套**可复用的工程方法论**：

- **三条管线阶段切换**：设计（kcaa 多层 PNS 布线）→ 验证（kicad-cli DRC）→ 导出（Gerber/钻孔/3D）
- **强制审计铁律**：每个工序完成后独立复核，审计不过不进下一步
- **真实踩坑记录**：B.Cu SVG 颜色不可见、丝印文字被铣掉、SPICE 仿真陷阱、Freerouting 高密度板救星……全是真金白银的教训

## 🏗️ 三条管线架构

```
设计阶段（Phase 0-4）     → 管线 C (kcaa)：多层 PNS 自动布线（A* + 自动过孔）
                           管线 B (mixelpixx)：单层布线 + JLCPCB 集成
验证阶段（Phase 5）       → 管线 A (kicad-cli)：权威 DRC 检查
导出阶段（Phase 6）       → 管线 A (kicad-cli)：Gerber / 钻孔 / 3D 渲染
```

**核心原则：按阶段切换，同一时刻不混用。**

## 📦 包含 6 个 Skill

| Skill | 职责 |
|---|---|
| `pcb-design` | 伞形主 Skill：需求→选型→原理图→布局→布线→验证→导出全流程 |
| `kicad-export-reporting` | SVG 走线图 / 3D 渲染 / Word 设计报告（含 SVG 颜色修复） |
| `kicad-ngspice-quick-sim` | 用 KiCad 自带 ngspice.dll 跑 SPICE（DC/AC/扫描） |
| `pcb-autorouting` | Freerouting 自动布线（DSN→Freerouting→SES） |
| `pcb-silk-text-audit` | 丝印文字板内验证（包围盒 r_max，非中心点） |
| `hermes-kicad-workflow` | 技能打包/迁移到新机器 |

## 🔧 真实项目验证

这套工作流不是纸面方案，已在实际项目中跑通：
- **520nm 激光二极管恒流驱动**（Ø14mm 双面板，21 元件）
- 手工布线反复 shorting/crossing 死结 → Freerouting 一次布通（shorting=0, crossing=0, unconnected=0, score 994.78）
- DRC 全过（JLC 0.1mm 制造标准）
- 完整交付物：设计报告（15 章 Word 文档）+ Gerber + 钻孔 + 3D 渲染 + 走线图

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/yymqd/kicad-pcb-agent-skills.git
# 2. 安装到 Hermes
mkdir -p ~/.hermes/skills/hardware
cp -r kicad-pcb-agent-skills/skills/hardware/* ~/.hermes/skills/hardware/
# 3. 开始对话
hermes  # 然后说："帮我设计一个 XX 电路"
```

需要 KiCad 10.0+（Windows 或 WSL），三条管线的安装详见 `docs/environment-setup.md`。

## 🤝 一起完善

这是**开源协作版**：所有路径已匿名化为占位符，任何人都可以按自己的环境适配。
欢迎：
- 提交你实测的新案例（格式见 CONTRIBUTING.md）
- 适配不同 KiCad 版本（7/8/9/10 差异是最大坑）
- 报告管线问题（标注 A/B/C）

**License: MIT**

---

*项目地址（GitHub）：https://github.com/yymqd/kicad-pcb-agent-skills*
*（国内镜像：https://cnb.cool/cnb-qdu/kicad-pcb-agent-skills）*
