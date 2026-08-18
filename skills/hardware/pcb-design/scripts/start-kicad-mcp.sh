#!/bin/bash
# KiCad MCP Server 启动脚本 (WSL → Windows)
# 从 WSL 调用 Windows PowerShell 启动 KiCad MCP

powershell.exe -Command "
`$env:PYTHONPATH = '<KICAD_DIR>\bin\Lib\site-packages;<KICAD_DIR>\bin\DLLs'
`$env:KICAD_PYTHON = '<KICAD_DIR>\bin\python.exe'
`$env:NODE_ENV = 'production'
`$env:LOG_LEVEL = 'info'
node '<KICAD_MCP_SERVER_DIR>\dist\index.js'
"
