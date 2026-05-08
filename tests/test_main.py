from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import unittest

from src import main


class MainSafetyGateTests(unittest.TestCase):
    def test_simulation_mode_prints_samples_without_hardware_imports(self) -> None:
        stdout = StringIO()

        main.main(["--simulate", "--samples", "2"], stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("Simulation mode", output)
        self.assertIn("sample DAC0_volts DAC0_code DAC1_volts DAC1_code", output)
        self.assertIn("000000", output)
        self.assertNotIn("src.spi_devices", main.sys.modules)
        self.assertNotIn("src.gpio_backend", main.sys.modules)
        self.assertNotIn("spidev", main.sys.modules)
        self.assertNotIn("gpiod", main.sys.modules)

    def test_refuses_without_simulate_or_enable_output(self) -> None:
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as context:
                main.main([], stdout=stdout)

        self.assertEqual(context.exception.code, 2)
        self.assertIn("real hardware output is disabled", stderr.getvalue())
        self.assertNotIn("src.spi_devices", main.sys.modules)
        self.assertNotIn("src.gpio_backend", main.sys.modules)


if __name__ == "__main__":
    unittest.main()
