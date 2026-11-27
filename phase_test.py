
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Radar parameters
NUM_RX = 4
NUM_SAMPLES = 512
NUM_CHIRPS = 128
NUM_FRAMES = 8

C = 299792458
FS = 10e6
SLOPE = 60.012e12

DATA_DIR = Path(__file__).parent / "phase_test"

MIN_RANGE = 0.8
MAX_RANGE = 2.5


def load_radar(filename):
    raw = np.fromfile(DATA_DIR / filename, dtype="<i2")

    expected = (
        NUM_FRAMES * NUM_CHIRPS *
        NUM_RX * NUM_SAMPLES * 2
    )

    if raw.size != expected:
        raise ValueError(f"Incorrect file size: {filename}")

    groups = raw.reshape(-1, 4).astype(np.float32)

    iq = (
        groups[:, :2] + 1j * groups[:, 2:]
    ).flatten()

    return iq.reshape(
        NUM_FRAMES,
        NUM_CHIRPS,
        NUM_RX,
        NUM_SAMPLES
    )


range_axis = (
    np.arange(NUM_SAMPLES) * C * FS
    / (2 * SLOPE * NUM_SAMPLES)
)

window = np.hanning(NUM_SAMPLES)

phases = []
amplitudes = []
target_bin = None

for i in range(1, 6):

    filename = f"phase_test_{i:02d}.bin"
    cube = load_radar(filename)

    # First frame, first receiver
    signal = cube[0, :, 0, :]

    # Range FFT
    spectrum = np.fft.fft(
        signal * window,
        axis=-1
    )

    # Coherent averaging
    average = np.mean(spectrum, axis=0)

    # Find strongest target in the search region
    if target_bin is None:
        valid = np.where(
            (range_axis >= MIN_RANGE) &
            (range_axis <= MAX_RANGE)
        )[0]

        target_bin = valid[
            np.argmax(np.abs(average[valid]))
        ]

    target = average[target_bin]

    phases.append(np.angle(target))
    amplitudes.append(np.abs(target))

    print(
        f"{filename}: "
        f"Phase = {np.degrees(np.angle(target)):.2f} deg, "
        f"Amplitude = {np.abs(target):.2f}"
    )

phases = np.array(phases)

relative_phase = np.degrees(
    np.angle(np.exp(1j * (phases - phases[0])))
)

coherence = np.abs(np.mean(np.exp(1j * phases)))

print(f"\nTarget range: {range_axis[target_bin]:.3f} m")
print(f"Phase coherence: {coherence:.4f}")

# Phase stability graph
plt.figure(figsize=(9, 4))
plt.plot(range(1, 6), relative_phase, "o-")
plt.xlabel("Capture number")
plt.ylabel("Relative phase (degrees)")
plt.title("Radar Phase Stability")
plt.xticks(range(1, 6))
plt.grid()
plt.tight_layout()

# Amplitude stability graph
plt.figure(figsize=(9, 4))
plt.plot(range(1, 6), amplitudes, "o-")
plt.xlabel("Capture number")
plt.ylabel("Amplitude")
plt.title("Radar Amplitude Stability")
plt.xticks(range(1, 6))
plt.grid()
plt.tight_layout()

plt.show()
