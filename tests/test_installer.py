import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'packaging/install-update.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_manifest_binds_version_url_size_and_checksum(self):
        valid={'version':'1.0.0','installer':{'url':'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v1.0.0/signalpier_1.0.0_arm64.deb','bytes':10,'sha256':'a'*64}}
        self.assertEqual(installer.validate_manifest(valid)[0],'1.0.0')
        alpha={'version':'0.1.0-alpha.1','installer':{**valid['installer'],'url':'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v0.1.0-alpha.1/signalpier_0.1.0-alpha.1_arm64.deb'}}
        self.assertEqual(installer.validate_manifest(alpha)[0],'0.1.0~alpha1')
        for field,value in [('url','https://example.com/test.deb'),('bytes',11_000_000),('sha256','invalid')]:
            with self.subTest(field=field),self.assertRaises(ValueError):installer.validate_manifest({**valid,'installer':{**valid['installer'],field:value}})

    def exercise(self,tamper=False):
        package=b'package-test-data';digest=hashlib.sha256(package).hexdigest()
        manifest={'version':'1.0.0','installer':{'url':'https://github.com/brandenskaggs-rgb/signalpier/releases/download/v1.0.0/signalpier_1.0.0_arm64.deb','bytes':len(package),'sha256':'b'*64 if tamper else digest}}
        def query(args,**kwargs):
            if args[0]=='dpkg-query':return '0.1.0~alpha1'
            return {'Package':'signalpier','Architecture':'arm64','Version':'1.0.0'}[args[-1]]
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp);(state/'update.request').touch()
            with patch.object(installer,'STATE',state),patch.object(installer,'urlopen',side_effect=[io.BytesIO(json.dumps(manifest).encode()),io.BytesIO(package)]),patch.object(installer.subprocess,'check_output',side_effect=query),patch.object(installer.subprocess,'run',return_value=Mock(returncode=0)) as runner:
                installer.main();result=json.loads((state/'update-status.json').read_text());commands=[call.args[0] for call in runner.call_args_list]
            return result,commands

    def test_verified_update_starts_only_fixed_package_install(self):
        result,commands=self.exercise();self.assertEqual(result['status'],'complete')
        apt=[args for args in commands if args[0]=='apt-get'];self.assertEqual(len(apt),1)
        self.assertEqual(apt[0][:4],['apt-get','install','-y','--no-install-recommends'])

    def test_tampered_download_never_runs_installer(self):
        result,commands=self.exercise(tamper=True);self.assertEqual(result['status'],'error')
        self.assertFalse(any(args[0]=='apt-get' for args in commands))
