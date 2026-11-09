"""Build Windows 10/11 x64 setup. Run with PyInstaller 6.20 and Inno Setup 7.1.1."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.request import urlopen
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DOWNLOADS=[
 ('rtlsdr.zip','https://github.com/rtlsdrblog/rtl-sdr-blog/releases/download/V1.4.0/Release.zip','7ef33f1304647f65e5e0fde43637a73d54f076e91e651a3cecc4f55a17fd9815'),
 ('rtl433.zip','https://github.com/merbanan/rtl_433/releases/download/25.12/rtl_433-win-x64-25.12.zip','ed42651d2a2a94f6419f7675955bd65449d8247e27822c65c363595b715b7de6')]

def main():
    if os.name!='nt': raise SystemExit('Build this installer on Windows x64.')
    parser=argparse.ArgumentParser();parser.add_argument('--iscc',required=True);args=parser.parse_args()
    cache=ROOT/'.test-tools/windows';cache.mkdir(parents=True,exist_ok=True)
    tools=cache/'tools';tools.mkdir(exist_ok=True)
    for name,url,digest in DOWNLOADS:
        archive=cache/name
        if not archive.exists(): archive.write_bytes(urlopen(url,timeout=60).read())
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=digest: raise RuntimeError('Dependency checksum mismatch: '+name)
        with zipfile.ZipFile(archive) as source:
            names=['x64/rtl_power.exe','x64/rtlsdr.dll'] if name=='rtlsdr.zip' else ['rtl_433.exe','libusb-1.0.dll','SoapySDR.dll']
            for member in names: (tools/Path(member).name).write_bytes(source.read(member))
    # Use one known RTL-SDR Blog build for enumeration, sweeps, and decoding.
    shutil.copyfile(tools/'rtlsdr.dll',tools/'librtlsdr.dll')
    for unused in ['msvcr100.dll','pthreadVC2.dll']:
        if (tools/unused).exists(): (tools/unused).unlink()
    licenses=cache/'licenses';licenses.mkdir(exist_ok=True)
    shutil.copyfile(Path(sys.base_prefix)/'LICENSE.txt',licenses/'Python-LICENSE.txt')
    import importlib.metadata
    distribution=importlib.metadata.distribution('pyinstaller')
    for entry in distribution.files or []:
        if entry.name=='COPYING.txt': shutil.copyfile(distribution.locate_file(entry),licenses/'PyInstaller-COPYING.txt')
    for name,url in [('RTL-SDR-COPYING','https://raw.githubusercontent.com/rtlsdrblog/rtl-sdr-blog/V1.4.0/COPYING'),('rtl_433-COPYING','https://raw.githubusercontent.com/merbanan/rtl_433/25.12/COPYING')]:
        (licenses/name).write_bytes(urlopen(url,timeout=30).read())
    for name,url in [('libusb-COPYING','https://raw.githubusercontent.com/libusb/libusb/v1.0.29/COPYING'),('SoapySDR-LICENSE','https://raw.githubusercontent.com/pothosware/SoapySDR/soapy-sdr-0.8.1/LICENSE_1_0.txt')]:
        (licenses/name).write_bytes(urlopen(url,timeout=30).read())
    work=ROOT/'.test-tools/pyinstaller';work.mkdir(exist_ok=True)
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','SignalPier','--icon',str(ROOT/'packaging/signalpier.ico'),'--distpath',str(ROOT/'dist/windows'),'--workpath',str(work/'build'),'--specpath',str(work)]
    for source,target in [('static','static'),('VERSION','.'),('LICENSE','.'),('NOTICE.md','.'),(str(tools),'tools'),(str(licenses),'licenses')]:
        path=Path(source);path=path if path.is_absolute() else ROOT/path
        command+=['--add-data',str(path)+os.pathsep+target]
    command+=[str(ROOT/'windows.py')]
    subprocess.run(command,cwd=ROOT,check=True)
    version=(ROOT/'VERSION').read_text().strip()
    subprocess.run([args.iscc,'/DAppVersion='+version,str(ROOT/'packaging/windows.iss')],cwd=ROOT,check=True)

if __name__=='__main__': main()
