
import numpy as np
import matplotlib.pyplot as plt
import hashlib
import sys

from pathlib import Path

# ==========================================
# Radar configuration
# ==========================================

NUM_RX = 4
NUM_SAMPLES = 512
NUM_CHIRPS = 128
NUM_FRAMES = 8

ADC_BITS = 16

EXPECTED_VALUES = (
    NUM_FRAMES * NUM_CHIRPS *
    NUM_RX * NUM_SAMPLES * 2
)

EXPECTED_BYTES = EXPECTED_VALUES * 2

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "acquisitions"

# ==========================================
# Find latest recording
# ==========================================

def latest_recording():

    files = [
        path for path in DATA_DIR.glob("capture_*.bin")
        if "_Raw_" not in path.name
    ]

    if not files:
        raise FileNotFoundError(
            "No processed radar recordings found."
        )

    return max(
        files,
        key=lambda path: path.stat().st_mtime
    )


# ==========================================
# Find longest consecutive zero sequence
# ==========================================

def longest_zero_run(raw):

    zeros = raw == 0

    padded = np.concatenate(
        ([False], zeros, [False])
    )

    edges = np.diff(padded.astype(np.int8))

    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]

    if starts.size == 0:
        return 0

    return int(np.max(ends - starts))


# ==========================================
# Inspect recording logs
# ==========================================

def inspect_logs(path):

    print("\n========== CAPTURE LOGS ==========")

    logs = list(
        path.parent.glob(path.stem + "*.csv")
    )

    logs += list(
        path.parent.glob(path.stem + "*.txt")
    )

    if not logs:
        print("No associated capture logs found.")
        print("Packet loss has NOT been verified.")
        return

    for log in logs:

        print(f"\nLog: {log.name}")

        content = log.read_text(
            encoding="utf-8",
            errors="replace"
        )

        keywords = (
            "packet", "lost", "loss",
            "drop", "zero", "error",
            "missing", "received"
        )

        matches = [
            line for line in content.splitlines()
            if any(
                word in line.lower()
                for word in keywords
            )
        ]

        if matches:
            for line in matches:
                print(line)
        else:
            print("No packet statistics identified.")

    print("\nReview packet statistics before")
    print("considering packet integrity verified.")


# ==========================================
# Analyze radar recording
# ==========================================

def analyze(path):

    print("\n========== RADAR INTEGRITY ==========")

    print(f"Recording: {path.name}")
    print(f"Actual bytes:   {path.stat().st_size}")
    print(f"Expected bytes: {EXPECTED_BYTES}")

    if path.stat().st_size != EXPECTED_BYTES:
        raise ValueError("Incorrect recording size")

    print("File size: PASS")

    with open(path, "rb") as file:
        digest = hashlib.file_digest(
            file, "sha256"
        ).hexdigest()

    print(f"SHA256: {digest}")

    raw = np.fromfile(path, dtype="<i2")

    # ======================================
    # ADC statistics
    # ======================================

    zero_count = np.count_nonzero(raw == 0)
    zero_percent = 100 * zero_count / raw.size

    longest_run = longest_zero_run(raw)

    adc_min = -(2 ** (ADC_BITS - 1))
    adc_max = 2 ** (ADC_BITS - 1) - 1

    saturated = np.count_nonzero(
        (raw == adc_min) | (raw == adc_max)
    )

    saturation_percent = (
        100 * saturated / raw.size
    )

    print("\n========== ADC STATISTICS ==========")

    print(f"ADC values: {raw.size}")
    print(f"Minimum: {raw.min()}")
    print(f"Maximum: {raw.max()}")
    print(f"Mean: {raw.mean():.4f}")
    print(f"Standard deviation: {raw.std():.4f}")
    print(f"Zero values: {zero_count}")
    print(f"Zero percentage: {zero_percent:.4f}%")
    print(f"Longest zero run: {longest_run}")
    print(f"Saturated values: {saturated}")
    print(f"Saturation: {saturation_percent:.6f}%")

    # ======================================
    # Decode complex I/Q
    # ======================================

    groups = raw.reshape(-1, 4).astype(np.float32)

    iq = (
        groups[:, :2] +
        1j * groups[:, 2:]
    ).flatten()

    cube = iq.reshape(
        NUM_FRAMES,
        NUM_CHIRPS,
        NUM_RX,
        NUM_SAMPLES
    )

    print(f"\nRadar cube: {cube.shape}")

    power = np.abs(cube) ** 2

    # ======================================
    # RX channel integrity
    # ======================================

    rx_power = np.mean(
        power,
        axis=(0, 1, 3)
    )

    print("\n========== RX CHANNEL POWER ==========")

    for i, value in enumerate(rx_power):
        print(f"RX{i}: {value:.2f}")

    # ======================================
    # Frame integrity
    # ======================================

    frame_power = np.mean(
        power,
        axis=(1, 2, 3)
    )

    print("\n========== FRAME POWER ==========")

    for i, value in enumerate(frame_power):
        print(f"Frame {i + 1}: {value:.2f}")

    # ======================================
    # Diagnostic warnings
    # ======================================

    warnings = []

    if saturated > 0:
        warnings.append(
            "ADC full-scale clipping detected."
        )

    # Preliminary heuristic, not a TI specification
    if longest_run >= 128:
        warnings.append(
            "Long zero sequence detected."
        )

    if np.any(rx_power == 0):
        warnings.append(
            "At least one RX channel is entirely zero."
        )

    if np.any(frame_power == 0):
        warnings.append(
            "At least one frame is entirely zero."
        )

    print("\n========== DIAGNOSTICS ==========")

    if warnings:
        for warning in warnings:
            print("WARNING:", warning)
    else:
        print("No obvious ADC anomalies detected.")

    inspect_logs(path)

    # ======================================
    # Visualization
    # ======================================

    plt.figure(figsize=(9, 5))

    plt.hist(raw, bins=150)
    plt.title("ADC Sample Distribution")
    plt.xlabel("ADC Value")
    plt.ylabel("Count")
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.figure(figsize=(8, 5))

    plt.bar(
        ["RX0", "RX1", "RX2", "RX3"],
        rx_power
    )

    plt.title("Receiver Channel Power")
    plt.ylabel("Mean Power")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    plt.figure(figsize=(8, 5))

    plt.plot(
        np.arange(1, NUM_FRAMES + 1),
        frame_power,
        marker="o"
    )

    plt.title("Radar Frame Power Stability")
    plt.xlabel("Frame Number")
    plt.ylabel("Mean Power")
    plt.grid(True)
    plt.tight_layout()

    plt.figure(figsize=(10, 5))

    samples = cube[0, 0, 0, :]

    plt.plot(samples.real, label="I")
    plt.plot(samples.imag, label="Q")

    plt.title("Raw Complex ADC Signal - RX0")
    plt.xlabel("ADC Sample")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.show()


# ==========================================
# Main program
# ==========================================

if __name__ == "__main__":

    if len(sys.argv) > 1:
        recording = Path(sys.argv[1])
    else:
        recording = latest_recording()

    analyze(recording)
