"""Build a real ARM64 type-2 AppImage using a Debian Bookworm ARM64 sysroot.

Requires Linux, squashfs-tools, and a sysroot with rtl-sdr and rtl-433 installed.
Python 3.10+ and base system libraries come from the supported Pi OS host.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
RUNTIME_URL='https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-aarch64'
RUNTIME_SHA='00cbdfcf917cc6c0ff6d3347d59e0ca1f7f45a6df1a428a0d6d8a78664d87444'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('sysroot',type=Path);args=parser.parse_args()
    sysroot=args.sysroot.resolve();out=ROOT/'dist';out.mkdir(exist_ok=True)
    version=(ROOT/'VERSION').read_text().strip()
    with tempfile.TemporaryDirectory(prefix='signalpier-appimage-') as work:
        stage=Path(work)/'SignalPier.AppDir';stage.mkdir()
        app=stage/'app';app.mkdir()
        for name in ['app.py','updates.py','portable_update.py','desktop.py','spaceweather.py','VERSION','LICENSE','NOTICE.md']:
            shutil.copyfile(ROOT/name,app/name)
        shutil.copytree(ROOT/'static',app/'static')
        shutil.copyfile(ROOT/'packaging/AppRun',stage/'AppRun');(stage/'AppRun').chmod(0o755)
        shutil.copyfile(ROOT/'site/icon.svg',stage/'signalpier.svg')
        shutil.copyfile(ROOT/'site/icon.svg',stage/'.DirIcon')
        (stage/'signalpier.desktop').write_text('[Desktop Entry]\nType=Application\nName=SignalPier\nExec=AppRun\nIcon=signalpier\nCategories=Utility;HamRadio;\nTerminal=false\n')
        bins=stage/'usr/bin';bins.mkdir(parents=True)
        native=stage/'usr/lib/signalpier';native.mkdir(parents=True)
        libs=stage/'usr/lib/aarch64-linux-gnu';libs.mkdir(parents=True)
        for name in ['rtl_power','rtl_433']:
            shutil.copyfile(sysroot/'usr/bin'/name,native/name);(native/name).chmod(0o755)
            wrapper=bins/name
            wrapper.write_text('#!/bin/sh\nbase=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\nexport LD_LIBRARY_PATH="$base/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "$base/lib/signalpier/'+name+'" "$@"\n')
            wrapper.chmod(0o755)
        for name in ['librtlsdr.so.0','libusb-1.0.so.0','libSoapySDR.so.0.8']:
            shutil.copyfile(sysroot/'usr/lib/aarch64-linux-gnu'/name,libs/name)
        licenses=stage/'usr/share/doc';licenses.mkdir(parents=True)
        for name in ['rtl-sdr','rtl-433','librtlsdr0','libusb-1.0-0','libsoapysdr0.8']:
            target=licenses/name;target.mkdir()
            shutil.copyfile(sysroot/'usr/share/doc'/name/'copyright',target/'copyright')
        shutil.copytree(sysroot/'usr/share/common-licenses',licenses/'common-licenses')
        (licenses/'AppImage-runtime-LICENSE').write_bytes(urlopen('https://raw.githubusercontent.com/AppImage/type2-runtime/20251108/LICENSE').read())
        rules=list(sysroot.glob('**/60-librtlsdr*.rules'))
        if not rules: rules=list(sysroot.glob('**/*rtl*sdr*.rules'))
        if not rules: raise RuntimeError('RTL-SDR USB rules were not found in the sysroot')
        shutil.copyfile(rules[0],app/'rtl-sdr.rules')
        runtime=urlopen(RUNTIME_URL).read()
        if hashlib.sha256(runtime).hexdigest()!=RUNTIME_SHA: raise RuntimeError('Runtime checksum mismatch')
        filesystem=Path(work)/'payload.squashfs'
        subprocess.run(['mksquashfs',str(stage),str(filesystem),'-noappend','-all-root','-comp','gzip','-no-xattrs','-processors','2'],check=True,stdout=subprocess.DEVNULL)
        image=out/f'SignalPier-{version}-aarch64.AppImage'
        image.write_bytes(runtime+filesystem.read_bytes());image.chmod(0o755)
        (out/'appimage-build.json').write_text(json.dumps({'version':version,'runtime_url':RUNTIME_URL,'runtime_sha256':RUNTIME_SHA,'appimage_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'bytes':image.stat().st_size},indent=2))
        print(image,flush=True)

if __name__=='__main__': main()
