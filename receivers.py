"""RTL-SDR enumeration and explicit connection checks in a bounded child process."""
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import tempfile

MESSAGES={
 'detected':'Receiver detected. Test the connection before your first hardware capture.',
 'not_connected':'No supported RTL-SDR found. Connect the dongle to the Pi and refresh.',
 'driver_missing':'RTL-SDR driver could not load. Open the current SignalPier AppImage on 64-bit Pi OS.',
 'ready':'Connection test passed. The receiver opened and closed successfully. You can start a hardware capture.',
 'permission_denied':'USB access was denied. In Settings, enable USB receiver access, then unplug and reconnect the dongle.',
 'busy':'Another program or the TV driver is using this receiver. Stop SDR++ or other receiver software and retry.',
 'error':'The receiver could not be opened. Check its USB connection and power, then try again.',
 'timeout':'The receiver did not respond in time. Reconnect it and check the Pi power supply.',
 'checking':'Receiver check in progress.',
}

def result(status,**extra):
    message=MESSAGES[status]
    if os.environ.get('SIGNALPIER_WINDOWS'):
        message={'not_connected':'No supported RTL-SDR found. Connect it to this computer. If needed, follow Windows USB setup in Settings.',
                 'driver_missing':'The bundled RTL-SDR library could not load. Reinstall SignalPier for Windows.',
                 'permission_denied':'USB access was denied. Follow Windows USB setup in Settings, then reconnect your SDR.',
                 'timeout':'The receiver did not respond in time. Reconnect it and check its USB connection.'}.get(status,message)
    return dict(status=status,message=message,devices=[],**extra)

def load_library():
    bundled=Path(__file__).resolve().parent.parent/'usr/lib/aarch64-linux-gnu'
    if os.environ.get('SIGNALPIER_WINDOWS'):
        folder=Path(__file__).resolve().parent/'tools'
        with os.add_dll_directory(str(folder)):
            lib=ctypes.CDLL(str(folder/'rtlsdr.dll'))
    elif os.environ.get('SIGNALPIER_PORTABLE'):
        ctypes.CDLL(str(bundled/'libusb-1.0.so.0'),mode=ctypes.RTLD_GLOBAL)
        lib=ctypes.CDLL(str(bundled/'librtlsdr.so.0'))
    else:
        name=ctypes.util.find_library('rtlsdr')
        if not name: raise OSError('librtlsdr was not found')
        lib=ctypes.CDLL(name)
    lib.rtlsdr_get_device_count.restype=ctypes.c_uint32
    lib.rtlsdr_get_device_name.argtypes=[ctypes.c_uint32];lib.rtlsdr_get_device_name.restype=ctypes.c_char_p
    lib.rtlsdr_get_device_usb_strings.argtypes=[ctypes.c_uint32,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_char_p]
    lib.rtlsdr_open.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_uint32]
    lib.rtlsdr_close.argtypes=[ctypes.c_void_p]
    return lib

def inspect_native(index=None):
    try: lib=load_library()
    except (OSError,AttributeError): return result('driver_missing')
    count=int(lib.rtlsdr_get_device_count())
    if index is not None:
        if index>=count: return result('not_connected',index=index)
        handle=ctypes.c_void_p()
        code=lib.rtlsdr_open(ctypes.byref(handle),index)
        if code==0 and handle.value:
            lib.rtlsdr_close(handle)
            return result('ready',index=index)
        return result({-3:'permission_denied',-6:'busy',-4:'not_connected'}.get(code,'error'),index=index,code=code)
    devices=[]
    for i in range(min(count,100)):
        name=lib.rtlsdr_get_device_name(i) or b'RTL-SDR'
        manufacturer,product,serial=(ctypes.create_string_buffer(256) for _ in range(3))
        code=lib.rtlsdr_get_device_usb_strings(i,manufacturer,product,serial)
        decode=lambda value:value.decode('utf-8',errors='replace')
        devices.append({'index':i,'name':decode(name),'manufacturer':decode(manufacturer.value) if code==0 else '',
                        'product':decode(product.value) if code==0 else '', 'serial':decode(serial.value) if code==0 else ''})
    response=result('detected' if devices else 'not_connected',count=count)
    response['devices']=devices
    return response

def inspect_receiver(index=None):
    if index is not None and (type(index) is not int or not 0<=index<=99): raise ValueError('Choose a receiver index from 0 to 99.')
    if getattr(sys,'frozen',False) and os.name=='nt':
        with tempfile.TemporaryDirectory(prefix='signalpier-probe-') as work:
            output=Path(work)/'result.json'
            args=[sys.executable,'--receiver-probe',str(output)]+([str(index)] if index is not None else [])
            try:
                process=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
                if process.returncode: return result('error')
                return json.loads(output.read_text(encoding='utf-8'))
            except subprocess.TimeoutExpired: return result('timeout')
            except (OSError,ValueError): return result('error')
    args=[sys.executable,str(Path(__file__).resolve()),'--native']
    if index is not None:
        if type(index) is not int or not 0<=index<=99: raise ValueError('Choose a receiver index from 0 to 99.')
        args.append(str(index))
    try:
        process=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8,check=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        lines=process.stdout.decode('utf-8',errors='replace').splitlines()
        data=json.loads(lines[-1])
        if process.returncode or data.get('status') not in MESSAGES: return result('error')
        return data
    except subprocess.TimeoutExpired: return result('timeout')
    except (OSError,ValueError,IndexError): return result('error')

class ReceiverMonitor:
    def __init__(self):
        self.lock=threading.Lock();self.expires=0
        self.cached={'status':'checking','message':'Connect an RTL-SDR to the Pi, or use Demo mode.','devices':[]}

    def scan(self,force=False):
        with self.lock:
            if force or time.monotonic()>=self.expires:
                self.cached=dict(inspect_receiver(),checked_at=time.time())
                self.expires=time.monotonic()+10
            return dict(self.cached)

    def peek(self):
        return dict(self.cached)

if __name__=='__main__':
    if len(sys.argv) not in (2,3) or sys.argv[1]!='--native': raise SystemExit(2)
    index=int(sys.argv[2]) if len(sys.argv)==3 else None
    if index is not None and not 0<=index<=99: raise SystemExit(2)
    print(json.dumps(inspect_native(index)),flush=True)
