from __future__ import annotations

from contextlib import redirect_stderr
import csv
from io import StringIO
import json
import unittest

from src import control_monitor


class ControlMonitorTests(unittest.TestCase):
    def test_simulation_table_output_includes_control_mapping(self) -> None:
        stdout = StringIO()

        control_monitor.main(["--simulate", "--samples", "1"], stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("sample channel control raw normalized mapped unit", output)
        self.assertIn("AD4 pitch", output)
        self.assertIn("AD1 timbre", output)
        self.assertIn("AD2 morph", output)
        self.assertIn("AD3 index", output)
        self.assertEqual(control_monitor.hardware_modules_loaded(), [])

    def test_refuses_without_simulate_or_enable_input(self) -> None:
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as context:
                control_monitor.main(["--samples", "1"], stdout=stdout)

        self.assertEqual(context.exception.code, 2)
        self.assertIn("real ADC input is disabled", stderr.getvalue())

    def test_csv_output_formatting(self) -> None:
        stdout = StringIO()

        control_monitor.main(
            ["--simulate", "--samples", "1", "--csv"],
            stdout=stdout,
        )

        rows = list(csv.DictReader(StringIO(stdout.getvalue())))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["channel"], "AD4")
        self.assertEqual(rows[0]["control"], "pitch")
        self.assertIn("normalized", rows[0])

    def test_json_output_formatting(self) -> None:
        stdout = StringIO()

        control_monitor.main(
            ["--simulate", "--samples", "1", "--json"],
            stdout=stdout,
        )

        rows = json.loads(stdout.getvalue())
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["channel"], "AD4")
        self.assertEqual(rows[0]["control"], "pitch")
        self.assertIn("mapped", rows[0])


if __name__ == "__main__":
    unittest.main()
