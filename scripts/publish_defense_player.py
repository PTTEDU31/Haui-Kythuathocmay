"""Create CSP-compatible public copies of the offline player/source viewer."""
from pathlib import Path
import hashlib
import re
from code_viewer_assets import include_code_viewer

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'app/static'


def publish_page(source, name, hide_original=False):
    html = source.read_text()
    styles = re.findall(r'<style[^>]*>([\s\S]*?)</style>', html)
    html = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html)
    scripts = []

    def externalize(match):
        attrs, code = match.groups()
        if 'application/json' in attrs or 'src=' in attrs:
            return match.group(0)
        scripts.append(code.replace('source.html#path=', 'huong-dan-source.html#path='))
        return ''

    html = re.sub(r'<script([^>]*)>([\s\S]*?)</script>', externalize, html)
    css = '\n'.join(styles) + '\n'
    javascript = '\n;\n'.join(scripts) + '\n'
    css_version = hashlib.sha256(css.encode()).hexdigest()[:12]
    js_version = hashlib.sha256(javascript.encode()).hexdigest()[:12]
    stylesheet = f'<link rel="stylesheet" href="/static/{name}.css?v={css_version}">'
    executable = f'<script src="/static/{name}.js?v={js_version}" defer></script>'
    # The source explorer uses HTML's optional head/body tags.
    if '</head>' in html:
        html = html.replace('</head>', stylesheet + '\n</head>', 1)
    else:
        assert '</title>' in html
        html = html.replace('</title>', '</title>' + stylesheet, 1)
    closing = '</body>' if '</body>' in html else '</html>'
    assert closing in html
    html = html.replace(closing, executable + '\n' + closing, 1)
    html = html.replace('href="index.html"', 'href="/static/huong-dan-bao-ve.html"')
    if hide_original:
        html = html.replace('id="original-link"', 'id="original-link" hidden', 1)
    assert scripts and styles
    assert stylesheet in html and executable in html
    assert not re.search(r'<style[\s>]', html)
    assert all('application/json' in attrs or 'src=' in attrs
               for attrs in re.findall(r'<script([^>]*)>', html))
    (STATIC / f'{name}.css').write_text(css)
    (STATIC / f'{name}.js').write_text(javascript)
    (STATIC / f'{name}.html').write_text(include_code_viewer(html))
    print(f'Published /static/{name}.html with external scripts/styles.')


if __name__ == '__main__':
    publish_page(ROOT / 'docs/architecture/presentation.html', 'huong-dan-mo-phong', hide_original=True)
    publish_page(ROOT / 'docs/architecture/source.html', 'huong-dan-source')
