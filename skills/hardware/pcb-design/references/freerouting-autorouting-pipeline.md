# Freerouting 自动布线管线（KiCad 10）

**来源**: 520nmLD_Driver 项目（2026-07-31，Ø14mm/21 元件/110 段走线/20 过孔/score 994.78/1000）
**适用**: 高密度板（<Ø20mm、20+ 元件）自动布线 → 人工微调的标准路径

## 流程总览

```
KiCad pcbnew ──ExportSpecctraDSN──▶ board.dsn (Specctra 任务文件)
                                        │
                                        ▼
                              Freerouting 2.2.4 (Java GUI/CLI)
                                        │
                                        ▼
board.ses (Specctra 布线结果) ──ImportSpecctraSES──▶ KiCad pcbnew
```

## Step 1: KiCad 导出 DSN

```python
# pcbnew API
board = pcbnew.LoadBoard("board.kicad_pcb")
board.ExportSpecctraDSN("board.dsn")
# 或 KiCad GUI: 文件 → 导出 → Specctra DSN
```

产物特征：`(pcb <name>.dsn (parser (host_cad "KiCad's Pcbnew") ...))`，含元件 placement 与 net 信息。

## Step 2: Freerouting 布线

- **工具**: Freerouting 2.2.4（Java，跨平台；WSL 可跑 `java -jar freerouting.jar board.dsn`）
- **关键参数**（本项目实际）：
  - 布线网格 resolution 10µm（DSN/SES 中 `(resolution um 10)`）
  - 层：F.Cu + B.Cu（双层）；过孔 THROUGH
  - 线宽/间距：按设计规则（本项目 0.2mm/0.1016mm）
- 输出评分（score）：本项目 994.78/1000（未连接 0 的接近最优）

## Step 3: SES 导回 KiCad

```python
board.ImportSpecctraSES("board.ses")
board.Save("board.kicad_pcb")
```

SES 特征：`(session board (placement ...) (route ...))`，含最终布线。

## ⛔ 自动布线后必做的人工检查（Freerouting 的盲区）

Freerouting **不知道电路的电气语义**，以下必须人工核对/微调：

| 检查项 | 本项目教训 |
|---|---|
| **敏感信号 vs 开关节点隔离** | FB 距 SW 仅 0.28mm（自动布线的产物）——串扰 0.06% 可接受但必须量化确认；自动布线不会主动隔离 |
| **去耦电容就近 IC** | C1→U1 5.27mm（>5mm 判据，妥协记录）——自动布线按连接布，不按"去耦应就近"布 |
| **功率回路面积** | Boost SW 回路（U1→D1→C2→GND）——自动布线不优化回路，需人工检查 ≤100mm² |
| **开关节点铜皮** | SW 节点总铜面积（本项目 4.4mm² < 10mm²）——自动布线可能把开关节点布得过大 |
| **电源走线宽度** | 自动布线默认统一线宽——电源网络（VIN/VOUT/GND）需人工加宽（本项目统一 0.2mm，载流 39% 够用） |
| **GND 完整性** | 本项目 B.Cu GND 覆铜是人工加的（自动布线只管走线） |

## Step 4: 后续人工修改（pcbnew API）

自动布线后任何元件增删/封装更换，用 pcbnew API 局部改（见 `pcb-routing-pipeline-kicad10.md`）：
- 加元件（R8）：新建 2 段 PCB_TRACK + 1 个 PCB_VIA，端点读实际 pad 位置
- 换封装（L1）：SetFPID 只改 ID 不改几何 → 必须删旧 footprint + FootprintLoad 新封装；SetStart/SetEnd 移动受影响走线端点
- 改值（R6）：只改 Value 字段，不动布线

## 验证

改完布线必须：
1. `kicad-cli pcb drc` 重跑 → shorting_items=0 / unconnected_items=0 / tracks_crossing=0
2. `kicad-cli pcb export stats` 核对统计
3. 重新导出 Gerber（时间戳链 PCB ≤ Gerber ≤ zip）

## Pitfalls

- DSN/SES 中文字符路径会失败 → 放纯 ASCII 路径（`<TEMP_DIR>\`）
- Freerouting 评分高 ≠ 电气正确（score 只看几何/DRC 类指标）
- 自动布线不处理：覆铜、丝印、热焊盘、电源网络加宽、敏感信号隔离——这些是人工职责
- 换封装后 pad 位置可能变化（SWPA252012S 焊盘 0.85×2.0mm 竖长 vs 0805）→ 必须重跑 DRC 查几何冲突（曾导致与 C1 焊盘 1 条短路）
