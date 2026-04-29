from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from typing import Callable, TextIO

from .calibration import Calibration, load_calibration
from .control_mapping import CONTROL_CHANNELS, ControlReading, reading_from_raw

HARDWARE_MODULES = (
    "spidev",
    "gpiod",
    "src.spi_devices",
    "src.gpio_backend",
)


def hardware_modules_loaded() -> list[str]:
    return [module for module in HARDWARE_MODULES if module in sys.modules]


def simulated_raw_value(sample: int, channel_index: int, total_samples: int) -> float:
    if total_samples <= 1:
        base = 0.5
    else:
        base = sample / total_samples
    return (base + channel_index * 0.17) % 1.0


def collect_simulated_readings(
    samples: int,
    calibration: Calibration,
) -> list[ControlReading]:
    return [
        reading_from_raw(
            sample=sample,
            channel=channel,
            raw_value=simulated_raw_value(sample, channel_index, samples),
            calibration=calibration,
        )
        for sample in range(samples)
        for channel_index, channel in enumerate(CONTROL_CHANNELS)
    ]


def collect_input_readings(
    samples: int,
    calibration: Calibration,
    read_raw: Callable[[int], float],
    interval_s: float,
) -> list[ControlReading]:
    readings: list[ControlReading] = []
    for sample in range(samples):
        for channel in CONTROL_CHANNELS:
            readings.append(
                reading_from_raw(
                    sample=sample,
                    channel=channel,
                    raw_value=read_raw(channel.hardware_channel),
                    calibration=calibration,
                )
            )
        if interval_s > 0.0 and sample < samples - 1:
            time.sleep(interval_s)
    return readings


def print_table(readings: list[ControlReading], stdout: TextIO) -> None:
    print("sample channel control raw normalized mapped unit", file=stdout)
    for reading in readings:
        print(
            f"{reading.sample:03d} "
            f"{reading.adc_name:<3} "
            f"{reading.control_name:<7} "
            f"{reading.raw_value:0.6f} "
            f"{reading.normalized:0.6f} "
            f"{reading.mapped_value:0.6f} "
            f"{reading.mapped_unit}",
            file=stdout,
        )


def print_csv(readings: list[ControlReading], stdout: TextIO) -> None:
    writer = csv.writer(stdout)
    writer.writerow(["sample", "channel", "control", "raw", "normalized", "mapped", "unit"])
    for reading in readings:
        writer.writerow(
            [
                reading.sample,
                reading.adc_name,
                reading.control_name,
                f"{reading.raw_value:0.6f}",
                f"{reading.normalized:0.6f}",
                f"{reading.mapped_value:0.6f}",
                reading.mapped_unit,
            ]
        )


def print_json(readings: list[ControlReading], stdout: TextIO) -> None:
    payload = [
        {
            "sample": reading.sample,
            "channel": reading.adc_name,
            "control": reading.control_name,
            "raw": reading.raw_value,
            "normalized": reading.normalized,
            "mapped": reading.mapped_value,
            "unit": reading.mapped_unit,
        }
        for reading in readings
    ]
    json.dump(payload, stdout, indent=2)
    print(file=stdout)


def emit_readings(
    readings: list[ControlReading],
    output_format: str,
    stdout: TextIO,
) -> None:
    if output_format == "csv":
        print_csv(readings, stdout)
    elif output_format == "json":
        print_json(readings, stdout)
    else:
        print_table(readings, stdout)


def run_simulation(
    samples: int,
    calibration: Calibration,
    output_format: str,
    stdout: TextIO,
) -> list[ControlReading]:
    readings = collect_simulated_readings(samples, calibration)
    emit_readings(readings, output_format, stdout)
    return readings


def run_input(
    samples: int,
    interval_s: float,
    calibration: Calibration,
    output_format: str,
    stdout: TextIO,
) -> list[ControlReading]:
    from .gpio_backend import GPIOBackend
    from .spi_devices import ADS1256

    gpio = GPIOBackend()
    adc = ADS1256(gpio)
    adc.init()

    try:
        readings = collect_input_readings(
            samples=samples,
            calibration=calibration,
            read_raw=adc.read_channel_raw,
            interval_s=interval_s,
        )
        emit_readings(readings, output_format, stdout)
        return readings
    finally:
        adc.close()
        gpio.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor calibrated ADC control values.")
    parser.add_argument("--simulate", action="store_true", help="run without ADC/GPIO/SPI access")
    parser.add_argument("--enable-input", action="store_true", help="allow real ADC input reads")
    parser.add_argument("--samples", type=int, default=10, help="number of sample frames")
    parser.add_argument("--interval", type=float, default=0.0, help="seconds between sample frames")
    parser.add_argument("--csv", action="store_true", help="print CSV output")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    parser.add_argument(
        "--calibration",
        default=None,
        help="path to calibration JSON; defaults to config/calibration.json",
    )
    return parser


def main(argv: list[str] | None = None, stdout: TextIO = sys.stdout) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.simulate and args.enable_input:
        parser.error("--simulate and --enable-input cannot be used together")
    if args.csv and args.json:
        parser.error("--csv and --json cannot be used together")
    if args.samples < 1:
        parser.error("--samples must be at least 1")
    if args.interval < 0.0:
        parser.error("--interval must be non-negative")

    if not args.simulate and not args.enable_input:
        parser.error(
            "real ADC input is disabled by default; use --simulate for safe "
            "software output or --enable-input while present to allow ADC/GPIO/SPI access"
        )

    calibration = load_calibration(args.calibration)
    output_format = "json" if args.json else "csv" if args.csv else "table"

    if args.simulate:
        run_simulation(
            samples=args.samples,
            calibration=calibration,
            output_format=output_format,
            stdout=stdout,
        )
        return

    run_input(
        samples=args.samples,
        interval_s=args.interval,
        calibration=calibration,
        output_format=output_format,
        stdout=stdout,
    )


if __name__ == "__main__":
    main()
