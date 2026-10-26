# Intel NUC10 fan RPM for Linux

Expose the CPU fan speed of the Intel **NUC10i5FNK** through Linux hwmon,
`sensors`, and monitoring tools.

This is nowrap's NUC10 adaptation of
[Timandes/platform-fans-hwmon](https://github.com/Timandes/platform-fans-hwmon).
The existing kernel driver code, module name and DKMS package identity are
preserved. See [UPSTREAM.md](UPSTREAM.md) for provenance.

## Confirmed hardware

| Item | Validated value |
| --- | --- |
| Product | NUC10i5FNK |
| BIOS | FNCML357.0053.2021.0707.1420 |
| Kernel | 7.0.14-25-pve |
| Fan | CPU fan, EC V9 register 0x41B |
| Result | 2177 RPM in `sensors`; DKMS status `installed` |

Only this NUC10 model has been validated by this project. The inherited NUC9
and DS2308 platform descriptors remain in the upstream framework; this project
does not claim additional hardware validation for them.

The NUC10 descriptor requires the exact product name and the FNCML357 BIOS
family. The backend derives the EC MMIO address from the active PCI LGMR
register and checks for an ELM_EC or SPG_EC identifier.

Fan attributes are read-only. Firmware continues to control fan speed.

## Install on Proxmox VE / Debian trixie

Run these commands as root **on the physical Proxmox host**. The kernel module
belongs on the host even if Checkmk runs in an LXC container.

```bash
apt update
apt install build-essential dkms libelf1t64 zstd lm-sensors git \
  proxmox-default-headers proxmox-headers-7.0 \
  "proxmox-headers-$(uname -r)"

git clone https://github.com/nowrap/intel-nuc10-fan.git
cd intel-nuc10-fan
dkms install .
modprobe platform_fans_hwmon platform=intel-nuc10-ec-v9
sensors 'intel_nuc_ec-*'
```

Expected example:

```text
intel_nuc_ec-isa-0000
Adapter: ISA adapter
CPU Fan:     2177 RPM
```

Once the readout works, enable loading at boot:

```bash
printf '%s\n' platform_fans_hwmon > /etc/modules-load.d/nuc10-fan.conf
```

The module is `platform_fans_hwmon`; the DKMS package is
`platform-fans-hwmon/0.2.0`. Users of the earlier `nuc10-hwmon.tar.gz`
already have this same driver installed and do not need to reinstall it.

### Kernel updates

`dkms.conf` sets `AUTOINSTALL="yes"`. DKMS rebuilds the registered source for
new kernels when matching headers are available. The header metapackages above
follow the Proxmox default kernel series and the validated 7.0 series. Install
the corresponding headers when manually switching to another optional series.

After a kernel update, check the new kernel's status before rebooting:

```bash
dkms status -m platform-fans-hwmon
```

It should say `installed` for that kernel. DKMS cannot fix incompatible kernel
API changes in the source. Secure Boot requires trusting the DKMS signing key.

### Other Linux distributions

The interface is Linux hwmon, but the installation above is only validated on
Proxmox/Debian trixie. Install your distribution's compiler, DKMS and headers
for the target kernel before using `dkms install .`.

## Checkmk

The **agent and local check run on the Proxmox host**; the Checkmk server may
run in an LXC container.

```bash
install -D -m 0755 check-fan-rpm.py /usr/lib/check_mk_agent/local/fan_rpm
/usr/lib/check_mk_agent/local/fan_rpm
```

Discover and accept the `Fan RPM` service in Checkmk, then activate changes.
The check returns an `rpm` metric and reports read errors as `UNKNOWN`.
No lower RPM alarm threshold is configured: a permitted idle fan stop must
be established before choosing one.

The check prefers hwmon. Without a supported hwmon chip it can call the
validated direct EC reader, installed as root:

```bash
install -D -m 0755 nuc10-fan.py /usr/local/libexec/nuc10-fan.py
```

That fallback requires root and access to `/dev/mem`. The optional check also
retains the existing `nct6792` fan1 readout; it is not kernel-driver support.

See [Checkmk local checks](https://docs.checkmk.com/latest/en/localchecks.html).

## Troubleshooting and removal

```bash
dkms status -m platform-fans-hwmon
dmesg | grep -iE 'platform_fans|intel.nuc|EC MMIO'
```

To remove the driver:

```bash
modprobe -r platform_fans_hwmon
dkms remove platform-fans-hwmon/0.2.0 --all
rm -f /etc/modules-load.d/nuc10-fan.conf
```

No runtime module unload, reboot persistence, or future kernel update has yet
been validated by this project. [Validation evidence](docs/validation.md)
distinguishes hardware results from automated tests.

## Development

```bash
python3 -m unittest discover -s tests -v
make KERNEL_VERSION="$(uname -r)"
```

The build can be repeated in a disposable container:

```bash
docker run --rm --mount "type=bind,source=$PWD,target=/src,readonly" \
  --workdir /src debian:trixie-slim bash ci/build-proxmox.sh
```

[GitHub Actions](.github/workflows/check.yml) runs on pushes, pull requests
and manual dispatch. It runs the Python tests and builds/installs DKMS with
the available Proxmox 7.0 headers in an isolated Debian trixie container.

The build does not load the module or prove support for additional hardware.

For another NUC model, open an issue with product name, BIOS version, kernel
and existing `sensors` output. Remove identifying information before sharing
logs. Do not bypass the hardware guards to test unknown EC layouts.

## License and credits

GPL-2.0-only. Original framework copyright (C) 2026 Timandes White.
NUC10 support, readout helper, Checkmk integration and project documentation
are maintained by nowrap. The original license notice is preserved in
[COPYING.upstream](COPYING.upstream); the complete GPLv2 text is in [LICENSE](LICENSE).
