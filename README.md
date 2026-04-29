# Pi 5 Macro Oscillator Prototype

Prototype firmware for a Raspberry Pi 5 with the Waveshare High-Precision AD/DA Board.

This version is for bench prototyping on the Pi 5:
- reads pots/CV from the ADS1256 ADC
- writes oscillator values to the DAC8552 DAC
- uses SPI plus GPIO control pins matching the Waveshare HAT pinout
- keeps the oscillator/control architecture portable so the DSP core can later move to the Raspberry Pi Pico

## Waveshare board facts this project assumes
The Waveshare board exposes:
- ADS1256, 8-channel 24-bit ADC
- DAC8552, 2-channel 16-bit DAC
- SPI pins on DIN/DOUT/SCK
- control pins:
  - DRDY = BCM 17
  - RESET = BCM 18
  - PDWN = BCM 27
  - ADC CS = BCM 22
  - DAC CS = BCM 23

## Install on Raspberry Pi 5
Enable SPI first:
```bash
sudo raspi-config
# Interface Options -> SPI -> Enable
sudo reboot
```

Install Python dependencies:
```bash
sudo apt update
sudo apt install -y python3-spidev python3-libgpiod
```

## Run
Simulation is the safe default for development because it does not open GPIO,
SPI, ADC, or DAC hardware:

```bash
python3 -m src.main --simulate --samples 20
```

Real output is disabled unless you explicitly opt in:

```bash
python3 -m src.main --enable-output
```

Running without either option exits before importing the hardware backends.

## DAC test utility
Start with simulation. It prints timestamp, channel, clamped volts, and DAC code
without opening GPIO or SPI:

```bash
python3 -m src.dac_test --channel DAC0 --volts 1.65 --seconds 0
python3 -m src.dac_test --channel DAC1 --pattern ramp --seconds 10
python3 -m src.dac_test --channel DAC1 --pattern triangle --seconds 10
```

Real DAC output requires the explicit hardware opt-in:

```bash
python3 -m src.dac_test --channel DAC0 --volts 1.65 --seconds 0 --enable-output
python3 -m src.dac_test --channel DAC1 --pattern ramp --seconds 10 --enable-output
```

All DAC test values are clamped to 0.0-3.3V before becoming DAC codes.

## Smoke tests
Run the software-only smoke test before bench work:

```bash
python3 -m src.smoke_test --simulate
```

The smoke test checks waveform generation, DAC clamping, DAC0/DAC1 simulation
mapping, and that simulation mode does not import the hardware backends.

## Calibration
Default calibration lives in:

```text
config/calibration.json
```

The DAC path applies calibration before converting volts to a DAC code:

```text
calibrated_volts = volts * gain + offset
```

Print safe Pokit Pro calibration steps:

```bash
python3 -m src.calibrate
```

This command only prints instructions. Real output still requires using the DAC
test utility with `--enable-output`, and only while watching the meter or scope.
Measured full-scale may be around 3.28V instead of exactly 3.30V.

## Pokit Pro bench notes
- Pokit black/COM to GND.
- Pokit red/V to DAC0 or DAC1.
- Expected DAC range is 0-3.3V.
- Start in simulation mode first.
- Only use `--enable-output` while watching the meter or scope.
- Use DC coupling and a slow timebase for slow LFO-style signals.

## Notes
- This is a userspace Linux prototype. It is good for proving control flow and rough output behavior.
- Final real-time audio behavior should be moved to the Pico.
- The ADC normalization assumes your prototype pots are wired into a safe, board-compatible range.
- DAC voltage conversion clamps every output to 0.0-3.3V before it becomes a DAC code.
