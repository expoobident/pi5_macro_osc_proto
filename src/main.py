from __future__ import annotations

import argparse
import sys
import threading
import time
from typing import TextIO, TYPE_CHECKING

from . import config
from .controls import Controls
from .dac_output import SimulationDAC
from .oscillator import Oscillator

if TYPE_CHECKING:
    from .gpio_backend import GPIOBackend
    from .spi_devices import DAC8552


class SharedState:
    def __init__(self) -> None:
        self.pitch_hz = 1.0
        self.timbre = 0.0
        self.morph = 0.0
        self.index = 0.0
        self.running = True
        self.lock = threading.Lock()


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def other_target(current: str) -> str:
    return "morph" if current == "index" else "index"


def audio_loop(dac: DAC8552, state: SharedState, gpio: GPIOBackend) -> None:
    osc = Oscillator(config.AUDIO_HZ)
    period = 1.0 / config.AUDIO_HZ
    next_t = time.perf_counter()

    trig_a_armed = True
    trig_b_armed = True
    trig_c_armed = True
    trig_b_press_time = None

    last_trig_a_time = 0.0
    last_trig_b_time = 0.0
    last_trig_c_time = 0.0

    debounce_s = getattr(config, "TRIG_DEBOUNCE_MS", 50) / 1000.0
    long_press_s = getattr(config, "TRIG_B_LONG_PRESS_MS", 600) / 1000.0

    func_a = 0.0
    func_a_cycle_enabled = False
    func_a_phase = 0.0

    decay_per_sample = 0.0025
    cycle_rate_hz = 0.75
    func_a_target = getattr(config, "FUNC_A_TARGET", "index")

    # Function B: always-on slow triangle LFO
    func_b_phase = 0.0
    func_b = 0.0
    func_b_rate_hz = getattr(config, "FUNC_B_RATE_HZ", 0.2)
    func_b_amount = getattr(config, "FUNC_B_AMOUNT", 0.20)

    while state.running:
        with state.lock:
            pitch_hz = state.pitch_hz
            timbre = state.timbre
            morph = state.morph
            index = state.index

        now = time.monotonic()

        # Trig A = oscillator reset
        trig_a = gpio.read(config.PIN_TRIG_A)
        if not trig_a:
            trig_a_armed = True
        elif trig_a and trig_a_armed and (now - last_trig_a_time) >= debounce_s:
            osc.reset()
            trig_a_armed = False
            last_trig_a_time = now
            print("Trig A: reset")

        # Trig B = Function A action
        trig_b = gpio.read(config.PIN_TRIG_B)

        if trig_b and trig_b_armed and trig_b_press_time is None:
            trig_b_press_time = now

        if not trig_b and trig_b_press_time is not None:
            held = now - trig_b_press_time
            trig_b_press_time = None
            trig_b_armed = True

            if (now - last_trig_b_time) >= debounce_s:
                last_trig_b_time = now

                if held >= long_press_s:
                    func_a_target = other_target(func_a_target)
                    print(f"Trig B: Function A target -> {func_a_target}")
                else:
                    if config.FUNC_A_MODE == "decay":
                        func_a = 1.0
                        print(f"Trig B: Function A trigger -> {func_a_target} ({config.FUNC_A_MODE})")
                    elif config.FUNC_A_MODE == "cycle":
                        func_a_cycle_enabled = not func_a_cycle_enabled
                        state_txt = "ON" if func_a_cycle_enabled else "OFF"
                        print(f"Trig B: Function A cycle {state_txt} -> {func_a_target}")

        elif trig_b and trig_b_armed:
            trig_b_armed = False

        # Trig C = Function B reset/sync
        trig_c = gpio.read(config.PIN_TRIG_C)
        if not trig_c:
            trig_c_armed = True
        elif trig_c and trig_c_armed and (now - last_trig_c_time) >= debounce_s:
            func_b_phase = 0.0
            trig_c_armed = False
            last_trig_c_time = now
            print("Trig C: Function B reset")

        # Function A
        if config.FUNC_A_MODE == "decay":
            if func_a > 0.0:
                func_a = max(0.0, func_a - decay_per_sample)

        elif config.FUNC_A_MODE == "cycle":
            if func_a_cycle_enabled:
                func_a_phase += cycle_rate_hz / config.AUDIO_HZ
                while func_a_phase >= 1.0:
                    func_a_phase -= 1.0

                if func_a_phase < 0.5:
                    func_a = func_a_phase * 2.0
                else:
                    func_a = 2.0 - func_a_phase * 2.0
            else:
                func_a = 0.0

        # Function B
        func_b_phase += func_b_rate_hz / config.AUDIO_HZ
        while func_b_phase >= 1.0:
            func_b_phase -= 1.0

        if func_b_phase < 0.5:
            func_b = func_b_phase * 2.0
        else:
            func_b = 2.0 - func_b_phase * 2.0

        mod_morph = morph
        mod_index = index

        func_a_amount = getattr(config, "FUNC_A_AMOUNT", 0.35)
        func_b_target = other_target(func_a_target)

        if func_a_target == "morph":
            mod_morph = clamp01(mod_morph + func_a_amount * func_a)
        elif func_a_target == "index":
            mod_index = clamp01(mod_index + func_a_amount * func_a)

        if func_b_target == "morph":
            mod_morph = clamp01(mod_morph + func_b_amount * func_b)
        elif func_b_target == "index":
            mod_index = clamp01(mod_index + func_b_amount * func_b)

        osc.set_params(pitch_hz, timbre, mod_morph, mod_index)
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
                    f"index={values.index:0.3f}  "
                    f"funcA={config.FUNC_A_MODE}"
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
    stdout: TextIO = sys.stdout,
) -> None:
    osc = Oscillator(config.AUDIO_HZ)
    dac = SimulationDAC()

    print("Simulation mode: no GPIO, SPI, ADC, or DAC hardware will be opened.", file=stdout)
    print("sample DAC0_volts DAC0_code DAC1_volts DAC1_code", file=stdout)

    for sample in range(samples):
        osc.set_params(pitch_hz, timbre, morph, index)
        main, aux = osc.render()
        dac0 = dac.write_a(main)
        dac1 = dac.write_b(aux)
        print(
            f"{sample:06d} "
            f"{dac0.voltage:0.6f} {dac0.code:05d} "
            f"{dac1.voltage:0.6f} {dac1.code:05d}",
            file=stdout,
        )


