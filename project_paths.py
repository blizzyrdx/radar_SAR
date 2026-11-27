from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
ACQUISITIONS_DIR = PROJECT_ROOT / "acquisitions"
SCANS_DIR = PROJECT_ROOT / "sar_scans"
RESULTS_DIR = PROJECT_ROOT / "results"

HARDWARE_DIR = PROJECT_ROOT / "hardware"
LUA_DIR = HARDWARE_DIR / "lua"
POWERSHELL_DIR = HARDWARE_DIR / "powershell"

POSTPROC_DIR = Path(
    r"C:\ti\mmwave_studio_02_01_01_00"
    r"\mmWaveStudio\PostProc"
)