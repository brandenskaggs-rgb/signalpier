"""User-owned AppImage updates. Never runs a package manager or elevates privileges."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.request import Request, urlopen

FEED='https://brandenskaggs-rgb.github.io/signalpier/release.json'
_lock=threading.Lock()
_status={'status':'idle'}

def status():
    return {'supported':True,**_status}

def validate(manifest):
    version=manifest['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?',version):
        raise ValueError('Invalid release version')
    item=manifest['appimage']
    expected=f'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v{version}/SignalPier-{version}-aarch64.AppImage'
    if item['url']!=expected or not re.fullmatch('[a-f0-9]{64}',item['sha256']):
        raise ValueError('Invalid AppImage release')
    if type(item['bytes']) is not int or not 4096<item['bytes']<150_000_000:
        raise ValueError('Invalid AppImage size')
    return item

def install():
    global _status
    temporary=None
    try:
        _status={'status':'installing','message':'Downloading the AppImage update…'}
        from updates import VERSION, version_key
        with urlopen(Request(FEED,headers={'User-Agent':'SignalPier-AppImage'}),timeout=15) as response:
            raw=response.read(100001)
        if len(raw)>100000: raise ValueError('Manifest too large')
        manifest=json.loads(raw)
        if version_key(manifest['version'])<=version_key(VERSION):
            raise ValueError('No newer update is available')
        item=validate(manifest)
        target=Path(os.environ['SIGNALPIER_APPIMAGE'])
        fd,temporary=tempfile.mkstemp(prefix='.signalpier-update-',dir=target.parent)
        digest=hashlib.sha256();size=0;header=b''
        with os.fdopen(fd,'wb') as output,urlopen(item['url'],timeout=30) as response:
            while block:=response.read(262144):
                if not header: header=block[:64]
                size+=len(block)
                if size>item['bytes']: raise ValueError('Download exceeds expected size')
                digest.update(block);output.write(block)
            output.flush();os.fsync(output.fileno())
        if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:
            raise ValueError('Update checksum verification failed')
        if header[:6]!=b'\x7fELF\x02\x01' or header[8:11]!=b'AI\x02' or header[18:20]!=b'\xb7\x00':
            raise ValueError('Update is not an ARM64 AppImage')
        os.chmod(temporary,0o755)
        os.replace(temporary,target)
        (target.parent/'installed-version').write_text(manifest['version'])
        _status={'status':'complete','message':'Update installed. Quit SignalPier, then reopen it from your applications menu.','restart_required':True}
    except Exception as error:
        _status={'status':'error','message':str(error)}
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)
        _lock.release()

def request_install():
    global _status
    if not _lock.acquire(blocking=False): raise RuntimeError('An update is already running')
    _status={'status':'queued','message':'Starting update…'}
    threading.Thread(target=install,daemon=True).start()
