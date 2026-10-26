# Provenance

This repository is a standalone derivative of
https://github.com/Timandes/platform-fans-hwmon at commit
`8024625707649403616e2158907ff58579404ef1`
("merge: platform fans hwmon 0.2.0", Timandes White, 2026-05-29).

The framework, EC and ITE backends, NUC9/DS2308 descriptors, Makefile and DKMS
configuration originate upstream. Original SPDX and author declarations are
retained. Upstream's original license notice is preserved as COPYING.upstream.

Changes maintained here:
- NUC10i5FNK / FNCML357 platform descriptor exposing the CPU fan only.
- Registration and declaration of that descriptor in the existing framework.
- Direct Python EC readout, optional Checkmk local check, their tests, and docs.
- A complete GPLv2 license text and a Proxmox DKMS build script and workflow template.

The inherited module name `platform_fans_hwmon` and DKMS identity
`platform-fans-hwmon/0.2.0` are deliberately retained for compatibility with
the hardware-tested installation. Do not install this repository alongside
another variant of that same DKMS package.

The EC V9 register layout was cross-checked with
[VirtualSMC ECDeviceNUC.hpp](https://github.com/acidanthera/VirtualSMC/blob/master/Sensors/SMCSuperIO/ECDeviceNUC.hpp).
No VirtualSMC implementation code is included in this repository.
