#!/bin/bash
# Isolated CI container only: installs build dependencies and Proxmox headers.
set -euo pipefail

apt-get update
apt-get install -y --no-install-recommends \
  build-essential dkms ca-certificates curl libelf1t64 zstd
curl -fsSL https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg \
  -o /usr/share/keyrings/proxmox-release-trixie.gpg
printf '%s\n' \
  'deb [signed-by=/usr/share/keyrings/proxmox-release-trixie.gpg] http://download.proxmox.com/debian/pve trixie pve-no-subscription' \
  > /etc/apt/sources.list.d/proxmox-ci.list
apt-get update
apt-get install -y --no-install-recommends proxmox-headers-7.0
kernel_version=$(find /lib/modules -mindepth 1 -maxdepth 1 -type d -name '*-pve' -printf '%f\n' | sort -V | tail -n 1)
test -n "$kernel_version"
dkms install . -k "$kernel_version"
modinfo /lib/modules/"$kernel_version"/updates/dkms/platform_fans_hwmon.ko*
dkms status -m platform-fans-hwmon
