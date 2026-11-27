
import time
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

from radar.radar_session import RadarSession
from radar.packet_validator import validate_packets
from radar.radar_config import CONFIG

# ==========================================
# Directories
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

POSTPROC_DIR = Path(
    r"C:\ti\mmwave_studio_02_01_01_00"
    r"\mmWaveStudio\PostProc"
)

OUTPUT_DIR = PROJECT_DIR / "acquisitions"
OUTPUT_DIR.mkdir(exist_ok=True)

# ==========================================
# Radar configuration
# ==========================================

NUM_RX = CONFIG.num_rx
NUM_SAMPLES = CONFIG.num_samples
NUM_CHIRPS = CONFIG.num_chirps
NUM_FRAMES = CONFIG.num_frames

EXPECTED_BYTES = CONFIG.expected_bytes

# ==========================================
# Verify captured file
# ==========================================

def verify_capture(path, timeout=30):

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:

        if path.exists():

            size = path.stat().st_size

            if size == EXPECTED_BYTES:

                # Check that file writing has settled
                time.sleep(1)

                if path.stat().st_size == size:
                    return

            elif size > EXPECTED_BYTES:
                raise ValueError(
                    f"Unexpected file size: {size}"
                )

        time.sleep(0.5)

    raise TimeoutError(
        f"Recording missing or incomplete: {path}"
    )


# ==========================================
# File integrity verification
# ==========================================

def file_hash(path):

    with open(path, "rb") as file:
        return hashlib.file_digest(
            file, "sha256"
        ).hexdigest()


# ==========================================
# Automated acquisition
# ==========================================

def acquire(radar):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    name = f"capture_{timestamp}"
    filename = name + ".bin"

    source = POSTPROC_DIR / filename
    destination = OUTPUT_DIR / filename

    if source.exists() or destination.exists():
        raise FileExistsError(filename)

    # Preserve Windows backslashes
    lua_path = str(source)

    print(f"\nStarting acquisition: {filename}")

    # Generate Lua acquisition commands
    lua = f"""
    ar1.SelectCaptureDevice("DCA1000")

    WriteToLog("Arming DCA1000...\\n", "green")

    local status = ar1.CaptureCardConfig_StartRecord(
        [[{lua_path}]], 1
    )

    if status ~= 0 then
        error("DCA1000 ARM failed")
    end

    RSTD.Sleep(3000)

    WriteToLog("Triggering radar...\\n", "green")

    status = ar1.StartFrame()

    if status ~= 0 then
        error("Frame trigger failed")
    end

    RSTD.Sleep(8000)

    WriteToLog("Processing captured data...\\n", "green")

    ar1.StartMatlabPostProc([[{lua_path}]])
    """

    # Save generated Lua script
    script = OUTPUT_DIR / (name + ".lua")
    script.write_text(lua, encoding="ascii")

    # Execute using persistent radar connection
    radar.send(
        f'dofile([[{str(script)}]])',
        timeout=60
    )

    # ======================================
    # Verify recording size
    # ======================================

    print("Verifying recorded data...")

    verify_capture(source)

    print("File size verification: PASS")

    # ======================================
    # Copy recording to project
    # ======================================

    shutil.copy2(source, destination)

    # Verify copied file integrity
    source_hash = file_hash(source)
    destination_hash = file_hash(destination)

    if source_hash != destination_hash:
        raise IOError("File copy verification failed")

    print("SHA256 verification: PASS")

    # ======================================
    # Preserve capture logs
    # ======================================

    for log in POSTPROC_DIR.glob(name + "*"):

        if log.suffix.lower() in (".txt", ".csv"):
            shutil.copy2(
                log,
                OUTPUT_DIR / log.name
            )

    # ======================================
    # Automatic packet integrity validation
    # ======================================

    print("\nValidating packet integrity...")

    if not validate_packets(destination):

        print("\n================================")
        print("ACQUISITION REJECTED")
        print("================================")

        print("Reason: Packet integrity validation failed.")
        print(f"Recording: {destination.name}")
        print("Files preserved for diagnostics.")

        raise RuntimeError(
            "Recording rejected due to packet loss "
            "or unexpected packet statistics."
        )

    # ======================================
    # Display successful acquisition results
    # ======================================

    print("\n================================")
    print("ACQUISITION SUCCESSFUL")
    print("================================")

    print(f"File: {destination.name}")
    print(f"Size: {destination.stat().st_size} bytes")
    print(f"Expected size: {EXPECTED_BYTES} bytes")
    print(f"SHA256: {destination_hash}")
    print("Packet integrity: PASS")
    print(f"Saved to: {OUTPUT_DIR}")

    return destination


# ==========================================
# Main program
# ==========================================

if __name__ == "__main__":

    radar = RadarSession()

    try:

        acquire(radar)

    finally:

        radar.close()
