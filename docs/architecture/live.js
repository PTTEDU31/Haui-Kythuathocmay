/* Observe real NDJSON events. No synthetic execution steps or delayed playback. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const nodes = {web:'browser',main:'api',db:'db',engine:'engine',llm:'provider'};
  const names = {web:'Trình duyệt',main:'API Python',db:'SQLite',engine:'Engine',llm:'Provider AI'};
  const records = new Map();
  let busy = false;
  let selected = null;
  let originalViewBox = $('#graph svg').getAttribute('viewBox');
  let observedTrace = null;
  let observedFailed = false;
  let observerAbort = null;
  let observerVersion = 0;

  function resetTrace() {
    records.clear();selected=null;
    $('#timeline').replaceChildren();$('#event-count').textContent='0 lời gọi';
    $('#answer').textContent='Đang xử lý…';$('#answer-sources').replaceChildren();$('#response-json').textContent='';
    $('#follow-events').checked=true;
    for (const element of $('#graph').querySelectorAll('[data-node-id]')) {
      element.classList.remove('selected','observed');
      element.setAttribute('aria-pressed','false');
    }
    $('#selected-title').textContent='Chờ sự kiện runtime';$('#function-name').textContent='';
    $('#timing').textContent='Đang chờ hàm bắt đầu.';
    $('#input-value').textContent='Chưa có dữ liệu.';$('#output-value').textContent='Chưa có dữ liệu.';
    $('#source-label').textContent='Mã nguồn';$('#source-code').textContent='';
    window.DefenseGuide.render($('#defense-step'), '', {mode:'live'});
  }

  function observerStatus(message, failed=false) {
    $('#observer-status').textContent=message;
    $('#observer-status').classList.toggle('failed',failed);
  }

  function receiveObserved(event) {
    if (event.event==='observer_ready') {
      observerStatus('Đang nghe chat web · cùng phiên trình duyệt. Mở tab chat và gửi câu hỏi.');
      return;
    }
    if (event.event==='heartbeat') return;
    if (event.event==='observer_overflow') throw new Error('Mất sự kiện vì trang nhận quá chậm; cần gửi lượt hỏi mới sau khi kết nối lại.');
    // A direct trace request owns this inspector until it completes.
    if (busy) return;
    if (event.event==='trace') {
      resetTrace();observedTrace=event.trace_id;observedFailed=false;
      $('#question').value=event.question || '';
    }
    // Concurrent requests have separate IDs. Display the newest observed request only.
    if (!observedTrace || event.trace_id!==observedTrace) return;
    receive(event);
    if (event.event==='request_error') observedFailed=true;
    if (event.event==='done' && !observedFailed) {
      setStatus(`Đã trace chat web thật · ${records.size} lời gọi. Chọn từng lời gọi để xem input/output.`);
    }
  }

  async function listenToWebChat() {
    const version=++observerVersion;
    observerAbort?.abort();
    if (!$('#observe-chat').checked) {observerStatus('Đã tắt nghe chat web.');return;}
    while ($('#observe-chat').checked && version===observerVersion) {
      const controller=new AbortController();observerAbort=controller;
      let reader;
      try {
        observerStatus('Đang nối kênh chat web…');
        const response=await fetch('/api/chat/trace/events',{method:'POST',credentials:'same-origin',signal:controller.signal});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        reader=response.body.getReader();
        const decoder=new TextDecoder();let buffer='';
        while (true) {
          const {value,done}=await reader.read();
          buffer+=decoder.decode(value || new Uint8Array(),{stream:!done});
          let newline;
          while ((newline=buffer.indexOf('\n'))>=0) {
            const line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);
            if (line.trim()) receiveObserved(JSON.parse(line));
          }
          if (done) throw new Error('Kênh quan sát bị ngắt.');
        }
      } catch (error) {
        if (version!==observerVersion) return;
        observerStatus(`Chưa nghe được chat web: ${error.message} Đang nối lại; không phát lại sự kiện đã mất.`,true);
        observedTrace=null;
      } finally {
        controller.abort();
        if (reader) reader.releaseLock();
      }
      await new Promise(resolve=>setTimeout(resolve,2000));
    }
  }

  function setStatus(message, failed = false) {
    $('#connection-status').textContent = message;
    $('#connection-status').classList.toggle('failed', failed);
  }

  function values(value) {
    const list = document.createElement('div');
    list.className = 'value-list';
    const entries = value && typeof value === 'object' && !Array.isArray(value) ? Object.entries(value) : [['Giá trị', value]];
    for (const [key, content] of entries) {
      const row = document.createElement('div');
      row.className = 'value-row';
      const label = document.createElement('span');
      label.className = 'value-key';
      label.textContent = key;
      const text = document.createElement('div');
      text.className = 'value-content';
      text.textContent = typeof content === 'object' ? JSON.stringify(content, null, 2) : String(content);
      row.append(label, text);list.append(row);
    }
    return list;
  }

  function focusGraph(record) {
    const activeId = nodes[record.node];
    const observed = new Set([...records.values()].map(item => nodes[item.node]));
    for (const element of $('#graph').querySelectorAll('[data-node-id]')) {
      element.classList.toggle('observed', observed.has(element.dataset.nodeId));
      element.classList.toggle('selected', element.dataset.nodeId === activeId);
      element.setAttribute('aria-pressed', String(element.dataset.nodeId === activeId));
    }
    const svg = $('#graph svg');
    const active = svg.querySelector(`[data-node-id="${activeId}"]`);
    if ($('#follow-node').checked && active) {
      const b = active.getBBox();
      const [ox,oy,w,h] = originalViewBox.split(/\s+/).map(Number);
      const fw = Math.min(w, Math.max(520, b.width + 230));
      const fh = Math.min(h, Math.max(310, b.height + 160));
      const x = Math.max(ox,Math.min(ox+w-fw,b.x+b.width/2-fw/2));
      const y = Math.max(oy,Math.min(oy+h-fh,b.y+b.height/2-fh/2));
      svg.setAttribute('viewBox',`${x} ${y} ${fw} ${fh}`);
    } else svg.setAttribute('viewBox',originalViewBox);
  }

  function selectRecord(record) {
    selected = record;
    $('#selected-title').textContent = names[record.node] || record.node;
    $('#function-name').textContent = record.function;
    const origin = record.origin === 'browser' ? 'trình duyệt' : 'server';
    const state = record.error ? 'Lỗi' : record.finished ? 'Đã hoàn tất' : 'Đang chạy';
    $('#timing').textContent = `${state} · ${origin} · ${record.at || ''} · t+${record.elapsed_ms.toFixed(3)} ms${record.finished ? ' · mất ' + record.duration_ms.toFixed(3) + ' ms' : ''}`;
    $('#input-value').replaceChildren(values(record.input));
    $('#output-value').replaceChildren(values(record.error || (record.finished ? record.output : 'Đang chạy… chưa có output.')));
    const source = record.source;
    $('#source-label').textContent = source ? `${source.path}:${source.line || '?'}${source.end_line ? '–'+source.end_line : ''} · mã nguồn hiện tại` : 'Mã nguồn';
    // Live code is read at runtime, so link to main rather than a pinned commit.
    const github = $('#source-github');
    github.hidden = !source?.path;
    if (source?.path) github.href = `https://github.com/PTTEDU31/Haui-Kythuathocmay/blob/main/${source.path}#L${source.line || 1}${source.end_line ? '-L' + source.end_line : ''}`;
    $('#source-code').textContent = source?.code || 'Tham chiếu tới vị trí gọi ở trên. Đây là thao tác I/O tại call site.';
    window.DefenseGuide.render($('#defense-step'), record.function, {mode:'live',record});
    for (const item of records.values()) item.button.classList.toggle('selected',item === record);
    focusGraph(record);
  }

  function renderRow(record) {
    record.button.classList.toggle('running', !record.finished);
    record.button.classList.toggle('error', Boolean(record.error));
    record.button.querySelector('.event-name').textContent = `${record.parent_id ? '↳ ' : ''}${record.function}`;
    record.button.querySelector('.event-time').textContent = record.error ? 'Lỗi' : record.finished ? `${record.duration_ms.toFixed(3)} ms` : 'Đang chạy…';
    $('#event-count').textContent = `${records.size} lời gọi`;
  }

  function receive(event) {
    if (event.event === 'trace') { setStatus(`Đang chạy ${event.origin==='web-chat'?'chat web ':''}thật · trace ${event.trace_id}`);return; }
    if (event.event === 'heartbeat' || event.event === 'done') return;
    if (event.event === 'result') { showAnswer(event.result);return; }
    if (event.event === 'request_error') {
      setStatus(`Lỗi HTTP ${event.status_code}: ${event.detail}`,true);
      $('#answer').textContent = `Lượt hỏi thất bại: ${event.detail}`;
      return;
    }
    if (event.event === 'start') {
      const record = {...event, origin:event.origin || 'server', finished:false};
      const button = document.createElement('button');
      button.type='button';button.className='event-row';
      const label=document.createElement('span');label.className='event-name';
      const duration=document.createElement('span');duration.className='event-time';
      button.append(label,duration);record.button=button;
      button.addEventListener('click',()=>{$('#follow-events').checked=false;selectRecord(record);});
      records.set(record.span_id,record);$('#timeline').append(button);renderRow(record);
      if ($('#follow-events').checked) { selectRecord(record);$('#timeline').scrollTop=$('#timeline').scrollHeight; }
    } else if (event.event === 'end' || event.event === 'error') {
      const record = records.get(event.span_id);
      if (!record) return;
      Object.assign(record,{finished:true,duration_ms:event.duration_ms,output:event.output,error:event.error});
      renderRow(record);
      if ($('#follow-events').checked || selected === record) selectRecord(record);
    }
  }

  function showAnswer(result) {
    $('#answer').textContent=result.answer;
    $('#response-json').textContent=JSON.stringify(result,null,2);
    $('#answer-sources').replaceChildren();
    for (const source of result.sources || []) {
      const url = new URL(source.url);
      if (url.protocol !== 'https:') continue;
      const link=document.createElement('a');link.href=url.href;link.textContent=source.title;
      link.target='_blank';link.rel='noopener noreferrer';$('#answer-sources').append(link);
    }
  }

  async function runLiveChat(event) {
    event.preventDefault();
    if (busy) return;
    const question=$('#question').value.trim();
    if (!question) return;
    busy=true;$('#run').disabled=true;observedTrace=null;resetTrace();
    setStatus('Đang gửi câu hỏi đến ứng dụng…');
    const body={question,use_ai:$('#use-ai').checked};
    const started=performance.now();
    const clientCode=runLiveChat.toString();
    const clientLine=Number(document.body.dataset.clientLine);
    const browserSource={path:'docs/architecture/live.js',line:clientLine,end_line:clientLine+clientCode.split('\n').length-1,code:clientCode};
    receive({event:'start',span_id:'browser-request',node:'web',function:'runLiveChat() → fetch()',input:body,source:browserSource,origin:'browser',elapsed_ms:0,at:new Date().toISOString()});
    let reader;
    let finalResult=null;
    let terminalError=null;
    let completed=false;
    try {
      // Ordinary bootstrap establishes the HttpOnly visitor cookie before the streamed request.
      const bootstrap=await fetch('/api/bootstrap',{credentials:'same-origin'});
      if (!bootstrap.ok) throw new Error(`Bootstrap HTTP ${bootstrap.status}`);
      const response=await fetch('/api/chat/trace',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if (!response.ok) {const text=await response.text();throw new Error(`HTTP ${response.status}: ${text}`);}
      reader=response.body.getReader();
      const decoder=new TextDecoder();
      let buffer='';
      while (true) {
        const {value,done}=await reader.read();
        buffer+=decoder.decode(value || new Uint8Array(),{stream:!done});
        let newline;
        while ((newline=buffer.indexOf('\n'))>=0) {
          const line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);
          if (!line.trim()) continue;
          const item=JSON.parse(line);
          if (item.event==='result') finalResult=item.result;
          if (item.event==='request_error') terminalError=item;
          if (item.event==='done') completed=true;
          receive(item);
        }
        if (done) break;
      }
      if (!completed || (!finalResult && !terminalError)) throw new Error('Luồng trace bị ngắt trước khi hoàn tất. Không tự gửi lại để tránh ghi trùng hội thoại.');
      const duration_ms=performance.now()-started;
      if (terminalError) {
        receive({event:'error',span_id:'browser-request',duration_ms,error:{status_code:terminalError.status_code,detail:terminalError.detail}});
      } else {
        receive({event:'end',span_id:'browser-request',duration_ms,output:finalResult});
        setStatus(`Đã hoàn tất · ${records.size} lời gọi · ${duration_ms.toFixed(1)} ms tại trình duyệt · API ${finalResult.latency_ms} ms. Chọn từng lời gọi để thuyết trình.`);
      }
    } catch (error) {
      receive({event:'error',span_id:'browser-request',duration_ms:performance.now()-started,error:{message:error.message}});
      setStatus(error.message,true);
    } finally {
      if (reader) reader.releaseLock();
      busy=false;$('#run').disabled=false;
    }
  }

  $('#trace-form').addEventListener('submit',runLiveChat);
  $('#observe-chat').addEventListener('change',listenToWebChat);
  window.addEventListener('pagehide',()=>{observerVersion++;observerAbort?.abort();});
  window.addEventListener('pageshow',event=>{if(event.persisted && $('#observe-chat').checked)listenToWebChat();});
  $('#follow-node').addEventListener('change',()=>{if(selected)focusGraph(selected);});
  $('#follow-events').addEventListener('change',()=>{if($('#follow-events').checked && records.size)selectRecord([...records.values()].at(-1));});
  for (const node of $('#graph').querySelectorAll('[data-node-id]')) {
    const choose=()=>{
      const record=[...records.values()].reverse().find(item=>nodes[item.node]===node.dataset.nodeId);
      $('#follow-events').checked=false;
      if (record) selectRecord(record);
      else {
        selected=null;node.classList.remove('selected');
        for(const other of $('#graph').querySelectorAll('.selected'))other.classList.remove('selected');
        node.classList.add('selected');
        $('#selected-title').textContent='Chưa quan sát khối này';$('#function-name').textContent=node.dataset.nodeId;
        $('#timing').textContent='Không có sự kiện runtime từ khối này trong lượt hỏi hiện tại.';
        $('#input-value').textContent='Chưa thu được input.';$('#output-value').textContent='Chưa thu được output.';
        $('#source-label').textContent='Mã nguồn';$('#source-code').textContent='Không gán dữ liệu minh họa cho khối chưa được quan sát.';
        window.DefenseGuide.render($('#defense-step'), '', {mode:'live'});
      }
    };
    node.addEventListener('click',choose);
    node.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}});
  }
  $('#theme').addEventListener('click',()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';});
  $('#fullscreen').addEventListener('click',async()=>{
    try {if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}
    catch {setStatus('Dùng F11 nếu trình duyệt không cho phép toàn màn hình.');}
  });
  if(location.protocol==='file:') {
    setStatus('Trace thật cần ứng dụng đang chạy. Mở http://127.0.0.1:8088/architecture/live sau khi bật STUDENT_TRACE=1.',true);
  } else {
    fetch('/api/bootstrap',{credentials:'same-origin'}).then(response=>{
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      $('#run').disabled=false;setStatus('Đã kết nối · sẵn sàng gửi câu hỏi và trace thật.');
      listenToWebChat();
    }).catch(error=>setStatus(`Chưa kết nối ứng dụng: ${error.message}`,true));
  }
})();
