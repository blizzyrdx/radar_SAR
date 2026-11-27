
import pytest

from radar.radar_config import CONFIG


# ==========================================
# Radar hardware configuration
# ==========================================

def test_receiver_count():
    assert CONFIG.num_rx == 4


def test_transmitter_count():
    assert CONFIG.num_tx == 1


def test_adc_samples():
    assert CONFIG.num_samples == 512


def test_chirps_per_frame():
    assert CONFIG.num_chirps == 128


def test_frame_count():
    assert CONFIG.num_frames == 8


def test_adc_bits():
    assert CONFIG.adc_bits == 16


def test_fft_size():
    assert CONFIG.nfft == 2048


def test_packet_delay():
    assert CONFIG.packet_delay_us == 50


# ==========================================
# Radar mathematical calculations
# ==========================================

def test_sampled_bandwidth():
    assert CONFIG.bandwidth == pytest.approx(
        3.0726144e9,
        rel=1e-6
    )


def test_center_frequency():
    assert CONFIG.center_frequency == pytest.approx(
        78.8934e9,
        rel=1e-6
    )


def test_range_resolution():
    assert CONFIG.range_resolution == pytest.approx(
        0.0487846,
        rel=1e-5
    )


def test_range_bin_spacing():
    assert CONFIG.range_bin_spacing == pytest.approx(
        0.0121961,
        rel=1e-5
    )


def test_expected_recording_size():
    assert CONFIG.expected_bytes == 8388608


def test_configuration_serialization():
    configuration = CONFIG.to_dict()

    assert isinstance(configuration, dict)
    assert configuration["num_rx"] == 4
    assert configuration["num_samples"] == 512
    assert configuration["num_frames"] == 8


def test_fft_not_smaller_than_adc():
    assert CONFIG.nfft >= CONFIG.num_samples
