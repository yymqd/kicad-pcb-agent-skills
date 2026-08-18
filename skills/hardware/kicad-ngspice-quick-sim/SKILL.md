---
name: kicad-ngspice-quick-sim
description: Run SPICE on KiCad with its bundled ngspice.dll.
trigger: "User asks to run SPICE simulation on a KiCad project (DC/AC/sweep/transient), especially in WSL without standalone ngspice, or asks to use KiCad's built-in simulator."
---

# KiCad ngspice 快速仿真工作流

**上游路由**: 由 pcb-design（伞形主 skill）在 Phase 3 仿真阶段触发；本 skill 是聚焦 skill，只处理仿真任务。完整设计/审查请回 pcb-design。

在 WSL/无独立 ngspice 环境下，用 **KiCad 安装自带的 `ngspice.dll`**（标准 ngspice shared library）跑仿真。2026-07-31 实测：从改参数到出结果 <1 秒。

## 前置条件

- KiCad 10.0.3 Windows 安装（`<D_DRIVE>\Users\<user>\AppData\Local\Programs\KiCad\10.0\bin\ngspice.dll`）
- WSL 的 Linux python **不能**加载 Windows DLL → 必须用 **KiCad 自带 python.exe** 跑驱动脚本
- 网表/脚本放 `<TEMP_DIR>/` 类路径（避免中文路径问题）

## 核心：ctypes 驱动脚本（ngspice_drv.py）

```python
"""用 KiCad 自带 ngspice.dll (ctypes) 跑 SPICE 网表
用法: python ngspice_drv.py <网表.cir> [工作目录]"""
import ctypes, sys, os

KICAD_BIN = r"<D_DRIVE>\Users\<user>\AppData\Local\Programs\KiCad\10.0\bin"
os.add_dll_directory(KICAD_BIN)
os.chdir(KICAD_BIN)  # 依赖 DLL 解析

cir_path = sys.argv[1]
workdir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(cir_path))
os.chdir(workdir)

SendChar = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int)
SendStat = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int)
ControlledExit = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
SendData = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
SendInitData = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int)
SendBG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int)
SendRunning = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int)

@SendChar
def send_char(msg, ident):
    if msg:
        sys.stdout.write(msg.decode('utf-8', 'replace')); sys.stdout.flush()

@SendStat
def send_stat(msg, ident):
    if msg:
        sys.stderr.write("STAT: " + msg.decode('utf-8', 'replace')); sys.stderr.flush()

@ControlledExit
def controlled_exit(status, immediate, ident): return 0

@SendData
def send_data(data, num_vecs, ident): return 1

@SendInitData
def send_init_data(vecnames, num_vecs, ident): return 1

@SendBG
def send_bg(running, ident): return 1

@SendRunning
def send_running(running, ident): return 1

ng = ctypes.CDLL(os.path.join(KICAD_BIN, "ngspice.dll"))
ng.ngSpice_Init(ctypes.cast(send_char, SendChar),
                ctypes.cast(send_stat, SendStat),
                ctypes.cast(controlled_exit, ControlledExit),
                ctypes.cast(send_data, SendData),
                ctypes.cast(send_init_data, SendInitData),
                ctypes.cast(send_bg, SendBG),
                ctypes.cast(send_running, SendRunning))

ng.ngSpice_Command.argtypes = [ctypes.c_char_p]
ng.ngSpice_Command.restype = ctypes.c_int
def cmd(c): ng.ngSpice_Command(c.encode('utf-8'))

cmd(f"cd {workdir}")
cmd(f"source {os.path.basename(cir_path)}")
cmd("run")
import time; time.sleep(0.3)
cmd("quit")
print("\n=== ngspice 完成 ===")
```

运行：`<D_DRIVE>\Users\<user>\AppData\Local\Programs\KiCad\10.0\bin\python.exe ngspice_drv.py netlist.cir <workdir>`

## 网表模板

### DC/扫描实验（netlist_b 模式）

```spice
* 关键: .control 批处理 + print 输出 (wrdata 列序不可靠!)
VIN VIN 0 DC 5
VTTL TTL 0 DC 5
.control
op
print v(vout) v(vsns) v(gate) v(en)
alter vttl dc 0
op
print v(vout) v(vsns)
alter vttl dc 5
op
print v(vout) v(vsns)
alter vin dc 4.5
op
print v(vout) v(vsns) v(vref)
alter vin dc 5
altermod ld520 n=3.2
op
print v(vsns)
.endc
.end
```

