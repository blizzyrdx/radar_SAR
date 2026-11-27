
import subprocess
from pathlib import Path
import os

PROJECT_DIR = Path(__file__).resolve().parent
BRIDGE = PROJECT_DIR / "rstd_bridge.ps1"


def send_lua(command):

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-File",
            str(BRIDGE),
            "-Command",
            command
        ],
        capture_output=True,
        text=True,
        timeout=60
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def run_lua_script(filename):

    script = PROJECT_DIR / filename

    if not script.is_file():
        raise FileNotFoundError(script)

    path = script.as_posix()

    send_lua(f'dofile([[{path}]])')


if __name__ == "__main__":

    print("Starting automated radar capture...")

    run_lua_script("capture_single.lua")

    print("Remote capture command finished.")
