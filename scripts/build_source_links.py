"""Embed source ranges referenced by data-src="path:start-end" in hoc-mo-hinh.html.

Writes app/static/source-snippets.js; links point to the same lines on GitHub,
pinned to the current commit so line numbers stay valid. Re-run after editing code.
"""
import json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/PTTEDU31/Haui-Kythuathocmay'
PAGE = ROOT/'app/static/hoc-mo-hinh.html'

commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
snippets = {}
for ref in sorted(set(re.findall(r'data-src="([^"]+)"', PAGE.read_text()))):
    path, span = ref.split(':')
    start, end = map(int, span.split('-'))
    # Must match the committed blob, otherwise GitHub line anchors drift.
    assert not subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', path], cwd=ROOT).returncode, f'{path} has uncommitted changes'
    lines = (ROOT/path).read_text(encoding='utf-8').splitlines()
    assert end <= len(lines), ref
    snippets[ref] = '\n'.join(f'{n}  {lines[n-1]}' for n in range(start, end+1))
out = ROOT/'app/static/source-snippets.js'
out.write_text('window.HauiSource=' + json.dumps(dict(base=f'{REPO}/blob/{commit}/', snippets=snippets), ensure_ascii=False) + ';\n')
print(len(snippets), 'snippets @', commit[:7])
