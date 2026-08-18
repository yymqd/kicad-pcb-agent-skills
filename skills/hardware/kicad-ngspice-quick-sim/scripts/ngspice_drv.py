"""KiCad 自带 ngspice.dll 驱动脚本 (ctypes)
用法: <KiCad python> ngspice_drv.py <网表.cir> [工作目录]
示例: <D_DRIVE>\\Users\\<user>\\AppData\\Local\\Programs\\KiCad\\10.0\\bin\\python.exe ngspice_drv.py netlist.cir <D_DRIVE>\\temp\\sim
"""
import ctypes, sys, os, time

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
print(f"ngspice.dll 加载: {ng}", flush=True)
ng.ngSpice_Init(ctypes.cast(send_char, SendChar),
                ctypes.cast(send_stat, SendStat),
                ctypes.cast(controlled_exit, ControlledExit),
                ctypes.cast(send_data, SendData),
                ctypes.cast(send_init_data, SendInitData),
                ctypes.cast(send_bg, SendBG),
                ctypes.cast(send_running, SendRunning))
ng.ngSpice_Command.argtypes = [ctypes.c_char_p]
ng.ngSpice_Command.restype = ctypes.c_int

def cmd(c):
    ng.ngSpice_Command(c.encode('utf-8'))

cmd(f"cd {workdir}")
cmd(f"source {os.path.basename(cir_path)}")
cmd("run")
time.sleep(0.3)
cmd("quit")
print("\n=== ngspice 完成 ===", flush=True)
