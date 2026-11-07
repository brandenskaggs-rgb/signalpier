#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo 'Run: sudo bash scripts/install.sh'; exit 1; fi
if [[ $(uname -m) != aarch64 && ${SIGNALPIER_ALLOW_OTHER_ARCH:-0} != 1 ]]; then
  echo 'Primary target: 64-bit Raspberry Pi OS. Other Linux hosts can opt in with SIGNALPIER_ALLOW_OTHER_ARCH=1.' >&2
  exit 1
fi
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
apt-get update
apt-get install -y --no-install-recommends python3 rtl-sdr rtl-433 ca-certificates
getent group plugdev >/dev/null || groupadd --system plugdev
id signalpier >/dev/null 2>&1 || useradd --system --user-group --home-dir /opt/signalpier --shell /usr/sbin/nologin signalpier
usermod -a -G plugdev signalpier
install -d -m 755 /opt/signalpier
install -m 644 "$source_dir/app.py" "$source_dir/spaceweather.py" "$source_dir/updates.py" "$source_dir/LICENSE" "$source_dir/VERSION" /opt/signalpier/
cp -R "$source_dir/static" /opt/signalpier/
install -m 644 "$source_dir/systemd/signalpier.service" /etc/systemd/system/signalpier.service
python3 -m py_compile /opt/signalpier/app.py /opt/signalpier/spaceweather.py
systemctl daemon-reload
systemctl enable --now signalpier
echo 'SignalPier is running on localhost:8765. Connect through the SSH tunnel documented in README.md.'
