from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.calibration import (
    apply_dac_calibration,
    default_calibration,
    load_calibration,
)
from src.dac_output import dac_value_from_voltage, voltage_to_u16


class CalibrationTests(unittest.TestCase):
    def test_default_calibration_values_load_from_config(self) -> None:
        calibration = load_calibration()

        self.assertEqual(calibration.dac0.gain, 1.0)
        self.assertEqual(calibration.dac0.offset_volts, 0.0)
        self.assertEqual(calibration.dac1.gain, 1.0)
        self.assertEqual(calibration.dac1.offset_volts, 0.0)
        self.assertEqual(set(calibration.adc), {"AD1", "AD2", "AD3", "AD4"})
        self.assertEqual(calibration.adc["AD1"].minimum, 0.0)
        self.assertEqual(calibration.adc["AD1"].maximum, 1.0)

    def test_gain_and_offset_apply_before_dac_code_conversion(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.json"
            path.write_text(
                json.dumps(
                    {
                        "dac0_gain": 2.0,
                        "dac0_offset_volts": 0.1,
                        "dac1_gain": 0.5,
                        "dac1_offset_volts": -0.1,
                    }
                ),
                encoding="utf-8",
            )
            calibration = load_calibration(path)

        self.assertAlmostEqual(
            apply_dac_calibration(1.0, "DAC0", calibration),
            2.1,
        )
        self.assertAlmostEqual(
            apply_dac_calibration(1.0, "DAC1", calibration),
            0.4,
        )
        self.assertEqual(
            dac_value_from_voltage(2.0, "DAC0", calibration).voltage,
            3.3,
        )
        self.assertEqual(
            voltage_to_u16(1.0, "DAC1", calibration),
            voltage_to_u16(0.4),
        )

    def test_missing_calibration_file_falls_back_to_defaults(self) -> None:
        calibration = load_calibration("/missing/calibration.json")

        self.assertEqual(calibration, default_calibration())

    def test_malformed_calibration_file_falls_back_to_defaults(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.json"
            path.write_text("{not json", encoding="utf-8")

            calibration = load_calibration(path)

        self.assertEqual(calibration, default_calibration())


if __name__ == "__main__":
    unittest.main()
