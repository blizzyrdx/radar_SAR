
import time
import csv
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime
from pathlib import Path

from radar_session import RadarSession
from radar_acquisition import acquire

from radar_processing import (
    load_adc,
    range_fft,
    coherent_profile,
    WAVELENGTH
)

# ==========================================
# Experiment configuration
# ==========================================

NUM_CAPTURES = 10
RX_CHANNEL = 0

TARGET_RANGE_MIN = 1.0
TARGET_RANGE_MAX = 1.4

CAPTURE_DELAY = 3

PROJECT_DIR = Path(__file__).resolve().parent

RESULTS_DIR = PROJECT_DIR / "results" / "coherence"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# Main coherence experiment
# ==========================================

def run_coherence_test():

    measurements = []
    recordings = []

    reference_index = None
    reference_range = None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    print("\n================================")
    print("RADAR PHASE COHERENCE TEST")
    print("================================")

    print(f"Number of captures: {NUM_CAPTURES}")
    print(f"Receiver channel: RX{RX_CHANNEL}")
    print("Keep radar and target stationary.")

    radar = RadarSession()

    try:

        for i in range(NUM_CAPTURES):

            print("\n================================")
            print(f"CAPTURE {i + 1}/{NUM_CAPTURES}")
            print("================================")

            input(
                "Close PostProc if open, "
                "then press Enter to capture..."
            )

            # Acquire packet-validated radar data
            recording = acquire(radar)

            # Decode complex ADC samples
            cube = load_adc(recording)

            # Perform complex range FFT
            ranges, spectrum = range_fft(cube)

            # Extract coherent RX profile
            profile = coherent_profile(
                spectrum,
                rx=RX_CHANNEL
            )

            # Select reference bin using first capture
            if reference_index is None:

                mask = (
                    (ranges >= TARGET_RANGE_MIN)
                    & (ranges <= TARGET_RANGE_MAX)
                )

                indices = np.flatnonzero(mask)

                reference_index = indices[
                    np.argmax(
                        np.abs(profile[indices])
                    )
                ]

                reference_range = ranges[
                    reference_index
                ]

                print(
                    f"Reference bin: {reference_index}"
                )

                print(
                    f"Reference range: "
                    f"{reference_range:.4f} m"
                )

            # Always use the same reference range bin
            value = profile[reference_index]

            if not np.isfinite(value) or abs(value) == 0:
                raise ValueError(
                    "Invalid complex measurement"
                )

            measurements.append(value)
            recordings.append(recording.name)

            print(
                f"Amplitude: {abs(value):.4f}"
            )

            print(
                f"Phase: "
                f"{np.angle(value, deg=True):.4f} degrees"
            )

            if i < NUM_CAPTURES - 1:
                time.sleep(CAPTURE_DELAY)

    finally:

        radar.close()

    # ======================================
    # Convert collected measurements
    # ======================================

    measurements = np.asarray(measurements)

    amplitudes = np.abs(measurements)

    relative_phase = np.angle(
        measurements *
        np.conj(measurements[0]),
        deg=True
    )

    unwrapped_phase = np.rad2deg(
        np.unwrap(
            np.angle(measurements)
        )
    )

    unwrapped_phase -= unwrapped_phase[0]

    # ======================================
    # Phase and amplitude statistics
    # ======================================

    phase_std = np.std(unwrapped_phase)

    phase_variation = np.ptp(unwrapped_phase)

    amplitude_mean = np.mean(amplitudes)

    amplitude_std = np.std(amplitudes)

    amplitude_cv = (
        100 * amplitude_std / amplitude_mean
    )

    # Coherent amplitude efficiency
    coherence = (
        np.abs(np.sum(measurements))
        / np.sum(amplitudes)
    )

    # Equivalent radial displacement magnitude
    # Only valid if phase changes are caused
    # entirely by physical radial motion.

    displacement_mm = (
        WAVELENGTH
        * np.deg2rad(unwrapped_phase)
        / (4 * np.pi)
        * 1000
    )

    # ======================================
    # Print experiment results
    # ======================================

    print("\n================================")
    print("COHERENCE TEST RESULTS")
    print("================================")

    print(f"Valid captures: {len(measurements)}")

    print(
        f"Reference range: "
        f"{reference_range:.4f} m"
    )

    print(
        f"Mean amplitude: "
        f"{amplitude_mean:.4f}"
    )

    print(
        f"Amplitude variation (CV): "
        f"{amplitude_cv:.4f}%"
    )

    print(
        f"Phase standard deviation: "
        f"{phase_std:.4f} degrees"
    )

    print(
        f"Peak-to-peak phase variation: "
        f"{phase_variation:.4f} degrees"
    )

    print(
        f"Coherent amplitude efficiency: "
        f"{coherence * 100:.4f}%"
    )

    print(
        f"Equivalent displacement variation: "
        f"{np.ptp(displacement_mm):.4f} mm"
    )

    # ======================================
    # Save experimental data
    # ======================================

    csv_path = RESULTS_DIR / (
        f"coherence_{timestamp}.csv"
    )

    with open(csv_path, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "capture",
            "recording",
            "range_m",
            "real",
            "imaginary",
            "amplitude",
            "relative_phase_deg",
            "unwrapped_phase_deg",
            "equivalent_displacement_mm"
        ])

        for i, value in enumerate(measurements):

            writer.writerow([
                i + 1,
                recordings[i],
                reference_range,
                value.real,
                value.imag,
                amplitudes[i],
                relative_phase[i],
                unwrapped_phase[i],
                displacement_mm[i]
            ])

    print(f"\nResults saved to: {csv_path}")

    capture_numbers = np.arange(
        1, len(measurements) + 1
    )

    # ======================================
    # Figure 1: Phase stability
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.plot(
        capture_numbers,
        unwrapped_phase,
        marker="o"
    )

    plt.axhline(
        0,
        color="gray",
        linestyle="--"
    )

    plt.title("Inter-Capture Phase Stability")
    plt.xlabel("Capture Number")
    plt.ylabel("Relative Phase (degrees)")
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"phase_{timestamp}.png",
        dpi=200
    )

    # ======================================
    # Figure 2: Amplitude stability
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.plot(
        capture_numbers,
        amplitudes,
        marker="o"
    )

    plt.title("Inter-Capture Amplitude Stability")
    plt.xlabel("Capture Number")
    plt.ylabel("Coherent Amplitude")
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"amplitude_{timestamp}.png",
        dpi=200
    )

    # ======================================
    # Figure 3: Complex measurement plane
    # ======================================

    plt.figure(figsize=(7, 7))

    plt.scatter(
        measurements.real,
        measurements.imag,
        s=60
    )

    for i, value in enumerate(measurements):

        plt.annotate(
            str(i + 1),
            (value.real, value.imag),
            xytext=(5, 5),
            textcoords="offset points"
        )

    plt.axhline(0, color="gray")
    plt.axvline(0, color="gray")

    plt.title("Complex Measurement Stability")
    plt.xlabel("Real Component (I)")
    plt.ylabel("Imaginary Component (Q)")
    plt.axis("equal")
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"complex_{timestamp}.png",
        dpi=200
    )

    # ======================================
    # Figure 4: Equivalent displacement
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.plot(
        capture_numbers,
        displacement_mm,
        marker="o"
    )

    plt.title("Phase-Equivalent Radial Displacement")
    plt.xlabel("Capture Number")
    plt.ylabel("Equivalent Displacement (mm)")
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"displacement_{timestamp}.png",
        dpi=200
    )

    plt.show()


if __name__ == "__main__":

    run_coherence_test()
