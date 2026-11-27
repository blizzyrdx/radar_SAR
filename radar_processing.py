
import numpy as np
import matplotlib.pyplot as plt
import sys

from pathlib import Path
from packet_validator import validate_packets
from radar_config import CONFIG

# ==========================================
# Radar configuration
# ==========================================

NUM_RX = CONFIG.num_rx
NUM_SAMPLES = CONFIG.num_samples
NUM_CHIRPS = CONFIG.num_chirps
NUM_FRAMES = CONFIG.num_frames

C = CONFIG.speed_of_light
FC = CONFIG.start_frequency_hz
FS = CONFIG.sample_rate_hz
SLOPE = CONFIG.slope_hz_s

WAVELENGTH = CONFIG.wavelength
BANDWIDTH = CONFIG.bandwidth
RANGE_RESOLUTION = CONFIG.range_resolution

EXPECTED_BYTES = CONFIG.expected_bytes

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "acquisitions"


# ==========================================
# Find latest recording
# ==========================================

def latest_recording():

    files = list(DATA_DIR.glob("capture_*.bin"))

    if not files:
        raise FileNotFoundError(
            "No radar recordings found."
        )

    return max(
        files,
        key=lambda path: path.stat().st_mtime
    )


# ==========================================
# Decode complex ADC data
# ==========================================

def load_adc(path):

    path = Path(path)

    if path.stat().st_size != EXPECTED_BYTES:
        raise ValueError(
            "Unexpected recording size."
        )

    if not validate_packets(path):
        raise ValueError(
            "Recording failed packet validation."
        )

    raw = np.fromfile(path, dtype="<i2")

    # Two I samples followed by two Q samples
    groups = raw.reshape(-1, 4).astype(
        np.float32
    )

    iq = (
        groups[:, :2] +
        1j * groups[:, 2:]
    ).flatten()

    cube = iq.reshape(
        NUM_FRAMES,
        NUM_CHIRPS,
        NUM_RX,
        NUM_SAMPLES
    )

    return cube


# ==========================================
# Complex range FFT
# ==========================================

def range_fft(cube, nfft=CONFIG.nfft):
    
    if nfft < NUM_SAMPLES:
        raise ValueError("FFT length too small.")

    window = np.hanning(NUM_SAMPLES)

    windowed = cube * window

    spectrum = np.fft.fft(
        windowed,
        n=nfft,
        axis=-1
    )

    spectrum /= np.sum(window)

    spectrum = spectrum[..., :nfft // 2]

    frequencies = (
        np.arange(nfft // 2) * FS / nfft
    )

    ranges = (
        C * frequencies / (2 * SLOPE)
    )

    return ranges, spectrum


# ==========================================
# Average range power
# ==========================================

def range_power(spectrum):

    return np.mean(
        np.abs(spectrum) ** 2,
        axis=(0, 1, 2)
    )


# ==========================================
# Coherent range profile
# ==========================================

def coherent_profile(spectrum, rx=0):

    if rx < 0 or rx >= NUM_RX:
        raise ValueError("Invalid RX channel.")

    selected = spectrum[:, :, rx, :]

    # Preserve complex amplitude and phase
    profile = np.mean(
        selected,
        axis=(0, 1)
    )

    return profile


# ==========================================
# Relative power in decibels
# ==========================================

def power_db(power):

    reference = np.max(power)

    if reference <= 0:
        return np.full_like(
            power, -120, dtype=float
        )

    return 10 * np.log10(
        np.maximum(power / reference, 1e-12)
    )


# ==========================================
# Process and visualize recording
# ==========================================

def process_recording(path):

    print("\n========== RADAR PROCESSING ==========")

    print(f"Recording: {path.name}")

    cube = load_adc(path)

    print(f"ADC cube: {cube.shape}")
    print(f"ADC type: {cube.dtype}")
    print(f"Wavelength: {WAVELENGTH * 1000:.3f} mm")
    print(f"Bandwidth: {BANDWIDTH / 1e9:.4f} GHz")
    print(
        f"Range resolution: "
        f"{RANGE_RESOLUTION * 100:.3f} cm"
    )

    ranges, spectrum = range_fft(cube)

    print(f"Range FFT cube: {spectrum.shape}")

    power = range_power(spectrum)

    coherent = coherent_profile(
        spectrum,
        rx=0
    )

    power_dB = power_db(power)

    coherent_dB = power_db(
        np.abs(coherent) ** 2
    )

    # Strongest reflection between 0.5 and 3 m
    mask = (ranges >= 0.5) & (ranges <= 3.0)

    indices = np.flatnonzero(mask)

    peak_index = indices[
        np.argmax(power[indices])
    ]

    peak_range = ranges[peak_index]

    print("\n========== RANGE ANALYSIS ==========")

    print(
        f"Strongest reflection (0.5-3 m): "
        f"{peak_range:.4f} m"
    )

    print(
        f"RX0 coherent amplitude: "
        f"{np.abs(coherent[peak_index]):.4f}"
    )

    print(
        f"RX0 coherent phase: "
        f"{np.angle(coherent[peak_index], deg=True):.4f} degrees"
    )

    # ======================================
    # Figure 1: Range profile
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.plot(
        ranges,
        power_dB,
        label="Average range power"
    )

    plt.axvline(
        peak_range,
        color="red",
        linestyle="--",
        label=f"Peak: {peak_range:.3f} m"
    )

    plt.title("Measured Radar Range Profile")
    plt.xlabel("Distance (m)")
    plt.ylabel("Relative Power (dB)")
    plt.xlim(0, 10)
    plt.ylim(-70, 5)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # ======================================
    # Figure 2: Coherent amplitude
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.plot(
        ranges,
        coherent_dB
    )

    plt.title("Coherent Range Profile - RX0")
    plt.xlabel("Distance (m)")
    plt.ylabel("Relative Power (dB)")
    plt.xlim(0, 10)
    plt.ylim(-70, 5)
    plt.grid(True)
    plt.tight_layout()

    # ======================================
    # Figure 3: Complex range profile
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.plot(
        ranges,
        coherent.real,
        label="Real"
    )

    plt.plot(
        ranges,
        coherent.imag,
        label="Imaginary"
    )

    plt.title("Complex Range Measurements - RX0")
    plt.xlabel("Distance (m)")
    plt.ylabel("Amplitude")
    plt.xlim(0, 5)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # ======================================
    # Figure 4: Phase across frames
    # ======================================

    frame_complex = np.mean(
        spectrum[:, :, 0, peak_index],
        axis=1
    )

    relative_phase = np.angle(
        frame_complex *
        np.conj(frame_complex[0]),
        deg=True
    )

    plt.figure(figsize=(9, 5))

    plt.plot(
        np.arange(1, NUM_FRAMES + 1),
        relative_phase,
        marker="o"
    )

    plt.title("Target Phase Across Frames")
    plt.xlabel("Frame Number")
    plt.ylabel("Relative Phase (degrees)")
    plt.grid(True)
    plt.tight_layout()

    plt.show()

    return ranges, coherent


# ==========================================
# Main program
# ==========================================

if __name__ == "__main__":

    if len(sys.argv) > 1:
        recording = Path(sys.argv[1])
    else:
        recording = latest_recording()

    process_recording(recording)
