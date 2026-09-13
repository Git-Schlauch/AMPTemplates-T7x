import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('upgrade', REPO / 'scripts/Upgrade-Instance.py')
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)

class UpgradeTests(unittest.TestCase):
    def test_preserves_settings_and_unrelated_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            instance = Path(tmp)
            (instance / 'GenericModule.kvp').write_text(
                'App.RootDir=./bo3-t7x/\nApp.BaseDirectory=./bo3-t7x/server/\n'
                'App.AppSettings={"ZmServerName":"My server","ServerConfig":"amp_zombies.cfg","ZmJoinPassword":"private"}\n'
                'App.Ports=[{"Port":27019}]\n', encoding='utf-8')
            files = upgrade.prepare(instance, REPO)
            kvp = dict(line.split('=', 1) for line in files['GenericModule.kvp'].splitlines())
            values = json.loads(kvp['App.AppSettings'])
            self.assertEqual(values['ZmJoinPassword'], 'private')
            self.assertEqual(values['ZmServerName'], 'My server')
            self.assertEqual(values['ServerBackend'], 't7x')
            self.assertEqual(kvp['App.Ports'], '[{"Port":27019}]')
            self.assertEqual(kvp['App.ExecutableLinux'], '/usr/bin/python3')
            self.assertIsInstance(json.loads(kvp['App.UpdateSources']), list)
            self.assertFalse((instance / 'metaconfig.json').exists())

    def test_rejects_other_instance_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            instance = Path(tmp)
            (instance / 'GenericModule.kvp').write_text('App.RootDir=./minecraft/\n')
            with self.assertRaises(ValueError):
                upgrade.prepare(instance, REPO)

if __name__ == '__main__':
    unittest.main()
