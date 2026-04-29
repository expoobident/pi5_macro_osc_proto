from __future__ import annotations

from io import StringIO
import unittest

from src import smoke_test


class SmokeTestSimulationTests(unittest.TestCase):
    def test_smoke_test_simulation_behavior(self) -> None:
        stdout = StringIO()

        exit_code = smoke_test.main(["--simulate"], stdout=stdout)

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Smoke test passed", output)
        self.assertIn("waveform generation works", output)
        self.assertIn("DAC voltage clamping works", output)
        self.assertIn("DAC0/DAC1 channel mapping exists", output)
        self.assertIn("simulation mode can produce values for both DACs", output)
        self.assertEqual(smoke_test.hardware_modules_loaded(), [])


if __name__ == "__main__":
    unittest.main()
