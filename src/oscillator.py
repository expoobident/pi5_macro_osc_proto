from __future__ import annotations

import math


class Oscillator:
    def __init__(self, sample_rate: float) -> None:
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.freq = 1.0
        self.timbre = 0.0
        self.morph = 0.0
        self.index = 0.0

    def set_params(self, pitch_hz: float, timbre: float, morph: float, index: float) -> None:
        self.freq = max(0.01, pitch_hz)
        self.timbre = max(0.0, min(1.0, timbre))
        self.morph = max(0.0, min(1.0, morph))
        self.index = max(0.0, min(1.0, index))

    @staticmethod
    def _tri(phase: float) -> float:
        x = 2.0 * phase - 1.0
        return 2.0 * (abs(x) - 0.5)

    def render(self) -> tuple[float, float]:
        inc = self.freq / self.sample_rate
        self.phase += inc
        while self.phase >= 1.0:
            self.phase -= 1.0

        saw = 2.0 * self.phase - 1.0
        tri = self._tri(self.phase)
        square = 1.0 if self.phase < 0.5 else -1.0

        # Main: triangle -> saw morph
        main = tri * (1.0 - self.morph) + saw * self.morph

        # Timbre: gentle saturation only
        drive = 1.0 + self.timbre * 2.0
        main = math.tanh(main * drive)

        # Aux: triangle -> square blend
        aux = tri * (1.0 - self.index) + square * self.index

        return max(-1.0, min(1.0, main)), max(-1.0, min(1.0, aux))
