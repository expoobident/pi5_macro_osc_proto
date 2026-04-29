from __future__ import annotations

import time

try:
    import gpiod
    from gpiod.line import Direction, Value
except ImportError as exc:
    raise RuntimeError(
        "python3-libgpiod is required. Install with: sudo apt install python3-libgpiod"
    ) from exc


class GPIOBackend:
    def __init__(self, chip_name: str = "/dev/gpiochip0") -> None:
        self.chip_name = chip_name
        self._reqs = {}

    def setup_output(self, pin: int, initial: int = 0) -> None:
        req = gpiod.request_lines(
            self.chip_name,
            consumer="pi5_macro_osc",
            config={
                pin: gpiod.LineSettings(
                    direction=Direction.OUTPUT,
                    output_value=Value.ACTIVE if initial else Value.INACTIVE,
                )
            },
        )
        self._reqs[pin] = req

    def setup_input(self, pin: int) -> None:
        req = gpiod.request_lines(
            self.chip_name,
            consumer="pi5_macro_osc",
            config={
                pin: gpiod.LineSettings(direction=Direction.INPUT)
            },
        )
        self._reqs[pin] = req

    def write(self, pin: int, value: int) -> None:
        self._reqs[pin].set_value(pin, Value.ACTIVE if value else Value.INACTIVE)

    def read(self, pin: int) -> int:
        return 1 if self._reqs[pin].get_value(pin) == Value.ACTIVE else 0

    def pulse_low(self, pin: int, delay_s: float = 0.001) -> None:
        self.write(pin, 0)
        time.sleep(delay_s)
        self.write(pin, 1)

    def close(self) -> None:
        for req in self._reqs.values():
            try:
                req.release()
            except Exception:
                pass
        self._reqs.clear()
