from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .calibration import Calibration, load_calibration, normalize_adc_value
from . import config

if TYPE_CHECKING:
    from .spi_devices import ADS1256


@dataclass
class ControlState:
    pitch_hz: float = 1.0
    timbre: float = 0.0
    morph: float = 0.0
    index: float = 0.0


class Controls:
    def __init__(self, adc: ADS1256, calibration: Calibration | None = None) -> None:
        self.adc = adc
        self.calibration = calibration if calibration is not None else load_calibration()
        self._pitch = 0.5
        self._timbre = 0.0
        self._morph = 0.0
        self._index = 0.0

    @staticmethod
    def _smooth(prev: float, nxt: float, amt: float = 0.12) -> float:
        return prev + (nxt - prev) * amt

    def update(self) -> ControlState:
        pitch_n = normalize_adc_value(
            self.adc.read_channel_norm01(config.ADC_CH_PITCH),
            "AD4",
            self.calibration,
        )
        timbre_n = normalize_adc_value(
            self.adc.read_channel_norm01(config.ADC_CH_TIMBRE),
            "AD1",
            self.calibration,
        )
        morph_n = normalize_adc_value(
            self.adc.read_channel_norm01(config.ADC_CH_MORPH),
            "AD2",
            self.calibration,
        )
        index_n = normalize_adc_value(
            self.adc.read_channel_norm01(config.ADC_CH_INDEX),
            "AD3",
            self.calibration,
        )

        self._pitch = self._smooth(self._pitch, pitch_n)
        self._timbre = self._smooth(self._timbre, timbre_n)
        self._morph = self._smooth(self._morph, morph_n)
        self._index = self._smooth(self._index, index_n)

        # 1 Hz to 8 Hz, easy to see on the Pokit
        octaves = self._pitch * 3.0
        pitch_hz = 1.0 * (2.0 ** octaves)

        return ControlState(
            pitch_hz=pitch_hz,
            timbre=max(0.0, min(1.0, self._timbre)),
            morph=max(0.0, min(1.0, self._morph)),
            index=max(0.0, min(1.0, self._index)),
        )
