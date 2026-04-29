from __future__ import annotations

from dataclasses import dataclass
import math

DAC_MIN_VOLTAGE = 0.0
DAC_MAX_VOLTAGE = 3.3
DAC_MAX_CODE = 0xFFFF


@dataclass(frozen=True)
class DacValue:
    bipolar: float
    voltage: float
    code: int


def clamp_voltage(voltage: float) -> float:
    if not math.isfinite(voltage):
        return DAC_MIN_VOLTAGE
    return max(DAC_MIN_VOLTAGE, min(DAC_MAX_VOLTAGE, voltage))


def clamp_bipolar(value: float) -> float:
    if not math.isfinite(value):
        return -1.0
    return max(-1.0, min(1.0, value))


def bipolar_to_voltage(value: float) -> float:
    bipolar = clamp_bipolar(value)
    return clamp_voltage((bipolar + 1.0) * 0.5 * DAC_MAX_VOLTAGE)


def voltage_to_u16(voltage: float) -> int:
    clamped = clamp_voltage(voltage)
    return int(round((clamped / DAC_MAX_VOLTAGE) * DAC_MAX_CODE))


def voltage_to_bipolar(voltage: float) -> float:
    clamped = clamp_voltage(voltage)
    return (clamped / DAC_MAX_VOLTAGE) * 2.0 - 1.0


def clamp_u16(value: int) -> int:
    return max(0, min(DAC_MAX_CODE, int(value)))


def bipolar_to_u16(value: float) -> int:
    return voltage_to_u16(bipolar_to_voltage(value))


def dac_value_from_bipolar(value: float) -> DacValue:
    bipolar = clamp_bipolar(value)
    voltage = bipolar_to_voltage(bipolar)
    return DacValue(
        bipolar=bipolar,
        voltage=voltage,
        code=voltage_to_u16(voltage),
    )


def dac_value_from_voltage(voltage: float) -> DacValue:
    clamped = clamp_voltage(voltage)
    return DacValue(
        bipolar=voltage_to_bipolar(clamped),
        voltage=clamped,
        code=voltage_to_u16(clamped),
    )


class SimulationDAC:
    def __init__(self) -> None:
        self.writes: list[tuple[str, DacValue]] = []

    def write_a(self, value: float) -> DacValue:
        dac_value = dac_value_from_bipolar(value)
        self.writes.append(("DAC0", dac_value))
        return dac_value

    def write_b(self, value: float) -> DacValue:
        dac_value = dac_value_from_bipolar(value)
        self.writes.append(("DAC1", dac_value))
        return dac_value

    def write_voltage_a(self, voltage: float) -> DacValue:
        dac_value = dac_value_from_voltage(voltage)
        self.writes.append(("DAC0", dac_value))
        return dac_value

    def write_voltage_b(self, voltage: float) -> DacValue:
        dac_value = dac_value_from_voltage(voltage)
        self.writes.append(("DAC1", dac_value))
        return dac_value
