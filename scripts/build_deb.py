"""Stage a small ARM64 Debian application package; run dpkg-deb separately."""
from pathlib import Path
import os
import shutil

ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
DEB_VERSION=VERSION.replace('-alpha.','~alpha')
STAGE=ROOT/'dist'/'deb-stage'
STAGE.mkdir(parents=True,exist_ok=True)
app=STAGE/'opt'/'signalpier';app.mkdir(parents=True,exist_ok=True)
for name in ['app.py','spaceweather.py','updates.py','portable_update.py','LICENSE','VERSION']:
    shutil.copy2(ROOT/name,app/name)
shutil.copytree(ROOT/'static',app/'static',dirs_exist_ok=True)
for source,target in [
    ('systemd/signalpier.service','lib/systemd/system/signalpier.service'),
    ('systemd/signalpier-update.service','lib/systemd/system/signalpier-update.service'),
    ('systemd/signalpier-update.path','lib/systemd/system/signalpier-update.path'),
    ('packaging/install-update.py','usr/lib/signalpier/install-update.py'),
    ('packaging/signalpier.desktop','usr/share/applications/signalpier.desktop'),
    ('site/icon.svg','usr/share/icons/hicolor/scalable/apps/signalpier.svg'),
    ('packaging/launch.sh','usr/bin/signalpier'),
    ('NOTICE.md','usr/share/doc/signalpier/NOTICE.md'),
    ('LICENSE','usr/share/doc/signalpier/copyright'),
]:
    destination=STAGE/target;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,destination)
control=STAGE/'DEBIAN';control.mkdir(exist_ok=True)
size=sum(p.stat().st_size for p in STAGE.rglob('*') if p.is_file())//1024+1
(control/'control').write_text(f'''Package: signalpier
Version: {DEB_VERSION}
Section: hamradio
Priority: optional
Architecture: arm64
Maintainer: SignalPier contributors <noreply@github.com>
Depends: python3 (>= 3.10), rtl-sdr, rtl-433, adduser
Suggests: xdg-utils
Installed-Size: {size}
Homepage: https://brandenskaggs-rgb.github.io/signalpier/
Description: Lightweight radio workbench and station clock for Raspberry Pi 3
 Browser-based spectrum surveys, supported sensor protocol decoding,
 station clock and a local AES-GCM message lab. Receiver hardware is
 required for live reception. Runs on an existing 64-bit Raspberry Pi OS.
''')
for name in ['postinst','prerm','postrm']:
    shutil.copy2(ROOT/'packaging'/name,control/name)
for path in [STAGE/'usr/bin/signalpier',*(control/name for name in ['postinst','prerm','postrm'])]:
    path.chmod(0o755)
print(f'deb-stage -> signalpier_{VERSION}_arm64.deb')
