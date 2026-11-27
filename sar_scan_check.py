
import sys
import numpy as np

from pathlib import Path

from sar_dataset import (
    load_dataset,
    latest_dataset
)


def check_scan(dataset):

    positions = dataset["positions"]
    profiles = dataset["profiles"]
    ranges = dataset["ranges"]

    count = len(positions)

    unique_count = len(
        np.unique(positions, axis=0)
    )

    amplitudes = np.abs(profiles)

    finite = (
        np.isfinite(positions).all()
        and np.isfinite(profiles).all()
        and np.isfinite(ranges).all()
    )

    nonzero = np.all(
        np.max(amplitudes, axis=1) > 0
    )

    print("\n================================")
    print("SAR SCAN READINESS")
    print("================================")

    print(f"Measurements: {count}")
    print(f"Unique positions: {unique_count}")
    print(f"Profile shape: {profiles.shape}")

    print(
        f"X span: "
        f"{np.ptp(positions[:, 0]):.6f} m"
    )

    print(
        f"Y span: "
        f"{np.ptp(positions[:, 1]):.6f} m"
    )

    print(
        f"Finite measurements: "
        f"{'PASS' if finite else 'FAIL'}"
    )

    print(
        f"Nonzero profiles: "
        f"{'PASS' if nonzero else 'FAIL'}"
    )

    print(
        f"Range axis: "
        f"{ranges[0]:.4f} to "
        f"{ranges[-1]:.4f} m"
    )

    print(
        f"Complex profiles: "
        f"{'PASS' if np.iscomplexobj(profiles) else 'FAIL'}"
    )

    if not finite or not nonzero:
        raise ValueError(
            "Invalid measurement data."
        )

    if not np.iscomplexobj(profiles):
        raise ValueError(
            "Complex phase information missing."
        )

    print("\nDATASET CONTENT: PASS")

    if unique_count < 2:

        print("Spatial diversity: NOT AVAILABLE")
        print("Stationary test dataset detected.")
        print("Reconstruction readiness: PENDING")

        return False

    print("Spatial diversity: PRESENT")

    print(
        "Physical position accuracy and phase "
        "convention require independent verification."
    )

    return True


if __name__ == "__main__":

    if len(sys.argv) > 1:
        directory = Path(sys.argv[1])
    else:
        directory = latest_dataset()

    dataset = load_dataset(directory)

    check_scan(dataset)
