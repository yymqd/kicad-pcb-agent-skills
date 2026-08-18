# 布线后交付审计教训（2026-07-31 实测，520nm 驱动 Ø14mm）

> 布线全通过 ≠ 可以交付。以下教训来自同一会话的 A-O 全面审计轮，全部实测发现。

## 1. 程序化生成 PCB 无丝印（K.3）— 必查

用 pcbnew API 从零生成的板，**没有任何丝印**（位号、极性标记全缺失）。
这不是 pcbnew 默认行为——FootprintLoad 来的封装通常自带 fp_text，但若封装库符号
缺丝印或生成时覆盖了，检查方法是：

```python
# ⛔ GraphicalItems() 不含 fp_text！要用下面方式检查：
has_silk = False
for item in fp.GraphicalItems():
    if item.GetLayerName() == "F.SilkS":
        has_silk = True
```

**交付前必须补**：
- 位号文字：`PCB_TEXT(board)` + `SetText(ref)` + `fp.Add(t)`（用 fp.Add 让它随封装移动）
- D1 等极性件：阴极侧加竖线（SHAPE_T_SEGMENT）
- U1 等 IC：Pin1 圆点（SHAPE_T_CIRCLE）

补完 DRC 中 silk_over_copper/silk_overlap 会上升（36→67 正常），这是丝印生效的标志。

## 2. Gerber 重导（L.5）— 任何 PCB 修改后必做

改元件值、加丝印、改走线后，**必须重新导出 Gerber**，不能沿用旧文件。
用时间戳核对：

```python
pcb_mtime = os.path.getmtime(pcb_path)
g_mtime = os.path.getmtime(gdir_first_file)
# 要求 g_mtime > pcb_mtime
```

## 3. IPC-2221 走线载流 — 单位陷阱

公式 `I = k × ΔT^0.44 × A^0.725`，**A 必须用 mil²（不是 mm²）**，k=0.048 外层、0.024 内层。

```python
def ipc2221_mil(width_mil, thickness_mil, dT=10, k=0.048):
    A = width_mil * thickness_mil  # mil²
    return k * dT**0.44 * A**0.725
# 1oz = 1.378 mil 厚; 0.4mm = 15.75 mil
# 0.4mm/1oz 外层 @10°C ≈ 1.23A（10x 余量 for 120mA 电源）
```

用 mm² 直接代入会得到 0.01A 的错误结果（虚惊一场）。

## 4. 恒流环 Vf 裕量 — LD 驱动特有教训

恒流环要求 MOSFET 工作在线性区：`VDS = VOUT - Vf_LD - VSNS`。
**Rsense 越大 VSNS 压降越大 → VDS 裕量越小 → LD Vf 高时恒流失效。**

| 参数 | 失效场景 |
|---|---|
| Rsense=3.3Ω, VREF=0.264V | LD Vf=5.4V 时 VDS=-0.06V → 电流 80→60mA ❌ |
| Rsense=2.2Ω, VREF=0.176V | LD Vf=5.4V 时 VDS=0.026V → 电流保持 79mA ✅ |

修法：降 Rsense + 同步调 VREF 分压（R3/R4），保持 I=VREF/Rsense=80mA。

**验证恒流精度必须用 gain=1000 运放模型**：gain=100 有 ~5% 跟踪误差（76.3mA vs 79.4mA），
gain=1000（接近真实 100dB 运放）才准。

## 5. wrdata 列格式 — 交错重复 sweep 列

`.control` 里 `wrdata out.csv v(a) v(b) v(c)` 的输出**不是** `[t, a, b, c]`，
而是每个变量前重复时间列：`[t, v(a), t, v(b), t, v(c)]`（6 列）。

解析要隔列取：`parts[0]=t, parts[1]=v(a), parts[3]=v(b), parts[5]=v(c)`。
用 `.control` + `print` + parse_tables（按表头列名定位）比 wrdata 可靠。

## 6. 手工补线节奏

Freerouting 剩的 unrouted 手工补时：**逐条加 → DRC → 确认无新冲突**，
一次加多条错线会引入 5-10 个 shorting 且难定位（本会话踩过：一次补 4 条引入 15 shorting）。
