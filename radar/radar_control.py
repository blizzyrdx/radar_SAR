
import subprocess

from project_paths import POWERSHELL_DIR, LUA_DIR

# ==========================================
# Hardware script paths
# ==========================================

BRIDGE = POWERSHELL_DIR / "rstd_bridge.ps1"


# ==========================================
# Send Lua command to mmWave Studio
# ==========================================

def send_lua(command):

    if not BRIDGE.is_file():
        raise FileNotFoundError(BRIDGE)

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
        raise RuntimeError(
            result.stderr or result.stdout
        )


# ==========================================
# Execute Lua script
# ==========================================

def run_lua_script(filename):

    script = LUA_DIR / filename

    if not script.is_file():
        raise FileNotFoundError(script)

    path = str(script.resolve())

    send_lua(f'dofile([[{path}]])')


# ==========================================
# Main program
# ==========================================

if __name__ == "__main__":

    print("Starting automated radar capture...")

    run_lua_script("capture_single.lua")

    print("Remote capture command finished.")
