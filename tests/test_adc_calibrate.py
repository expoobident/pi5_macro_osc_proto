from __future__ import annotations

from io import StringIO
import unittest

from src import adc_calibrate


class AdcCalibrateTests(unittest.TestCase):
    def test_adc_calibrate_prints_safe_instructions(self) -> None:
        stdout = StringIO()

        adc_calibrate.main([], stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("Instruction mode", output)
        self.assertIn("AD4 = pitch", output)
        self.assertIn("AD1 = timbre", output)
        self.assertIn("AD2 = morph", output)
        self.assertIn("AD3 = index", output)
        self.assertIn("adc_min and adc_max", output)


if __name__ == "__main__":
    unittest.main()
