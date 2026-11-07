import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import portable_update as updater

class PortableUpdateTests(unittest.TestCase):
    def exercise(self,tamper=False):
        binary=bytearray(8192);binary[:6]=b'\x7fELF\x02\x01';binary[8:11]=b'AI\x02';binary[18:20]=b'\xb7\x00'
        manifest={'version':'9.0.0','appimage':{'url':'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v9.0.0/SignalPier-9.0.0-aarch64.AppImage','bytes':len(binary),'sha256':'a'*64 if tamper else hashlib.sha256(binary).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'SignalPier.AppImage';target.write_bytes(b'original')
            updater._lock.acquire()
            with patch.dict(os.environ,{'SIGNALPIER_APPIMAGE':str(target)}),patch.object(updater,'urlopen',side_effect=[io.BytesIO(json.dumps(manifest).encode()),io.BytesIO(binary)]):
                updater.install()
            self.assertFalse(updater._lock.locked())
            self.assertFalse(list(Path(directory).glob('.signalpier-update-*')))
            if not tamper: self.assertEqual((target.parent/'installed-version').read_text(),'9.0.0')
            return target.read_bytes(),updater.status()

    def test_verified_appimage_replaces_installed_file_and_requires_restart(self):
        data,status=self.exercise();self.assertEqual(data[:4],b'\x7fELF');self.assertTrue(status['restart_required']);self.assertEqual(status['status'],'complete')

    def test_tampering_keeps_original_appimage(self):
        data,status=self.exercise(True);self.assertEqual(data,b'original');self.assertEqual(status['status'],'error')

    def test_manifest_rejects_foreign_url(self):
        with self.assertRaises(ValueError):
            updater.validate({'version':'9.0.0','appimage':{'url':'https://example.com/a.AppImage','bytes':8192,'sha256':'a'*64}})

    def tearDown(self): updater._status={'status':'idle'}
