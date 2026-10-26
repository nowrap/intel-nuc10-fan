#!/usr/bin/env python3
"""Checkmk fan1 check using hwmon or the validated NUC10 readout helper."""

import re
import subprocess
import sys
from pathlib import Path

NUC_READER = Path("/usr/local/libexec/nuc10-fan.py")


def check(hwmon=Path("/sys/class/hwmon")):
    try:
        matches = []
        for device in hwmon.glob("hwmon*"):
            name = (device / "name").read_text().strip()
            if name in ("intel_nuc_ec", "nct6792"):
                matches.append((device, name))
        if len(matches) > 1:
            raise ValueError(f"Erwartet wird genau ein Luefterchip, gefunden: {len(matches)}")
        if matches:
            device, name = matches[0]
            rpm = int((device / "fan1_input").read_text().strip())
        else:
            if not NUC_READER.is_file():
                raise ValueError(f"Kein hwmon-Luefterchip; NUC-Helfer {NUC_READER} fehlt")
            result = subprocess.run(
                [sys.executable, str(NUC_READER)],
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=5, check=False,
            )
            if result.returncode:
                raise ValueError(result.stderr.strip() or "NUC-Abfrage fehlgeschlagen")
            match = re.search(r"^CPU-Luefter \(EC V9 fan1\): ([0-9]+) RPM$", result.stdout, re.MULTILINE)
            if not match:
                raise ValueError("NUC-Abfrage liefert keine gueltige RPM-Zeile")
            rpm = int(match.group(1))
            name = "NUC10 EC (Python)"
        if not 0 <= rpm < 65535:
            raise ValueError("Ungueltiger RPM-Messwert")
        # shortcut: no low-RPM alarm until this host's fan-stop behavior is confirmed.
        return f'0 "Fan RPM" rpm={rpm} {name} fan1: {rpm} RPM (ohne RPM-Untergrenze)'
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        message = " ".join(str(error).splitlines())
        return f'3 "Fan RPM" - Auslesen fehlgeschlagen: {message}'


if __name__ == "__main__":
    print(check())
