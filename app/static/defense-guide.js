/* Flowchart-to-code teaching layer. Runtime evidence remains in the trace UI. */
(() => {
  'use strict';
  const lessons = window.HauiDefenseLessons.lessons;
  const byId = new Map(lessons.map(lesson => [lesson.id, lesson]));
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function resolve(hint, context) {
    if (byId.has(context.lesson)) return context.lesson;
    const node = context.node || '';
    const diagram = context.diagram || '';
    const routing = {
      input:'normalize',rules:'rules',topics:'rules',multiple:'rules','multiple-exit':'rules',
      'rules-out-exit':'rules','rules-greeting-exit':'rules',vague:'evidence','vague-exit':'evidence',
      classify:'classify',global:'search',category:'classify',ranked:'search',enough:'evidence',
      'enough-exit':'evidence',conflict:'evidence','conflict-exit':'evidence',lexical:'evidence',
      'lexical-exit':'evidence',answer:'persist'
    };
    if (diagram === 'routing' && routing[node]) return routing[node];
    if (diagram === 'research-training' && ['train','pipe','disk'].includes(node)) return 'train';
    if (diagram === 'knowledge-admin') return 'approval';
    if (diagram === 'startup' && node !== 'web') return 'startup';
    if (diagram === 'modules' && node === 'text') return 'normalize';
    if (diagram === 'modules' && node === 'model-tools') return 'train';
    if (diagram === 'modules' && node === 'tests') return 'evaluate';
    if (hint.includes('SELECT history')) return 'history';
    if (hint.includes('INSERT messages')) return 'persist';
    if (hint.includes('evidence_matches')) return 'evidence';
    if (hint.includes('Engine.classify')) {
      const model = context.record?.output?.model;
      return model === 'MLPClassifier' ? 'mlp' : model === 'LinearSVC' ? 'svc' : 'classify';
    }
    if (hint.includes('Engine.search')) return 'search';
    if (hint.includes('Engine.generate')) return 'generate';
    if (hint.includes('httpx.Client.post')) return 'provider';
    if (hint.includes('Engine.route')) return 'routing';
    if (hint.includes('normalize')) return 'normalize';
    if (hint.includes('Engine.__init__') || hint.includes('rebuild') || hint.includes('lifespan') || hint.includes('init_db')) return 'startup';
    if (hint.includes('scripts/train') || hint.includes('Pipeline.fit') || hint.includes('joblib.dump')) return 'train';
    if (hint.includes('message()') || node === 'db') return 'persist';
    if (['provider','llm'].includes(node)) return 'provider';
    if (node === 'models') return 'startup';
    if (node === 'train') return 'train';
    if (hint.includes('chat(') || hint.includes('runLiveChat') || hint.includes('ask(') || ['browser','web','main','api'].includes(node)) return 'request';
    return null;
  }

  function runtimeNote(record) {
    if (!record) return 'Chưa chọn lời gọi. Gửi câu hỏi rồi chọn một sự kiện để đối chiếu với bước lưu đồ.';
    if (record.error) return 'Lời gọi này phát sinh lỗi. Xem lỗi thật ở Output; nội dung phương pháp bên dưới không khẳng định nhánh thành công đã chạy.';
    if (!record.finished) return 'Lời gọi đang chạy; chưa có Output cuối để kết luận nhánh thực thi.';
    const output = record.output;
    if (record.function.includes('classify') && output === null) return 'Lời gọi phân loại đã kết thúc với null: không có kết quả mô hình được dùng ở bước này (ví dụ chế độ chỉ truy hồi).';
    if (output?.routing) {
      const route = output.routing;
      return `Kết quả thật: ${output.status}. routing.reason=${route.reason}; classifier_used=${route.classifier_used}. ${route.classifier_used ? 'Nhãn mô hình đã quyết định nhóm tìm kiếm.' : 'Không kết luận nhãn mô hình đã quyết định nhóm tìm kiếm.'}`;
    }
    if (record.function.includes('evidence_matches')) return `Kết quả kiểm tra thật: ${String(output)}. Đây là kiểm tra theo quy tắc từ vựng/năm học.`;
    if (output?.generation) return `AI trong kết quả thật: used=${output.generation.used}; reason=${output.generation.reason ?? 'không có'}. Xem sự kiện HTTP riêng để biết provider có được gọi không.`;
    if (output?.model) return `Mô hình thực sự trả kết quả: ${output.model}; nhãn=${output.intent}; loại điểm=${output.score_type}. Nội bộ sklearn không được trace từng phép tính.`;
    return 'Đã quan sát lời gọi này. Input/Output ở bảng trace là dữ liệu thật; giải thích phương pháp bên dưới là chú giải code, không phải các sự kiện runtime bổ sung.';
  }

  function render(container, hint = '', context = {}) {
    if (!container) return;
    container.replaceChildren();
    const id = resolve(hint, context);
    container.dataset.lessonId = id || '';
    container.append(el('h2', 'defense-heading', 'Đối chiếu lưu đồ với code'));
    const state = context.mode === 'live' ? runtimeNote(context.record)
      : context.mode === 'offline' ? 'Đang xem kịch bản minh họa offline. Các đoạn code dưới đây chụp từ checkout hiện tại; Input/Output của kịch bản vẫn là ví dụ theo snapshot đã ghi.'
      : 'Bài hướng dẫn theo mã nguồn. Không chạy mô hình, không tạo hội thoại khi đọc hoặc đổi bài.';
    container.append(el('p', 'defense-state', state));
    if (!id) {
      container.append(el('p', '', 'Chưa có bài đối chiếu riêng cho khối này. Không gán một phương pháp hay dữ liệu giả cho khối chưa được ánh xạ.'));
      const link = el('a', '', 'Mở hướng dẫn bảo vệ đầy đủ ↗');
      link.href = '/static/huong-dan-bao-ve.html';
      link.target = '_blank';link.rel = 'noopener';container.append(link);
      return;
    }
    const lesson = byId.get(id);
    container.append(el('h3', 'defense-title', lesson.title));
    for (const [label, value] of [
      ['Lưu đồ viết gì?', lesson.flow],
      ['Phương pháp sử dụng', lesson.method],
      ['Code triển khai như thế nào?', lesson.implementation]
    ]) {
      const section = el('section', 'defense-part');
      section.append(el('h4', '', label), el('p', '', value));container.append(section);
    }
    const source = el('details', 'defense-source');
    source.open = true;
    source.append(el('summary', '', 'Chỉ vào đoạn code này khi cô hỏi'));
    for (const ref of lesson.refs) {
      const figure = el('figure', 'defense-excerpt');
      const caption = el('figcaption', '', `${ref.path}:${ref.line}–${ref.end_line} · `);
      const github = el('a', '', 'Mở trên GitHub ↗');
      github.href = window.HauiDefenseLessons.github+ref.path+'#L'+ref.line+'-L'+ref.end_line;github.target = '_blank';github.rel = 'noopener';
      caption.append(github);figure.append(caption);
      const pre = el('pre', '');
      const code = el('code', '');
      code.textContent = ref.code.split('\n').map((line, index) => `${ref.line + index}  ${line}`).join('\n');
      pre.append(code);figure.append(pre);source.append(figure);
    }
    container.append(source);
    const say = el('section', 'defense-say');
    say.append(el('h4', '', 'Cách trả lời vấn đáp'), el('p', '', lesson.say));container.append(say);
    const qa = el('details', 'defense-question');
    qa.append(el('summary', '', 'Cô hỏi tiếp: ' + lesson.qa.question), el('p', '', lesson.qa.answer));container.append(qa);
    container.append(el('p', 'defense-caution', lesson.caution));
  }

  function initializeGuide() {
    const list = document.querySelector('[data-defense-list]');
    const panel = document.querySelector('[data-defense-guide]');
    if (!list || !panel) return;
    const buttons = new Map();
    const select = id => {
      if (!byId.has(id)) id = 'request';
      render(panel, '', {lesson:id,mode:'guide'});
      for (const [key, button] of buttons) button.setAttribute('aria-pressed', String(key === id));
    };
    for (const group of [...new Set(lessons.map(item => item.group))]) {
      list.append(el('h2', '', group));
      for (const lesson of lessons.filter(item => item.group === group)) {
        const button = el('button', 'defense-choice', lesson.title);
        button.type = 'button';button.dataset.lessonId = lesson.id;
        button.setAttribute('aria-pressed', 'false');
        button.addEventListener('click', () => {location.hash = lesson.id;select(lesson.id);});
        buttons.set(lesson.id, button);list.append(button);
      }
    }
    window.addEventListener('hashchange', () => select(location.hash.slice(1)));
    select(location.hash.slice(1));
    document.querySelector('[data-defense-theme]')?.addEventListener('click', () => {
      document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    });
  }

  window.DefenseGuide = {render};
  initializeGuide();
})();
