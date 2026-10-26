import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "check_fan_rpm", Path(__file__).resolve().parents[1] / "check-fan-rpm.py"
)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class CheckmkFanTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        helper = patch.object(reader, "NUC_READER", self.root / "nuc10-fan.py")
        helper.start()
        self.addCleanup(helper.stop)

    def device(self, number, name, rpm=None):
        path = self.root / f"hwmon{number}"
        path.mkdir()
        (path / "name").write_text(name)
        if rpm is not None:
            (path / "fan1_input").write_text(str(rpm))
        return path

    def test_uses_chip_name_instead_of_unstable_hwmon_number(self):
        self.device(0, "coretemp")
        path = self.device(7, "intel_nuc_ec", 2148)
        output = reader.check(self.root)
        self.assertEqual(output, '0 "Fan RPM" rpm=2148 intel_nuc_ec fan1: 2148 RPM (ohne RPM-Untergrenze)')
        self.assertEqual((path / "fan1_input").read_text(), "2148")

    def test_fujitsu_ignores_unused_second_fan(self):
        path = self.device(3, "nct6792", 1248)
        (path / "fan2_input").write_text("0")
        self.assertIn('0 "Fan RPM" rpm=1248 nct6792 fan1:', reader.check(self.root))

    def test_zero_is_reported_without_inventing_a_fan_fault(self):
        self.device(1, "intel_nuc_ec", 0)
        self.assertTrue(reader.check(self.root).startswith('0 "Fan RPM" rpm=0 '))

    def test_missing_driver_has_stable_unknown_service_name(self):
        self.device(0, "coretemp")
        self.assertTrue(reader.check(self.root).startswith('3 "Fan RPM" - '))

    def test_missing_or_invalid_rpm_is_unknown(self):
        path = self.device(2, "nct6792")
        self.assertTrue(reader.check(self.root).startswith('3 "Fan RPM" - '))
        for value in ("", "not-a-number", "-1", "65535"):
            (path / "fan1_input").write_text(value)
            self.assertTrue(reader.check(self.root).startswith('3 "Fan RPM" - '))

    def test_ambiguous_chips_are_not_silently_misattributed(self):
        self.device(1, "intel_nuc_ec", 2148)
        self.device(2, "nct6792", 1248)
        self.assertTrue(reader.check(self.root).startswith('3 "Fan RPM" - '))


    def test_nuc_helper_supplies_rpm_when_hwmon_is_missing(self):
        reader.NUC_READER.touch()
        result = subprocess.CompletedProcess([], 0, "NUC10i5FNK, BIOS FNCML357\nCPU-Luefter (EC V9 fan1): 2148 RPM\n", "")
        with patch.object(reader.subprocess, "run", return_value=result) as run:
            self.assertIn('0 "Fan RPM" rpm=2148 NUC10 EC (Python) fan1:', reader.check(self.root))
        run.assert_called_once_with(
            [reader.sys.executable, str(reader.NUC_READER)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=5, check=False,
        )

    def test_hwmon_takes_priority_over_helper(self):
        self.device(1, "intel_nuc_ec", 2148)
        reader.NUC_READER.touch()
        with patch.object(reader.subprocess, "run") as run:
            self.assertIn('0 "Fan RPM" rpm=2148 intel_nuc_ec fan1:', reader.check(self.root))
        run.assert_not_called()

    def test_helper_failure_preserves_error_as_single_line_unknown(self):
        reader.NUC_READER.touch()
        result = subprocess.CompletedProcess([], 1, "", "Abbruch: Zugriff verweigert\nDetails\n")
        with patch.object(reader.subprocess, "run", return_value=result):
            output = reader.check(self.root)
        self.assertEqual(output, '3 "Fan RPM" - Auslesen fehlgeschlagen: Abbruch: Zugriff verweigert Details')

    def test_helper_malformed_or_out_of_range_output_is_unknown(self):
        reader.NUC_READER.touch()
        for output in ("", "NUC10: 2148 RPM", "CPU-Luefter (EC V9 fan1): -1 RPM\n", "CPU-Luefter (EC V9 fan1): 65535 RPM\n"):
            with patch.object(reader.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")):
                self.assertTrue(reader.check(self.root).startswith('3 "Fan RPM" - '))

    def test_helper_timeout_is_unknown(self):
        reader.NUC_READER.touch()
        with patch.object(reader.subprocess, "run", side_effect=subprocess.TimeoutExpired("nuc10-fan.py", 5)):
            self.assertTrue(reader.check(self.root).startswith('3 "Fan RPM" - '))

    def test_helper_subprocess_round_trip(self):
        reader.NUC_READER.write_text("print('NUC10i5FNK')\nprint('CPU-Luefter (EC V9 fan1): 2170 RPM')\n")
        self.assertIn('0 "Fan RPM" rpm=2170 NUC10 EC (Python) fan1:', reader.check(self.root))


if __name__ == "__main__":
    unittest.main()
