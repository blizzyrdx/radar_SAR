
import re
import sys
from pathlib import Path

# Expected packet count for current radar configuration
EXPECTED_PACKETS = 5762


def validate_packets(recording):

    recording = Path(recording)

    log_path = recording.with_name(
        recording.stem + "_Raw_LogFile.csv"
    )

    if not log_path.is_file():
        raise FileNotFoundError(
            f"Missing packet log: {log_path.name}"
        )

    content = log_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    def extract(label):

        match = re.search(
            rf"{re.escape(label)}\s*-\s*(\d+)",
            content,
            re.IGNORECASE
        )

        if match is None:
            raise ValueError(
                f"Missing statistic: {label}"
            )

        return int(match.group(1))

    first = extract("First Packet ID")
    last = extract("Last Packet ID")

    received = extract(
        "Number of received packets"
    )

    lost = extract(
        "Number of zero filled packets"
    )

    zero_bytes = extract(
        "Number of zero filled bytes"
    )

    total = received + lost

    loss_rate = (
        100 * lost / total if total > 0 else 100
    )

    passed = (
        first == 1
        and last == EXPECTED_PACKETS
        and received == EXPECTED_PACKETS
        and lost == 0
        and zero_bytes == 0
    )

    print("\n========== PACKET VALIDATION ==========")

    print(f"First packet: {first}")
    print(f"Last packet: {last}")
    print(f"Expected packets: {EXPECTED_PACKETS}")
    print(f"Received packets: {received}")
    print(f"Lost packets: {lost}")
    print(f"Zero-filled bytes: {zero_bytes}")
    print(f"Packet loss: {loss_rate:.4f}%")

    if passed:
        print("PACKET INTEGRITY: PASS")
    else:
        print("PACKET INTEGRITY: FAIL")

    return passed


if __name__ == "__main__":

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python packet_validator.py <recording.bin>"
        )

    passed = validate_packets(sys.argv[1])

    sys.exit(0 if passed else 1)
