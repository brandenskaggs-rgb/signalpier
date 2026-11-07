"""Root updater: no caller-supplied URL, path, command, package name, or arguments."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.request import Request, urlopen

FEED='https://brandenskaggs-rgb.github.io/signalpier/release.json'
STATE=Path('/var/lib/signalpier')


def report(status,message):
    fd,path=tempfile.mkstemp(prefix='.update-status-',dir=STATE)
    try:
        with os.fdopen(fd,'w') as output:
            json.dump({'status':status,'message':message},output)
        os.chmod(path,0o644)
        os.replace(path,STATE/'update-status.json')
    finally:
        if os.path.exists(path):os.unlink(path)


def validate_manifest(manifest):
    version=str(manifest['version'])
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?',version):raise ValueError('Invalid release version')
    deb_version=re.sub(r'-(alpha|beta|rc)\.',r'~\1',version)
    item=manifest['installer']
    expected=f'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v{version}/signalpier_{deb_version}_arm64.deb'
    if item['url']!=expected:raise ValueError('Release URL does not match the project/version')
    if not re.fullmatch('[a-f0-9]{64}',str(item['sha256'])):raise ValueError('Invalid release checksum')
    if not isinstance(item['bytes'],int) or not 0<item['bytes']<=10_000_000:raise ValueError('Unexpected installer size')
    return deb_version,item


def main():
    marker=STATE/'update.request'
    if not marker.exists():return
    marker.unlink()
    report('installing','Checking the latest release…')
    try:
        with urlopen(Request(FEED,headers={'User-Agent':'SignalPier-updater'}),timeout=15) as response:
            raw=response.read(100001)
        if len(raw)>100000:raise ValueError('Release manifest too large')
        version,item=validate_manifest(json.loads(raw))
        current=subprocess.check_output(['dpkg-query','-W','-f=${Version}','signalpier'],text=True).strip()
        if subprocess.run(['dpkg','--compare-versions',version,'gt',current],check=False).returncode!=0:
            report('complete','SignalPier is already up to date.');return
        with tempfile.TemporaryDirectory(prefix='signalpier-update-') as work:
            package=Path(work)/'signalpier.deb';digest=hashlib.sha256();size=0
            report('installing','Downloading the SignalPier update…')
            with urlopen(Request(item['url'],headers={'User-Agent':'SignalPier-updater'}),timeout=30) as response,package.open('wb') as output:
                while block:=response.read(262144):
                    size+=len(block)
                    if size>item['bytes']:raise ValueError('Download exceeds expected size')
                    digest.update(block);output.write(block)
            if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise ValueError('Download checksum verification failed')
            for field,expected in [('Package','signalpier'),('Architecture','arm64'),('Version',version)]:
                actual=subprocess.check_output(['dpkg-deb','-f',str(package),field],text=True).strip()
                if actual!=expected:raise ValueError(f'Unexpected installer {field}')
            report('installing','Installing update. The dashboard will reconnect automatically…')
            env=dict(os.environ,DEBIAN_FRONTEND='noninteractive')
            result=subprocess.run(['apt-get','install','-y','--no-install-recommends',str(package)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=480)
            if result.returncode:raise RuntimeError('Package installation failed. Check journalctl -u signalpier-update.')
        report('complete','Update installed. Refreshing the dashboard…')
    except Exception as error:
        report('error',str(error))


if __name__=='__main__':main()
