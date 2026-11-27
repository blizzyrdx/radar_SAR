
import sys
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path

from radar_processing import (
    C,
    FC,
    FS,
    SLOPE,
    NUM_SAMPLES
)

from sar_dataset import (
    load_dataset,
    latest_dataset
)

# ==========================================
# Imaging configuration
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent

RESULTS_DIR = PROJECT_DIR / "results" / "sar"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

NFFT = 2048

ADC_START_TIME = 6e-6

# Effective frequency at center of ADC sampling
F_CENTER = FC + SLOPE * (
    ADC_START_TIME +
    (NUM_SAMPLES - 1) / (2 * FS)
)

WAVELENGTH = C / F_CENTER

X_MIN = -0.5
X_MAX = 0.5

Y_MIN = 0.5
Y_MAX = 1.8

PIXEL_SIZE = 0.005

# ==========================================
# Generate imaging grid
# ==========================================

def create_grid():

    x = np.arange(
        X_MIN,
        X_MAX + PIXEL_SIZE / 2,
        PIXEL_SIZE
    )

    y = np.arange(
        Y_MIN,
        Y_MAX + PIXEL_SIZE / 2,
        PIXEL_SIZE
    )

    X, Y = np.meshgrid(x, y)

    return x, y, X, Y


# ==========================================
# Complex interpolation
# ==========================================

def interpolate_complex(ranges, profile, distance):

    real = np.interp(
        distance,
        ranges,
        profile.real,
        left=0,
        right=0
    )

    imag = np.interp(
        distance,
        ranges,
        profile.imag,
        left=0,
        right=0
    )

    return real + 1j * imag


# ==========================================
# Reference range FFT phase correction
# ==========================================

def center_range_profiles(ranges, profiles):

    beat_frequency = (
        2 * SLOPE * ranges / C
    )

    center_time = (
        (NUM_SAMPLES - 1) / (2 * FS)
    )

    correction = np.exp(
        1j * 2 * np.pi *
        beat_frequency * center_time
    )

    return profiles * correction


# ==========================================
# SAR backprojection
# ==========================================

def backproject(dataset, phase_sign=-1):

    positions = dataset["positions"]
    ranges = dataset["ranges"]

    profiles = center_range_profiles(
        ranges,
        dataset["profiles"]
    )

    unique_positions = np.unique(
        positions,
        axis=0
    )

    if len(unique_positions) < 2:

        raise ValueError(
            "Spatial reconstruction requires "
            "multiple distinct radar positions."
        )

    x, y, X, Y = create_grid()

    image = np.zeros(
        X.shape,
        dtype=np.complex128
    )

    print("\nPerforming SAR backprojection...")
    print(f"Measurements: {len(positions)}")
    print(f"Image grid: {X.shape}")

    for i, position in enumerate(positions):

        radar_x, radar_y = position

        # Distance to each image pixel
        distance = np.sqrt(
            (X - radar_x) ** 2 +
            (Y - radar_y) ** 2
        )

        # Interpolate complex range measurements
        values = interpolate_complex(
            ranges,
            profiles[i],
            distance
        )

        # Compensate carrier phase
        phase_correction = np.exp(
            phase_sign * 1j *
            4 * np.pi *
            distance / WAVELENGTH
        )

        # Coherent accumulation
        image += values * phase_correction

        if (i + 1) % 50 == 0:

            print(
                f"Processed "
                f"{i + 1}/{len(positions)}"
            )

    image /= len(positions)

    print("Backprojection completed.")

    return x, y, image


# ==========================================
# Synthetic validation dataset
# ==========================================

