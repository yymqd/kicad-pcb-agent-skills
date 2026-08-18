# KiCad 7 pcbnew Python API Pitfalls

实战验证（RC低通滤波器，KiCad 7.0.11 on Ubuntu 24.04）。

## 关键 API 差异（KiCad 7 vs 新版本）

### 1. 矢量类型

| KiCad 7 | KiCad 8+ |
|---------|----------|
| `VECTOR2I(x, y)` | `Vector2i(x, y)` 或 `VECTOR2I`（兼容） |
| `VECTOR2D(x, y)` | `Vector2d(x, y)` |

KiCad 7 所有矢量类型名**全大写**。使用小写会抛出 `NameError`。

### 2. 网络（Nets）

```python
# KiCad 7 正确方式：
from pcbnew import NETINFO_ITEM
net = NETINFO_ITEM(board, "net_name")
board.Add(net)           # 必须显式 Add，不是 board.AddNet()
board.Add(net) 后会创建 net 但不会设置 netcode——需要手动查找：
netcode = board.GetNetCount() - 1   # 刚添加的 net 的 code
```

### 3. 封装（Footprints）路径

| 环境 | 路径 |
|:-----|:-----|
| KiCad 7 (apt) | `/usr/share/kicad/footprints/` |
| KiCad 8+ | `/usr/share/kicad/footprints/`（同） |
| Windows | `<C_DRIVE>\Program Files\KiCad\share\kicad\footprints\` |

### 4. 铜皮（Copper Zones）

```python
from pcbnew import ZONE, ZONE_SETTINGS, PCB_LAYER_ID

# 创建铜皮
zone = ZONE()
zone.SetLayer(PCB_LAYER_ID.F_Cu)

# 轮廓——注意 Outline 方法链的使用
outline = zone.Outline()        # 返回 POLYSET
outline.NewOutline()            # 开始一个新轮廓
outline.Append(x, y)            # 添加顶点（不是 AddCorner/AddPoint）
outline.Append(x2, y2)          # 依次加顶点，自动闭合

# 只需在顶层铜皮加
board.Add(zone)
```

### 5. 走线（Tracks）

```python
from pcbnew import PCB_TRACK, PCB_VIA, VECTOR2I

# 走线
track = PCB_TRACK(board)
track.SetStart(VECTOR2I(x1_nm, y1_nm))   # 注意坐标单位是纳米
track.SetEnd(VECTOR2I(x2_nm, y2_nm))
track.SetWidth(width_nm)
track.SetLayer(PCB_LAYER_ID.F_Cu)
board.Add(track)

# 过孔
via = PCB_VIA(board)
via.SetPosition(VECTOR2I(x_nm, y_nm))
via.SetViaType(PCB_VIA.THROUGH)
via.SetDrill(drill_nm)
via.SetWidth(dia_nm)
board.Add(via)
```

### 6. 板框

```python
from pcbnew import EDGE_MODULE, PCB_SHAPE, PCB_LAYER_ID

# 用 PCB_SHAPE 画板框（不要用 EDGE_MODULE）
edge = PCB_SHAPE(board)
edge.SetShape(PCB_SHAPE.SHAPE_S_RECT)  # KiCad 7 用 SHAPE_S_RECT
edge.SetWidth(100000)                   # KiCad 7 单位纳米（0.1mm）
edge.SetStart(VECTOR2I(x1, y1))
edge.SetEnd(VECTOR2I(x2, y2))           # SetEnd 定义了矩形对角线
edge.SetLayer(PCB_LAYER_ID.Edge_Cuts)
board.Add(edge)
```

## KiCad 7 pcbnew 代码实战坑（2026-06 验证）

以下问题在 1kHz RC 低通滤波器 PCB 生成过程中逐一发现并解决。

### 焊盘 API 陷阱

| 错误写法 | 正确写法 | 现象 |
|:---------|:---------|:-----|
| `pad.SetDrill(mm(0.8))` | `pad.SetDrillSize(VECTOR2I(mm(0.8), mm(0.8)))` | `AttributeError: no SetDrill` |
| `pad.SetLayerSet(pcbnew.PAD::SMDMask())` | `pad.SetLayer(pcbnew.F_Cu)` 或 `LSET` 逐层添加 | C++ 语法，Python 无效 |
| `pad.SetLayerSet(ls)` 设 `F_Cu+B_Cu` | THT 焊盘用 `layers "*.Cu" "*.Mask"`（S表达式） | 层设置复杂时可直写 S表达式 |

### `list(fp.Pads())` 顺序陷阱

**`list(fp.Pads())` 返回的焊盘顺序不一定与焊盘编号对应。** 用索引分配网络可能导致 net 错乱：

```python
# ❌ 错误：假设索引 0 = pad "1"
p(j1,0).SetNet(ni)  # 实际可能是 pad "2"!
p(j1,1).SetNet(ng)

