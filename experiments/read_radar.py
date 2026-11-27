
import numpy as np
from pathlib import Path

# Radar configuration
NUM_RX = 4
NUM_SAMPLES = 256
NUM_CHIRPS = 128
NUM_FRAMES = 8

# Locate the radar data file
file_path = Path(__file__).resolve().parents[1] / "data" / "adc_data.bin"

# Read signed 16-bit ADC measurements
raw_data = np.fromfile(file_path, dtype="<i2")

expected = NUM_RX * NUM_SAMPLES * NUM_CHIRPS * NUM_FRAMES * 2

print("File size:", file_path.stat().st_size, "bytes")
print("ADC values:", raw_data.size)
print("Expected values:", expected)
print("Minimum ADC value:", raw_data.min())
print("Maximum ADC value:", raw_data.max())
print("Zero values:", np.count_nonzero(raw_data == 0))

if raw_data.size == expected:
    print("SUCCESS: Radar data size matches!")
else:
    print("ERROR: Unexpected data size!")
