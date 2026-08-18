#!/usr/bin/env python3
"""
Freerouting 自动布线一体化脚本（2026-07-31 实测管线）
用法: 在 PCB 生成脚本后调用。前提: board 已有元件+网络（无走线）。
流程: GND过孔+B.Cu铜皮 → 0.1mm规则 → DSN → 改DSN(class限F.Cu) → freerouting → SES导入

依赖:
- KiCad 10 (pcbnew)
- freerouting 2.2.4 linux-x64 解压于 /tmp/fr/freerouting-2.2.4-linux-x64/
  下载: ghproxy.net/https://github.com/freerouting/freerouting/releases/download/v2.2.4/freerouting-2.2.4-linux-x64.zip
"""
import math, os, re, subprocess, sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, SHAPE_LINE_CHAIN

FR_BIN = "/tmp/fr/freerouting-2.2.4-linux-x64/bin/freerouting"
BOARD_PATH = sys.argv[1] if len(sys.argv) > 1 else r"<TEMP_DIR>\board.kicad_pcb"
WORK = "<TEMP_DIR>"  # 无中文路径的工作目录
DSN = os.path.join(WORK, "board.dsn")
SES = os.path.join(WORK, "board.ses")
FR_DRC = os.path.join(WORK, "fr_drc.json")


def add_gnd_vias_and_zone(board):
    """GND 过孔 + B.Cu GND 铜皮（关键前提 1）"""
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == "GND":
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pad.GetPosition())
                via.SetWidth(FromMM(0.6))
                via.SetDrill(FromMM(0.3))
                via.SetNet(board.FindNet("GND"))
                board.Add(via)
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetNet(board.FindNet("GND"))
    chain = SHAPE_LINE_CHAIN()
    n, r = 64, 6.7  # 按板子半径调整 (板半径-0.3)
    for i in range(n):
        a = 2 * math.pi * i / n
        chain.Append(VECTOR2I(FromMM(r * math.cos(a)), FromMM(r * math.sin(a))))
    chain.SetClosed(True)
    zone.AddPolygon(chain)  # 注意: AddPolygon 收 SHAPE_LINE_CHAIN
    zone.SetLocalClearance(FromMM(0.25))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetMinThickness(FromMM(0.2))
    board.Add(zone)


def set_01mm_rules(board):
    """0.1mm clearance（关键前提 2, JLC 制造下限）"""
    ds = board.GetDesignSettings()
    ds.m_Clearance = FromMM(0.1)
    ds.m_TrackMinWidth = FromMM(0.15)
    ds.m_ViasMinSize = FromMM(0.5)
    ds.m_ViasMinDrill = FromMM(0.25)


def patch_dsn(dsn_path):
    """改 DSN: kicad_default class 限定 F.Cu（B.Cu 留给 GND plane）"""
    with open(dsn_path, encoding="utf-8", errors="replace") as f:
        dsn = f.read()
    # 1) clearance 200 -> 100
    dsn = re.sub(r"\(clearance 200\)", "(clearance 100)", dsn)
    # 2) kicad_default class 加 use_layer F.Cu
    old = """(circuit
        (use_via "Via[0-1]_600:300_um")"""
    new = """(circuit
        (use_layer "F.Cu")
        (use_via "Via[0-1]_600:300_um")"""
    dsn = dsn.replace(old, new, 1)
    # 3) 可选: 电源网络指定 B.Cu（把 VIN 换成你的电源网络名）
    # dsn = dsn.replace(
    #     '(net VIN\n      (pins',
    #     '(net VIN\n      (class VIN_CLASS)\n      (pins')
    # vin_class = ('(class VIN_CLASS VIN\n      (circuit\n'
    #              '        (use_via "Via[0-1]_600:300_um")\n'
    #              '      )\n      (rule\n        (width 300)\n      )\n    )\n')
    # dsn = dsn.replace('(class kicad_default', vin_class + '    (class kicad_default')
    with open(dsn_path, "w", encoding="utf-8") as f:
        f.write(dsn)


def run():
    board = pcbnew.LoadBoard(BOARD_PATH)
    add_gnd_vias_and_zone(board)
    set_01mm_rules(board)
    board.Save(BOARD_PATH)

    pcbnew.ExportSpecctraDSN(board, DSN)
    patch_dsn(DSN)

    # 导入前确保无旧走线（从干净板开始）
    if not os.path.exists(SES):
        pass  # 首次运行

    fr = subprocess.run(
        [FR_BIN, "-de", DSN, "-do", SES, "-drc", FR_DRC],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "DISPLAY": ":0"},
    )
    print("freerouting exit:", fr.returncode)
    if os.path.exists(SES):
        # 导入前删旧走线（防叠加）
        for t in list(board.GetTracks()):
            board.Remove(t)
        board = pcbnew.LoadBoard(BOARD_PATH)  # 重载干净的
        pcbnew.ImportSpecctraSES(board, SES)
        board.Save(BOARD_PATH)
        print("SES 导入成功:", SES)
    else:
        print("❌ SES 未生成（freerouting 卡住或失败，检查 -drc 参数）")


if __name__ == "__main__":
    run()