# ✅ 正确：按焊盘编号分配
for pad in fp.Pads():
    if pad.GetNumber() == "1":
        pad.SetNet(net_vin)
    elif pad.GetNumber() == "2":
        pad.SetNet(net_gnd)
```

**修复方式**：已经生成的 PCB 文件中直接替换 S-expression 的 `(net N)` 值比重跑 pcbnew 更可靠。

### 铜皮（ZONE）段错误

```python
# ❌ 下面代码在 KiCad 7 中导致段错误：
zone = pcbnew.ZONE(board)
zone.Outline().Append(VECTOR2I(x,y))
board.Add(zone)

# ✅ 替代方案：不通过 pcbnew API 加铜皮
# 1. 在 KiCad GUI 中选中区域 → 按 B 刷新
# 2. 或用 S-expression 直接写 (zone ...) 块
# 3. 对于简单电路，GND 网络连接已充分，铜皮是锦上添花
```

### `PCB_SHAPE` 不是铜皮

```python
# ❌ PCB_SHAPE 没有 SetNet 方法
shape = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
shape.SetNet(net)  # AttributeError！

# ✅ 铜皮必须用 pcbnew.ZONE(board)
```

### `pcbnew.DRC()` 不存在

KiCad 7 的 pcbnew Python API 没有 `DRC` 类：

```python
# ❌
drc = pcbnew.DRC(board)  # AttributeError

# ✅ 替代 DRC 检查方法：
# 1. kicad-cli 在 KiCad 7 中没有 drc 子命令
# 2. 手动检查：确认所有焊盘有 net、走线连接正确、无孤立焊盘
# 3. 建议用户在 KiCad GUI 中按 F7 运行 DRC
```

### S-expression 格式坑

**`sexpdata.dumps()` 给所有标识符加引号，KiCad 不识别。**

```python
# sexpdata 输出：
("kicad_pcb" ("version" "20221018"))  # ❌ KiCad 不认
# 需要：
(kicad_pcb (version 20221018))         # ✅

# 解决方案：直接写 S-expression 字符串，不用 sexpdata
pcb = """(kicad_pcb (version 20221018) ...)"""
with open(path, 'w') as f:
    f.write(pcb)
```

**`*.Cu` 必须加引号：**

```
(layers *.Cu *.Mask)     # ❌ KiCad 7 解析失败
(layers "*.Cu" "*.Mask") # ✅
```

## KiCad 7 pcbnew 模块要点

### ✅ 可用的关键类
- `BOARD`（核心类）
- `FOOTPRINT`（`board.GetFootprint()` 获取）
- `PCB_TRACK`, `PCB_VIA`, `PCB_SHAPE`
- `ZONE`, `ZONE_SETTINGS`
- `NETINFO_ITEM`
- `VECTOR2I`, `VECTOR2D`
- `PCB_LAYER_ID`, `PCB_PAD`

### ❌ KiCad 7 中不可用的 API
- `board.AddNet()` — 不存在，用 `NETINFO_ITEM + board.Add()`
- `board.CreateNet()` — 不存在
- `pcbnew.FromMM()` — 不存在，需手动 `int(mm * 1e6)` 换算为纳米
- `pcbnew.ToMM()` — 同上
- `FOOTPRINT.RefDes()` — KiCad 7 没有统一的 RefDes 方法，用 `SetReference()` / `GetReference()`
- `pcbnew.DRC()` — 不存在
- `PAD.SetDrill()` — 不存在，用 `SetDrillSize(VECTOR2I)`
- 部分 KiCad 8 的 wxPython 绑定不可用

## 单位换算

```
1 mm = 1,000,000 nm（1e6）
0.254 mm (10mil pin header) = 254,000 nm
20 mm = 20,000,000 nm
15 mm = 15,000,000 nm
```

## KiCad CLI 导出命令汇总

| 命令 | 用途 | KiCad 7 | KiCad 10 |
|:-----|:-----|:-------:|:--------:|
| `kicad-cli pcb export svg` | SVG 渲染 | ✅ | ✅ |
| `kicad-cli pcb export gerbers` | Gerber 文件 | ✅ | ✅ |
| `kicad-cli pcb export drill` | NC 钻孔 | ✅ | ✅ |
| `kicad-cli pcb export pdf` | PDF 输出 | ✅ | ✅ |
| `kicad-cli pcb export step` | 3D STEP | ✅ | ✅ |
| `kicad-cli sch export svg` | 原理图 SVG | ✅ | ✅ |
| `kicad-cli pcb drc` | DRC | ❌ (KiCad 7 无子命令) | ✅ **存在** (KiCad 10) |

**注意**：KiCad CLI 的 `drc` 子命令在 **7.0 不存在**（只能 GUI F7），但 **KiCad 10 实测可用**（2026-06/07 多次使用）：`kicad-cli pcb drc board.kicad_pcb --output out.json --format json --severity-all --refill-zones`，支持 report/json 格式与 `--severity-all`。JSON 中检查 `violations`（按 `type` 统计，如 shorting_items/silk_overlap/clearance）与 `unconnected_items`。

---

## KiCad 10 pcbnew API 差异（实测 2026-06）

从 KiCad 7 升级到 KiCad 10.0.3，以下 API 变化已实测验证：

### 1. Layer ID → 直接 int 常量

```python
# KiCad 7:
from pcbnew import PCB_LAYER_ID
layer = PCB_LAYER_ID.F_Cu   # PCB_LAYER_ID 类不存在于 KiCad 10

