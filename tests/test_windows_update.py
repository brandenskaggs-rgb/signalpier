import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import windows_update as updater
from updates import UpdateChecker

class WindowsUpdateTests(unittest.TestCase):
    def manifest(self,content):
        return {'version':'9.0.0','windows':{'url':'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v9.0.0/SignalPier-9.0.0-windows-x64-Setup.exe','bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}}

    def test_windows_feed_and_manual_check_bypasses_cache(self):
        feed=self.manifest(b'MZ'+b'x'*8192);checker=UpdateChecker()
        with patch.dict(os.environ,{'SIGNALPIER_WINDOWS':'1'}),patch('updates.urlopen',side_effect=lambda *a,**k:io.BytesIO(json.dumps(feed).encode())) as fetch:
            self.assertTrue(checker.check()['available']);self.assertTrue(checker.check()['url'].endswith('Setup.exe'))
            self.assertEqual(fetch.call_count,1);checker.check(force=True);self.assertEqual(fetch.call_count,2)

    def exercise(self,tamper=False):
        content=b'MZ'+b'x'*8192;manifest=self.manifest(content)
        if tamper: manifest['windows']['sha256']='a'*64
        with tempfile.TemporaryDirectory() as directory:
            updater._lock.acquire()
            with patch.dict(os.environ,{'LOCALAPPDATA':directory}),patch.object(updater,'urlopen',side_effect=[io.BytesIO(json.dumps(manifest).encode()),io.BytesIO(content)]),patch.object(updater.subprocess,'Popen') as execute:
                updater.install()
                scripts=list(Path(directory).rglob('*.ps1'))
                if not tamper:
                    self.assertEqual(len(scripts),1)
                    self.assertIn('Wait-Process',scripts[0].read_text(encoding='utf-8-sig'))
                    self.assertIn('/SIGNALPIERUPDATE',scripts[0].read_text(encoding='utf-8-sig'))
                return execute.call_count,updater._status,updater.shutdown_requested.is_set()

    def test_verified_setup_starts_upgrade_then_requests_graceful_exit(self):
        calls,status,shutdown=self.exercise();self.assertEqual(calls,1);self.assertEqual(status['status'],'installing');self.assertTrue(shutdown)

    def test_corrupt_setup_is_not_executed_and_app_stays_open(self):
        calls,status,shutdown=self.exercise(True);self.assertEqual(calls,0);self.assertEqual(status['status'],'error');self.assertFalse(shutdown)

    def test_foreign_installer_is_rejected(self):
        data=self.manifest(b'MZ'+b'x'*8192);data['windows']['url']='https://example.com/setup.exe'
        with self.assertRaises(ValueError): updater.validate(data)

    def tearDown(self):
        updater._status={'status':'idle'};updater.shutdown_requested.clear()
