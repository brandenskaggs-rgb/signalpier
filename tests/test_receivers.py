import ctypes
import json
import subprocess
import threading
import unittest
from unittest.mock import Mock,patch
import receivers
from app import Workbench

class ReceiverConnectionTests(unittest.TestCase):
    def library(self,count=1,code=0):
        lib=Mock();lib.rtlsdr_get_device_count.return_value=count
        lib.rtlsdr_get_device_name.return_value=b'RTL-SDR'
        def strings(index,manufacturer,product,serial):
            manufacturer.value=b'RTLSDRBlog';product.value=b'Blog V3';serial.value=b'00000001';return 0
        lib.rtlsdr_get_device_usb_strings.side_effect=strings
        def opened(pointer,index):
            if code==0: ctypes.cast(pointer,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.c_void_p(123)
            return code
        lib.rtlsdr_open.side_effect=opened
        return lib

    def test_discovery_returns_real_identifiers_without_claiming_ready(self):
        lib=self.library()
        with patch('receivers.load_library',return_value=lib): data=receivers.inspect_native()
        self.assertEqual(data['status'],'detected');self.assertEqual(data['devices'][0]['serial'],'00000001')
        lib.rtlsdr_open.assert_not_called()

    def test_connection_result_and_handle_cleanup(self):
        for code,status in [(0,'ready'),(-3,'permission_denied'),(-6,'busy'),(-4,'not_connected'),(-1,'error')]:
            with self.subTest(code=code):
                lib=self.library(code=code)
                with patch('receivers.load_library',return_value=lib): data=receivers.inspect_native(0)
                self.assertEqual(data['status'],status)
                self.assertEqual(lib.rtlsdr_close.call_count,int(code==0))

    def test_missing_driver_and_disconnected_device_are_different(self):
        with patch('receivers.load_library',side_effect=OSError()): self.assertEqual(receivers.inspect_native()['status'],'driver_missing')
        lib=self.library(count=0)
        with patch('receivers.load_library',return_value=lib): self.assertEqual(receivers.inspect_native(0)['status'],'not_connected')
        lib.rtlsdr_open.assert_not_called()

    def test_child_timeout_is_reported_and_indices_are_validated(self):
        with patch('receivers.subprocess.run',side_effect=subprocess.TimeoutExpired('test',8)):
            self.assertEqual(receivers.inspect_receiver(0)['status'],'timeout')
        for value in [-1,100,'0;bad',True]:
            with self.assertRaises(ValueError): receivers.inspect_receiver(value)

    def test_inventory_cache_and_explicit_refresh(self):
        monitor=receivers.ReceiverMonitor()
        with patch('receivers.inspect_receiver',return_value=receivers.result('not_connected')) as inspect:
            monitor.scan();monitor.scan();self.assertEqual(inspect.call_count,1)
            monitor.scan(True);self.assertEqual(inspect.call_count,2)

    def test_probe_excludes_capture_and_releases_reservation_on_failure(self):
        bench=Workbench();entered=threading.Event();release=threading.Event();errors=[]
        def probe(_):
            entered.set();release.wait(2);raise ValueError('test failure')
        def run():
            try: bench.test_receiver(0)
            except ValueError as error: errors.append(str(error))
        with patch('app.inspect_receiver',side_effect=probe):
            thread=threading.Thread(target=run);thread.start();self.assertTrue(entered.wait(1))
            self.assertTrue(bench.busy())
            with self.assertRaises(RuntimeError): bench.start({'duration':2})
            with self.assertRaises(RuntimeError): bench.test_receiver(0)
            release.set();thread.join(2)
        self.assertFalse(bench.busy());self.assertEqual(errors,['test failure'])
