"""Reuse the checked Archify geometry in a CSP-compatible live observer."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'scripts'))
from code_viewer_assets import include_code_viewer


def build_live():
    native = (ROOT / 'architecture.html').read_text()
    start = native.index('<svg', native.index('<div class="diagram-container"'))
    svg = native[start:native.index('</svg>', start) + 6]
    head_styles = re.findall(r'<style[^>]*>([\s\S]*?)</style>', native.split('</head>', 1)[0])
    svg_styles = re.findall(r'<style[^>]*>([\s\S]*?)</style>', svg)
    svg = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', svg)
    svg = re.sub(r' style="--step:\d+"', '', svg)
    svg = svg.replace('start() · ask() · api()', 'ask() / runLiveChat() · fetch()')
    # Font embedding is unnecessary for the observer; use the system monospace fallback.
    (ROOT / 'live-diagram.css').write_text('\n'.join(head_styles[1:] + svg_styles).rstrip() + '\n')
    template = (ROOT / 'live.template.html').read_text()
    script = (ROOT / 'live.js').read_text()
    client_line = script[:script.index('  async function runLiveChat(')].count('\n') + 1
    (ROOT / 'live.html').write_text(include_code_viewer(template.replace('__ARCHIFY_SVG__', svg).replace('__CLIENT_LINE__', str(client_line))))
    paths = ('live.html', 'live.js', 'live.css', 'live-diagram.css')
    receipt = {'mode': 'live-runtime', 'diagram_geometry': 'architecture.html',
               'original_diagram_modified': False,
               'requires': 'STUDENT_TRACE=1; GET /architecture/live; same-origin server',
               'artifacts': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}
    (ROOT / 'evidence/live-build.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    build_live()
