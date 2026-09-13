"""Run from an unpacked repository on Ubuntu, as amp, while target instance is stopped."""
import argparse
import datetime
import json
from pathlib import Path
import shutil

def prepare(instance, repo):
    kvp_path = instance / 'GenericModule.kvp'
    original = kvp_path.read_text(encoding='utf-8-sig')
    current = dict(line.split('=', 1) for line in original.splitlines() if '=' in line)
    if current.get('App.RootDir') != './bo3-t7x/' or current.get('App.BaseDirectory') != './bo3-t7x/server/':
        raise ValueError('Not the expected BO3 instance layout; no changes made')
    template = dict(line.split('=', 1) for line in (repo / 'bo3-t7x.kvp').read_text(encoding='utf-8-sig').splitlines() if '=' in line)
    defaults = json.loads(template['App.AppSettings'])
    defaults.update(json.loads(current.get('App.AppSettings', '{}')))
    selected = ['App.ExecutableLinux', 'App.LinuxCommandLineArgs', 'App.CommandLineArgs',
                'App.UseLinuxIOREDIR', 'App.ExitMethod', 'App.ExitTimeout', 'App.ExitString',
                'App.HasWriteableConsole', 'App.HasReadableConsole', 'App.AdminMethod',
                'Console.UserJoinRegex', 'Console.UserLeaveRegex', 'Meta.ConfigVersion',
                'Meta.ExtraContainerPackages']
    replacements = {key: template[key] for key in selected}
    replacements['App.AppSettings'] = json.dumps(defaults, ensure_ascii=False, separators=(',', ':'))
    updates = json.loads((repo / 'bo3-t7xupdates.json').read_text(encoding='utf-8-sig'))
    replacements['App.UpdateSources'] = json.dumps(updates, separators=(',', ':'))
    lines = []
    for line in original.splitlines():
        key = line.split('=', 1)[0]
        if key in replacements:
            lines.append(key + '=' + replacements.pop(key))
        else:
            lines.append(line)
    lines += [key + '=' + value for key, value in replacements.items()]
    files = {'GenericModule.kvp': '\n'.join(lines) + '\n'}
    for src, dst in [('bo3-t7xconfig.json', 'configmanifest.json'),
                     ('bo3-t7xmetaconfig.json', 'metaconfig.json')]:
        text = (repo / src).read_text(encoding='utf-8-sig')
        json.loads(text)
        files[dst] = text
    files['bo3-t7x/server/UnrankedServer/amp_bo3.py'] = (repo / 'runtime/amp_bo3.py').read_text(encoding='utf-8')
    return files

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance-dir', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Write after preview; instance must be stopped')
    args = parser.parse_args()
    instance = args.instance_dir.resolve(strict=True)
    repo = Path(__file__).resolve().parents[1]
    files = prepare(instance, repo)
    for name in files:
        print('Update:', name)
    if not args.apply:
        print('Preview only. Existing setting values and ports are preserved.')
        return
    backup = instance / ('amp-bo3-backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(mode=0o700)
    for name in files:
        target = instance / name
        if target.exists():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    for name, text in files.items():
        target = instance / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.v5-new')
        temp.write_text(text, encoding='utf-8', newline='\n')
        temp.chmod(0o600)
        temp.replace(target)
    print('Backup:', backup)
    print('Restart instance, select backend, run Update, then start game server.')

if __name__ == '__main__':
    main()
