"""Create deterministic application archives, without logs, private state or binaries."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
VERSION = (ROOT / 'VERSION').read_text().strip()
ALLOWED_DIRS = ['static', 'scripts', 'systemd', 'docs', 'packaging', 'tests']
ALLOWED_FILES = ['app.py', 'spaceweather.py', 'updates.py', 'portable_update.py', 'desktop.py', 'README.md', 'LICENSE', 'NOTICE.md', 'VERSION', 'CONTRIBUTING.md', 'SECURITY.md']


def sources():
    files = [ROOT / name for name in ALLOWED_FILES if (ROOT / name).is_file()]
    for folder in ALLOWED_DIRS:
        files.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and not any(part in ('__pycache__', 'work') for part in p.parts))
    return sorted(files)


def main():
    OUT.mkdir(exist_ok=True)
    prefix = f'signalpier-{VERSION}'
    files = sources()
    with zipfile.ZipFile(OUT / f'{prefix}-app.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(f'{prefix}/{path.relative_to(ROOT).as_posix()}', (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if path.suffix == '.sh' else 0o100644) << 16
            archive.writestr(info, path.read_bytes())
    with (OUT / f'{prefix}-app.tar.gz').open('wb') as output:
        with gzip.GzipFile(fileobj=output, mode='wb', mtime=0, filename='') as zipped:
            with tarfile.open(fileobj=zipped, mode='w') as archive:
                for path in files:
                    blob = path.read_bytes()
                    info = tarfile.TarInfo(f'{prefix}/{path.relative_to(ROOT).as_posix()}')
                    info.size = len(blob)
                    info.mode = 0o755 if path.suffix == '.sh' else 0o644
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(blob))
    hashes = []
    for path in sorted(OUT.glob(f'{prefix}-app.*')):
        sha = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        hashes.append(f'{sha}  {path.name}')
    (OUT / 'SHA256SUMS-app.txt').write_text('\n'.join(hashes) + '\n')
    print('\n'.join(hashes))


if __name__ == '__main__':
    main()
