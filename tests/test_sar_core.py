
import numpy as np
import pytest

from radar.radar_config import CONFIG
from radar.packet_validator import validate_packets
from radar.radar_processing import (
    load_adc,
    range_fft,
    coherent_profile
)


# ==========================================
# Generate controlled packet logs
# ==========================================

def write_packet_log(recording, lost=0):

    log = recording.with_name(
        recording.stem + "_Raw_LogFile.csv"
    )

    log.write_text(
        f"First Packet ID - 1\n"
        f"Last Packet ID - 5762\n"
        f"Number of received packets - {5762 - lost}\n"
        f"Number of zero filled packets - {lost}\n"
        f"Number of zero filled bytes - {lost * 1456}\n",
        encoding="utf-8"
    )


# ==========================================
# Test 1: Accept complete recordings
# ==========================================

def test_valid_packets(tmp_path):

    recording = tmp_path / "capture.bin"

    write_packet_log(recording)

    assert validate_packets(recording) is True


# ==========================================
# Test 2: Reject missing packets
# ==========================================

def test_packet_loss_rejection(tmp_path):

    recording = tmp_path / "capture.bin"

    write_packet_log(recording, lost=1)

    assert validate_packets(recording) is False


# ==========================================
# Test 3: Verify complex ADC decoding
# ==========================================

def test_adc_decoding(tmp_path):

    recording = tmp_path / "capture.bin"

    raw = np.zeros(
        CONFIG.expected_bytes // 2,
        dtype="<i2"
    )

    raw[:8] = [
        100, 200, -300, 400,
        500, 600, 700, -800
    ]

    raw.tofile(recording)

    write_packet_log(recording)

    cube = load_adc(recording)

    assert cube.shape == (
        CONFIG.num_frames,
        CONFIG.num_chirps,
        CONFIG.num_rx,
        CONFIG.num_samples
    )

    np.testing.assert_array_equal(
        cube.flatten()[:4],
        [
            100 - 300j,
            200 + 400j,
            500 + 700j,
            600 - 800j
        ]
    )


# ==========================================
# Test 4: Reject incomplete recordings
# ==========================================

def test_invalid_recording_size(tmp_path):

    recording = tmp_path / "capture.bin"

    recording.write_bytes(b"\x00\x00")

    with pytest.raises(ValueError):
        load_adc(recording)


# ==========================================
# Test 5: Verify range FFT and phase
# ==========================================

def test_range_fft():

    peak_bin = 100
    phase = 0.75

    n = np.arange(CONFIG.num_samples)

    signal = np.exp(
        1j * (
            2 * np.pi * peak_bin * n / CONFIG.nfft
            + phase
        )
    )

    cube = signal.reshape(1, 1, 1, -1)

    ranges, spectrum = range_fft(cube)

    profile = spectrum[0, 0, 0]

    assert np.argmax(np.abs(profile)) == peak_bin

    assert ranges[peak_bin] == pytest.approx(
        peak_bin * CONFIG.range_bin_spacing
    )

    assert np.angle(profile[peak_bin]) == pytest.approx(
        phase,
        abs=1e-6
    )


# ==========================================
# Test 6: Verify coherent phase preservation
# ==========================================

def test_coherent_phase():

    spectrum = np.zeros(
        (2, 4, CONFIG.num_rx, 1024),
        dtype=np.complex128
    )

    expected = 3 + 4j

    spectrum[:, :, 0, 100] = expected

    profile = coherent_profile(spectrum, rx=0)

    assert profile[100] == pytest.approx(expected)

    assert np.abs(profile[100]) == pytest.approx(5.0)
