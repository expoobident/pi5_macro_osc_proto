from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
import time
from typing import Any, TextIO

from .calibration import Calibration, load_calibration
from .dac_output import (
    DAC_MAX_VOLTAGE,
    DacValue,
    SimulationDAC,
    clamp_voltage,
    dac_value_from_voltage,
)

CHANNELS = ("DAC0", "DAC1")
PATTERNS = ("steady", "ramp", "triangle")


@dataclass(frozen=True)
class DacTestRow:
    timestamp_s: float
    channel: str
    dac_value: DacValue


def normalize_channel(channel: str) -> str:
    normalized = channel.upper()
    if normalized not in CHANNELS:
        raise ValueError(f"channel must be one of: {', '.join(CHANNELS)}")
    return normalized


def write_channel(dac: Any, channel: str, voltage: float) -> Any:
    normalized = normalize_channel(channel)
    if normalized == "DAC0":
        return dac.write_voltage_a(voltage)
    return dac.write_voltage_b(voltage)


def resolve_target_voltage(pattern: str, volts: float | None) -> float:
    if volts is not None:
        return clamp_voltage(volts)
    if pattern == "steady":
        return 1.65
    return DAC_MAX_VOLTAGE


def sample_timestamps(seconds: float, rate_hz: float) -> list[float]:
    if seconds < 0.0:
        raise ValueError("seconds must be non-negative")
    if rate_hz <= 0.0:
        raise ValueError("rate_hz must be greater than zero")

    sample_count = max(1, int(round(seconds * rate_hz)) + 1)
    return [min(index / rate_hz, seconds) for index in range(sample_count)]


def pattern_voltage(pattern: str, target_voltage: float, index: int, count: int) -> float:
    target = clamp_voltage(target_voltage)
    if pattern == "steady" or count == 1:
        return target

    fraction = index / (count - 1)
    if pattern == "ramp":
        return clamp_voltage(target * fraction)
    if pattern == "triangle":
        return clamp_voltage(target * (1.0 - abs(2.0 * fraction - 1.0)))
    raise ValueError(f"unsupported pattern: {pattern}")


def generate_rows(
    pattern: str,
    channel: str,
    volts: float | None,
    seconds: float,
    rate_hz: float,
    calibration: Calibration | None = None,
) -> list[DacTestRow]:
    if pattern not in PATTERNS:
        raise ValueError(f"pattern must be one of: {', '.join(PATTERNS)}")

    normalized_channel = normalize_channel(channel)
    target_voltage = resolve_target_voltage(pattern, volts)
    timestamps = sample_timestamps(seconds, rate_hz)
    count = len(timestamps)
    active_calibration = calibration if calibration is not None else load_calibration()

    return [
        DacTestRow(
            timestamp_s=timestamp,
            channel=normalized_channel,
            dac_value=dac_value_from_voltage(
                pattern_voltage(pattern, target_voltage, index, count),
                normalized_channel,
                active_calibration,
            ),
        )
        for index, timestamp in enumerate(timestamps)
    ]


def print_header(stdout: TextIO) -> None:
    print("timestamp_s channel volts code", file=stdout)


def print_row(row: DacTestRow, stdout: TextIO) -> None:
    print(
        f"{row.timestamp_s:0.3f} "
        f"{row.channel} "
        f"{row.dac_value.voltage:0.6f} "
        f"{row.dac_value.code:05d}",
        file=stdout,
    )


def run_simulation(
    rows: list[DacTestRow],
    stdout: TextIO,
    calibration: Calibration | None = None,
) -> SimulationDAC:
    dac = SimulationDAC(calibration=calibration)
    print("Simulation mode: no GPIO, SPI, ADC, or DAC hardware will be opened.", file=stdout)
    print_header(stdout)
    for row in rows:
        write_channel(dac, row.channel, row.dac_value.voltage)
        print_row(row, stdout)
    return dac


def run_hardware(
    rows: list[DacTestRow],
    stdout: TextIO,
    calibration: Calibration | None = None,
) -> None:
    from .gpio_backend import GPIOBackend
    from .spi_devices import DAC8552

    gpio = GPIOBackend()
    dac = DAC8552(gpio, calibration=calibration)
    start = time.monotonic()

    try:
        print_header(stdout)
        for row in rows:
            delay = start + row.timestamp_s - time.monotonic()
            if delay > 0.0:
                time.sleep(delay)
            write_channel(dac, row.channel, row.dac_value.voltage)
            print_row(row, stdout)
    finally:
        dac.close()
        gpio.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely exercise one DAC channel with clamped test patterns.",
    )
    parser.add_argument(
        "--channel",
        choices=CHANNELS,
        required=True,
        help="DAC channel to test",
    )
    parser.add_argument(
        "--pattern",
        choices=PATTERNS,
        default="steady",
        help="test pattern to generate",
    )
    parser.add_argument(
        "--volts",
        type=float,
        default=None,
        help="target voltage; defaults to 1.65V for steady or 3.3V for patterns",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=10.0,
        help="pattern duration in seconds",
    )
    parser.add_argument(
        "--rate-hz",
        type=float,
        default=1.0,
        help="table/output update rate",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="run without hardware access; this is the default",
    )
    parser.add_argument(
        "--enable-output",
        action="store_true",
        help="allow real GPIO/SPI/DAC output",
    )
    parser.add_argument(
        "--calibration",
        default=None,
        help="path to calibration JSON; defaults to config/calibration.json",
    )
    return parser


def main(argv: list[str] | None = None, stdout: TextIO = sys.stdout) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.simulate and args.enable_output:
        parser.error("--simulate and --enable-output cannot be used together")

    try:
        calibration = load_calibration(args.calibration)
        rows = generate_rows(
            pattern=args.pattern,
            channel=args.channel,
            volts=args.volts,
            seconds=args.seconds,
            rate_hz=args.rate_hz,
            calibration=calibration,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.enable_output:
        run_hardware(rows, stdout, calibration=calibration)
    else:
        run_simulation(rows, stdout, calibration=calibration)


if __name__ == "__main__":
    main()
