# WSL → Windows KiCad MCP 桥接模式

## 问题背景

KiCad MCP Server 是 Windows 原生应用，依赖：
1. Windows PowerShell 运行
2. KiCad Python 模块（pcbnew）
3. Windows 文件系统路径（`<D_DRIVE>\Program Files\...`）

在 WSL 中无法直接运行，需要通过 `powershell.exe` 桥接。

## 解决方案

### 启动脚本模式

创建 bash 脚本包装 PowerShell 调用：

```bash
#!/bin/bash
# start-kicad-mcp.sh
powershell.exe -Command "
`$env:PYTHONPATH = '<KICAD_DIR>\bin\Lib\site-packages'
`$env:KICAD_PYTHON = '<KICAD_DIR>\bin\python.exe'
`$env:NODE_ENV = 'production'
node '<KICAD_MCP_SERVER_DIR>\dist\index.js'
"
```

### Hermes MCP 配置

```yaml
mcp_servers:
  kicad:
    command: bash
    args:
    - ~/.hermes/skills/hardware/pcb-design/scripts/start-kicad-mcp.sh
    enabled: true
```

## 环境变量传递

| 变量 | 值 | 说明 |
|------|-----|------|
| `KICAD_PYTHON` | `<KICAD_DIR>\bin\python.exe` | KiCad 内置 Python |
| `PYTHONPATH` | `<KICAD_DIR>\bin\Lib\site-packages` | pcbnew 模块路径 |
| `NODE_ENV` | `production` | 生产模式 |

## 已知问题

### 1. PowerShell 变量转义
在 bash heredoc 中，PowerShell 变量需用反引号转义：
```bash
`$env:VAR = 'value'
```

### 2. 路径分隔符
- Windows: `<D_DRIVE>\Program Files\...`
- WSL 访问: `<D_DRIVE>/Program Files\...`
- PowerShell 内部: 使用 Windows 路径格式

### 3. 首次启动较慢
Python 进程初始化需要 5-10 秒，首次调用可能超时。

## 调试技巧

### 测试 KiCad Python 可用性
```bash
"<KICAD_DIR>/bin/python.exe" -c "import pcbnew; print(pcbnew.GetBuildVersion())"
```

### 测试 Node.js 启动
```bash
node "<KICAD_MCP_SERVER_DIR>/dist/index.js" 2>&1 | head -20
```

### 检查 Hermes MCP 状态
```bash
hermes mcp list | grep kicad
```

## 跨平台工具桥接通用模式

此模式适用于所有需要在 Windows 上运行但从 WSL 调用的 MCP Server：

1. 创建 `scripts/start-xxx.sh` 启动脚本
2. 使用 `powershell.exe -Command` 包装
3. 在 Hermes config.yaml 中配置 command: bash, args: [启动脚本路径]
4. 首次启动可能需要等待 Python/Node 进程初始化
