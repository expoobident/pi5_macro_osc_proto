from __future__ import annotations

import time
import threading
import spidev

from . import config
from .gpio_backend import GPIOBackend

SPI_LOCK = threading.Lock()


class DAC8552:
    def __init__(self, gpio: GPIOBackend) -> None:
        self.gpio = gpio
        self.spi = spidev.SpiDev()
        self.spi.open(config.SPI_BUS, config.SPI_DEVICE_DAC)
        self.spi.max_speed_hz = config.DAC_SPI_HZ
        self.spi.mode = 0b01
        self.gpio.setup_output(config.PIN_DAC_CS, 1)

    @staticmethod
    def _float_to_u16(value: float) -> int:
        x = max(-1.0, min(1.0, value))
        unipolar = (x + 1.0) * 0.5
        return int(round(unipolar * 65535.0))

    def write_raw(self, channel_b: bool, value: int) -> None:
        tx = [
            (0x10 if channel_b else 0x00) | ((value >> 12) & 0x0F),
            (value >> 4) & 0xFF,
            ((value & 0x0F) << 4) & 0xFF,
        ]
        with SPI_LOCK:
            self.gpio.write(config.PIN_DAC_CS, 0)
            self.spi.xfer2(tx)
            self.gpio.write(config.PIN_DAC_CS, 1)

    def write_a(self, value: float) -> None:
        self.write_raw(False, self._float_to_u16(value))

    def write_b(self, value: float) -> None:
        self.write_raw(True, self._float_to_u16(value))

    def close(self) -> None:
        self.spi.close()


class ADS1256:
    CMD_WAKEUP = 0x00
    CMD_RDATA = 0x01
    CMD_SDATAC = 0x0F
    CMD_WREG = 0x50
    CMD_SELFCAL = 0xF0
    CMD_SYNC = 0xFC
    CMD_RESET = 0xFE

    REG_STATUS = 0x00
    REG_MUX = 0x01
    REG_ADCON = 0x02
    REG_DRATE = 0x03

    def __init__(self, gpio: GPIOBackend) -> None:
        self.gpio = gpio
        self.spi = spidev.SpiDev()
        self.spi.open(config.SPI_BUS, config.SPI_DEVICE_ADC)
        self.spi.max_speed_hz = config.ADC_SPI_HZ
        self.spi.mode = 0b01

        self.gpio.setup_output(config.PIN_ADC_CS, 1)
        self.gpio.setup_output(config.PIN_RESET, 1)
        self.gpio.setup_output(config.PIN_PDWN, 1)
        self.gpio.setup_input(config.PIN_DRDY)

    def _xfer(self, data: list[int]) -> list[int]:
        with SPI_LOCK:
            self.gpio.write(config.PIN_ADC_CS, 0)
            rx = self.spi.xfer2(data)
            self.gpio.write(config.PIN_ADC_CS, 1)
        return rx

    def reset(self) -> None:
        self.gpio.pulse_low(config.PIN_RESET, 0.002)
        time.sleep(0.01)
        self._xfer([self.CMD_RESET])
        time.sleep(0.01)

    def write_cmd(self, cmd: int) -> None:
        self._xfer([cmd])

    def write_reg(self, reg: int, value: int) -> None:
        self._xfer([self.CMD_WREG | reg, 0x00, value & 0xFF])
        time.sleep(0.001)

    def wait_drdy(self, timeout_s: float = 0.2) -> None:
        t0 = time.monotonic()
        while self.gpio.read(config.PIN_DRDY) != 0:
            if time.monotonic() - t0 > timeout_s:
                raise TimeoutError("ADS1256 DRDY timeout")
            time.sleep(0.00005)

    def init(self) -> None:
        self.reset()
        self.write_cmd(self.CMD_SDATAC)
        time.sleep(0.001)
        self.write_reg(self.REG_STATUS, 0x00)
        self.write_reg(self.REG_ADCON, 0x00)
        self.write_reg(self.REG_DRATE, 0xF0)
        self.write_cmd(self.CMD_SELFCAL)
        time.sleep(0.05)

    def set_channel(self, ch: int) -> None:
        ch &= 0x07
        mux = (ch << 4) | 0x08
        self.write_reg(self.REG_MUX, mux)
        self.write_cmd(self.CMD_SYNC)
        time.sleep(0.00001)
        self.write_cmd(self.CMD_WAKEUP)
        time.sleep(0.00001)

    def read_data24(self) -> int:
        rx = self._xfer([self.CMD_RDATA, 0xFF, 0xFF, 0xFF])
        value = (rx[1] << 16) | (rx[2] << 8) | rx[3]
        if value & 0x800000:
            value -= 1 << 24
        return value

    def read_channel_raw(self, ch: int) -> int:
        self.wait_drdy()
        self.set_channel(ch)
        self.wait_drdy()
        return self.read_data24()

    def read_channel_norm01(self, ch: int) -> float:
        raw = self.read_channel_raw(ch)
        minv = -8388608.0
        maxv = 8388607.0
        n = (raw - minv) / (maxv - minv)
        return max(0.0, min(1.0, n))

    def close(self) -> None:
        self.spi.close()
