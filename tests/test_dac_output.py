from __future__ import annotations

import math
import unittest

from src.dac_output import (
    DAC_MAX_CODE,
    bipolar_to_u16,
    bipolar_to_voltage,
    clamp_u16,
    clamp_voltage,
    voltage_to_u16,
)


class DacOutputTests(unittest.TestCase):
    def test_voltage_clamping_limits_outputs_to_0_to_3v3(self) -> None:
        self.assertEqual(clamp_voltage(-0.25), 0.0)
        self.assertEqual(clamp_voltage(0.0), 0.0)
        self.assertEqual(clamp_voltage(1.2), 1.2)
        self.assertEqual(clamp_voltage(3.3), 3.3)
        self.assertEqual(clamp_voltage(4.7), 3.3)

    def test_nonfinite_voltage_fails_safe_to_zero_volts(self) -> None:
        self.assertEqual(clamp_voltage(math.nan), 0.0)
        self.assertEqual(clamp_voltage(math.inf), 0.0)
        self.assertEqual(clamp_voltage(-math.inf), 0.0)

    def test_bipolar_waveform_maps_to_dac_voltage_range(self) -> None:
        self.assertEqual(bipolar_to_voltage(-2.0), 0.0)
        self.assertAlmostEqual(bipolar_to_voltage(0.0), 1.65)
        self.assertEqual(bipolar_to_voltage(2.0), 3.3)
        self.assertEqual(bipolar_to_voltage(math.nan), 0.0)

    def test_voltage_and_raw_codes_are_clamped(self) -> None:
        self.assertEqual(voltage_to_u16(-1.0), 0)
        self.assertEqual(voltage_to_u16(3.3), DAC_MAX_CODE)
        self.assertEqual(voltage_to_u16(99.0), DAC_MAX_CODE)
        self.assertEqual(bipolar_to_u16(-99.0), 0)
        self.assertEqual(bipolar_to_u16(99.0), DAC_MAX_CODE)
        self.assertEqual(clamp_u16(-10), 0)
        self.assertEqual(clamp_u16(DAC_MAX_CODE + 1), DAC_MAX_CODE)


if __name__ == "__main__":
    unittest.main()
