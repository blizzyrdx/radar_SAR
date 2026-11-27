
import argparse
import json
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from datetime import datetime

from radar_config import CONFIG

from sar_dataset import (
    load_dataset,
    latest_dataset
)

from sar_scan_check import check_scan

import sar_backprojection as bp

# ==========================================
# Project directories
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent

RESULTS_DIR = PROJECT_DIR / "results" / "reconstruction"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# Reconstruction arguments
# ==========================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description="SAR reconstruction interface"
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to SAR dataset directory"
    )

    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run synthetic reconstruction"
    )

    parser.add_argument(
        "--rx",
        type=int,
        choices=range(CONFIG.num_rx),
        default=0,
        help="Receiver channel"
    )

    parser.add_argument(
        "--phase-sign",
        type=int,
        choices=[-1, 1],
        default=-1
    )

    parser.add_argument(
        "--compare-signs",
        action="store_true",
        help="Compare both phase compensation signs"
    )

    parser.add_argument(
        "--xmin", type=float, default=-0.5
    )

    parser.add_argument(
        "--xmax", type=float, default=0.5
    )

    parser.add_argument(
        "--ymin", type=float, default=0.5
    )

    parser.add_argument(
        "--ymax", type=float, default=1.8
    )

    parser.add_argument(
        "--pixel-size",
        type=float,
        default=0.002
    )

    parser.add_argument(
        "--dynamic-range",
        type=float,
        default=40
    )

    parser.add_argument(
        "--no-show",
        action="store_true"
    )

    return parser.parse_args()


# ==========================================
# Validate reconstruction settings
# ==========================================

def validate_settings(args):

    values = [
        args.xmin,
        args.xmax,
        args.ymin,
        args.ymax,
        args.pixel_size,
        args.dynamic_range
    ]

    if not np.isfinite(values).all():
        raise ValueError("Nonfinite imaging settings.")

    if args.xmax <= args.xmin:
        raise ValueError("Invalid X limits.")

    if args.ymax <= args.ymin:
        raise ValueError("Invalid Y limits.")

    if args.pixel_size <= 0:
        raise ValueError("Invalid pixel size.")

    if args.dynamic_range <= 0:
        raise ValueError("Invalid dynamic range.")

    nx = int(
        np.ceil(
            (args.xmax - args.xmin)
            / args.pixel_size
        )
    ) + 1

    ny = int(
        np.ceil(
            (args.ymax - args.ymin)
            / args.pixel_size
        )
    ) + 1

    if nx * ny > 2_000_000:
        raise ValueError(
            "Image grid too large. "
            "Increase pixel size or reduce image area."
        )


# ==========================================
# Configure reconstruction engine
# ==========================================

def configure_engine(args):

    bp.X_MIN = args.xmin
    bp.X_MAX = args.xmax

    bp.Y_MIN = args.ymin
    bp.Y_MAX = args.ymax

    bp.PIXEL_SIZE = args.pixel_size


# ==========================================
# Create reconstruction output directory
# ==========================================

def create_output_directory(label):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    directory = RESULTS_DIR / (
        f"{label}_{timestamp}"
    )

    directory.mkdir()

    return directory


# ==========================================
# Normalize complex SAR image
# ==========================================

def normalize_image(image):

    amplitude = np.abs(image)

    if not np.isfinite(amplitude).all():
        raise ValueError("Invalid reconstructed image.")

    peak = np.max(amplitude)

    if peak <= 0:
        raise ValueError("Empty reconstructed image.")

    return 20 * np.log10(
        np.maximum(
            amplitude / peak,
            1e-8
        )
    )


# ==========================================
# Calculate preliminary image metrics
# ==========================================

def image_metrics(x, y, image):

    amplitude = np.abs(image)
    power = amplitude ** 2

    row, col = np.unravel_index(
        np.argmax(amplitude),
        amplitude.shape
    )

    total_power = np.sum(power)

    distribution = (
        power.ravel() / total_power
    )

    distribution = distribution[
        distribution > 0
    ]

    entropy = -np.sum(
        distribution * np.log2(distribution)
    )

    mean_power = np.mean(power)

    return {
        "peak_x_m": float(x[col]),
        "peak_y_m": float(y[row]),

        "peak_amplitude":
            float(amplitude[row, col]),

        "peak_to_mean_power_db":
            float(
                10 * np.log10(
                    np.max(power) / mean_power
                )
            ),

        "image_entropy":
            float(entropy),

        "image_rows": int(image.shape[0]),
        "image_columns": int(image.shape[1])
    }


# ==========================================
# Print image metrics
# ==========================================

def print_metrics(metrics):

    print("\n========== IMAGE METRICS ==========")

    print(
        f"Strongest X position: "
        f"{metrics['peak_x_m']:.4f} m"
    )

    print(
        f"Strongest Y position: "
        f"{metrics['peak_y_m']:.4f} m"
    )

    print(
        f"Peak amplitude: "
        f"{metrics['peak_amplitude']:.6f}"
    )

    print(
        f"Peak-to-mean power: "
        f"{metrics['peak_to_mean_power_db']:.4f} dB"
    )

    print(
        f"Image entropy: "
        f"{metrics['image_entropy']:.4f} bits"
    )


