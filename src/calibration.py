from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

DEFAULT_CALIBRATION_PATH = Path(__file__).resolve().parent.parent / "config" / "calibration.json"
ADC_CHANNELS = ("AD1", "AD2", "AD3", "AD4")


@dataclass(frozen=True)
class DacCalibration:
    gain: float = 1.0
    offset_volts: float = 0.0


@dataclass(frozen=True)
class AdcCalibration:
    minimum: float = 0.0
    maximum: float = 1.0


@dataclass(frozen=True)
class Calibration:
    dac0: DacCalibration
    dac1: DacCalibration
    adc: dict[str, AdcCalibration]


def default_calibration() -> Calibration:
    return Calibration(
        dac0=DacCalibration(),
        dac1=DacCalibration(),
        adc={channel: AdcCalibration() for channel in ADC_CHANNELS},
    )


def _float_from_mapping(
    data: dict[str, Any],
    key: str,
    fallback: float,
) -> float:
    try:
        return float(data.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def calibration_from_mapping(data: dict[str, Any]) -> Calibration:
    defaults = default_calibration()
    adc_data = data.get("adc", {})
    if not isinstance(adc_data, dict):
        adc_data = {}

    adc: dict[str, AdcCalibration] = {}
    for channel, channel_default in defaults.adc.items():
        channel_data = adc_data.get(channel, {})
        if not isinstance(channel_data, dict):
            channel_data = {}
        adc[channel] = AdcCalibration(
            minimum=_float_from_mapping(channel_data, "min", channel_default.minimum),
            maximum=_float_from_mapping(channel_data, "max", channel_default.maximum),
        )

    return Calibration(
        dac0=DacCalibration(
            gain=_float_from_mapping(data, "dac0_gain", defaults.dac0.gain),
            offset_volts=_float_from_mapping(
                data,
                "dac0_offset_volts",
                defaults.dac0.offset_volts,
            ),
        ),
        dac1=DacCalibration(
            gain=_float_from_mapping(data, "dac1_gain", defaults.dac1.gain),
            offset_volts=_float_from_mapping(
                data,
                "dac1_offset_volts",
                defaults.dac1.offset_volts,
            ),
        ),
        adc=adc,
    )


def load_calibration(path: str | Path | None = None) -> Calibration:
    config_path = Path(path) if path is not None else DEFAULT_CALIBRATION_PATH

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default_calibration()

    if not isinstance(data, dict):
        return default_calibration()

    return calibration_from_mapping(data)


def dac_calibration_for_channel(
    calibration: Calibration,
    channel: str,
) -> DacCalibration:
    normalized = channel.upper()
    if normalized == "DAC0":
        return calibration.dac0
    if normalized == "DAC1":
        return calibration.dac1
    raise ValueError("channel must be DAC0 or DAC1")


def apply_dac_calibration(
    volts: float,
    channel: str,
    calibration: Calibration,
) -> float:
    dac_calibration = dac_calibration_for_channel(calibration, channel)
    return volts * dac_calibration.gain + dac_calibration.offset_volts
