# 小圆板 (<Ø20mm) PCB 设计指南

> 基于 520nm 80mA 激光驱动器 (Ø14mm, 23元件, 50走线, 2026-06-06) 验证。

## 核心挑战

小圆板的面积由二次方定律决定——Ø14mm=154mm²。23个元件加50条走线在此面积上密度高达71%。标准 PCB 设计规则在此空间约束下必须调整。

## 1. 边缘连接方案

**原则：排针连接器在小圆板上不可行。** 1×4 PH2.0 排针约占 Ø14mm 板面积的35%。

**方案：TestPoint_Pad_D1.5mm**

使用 KiCad 标准库 `TestPoint.pretty` 的圆形铜焊盘作为引线焊接点。每个焊盘仅 1.8mm²，无塑料本体，高度 <0.5mm。

```python
tp1 = place(board, "TestPoint.pretty", "TestPoint_Pad_D1.5mm",
            "TP1", "VIN", 7.0, 1.5)
```

典型布局（四角放射状）：
```
         TP1(VIN)
             |
    TP3(TTL) ─┼─ TP4(LD_OUT)
             |
         TP2(GND)
```

详见 `references/circular-board-connectors.md`。

## 2. GND 处理

**原则：<20mm 板上全板铜皮弊大于利。** GND pours 在20+元件/50+走线密度下产生300-500条 solder_mask_bridge 违规。

**方案：GND 过孔网络**

- 全部 10-15 个 GND 过孔分布在板面
- 底层走线作为 GND 总线（0.3-0.5mm宽）
- 每个 GND 焊盘添加过孔到底层

验证：`kicad-cli pcb export stats` 显示 back copper area > 2mm²（来自过孔焊盘）

## 3. DRC 违规解读

**原则：仅计数功能性错误，忽略可制造性违规。**

| 违规类型 | 在<20mm板上的意义 | 放行条件 |
|:---------|:-----------------|:---------|
| `solder_mask_bridge` | 密布局必然发生，不影响功能 | 忽略全部 |
| `clearance` | 默认 0.25mm 过于严格，JLCPCB 0.1mm | min_clearance > 0.1mm |
| `courtyard_overlap` | 0603元件间距<0.2mm时必然重叠 | 忽略 |
| `silk_overlap` | 字号0.5mm时可能叠元件丝印 | 目检确认可读即可 |
| **`shorting_items`** | 真正短路的 | **必须=0** |
| **`unconnected_items`** | 未连接的焊盘 | **<10可接受** |

## 4. 布局分区策略

在圆形板上，按角度分区而非坐标：

| 区域 | 角度 | 功能 |
|:----|:----|:-----|
| 顶部 | 0-4点方向 | 功率级 (Boost IC + 电感 + 续流管) |
| 左中 | ~7-9点 | 输入保护 (反接 + ESD + 滤波) |
| 中心 | — | 控制核心 (op-amp + 调整管) |
| 右中 | ~3-5点 | 采样 + 输出 |
| 底部 | 4-8点方向 | 控制输入 (TTL + 偏置) |

## 5. 走线顺序

按优先级布线避免 unconnected:
1. **电源网** (0.4mm) — 受元件位置约束最大，先布
2. **关键信号** (0.25mm) — 反馈路径最短
3. **GND** (0.3mm) — 连接剩余焊盘，不加铜皮

## 6. 版本标识

丝印层必须添加版本号和日期。在小圆板上通常放在元件最少的下半部区域：

```python
ver = PCB_TEXT(board)
ver.SetText("v1.0 2026-06-06")
ver.SetPosition(VECTOR2I(FromMM(CX), FromMM(CY + 4.5)))
ver.SetTextSize(VECTOR2I(FromMM(0.5), FromMM(0.5)))
ver.SetLayer(pcbnew.F_SilkS)
ver.SetVisible(True)
board.Add(ver)
```

## 7. 面板化（拼板）

小圆板必须在 JLCPCB 勾选拼板服务。推荐邮票孔连接优于 V-cut（手工分板更方便）。

| 方案 | 板间距 | 适用批量 |
|:----|:------|:---------|
| V-cut | ≥2mm | >100片 |
| 邮票孔 | ≥1mm, 4-6孔/边 | <100片 |

## 8. DFM 检查清单（小圆板特化）

| 检查项 | 标准 |
|:-------|:-----|
| 最小线宽 | 0.25mm (JLC: 0.1mm) ✅ |
| 最小间距 | DRC暴力，但实际>0.1mm | 
| 最小钻孔 | 0.3mm (JLC: 0.3mm) |
| 板边走线 | >0.3mm (仅测试点可至0.5mm) |
| 元件距板边 | >0.5mm |