# KiCad 10:
layer = pcbnew.F_Cu         # 0 — 直接 int 常量
pcbnew.Edge_Cuts            # 25
pcbnew.F_SilkS              # 5
pcbnew.F_Mask               # 1
pcbnew.B_Cu                 # 2
```

### 2. LSET 操作符

```python
# KiCad 7: LSET 支持 | 操作符
mask = LSET.FrontCu() | LSET.FrontMask()

# KiCad 10: LSET 不支持 |，用 AddLayerSet()
mask = pcbnew.LSET.AllCuMask()
mask.AddLayerSet(pcbnew.LSET.AllTechMask())

# 预置工厂方法：
pcbnew.LSET.FrontMask()       # 顶层铜皮+阻焊
pcbnew.LSET.AllCuMask()       # 所有铜层
pcbnew.LSET.AllTechMask()     # 所有技术层
```

### 3. PAD 构造需要 FOOTPRINT 父对象

```python
# KiCad 7:
pad = pcbnew.PAD()
# KiCad 10:
pad = pcbnew.PAD(footprint)   # 必须传父 FOOTPRINT
```

### 4. FromMM() / ToMM() 可用

```python
# KiCad 7: 手动 int(mm * 1e6)
# KiCad 10:
from pcbnew import FromMM, ToMM
x_nm = FromMM(7.5)    # → 7500000
x_mm  = ToMM(7500000) # → 7.5
```

### 5. 板框形状

```python
# KiCad 7: SHAPE_S_RECT
shape.SetShape(PCB_SHAPE.SHAPE_S_RECT)     # ❌ KiCad 10 中不存在

# KiCad 10:
from pcbnew import SHAPE_T_RECT, SHAPE_T_SEGMENT
shape.SetShape(SHAPE_T_RECT)               # ✅ 矩形
# 或逐段画线：
shape.SetShape(SHAPE_T_SEGMENT)            # ✅ 线段
```

### 6. 文件格式版本

```python
# KiCad 7: version 20221018
# KiCad 10: version 20260206
```

### 7. BOARD 保存

```python
# 两种版本均可：
board.Save('/path/to/output.kicad_pcb')

