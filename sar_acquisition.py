
import csv
import json
from pathlib import Path
from datetime import datetime

from radar_session import RadarSession
from radar_acquisition import acquire

# ==========================================
# Project directories
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent
SCAN_DIR = PROJECT_DIR / "sar_scans"

SCAN_DIR.mkdir(exist_ok=True)

# ==========================================
# Radar configuration
# ==========================================

RADAR_CONFIG = {
    "start_frequency_hz": 77e9,
    "frequency_slope_hz_s": 60.012e12,
    "sample_rate_hz": 10e6,
    "adc_samples": 512,
    "rx_channels": 4,
    "tx_channels": 1,
    "chirps_per_frame": 128,
    "frames": 8,
    "frame_periodicity_ms": 40,
    "packet_delay_us": 50
}


def create_experiment():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    directory = SCAN_DIR / f"scan_{timestamp}"
    directory.mkdir()

    config_path = directory / "configuration.json"

    config_path.write_text(
        json.dumps(RADAR_CONFIG, indent=4),
        encoding="utf-8"
    )

    return directory


def record_metadata(directory, index, recording, x, y):

    manifest = directory / "measurements.csv"

    new_file = not manifest.exists()

    with manifest.open(
        "a", newline="", encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        if new_file:

            writer.writerow([
                "measurement",
                "recording",
                "x_m",
                "y_m",
                "timestamp",
                "packet_validation"
            ])

        writer.writerow([
            index,
            str(recording.relative_to(PROJECT_DIR)),
            x,
            y,
            datetime.now().isoformat(),
            "PASS"
        ])


def run_experiment():

    directory = create_experiment()

    print("\nSAR DATASET ACQUISITION")
    print(f"Experiment: {directory.name}")

    radar = RadarSession()

    index = 1

    try:

        while True:

            command = input(
                "\nPress Enter to record "
                "or Q to finish: "
            ).strip().lower()

            if command == "q":
                break

            x = float(input(
                "Measured X position (meters): "
            ))

            y = float(input(
                "Measured Y position (meters): "
            ))

            print(f"\nMeasurement {index}")

            recording = acquire(radar)

            record_metadata(
                directory,
                index,
                recording,
                x,
                y
            )

            print("Measurement metadata saved.")

            index += 1

    finally:

        radar.close()

    print("\nEXPERIMENT FINISHED")
    print(f"Measurements saved: {index - 1}")
    print(f"Dataset directory: {directory}")


if __name__ == "__main__":

    run_experiment()
