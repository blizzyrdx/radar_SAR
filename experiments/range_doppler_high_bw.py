import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# =====================================
# Radar configuration
# =====================================

NUM_RX = 4
NUM_SAMPLES = 512
NUM_CHIRPS = 128
NUM_FRAMES = 8

C = 299792458
FC = 77e9
FS = 10e6
SLOPE = 60.012e12
CHIRP_TIME = 165e-6

# =====================================
# Read binary ADC data
# =====================================

file_path = Path(__file__).resolve().parents[1] / "data" / "adc_high_bw_01.bin"

raw = np.fromfile(file_path, dtype="<i2")

expected = NUM_FRAMES * NUM_CHIRPS * NUM_RX * NUM_SAMPLES * 2

if raw.size != expected:
    raise ValueError("Unexpected ADC file size")

# =====================================
# Decode complex I/Q samples
# =====================================

# Two I samples followed by two Q samples
groups = raw.reshape(-1, 4).astype(np.float32)

iq = (groups[:, :2] + 1j * groups[:, 2:]).flatten()

# Organize into a radar data cube
cube = iq.reshape(
    NUM_FRAMES,
    NUM_CHIRPS,
    NUM_RX,
    NUM_SAMPLES
)

print("Radar data cube:", cube.shape)

# Select first frame and receiver
signal = cube[0, :, 0, :]

# =====================================
# Range FFT
# =====================================

range_window = np.hanning(NUM_SAMPLES)

range_fft = np.fft.fft(
    signal * range_window,
    axis=1
)

range_axis = (
    np.arange(NUM_SAMPLES)
    * C * FS
    / (2 * SLOPE * NUM_SAMPLES)
)

range_profile = np.mean(
    np.abs(range_fft) ** 2,
    axis=0
)

range_db = 10 * np.log10(
    range_profile / (range_profile.max() + 1e-12)
    + 1e-12
)

# =====================================
# Doppler FFT
# =====================================

doppler_window = np.hanning(NUM_CHIRPS)

rd_fft = np.fft.fftshift(
    np.fft.fft(
        range_fft * doppler_window[:, None],
        axis=0
    ),
    axes=0
)

rd_power = np.abs(rd_fft) ** 2

rd_db = 10 * np.log10(
    rd_power / (rd_power.max() + 1e-12)
    + 1e-12
)

velocity_axis = (
    np.fft.fftshift(
        np.fft.fftfreq(NUM_CHIRPS, CHIRP_TIME)
    ) * C / (2 * FC)
)

# =====================================
# Plot 1: Raw I/Q signals
# =====================================

plt.figure(figsize=(10, 4))
plt.plot(signal[0].real, label="I")
plt.plot(signal[0].imag, label="Q")
plt.title("Raw Radar I/Q Samples")
plt.xlabel("ADC Sample")
plt.ylabel("Amplitude")
plt.legend()
plt.grid()

# =====================================
# Plot 2: Range profile
# =====================================

plt.figure(figsize=(10, 4))
plt.plot(range_axis, range_db)
plt.title("Radar Range Profile")
plt.xlabel("Distance (m)")
plt.ylabel("Relative Power (dB)")
plt.grid()

# =====================================
# Plot 3: Range-Doppler map
# =====================================

plt.figure(figsize=(9, 7))

plt.imshow(
    rd_db.T,
    aspect="auto",
    origin="lower",
    extent=[
        velocity_axis[0],
        velocity_axis[-1],
        range_axis[0],
        range_axis[-1]
    ],
    cmap="jet",
    vmin=-60,
    vmax=0
)

plt.title("Range-Doppler Map")
plt.xlabel("Velocity (m/s)")
plt.ylabel("Distance (m)")
plt.colorbar(label="Relative Power (dB)")
plt.tight_layout()

plt.show()
