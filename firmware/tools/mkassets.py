#!/usr/bin/env python3
"""miseru の dist/box を gzip して C の配列（app/assets_gen.c）にする。
使い方: python3 tools/mkassets.py <dist/box のパス> app/assets_gen.c"""
import gzip, os, sys

MIME = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css',
        '.svg': 'image/svg+xml', '.json': 'application/json', '.png': 'image/png', '.ico': 'image/x-icon',
        '.woff2': 'font/woff2', '.webmanifest': 'application/manifest+json'}

src, out = sys.argv[1], sys.argv[2]
files = []
for root, _, names in os.walk(src):
    for n in sorted(names):
        full = os.path.join(root, n)
        rel = os.path.relpath(full, src).replace(os.sep, '/')
        files.append((rel, full))
files.sort()
total = 0
with open(out, 'w') as f:
    f.write('/* tools/mkassets.py が作ったファイル。手で直さない。元: miseru の dist/box */\n')
    f.write('#include "assets.h"\n\n')
    for i, (rel, full) in enumerate(files):
        raw = open(full, 'rb').read()
        gz = gzip.compress(raw, 9, mtime=0)
        use_gz = len(gz) < len(raw)
        data = gz if use_gz else raw
        total += len(data)
        f.write(f'/* {rel} {len(raw)} -> {len(data)} */\nstatic const uint8_t a{i}[{len(data)}] = {{\n')
        for j in range(0, len(data), 24):
            f.write(','.join(str(b) for b in data[j:j+24]) + ',\n')
        f.write('};\n')
    f.write('\nconst asset_t g_assets[] = {\n')
    for i, (rel, full) in enumerate(files):
        ext = os.path.splitext(rel)[1]
        raw_len = os.path.getsize(full)
        f.write(f'    {{"{rel}", "{MIME.get(ext, "application/octet-stream")}", a{i}, sizeof(a{i}), {1 if len(gzip.compress(open(full,"rb").read(),9,mtime=0)) < raw_len else 0}}},\n')
    f.write('};\nconst int g_nassets = %d;\n' % len(files))
print(f'{len(files)} files, {total} bytes', file=sys.stderr)
