
import csv
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from datetime import datetime

import sar_backprojection as bp

# ==========================================
# Experiment configuration
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent

RESULTS_DIR = PROJECT_DIR / "results" / "quality"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_X = 0.0
TARGET_Y = 1.2

APERTURE_LENGTHS = [
    0.05,
    0.10,
    0.20,
    0.30
]

MEASUREMENT_SPACING = 0.001

SPACING_TESTS = [
    0.001,
    0.002,
    0.005,
    0.010
]

# ==========================================
# Generate single point target measurements
# ==========================================

def generate_dataset(aperture, spacing):

    count = int(round(aperture / spacing)) + 1

    scan_x = np.linspace(
        -aperture / 2,
        aperture / 2,
        count
    )

    positions = np.column_stack([
        scan_x,
        np.zeros_like(scan_x)
    ])

    t = np.arange(bp.NUM_SAMPLES) / bp.FS

    window = np.hanning(bp.NUM_SAMPLES)

    profiles = []

    for radar_x, radar_y in positions:

        distance = np.hypot(
            TARGET_X - radar_x,
            TARGET_Y - radar_y
        )

        delay = 2 * distance / bp.C

        beat_frequency = bp.SLOPE * delay

        phase = 2 * np.pi * (
            (
                bp.FC +
                bp.SLOPE * bp.ADC_START_TIME
            ) * delay
            - 0.5 * bp.SLOPE * delay ** 2
        )

        signal = np.exp(
            1j * (
                2 * np.pi *
                beat_frequency * t
                + phase
            )
        )

        spectrum = np.fft.fft(
            signal * window,
            n=bp.NFFT
        )

        spectrum /= np.sum(window)

        profiles.append(
            spectrum[:bp.NFFT // 2]
        )

    frequencies = (
        np.arange(bp.NFFT // 2)
        * bp.FS / bp.NFFT
    )

    ranges = (
        bp.C * frequencies /
        (2 * bp.SLOPE)
    )

    return {
        "positions": positions,
        "ranges": ranges,
        "profiles": np.asarray(profiles),
        "targets": [
            (TARGET_X, TARGET_Y, 1.0)
        ]
    }


# ==========================================
# Convert normalized amplitude to dB
# ==========================================

def amplitude_db(values):

    amplitude = np.abs(values)

    peak = np.max(amplitude)

    if peak <= 0:
        raise ValueError("Empty response.")

    return 20 * np.log10(
        np.maximum(
            amplitude / peak,
            1e-8
        )
    )


# ==========================================
# Measure -3 dB resolution
# ==========================================

def measure_width(axis, response):

    power = np.abs(response) ** 2
    peak_index = np.argmax(power)

    threshold = power[peak_index] / 2

    left = peak_index
    right = peak_index

    while left > 0 and power[left] >= threshold:
        left -= 1

    while (
        right < len(power) - 1
        and power[right] >= threshold
    ):
        right += 1

    if (
        power[left] >= threshold
        or power[right] >= threshold
    ):
        return np.nan

    left_crossing = np.interp(
        threshold,
        [power[left], power[left + 1]],
        [axis[left], axis[left + 1]]
    )

    right_crossing = np.interp(
        threshold,
        [power[right], power[right - 1]],
        [axis[right], axis[right - 1]]
    )

    return right_crossing - left_crossing


# ==========================================
# Estimate peak sidelobe ratio
# ==========================================

def measure_pslr(response):

    amplitude = np.abs(response)

    peak_index = np.argmax(amplitude)
    peak = amplitude[peak_index]

    if peak <= 0:
        return np.nan

    left = peak_index
    right = peak_index

    # Locate first local minimum on each side
    while (
        left > 0
        and amplitude[left - 1] <= amplitude[left]
    ):
        left -= 1

    while (
        right < len(amplitude) - 1
        and amplitude[right + 1] <= amplitude[right]
    ):
        right += 1

    if left == 0 or right == len(amplitude) - 1:
        return np.nan

    sidelobes = np.concatenate([
        amplitude[:left],
        amplitude[right + 1:]
    ])

    if len(sidelobes) == 0:
        return np.nan

    return 20 * np.log10(
        max(np.max(sidelobes) / peak, 1e-8)
    )


# ==========================================
# Measure reconstructed point response
# ==========================================

def analyze_image(x, y, image):

    magnitude = np.abs(image)

    row, col = np.unravel_index(
        np.argmax(magnitude),
        magnitude.shape
    )

    peak_x = x[col]
    peak_y = y[row]

    cross_range_cut = image[row, :]
    range_cut = image[:, col]

    cross_range_resolution = measure_width(
        x, cross_range_cut
    )

    range_resolution = measure_width(
        y, range_cut
    )

    localization_error = np.hypot(
        peak_x - TARGET_X,
        peak_y - TARGET_Y
    )

    return {
        "peak_x": peak_x,
        "peak_y": peak_y,
        "localization_error_mm":
            localization_error * 1000,

        "cross_range_resolution_mm":
            cross_range_resolution * 1000,

        "range_resolution_mm":
            range_resolution * 1000,

        "cross_range_pslr_db":
            measure_pslr(cross_range_cut),

        "range_pslr_db":
            measure_pslr(range_cut),

        "cross_range_cut":
            cross_range_cut,

        "range_cut":
            range_cut
    }


# ==========================================
# Run one reconstruction experiment
# ==========================================

def run_test(aperture, spacing):

    dataset = generate_dataset(
        aperture, spacing
    )

    # Use fine local grid for PSF analysis
    settings = {
        "X_MIN": -0.15,
        "X_MAX": 0.15,
        "Y_MIN": 1.0,
        "Y_MAX": 1.4,
        "PIXEL_SIZE": 0.001
    }

    original = {
        key: getattr(bp, key)
        for key in settings
    }

    try:

        for key, value in settings.items():
            setattr(bp, key, value)

        x, y, image = bp.backproject(
            dataset,
            phase_sign=-1
        )

    finally:

        for key, value in original.items():
            setattr(bp, key, value)

    metrics = analyze_image(
        x, y, image
    )

    metrics["aperture_m"] = aperture
    metrics["spacing_m"] = spacing

    metrics["measurements"] = len(
        dataset["positions"]
    )

    print("\n========== QUALITY RESULTS ==========")

    print(f"Aperture: {aperture * 100:.1f} cm")
    print(f"Spacing: {spacing * 1000:.1f} mm")

    print(
        f"Measurements: "
        f"{metrics['measurements']}"
    )

    print(
        f"Range resolution (-3 dB): "
        f"{metrics['range_resolution_mm']:.3f} mm"
    )

    print(
        f"Cross-range resolution (-3 dB): "
        f"{metrics['cross_range_resolution_mm']:.3f} mm"
    )

    print(
        f"Cross-range PSLR: "
        f"{metrics['cross_range_pslr_db']:.3f} dB"
    )

    print(
        f"Range PSLR: "
        f"{metrics['range_pslr_db']:.3f} dB"
    )

    print(
        f"Localization error: "
        f"{metrics['localization_error_mm']:.3f} mm"
    )

    return x, y, image, metrics


# ==========================================
# Main quality characterization experiment
# ==========================================

def main():

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    results = []
    spacing_results = []

    print("SAR IMAGE QUALITY CHARACTERIZATION")
    print("Synthetic single point target")

    # ======================================
    # Experiment 1: Aperture length
    # ======================================

    plt.figure(figsize=(10, 6))

    for aperture in APERTURE_LENGTHS:

        x, y, image, metrics = run_test(
            aperture,
            MEASUREMENT_SPACING
        )

        results.append(metrics)

        plt.plot(
            x * 1000,
            amplitude_db(
                metrics["cross_range_cut"]
            ),
            label=f"{aperture * 100:.0f} cm"
        )

    plt.axhline(
        -3,
        color="gray",
        linestyle="--"
    )

    plt.title("Cross-Range PSF vs Aperture Length")
    plt.xlabel("Cross-range displacement (mm)")
    plt.ylabel("Relative amplitude (dB)")
    plt.xlim(-100, 100)
    plt.ylim(-60, 2)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"psf_{timestamp}.png",
        dpi=200
    )

    # ======================================
    # Experiment 2: Resolution comparison
    # ======================================

    apertures_cm = [
        item["aperture_m"] * 100
        for item in results
    ]

    cross_resolution = [
        item["cross_range_resolution_mm"]
        for item in results
    ]

    range_resolution = [
        item["range_resolution_mm"]
        for item in results
    ]

    plt.figure(figsize=(10, 6))

    plt.plot(
        apertures_cm,
        cross_resolution,
        marker="o",
        label="Cross-range"
    )

    plt.plot(
        apertures_cm,
        range_resolution,
        marker="s",
        label="Range"
    )

    plt.title("SAR Resolution vs Aperture Length")
    plt.xlabel("Aperture length (cm)")
    plt.ylabel("-3 dB resolution (mm)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"resolution_{timestamp}.png",
        dpi=200
    )

    # ======================================
    # Experiment 3: Measurement spacing
    # ======================================

    plt.figure(figsize=(10, 6))

    for spacing in SPACING_TESTS:

        if spacing == MEASUREMENT_SPACING:

            metrics = results[-1]

        else:

            x, y, image, metrics = run_test(
                0.30,
                spacing
            )

        spacing_results.append(metrics)

        plt.plot(
            x * 1000,
            amplitude_db(
                metrics["cross_range_cut"]
            ),
            label=f"{spacing * 1000:.0f} mm"
        )

    plt.title("Cross-Range PSF vs Measurement Spacing")
    plt.xlabel("Cross-range displacement (mm)")
    plt.ylabel("Relative amplitude (dB)")
    plt.ylim(-60, 2)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"spacing_{timestamp}.png",
        dpi=200
    )

    # ======================================
    # Experiment 4: Detailed point response
    # ======================================

    x, y, image, best = run_test(
        0.30,
        0.001
    )

    fig, ax = plt.subplots(figsize=(8, 8))

    im = ax.imshow(
        amplitude_db(image),
        origin="lower",
        extent=[
            x[0] - 0.0005,
            x[-1] + 0.0005,
            y[0] - 0.0005,
            y[-1] + 0.0005
        ],
        aspect="equal",
        cmap="jet",
        vmin=-40,
        vmax=0
    )

    ax.scatter(
        TARGET_X,
        TARGET_Y,
        marker="+",
        color="white",
        s=100
    )

    ax.set_title("SAR Single Target Point Spread Function")
    ax.set_xlabel("Cross-range (m)")
    ax.set_ylabel("Forward distance (m)")

    fig.colorbar(
        im,
        ax=ax,
        label="Relative amplitude (dB)"
    )

    fig.tight_layout()

    fig.savefig(
        RESULTS_DIR / f"point_target_{timestamp}.png",
        dpi=200
    )

    # ======================================
    # Save quality metrics
    # ======================================

    fields = [
        "experiment",
        "aperture_m",
        "spacing_m",
        "measurements",
        "range_resolution_mm",
        "cross_range_resolution_mm",
        "range_pslr_db",
        "cross_range_pslr_db",
        "localization_error_mm"
    ]

    csv_path = (
        RESULTS_DIR /
        f"quality_{timestamp}.csv"
    )

    with csv_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
            extrasaction="ignore"
        )

        writer.writeheader()

        for item in results:

            writer.writerow({
                **item,
                "experiment": "aperture"
            })

        for item in spacing_results:

            writer.writerow({
                **item,
                "experiment": "spacing"
            })

    print("\n================================")
    print("QUALITY CHARACTERIZATION COMPLETE")
    print("================================")

    print(f"Results saved to: {csv_path}")

    plt.show()


if __name__ == "__main__":

    main()
