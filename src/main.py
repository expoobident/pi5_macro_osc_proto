from __future__ import annotations

import threading
import time

from . import config
from .controls import Controls
from .gpio_backend import GPIOBackend
from .oscillator import Oscillator
from .spi_devices import ADS1256, DAC8552


class SharedState:
    def __init__(self) -> None:
        self.pitch_hz = 1.0
        self.timbre = 0.0
        self.morph = 0.0
        self.index = 0.0
        self.running = True
        self.lock = threading.Lock()


def audio_loop(dac: DAC8552, state: SharedState) -> None:
    osc = Oscillator(config.AUDIO_HZ)
    period = 1.0 / config.AUDIO_HZ
    next_t = time.perf_counter()

    while state.running:
        with state.lock:
            pitch_hz = state.pitch_hz
            timbre = state.timbre
            morph = state.morph
            index = state.index

        osc.set_params(pitch_hz, timbre, morph, index)
        main, aux = osc.render()

        dac.write_a(main)
        dac.write_b(aux)

        next_t += period
        delay = next_t - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        else:
            next_t = time.perf_counter()


def control_loop(controls: Controls, state: SharedState) -> None:
    period = 1.0 / config.CONTROL_HZ
    next_t = time.perf_counter()
    last_print = 0.0

    while state.running:
        try:
            values = controls.update()

            with state.lock:
                state.pitch_hz = values.pitch_hz
                state.timbre = values.timbre
                state.morph = values.morph
                state.index = values.index

            now = time.monotonic()
            if now - last_print >= 1.0:
                print(
                    f"pitch={values.pitch_hz:6.2f} Hz  "
                    f"timbre={values.timbre:0.3f}  "
                    f"morph={values.morph:0.3f}  "
                    f"index={values.index:0.3f}"
                )
                last_print = now

        except Exception as e:
            print(f"control_loop warning: {e}")
            time.sleep(0.02)

        next_t += period
        delay = next_t - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        else:
            next_t = time.perf_counter()


def main() -> None:
    gpio = GPIOBackend()
    adc = ADS1256(gpio)
    dac = DAC8552(gpio)
    adc.init()

    controls = Controls(adc)
    state = SharedState()

    t_audio = threading.Thread(target=audio_loop, args=(dac, state), daemon=True)
    t_ctrl = threading.Thread(target=control_loop, args=(controls, state), daemon=True)

    t_audio.start()
    t_ctrl.start()

    print("Pi 5 macro oscillator prototype running.")
    print("AD4=pitch  AD1=timbre  AD2=morph  AD3=index")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping...")
        state.running = False
        t_audio.join(timeout=1.0)
        t_ctrl.join(timeout=1.0)
        adc.close()
        dac.close()
        gpio.close()


if __name__ == "__main__":
    main()
