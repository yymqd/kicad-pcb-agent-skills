---
name: pcb-autorouting
description: >
  PCB 自动布线：KiCad DSN → Freerouting → SES。Use when 高密度板布线反复冲突。
version: 1.0.0
author: hermes-curator
tags: [pcb, kicad, freerouting, autorouting, dsn, ses, routing]
related_skills:
  - hardware/pcb-design
---

# PCB 自动布线（Freerouting 管线）

**上游路由**: 由 pcb-design（伞形主 skill）在 Phase 5 布局布线阶段触发；本 skill 是聚焦 skill，只处理自动布线（DSN→Freerouting→SES）。手动布线/局部修改用 pcb-design 的 `references/pcb-routing-pipeline-kicad10.md`；完整设计/审查回 pcb-design。

> 2026-07-31 实测：Ø14mm 圆板、20 元件、12 网络、双面板，手工/程序化布线全部失败
> （shorting/crossing 反复出现）后，用本管线一次布通：**shorting=0, crossing=0, unconnected=0**。
> freerouting score 994.78/1000。JLC 0.1mm 制造标准下 DRC 全过。

## 适用场景

- 高密度板（<20mm、20+ 元件）手工/程序化布线反复产生 shorting/crossing 死结
- 任何需要自动布线的双面板

## 关键前提（不满足 = 白跑）

1. **GND 用 B.Cu 铜皮（zone）而非布线**：先在 KiCad 加 B.Cu GND 铜皮 + 每个 GND 焊盘加过孔，
   再导出 DSN。这样 DSN 里 GND 变成 `(plane)`，freerouting 不布 GND 走线，B.Cu 空间释放。
   GND 焊盘过孔让 GND 焊盘在 F.Cu/B.Cu 间连通。
2. **clearance 必须降到 0.1mm（JLC 标准）**：KiCad 默认 0.2mm 太严，高密度板布不完。
   pcbnew 设 `ds.m_Clearance = FromMM(0.1)`、`ds.m_TrackMinWidth = FromMM(0.15)`。
   DSN 内的 clearance 也改（KiCad 导出为 200 = 0.2mm，改 100 = 0.1mm）。
3. **freerouting Linux 版自带 JRE，免 Java**：`freerouting-2.2.4-linux-x64.zip`（81MB, jpackage 打包，
   内含 runtime），解压后 `bin/freerouting` 直接跑。国内用 ghproxy：
   ```bash
   curl -sL "https://ghproxy.net/https://github.com/freerouting/freerouting/releases/download/v2.2.4/freerouting-2.2.4-linux-x64.zip" -o /tmp/fr.zip
   python3 -c "import zipfile; zipfile.ZipFile('/tmp/fr.zip').extractall('/tmp/fr')"  # WSL 无 unzip 时
   ```

## 管线步骤

### 1. 生成 PCB（元件+网络，无走线）

`pcbnew.BOARD()` + FootprintLoad + 放置 + SetNet（见 pcb-design 的 kicad10-pcbnew-helpers.py）。

### 2. 加 GND 过孔 + B.Cu GND 铜皮

```python
# GND 过孔：每个 GND 焊盘中心加 0.6/0.3 via
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == "GND":
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pad.GetPosition())
            via.SetWidth(FromMM(0.6)); via.SetDrill(FromMM(0.3))
            via.SetNet(board.FindNet("GND"))
            board.Add(via)

# B.Cu GND 铜皮（关键：让 DSN 里 GND 变 plane）
from pcbnew import SHAPE_LINE_CHAIN
zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.B_Cu)
zone.SetNet(board.FindNet("GND"))
chain = SHAPE_LINE_CHAIN()
n, r = 64, 6.7  # Ø14mm 板半径 7 - 0.3 边距
for i in range(n):
    a = 2*math.pi*i/n
    chain.Append(VECTOR2I(FromMM(r*math.cos(a)), FromMM(r*math.sin(a))))
chain.SetClosed(True)
zone.AddPolygon(chain)  # AddPolygon 收 SHAPE_LINE_CHAIN，不是 POLY_SET！
zone.SetLocalClearance(FromMM(0.25))
zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
zone.SetMinThickness(FromMM(0.2))
board.Add(zone)
```

### 3. 设 0.1mm 设计规则

```python
ds = board.GetDesignSettings()
ds.m_Clearance = FromMM(0.1)
ds.m_TrackMinWidth = FromMM(0.15)
ds.m_ViasMinSize = FromMM(0.5)
ds.m_ViasMinDrill = FromMM(0.25)
```

### 4. 导出 DSN

```python
pcbnew.ExportSpecctraDSN(board, r"<TEMP_DIR>\board.dsn")
```

### 5. 修改 DSN（可选但推荐）

**推荐：kicad_default class 限定 F.Cu** —— 让 freerouting 只在 F.Cu 布信号，
B.Cu 全留给 GND plane，B.Cu 空出来可手工补线：

```
(class kicad_default ... (circuit (use_layer "F.Cu") (use_via "Via[0-1]_600:300_um")) ...)
```

电源网络（如 VIN）想走 B.Cu 时：net 定义加 `(class VIN_CLASS)`，class 区加
`(class VIN_CLASS VIN (circuit (use_via "Via[0-1]_600:300_um")) (rule (width 300)))`。

### 6. 跑 freerouting（⛔ 必须带 -drc！）

