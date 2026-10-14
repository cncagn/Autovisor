import argparse
import os
import shutil
import subprocess
import sys

name = "Autovisor"

# 必须与 modules.installer.SUPPORTED_PYTHON 一致: 冻结产物内嵌的解释器会由
# Autovisor.exe 启动时校验, 不在范围内会直接拒绝运行。
BUILD_PYTHON = ((3, 10), (3, 11), (3, 12), (3, 13))

ROOT = os.path.dirname(os.path.abspath(__file__))
parser = argparse.ArgumentParser(description="构建 Windows 便携版；使用新目录以保留原配置和登录记录")
parser.add_argument("--dist-dir", default=os.path.join(ROOT, "dist"), help="发行目录的父目录")
args = parser.parse_args()
DIST_ROOT = os.path.abspath(args.dist_dir)
OUTPUT = os.path.join(DIST_ROOT, name)
if os.path.exists(OUTPUT):
    raise SystemExit(f"发行目录已存在，为保护配置和登录记录不覆盖: {OUTPUT}\n请使用 --dist-dir 指定新目录。")


def check_build_python():
    """用固定的解释器构建, 避免 PATH 上另一个 pyinstaller 悄悄换掉运行时。"""
    if sys.version_info[:2] not in BUILD_PYTHON:
        supported = ", ".join(f"{major}.{minor}" for major, minor in BUILD_PYTHON)
        raise SystemExit(
            f"构建需要 Python {supported}, 当前是 {sys.version_info[0]}.{sys.version_info[1]}"
            f"({sys.executable}); 否则打包出来的 Autovisor.exe 会在启动时拒绝运行。"
        )
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            f"当前 Python 缺少 PyInstaller: {sys.executable}\n"
            "可执行: uv run --with pyinstaller python build.py"
        ) from exc


check_build_python()

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--log-level=INFO",
    "--noconfirm",
    "-c",
    "-i", os.path.join(ROOT, "resources", "zhs.ico"),
    "--onedir",
    "--contents-directory=internal",
    "--distpath", DIST_ROOT,
    "--workpath", os.path.join(ROOT, "build"),
    "--specpath", ROOT,
    f"--name={name}",
    os.path.join(ROOT, "Autovisor.py"),
    "--exclude-module", "cv2",
    "--exclude-module", "numpy",
]
code = subprocess.call(cmd, cwd=ROOT)
if code != 0:
    raise SystemExit(f"pyinstaller 构建失败: {name} (exit={code})")

os.mkdir(os.path.join(OUTPUT, "resources"))
os.mkdir(os.path.join(OUTPUT, "data"))
for source, destination in (
    ("resources/QRcode.jpg", "resources/QRcode.jpg"),
    ("config.ini.example", "config.ini"),
    ("data/mirrors.json", "data/mirrors.json"),
    ("resources/stealth.min.js", "resources/stealth.min.js"),
    ("LICENSE", "LICENSE"),
):
    shutil.copyfile(os.path.join(ROOT, source), os.path.join(OUTPUT, destination))

# 稳定 ABI (abi3) 扩展(如 opencv 的 cv2.pyd)依赖 python3.dll,
# PyInstaller 不会自动收集,必须随包提供,否则运行时报 "DLL load failed while importing cv2".
python3_dll = os.path.join(sys.base_prefix, "python3.dll")
if os.path.isfile(python3_dll):
    shutil.copyfile(python3_dll, os.path.join(OUTPUT, "internal", "python3.dll"))
else:
    print(f"WARNING: 未找到 {python3_dll}, 发行版可能因缺少 python3.dll 导致 cv2 加载失败!")

# Keep the ignored build directory for diagnostics; never recursively delete
# a caller's working directory or overwrite an existing release's user data.
os.remove(os.path.join(ROOT, "Autovisor.spec"))
