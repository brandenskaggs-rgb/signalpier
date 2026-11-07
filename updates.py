"""Optional update notices. No downloads or executable installation occur here."""
import json
from pathlib import Path
import re
import threading
import time
import os
from urllib.request import Request, urlopen

FEED='https://brandenskaggs-rgb.github.io/signalpier/release.json'
DOWNLOAD_PREFIX='https://github.com/brandenskaggs-rgb/signalpier/releases/download/'
VERSION=(Path(__file__).parent/'VERSION').read_text().strip()
STATE=Path('/var/lib/signalpier')


def installer_status():
    if os.environ.get('SIGNALPIER_PORTABLE'):
        from portable_update import status
        return status()
    supported=Path('/usr/lib/signalpier/install-update.py').is_file() and STATE.is_dir()
    try:
        status=json.loads((STATE/'update-status.json').read_text()[:4000])
    except (OSError,ValueError):
        status={'status':'idle'}
    if (STATE/'update.request').exists():
        status={'status':'queued','message':'Update queued…'}
    return {'supported':supported,**status}


def request_install():
    if os.environ.get('SIGNALPIER_PORTABLE'):
        from portable_update import request_install as portable_install
        return portable_install()
    status=installer_status()
    if not status['supported']:
        raise ValueError('Automatic installation is available in the Raspberry Pi .deb package.')
    if status.get('status') in ('queued','installing') or (STATE/'update.request').exists():
        raise RuntimeError('An update is already running.')
    fd=os.open(STATE/'update.request',os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    os.close(fd)


def version_key(value):
    match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?',value)
    if not match:
        raise ValueError('Unsupported version format')
    major,minor,patch,stage,sequence=match.groups()
    return (int(major),int(minor),int(patch),{'alpha':0,'beta':1,'rc':2,None:3}[stage],int(sequence or 0))


class UpdateChecker:
    def __init__(self):
        self.lock=threading.Lock()
        self.next_check=0
        self.cached={'current':VERSION,'available':False,'online':False}

    def check(self):
        with self.lock:
            if time.monotonic()<self.next_check:
                return self.cached
            try:
                with urlopen(Request(FEED,headers={'User-Agent':'SignalPier/'+VERSION}),timeout=5) as response:
                    data=response.read(100001)
                if len(data)>100000: raise ValueError('Update response too large')
                manifest=json.loads(data)
                latest=str(manifest['version'])
                item=manifest['appimage' if os.environ.get('SIGNALPIER_PORTABLE') else 'installer']
                url=str(item['url'])
                digest=str(item['sha256'])
                suffix='-aarch64.AppImage' if os.environ.get('SIGNALPIER_PORTABLE') else '_arm64.deb'
                if not url.startswith(DOWNLOAD_PREFIX) or not url.endswith(suffix):
                    raise ValueError('Unsupported download URL')
                if not re.fullmatch('[a-f0-9]{64}',digest): raise ValueError('Invalid checksum')
                newer=version_key(latest)>version_key(VERSION)
                if '-' not in VERSION and '-' in latest: newer=False
                self.cached={'current':VERSION,'latest':latest,'available':newer,'online':True,'url':url,'sha256':digest}
                self.next_check=time.monotonic()+3600
            except Exception:
                self.cached={'current':VERSION,'available':False,'online':False}
                self.next_check=time.monotonic()+60
            return self.cached
