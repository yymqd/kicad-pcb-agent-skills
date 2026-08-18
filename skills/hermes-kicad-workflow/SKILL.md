---
name: hermes-kicad-workflow
description: Pack and distribute KiCad skills to another machine.
---

# Hermes KiCad Skills 打包与分发

## 1. 识别需要打包的内容

KiCad相关skills位于 `~/.hermes/skills/hardware/`：

```bash
ls ~/.hermes/skills/hardware/ | grep -E "(kicad|pcb)"
```

包含7个skills：pcb-design、kicad-*、pcb-*。操作手册位于 `<KICAD_MCP_SERVER_DIR>\docs\`。

## 2. 打包步骤

```bash
mkdir -p /tmp/kicad_package/{skills,hardware_docs}
cp -r ~/.hermes/skills/hardware/kicad-* /tmp/kicad_package/skills/
cp -r ~/.hermes/skills/hardware/pcb-* /tmp/kicad_package/skills/
cp -r "<KICAD_MCP_SERVER_DIR>/docs/"* /tmp/kicad_package/hardware_docs/
cp <D_DRIVE>/Download\ Softs/kicad-10.0.5-x86_64.exe /tmp/kicad_package/ 2>/dev/null || true
cd /tmp && tar -czf kicad_complete_package.tar.gz kicad_package/
```

## 3. 传输到目标机器

如果目标盘符不可挂载，使用PowerShell：

```bash
cp /tmp/kicad_complete_package.tar.gz <WIN_USER_HOME>/Downloads/
powershell.exe -ExecutionPolicy Bypass -Command "Copy-Item '<WIN_USER_HOME>\Downloads\kicad_complete_package.tar.gz' -Destination 'F:\' -Force"
```

## 4. 目标机器安装

```bash
tar -xzf kicad_complete_package.tar.gz
cd kicad_skills_package
mkdir -p ~/.hermes/skills/hardware && cp -r skills/* ~/.hermes/skills/hardware/
cp -r hardware_docs/* "<KICAD_MCP_SERVER_DIR>/docs/"
hermes skills list | grep -E "(kicad|pcb)"
```

## 5. Pitfalls

1. KiCad版本是 10.0.5（不是10.5）
2. WSL默认不挂载所有Windows盘符，需使用PowerShell
3. 确保操作手册路径在 SKILL.md 中正确配置