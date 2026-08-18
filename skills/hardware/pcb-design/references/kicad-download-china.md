# KiCad 国内下载指南（墙内专用）

**背景**：KiCad 官网（CERN 服务器）在国内下载极慢且容易中断。国内镜像已验证可用。

## 当前最新稳定版

| 版本 | 发布日期 | 架构 | 文件 |
|:----|:---------|:----|:----|
| **10.0.3** | 2026-05 | x86_64 | `kicad-10.0.3-x86_64.exe` (≈922MB) |
| **10.0.3** | 2026-05 | arm64 | `kicad-10.0.3-arm64.exe` |

## 镜像源（在国内均直连可用）

按优先级排列：

| 镜像 | 速度 | 说明 |
|:----|:----:|:-----|
| **阿里云** `mirrors.aliyun.com` | ⭐ ~1.9 MB/s | **首选，实测稳定** |
| **清华 TUNA** `mirror.tuna.tsinghua.edu.cn` | ⭐ ~1.5 MB/s | 备选，速度相当 |

## 下载命令（阿里云 + curl 续传）

```bash
# x86_64 桌面版（最常用）
curl -C - -L -o kicad-10.0.3-x86_64.exe \
  "https://mirrors.aliyun.com/kicad/windows/stable/kicad-10.0.3-x86_64.exe"

# arm64 版
curl -C - -L -o kicad-10.0.3-arm64.exe \
  "https://mirrors.aliyun.com/kicad/windows/stable/kicad-10.0.3-arm64.exe"

# 清华 TUNA 备用
curl -C - -L -o kicad-10.0.3-x86_64.exe \
  "https://mirror.tuna.tsinghua.edu.cn/kicad/windows/stable/kicad-10.0.3-x86_64.exe"
```

**关键参数说明：**
- `-C -` — 自动续传。下载中断后重跑同一命令继续，不重头开始
- `-L` — 跟随重定向
- 国内镜像无需翻墙，直连即可

## 安装后验证

```bash
# Windows 上安装后，验证 CLI 可用
# 在 cmd.exe 或 PowerShell 中运行：
kicad-cli --version
# 应输出：KiCad 10.0.3

# 验证 pcbnew Python API
python -c "import pcbnew; print('pcbnew OK')"
```

## 历史版本

旧版本在国内镜像同样可用，只需替换版本号：

```
https://mirrors.aliyun.com/kicad/windows/stable/kicad-8.0.0-x86_64.exe
https://mirrors.aliyun.com/kicad/windows/stable/kicad-7.0.11-x86_64.exe
```

## 验证数字签名（可选）

安装前用 Windows 右键 → 属性 → 数字签名，验证签名者为 **KICAD SERVICES CORPORATION**。

## 已知问题

1. **下载中断**：大文件（~1GB）在墙内可能不稳定。用 `curl -C -` 续传即可，不需要重新下载
2. **多用户环境**：下载路径不要有中文空格以外字符，避免转义问题
3. **WSL 与 Windows 双版本共存**：WSL 版（apt install kicad→7.0.11）和 Windows 版（10.0.3）可以共存，互不影响

## 安装后的路径

Windows 版 KiCad 默认安装在 per-user 路径（非 Program Files）：

```
<D_DRIVE>\Users\<用户名>\AppData\Local\Programs\KiCad\<版本号>\bin\kicad.exe
<D_DRIVE>\Users\<用户名>\AppData\Local\Programs\KiCad\<版本号>\bin\kicad-cli.exe
```

从 WSL 访问该路径：
```bash
ls <D_DRIVE>/Users/*/AppData/Local/Programs/KiCad/*/bin/kicad-cli.exe
```

如需从 WSL 调用 Windows KiCad CLI，见 `hermes-pcb-design` skill 的 `references/wsl-windows-kicad-bridge.md`。
