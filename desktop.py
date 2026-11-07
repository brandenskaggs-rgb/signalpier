"""AppImage desktop entry: user-owned install, menu shortcut, local dashboard."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile
import threading
import webbrowser

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
    home=data/'signalpier';home.mkdir(parents=True,exist_ok=True)
    lock=(home/'running.lock').open('a+')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        try:
            port=json.loads((home/'session.json').read_text())['port']
            if not args.no_browser: webbrowser.open(f'http://127.0.0.1:{port}')
        except (OSError,ValueError,KeyError): pass
        return
    image=Path(os.environ['APPIMAGE']).resolve()
    target=home/'SignalPier.AppImage'
    if image!=target.resolve():
        from updates import VERSION,version_key
        try: installed_version=(home/'installed-version').read_text().strip()
        except OSError: installed_version='0.0.0'
        if target.is_file() and version_key(installed_version)>=version_key(VERSION):
            lock.close()
            os.execv(str(target),[str(target),'--appimage-extract-and-run',*os.sys.argv[1:]])
        fd,temp=tempfile.mkstemp(prefix='.install-',dir=home)
        os.close(fd)
        try:
            shutil.copyfile(image,temp);os.chmod(temp,0o755);os.replace(temp,target)
            (home/'installed-version').write_text(VERSION)
        finally:
            if os.path.exists(temp): os.unlink(temp)
    os.environ['SIGNALPIER_APPIMAGE']=str(target)
    icon=home/'signalpier.svg';shutil.copyfile(Path(__file__).parent.parent/'signalpier.svg',icon)
    menus=data/'applications';menus.mkdir(parents=True,exist_ok=True)
    # Desktop-entry quoting differs from shell quoting. Escape reserved characters.
    executable=str(target).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
    (menus/'signalpier.desktop').write_text('[Desktop Entry]\nType=Application\nName=SignalPier\nComment=Radio workbench and station clock\nExec="'+executable+'" --appimage-extract-and-run\nIcon='+str(icon)+'\nTerminal=false\nCategories=Utility;HamRadio;\n')
    from app import Server
    try: server=Server(('127.0.0.1',args.port))
    except OSError: server=Server(('127.0.0.1',0))
    (home/'session.json').write_text(json.dumps({'port':server.server_port}))
    url=f'http://127.0.0.1:{server.server_port}'
    def stop(*_): threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    print('SignalPier: '+url,flush=True)
    if not args.no_browser: threading.Timer(0.3,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    finally:
        server.workbench.stop()
        if server.workbench.worker: server.workbench.worker.join(timeout=7)
        server.server_close()
        lock.close()

if __name__=='__main__': main()
