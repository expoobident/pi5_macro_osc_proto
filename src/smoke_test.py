from __future__ import annotations

import argparse
import sys
from typing import TextIO

from .calibration import default_calibration
from .dac_output import SimulationDAC, dac_value_from_voltage
from .dac_test import generate_rows, write_channel
from .oscillator import Oscillator

HARDWARE_MODULES = (
    "spidev",
    "gpiod",
    "src.spi_devices",
    "src.gpio_backend",
)


def hardware_modules_loaded() -> list[str]:
    return [module for module in HARDWARE_MODULES if module in sys.modules]


def run_simulation_smoke(stdout: TextIO) -> bool:
    loaded_before = set(hardware_modules_loaded())
    failures: list[str] = []

    osc = Oscillator(sample_rate=100.0)
    osc.set_params(pitch_hz=2.0, timbre=0.25, morph=0.5, index=0.5)
    main, aux = osc.render()
    if not (-1.0 <= main <= 1.0 and -1.0 <= aux <= 1.0):
        failures.append("waveform generation produced out-of-range values")

    low = dac_value_from_voltage(-1.0)
    high = dac_value_from_voltage(4.0)
    if low.voltage != 0.0 or high.voltage != 3.3:
        failures.append("DAC voltage clamping failed")

    dac = SimulationDAC(calibration=default_calibration())
    write_channel(dac, "DAC0", 1.0)
    write_channel(dac, "DAC1", 2.0)
    if [channel for channel, _ in dac.writes] != ["DAC0", "DAC1"]:
        failures.append("DAC0/DAC1 channel mapping failed")

    rows0 = generate_rows("steady", "DAC0", 1.65, 0.0, 1.0, default_calibration())
    rows1 = generate_rows("steady", "DAC1", 1.65, 0.0, 1.0, default_calibration())
    if not rows0 or not rows1:
        failures.append("simulation mode did not produce both DAC values")

    loaded_after = set(hardware_modules_loaded())
    newly_loaded = sorted(loaded_after - loaded_before)
    if newly_loaded:
        failures.append(f"simulation imported hardware modules: {', '.join(newly_loaded)}")

    if failures:
        print("Smoke test failed:", file=stdout)
        for failure in failures:
            print(f"- {failure}", file=stdout)
        return False

    print("Smoke test passed:", file=stdout)
    print("- waveform generation works", file=stdout)
    print("- DAC voltage clamping works", file=stdout)
    print("- DAC0/DAC1 channel mapping exists", file=stdout)
    print("- simulation mode can produce values for both DACs", file=stdout)
    print("- no hardware modules were imported in simulation mode", file=stdout)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run safe software smoke tests.")
    parser.add_argument(
        "--simulate",
        action="store_true",
        required=True,
        help="required; smoke tests never access hardware",
    )
    return parser


def main(argv: list[str] | None = None, stdout: TextIO = sys.stdout) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0 if run_simulation_smoke(stdout) else 1


if __name__ == "__main__":
    raise SystemExit(main())
