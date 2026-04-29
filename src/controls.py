from __future__ import annotations

from dataclasses import dataclass

from . import config
from .spi_devices import ADS1256


@dataclass
class ControlState:
    pitch_hz: float = 1.0
    timbre: float = 0.0
    morph: float = 0.0
    index: float = 0.0


class Controls:
    def __init__(self, adc: ADS1256) -> None:
        self.adc = adc
        self._pitch = 0.5
        self._timbre = 0.0
        self._morph = 0.0
        self._index = 0.0

    @staticmethod
    def _smooth(prev: float, nxt: float, amt: float = 0.12) -> float:
        return prev + (nxt - prev) * amt

    def update(self) -> ControlState:
        pitch_n = self.adc.read_channel_norm01(config.ADC_CH_PITCH)
        timbre_n = self.adc.read_channel_norm01(config.ADC_CH_TIMBRE)
        morph_n = self.adc.read_channel_norm01(config.ADC_CH_MORPH)
        index_n = self.adc.read_channel_norm01(config.ADC_CH_INDEX)

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
