from __future__ import annotations

from io import StringIO
import unittest

from src.dac_output import DAC_MAX_CODE
from src.dac_test import (
    generate_rows,
    main,
    normalize_channel,
    pattern_voltage,
    write_channel,
)


class RecordingDAC:
    def __init__(self) -> None:
        self.writes: list[tuple[str, float]] = []

    def write_voltage_a(self, voltage: float) -> None:
        self.writes.append(("DAC0", voltage))

    def write_voltage_b(self, voltage: float) -> None:
        self.writes.append(("DAC1", voltage))


class DacTestUtilityTests(unittest.TestCase):
    def test_channel_selection_routes_to_requested_output(self) -> None:
        dac = RecordingDAC()

        write_channel(dac, "DAC0", 1.0)
        write_channel(dac, "dac1", 2.0)

        self.assertEqual(dac.writes, [("DAC0", 1.0), ("DAC1", 2.0)])
        self.assertEqual(normalize_channel("dac0"), "DAC0")
        with self.assertRaises(ValueError):
            normalize_channel("DAC2")

    def test_generate_rows_clamps_voltage(self) -> None:
        rows = generate_rows(
            pattern="steady",
            channel="DAC0",
            volts=9.0,
            seconds=0.0,
            rate_hz=1.0,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].dac_value.voltage, 3.3)
        self.assertEqual(rows[0].dac_value.code, DAC_MAX_CODE)

    def test_simulation_output_path_prints_table_and_records_write(self) -> None:
        stdout = StringIO()

        main(
            [
                "--channel",
                "DAC1",
                "--volts",
                "1.65",
                "--seconds",
                "0",
            ],
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("Simulation mode", output)
        self.assertIn("timestamp_s channel volts code", output)
        self.assertIn("0.000 DAC1 1.650000", output)

    def test_ramp_value_generation(self) -> None:
        rows = generate_rows(
            pattern="ramp",
            channel="DAC0",
            volts=3.3,
            seconds=2.0,
            rate_hz=1.0,
        )

        self.assertEqual([row.timestamp_s for row in rows], [0.0, 1.0, 2.0])
        self.assertEqual([row.dac_value.voltage for row in rows], [0.0, 1.65, 3.3])

    def test_triangle_value_generation(self) -> None:
        rows = generate_rows(
            pattern="triangle",
            channel="DAC1",
            volts=3.3,
            seconds=2.0,
            rate_hz=1.0,
        )

        self.assertEqual([row.timestamp_s for row in rows], [0.0, 1.0, 2.0])
        self.assertEqual([row.dac_value.voltage for row in rows], [0.0, 3.3, 0.0])
        self.assertEqual(pattern_voltage("triangle", 3.3, 1, 3), 3.3)


if __name__ == "__main__":
    unittest.main()