# 读取：
board = pcbnew.LoadBoard('/path/to/file.kicad_pcb')
```

### 8. 完整工作示例

见 `/tmp/gen_lpf_kicad10.py`（1kHz RC 低通滤波器完整 PCB 生成脚本，兼容 KiCad 10.0.3）。

### 9. ✅ KiCad 10 board.Save() net mapping

**2026-06-05 实测**（KiCad 10.0.3, Ubuntu 24.04 WSL）：`board.Save()` 输出 S-expression 使用字符串 net 名，6 个不同 net 交叉验证全部正确。**无需后处理修复。**

### 10. ⚠️ KiCad 10 pcbnew PAD_SHAPE constants（完整性备注）

无额外注意点 — `PAD_SHAPE_RECT`, `PAD_SHAPE_CIRCLE` 等在 KiCad 10 中均可用。注意 PAD 构造已改为必须传 FOOTPRINT 父对象（见 §3）。

### 11. ⚠️ KiCad 10 PCB_VIA.GetWidth() 必须传 layer 参数（实测 2026-07-31）

```python
via.GetWidth()                # ❌ assert 失败: "PCB_VIA::GetWidth called without a layer argument"，进程挂起
via.GetWidth(via.GetLayer())  # ✅ 正确
```

KiCad 10 中 `PCB_VIA::GetWidth` 有 layer 参数（KiCad 7 无）。审计脚本遍历过孔时**必须**传层参数，否则 assert 挂起且无输出。`GetDrillValue()` 无此问题。

### 12. ⚠️ board.Remove() 之后 GetTracks() 失效（实测 2026-07-31）

```python
board.Remove(fp)             # 删除 footprint
list(board.GetTracks())      # ❌ TypeError: 'SwigPyObject' object is not iterable（Remove 后 Tracks() 返回空 swig 对象）
```

**删除元素前先收集清单**：先遍历 GetFootprints()/GetTracks() 把要删的对象收集到 list，再逐个 Remove。修改板子（Add/Remove）之后同理不要再依赖旧的 GetTracks() 迭代。

### 13. ⚠️ 放置新元件前必须检查目标区域的走线占用（实测 2026-07-31）

硬编码 pad 坐标（即使 pad 编号位置猜对）仍会翻车：**附近可能有你看不见的电源走线**。真实案例：R_0402_1005Metric 的 pad 实际在 ±0.51mm（相对中心），放 (x,y) 后 pad 落在 (−5.46,−3.0)/(−4.44,−3.0)，结果 VIN 网络走线正好经过 (−4.61,−1.83)→(−4.61,−3.11) 竖直段和 (−4.38,−3.33)→(−1.51,−3.33) 水平段 → 新增 4 条短路 + 1 条未连接 + 1 条交叉。

**正确流程**：
1. `FootprintLoad()` + `SetPosition()` 放置
2. `fp.Pads()` 读取**实际** pad 绝对坐标（不猜）
3. **dump 目标区域全部走线**（`board.GetTracks()` 过滤坐标范围，按 net 分组打印路径）——特别注意电源网络（VIN/VOUT/GND）的走线走廊
4. 确认 pad、走线、过孔三者的 clearance 后再布线
5. DRC 验证（shorting_items=0, unconnected_items=0）后才算完成

### 14. ⚠️ 换封装三坑（实测 2026-07-31，L1 换 SWPA252012S）

| 坑 | 现象 | 正确做法 |
|---|---|---|
| `fp.SetFPID(LIB_ID(...))` **只改 ID 不改几何** | DRC 报 lib_footprint_mismatch；焊盘还是旧封装位置 | 换封装必须：先 `FootprintLoad()` 新封装 → 删除旧 footprint → `board.Add()` 新封装（**先加载再删除**，Remove 后 FootprintLoad/Pads() 会失效） |
| `board.Remove()` 后 swig 容器失效 | Remove 后 `GetTracks()`/`fp.Pads()`/`FootprintLoad` 全部报 'SwigPyObject' not iterable | 全部收集/设置/加载操作在 Remove **之前**完成；Remove 后只做 board.Add + 对已持有引用的对象操作 |
| 新封装焊盘几何可能撞邻件 | SWPA252012S 焊盘 0.85×2.0mm（竖长），L1.pad2 下缘与 C1.pad2 上缘重叠 → 1 条 shorting | 换封装后**必须重跑 DRC**（shorting_items 会暴露几何冲突）；必要时移动元件（本例 L1 y 2.69→3.10） |

### 15. ⚠️ 电源电感必须查 Isat（2026-07-31 实测）

**0805 叠层电感（L_0805_2012Metric）22µH 的饱和电流典型仅 90-150mA**——boost 输入峰值电流 128mA 时饱和失效（降额需 ≥160mA）。MT3608 手册明确 "To avoid inductor saturation current rating should be considered"。

**正确流程**：
1. 计算电感峰值电流：I_peak = I_in_avg/(1-D) + ΔI/2（本例 105mA/0.893 + 10mA ≈ 128mA）
2. 要求 Isat ≥ I_peak/0.8（降额）
3. **查立创商城实际型号**（so.szlcsc.com）：功率电感（SWPA/CDRH 系列）Isat 明确标注；普通叠层电感 Isat 普遍不足
4. 换功率电感封装（KiCad 库 L_Sunlord_SWPA252012S 等），BOM 写具体料号 + LCSC#
   本例选型：**SWPA252012S220MT（C65856）** 22µH Isat 530mA（余量 4.1x）

---