def synthetic_dataset():

    # Software-only test geometry
    scan_x = np.linspace(
        -0.15,
        0.15,
        301
    )

    positions = np.column_stack([
        scan_x,
        np.zeros_like(scan_x)
    ])

    targets = [
        (-0.15, 1.2, 1.0),
        (0.15, 1.2, 0.8)
    ]

    t = np.arange(NUM_SAMPLES) / FS

    window = np.hanning(NUM_SAMPLES)

    profiles = []

    for radar_x, radar_y in positions:

        signal = np.zeros(
            NUM_SAMPLES,
            dtype=np.complex128
        )

        for tx, ty, amplitude in targets:

            distance = np.sqrt(
                (tx - radar_x) ** 2 +
                (ty - radar_y) ** 2
            )

            delay = 2 * distance / C

            beat_frequency = SLOPE * delay

            phase = (
                2 * np.pi *
                (
                    (FC + SLOPE * ADC_START_TIME)
                    * delay
                    - 0.5 * SLOPE * delay ** 2
                )
            )

            signal += amplitude * np.exp(
                1j * (
                    2 * np.pi *
                    beat_frequency * t
                    + phase
                )
            )

        spectrum = np.fft.fft(
            signal * window,
            n=NFFT
        )

        spectrum /= np.sum(window)

        profiles.append(
            spectrum[:NFFT // 2]
        )

    frequencies = (
        np.arange(NFFT // 2)
        * FS / NFFT
    )

    ranges = (
        C * frequencies / (2 * SLOPE)
    )

    return {
        "positions": positions,
        "ranges": ranges,
        "profiles": np.asarray(profiles),
        "targets": targets
    }


# ==========================================
# Image normalization
# ==========================================

def image_db(image):

    amplitude = np.abs(image)

    maximum = np.max(amplitude)

    if maximum <= 0:
        raise ValueError("Empty SAR image.")

    return 20 * np.log10(
        np.maximum(
            amplitude / maximum,
            1e-6
        )
    )


# ==========================================
# Visualization
# ==========================================

def visualize(dataset, x, y, image, label):

    positions = dataset["positions"]
    ranges = dataset["ranges"]
    profiles = dataset["profiles"]

    db = image_db(image)

    # Figure 1: Measurement geometry

    plt.figure(figsize=(8, 7))

    plt.scatter(
        positions[:, 0],
        positions[:, 1],
        s=5,
        label="Radar positions"
    )

    for tx, ty, amplitude in dataset.get(
        "targets", []
    ):

        plt.scatter(
            tx,
            ty,
            marker="x",
            color="red",
            s=100
        )

    plt.xlabel("Cross-range (m)")
    plt.ylabel("Forward distance (m)")
    plt.title("SAR Measurement Geometry")
    plt.xlim(X_MIN, X_MAX)
    plt.ylim(-0.1, Y_MAX)
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    # Figure 2: Range measurements

    amplitude = np.abs(profiles)

    range_db = 20 * np.log10(
        np.maximum(
            amplitude /
            max(np.max(amplitude), 1e-12),
            1e-6
        )
    )

    plt.figure(figsize=(10, 6))

    plt.imshow(
        range_db.T,
        origin="lower",
        aspect="auto",
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

    plt.ylim(Y_MIN, Y_MAX)
    plt.xlabel("Measurement number")
    plt.ylabel("Range (m)")
    plt.title("SAR Range Measurements")
    plt.colorbar(label="Relative amplitude (dB)")
    plt.tight_layout()

    # Figure 3: Reconstructed image

    plt.figure(figsize=(8, 8))

    plt.imshow(
        db,
        extent=[
            x[0] - PIXEL_SIZE / 2,
            x[-1] + PIXEL_SIZE / 2,
            y[0] - PIXEL_SIZE / 2,
            y[-1] + PIXEL_SIZE / 2
        ],
        origin="lower",
        aspect="equal",
        cmap="jet",
        vmin=-40,
        vmax=0
    )

    for tx, ty, amplitude in dataset.get(
        "targets", []
    ):

        plt.scatter(
            tx,
            ty,
            marker="+",
            color="white",
            s=100
        )

    plt.title(f"SAR Reconstruction - {label}")
    plt.xlabel("Cross-range (m)")
    plt.ylabel("Forward distance (m)")
    plt.colorbar(label="Relative amplitude (dB)")
    plt.tight_layout()

    plt.savefig(
        RESULTS_DIR / f"{label}_image.png",
        dpi=200
    )

    np.savez_compressed(
        RESULTS_DIR / f"{label}_image.npz",
        x=x,
        y=y,
        image=image
    )

    plt.show()


# ==========================================
# Validate synthetic targets
# ==========================================

def validate_synthetic(dataset, x, y, image):

    X, Y = np.meshgrid(x, y)

    print("\n========== SYNTHETIC VALIDATION ==========")

    passed = True

    for i, (tx, ty, amplitude) in enumerate(
        dataset["targets"]
    ):

        region = (
            (np.abs(X - tx) < 0.05)
            & (np.abs(Y - ty) < 0.10)
        )

        local = np.where(
            region,
            np.abs(image),
            0
        )

        row, col = np.unravel_index(
            np.argmax(local),
            local.shape
        )

        estimated_x = x[col]
        estimated_y = y[row]

        error = np.hypot(
            estimated_x - tx,
            estimated_y - ty
        )

        print(f"\nTarget {i + 1}")
        print(f"True: ({tx:.3f}, {ty:.3f}) m")

        print(
            f"Estimated: "
            f"({estimated_x:.3f}, "
            f"{estimated_y:.3f}) m"
        )

        print(
            f"Position error: "
            f"{error * 1000:.2f} mm"
        )

        if error > 0.015:
            passed = False

    print(
        "\nSynthetic localization test:",
        "PASS" if passed else "FAIL"
    )


# ==========================================
# Main program
# ==========================================

if __name__ == "__main__":

    print("SAR BACKPROJECTION ENGINE")

    if "--synthetic" in sys.argv:

        dataset = synthetic_dataset()

        x, y, image = backproject(
            dataset,
            phase_sign=-1
        )

        validate_synthetic(
            dataset, x, y, image
        )

        visualize(
            dataset,
            x,
            y,
            image,
            "synthetic"
        )

    else:

        print(
            "Use --synthetic for the initial "
            "software validation."
        )

        print(
            "Measured-data reconstruction "
            "requires a spatial scan and "
            "phase-convention verification."
        )
