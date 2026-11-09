"""Windows desktop entry point; also hosts the isolated receiver-probe process."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
import webbrowser

def data_directory():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'SignalPier'

def main():
    os.environ['SIGNALPIER_WINDOWS']='1'
    tools=Path(__file__).resolve().parent/'tools'
    os.environ['PATH']=str(tools)+os.pathsep+os.environ.get('PATH','')
    if len(sys.argv)>2 and sys.argv[1]=='--receiver-probe':
        from receivers import inspect_native
        index=int(sys.argv[3]) if len(sys.argv)>3 else None
        if index is not None and not 0<=index<=99: raise ValueError('Invalid receiver index')
        Path(sys.argv[2]).write_text(json.dumps(inspect_native(index)),encoding='utf-8')
        return
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args();args.no_browser=args.no_browser or os.environ.get('SIGNALPIER_NO_BROWSER')=='1';home=data_directory();home.mkdir(parents=True,exist_ok=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p];kernel.CreateMutexW.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    mutex=kernel.CreateMutexW(None,False,'Local\\SignalPierDesktop')
    if not mutex: raise ctypes.WinError(ctypes.get_last_error())
    existing=ctypes.get_last_error()==183
    try:
        if existing:
            for _ in range(15):
                try:
                    port=json.loads((home/'session.json').read_text())['port']
                    if not args.no_browser: webbrowser.open(f'http://127.0.0.1:{port}')
                    return
                except (OSError,ValueError,KeyError): time.sleep(.2)
            return
        from app import Server
        from windows_update import shutdown_requested
        port=args.port
        if port==8765:
            try: port=int(json.loads((home/'session.json').read_text())['port'])
            except (OSError,ValueError,KeyError): pass
        try: server=Server(('127.0.0.1',port))
        except OSError: server=Server(('127.0.0.1',0))
        (home/'session.json').write_text(json.dumps({'port':server.server_port,'pid':os.getpid()}))
        def watch_update():
            shutdown_requested.wait();server.shutdown()
        threading.Thread(target=watch_update,daemon=True).start()
        if not args.no_browser: threading.Timer(.3,lambda:webbrowser.open(f'http://127.0.0.1:{server.server_port}')).start()
        try: server.serve_forever()
        finally:
            server.workbench.stop()
            if server.workbench.worker: server.workbench.worker.join(timeout=7)
            server.server_close()
    finally: kernel.CloseHandle(mutex)

if __name__=='__main__':
    try: main()
    except Exception:
        error=traceback.format_exc()
        try:
            home=data_directory();home.mkdir(parents=True,exist_ok=True);(home/'startup-error.log').write_text(error,encoding='utf-8')
            if '--receiver-probe' not in sys.argv and '--no-browser' not in sys.argv:
                ctypes.windll.user32.MessageBoxW(None,'SignalPier could not start. Details were saved to:\n'+str(home/'startup-error.log'),'SignalPier',0x10)
        finally: raise SystemExit(1)
