"""Download a verified Windows setup and begin the user-requested upgrade."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
from urllib.request import Request,urlopen

FEED='https://brandenskaggs-rgb.github.io/signalpier/release.json'
shutdown_requested=threading.Event()
_lock=threading.Lock()
_status={'status':'idle'}

def status(): return {'supported':bool(getattr(sys,'frozen',False)),**_status}

def validate(manifest):
    version=manifest['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?',version): raise ValueError('Invalid version')
    item=manifest['windows']
    expected=f'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v{version}/SignalPier-{version}-windows-x64-Setup.exe'
    if item['url']!=expected or not re.fullmatch('[a-f0-9]{64}',item['sha256']): raise ValueError('Invalid Windows update')
    if type(item['bytes']) is not int or not 4096<item['bytes']<150_000_000: raise ValueError('Unexpected installer size')
    return item

def install():
    global _status
    temporary=None
    try:
        from updates import VERSION,version_key
        _status={'status':'installing','message':'Downloading the Windows update…'}
        with urlopen(Request(FEED,headers={'User-Agent':'SignalPier-Windows'}),timeout=15) as response: raw=response.read(100001)
        if len(raw)>100000: raise ValueError('Manifest too large')
        manifest=json.loads(raw);item=validate(manifest)
        if version_key(manifest['version'])<=version_key(VERSION): raise ValueError('No newer update is available')
        folder=Path(os.environ['LOCALAPPDATA'])/'SignalPier/updates';folder.mkdir(parents=True,exist_ok=True)
        fd,temporary=tempfile.mkstemp(prefix='setup-',suffix='.exe',dir=folder)
        digest=hashlib.sha256();size=0;header=b''
        with os.fdopen(fd,'wb') as output,urlopen(item['url'],timeout=30) as response:
            while block:=response.read(262144):
                if not header: header=block[:2]
                size+=len(block)
                if size>item['bytes']: raise ValueError('Download exceeds expected size')
                digest.update(block);output.write(block)
            output.flush();os.fsync(output.fileno())
        if size!=item['bytes'] or digest.hexdigest()!=item['sha256'] or header!=b'MZ': raise ValueError('Windows update verification failed')
        # Wait in a separate process for this running app to exit before replacing it.
        script=Path(temporary).with_suffix('.ps1')
        executable=str(Path(temporary)).replace("'","''")
        destination=str(Path(sys.executable).parent).replace("'","''")
        script.write_text("$ErrorActionPreference='Stop'\ntry { Wait-Process -Id "+str(os.getpid())+" -Timeout 45 -ErrorAction SilentlyContinue } catch {}\nif (Get-Process -Id "+str(os.getpid())+" -ErrorAction SilentlyContinue) { exit 1 }\n& '"+executable+"' '/SILENT' '/SUPPRESSMSGBOXES' '/NORESTART' '/SIGNALPIERUPDATE' '/DIR="+destination+"'\n",encoding='utf-8-sig')
        subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),close_fds=True)
        temporary=None
        _status={'status':'installing','message':'Installing update. SignalPier will close and reopen automatically.'}
        shutdown_requested.set()
    except Exception as error: _status={'status':'error','message':str(error)}
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)
        _lock.release()

def request_install():
    global _status
    if not getattr(sys,'frozen',False): raise ValueError('Install the Windows application to use automatic updates.')
    if not _lock.acquire(blocking=False): raise RuntimeError('An update is already running')
    _status={'status':'queued','message':'Starting update…'}
    threading.Thread(target=install,daemon=True).start()
