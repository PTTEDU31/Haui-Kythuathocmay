"""Include local, CSP-compatible source-reader assets with content versions."""
import hashlib
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / 'app/static'


def include_code_viewer(html):
    # Idempotent when an already published teaching page is rebuilt.
    html = re.sub(r'<link\b[^>]*href="/static/code-viewer\.css[^\"]*"[^>]*>\s*', '', html)
    html = re.sub(r'<script\b[^>]*src="/static/(?:code-viewer\.js|vendor/highlight-11\.11\.1\.min\.js)[^\"]*"[^>]*></script>\s*', '', html)
    assets = []
    for filename in ['code-viewer.css', 'vendor/highlight-11.11.1.min.js', 'code-viewer.js']:
        version = hashlib.sha256((STATIC / filename).read_bytes()).hexdigest()[:12]
        url = f'/static/{filename}?v={version}'
        assets.append(f'<link rel="stylesheet" href="{url}">' if filename.endswith('.css')
                      else f'<script src="{url}" defer></script>')
    # Optional head/body tags are used by the pinned source page.
    insertion = '</head>' if '</head>' in html else '</title>'
    markup = '\n'.join(assets) + '\n'
    return html.replace(insertion, markup + insertion if insertion == '</head>' else insertion + markup, 1)


if __name__ == '__main__':
    for filename in ['huong-dan-bao-ve.html', 'hoc-mo-hinh.html', 'huong-dan-mo-phong.html', 'huong-dan-source.html']:
        path = STATIC / filename
        path.write_text(include_code_viewer(path.read_text()))
        print(f'Updated code reader: {filename}')
