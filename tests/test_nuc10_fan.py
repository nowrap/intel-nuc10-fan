import contextlib
import importlib.util
import io
import mmap
import os
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "nuc10_fan", Path(__file__).resolve().parents[1] / "nuc10-fan.py"
)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def sample(identifier=b"ELM_EC", rpm=2500):
    data = bytearray(4096)
    data[0x400:0x406] = identifier
    data[0x41B:0x41D] = rpm.to_bytes(2, "big")
    return data


class FanReaderTests(unittest.TestCase):
    def test_identifiers_zero_and_big_endian_rpm(self):
        for identifier in (b"ELM_EC", b"SPG_EC"):
            for rpm in (0, 255, 256, 2500, 6000):
                self.assertEqual(reader.read_rpm(sample(identifier, rpm)), rpm)

    def test_rejects_unknown_layout_and_invalid_read(self):
        for data in (sample(b"NUC_EC"), sample(rpm=65535)):
            with self.assertRaises(ValueError):
                reader.read_rpm(data)

    def test_retries_if_high_byte_changes(self):
        class ChangingEC:
            high = iter((1, 2, 2, 2))

            def __getitem__(self, offset):
                return next(self.high) if offset == 0x41B else sample(rpm=600)[offset]

        self.assertEqual(reader.read_rpm(ChangingEC()), 600)

    def test_stops_if_measurement_never_stabilizes(self):
        class ChangingEC:
            high = iter(range(10))

            def __getitem__(self, offset):
                return next(self.high) if offset == 0x41B else sample()[offset]

        with self.assertRaises(ValueError):
            reader.read_rpm(ChangingEC())

    def test_hardware_access_is_read_only_and_stops_at_bad_lgmr(self):
        values = {
            "product_name": "NUC10i5FNK",
            "bios_version": "FNCML357.0066.2024.0823.1515",
            "vendor": "0x8086",
            "class": "0x060100",
        }
        for lgmr in (0, 0xFE410000, 1, 0xFFFFFFFF, 0xFE410001):
            config = io.BytesIO(bytes(0x98) + lgmr.to_bytes(4, "little"))
            with (
                patch.object(reader.Path, "read_text", lambda path: values[path.name]),
                patch.object(reader.Path, "open", return_value=config) as opened,
                patch.object(reader.os, "open", return_value=123) as mem_open,
                patch.object(reader.os, "close") as mem_close,
                patch.object(reader.mmap, "mmap") as mapped,
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                mapped.return_value.__enter__.return_value = sample()
                if lgmr != 0xFE410001:
                    with self.assertRaises(ValueError):
                        reader.main()
                    mem_open.assert_not_called()
                else:
                    reader.main()
                    mem_open.assert_called_once_with("/dev/mem", os.O_RDONLY | os.O_SYNC)
                    mapped.assert_called_once_with(
                        123, 4096, access=mmap.ACCESS_READ, offset=0xFE410000
                    )
                    mem_close.assert_called_once_with(123)
                    self.assertIn("2500 RPM", output.getvalue())
                opened.assert_called_once_with("rb", buffering=0)

    def test_wrong_model_and_bios_never_open_hardware(self):
        for values in (("NUC9i7QNX", "FNCML357.0066"), ("NUC10i5FNK", "OTHER")):
            with (
                patch.object(reader.Path, "read_text", side_effect=values),
                patch.object(reader.Path, "open") as opened,
                patch.object(reader.os, "open") as mem_open,
            ):
                with self.assertRaises(ValueError):
                    reader.main()
                opened.assert_not_called()
                mem_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
