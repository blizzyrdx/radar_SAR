
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================
# Radar configuration
# ==========================================

C = 299792458
FC = 77e9
FS = 10e6
SLOPE = 60.012e12

NUM_RX = 4
NUM_SAMPLES = 512
NUM_CHIRPS = 128
NUM_FRAMES = 8

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# ==========================================
# Load and decode ADC data
# ==========================================

def load_radar(filename):

    raw = np.fromfile(
        DATA_DIR / filename,
        dtype="<i2"
    )

    expected = (
        NUM_FRAMES * NUM_CHIRPS *
        NUM_RX * NUM_SAMPLES * 2
    )

    if raw.size != expected:
        raise ValueError(f"Invalid file size: {filename}")

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

background = load_radar("background.bin")
target = load_radar("target.bin")

print("Background:", background.shape)
print("Target:", target.shape)

# ==========================================
# Coherent averaging
# ==========================================

# Average chirps and frames independently
# for each receiving antenna

background_avg = np.mean(background, axis=(0, 1))
target_avg = np.mean(target, axis=(0, 1))

# ==========================================
# Background subtraction
# ==========================================

clean_signal = target_avg - background_avg

# ==========================================
# Range FFT
# ==========================================

window = np.hanning(NUM_SAMPLES)
NFFT = 2048

background_fft = np.fft.fft(
    background_avg * window,
    n=NFFT,
    axis=-1
)

target_fft = np.fft.fft(
    target_avg * window,
    n=NFFT,
    axis=-1
)

clean_fft = np.fft.fft(
    clean_signal * window,
    n=NFFT,
    axis=-1
)

range_axis = (
    np.arange(NFFT) * C * FS
    / (2 * SLOPE * NFFT)
)

# Combine power across receiving antennas
background_power = np.mean(
    np.abs(background_fft)**2, axis=0
)

target_power = np.mean(
    np.abs(target_fft)**2, axis=0
)

clean_power = np.mean(
    np.abs(clean_fft)**2, axis=0
)

# Use the same reference for all three plots
reference = max(target_power.max(), background_power.max())

def to_db(power):
    return 10 * np.log10(
        power / (reference + 1e-12) + 1e-12
    )

background_db = to_db(background_power)
target_db = to_db(target_power)
clean_db = to_db(clean_power)

# ==========================================
# Find strongest changed reflection
# ==========================================

valid = np.where(
    (range_axis >= 0.5) &
    (range_axis <= 3.0)
)[0]

peak = valid[np.argmax(clean_power[valid])]

print(
    f"Strongest changed reflection: "
    f"{range_axis[peak]:.3f} m"
)

# ==========================================
# Plot comparison
# ==========================================

fig, axes = plt.subplots(
    3, 1, figsize=(11, 9), sharex=True
)

profiles = [
    (background_db, "Background Only", "gray"),
    (target_db, "Environment With Target", "blue"),
    (clean_db, "Background Subtracted", "green")
]

for ax, (profile, title, color) in zip(axes, profiles):

    ax.plot(range_axis, profile, color=color)
    ax.set_title(title)
    ax.set_ylabel("Relative Power (dB)")
    ax.set_xlim(0, 10)
    ax.set_ylim(-65, 5)
    ax.grid(alpha=0.3)

axes[2].axvline(
    range_axis[peak],
    color="red",
    linestyle="--",
    label=f"Peak: {range_axis[peak]:.2f} m"
)

axes[2].legend()
axes[2].set_xlabel("Distance (m)")

plt.tight_layout()

# Preserve complex measurements for future SAR work
np.save(DATA_DIR / "clean_iq.npy", clean_signal)

print("Saved background-subtracted complex I/Q data.")

plt.show()
