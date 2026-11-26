
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# AWR1843AoP radar parameters
# ==========================================

C = 299792458
FC = 77e9
FS = 10e6
SLOPE = 60.012e12
NUM_SAMPLES = 512
ADC_START = 6e-6

BANDWIDTH = SLOPE * NUM_SAMPLES / FS
WAVELENGTH = C / FC

# ==========================================
# Synthetic aperture configuration
# ==========================================

APERTURE_LENGTH = 0.30
NUM_POSITIONS = 301

radar_positions = np.linspace(
    -APERTURE_LENGTH / 2,
    APERTURE_LENGTH / 2,
    NUM_POSITIONS
)

# Target format: (x position, y position, reflectivity)
# All positions are in meters

targets = [
    (-0.15, 0.8, 1.0),
    (0.00, 1.2, 0.8),
    (0.15, 0.9, 1.0)
]

# Instantaneous sampled frequencies
frequencies = FC + SLOPE * (
    ADC_START + np.arange(NUM_SAMPLES) / FS
)

print("Radar wavelength:", WAVELENGTH * 1000, "mm")
print("Sampled bandwidth:", BANDWIDTH / 1e9, "GHz")
print("Range resolution:", C / (2 * BANDWIDTH), "m")
print("Scanning positions:", NUM_POSITIONS)

# ==========================================
# Simulate complex radar measurements
# ==========================================

radar_data = np.zeros(
    (NUM_POSITIONS, NUM_SAMPLES),
    dtype=np.complex128
)

for i, radar_x in enumerate(radar_positions):

    for target_x, target_y, amplitude in targets:

        distance = np.sqrt(
            (target_x - radar_x)**2 + target_y**2
        )

        phase = -4 * np.pi * frequencies * distance / C

        radar_data[i] += amplitude * np.exp(1j * phase)

# Add simulated measurement noise
rng = np.random.default_rng(42)

noise = 0.05 * (
    rng.standard_normal(radar_data.shape)
    + 1j * rng.standard_normal(radar_data.shape)
)

radar_data += noise

print("Simulated radar data:", radar_data.shape)

# ==========================================
# Range compression
# ==========================================

NFFT = 4096

window = np.hanning(NUM_SAMPLES)

range_profiles = np.fft.ifft(
    radar_data * window,
    n=NFFT,
    axis=1
)

range_axis = (
    np.arange(NFFT) * C * FS
    / (2 * SLOPE * NFFT)
)

# ==========================================
# Define the reconstruction image
# ==========================================

x_axis = np.linspace(-0.5, 0.5, 251)
y_axis = np.linspace(0.5, 1.5, 251)

X, Y = np.meshgrid(x_axis, y_axis)

sar_image = np.zeros(
    X.shape,
    dtype=np.complex128
)

# ==========================================
# SAR backprojection algorithm
# ==========================================

reference_frequency = frequencies[0]

print("Performing SAR backprojection...")

for i, radar_x in enumerate(radar_positions):

    # Distance from radar to every image pixel
    R = np.sqrt((X - radar_x)**2 + Y**2)

    profile = range_profiles[i]

    # Interpolate complex range measurements
    real_part = np.interp(
        R.ravel(),
        range_axis,
        profile.real,
        left=0,
        right=0
    ).reshape(R.shape)

    imag_part = np.interp(
        R.ravel(),
        range_axis,
        profile.imag,
        left=0,
        right=0
    ).reshape(R.shape)

    complex_signal = real_part + 1j * imag_part

    # Compensate propagation phase
    phase_correction = np.exp(
        1j * 4 * np.pi * reference_frequency * R / C
    )

    # Coherently combine measurements
    sar_image += complex_signal * phase_correction

    if (i + 1) % 50 == 0:
        print(f"Processed {i + 1}/{NUM_POSITIONS}")

# ==========================================
# Normalize reconstructed image
# ==========================================

magnitude = np.abs(sar_image)

magnitude /= magnitude.max() + 1e-12

image_db = 20 * np.log10(magnitude + 1e-12)

print("SAR reconstruction completed!")

# ==========================================
# Plot 1: Experimental geometry
# ==========================================

plt.figure(figsize=(8, 6))

plt.plot(
    radar_positions,
    np.zeros(NUM_POSITIONS),
    "b.",
    label="Radar positions"
)

for tx, ty, amp in targets:
    plt.scatter(tx, ty, c="red", s=100, marker="x")

plt.xlabel("Cross-range (m)")
plt.ylabel("Forward distance (m)")
plt.title("Simulated SAR Geometry")
plt.legend()
plt.axis("equal")
plt.grid()

# ==========================================
# Plot 2: Range profiles
# ==========================================

plt.figure(figsize=(9, 6))

plt.imshow(
    np.abs(range_profiles).T,
    extent=[
        radar_positions[0],
        radar_positions[-1],
        range_axis[0],
        range_axis[-1]
    ],
    origin="lower",
    aspect="auto",
    cmap="jet"
)

plt.ylim(0.5, 1.5)
plt.xlabel("Radar position (m)")
plt.ylabel("Range (m)")
plt.title("Simulated Radar Range Measurements")
plt.colorbar(label="Amplitude")

# ==========================================
# Plot 3: Reconstructed SAR image
# ==========================================

plt.figure(figsize=(9, 7))

plt.imshow(
    image_db,
    extent=[
        x_axis[0],
        x_axis[-1],
        y_axis[0],
        y_axis[-1]
    ],
    origin="lower",
    aspect="equal",
    cmap="jet",
    vmin=-35,
    vmax=0
)

for tx, ty, amp in targets:
    plt.scatter(
        tx, ty,
        marker="+",
        c="white",
        s=100
    )

plt.xlabel("Cross-range (m)")
plt.ylabel("Forward distance (m)")
plt.title("Reconstructed SAR Image")
plt.colorbar(label="Relative amplitude (dB)")
plt.tight_layout()

plt.show()
