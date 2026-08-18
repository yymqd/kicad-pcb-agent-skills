# KiCad 执行路线（2026-06-05 确立）

kicad-cli 能做的 → kicad-cli 做
kicad-cli 做不了的 → pcbnew Python 模块（KiCad 官方 API）做
GUI 交互操作 → 永远不走（WSL Wayland 下无法自动化）

可用命令速查：

## kicad-cli 命令
kicad-cli pcb drc <file>              DRC
kicad-cli pcb export gerbers <file>   Gerber
kicad-cli pcb export svg <file>       预览图
kicad-cli pcb export pdf <file>       PDF
kicad-cli pcb export stats <file>     统计报告
kicad-cli pcb export pos <file>       位置表
kicad-cli pcb export glb <file>       3D 模型
kicad-cli pcb render <file>           3D 渲染
kicad-cli pcb export drill <file>     钻孔
kicad-cli pcb upgrade <file>          升级格式

## pcbnew Python 模块（布局布线）
from pcbnew import BOARD, FOOTPRINT, PCB_TRACK, ...
FootprintLoad(lib, name)    加载标准库封装
board.Add(fp)               摆放元件
PCB_TRACK(board)            创建走线
board.Save(path)            保存
board.Zones()               操作覆铜
pcbnew.ExportSpecctraDSN()  导出自动布线文件