def run_hardware() -> None:
    from .gpio_backend import GPIOBackend
    from .spi_devices import ADS1256, DAC8552

    gpio = GPIOBackend()
    gpio.setup_input(config.PIN_TRIG_A)
    gpio.setup_input(config.PIN_TRIG_B)
    gpio.setup_input(config.PIN_TRIG_C)

    adc = ADS1256(gpio)
    dac = DAC8552(gpio)
    adc.init()

    controls = Controls(adc)
    state = SharedState()

    t_audio = threading.Thread(target=audio_loop, args=(dac, state, gpio), daemon=True)
    t_ctrl = threading.Thread(target=control_loop, args=(controls, state), daemon=True)

    t_audio.start()
    t_ctrl.start()

    print("Pi 5 macro oscillator prototype running.")
    print("AD4=pitch  AD1=timbre  AD2=morph  AD3=index")
    print(f"Trig A on BCM {config.PIN_TRIG_A} = oscillator reset")
    print(f"Trig B on BCM {config.PIN_TRIG_B} = Function A action")
    print(f"Trig C on BCM {config.PIN_TRIG_C} = Function B reset")
    print(f"Function A mode: {config.FUNC_A_MODE}")
    print(f"Function A default target: {config.FUNC_A_TARGET}")
    print(f"Trigger debounce: {config.TRIG_DEBOUNCE_MS} ms")
    print(f"Trig B long press: {config.TRIG_B_LONG_PRESS_MS} ms")
    print(f"Function A amount: {config.FUNC_A_AMOUNT}")
    print(f"Function B rate: {config.FUNC_B_RATE_HZ} Hz")
    print(f"Function B amount: {config.FUNC_B_AMOUNT}")
    print("Short press Trig B = trigger/toggle Function A")
    print("Long press Trig B = switch Function A target")
    print("Trig C = reset/sync Function B")
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


def main(argv: list[str] | None = None, stdout: TextIO = sys.stdout) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.simulate and args.enable_output:
        parser.error("--simulate and --enable-output cannot be used together")
    if args.samples < 1:
        parser.error("--samples must be at least 1")

    if args.simulate:
        run_simulation(
            samples=args.samples,
            pitch_hz=args.pitch_hz,
            timbre=args.timbre,
            morph=args.morph,
            index=args.index,
            stdout=stdout,
        )
        return

    if not args.enable_output:
        parser.error(
            "real hardware output is disabled by default; use --simulate for "
            "software-only output or --enable-output while present to allow "
            "GPIO/SPI/ADC/DAC access"
        )

    run_hardware()


if __name__ == "__main__":
    main()
