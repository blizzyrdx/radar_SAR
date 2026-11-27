
from project_paths import (
    PROJECT_ROOT,
    LUA_DIR,
    POWERSHELL_DIR
)

from radar.radar_session import BRIDGE as PERSISTENT_BRIDGE
from radar.radar_control import BRIDGE as SINGLE_BRIDGE


# ==========================================
# Project directory tests
# ==========================================

def test_project_root():
    assert PROJECT_ROOT.is_dir()


def test_cli_exists():
    assert (PROJECT_ROOT / "sar.py").is_file()


def test_radar_package():
    assert (PROJECT_ROOT / "radar").is_dir()


def test_imaging_package():
    assert (PROJECT_ROOT / "imaging").is_dir()


def test_experiments_package():
    assert (PROJECT_ROOT / "experiments").is_dir()


def test_lua_directory():
    assert LUA_DIR.is_dir()


def test_powershell_directory():
    assert POWERSHELL_DIR.is_dir()


# ==========================================
# Hardware script tests
# ==========================================

def test_radar_initialization_script():
    assert (LUA_DIR / "radar_init.lua").is_file()


def test_capture_script():
    assert (LUA_DIR / "capture_single.lua").is_file()


def test_batch_capture_script():
    assert (LUA_DIR / "capture_batch.lua").is_file()


def test_dca_configuration_script():
    assert (LUA_DIR / "configure_dca1000.lua").is_file()


def test_persistent_bridge():
    assert PERSISTENT_BRIDGE.is_file()


def test_single_bridge():
    assert SINGLE_BRIDGE.is_file()


def test_persistent_bridge_location():
    assert PERSISTENT_BRIDGE.parent == POWERSHELL_DIR


def test_single_bridge_location():
    assert SINGLE_BRIDGE.parent == POWERSHELL_DIR