# ==========================================
# Export reconstruction results
# ==========================================

def save_reconstruction(
    directory,
    dataset,
    x,
    y,
    image,
    phase_sign,
    args
):

    db = normalize_image(image)

    metrics = image_metrics(
        x, y, image
    )

    label = (
        "negative_phase"
        if phase_sign == -1
        else "positive_phase"
    )

    # Save complex image and coordinate axes

    np.savez_compressed(
        directory / f"{label}.npz",

        x=x,
        y=y,

        image=image,
        amplitude_db=db,

        radar_positions=dataset["positions"],
        ranges=dataset["ranges"],

        phase_sign=phase_sign
    )

    # Save reconstruction metadata

    metadata = {
        "timestamp":
            datetime.now().isoformat(),

        "mode":
            "synthetic"
            if args.synthetic
            else "measured",

        "dataset":
            str(args.dataset)
            if args.dataset is not None
            else None,

        "receiver_channel": args.rx,

        "measurements":
            len(dataset["positions"]),

        "recordings":
            dataset.get("recordings", []),

        "phase_sign": phase_sign,

        "physical_phase_verified": False,

        "pixel_size_m": args.pixel_size,

        "dynamic_range_db":
            args.dynamic_range,

        "imaging_bounds": {
            "xmin": args.xmin,
            "xmax": args.xmax,
            "ymin": args.ymin,
            "ymax": args.ymax
        },

        "configuration":
            dataset.get(
                "configuration",
                CONFIG.to_dict()
            ),

        "processing_configuration":
            CONFIG.to_dict(),

        "metrics": metrics
    }

    with (
        directory / f"{label}.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            metadata,
            file,
            indent=4
        )

    # Generate reconstructed SAR image

    fig, ax = plt.subplots(
        figsize=(9, 8)
    )

    half_pixel = args.pixel_size / 2

    im = ax.imshow(
        db,

        origin="lower",

        extent=[
            x[0] - half_pixel,
            x[-1] + half_pixel,
            y[0] - half_pixel,
            y[-1] + half_pixel
        ],

        aspect="equal",

        cmap="jet",

        vmin=-args.dynamic_range,
        vmax=0
    )

    # Mark known simulated targets

    for tx, ty, amplitude in dataset.get(
        "targets", []
    ):

        ax.scatter(
            tx,
            ty,
            marker="+",
            color="white",
            s=100
        )

    ax.set_title(
        f"SAR Reconstruction "
        f"(Phase Sign: {phase_sign:+d})"
    )

    ax.set_xlabel("Cross-range (m)")
    ax.set_ylabel("Forward distance (m)")

    fig.colorbar(
        im,
        ax=ax,
        label="Relative amplitude (dB)"
    )

    fig.tight_layout()

    fig.savefig(
        directory / f"{label}.png",
        dpi=200
    )

    if args.no_show:
        plt.close(fig)

    print_metrics(metrics)

    return metrics


# ==========================================
# Main reconstruction workflow
# ==========================================

def main():

    args = parse_arguments()

    validate_settings(args)

    print("\n================================")
    print("SAR RECONSTRUCTION INTERFACE")
    print("================================")

    # Load synthetic or measured dataset

    if args.synthetic:

        print("Mode: SYNTHETIC")

        dataset = bp.synthetic_dataset()

        label = "synthetic"

    else:

        print("Mode: MEASURED")

        if args.dataset is None:
            args.dataset = latest_dataset()

        args.dataset = args.dataset.resolve()

        dataset = load_dataset(
            args.dataset,
            rx=args.rx
        )

        label = args.dataset.name

    # Check dataset readiness

    ready = check_scan(dataset)

    if not ready:

        print("\nRECONSTRUCTION NOT STARTED")

        print(
            "Collect measurements from "
            "multiple distinct radar positions."
        )

        return 2

    configure_engine(args)

    directory = create_output_directory(
        label
    )

    print(
        f"\nOutput directory: {directory}"
    )

    # Select phase compensation convention

    if args.compare_signs:
        signs = [-1, 1]
    else:
        signs = [args.phase_sign]

    comparison = {}

    for sign in signs:

        print("\n================================")

        print(
            f"RECONSTRUCTING: PHASE SIGN {sign:+d}"
        )

        print("================================")

        x, y, image = bp.backproject(
            dataset,
            phase_sign=sign
        )

        metrics = save_reconstruction(
            directory,
            dataset,
            x,
            y,
            image,
            sign,
            args
        )

        comparison[str(sign)] = metrics

        # Validate known synthetic positions

        if args.synthetic and sign == -1:

            bp.validate_synthetic(
                dataset,
                x,
                y,
                image
            )

    # Save comparison results

    with (
        directory / "comparison.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            comparison,
            file,
            indent=4
        )

    print("\n================================")
    print("RECONSTRUCTION COMPLETE")
    print("================================")

    print(f"Results saved to: {directory}")

    if args.compare_signs:

        print(
            "Compare both images using known "
            "target positions."
        )

        print(
            "Image metrics alone do not establish "
            "the correct physical phase convention."
        )

    if not args.synthetic:

        print(
            "Measured reconstruction remains "
            "experimental until physically calibrated."
        )

    if not args.no_show:
        plt.show()

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
