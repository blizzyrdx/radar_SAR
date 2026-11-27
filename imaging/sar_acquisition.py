
import csv
import json
from pathlib import Path
from datetime import datetime

from radar.radar_config import CONFIG
from radar.radar_session import RadarSession
from radar.radar_acquisition import acquire

# ==========================================
# Project directories
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCAN_DIR = PROJECT_DIR / "sar_scans"

SCAN_DIR.mkdir(exist_ok=True)

# ==========================================
# Radar configuration
# ==========================================

RADAR_CONFIG = {
    "start_frequency_hz": CONFIG.start_frequency_hz,
    "frequency_slope_hz_s": CONFIG.slope_hz_s,
    "sample_rate_hz": CONFIG.sample_rate_hz,
    "adc_start_time_s": CONFIG.adc_start_time_s,
    "adc_samples": CONFIG.num_samples,
    "rx_channels": CONFIG.num_rx,
    "tx_channels": CONFIG.num_tx,
    "chirps_per_frame": CONFIG.num_chirps,
    "frames": CONFIG.num_frames,
    "frame_periodicity_ms": CONFIG.frame_periodicity_ms,
    "packet_delay_us": CONFIG.packet_delay_us,
    "adc_bits": CONFIG.adc_bits,
    "nfft": CONFIG.nfft
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
