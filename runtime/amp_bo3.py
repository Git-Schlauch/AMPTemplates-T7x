"""AMP process adapter: Wine child, log tail, UDP RCON and player reconciliation."""
import argparse
import os
from pathlib import Path
import queue
import re
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time

MASTERS = {
    'ezz': ['master.ezz.lol:20810', 'm.ezz.lol:20810'],
    'alterware': ['server.alterware.dev:20810'],
    'both': ['master.ezz.lol:20810', 'm.ezz.lol:20810', 'server.alterware.dev:20810'],
}
PRINT = b'\xff\xff\xff\xffprint'
ROW = re.compile(r'^\s*(\d+)\s+(-?\d+)\s+(\d+|CNCT|ZMBI)\s+([0-9a-fA-F]+|bot\d+)\s+(.+?)\s+((?:\d{1,3}\.){3}\d{1,3}:\d+|loopback|bot)\s+\d+\s*$')

def emit(message):
    print(message, flush=True)

def clean_name(name):
    name = re.sub(r'\^[0-9]', '', name)
    return ''.join(c for c in name if c.isprintable()).strip().replace('|', '_') or 'Unnamed'

def parse_status(text):
    """Only accept complete recognized tables; failures must not imply zero players."""
    lines = text.replace('\x00', '').splitlines()
    header = next((i for i, line in enumerate(lines)
                   if re.search(r'num\s+score\s+ping\s+xuid\s+name\s+address\s+qport', line)), None)
    if header is None or not any(re.match(r'^\s*---\s+-----', line) for line in lines[header + 1:]):
        return None
    players = {}
    for line in lines[header + 1:]:
        if not line.strip() or re.match(r'^\s*---', line):
            continue
        match = ROW.match(line)
        if match:
            slot, _, ping, uid, name, address = match.groups()
            if uid.startswith('bot') or address == 'bot' or ping in ('CNCT', 'ZMBI'):
                continue
            players[uid.lower() + ':' + slot] = clean_name(name)
        elif line.strip():
            # Unknown/truncated row/footer: retain last known list, report unsupported format.
            return None
    return players

def player_events(previous, current):
    events = []
    for uid, name in previous.items():
        if current.get(uid) != name:
            events.append(f'[AMPBO3] LEAVE|{uid}|{name}')
    for uid, name in current.items():
        if previous.get(uid) != name:
            events.append(f'[AMPBO3] JOIN|{uid}|{name}')
    return events

def rcon(port, password, command, timeout=1.5):
    if any(c in command for c in '\r\n\x00') or len(command.encode('utf-8')) > 3000:
        raise ValueError('Command must be one line, at most 3000 UTF-8 bytes')
    packet = b'\xff\xff\xff\xffrcon ' + ('"' + password + '" ' + command).encode('utf-8')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(('127.0.0.1', port))  # Never sends admin credentials to a masterserver.
        sock.settimeout(timeout)
        sock.send(packet)
        chunks = []
        while len(chunks) < 64:
            try:
                data = sock.recv(65535)
            except socket.timeout:
                break
            if data.startswith(PRINT):
                payload = data[len(PRINT):]
                if payload[:1] in (b'\n', b' '):
                    payload = payload[1:]
                chunks.append(payload.rstrip(b'\x00'))
                sock.settimeout(0.2)
        if not chunks:
            raise TimeoutError('No RCON response')
        return b''.join(chunks).decode('utf-8', errors='replace')

