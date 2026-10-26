# Validation

## Real hardware, 2026-10-26

Reported by the project owner on NUC10i5FNK:
- BIOS: FNCML357.0053.2021.0707.1420.
- Proxmox kernel: 7.0.14-25-pve.
- Direct Python EC readout: 2148 RPM, changing around 2150 RPM.
- DKMS build, signing and installation completed successfully.
- Module loaded with `platform=intel-nuc10-ec-v9`.
- `sensors` displayed:

```text
intel_nuc_ec-isa-0000
Adapter: ISA adapter
CPU Fan:     2177 RPM
```

- `dkms status -m platform-fans-hwmon` displayed:

```text
platform-fans-hwmon/0.2.0, 7.0.14-25-pve, x86_64: installed
```

- Boot loading configuration was written to /etc/modules-load.d/nuc10-fan.conf.
  A reboot has not yet confirmed persistence.

## Automated verification

- 18 Python tests cover EC identifiers, big-endian RPM, stable reads,
  model/BIOS/LGMR guards, read-only memory access, local-check hwmon selection,
  fallback subprocess execution, invalid output, error propagation and timeout.
- The DKMS module was built, signed and installed against exact Proxmox
  7.0.14-25-pve headers in an isolated Debian trixie container.
- The published project retains the same C sources, Makefile and dkms.conf
  as the hardware-tested source package.
- The new CI build script passed locally in a fresh Debian trixie-slim container:
  DKMS build, signing, installation and modinfo inspection on 7.0.14-25-pve.
- The workflow template can repeat Python tests and a DKMS build with the
  available Proxmox 7.0 headers after being enabled; it is not active on GitHub.
  A successful build is not a hardware test.

## Still unverified

- A real subsequent kernel update and automatic DKMS rebuild.
- Reboot persistence and module unload on the NUC.
- Checkmk agent collection and service discovery on the actual host.
- Other NUC models, BIOS versions and Linux distributions.
