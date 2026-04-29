from __future__ import annotations

import argparse
import sys
from typing import TextIO

from .calibration import DEFAULT_CALIBRATION_PATH, load_calibration
from .control_mapping import CONTROL_CHANNELS


def print_instructions(stdout: TextIO) -> None:
    calibration = load_calibration()

    print("Pi 5 macro oscillator ADC calibration", file=stdout)
    print("Instruction mode: no GPIO, SPI, ADC, or DAC hardware is opened.", file=stdout)
    print("", file=stdout)
    print("Control mapping:", file=stdout)
    for channel in CONTROL_CHANNELS:
        print(f"  {channel.adc_name} = {channel.control_name}", file=stdout)
    print("", file=stdout)
    print("1. Run the safe simulation monitor first:", file=stdout)
    print("   python3 -m src.control_monitor --simulate --samples 10", file=stdout)
    print("2. When present at the bench, read real ADC values with --enable-input.", file=stdout)
    print("3. Move each control through its full travel.", file=stdout)
    print("4. Record the lowest and highest raw values printed for each channel.", file=stdout)
    print("5. Update adc_min and adc_max in:", file=stdout)
    print(f"   {DEFAULT_CALIBRATION_PATH}", file=stdout)
    print("", file=stdout)
    print("Current ADC calibration:", file=stdout)
    for channel in CONTROL_CHANNELS:
        adc_calibration = calibration.adc[channel.adc_name]
        print(
            f"  {channel.adc_name} {channel.control_name:<7} "
            f"min={adc_calibration.minimum:0.6f} "
            f"max={adc_calibration.maximum:0.6f}",
            file=stdout,
        )
    print("", file=stdout)
    print("Real ADC sampling requires --enable-input and should only be done while you are present.", file=stdout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print safe ADC calibration steps.")
    parser.add_argument(
        "--enable-input",
        action="store_true",
        help="reserved for explicit real ADC sampling; not used by instruction mode",
    )
    return parser


def main(argv: list[str] | None = None, stdout: TextIO = sys.stdout) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.enable_input:
        parser.error(
            "real ADC sampling is not automated by this guide; use "
            "python3 -m src.control_monitor --enable-input while present"
        )

    print_instructions(stdout)


if __name__ == "__main__":
    main()