### AC 稳定性（闭环峰值法，netlist_e 模式）

```spice
* 闭环峰值法: VREF 串 AC 源测 H=VSNS/VREF_ac
* 判据: 峰 >3dB ⇒ PM<45° 欠阻尼; <1dB ⇒ PM>60° 稳定
R3 VIN VR3 33k
VAC VR3 VREF DC 0 AC 1
R4 VREF 0 1.2k
.control
op
ac dec 30 1 10Meg
wrdata ac_closed.txt v(vsns) v(gate) v(vref)
.endc
.end
```

AC 解析：`H = VSNS/VREF`（注意 wrdata 每向量前有重复索引列 [t,v1,t,v2,...]），找 |H| 峰值 vs 低频值。

## ⚠️ KiCad ngspice 精简限制（实测，直接用避免踩坑）

| 功能 | 状态 | 替代 |
|---|---|---|
| `.meas` 命令 | ❌ "no such command" | `.control` 里 `print` 或 wrdata+Python |
| `VALUE={IF(c,a,b)}` | ❌ "no such function 'if'" | `min/max` 组合（如 `5.6*min(max(V(EN),0),1)`） |
| `print v(x) at=1.5m` | ❌ "vector at not available" | wrdata 全数据 + Python 过滤 |
| `wrdata` 列序 | ⚠️ 每向量前重复索引列 | 解析跳奇数列，或直接用 `print` |
| S 开关 (SW model) | ⚠️ op 时数值发散（VOUT=-789V 假象） | E 源 VALUE+min/max 替代 |
| 运放断环法 | ⚠️ 断环后运放输出饱和，\|T\| 测不出 | **闭环峰值法**（标准判据） |

## ⛔ 模型保真度检查清单（仿真结果可信的前提）

| 检查项 | 错误案例 | 正确 |
|---|---|---|
| 运放总增益 | 两级 1e5×1e5=1e10(200dB) | 总增益=各级乘积=数据手册开环增益 |
| 运放 GBW | fp×A 算错（1e11Hz） | GBW=fp×A0；TLV9301: fp=10Hz,A=1e5 → 1MHz |
| LD 模型 Vf | Vf@80mA=1.6V（真实 4-5V） | 算 Vf=I·N·Vt·ln(I/Is)+I·Rs 覆盖真实范围 |
| MOSFET 单向性 | 无 VDS 限制→灭态假象 | `I=...*min(max(V(D,S)*1e2,0),1)` |
| Ciss 建模 | 缺栅极电容→稳定性乐观 | 补 CGS（SI2302≈400pF）——R6×Ciss 极点常是 PM 不足根因 |
| 开关级缺失 | 无 Boost 开关→VOUT 直通 | Boost 级用 E 源理想模型（稳态值由分压计算保证）+ E.4 声明 |
| 网表可复现性 | 报告数据与网表不符 | 报告必须关联实际 .cir 路径，可重跑 |

## 工作流（5 分钟标准流程）

1. 复制模板网表（DC 或 AC 版）→ 改参数
2. `ngspice_drv.py netlist.cir workdir` 运行
3. grep `v(x) =` 读结果
4. 关键判定：DC 工作点 / 扫描曲线 / AC 峰值（PM 判据）
5. 结果写入仿真报告（含网表路径，可复现）

## Pitfalls

- 中文路径 → 网表和工作目录放 `<TEMP_DIR>/` 或纯 ASCII 路径
- 输出重定向 `> file.txt` 时 cmd 编码问题 → 用管道直接看，或读文件时 UTF-8
- `board.Remove()` 后 swig 容器失效（PCB 脚本用，仿真无关但同环境注意）
- 运放模型大信号 tran 动态不足（内部节点 τ 大）→ DC/AC 可信，tran 波形谨慎（记录 E.4）
- 修改网表参数后必须重跑验证（仿真报告数据要有对应网表版本）

## 验证过的完整实例

- 520nmLD_Driver（2026-07-31）：`<TEMP_DIR>\ld520_v2\netlist_b.cir`（DC/扫描 8 实验）+ `netlist_e.cir`（AC 稳定性）——完整可复现，从改参到结果 <1s
