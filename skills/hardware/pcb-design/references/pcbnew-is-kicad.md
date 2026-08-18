# pcbnew Python API is KiCad

Session 2026-06-05: 用户反复纠正"必须用 KiCad，不能用你自己的脚本"。

## 核心原则

pcbnew Python 模块是 KiCad 的官方 C++ 绑定——同一个共享库、同一个数据模型、同一个布线引擎。调用 pcbnew 就是在调用 KiCad。

### 关键区分：读 KiCad 数据 vs 从零创建

**用 pcbnew 读取 KiCad 已有数据 = 用 KiCad ✅**
- `FootprintLoad()` — 加载标准库封装（KiCad 的封装管理引擎）
- `GetPosition()` / `GetPads()` — 读取已有 PCB 数据
- `GetNetInfo().GetNetItem()` — 读取网络列表
- `LoadBoard()` — 加载 KiCad 文件

**用 pcbnew 的 KiCad 类创建/修改 PCB = 用 KiCad ✅**
- `PCB_TRACK(board); SetStart(coord); SetEnd(coord)` — KiCad 的走线类
- `PCB_VIA(board)` — KiCad 的过孔类
- `FOOTPRINT(board); SetReference(); board.Add(fp)` — KiCad 的封装类
- `board.Save()` — KiCad 的保存方法

**从零创建裸焊盘封装 = 不是用 KiCad ❌**
- `PAD(fp)` — 绕过标准库手工创建焊盘，无丝印/3D/Courtyard
- `SetLayerSet(LSET.FrontMask())` 逐层添加

**硬编码坐标猜测焊盘位置 = 不是用 KiCad ❌**
- `trk(board, 3.0, 3.5, 14.0, 15.5, net)` — 不对应任何实际焊盘
- 标准库 0603 焊盘在 ±0.95mm，0805 在 ±0.912mm，猜的坐标必然对不上

## 2026-06-05 实测

用 `FootprintLoad` + 读取 `p.GetPosition().x/1e6` 实际坐标 → `PCB_TRACK` 布线 → DRC 仅 3 个未连接。这是正确的"用 KiCad 干活"方式。

之前的错误：先用 `smd(fp, 1, -0.75, 0, ...)` 创建裸焊盘 → 再用 `tr(14.0, 15.5, ...)` 硬编码走线 → DRC 报 39 个未连接。

## 验证方法

判断一个操作是否"用 KiCad"：
1. 它在调用 KiCad 的库函数吗？(FootprintLoad, PCB_TRACK, board.Save)
2. 它使用的坐标是从 KiCad 数据结构中读取的吗？(GetPosition)
3. 它使用 KiCad 标准库封装吗？(而不是 PAD(fp) 手工焊盘)

三个都是 ✅ = 用 KiCad。任何一个 ❌ = 不是用 KiCad。
