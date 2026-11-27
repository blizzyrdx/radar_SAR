
from dataclasses import dataclass, asdict
import json


@dataclass(frozen=True)
class RadarConfig:

    # Physical constants
    speed_of_light: float = 299792458

    # Radar profile
    start_frequency_hz: float = 77e9
    slope_hz_s: float = 60.012e12
    sample_rate_hz: float = 10e6

    adc_start_time_s: float = 6e-6
    idle_time_s: float = 100e-6
    ramp_end_time_s: float = 65e-6

    # Acquisition configuration
    num_rx: int = 4
    num_tx: int = 1
    num_samples: int = 512
    num_chirps: int = 128
    num_frames: int = 8
    adc_bits: int = 16

    frame_periodicity_ms: float = 40
    packet_delay_us: int = 50

    # Processing configuration
    nfft: int = 2048

    @property
    def bandwidth(self):
        return (
            self.slope_hz_s *
            self.num_samples /
            self.sample_rate_hz
        )

    @property
    def wavelength(self):
        return (
            self.speed_of_light /
            self.start_frequency_hz
        )

    @property
    def center_frequency(self):
        return (
            self.start_frequency_hz +
            self.slope_hz_s * (
                self.adc_start_time_s +
                (self.num_samples - 1) /
                (2 * self.sample_rate_hz)
            )
        )

    @property
    def range_resolution(self):
        return (
            self.speed_of_light /
            (2 * self.bandwidth)
        )

    @property
    def range_bin_spacing(self):
        return (
            self.speed_of_light *
            self.sample_rate_hz /
            (2 * self.slope_hz_s * self.nfft)
        )

    @property
    def expected_bytes(self):
        return (
            self.num_rx *
            self.num_samples *
            self.num_chirps *
            self.num_frames *
            2 *
            (self.adc_bits // 8)
        )

    def to_dict(self):
        return asdict(self)

    def summary(self):

        print("\n========== RADAR CONFIGURATION ==========")

        print(f"RX channels: {self.num_rx}")
        print(f"TX channels: {self.num_tx}")
        print(f"ADC samples: {self.num_samples}")
        print(f"Chirps per frame: {self.num_chirps}")
        print(f"Frames: {self.num_frames}")
        print(f"FFT size: {self.nfft}")

        print(
            f"Start frequency: "
            f"{self.start_frequency_hz / 1e9:.4f} GHz"
        )

        print(
            f"Center frequency: "
            f"{self.center_frequency / 1e9:.4f} GHz"
        )

        print(
            f"Sampled bandwidth: "
            f"{self.bandwidth / 1e9:.4f} GHz"
        )

        print(
            f"Range resolution: "
            f"{self.range_resolution * 1000:.4f} mm"
        )

        print(
            f"Range bin spacing: "
            f"{self.range_bin_spacing * 1000:.4f} mm"
        )

        print(
            f"Expected recording size: "
            f"{self.expected_bytes} bytes"
        )

        print(
            f"Packet delay: "
            f"{self.packet_delay_us} us"
        )


CONFIG = RadarConfig()


if __name__ == "__main__":

    CONFIG.summary()

    print("\n========== CONFIGURATION JSON ==========")

    print(json.dumps(CONFIG.to_dict(), indent=4))
