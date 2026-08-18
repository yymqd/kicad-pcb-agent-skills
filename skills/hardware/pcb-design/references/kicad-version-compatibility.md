# KiCad Version Compatibility Notes

## KiCad 7 vs 8/9/10 Differences

This project was tested with **KiCad 7.0.11** (Ubuntu 24.04 apt repository version).

**Current latest stable (2026-06): KiCad 10.0.3**

### Version Timeline

| Version | Release Year | Notes |
|---------|-------------|-------|
| 7.0 | 2023 | Ubuntu 24.04 apt 默认版, pcbnew Python API 可用, kicad-cli 基本功能 |
| 8.0 | 2024 | Gerber CLI 导出完整, 部分 API 改名（Vector2i, etc.） |
| 9.0 | 2025 | 更多 kicad-cli 子命令, 新版原理图格式 |
| 10.0 | 2026 | **当前最新**, Windows/macOS/Linux 均稳定 |

### Windows 下载（墙内专用）

阿里云镜像（已验证，~1.9 MB/s 稳定）：

```
curl -C - -L -o kicad-10.0.3-x86_64.exe \
  "https://mirrors.aliyun.com/kicad/windows/stable/kicad-10.0.3-x86_64.exe"
```

备用镜像（同样国内可访问）：
- 清华：`https://mirror.tuna.tsinghua.edu.cn/kicad/windows/stable/kicad-10.0.3-x86_64.exe`

### Known Limitations in KiCad 7

| Feature | KiCad 7 | KiCad 8+ |
|---------|---------|----------|
| `kicad-cli` subcommands | Basic (fp, pcb, sch, sym, version) | Extended |
| S-expression schematic format | 20220121 | 20230121+ |
| `kicad-cli sch export netlist` | ✅ Works | ✅ Works |
| `kicad-cli pcb run_drc` | ✅ Works | ✅ Works |
| Gerber export via CLI | ⚠️ Limited | ✅ Full |
| `kicad-cli pcb export gerber` | Not in 7.0 | ✅ In 8.0+ |

### S-expression Generation Tips

When generating `.kicad_sch` files programmatically:
1. **Version header**: KiCad 7 uses `(kicad_sch (version 20220121))`, KiCad 8+ uses `20230121`
2. **Symbol definitions**: KiCad 7 requires inline `(lib_symbols)` section within the schematic file
3. **UUIDs**: Every component and net needs unique UUIDs. Generate with Python's `uuid.uuid4()`
4. **Footprint assignments**: KiCad 7 uses `(property "Footprint" "...")` on the symbol instance
5. **Net wiring**: Simple RC filters don't need explicit net definitions in KiCad 7 S-expr — the schematic is mainly visual. For proper netlisting, use `kicad-cli sch export netlist`

### Fallback: Text-Only Schematic Generation

If KiCad CLI is unavailable or the version doesn't support the needed features, generate a text-based schematic description instead. This is a human-readable circuit diagram that can be manually recreated in KiCad.

### Installing KiCad 8+ on Ubuntu

```bash
# KiCad 8+ is not in Ubuntu 24.04 repos
# Option 1: Use KiCad official PPA (recommended — handles upgrade automatically)
sudo add-apt-repository --yes ppa:kicad/kicad-10.0-releases
sudo apt update
sudo apt install --install-recommends kicad
kicad-cli --version   # 验证: 10.0.3

# PPA 自动覆盖 apt 旧版本，无需先卸载
# 旧 apt 源记录会保留但 PPA 版本优先级更高

# Option 2: Use flatpak
flatpak install flathub org.kicad.KiCad
```

### KiCad 10 Specific API Changes (vs KiCad 7)

| KiCad 7 API | KiCad 10 API | Notes |
|-------------|-------------|-------|
| `BOARD.GetFileFormatVersion()` | `BOARD.GetFileFormatVersionAtLoad()` | 仅返回加载时的版本号，非 BOARD 版本 |
| `BOARD.GetTrackCount()` | removed | 不再直接提供；用 `list(board.Tracks())` |
| `ZONE()` constructor | unchanged | 仍可用 |
| `PLOT_CONTROLLER.OpenLayer()` | different API | KiCad 10 使用不同的绘图控制器接口；优先用 kicad-cli 导出 |
| `fp.SetPosition(VECTOR2I(...))` | `fp.SetPosition(VECTOR2I(...))` | VECTOR2I 签名不变（KiCad 8 曾用 Vector2i 别名） |
| S-expression version header | 20220121 → 20260206 | 生成 `.kicad_pcb` 文件时 version 必须匹配 KiCad 10 格式 |
| PCB file format | version=20221018 | version=20260206 |

### pcbnew Module Verification (KiCad 10)

```bash
python3 -c "
import pcbnew
board = pcbnew.BOARD()
print('BOARD: OK')
print('FileFormatVersionAtLoad:', board.GetFileFormatVersionAtLoad())
print('DesignPath:', board.GetDesignPath())
"""
```

注意：初始化时可能打印 property.h assert 警告（`m_choices.GetCount() > 0`），这是编译调试遗留，不影响功能。
