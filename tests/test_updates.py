import io
import json
import unittest
from unittest.mock import patch
from updates import UpdateChecker, version_key


class UpdateTests(unittest.TestCase):
    def feed(self,version='9.0.0',url='https://github.com/brandenskaggs-rgb/signalpier/releases/download/v9.0.0/signalpier_9.0.0_arm64.deb'):
        return io.BytesIO(json.dumps({'version':version,'installer':{'url':url,'sha256':'a'*64}}).encode())

    def test_newer_update_and_cache(self):
        checker=UpdateChecker()
        with patch('updates.urlopen',return_value=self.feed()) as request:
            self.assertTrue(checker.check()['available']);self.assertTrue(checker.check()['online'])
            self.assertEqual(request.call_count,1)

    def test_offline_does_not_break_app(self):
        with patch('updates.urlopen',side_effect=OSError('offline')):
            result=UpdateChecker().check()
        self.assertFalse(result['online']);self.assertFalse(result['available'])

    def test_same_or_older_release_does_not_prompt(self):
        with patch('updates.urlopen',return_value=self.feed('0.0.1')):
            self.assertFalse(UpdateChecker().check()['available'])

    def test_untrusted_download_is_not_advertised(self):
        with patch('updates.urlopen',return_value=self.feed(url='https://example.com/malware.deb')):
            self.assertFalse(UpdateChecker().check()['available'])

    def test_semantic_version_order(self):
        self.assertLess(version_key('0.1.0-alpha.9'),version_key('0.1.0-alpha.10'))
        self.assertLess(version_key('0.1.0-rc.1'),version_key('0.1.0'))
        with self.assertRaises(ValueError):version_key('latest')
