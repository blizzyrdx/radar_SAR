
import csv
import json
import sys
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path

from radar_processing import (
    load_adc,
    range_fft,
    coherent_profile
)

# ==========================================
# Project directories
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent
SCAN_DIR = PROJECT_DIR / "sar_scans"

RX_CHANNEL = 0
NFFT = 2048

# ==========================================
# Expected radar configuration
# ==========================================

EXPECTED_CONFIG = {
    "start_frequency_hz": 77e9,
    "frequency_slope_hz_s": 60.012e12,
    "sample_rate_hz": 10e6,
    "adc_samples": 512,
    "rx_channels": 4,
    "tx_channels": 1,
    "chirps_per_frame": 128,
    "frames": 8
}


# ==========================================
# Locate latest dataset
# ==========================================

def latest_dataset():

    directories = [
        path for path in SCAN_DIR.glob("scan_*")
        if path.is_dir()
        and (path / "measurements.csv").is_file()
        and (path / "configuration.json").is_file()
    ]

    if not directories:
        raise FileNotFoundError(
            "No complete SAR datasets found."
        )

    return max(
        directories,
        key=lambda path: path.name
    )


# ==========================================
# Load configuration
# ==========================================

def load_configuration(directory):

    path = directory / "configuration.json"

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    for key, expected in EXPECTED_CONFIG.items():

        actual = config.get(key)

        if actual != expected:
            raise ValueError(
                f"Configuration mismatch: {key}. "
                f"Expected {expected}, got {actual}"
            )

    print("Radar configuration: PASS")

    return config


# ==========================================
# Load SAR measurements
# ==========================================

def load_dataset(directory, rx=RX_CHANNEL):

    directory = Path(directory)

    config = load_configuration(directory)

    manifest = directory / "measurements.csv"

    with manifest.open(
        "r", newline="", encoding="utf-8"
    ) as file:

        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("SAR dataset is empty.")

    positions = []
    profiles = []
    recordings = []

    range_axis = None
    seen_files = set()

    print("\n================================")
    print("LOADING SAR DATASET")
    print("================================")

    print(f"Dataset: {directory.name}")
    print(f"Measurements: {len(rows)}")
    print(f"Receiver: RX{rx}")

    for i, row in enumerate(rows):

        if row["packet_validation"] != "PASS":
            raise ValueError(
                f"Invalid measurement: {i + 1}"
            )

        x = float(row["x_m"])
        y = float(row["y_m"])

        if not np.isfinite([x, y]).all():
            raise ValueError(
                "Invalid radar coordinates."
            )

        recording = (
            PROJECT_DIR / row["recording"]
        ).resolve()

        if recording in seen_files:
            raise ValueError(
                f"Duplicate recording: {recording.name}"
            )

        seen_files.add(recording)

        if not recording.is_file():
            raise FileNotFoundError(recording)

        print(
            f"\nMeasurement {i + 1}/{len(rows)}"
        )

        print(f"Position: ({x:.4f}, {y:.4f}) m")
        print(f"Recording: {recording.name}")

        # Decode and validate ADC data
        cube = load_adc(recording)

        # Complex range FFT
        ranges, spectrum = range_fft(
            cube,
            nfft=NFFT
        )

        # Preserve complex amplitude and phase
        profile = coherent_profile(
            spectrum,
            rx=rx
        )

        if not np.isfinite(profile).all():
            raise ValueError(
                "Invalid complex range profile."
            )

        if range_axis is None:
            range_axis = ranges

        elif not np.array_equal(
            ranges, range_axis
        ):
            raise ValueError(
                "Inconsistent range axes."
            )

        positions.append([x, y])
        profiles.append(profile)
        recordings.append(recording.name)

        # Release large intermediate arrays
        del cube
        del spectrum

    positions = np.asarray(
        positions,
        dtype=np.float64
    )

    profiles = np.asarray(profiles)

    return {
        "positions": positions,
        "ranges": range_axis,
        "profiles": profiles,
        "recordings": recordings,
        "configuration": config
    }


# ==========================================
# Dataset summary
# ==========================================

def summarize_dataset(dataset):

    positions = dataset["positions"]
    profiles = dataset["profiles"]
    ranges = dataset["ranges"]

    print("\n================================")
    print("SAR DATASET SUMMARY")
    print("================================")

    print(f"Measurements: {len(positions)}")
    print(f"Position array: {positions.shape}")
    print(f"Range profile array: {profiles.shape}")
    print(f"Range bins: {len(ranges)}")
    print(f"Complex data type: {profiles.dtype}")

    print(
        f"X position span: "
        f"{np.ptp(positions[:, 0]):.4f} m"
    )

    print(
        f"Y position span: "
        f"{np.ptp(positions[:, 1]):.4f} m"
    )

    print(
        f"Range bin spacing: "
        f"{ranges[1] - ranges[0]:.6f} m"
    )

    if np.unique(positions, axis=0).shape[0] < 2:

        print("\nStationary dataset detected.")
        print("Software validation is possible.")
        print("Spatial SAR reconstruction is not yet possible.")

    print("\nDATASET VALIDATION: PASS")


# ==========================================
# Visualize dataset
# ==========================================

def visualize_dataset(dataset):

    positions = dataset["positions"]
    ranges = dataset["ranges"]
    profiles = dataset["profiles"]

    # Figure 1: Recorded radar positions

    plt.figure(figsize=(9, 5))

    plt.scatter(
        positions[:, 0],
        positions[:, 1],
        s=60
    )

    plt.title("Recorded SAR Measurement Positions")
    plt.xlabel("X Position (m)")
    plt.ylabel("Y Position (m)")
    plt.axis("equal")
    plt.grid(True)
    plt.tight_layout()

    # Figure 2: Average range power

    power = np.mean(
        np.abs(profiles) ** 2,
        axis=0
    )

    reference = np.max(power)

    power_db = 10 * np.log10(
        np.maximum(
            power / max(reference, 1e-12),
            1e-12
        )
    )

    plt.figure(figsize=(10, 5))

    plt.plot(ranges, power_db)

    plt.title("SAR Dataset Average Range Profile")
    plt.xlabel("Range (m)")
    plt.ylabel("Relative Power (dB)")
    plt.xlim(0, 5)
    plt.grid(True)
    plt.tight_layout()

    # Figure 3: Measurement-range intensity

    amplitude = np.abs(profiles)

    amplitude_db = 20 * np.log10(
        np.maximum(
            amplitude / max(
                np.max(amplitude), 1e-12
            ),
            1e-6
        )
    )

    plt.figure(figsize=(10, 5))

    plt.imshow(
        amplitude_db.T,
        aspect="auto",
        origin="lower",
        extent=[
            0.5,
            len(positions) + 0.5,
            ranges[0],
            ranges[-1]
        ],
        cmap="jet",
        vmin=-50,
        vmax=0
    )

    plt.title("SAR Measurement Range Intensity")
    plt.xlabel("Measurement Number")
    plt.ylabel("Range (m)")
    plt.ylim(0, 5)

    plt.colorbar(
        label="Relative Amplitude (dB)"
    )

    plt.tight_layout()
    plt.show()


# ==========================================
# Main program
# ==========================================

if __name__ == "__main__":

    if len(sys.argv) > 1:
        directory = Path(sys.argv[1])
    else:
        directory = latest_dataset()

    dataset = load_dataset(directory)

    summarize_dataset(dataset)

    visualize_dataset(dataset)
