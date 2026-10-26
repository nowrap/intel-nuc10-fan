#!/usr/bin/env python3
"""Read Intel NUC10i5FNK EC V9 fan1 RPM without changing hardware settings."""

import mmap
import os
import sys
from pathlib import Path

# Register layout: acidanthera/VirtualSMC, Sensors/SMCSuperIO/ECDeviceNUC.hpp.
# shortcut: only NUC10i5FNK/FNCML357, validate each additional model before enabling it.


def read_rpm(ec):
    identifier = bytes(ec[0x400 + i] for i in range(6))
    if identifier not in (b"ELM_EC", b"SPG_EC"):
        raise ValueError(f"Unbekannte EC-Kennung: {identifier!r}")
    for _ in range(5):
        high = ec[0x41B]
        low = ec[0x41C]
        if high == ec[0x41B]:
            rpm = (high << 8) | low
            if rpm == 0xFFFF:
                raise ValueError("EC liefert 0xffff statt einer gueltigen Drehzahl")
            return rpm
    raise ValueError("Drehzahl waehrend der Abfrage geaendert; bitte erneut ausfuehren")


def main():
    dmi = Path("/sys/class/dmi/id")
    model = (dmi / "product_name").read_text().strip()
    bios = (dmi / "bios_version").read_text().strip()
    if model != "NUC10i5FNK" or not bios.startswith("FNCML357."):
        raise ValueError(f"Nicht freigegebenes Modell/BIOS: {model} / {bios}")

    pci = Path("/sys/bus/pci/devices/0000:00:1f.0")
    if (pci / "vendor").read_text().strip() != "0x8086" or (
        pci / "class"
    ).read_text().strip() != "0x060100":
        raise ValueError("Erwartete Intel-LPC/eSPI-Bridge fehlt")
    with (pci / "config").open("rb", buffering=0) as config:
        config.seek(0x98)
        raw = config.read(4)
    if len(raw) != 4:
        raise ValueError("PCI-Register LGMR konnte nicht vollstaendig gelesen werden")
    lgmr = int.from_bytes(raw, "little")
    base = lgmr & 0xFFFF0000
    if lgmr == 0xFFFFFFFF or not (lgmr & 1) or not base:
        raise ValueError(f"EC-Speicherfenster nicht nutzbar: LGMR=0x{lgmr:08x}")

    print(f"{model}, BIOS {bios}, EC-Adresse 0x{base:08x}", flush=True)
    fd = os.open("/dev/mem", os.O_RDONLY | os.O_SYNC)
    try:
        with mmap.mmap(fd, 4096, access=mmap.ACCESS_READ, offset=base) as ec:
            rpm = read_rpm(ec)
    finally:
        os.close(fd)
    print(f"CPU-Luefter (EC V9 fan1): {rpm} RPM")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(f"Abbruch: {error}")
