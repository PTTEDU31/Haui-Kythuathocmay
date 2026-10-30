/* Offline teaching player. Values are illustrative, never a live application trace. */
(() => {
  'use strict';
  const model = JSON.parse(document.querySelector('#presentation-data').textContent);
  const $ = selector => document.querySelector(selector);
  const diagramSelect = $('#diagram-select');
  const scenarioSelect = $('#scenario-select');
  const stage = $('#diagram-stage');
  let diagramId = 'architecture';
  let scenarioIndex = 0;
  let stepIndex = 0;
  let playing = false;
  let timer = null;
  let selectedNode = null;
  let originalViewBox = '';

  const diagram = () => model.diagrams[diagramId];
  const scenario = () => diagram().scenarios[scenarioIndex];
  const steps = () => scenario().steps;

  function stop() {
    clearTimeout(timer);
    timer = null;
    playing = false;
    $('#play').textContent = '▶ Phát';
    $('#play').setAttribute('aria-pressed', 'false');
  }

  function schedule() {
    clearTimeout(timer);
    if (!playing) return;
    timer = setTimeout(() => {
      if (stepIndex >= steps().length - 1) {
        stop();
        $('#playback-status').textContent = 'Đã hoàn tất kịch bản. Bấm Phát để chạy lại.';
        return;
      }
      showStep(stepIndex + 1);
      schedule();
    }, Number($('#speed').value) * 1000);
  }

  function valueCard(value) {
    const box = document.createElement('div');
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      box.className = 'value-list';
      for (const [key, content] of Object.entries(value)) {
        const row = document.createElement('div');
        row.className = 'value-row';
        const label = document.createElement('span');
        label.className = 'value-key';
        label.textContent = key;
        const result = document.createElement('span');
        result.className = 'value-content';
        result.textContent = typeof content === 'object' ? JSON.stringify(content, null, 2) : String(content);
        row.append(label, result);
        box.append(row);
      }
    } else {
      box.className = 'value-content';
      box.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    }
    return box;
  }

  function updateIO(step, inspecting = false) {
    $('#step-title').textContent = step.title;
    $('#step-explanation').textContent = step.explain;
    $('#function-name').textContent = step.fn || diagram().nodeLabels[step.node];
    $('#input-value').replaceChildren(valueCard(step.input));
    $('#output-value').replaceChildren(valueCard(step.output));
    $('#input-json').textContent = JSON.stringify(step.input, null, 2);
    $('#output-json').textContent = JSON.stringify(step.output, null, 2);
    $('#speaker-note').textContent = step.say || step.explain;
    window.DefenseGuide.render($('#defense-step'), step.fn || '', {mode:'offline',node:step.node,diagram:diagramId});
    $('#branch-status').textContent = inspecting ? 'Khám phá khối · ngoài bước đang phát' : (step.condition || 'Bước trong kịch bản minh họa');
    $('#branch-status').classList.toggle('is-inferred', Boolean(step.inferred));
    const refs = step.sources || diagram().sources[step.node] || [];
    $('#source-links').replaceChildren();
    for (const ref of refs) {
      const link = document.createElement('a');
      link.href = `source.html#path=${encodeURIComponent(ref.path)}&line=${ref.line}`;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = `${ref.path}:${ref.line}${ref.end_line !== ref.line ? '–' + ref.end_line : ''}`;
      $('#source-links').append(link);
    }
  }

  function focusGraph(step) {
    const svg = stage.querySelector('svg');
    const ids = step.nodes || [step.node];
    const edgeIds = step.edges || [];
    const completed = new Set(steps().slice(0, stepIndex).map(s => s.node));
    let active = null;
    for (const node of svg.querySelectorAll('[data-node-id]')) {
      const id = node.getAttribute('data-node-id');
      const current = ids.includes(id);
      node.classList.toggle('demo-active', current);
      node.classList.toggle('demo-done', !current && completed.has(id));
      node.setAttribute('aria-pressed', String(current));
      if (id === step.node) active = node;
    }
    for (const edge of svg.querySelectorAll('[data-edge-id]')) {
      edge.classList.toggle('demo-edge', edgeIds.includes(edge.getAttribute('data-edge-id')));
    }
    if ($('#follow-node').checked && active) {
      const bounds = active.getBBox();
      const [, , width, height] = originalViewBox.split(/\s+/).map(Number);
      const focusWidth = Math.min(width, Math.max(520, bounds.width + 240));
      const focusHeight = Math.min(height, Math.max(310, bounds.height + 160));
      const x = Math.max(0, Math.min(width - focusWidth, bounds.x + bounds.width / 2 - focusWidth / 2));
      const y = Math.max(0, Math.min(height - focusHeight, bounds.y + bounds.height / 2 - focusHeight / 2));
      svg.setAttribute('viewBox', `${x} ${y} ${focusWidth} ${focusHeight}`);
    } else {
      svg.setAttribute('viewBox', originalViewBox);
    }
  }

  function showStep(index) {
    stepIndex = Math.max(0, Math.min(index, steps().length - 1));
    const step = steps()[stepIndex];
    selectedNode = step;
    updateIO(step);
    focusGraph(step);
    $('#step-number').textContent = `${stepIndex + 1} / ${steps().length}`;
    $('#playback-status').textContent = playing ? 'Đang phát kịch bản minh họa' : 'Đang dừng · có thể giải thích từng bước';
    $('#previous').disabled = stepIndex === 0;
    $('#next').disabled = stepIndex === steps().length - 1;
    $('#progress').value = stepIndex;
    for (const [index, button] of [...$('#step-list').children].entries()) {
      button.classList.toggle('current', index === stepIndex);
      button.classList.toggle('completed', index < stepIndex);
      if (index === stepIndex) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    }
  }

  function selectNode(id) {
    stop();
    const found = steps().findIndex((step, index) => index >= stepIndex && step.node === id);
    const fallback = steps().findIndex(step => step.node === id);
    if (found >= 0 || fallback >= 0) {
      showStep(found >= 0 ? found : fallback);
      return;
    }
    const step = diagram().inspector[id];
    if (!step) return;
    selectedNode = step;
    updateIO(step, true);
    focusGraph(step);
    $('#playback-status').textContent = 'Đang xem riêng một khối. Bấm Tiếp để trở lại kịch bản.';
  }

  function loadScenario() {
    stop();
    $('#scenario-description').textContent = scenario().description;
    $('#progress').max = steps().length - 1;
    $('#step-list').replaceChildren();
    steps().forEach((step, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'step-item';
      button.textContent = `${String(index + 1).padStart(2, '0')}  ${step.title}`;
      button.addEventListener('click', () => { stop(); showStep(index); });
      $('#step-list').append(button);
    });
    showStep(0);
  }

  function loadDiagram() {
    stop();
    const current = diagram();
    $('#diagram-title').textContent = current.label;
    $('#original-link').href = `${diagramId}.html`;
    stage.innerHTML = current.svg;
    const svg = stage.querySelector('svg');
    originalViewBox = svg.getAttribute('viewBox');
    for (const node of svg.querySelectorAll('[data-node-id]')) {
      const id = node.getAttribute('data-node-id');
      node.setAttribute('aria-label', `Xem đầu vào và đầu ra: ${current.nodeLabels[id]}`);
      node.addEventListener('click', () => selectNode(id));
      node.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectNode(id); }
      });
    }
    scenarioSelect.replaceChildren();
    current.scenarios.forEach((item, index) => scenarioSelect.add(new Option(item.label, index)));
    scenarioIndex = 0;
    loadScenario();
  }

  function togglePlayback() {
    if (playing) { stop(); $('#playback-status').textContent = 'Đã tạm dừng để thuyết trình'; return; }
    if (stepIndex === steps().length - 1) showStep(0);
    playing = true;
    $('#play').textContent = 'Ⅱ Tạm dừng';
    $('#play').setAttribute('aria-pressed', 'true');
    showStep(stepIndex);
    schedule();
  }

  for (const [id, item] of Object.entries(model.diagrams)) diagramSelect.add(new Option(item.label, id));
  diagramSelect.value = diagramId;
  diagramSelect.addEventListener('change', () => { diagramId = diagramSelect.value; loadDiagram(); });
  scenarioSelect.addEventListener('change', () => { scenarioIndex = Number(scenarioSelect.value); loadScenario(); });
  $('#play').addEventListener('click', togglePlayback);
  $('#next').addEventListener('click', () => { stop(); showStep(stepIndex + 1); });
  $('#previous').addEventListener('click', () => { stop(); showStep(stepIndex - 1); });
  $('#restart').addEventListener('click', () => { stop(); showStep(0); });
  $('#progress').addEventListener('input', () => { stop(); showStep(Number($('#progress').value)); });
  $('#speed').addEventListener('change', schedule);
  $('#follow-node').addEventListener('change', () => focusGraph(selectedNode));
  $('#theme').addEventListener('click', () => {
    document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  });
  $('#fullscreen').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch { $('#playback-status').textContent = 'Có thể dùng F11 để mở toàn màn hình trong trình duyệt.'; }
  });
  document.addEventListener('keydown', event => {
    if (event.target.closest('input,select,textarea,button,[data-node-id],a,summary') || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === ' ') { event.preventDefault(); togglePlayback(); }
    if (event.key === 'ArrowRight') { event.preventDefault(); stop(); showStep(stepIndex + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); stop(); showStep(stepIndex - 1); }
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && playing) { stop(); $('#playback-status').textContent = 'Đã tạm dừng khi chuyển sang cửa sổ khác.'; }
  });
  loadDiagram();
})();