def write_private(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
    temp.replace(path)
    path.chmod(0o600)

def configure(root, backend, preset):
    if backend == 'ezz':
        master_file = root / 'boiii_players/user/master_servers.txt'
        if master_file.exists() and not master_file.with_suffix('.txt.before-amp').exists():
            write_private(master_file.with_suffix('.txt.before-amp'), master_file.read_text(encoding='utf-8'))
        write_private(master_file, '\n'.join(MASTERS[preset]) + '\n')
    # Dedicated administration password, generated once per instance, never an argv/env value.
    secret_path = root / '.amp-rcon-secret'
    if secret_path.exists():
        password = secret_path.read_text(encoding='ascii').strip()
        if not re.fullmatch(r'[a-f0-9]{64}', password):
            raise ValueError('Invalid .amp-rcon-secret; restore it or move it aside while stopped')
    else:
        password = secrets.token_hex(32)
        write_private(secret_path, password + '\n')
    write_private(root / 'zone/amp_control.cfg', f'set rcon_password "{password}"\nset logfile "2"\n')
    return password

class LogTail:
    def __init__(self, path):
        self.path = path
        self.identity = None
        self.position = 0
        self.pending = b''
        if path.exists():
            st = path.stat()
            self.identity = (st.st_dev, st.st_ino)
            self.position = st.st_size  # Do not replay old sessions on every start.

    def read(self):
        try:
            st = self.path.stat()
            identity = (st.st_dev, st.st_ino)
            if identity != self.identity or st.st_size < self.position:
                self.position, self.pending = 0, b''
            self.identity = identity
            with self.path.open('rb') as stream:
                stream.seek(self.position)
                data = stream.read(262144)
                self.position = stream.tell()
        except FileNotFoundError:
            return []
        lines = (self.pending + data).split(b'\n')
        self.pending = lines.pop()[-262144:]
        return [line.decode('utf-8', errors='replace').rstrip('\r') for line in lines]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', choices=('t7x', 'ezz'), default='t7x')
    parser.add_argument('--masters', choices=tuple(MASTERS), default='ezz')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--config', choices=('amp_zombies.cfg', 'server.cfg', 'server_zm.cfg', 'server_cp.cfg'), required=True)
    parser.add_argument('--mod', default='')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or any(c in args.mod for c in '\r\n\x00"'):
        parser.error('Invalid port or mod folder')
    root = Path.cwd()
    executable = 'boiii.exe' if args.backend == 'ezz' else 't7x.exe'
    if not (root / executable).is_file() or not (root / 'zone' / args.config).is_file():
        parser.error('Executable or selected configuration missing. Run AMP Update first.')
    password = configure(root, args.backend, args.masters)
    tail = LogTail(root / 'identities/dedicatedpc/console_mp.log')
    commands = queue.Queue(maxsize=100)
    stopping = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopping.set())

    def stdin_reader():
        for line in sys.stdin:
            line = line.strip()
            if line.lower() in ('quit', 'exit'):
                stopping.set()
                break
            if line:
                try:
                    commands.put_nowait(line)
                except queue.Full:
                    emit('[AMPBO3] Command queue full; command discarded')

    threading.Thread(target=stdin_reader, daemon=True).start()
    argv = ['/usr/bin/wine', executable, '-dedicated', '-headless']
    if args.backend == 'ezz':
        argv += ['-noupdate']
    argv += ['+set', 'fs_game', args.mod, '+set', 'net_port', str(args.port),
             '+set', 'logfile', '2', '+exec', args.config, '+exec', 'amp_control.cfg']
    emit(f'[AMPBO3] Starting {args.backend}; master selection: {args.masters if args.backend == "ezz" else "T7x built-in"}')
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)

    def output_reader():
        for raw in process.stdout:
            text = raw.decode('utf-8', errors='replace').rstrip().replace(password, '[REDACTED]')
            emit('[WINE] ' + text)

    threading.Thread(target=output_reader, daemon=True).start()
    previous = {}
    next_poll, next_command, next_warning = time.monotonic() + 10, 0, time.monotonic() + 60
    try:
        while process.poll() is None and not stopping.is_set():
            for line in tail.read():
                emit('[GAME] ' + line.replace(password, '[REDACTED]'))
            now = time.monotonic()
            if now >= next_command:
                command = None
                try:
                    command = commands.get_nowait()
                except queue.Empty:
                    pass
                if command is not None:
                    try:
                        response = rcon(args.port, password, command)
                        for line in response.splitlines():
                            emit('[RCON] ' + line.replace(password, '[REDACTED]'))
                    except (OSError, TimeoutError, ValueError):
                        emit('[AMPBO3] No command reply; execution unknown. Not retried automatically.')
                    next_command = time.monotonic() + 0.75
                elif now >= next_poll:
                    try:
                        players = parse_status(rcon(args.port, password, 'status'))
                        if players is None:
                            raise ValueError('Unrecognized status format')
                        for event in player_events(previous, players):
                            emit(event)
                        previous = players
                    except (OSError, TimeoutError, ValueError):
                        if now >= next_warning:
                            emit('[AMPBO3] Player query unavailable; keeping last known list. Check map startup and RCON status format.')
                            next_warning = now + 60
                    next_poll = time.monotonic() + 10
                    next_command = time.monotonic() + 0.75
            time.sleep(0.1)
    finally:
        if process.poll() is None:
            try:
                rcon(args.port, password, 'quit')
            except (OSError, TimeoutError):
                pass
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for event in player_events(previous, {}):
            emit(event)
    return process.returncode if not stopping.is_set() else 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        emit('[AMPBO3] Startup failed: ' + str(error))
        sys.exit(1)
