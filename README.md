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

## Pokit Pro bench notes
- Pokit black/COM goes to board GND.
- Pokit red/V goes to DAC0 or DAC1.
- Expected DAC range is 0-3.3V.
- Use DC coupling and a slow timebase for slow LFO-style signals.

## Notes
- This is a userspace Linux prototype. It is good for proving control flow and rough output behavior.
- Final real-time audio behavior should be moved to the Pico.
- The ADC normalization assumes your prototype pots are wired into a safe, board-compatible range.
- DAC voltage conversion clamps every output to 0.0-3.3V before it becomes a DAC code.
