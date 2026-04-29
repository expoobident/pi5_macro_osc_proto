from __future__ import annotations

import argparse
import threading
import time
from typing import Any

from . import config
from .dac_output import SimulationDAC
from .oscillator import Oscillator


class SharedState:
    def __init__(self) -> None:
        self.pitch_hz = 1.0
        self.timbre = 0.0
        self.morph = 0.0
        self.index = 0.0
        self.running = True
        self.lock = threading.Lock()


def audio_loop(dac: Any, state: SharedState) -> None:
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


def control_loop(controls: Any, state: SharedState) -> None:
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


def run_simulation(
    samples: int,
    pitch_hz: float,
    timbre: float,
    morph: float,
    index: float,
) -> None:
    osc = Oscillator(config.AUDIO_HZ)
    dac = SimulationDAC()

    print("Simulation mode: no GPIO, SPI, ADC, or DAC hardware will be opened.")
    print("sample DAC0_volts DAC0_code DAC1_volts DAC1_code")

    for sample in range(samples):
        osc.set_params(pitch_hz, timbre, morph, index)
        main, aux = osc.render()
        dac0 = dac.write_a(main)
        dac1 = dac.write_b(aux)
        print(
            f"{sample:06d} "
            f"{dac0.voltage:0.6f} {dac0.code:05d} "
            f"{dac1.voltage:0.6f} {dac1.code:05d}"
        )


def run_hardware() -> None:
    from .controls import Controls
    from .gpio_backend import GPIOBackend
    from .spi_devices import ADS1256, DAC8552

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pi 5 macro oscillator prototype",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="run without touching GPIO/SPI hardware and print DAC0/DAC1 values",
    )
    parser.add_argument(
        "--enable-output",
        action="store_true",
        help="allow real GPIO/SPI/ADC/DAC hardware output",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=32,
        help="number of generated samples to print in simulation mode",
    )
    parser.add_argument("--pitch-hz", type=float, default=1.0)
    parser.add_argument("--timbre", type=float, default=0.0)
    parser.add_argument("--morph", type=float, default=0.0)
    parser.add_argument("--index", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.samples < 1:
        parser.error("--samples must be at least 1")

    if args.simulate:
        run_simulation(
            samples=args.samples,
            pitch_hz=args.pitch_hz,
            timbre=args.timbre,
            morph=args.morph,
            index=args.index,
        )
        return

    if not args.enable_output:
        parser.error(
            "real hardware output is disabled by default; use --simulate for "
            "software-only output or --enable-output to allow GPIO/SPI/DAC access"
        )

    run_hardware()


if __name__ == "__main__":
    main()
