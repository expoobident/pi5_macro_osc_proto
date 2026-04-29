from __future__ import annotations

import argparse
import sys
from typing import TextIO

from .calibration import DEFAULT_CALIBRATION_PATH, load_calibration


def print_instructions(stdout: TextIO) -> None:
    calibration = load_calibration()

    print("Pi 5 macro oscillator DAC calibration", file=stdout)
    print("Simulation/instruction mode: no GPIO, SPI, ADC, or DAC hardware is opened.", file=stdout)
    print("", file=stdout)
    print("1. Connect Pokit black/COM to board GND.", file=stdout)
    print("2. Connect Pokit red/V to DAC0.", file=stdout)
    print("3. Start with the simulation command below and confirm the table looks sane:", file=stdout)
    print("   python3 -m src.dac_test --channel DAC0 --volts 1.65 --seconds 0", file=stdout)
    print("4. When ready, watch the meter/scope and run the same command with --enable-output.", file=stdout)
    print("5. Record measured DAC0 voltage at 0.0V and 3.3V targets.", file=stdout)
    print("6. Move Pokit red/V to DAC1 and repeat the same measurements.", file=stdout)
    print("7. Update calibration JSON with gain and offset corrections:", file=stdout)
    print(f"   {DEFAULT_CALIBRATION_PATH}", file=stdout)
    print("", file=stdout)
    print("Current DAC calibration:", file=stdout)
    print(
        f"  DAC0 gain={calibration.dac0.gain:0.6f} "
        f"offset={calibration.dac0.offset_volts:0.6f}V",
        file=stdout,
    )
    print(
        f"  DAC1 gain={calibration.dac1.gain:0.6f} "
        f"offset={calibration.dac1.offset_volts:0.6f}V",
        file=stdout,
    )
    print("", file=stdout)
    print("Note: measured full-scale may be around 3.28V instead of exactly 3.30V.", file=stdout)
    print("Real output requires --enable-output and should only be used while watching the meter/scope.", file=stdout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print safe Pokit Pro DAC calibration steps.",
    )
    parser.add_argument(
        "--enable-output",
        action="store_true",
        help="reserved for an explicit real-output calibration flow; not used by instruction mode",
    )
    return parser


def main(argv: list[str] | None = None, stdout: TextIO = sys.stdout) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.enable_output:
        parser.error(
            "real-output calibration is intentionally not automated here; use "
            "src.dac_test with --enable-output manually while watching the meter/scope"
        )

    print_instructions(stdout)


if __name__ == "__main__":
    main()
