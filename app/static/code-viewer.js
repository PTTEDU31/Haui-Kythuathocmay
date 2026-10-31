/* Shared read-only source presentation. Highlight.js is served locally. */
(() => {
  'use strict';
  const states = new WeakMap();
  const pending = new Set();
  const make = (tag, cls, text) => {
    const element = document.createElement(tag);
    if (cls) element.className = cls;
    if (text !== undefined) element.textContent = text;
    return element;
  };

  function languageFor(pre, text) {
    const label = pre.closest('figure')?.querySelector('figcaption')?.textContent
      || (pre.id === 'code' ? document.querySelector('#name')?.textContent : '')
      || (pre.id === 'source-code' ? document.querySelector('#source-label')?.textContent : '')
      || (pre.id === 'real-code' ? document.querySelector('#real-label')?.textContent : '') || '';
    const extension = label.match(/\.(py|js|json|html|css|sh)(?=[:\s]|$)/)?.[1];
    const languages = {py:'python', js:'javascript', json:'json', html:'xml', css:'css', sh:'bash'};
    if (extension) return languages[extension];
    if (pre.id === 'response-json' || /^\s*[\[{]/.test(text)) {
      try { JSON.parse(text); return 'json'; } catch (_) { /* Not JSON. */ }
    }
    if (/^x = \[/.test(text)) return 'javascript';
    if (/^\s*(?:from \w+ import|import \w+|def |class )/m.test(text)) return 'python';
    return 'plaintext';
  }

  function highlightedLines(text, language) {
    const template = document.createElement('template');
    // Only trusted highlighter output becomes markup; source text is escaped by it.
    template.innerHTML = window.hljs && language !== 'plaintext'
      ? window.hljs.highlight(text, {language, ignoreIllegals:true}).value : '';
    if (!template.content.childNodes.length) template.content.append(document.createTextNode(text));
    const lines = [document.createDocumentFragment()];
    const visit = (parent, classes = []) => {
      for (const child of parent.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) {
          child.textContent.split('\n').forEach((part, index) => {
            if (index) lines.push(document.createDocumentFragment());
            if (!part) return;
            let leaf = document.createTextNode(part);
            for (let i = classes.length - 1; i >= 0; i--) {
              const span = make('span', classes[i]);span.append(leaf);leaf = span;
            }
            lines.at(-1).append(leaf);
          });
        } else visit(child, [...classes, child.className]);
      }
    };
    visit(template.content);
    return lines;
  }

  function toolbar(pre) {
    const box = make('div', 'cv-block cv-font-normal');
    const bar = make('div', 'cv-toolbar');
    const label = make('span', 'cv-language');
    const controls = make('div', 'cv-controls');
    const status = make('span', 'cv-status');status.setAttribute('role', 'status');
    const button = (text, name, action) => {
      const b = make('button', '', text);b.type = 'button';
      b.setAttribute('aria-label', name);b.addEventListener('click', action);controls.append(b);return b;
    };
    const state = {box, label, status, raw:'', rendered:null, font:1};
    const wrap = button('Xuống dòng', 'Bật xuống dòng cho đoạn code', () => {
      const active = box.classList.toggle('cv-wrap');
      wrap.setAttribute('aria-pressed', String(active));
      wrap.setAttribute('aria-label', `${active?'Tắt':'Bật'} xuống dòng cho đoạn code`);
    });wrap.setAttribute('aria-pressed', 'false');
    const sizes = ['small','normal','large','largest'];
    const resize = delta => {
      state.font = Math.max(0, Math.min(sizes.length - 1, state.font + delta));
      sizes.forEach((size, index) => box.classList.toggle(`cv-font-${size}`, index === state.font));
      status.textContent = `Cỡ chữ ${[13,15,17,19][state.font]} px`;
    };
    button('A−', 'Giảm cỡ chữ code', () => resize(-1));
    button('A+', 'Tăng cỡ chữ code', () => resize(1));
    button('Sao chép', 'Sao chép code không kèm số dòng', async () => {
      try { await navigator.clipboard.writeText(state.raw);status.textContent = 'Đã sao chép code'; }
      catch (_) { status.textContent = 'Trình duyệt chặn sao chép. Bạn có thể chọn văn bản trong khung.'; }
    });
    bar.append(label, controls);box.append(bar);
    pre.before(box);box.append(pre, status);
    pre.classList.add('cv-pre');pre.tabIndex = 0;
    pre.setAttribute('aria-label', 'Đoạn code; cuộn ngang để xem dòng dài');
    states.set(pre, state);return state;
  }

  function enhance(pre) {
    if (!pre.isConnected || pre.closest('svg')) return;
    let state = states.get(pre);
    if (state?.rendered === pre.textContent) return;
    const sourceRows = pre.id === 'code' ? [...pre.querySelectorAll(':scope > .line')] : [];
    let raw = sourceRows.length ? sourceRows.map(row => [...row.childNodes]
      .filter(child => !child.classList?.contains('ln')).map(child => child.textContent).join('')).join('\n') : pre.textContent;
    if (!raw.trim()) { if (state) state.box.hidden = true; return; }
    state ||= toolbar(pre);state.box.hidden = false;
    let firstLine = 1;
    if (pre.closest('.defense-excerpt')) {
      firstLine = Number(raw.match(/^(\d+)  /)?.[1] || 1);
      raw = raw.replace(/^\d+  /gm, '');
    } else if (pre.dataset.firstLine) {
      firstLine = Number(pre.dataset.firstLine);
    } else if (pre.id === 'source-code') {
      firstLine = Number(document.querySelector('#source-label')?.textContent.match(/:(\d+)/)?.[1] || 1);
    }
    state.raw = raw;
    const language = languageFor(pre, raw);
    state.label.textContent = ({python:'Python',javascript:'JavaScript',xml:'HTML',plaintext:'Văn bản',bash:'Shell'})[language] || language.toUpperCase();
    state.status.textContent = 'Giữ thụt dòng · Vuốt ngang để xem dòng dài';
    // Excerpts can start inside a nested block: remove only shared leading spaces
    // for display. Copying still returns the original source with its indentation.
    const indent = !sourceRows.length ? Math.min(...raw.split('\n').filter(line => line.trim())
      .map(line => line.match(/^ */)[0].length)) : 0;
    const display = indent ? raw.replace(new RegExp(`^ {${indent}}`, 'gm'), '') : raw;
    const fragments = highlightedLines(display, language);
    if (sourceRows.length) {
      sourceRows.forEach((row, i) => {
        const number = row.querySelector('.ln');number.classList.add('cv-number');
        const text = make('span', 'cv-text');text.append(fragments[i]);
        row.replaceChildren(number, text);row.classList.add('cv-line');
      });
    } else {
      const code = make('code', 'cv-code');
      fragments.forEach((fragment, i) => {
        const row = make('span', 'cv-line');
        const number = make('span', 'cv-number', String(firstLine + i));number.setAttribute('aria-hidden', 'true');
        const text = make('span', 'cv-text');text.append(fragment);row.append(number, text);code.append(row);
      });
      pre.replaceChildren(code);
    }
    state.rendered = pre.textContent;
    // The source explorer scrolls before highlighting changes the line height.
    // Re-center its selected line once the final layout has been applied.
    sourceRows.find(row => row.classList.contains('selected'))?.scrollIntoView({block:'center'});
  }

  function queue(element) {
    if (!(element instanceof Element)) return;
    const pre = element.closest('pre');
    if (pre) pending.add(pre);
    element.querySelectorAll('pre').forEach(item => pending.add(item));
  }
  document.querySelectorAll('pre').forEach(enhance);
  new MutationObserver(records => {
    for (const record of records) {
      queue(record.target.nodeType === Node.TEXT_NODE ? record.target.parentElement : record.target);
    }
    if (pending.size) { const items = [...pending];pending.clear();items.forEach(enhance); }
  }).observe(document.body, {childList:true, subtree:true, characterData:true});
})();