```bash
timeout 90 /tmp/fr/freerouting-2.2.4-linux-x64/bin/freerouting \
  -de <TEMP_DIR>/board.dsn -do <TEMP_DIR>/board.ses \
  -drc <TEMP_DIR>/fr_drc.json < /dev/null > /tmp/fr_log.txt 2>&1
```

**⛔ 必须带 `-drc`**：freerouting 有 unrouted 时，不带 -drc 会卡 GUI、不写 SES 也不退出
（timeout 杀掉 = 白跑）。带 -drc 后完成即自动保存 SES 并退出（exit 0）。
`-drc` 名义是生成 DRC 报告，副作用是触发自动保存退出。

### 7. 导入 SES

```python
# ⛔ 导入前先删旧走线（否则叠加 → shorting 爆炸）
for t in list(board.GetTracks()):
    board.Remove(t)
pcbnew.ImportSpecctraSES(board, r"<TEMP_DIR>\board.ses")
```

### 8. DRC 验证 + 手工补线

```bash
kicad-cli pcb drc board.kicad_pcb --output drc.json --format json --severity-all --refill-zones
```

freerouting 通常剩几个 unrouted（电源焊盘缺 via 或特殊网络），手工补：
- 未连接焊盘 → 加 via → B.Cu 短走线连到网络主干
- **逐条加 → DRC → 确认无新冲突**，不要一次加多条（一条错线引入 5-10 shorting）

## 踩坑清单（全部实测）

| 坑 | 现象 | 修法 |
|---|---|---|
| 不带 -drc | freerouting 完成但卡 GUI，SES 不写，timeout 杀掉 | 必须加 `-drc <path>` |
| DSN 有 0 长度走线 | freerouting 报 "Polyline: must contain at least 2 different points" + NPE | 生成走线时避免起点=终点 |
| GND 没有铜皮就导出 DSN | freerouting 把 GND 当普通网络布 → B.Cu 被占满 → 其他网络交叉 | 先加 B.Cu GND zone + GND 过孔 |
| clearance 0.2mm 默认 | 高密度板布不完（unrouted 多）| 降到 0.1mm（JLC 下限）|
| SES 叠加旧走线 | 导入后 shorting 爆炸 | 导入前删全部走线 |
| 手工补线一次加多条 | 一条错线引入 5-10 shorting，难定位 | 逐条加 + 每步 DRC |
| 电源网络 F.Cu 穿板心 | VIN 等长线穿过元件区 → 交叉 | 电源 class 指定 B.Cu，或 kicad_default 限定 F.Cu |
| 补线路径超出圆板 | 沿 x=-5.8 走 → 圆板半径 7mm 处 x 只能到 ±3.9 | 先算板边界再画路径 |
| pcbnew 删走线后 GetTracks 崩溃 | 删后迭代器失效（SwigPyObject not iterable） | 先收集 `to_remove` 列表再逐个 Remove |
| Remove(zone) 报 thisown 错误 | `board.Remove(z)` AttributeError | zone 用 AddPolygon(chain) 重建覆盖，不删 |

## ngspice 免 sudo 安装（WSL 无 sudo 密码时）

```bash
cd /tmp
apt-get download ngspice libxaw7 libxt6t64 libxmu6 libxpm4 libsm6 libice6
mkdir ngspice_root && for d in ngspice libxaw7 libxt6t64 libxmu6 libxpm4 libsm6 libice6; do dpkg-deb -x ${d}_*.deb ngspice_root; done
LD_LIBRARY_PATH=/tmp/ngspice_root/usr/lib/x86_64-linux-gnu:/tmp/ngspice_root/usr/lib \
  /tmp/ngspice_root/usr/bin/ngspice -b circuit.cir
```

## 小圆板元件选型教训

**SOIC-8 焊盘包络 4.1mm 在 Ø14mm 板上占死中心**（LM358/TLV2372）。换 **SOT-23-5 单运放
（如 TLV9301, Vmax=40V, 包络 2.19mm）** 省一半空间，余量 88% 通过供电电压审查。
选型时实测封装焊盘包络半径：

```python
mr = 0
for pad in fp.Pads():
    pos, size = pad.GetPosition(), pad.GetSize()
    x, y = pos.x/1e6, pos.y/1e6
    w, h = size.x/1e6, size.y/1e6
    for cx, cy in [(x-w/2,y-h/2),(x+w/2,y-h/2),(x-w/2,y+h/2),(x+w/2,y+h/2)]:
        mr = max(mr, math.hypot(cx, cy))
```

高密度布局时：**按焊盘包络半径排序（大元件先放中心）**，用真实焊盘几何做冲突检测
（粗略 bbox 估计法会残留 22 处冲突）。

## 相关 skill

- `pcb-design`（hardware/）— 全栈 PCB 设计自动化（含 A-O 审查清单、SPICE 仿真、Gerber 导出）
- 本 skill 是 pcb-design 的自动布线补充；若 pcb-design 已 adopt 给 curator，建议合并其中布线内容

## 布线后的交付审计

布线 DRC 通过后不等于可交付。**程序化生成的 PCB 默认无丝印**（位号/极性标记缺失），
Gerber 也必须在每次 PCB 修改后重导。走线载流用 IPC-2221 时注意 mil² 单位陷阱，
恒流环验证需 gain=1000 模型，wrdata 输出列是交错重复 sweep 格式。

全部实测细节见 `references/post-routing-audit-lessons.md`。
