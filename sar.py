
import sys
import subprocess

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# ==========================================
# Radar and SAR commands
# ==========================================

COMMANDS = {
    "config": (
        "radar.radar_config",
        "Display radar configuration"
    ),

    "connection": (
        "radar.radar_session",
        "Test persistent radar connection"
    ),

    "capture": (
        "radar.radar_acquisition",
        "Acquire validated radar data"
    ),

    "integrity": (
        "radar.radar_integrity",
        "Check recording integrity"
    ),

    "process": (
        "radar.radar_processing",
        "Process complex radar signals"
    ),

    "coherence": (
        "experiments.coherence_test",
        "Test inter-capture phase coherence"
    ),

    "background": (
        "experiments.background_subtraction",
        "Perform background subtraction"
    ),

    "scan": (
        "imaging.sar_acquisition",
        "Collect position-tagged measurements"
    ),

    "dataset": (
        "imaging.sar_dataset",
        "Load and visualize SAR dataset"
    ),

    "validate": (
        "imaging.sar_scan_check",
        "Validate SAR scan readiness"
    ),

    "reconstruct": (
        "imaging.sar_reconstruct",
        "Reconstruct SAR image"
    ),

    "simulate": (
        "imaging.sar_simulation",
        "Run SAR simulation"
    ),

    "quality": (
        "imaging.sar_quality",
        "Characterize SAR image quality"
    )
}


# ==========================================
# Display command menu
# ==========================================

def show_commands():

    print("\n========================================")
    print("     SYNTHETIC APERTURE RADAR SYSTEM")
    print("========================================")

    print("Hardware: AWR1843AoP + DCA1000EVM")

    print("\nAVAILABLE COMMANDS\n")

    for name, (_, description) in COMMANDS.items():

        print(f"  {name:15} {description}")

    print("\nUSAGE")

    print("  python sar.py <command> [arguments]")

    print("\nEXAMPLES")

    print("  python sar.py config")
    print("  python sar.py capture")
    print("  python sar.py validate")
    print("  python sar.py reconstruct --synthetic")

    print(
        "  python sar.py reconstruct "
        "--synthetic --compare-signs"
    )


# ==========================================
# Main command-line interface
# ==========================================

def main():

    if len(sys.argv) < 2:

        show_commands()
        return 0

    command = sys.argv[1].lower()

    arguments = sys.argv[2:]

    if command in ("help", "--help", "-h"):

        show_commands()
        return 0

    if command not in COMMANDS:

        print(f"Unknown command: {command}")

        show_commands()

        return 1

    module, description = COMMANDS[command]

    print("\n========================================")
    print(f"SAR COMMAND: {command.upper()}")
    print(description)
    print("========================================\n", flush=True)

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                module,
                *arguments
            ],

            cwd=PROJECT_ROOT
        )

        return result.returncode

    except KeyboardInterrupt:

        print("\nOperation cancelled.")

        return 130


if __name__ == "__main__":

    raise SystemExit(main())
