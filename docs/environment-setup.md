# 环境适配指南

本仓库内容基于 **WSL (Ubuntu 24.04) + Windows KiCad 10.0.x** 实测沉淀。
所有路径已匿名化为占位符，请根据你的环境替换。

## 占位符对照表

| 占位符 | 默认值（本项目原始环境） | 说明 |
|---|---|---|
| `<KICAD_DIR>` | `D:\Program Files\KiCad\10.0` | KiCad 安装目录（含 bin/kicad-cli.exe、bin/python.exe） |
| `<KICAD_MCP_SERVER_DIR>` | `D:\Download Softs\KiCAD-MCP-Server` | mixelpixx/KiCAD-MCP-Server 源码目录 |
| `<KCAA_DIR>` | `D:\Download Softs\KiCad-MCP-Article\KiCad-AI-Assistant` | kcaa (paul356) 安装目录 |
| `<KICAD_PROJECTS_DIR>` | `D:\KiCadProjects` | KiCad 项目工作目录 |
| `<PROJECT_DIR>` | `D:\电路设计` | 具体项目根目录 |
| `<TEMP_DIR>` | `D:\temp` | 中间文件目录（SPICE 网表、DSN/SES） |
| `<D_DRIVE>` | `D:` | Windows D 盘在 WSL 下的挂载 |
| `<C_DRIVE>` | `C:` | Windows C 盘在 WSL 下的挂载 |
| `<WIN_USER_HOME>` | `C:\Users\yymqd` | Windows 用户主目录 |
| `<user>` | 任意 | 通用用户名占位符 |

## 三条管线的安装

### 管线 A：kicad-cli（必需）
```bash
# Windows: 安装 KiCad 10.x
# WSL: 若需 WSL 内运行（不推荐，Windows 版本功能全）
sudo add-apt-repository --yes ppa:kicad/kicad-10.0-releases
sudo apt update && sudo apt install --install-recommends kicad
kicad-cli --version
```

### 管线 B：MCP-KiCad (mixelpixx)
```bash
# Windows: 克隆并构建
git clone https://github.com/mixelpixx/KiCAD-MCP-Server.git <KICAD_MCP_SERVER_DIR>
cd <KICAD_MCP_SERVER_DIR> && npm install && npm run build
# WSL 桥接：使用 scripts/start-kicad-mcp.sh（需配置 KICAD_PYTHON/PYTHONPATH）
```

### 管线 C：kcaa (paul356)
```bash
git clone https://github.com/paul356/KiCad-AI-Assistant.git <KCAA_DIR>
cd <KCAA_DIR> && python -m venv kcaa-venv && source kcaa-venv/bin/activate
pip install -r requirements.txt
# 环境变量
export KICAD_APP_PATH=<KICAD_DIR>
export KICAD_VERSION=10.0
export KICAD_USER_DIR=<KICAD_PROJECTS_DIR>
export KICAD_SEARCH_PATHS=<KICAD_PROJECTS_DIR>
export MCP_TRANSPORT=stdio
```

## Hermes MCP 配置示例

```yaml
mcp_servers:
  kicad:
    command: bash
    args:
      - <KICAD_MCP_SERVER_DIR>/start-kicad-mcp.sh   # WSL 桥接脚本
    enabled: true
  kcaa:
    command: bash
    args:
      - <KCAA_DIR>/kcaa-server.sh
    enabled: true
```

## 已知环境差异

| 环境 | 差异 | 应对 |
|---|---|---|
| KiCad 7 | pcbnew API 差异显著 | 读 `pcb-design/references/kicad7-pcbnew-api.md` |
| KiCad 8/9 | 介于 7 和 10 之间 | 主要命令兼容，细节需实测 |
| 纯 Linux（无 Windows KiCad） | 无 ngspice.dll、无 Windows GUI | 用 apt 装 ngspice；走 kicad-cli |
| 无 WSL（纯 Windows） | 无 /mnt/ 挂载 | 路径直接写盘符 |

## 验证安装

```bash
# 检查 KiCad CLI
kicad-cli --version
# 检查 MCP 服务器
hermes mcp list | grep -E "(kicad|kcaa)"
# 检查 pcbnew 可用性（Windows 端）
"<KICAD_DIR>/bin/python.exe" -c "import pcbnew; print(pcbnew.GetBuildVersion())"
```
