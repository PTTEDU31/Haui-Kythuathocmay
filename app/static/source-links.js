/* a[data-src="path:start-end"] → GitHub line link + inline snippet (built by scripts/build_source_links.py). */
document.querySelectorAll('a[data-src]').forEach(a => {
  const ref = a.dataset.src, [path, span] = ref.split(':'), [start, end] = span.split('-');
  const {base, snippets} = window.HauiSource || {};
  if (!base || !snippets[ref]) return;
  a.href = `${base}${path}#L${start}-L${end}`; a.target = '_blank'; a.rel = 'noopener';
  if (!a.textContent.trim()) a.textContent = `${path}:${start}–${end} ↗`;
  const box = document.createElement('details'), summary = document.createElement('summary');
  const wrap = document.createElement('div'), pre = document.createElement('pre');
  summary.textContent = 'Xem code tại đây'; wrap.className = 'defense-excerpt'; pre.textContent = snippets[ref];
  wrap.append(pre); box.append(summary, wrap); box.className = 'src-view';
  a.after(box);
});
