from __future__ import annotations

from dataclasses import dataclass

from .calibration import Calibration, normalize_adc_value


@dataclass(frozen=True)
class ControlChannel:
    adc_name: str
    control_name: str
    hardware_channel: int
    mapped_unit: str


@dataclass(frozen=True)
class ControlReading:
    sample: int
    adc_name: str
    control_name: str
    raw_value: float
    normalized: float
    mapped_value: float
    mapped_unit: str


CONTROL_CHANNELS = (
    ControlChannel("AD4", "pitch", 4, "Hz"),
    ControlChannel("AD1", "timbre", 1, "norm"),
    ControlChannel("AD2", "morph", 2, "norm"),
    ControlChannel("AD3", "index", 3, "norm"),
)


def pitch_hz_from_normalized(normalized: float) -> float:
    clamped = max(0.0, min(1.0, normalized))
    return 1.0 * (2.0 ** (clamped * 3.0))


def mapped_value_for_control(control_name: str, normalized: float) -> float:
    if control_name == "pitch":
        return pitch_hz_from_normalized(normalized)
    return max(0.0, min(1.0, normalized))


def reading_from_raw(
    sample: int,
    channel: ControlChannel,
    raw_value: float,
    calibration: Calibration,
) -> ControlReading:
    normalized = normalize_adc_value(raw_value, channel.adc_name, calibration)
    return ControlReading(
        sample=sample,
        adc_name=channel.adc_name,
        control_name=channel.control_name,
        raw_value=raw_value,
        normalized=normalized,
        mapped_value=mapped_value_for_control(channel.control_name, normalized),
        mapped_unit=channel.mapped_unit,
    )
