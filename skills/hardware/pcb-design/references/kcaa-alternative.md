# kcaa (KiCad AI Assistant) — 多层 PNS 自动布线方案

## 项目信息

| 项目 | 地址 |
|------|------|
| GitHub | https://github.com/paul356/KiCad-AI-Assistant |
| 版本 | 0.1.9 |
| 工具数 | 116 个 |
| 安装路径 | `<KCAA_DIR>/` |
| 启动脚本 | `<D_DRIVE>/Download Softs/KiCad-MCP-Article/kcaa-server.sh` |
| Hermes MCP | `kcaa` server（已配置） |

---

## 与 mixelpixx 对比

| 功能 | mixelpixx | kcaa |
|------|-----------|------|
| 工具数量 | 122 | 116 |
| 多层 PNS 布线 | ❌ 仅单层 | ✅ A* 算法 + 自动过孔 |
| 电路模式识别 | ❌ | ✅ `identify_circuit_patterns` |
| 技能系统 | ❌ | ✅ 内置 `skill_tools` |
| 文档质量 | 高 (10K+ 行) | 中 (精简) |
| WSL 兼容性 | ✅ | ✅ |
| 依赖 KiCad GUI | ❌ | ❌ (独立模式) |

---

## 关键工具

### 多层自动布线

```python
# 单层布线
await pcb_route_pad_to_pad(
    pcb_path="/path/to/board.kicad_pcb",
    ref_a="R1", pad_a="1",
    ref_b="C1", pad_b="1",
    net="VCC",
    layer="F.Cu",
    width=0.5,
)

# 多层布线（自动插入过孔）
await pcb_route_pad_to_pad(
    pcb_path="/path/to/board.kicad_pcb",
    ref_a="R1", pad_a="1",
    ref_b="U1", pad_b="5",
    net="VCC",
    layer="F.Cu",
    target_layer="In1.Cu",
    via_pairs=(("F.Cu", "B.Cu"), ("B.Cu", "In1.Cu")),
)
```

### 电路模式识别

```python
await identify_circuit_patterns(schematic_path="/path/to/schematic.kicad_sch")
```

### 过孔管理

```python
# 单个过孔
await pcb_add_vias(
    pcb_path="/path/to/board.kicad_pcb",
    vias=[{"x": 40.0, "y": 25.0, "net": "GND"}],
)

# 批量过孔（接地缝合/扇出）
await pcb_add_vias(
    pcb_path="/path/to/board.kicad_pcb",
    vias=[
        {"x": 30.0, "y": 35.0, "net": "VCC"},
        {"x": 40.0, "y": 35.0, "net": "GND", "diameter": 1.0, "drill": 0.5},
    ],
)
```

---

## 部署配置

### Hermes MCP 配置

```yaml
mcp_servers:
  kcaa:
    command: bash
    args:
      '0': <D_DRIVE>/Download Softs/KiCad-MCP-Article/kcaa-server.sh
    enabled: true
```

### 环境变量

```bash
KICAD_APP_PATH=<KICAD_DIR>
KICAD_VERSION=10.0
KICAD_USER_DIR=<KICAD_PROJECTS_DIR>
KICAD_SEARCH_PATHS=<KICAD_PROJECTS_DIR>
MCP_TRANSPORT=stdio
```

---

## 安装验证

```bash
cd <KCAA_DIR>
source kcaa-venv/bin/activate
python -c "
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import asyncio, sys, os

async def test():
    params = StdioServerParameters(
        command=sys.executable,
        args=['main.py'],
        env={**os.environ, 
             'KICAD_APP_PATH': '<KICAD_DIR>',
             'KICAD_VERSION': '10.0',
             'KICAD_USER_DIR': '<KICAD_PROJECTS_DIR>',
             'MCP_TRANSPORT': 'stdio'}
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f'Total tools: {len(tools.tools)}')

asyncio.run(test())
"
```

输出应显示：`Total tools: 116`

---

## 文档位置

- 路由指南: `docs/pcb-routing.md`
- 多层设计: `docs/pns-multi-layer-design.md`
- 故障排除: `docs/troubleshooting.md`
- 配置指南: `docs/configuration.md`

---

## 限制说明

1. **kicad-python 模块**需要 KiCad GUI 运行时（仅 IPC 工具需要）
2. **独立模式**使用 skip 库解析 S-expression，不依赖 KiCad GUI
3. **BOM/DRC 工具**部分需要 KiCad GUI 通过 IPC 控制

---

## 使用建议

- 需要多层自动布线 → 选 kcaa（管线 C）
- 单层布线或详细文档需求 → 选 mixelpixx（管线 B）
- 验证/导出任务 → 选 kicad-cli（管线 A）
