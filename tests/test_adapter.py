import importlib.util
from pathlib import Path
import tempfile
import io
import json
import hashlib
import os
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('adapter', Path(__file__).parents[1] / 'runtime/amp_bo3.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
HEADER = 'num score ping xuid             name             address                  qport\n--- ----- ---- ---------------- ---------------- ------------------------ ------\n'

class AdapterTests(unittest.TestCase):
    def test_status_names_bots_and_events(self):
        text = HEADER + '0 50 33 abc123 ^2Chris With Spaces 10.0.1.2:27017 123\n1 0 0 bot0 AI bot 0\n'
        players = adapter.parse_status(text)
        self.assertEqual(players, {'abc123:0': 'Chris With Spaces'})
        self.assertEqual(adapter.player_events({}, players), ['[AMPBO3] JOIN|abc123:0|Chris With Spaces'])
        self.assertEqual(adapter.player_events(players, {}), ['[AMPBO3] LEAVE|abc123:0|Chris With Spaces'])
        self.assertEqual(adapter.player_events(players, players), [])

    def test_invalid_or_incomplete_status_is_not_empty_server(self):
        self.assertIsNone(adapter.parse_status('Server not running'))
        self.assertIsNone(adapter.parse_status(HEADER + '0 50 33 abc123 Truncated'))
        self.assertEqual(adapter.parse_status(HEADER), {})
        self.assertIsNone(adapter.parse_status('num score ping xuid name address qport\n'))

    def test_master_selection_and_private_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            password = adapter.configure(root, 'ezz', 'both')
            path = root / 'boiii_players/user/master_servers.txt'
            self.assertEqual(path.read_text().splitlines(), adapter.MASTERS['both'])
            self.assertEqual(adapter.configure(root, 'ezz', 'ezz'), password)
            self.assertEqual(path.read_text().splitlines(), adapter.MASTERS['ezz'])
            self.assertEqual(path.with_suffix('.txt.before-amp').read_text().splitlines(), adapter.MASTERS['both'])
            self.assertIn(password, (root / 'zone/amp_control.cfg').read_text())
            adapter.configure(root, 't7x', 'alterware')
            self.assertEqual(path.read_text().splitlines(), adapter.MASTERS['ezz'])

    def test_tail_skips_history_handles_partial_and_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'console.log'
            path.write_bytes(b'old session\n')
            tail = adapter.LogTail(path)
            self.assertEqual(tail.read(), [])
            with path.open('ab') as f:
                f.write(b'new')
            self.assertEqual(tail.read(), [])
            with path.open('ab') as f:
                f.write(b' line\n')
            self.assertEqual(tail.read(), ['new line'])
            path.write_bytes(b'reset\n')
            self.assertEqual(tail.read(), ['reset'])

    def test_rcon_wire_format_and_empty_response(self):
        with patch.object(adapter.socket, 'socket') as factory:
            sock = factory.return_value.__enter__.return_value
            sock.recv.side_effect = [adapter.PRINT + b'\nhello\n', adapter.socket.timeout()]
            self.assertEqual(adapter.rcon(27017, 'secret', 'status'), 'hello\n')
            sock.connect.assert_called_once_with(('127.0.0.1', 27017))
            sock.send.assert_called_once_with(b'\xff\xff\xff\xffrcon "secret" status')
        with self.assertRaises(ValueError):
            adapter.rcon(27017, 'secret', 'status\nquit')

    def test_process_exit_and_no_password_in_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'boiii.exe').touch()
            (root / 'zone').mkdir()
            (root / 'zone/amp_zombies.cfg').touch()
            with patch.object(adapter.Path, 'cwd', return_value=root), \
                 patch.object(adapter.sys, 'argv', ['amp_bo3.py', '--backend', 'ezz', '--port', '27017', '--config', 'amp_zombies.cfg']), \
                 patch.object(adapter.sys, 'stdin', io.StringIO('')), \
                 patch.object(adapter.signal, 'signal'), \
                 patch.object(adapter, 'bootstrap_ezz'), \
                 patch.object(adapter.subprocess, 'Popen') as popen:
                process = popen.return_value
                process.stdout = io.BytesIO()
                process.poll.return_value = 7
                process.returncode = 7
                self.assertEqual(adapter.main(), 7)
                argv = popen.call_args.args[0]
                self.assertIn('-noupdate', argv)
                self.assertNotIn('-nosteam', argv)
                self.assertNotIn((root / '.amp-rcon-secret').read_text().strip(), ' '.join(argv))

    def test_bootstrap_download_and_offline_reuse(self):
        data = b'<html>test</html>'
        manifest = [['data/launcher/main.html', len(data), hashlib.sha1(data).hexdigest()]]
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'WINEPREFIX': tmp}):
            with patch.object(adapter.urllib.request, 'urlopen', side_effect=[io.BytesIO(json.dumps(manifest).encode()), io.BytesIO(data)]) as fetch:
                adapter.bootstrap_ezz()
                self.assertEqual(fetch.call_count, 2)
            with patch.object(adapter.urllib.request, 'urlopen') as fetch:
                adapter.bootstrap_ezz()
                fetch.assert_not_called()

    def test_bootstrap_rejects_traversal_and_bad_hash(self):
        for manifest in ([['../outside', 1, 'a' * 40]],
                         [['data/launcher/main.html', 1, 'a' * 40]]):
            with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'WINEPREFIX': tmp}), \
                 patch.object(adapter.urllib.request, 'urlopen', side_effect=[io.BytesIO(json.dumps(manifest).encode()), io.BytesIO(b'x')]):
                with self.assertRaises(ValueError):
                    adapter.bootstrap_ezz()
                self.assertFalse((Path(tmp) / 'drive_c/users/amp/AppData/Local/boiii/data/launcher/main.html').exists())

if __name__ == '__main__':
    unittest.main()
