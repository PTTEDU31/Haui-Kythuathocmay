/* Read-only teaching UI. Numerical snapshots are verified by build_model_lab.py. */
(() => {
  'use strict';
  const data = window.ModelLabData;
  const $ = s => document.querySelector(s);
  const node = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
  const number = v => (Math.abs(Number(v))<0.0000005?0:Number(v)).toLocaleString('en-US', {maximumFractionDigits:6});
  const names = {hoc_phi:'Học phí',hoc_bong:'Học bổng',lich_thi:'Lịch thi',diem_hoc_tap:'Điểm học tập',dang_ky_hoc_phan:'Đăng ký học phần'};
  const paragraph = (parent, text, cls) => parent.append(node('p',text,cls));
  function table(parent, headings, rows) {
    const wrap=node('div',undefined,'table-wrap'), t=node('table'), head=node('thead'), body=node('tbody'), tr=node('tr');
    headings.forEach(h=>tr.append(node('th',h)));head.append(tr);
    rows.forEach(row=>{const r=node('tr');row.forEach(value=>r.append(node('td',String(value))));body.append(r);});
    t.append(head,body);wrap.append(t);parent.append(wrap);
  }
  function chooser(parent,label,count,chosen,onchange,labels) {
    const l=node('label',label), s=node('select');
    for(let i=0;i<count;i++){const o=node('option',labels?labels[i]:`Nơ-ron ${i+1}`);o.value=String(i);s.append(o);}
    s.value=String(chosen);s.addEventListener('change',()=>onchange(Number(s.value)));l.append(s);parent.append(l);
  }
  let stage=0, hiddenIndex=0, outputIndex=0;
  for(const [index, item] of data.cases.entries()) {
    for(const selector of ['#case-select','#teacher-case-select']){const o=node('option',item.question);o.value=String(index);$(selector).append(o);}
  }
  function vectorDetails(parent,r,meta) {
    const details=node('details');details.append(node('summary',`Mở đầy đủ ${meta.dimensions} tọa độ: vector và tên từng cột`));
    paragraph(details,'x[j] là trọng số của vocabulary[j]. Thứ tự cột bắt đầu từ 0 và giữ cố định; 0 là đặc trưng không xuất hiện trong vector của câu này.');
    const pre=node('pre');pre.append(node('code','x = [\n'+r.vector.map((v,i)=>`  ${number(v)}${i<r.vector.length-1?',':''}  // x[${i}] ↔ ${meta.vocabulary[i]}`).join('\n')+'\n]'));details.append(pre);
    parent.append(details);
  }
  function renderFeedback(sample) {
    const meta=data.models.mlp,r=sample.models.mlp,architecture=$('#teacher-architecture'),panel=$('#teacher-example');
    architecture.replaceChildren();panel.replaceChildren();
    const hidden=meta.shapes.slice(0,-1).map(s=>s[1]);
    table(architecture,['Đại lượng đọc từ artifact','Giá trị','Thuộc tính kiểm tra'],[
      ['Đầu vào số',`${meta.dimensions} tọa độ`,`coefs_[0].shape[0] = ${meta.shapes[0][0]}`],
      ['Lớp ẩn',`${hidden.length} lớp; số nơ-ron: ${hidden.join(', ')}`,'hidden_layer_sizes; coefs_'],
      ['Lớp đầu ra',`${meta.classes.length} đầu ra; softmax`, `coefs_[-1].shape[1] = ${meta.shapes.at(-1)[1]}`],
      ['Các ma trận kết nối',meta.shapes.map(s=>s.join(' × ')).join('; '),'coefs_[0], coefs_[1]'],
      ['Tổng hệ số MLP',meta.parameter_count,'Tổng phần tử coefs_ và intercepts_'],
      ['Chế độ auto của ứng dụng',data.selection.selected,'reports/selection.json']
    ]);
    paragraph(architecture,'Dữ liệu đầu vào để học: 50 câu hỏi công khai có nhãn trong data/original_50.csv. Mỗi hàng gồm câu hỏi, nhãn chủ đề và split; đây là bộ câu hỏi biên soạn, không phải dữ liệu hội thoại sinh viên thực tế. Chỉ 30 câu Train dùng để fit vocabulary, IDF và trọng số; Validation dùng chọn cấu hình, Test dùng báo cáo đánh giá.');
    table(architecture,['Nhãn chủ đề','Train','Validation','Test','Tổng'],Object.entries(data.dataset_counts).map(([label,counts])=>[names[label],counts.Train,counts.Validation,counts.Test,counts.Train+counts.Validation+counts.Test]));
    paragraph(panel,'Văn bản ở giao diện: “'+sample.question+'”');
    paragraph(panel,`Sau TF-IDF: x có ${r.vector.length} tọa độ, ${r.nonzero} tọa độ khác 0. Một câu là một vector, không phải một câu dài bao nhiêu từ thì mạng có bấy nhiêu đầu vào.`,'note');
    const preview=r.features.slice(0,6).map(f=>`x[${f.index}] (“${f.term}”) = ${number(f.x)}`).join('; ');
    paragraph(panel,preview||'Không có tọa độ khác 0; tất cả token/ngram đều ngoài vocabulary.');
    const diagram=node('div',undefined,'actual-network');
    const input=node('div',undefined,'network-column');input.append(node('h4',`${meta.dimensions} đầu vào số`),node('p','x = TF-IDF(câu hỏi)'),node('p',`327 chiều cố định; ${r.nonzero} số khác 0.`));
    const middle=node('div',undefined,'network-column');middle.append(node('h4',`${hidden.length} lớp ẩn · ${hidden[0]} nơ-ron`));
    const grid=node('div',undefined,'hidden-grid');
    r.hidden.forEach((h,i)=>{const b=node('button',`h${i+1}\n${number(h)}`,h>0?'active-unit':'');b.type='button';b.setAttribute('aria-label',`Xem phép tính nơ-ron ẩn ${i+1}`);b.addEventListener('click',()=>{hiddenIndex=i;stage=2;$('#model-select').value='mlp';renderLab();$('#real-lab').scrollIntoView({block:'start'});});grid.append(b);});middle.append(grid);
    const output=node('div',undefined,'network-column');output.append(node('h4',`${meta.classes.length} đầu ra softmax`));
    const winner=r.scores.indexOf(Math.max(...r.scores));
    r.scores.forEach((p,i)=>{const line=node('p',`${names[meta.classes[i]]}: ${number(p)}${i===winner?' ← lớn nhất':''}`,i===winner?'winner':'');output.append(line);});
    diagram.append(input,middle,output);panel.append(diagram);
    paragraph(panel,'Các nơ-ron h1–h16 hiển thị giá trị sau ReLU của MLP đã lưu. Bấm một nơ-ron để mở đúng phép tính tổng có trọng số ở mục 7. Các số không phải tọa độ không gian của từ.');
    paragraph(panel,`Đầu ra số p = [${r.scores.map(number).join(', ')}] → argmax = ${winner} → nhãn “${r.predicted}” (${names[r.predicted]}).`,'formula');
    const route=sample.routes.mlp;
    paragraph(panel,`Sau khi qua route() trên kho FAQ công khai: status=${route.status}; classifier được gọi=${route.classifier_called}; nhãn classifier quyết định nhóm tìm=${route.classifier_used}.`);
    paragraph(panel,'Văn bản trả cho người dùng ở ví dụ route: “'+route.answer+'”');
    paragraph(panel,'Nội dung văn bản trên đến từ FAQ/quy tắc, không phải 5 nơ-ron đầu ra tự ghép thành câu. Trong sơ đồ này ta luôn xem MLP; mục 7 cho phép chuyển sang LinearSVC.','note');
    const scope=$('#scope-results');scope.replaceChildren();
    const model=$('#model-select').value;
    paragraph(scope,`Đối chiếu với ${model==='mlp'?'MLP':'LinearSVC'} đang chọn ở mục 7. Cột “gọi classifier trực tiếp” cố ý bỏ qua route để minh họa việc ép vào 5 nhãn.`);
    table(scope,['Câu hỏi','Gọi classifier trực tiếp','status của route','Đã gọi classifier?','Nhãn classifier quyết định nhóm tìm?','Chủ đề trả lời / FAQ'],data.cases.map(c=>{
      const routed=c.routes[model];return [c.question,names[c.models[model].predicted],routed.status,routed.classifier_called?'Có':'Không',routed.classifier_used?'Có':'Không',routed.intent?`${routed.intent_label||names[routed.intent]||routed.intent} / ${routed.faq_ids.join(', ')}`:'Không trả FAQ'];
    }));
    paragraph(scope,`Snapshot dựng lúc ${data.created_at}; kho ${data.route_source.path}, ${data.route_source.faq_count} FAQ được đưa vào chỉ mục. Không gọi generate()/Qwen và không ghi hội thoại.`,'muted');
  }
  function renderLab() {
    const sample=data.cases[Number($('#case-select').value)], model=$('#model-select').value;
    const r=sample.models[model], meta=data.models[model], panel=$('#lab-output');panel.replaceChildren();
    $('#artifact-info').textContent=`Artifact ${model}.joblib · ${meta.dimensions} đặc trưng · ${meta.classes.length} lớp · ${model==='mlp'?meta.parameter_count+' tham số; '+meta.iterations+' vòng L-BFGS đã lưu':'C='+meta.parameters.C+'; '+meta.iterations+' vòng lặp được ghi trong artifact'}.`;
    $('#snapshot-info').textContent=`Dựng lúc ${data.created_at}. SHA-256 artifact: ${meta.artifact_sha256}. Dữ liệu Train: ${data.train_size} câu. Bộ dựng bài đã kiểm tra ${data.verified_cases} lượt forward và TF-IDF với sklearn, gồm 50 câu công khai × 2 mô hình cùng ${data.cases.length} ví dụ × 2 mô hình. Các số hiển thị làm tròn; kiểm tra dùng số đầy đủ.`;
    $('#teacher-case-select').value=$('#case-select').value;
    renderFeedback(sample);
    for(const button of document.querySelectorAll('[data-stage]'))button.setAttribute('aria-pressed',String(Number(button.dataset.stage)===stage));
    $('#stage-prev').disabled=stage===0;$('#stage-next').disabled=stage===4;$('#stage-status').textContent=`Bước ${stage+1}/5`;
    if(stage===0) {
      panel.append(node('h3','1 · Chuẩn hóa và tách token'));
      paragraph(panel,'Câu gốc: '+sample.question);paragraph(panel,'Sau NFC + chữ thường + gộp khoảng trắng: '+r.normalized);
      paragraph(panel,'Token: '+r.tokens.join(' | '));
      paragraph(panel,'Các token/ngram không nằm trong từ vựng đã học: '+(r.ignored.join(' | ')||'Không có.'));
      paragraph(panel,'Analyzer tạo unigram và bigram rồi chỉ giữ những cột đã học trên Train. Từ ngoài từ vựng không được thêm cột lúc suy luận.','note');
    } else if(stage===1) {
      panel.append(node('h3','2 · Đếm → TF × IDF → chuẩn hóa L2'));
      paragraph(panel,`${r.nonzero}/${meta.dimensions} tọa độ khác 0. Chuẩn vector thô = ${number(r.raw_norm)}. Các tọa độ còn lại bằng 0.`);
      if(r.nonzero)table(panel,['Cột / đặc trưng','c','df','TF','IDF','TF×IDF','x sau L2'],r.features.map(f=>[`${f.index}: ${f.term}`,f.count,f.df,number(f.tf),number(f.idf),number(f.raw),number(f.x)]));
      else paragraph(panel,'Toàn bộ đặc trưng ngoài từ vựng: x là vector 0. Không chia cho 0. Bước sau vẫn tính được bằng bias.','note');
      paragraph(panel,'Chỉ số cột bắt đầu từ 0. c đếm lần xuất hiện trong câu đang xét, df đếm số câu Train chứa đặc trưng đó. x = (TF×IDF) / chuẩn vector thô.');
      vectorDetails(panel,r,meta);
    } else if(stage===2) {
      panel.append(node('h3',model==='mlp'?'3 · Một nơ-ron ẩn nhận những đóng góp nào?':'3 · Một bộ OvR cộng các đặc trưng như thế nào?'));
      const index=model==='mlp'?hiddenIndex:outputIndex;
      chooser(panel,model==='mlp'?'Chọn nơ-ron ẩn':'Chọn lớp để tính điểm',model==='mlp'?meta.biases[0].length:meta.classes.length,index,i=>{if(model==='mlp')hiddenIndex=i;else outputIndex=i;renderLab();},model==='mlp'?null:meta.classes.map(k=>names[k]));
      const bias=model==='mlp'?meta.biases[0][index]:meta.biases[index];
      table(panel,['Đặc trưng','xᵢ','Trọng số wᵢ','Đóng góp xᵢ×wᵢ'],r.features.map(f=>[f.term,number(f.x),number(f.weights[index]),number(f.x*f.weights[index])]));
      const sum=r.features.reduce((s,f)=>s+f.x*f.weights[index],0);
      paragraph(panel,`Tổng đóng góp = ${number(sum)}; bias = ${number(bias)}; tổng + bias = ${number(sum+bias)}.`,'formula');
      if(model==='mlp'){
        paragraph(panel,`z${index+1} = ${number(r.hidden_z[index])}; h${index+1} = max(0,z) = ${number(r.hidden[index])}. ${r.hidden_z[index]>0?'Nơ-ron đang hoạt động.':'ReLU chặn giá trị về 0.'}`);
        table(panel,['Nơ-ron','z trước ReLU','h sau ReLU'],r.hidden.map((h,i)=>[i+1,number(r.hidden_z[i]),number(h)]));
      }else paragraph(panel,`Đây là điểm “${names[meta.classes[index]]} so với phần còn lại”. Để quyết định 5 lớp, còn phải tính cả 5 điểm rồi lấy lớn nhất.`);
      paragraph(panel,'Đóng góp âm/dương là tác động trong biểu diễn và mô hình này; không diễn giải như nguyên nhân chắc chắn trong ngôn ngữ tự nhiên.');
    } else if(stage===3) {
      panel.append(node('h3',model==='mlp'?'4 · Lớp ẩn → logits → softmax':'4 · So sánh 5 điểm One-vs-Rest'));
      if(model==='mlp'){
        chooser(panel,'Chọn đầu ra để xem tổng có trọng số',meta.classes.length,outputIndex,i=>{outputIndex=i;renderLab();},meta.classes.map(k=>names[k]));
        table(panel,['Nơ-ron ẩn','hⱼ','W₂ⱼₖ','hⱼ×W₂ⱼₖ'],r.hidden.map((h,j)=>[j+1,number(h),number(meta.output_weights[j][outputIndex]),number(h*meta.output_weights[j][outputIndex])]));
        paragraph(panel,`Cộng các đóng góp và bias ${number(meta.biases[1][outputIndex])} → logit ${number(r.logits[outputIndex])}. Softmax dùng cả 5 logits, không tính độc lập từng đầu ra.`);
        table(panel,['Lớp theo classes_','Logit','exp(a−max a)','p = exp / tổng'],meta.classes.map((k,i)=>[names[k],number(r.logits[i]),number(Math.exp(r.logits[i]-Math.max(...r.logits))),number(r.scores[i])]));
        paragraph(panel,`Tổng xác suất = ${number(r.scores.reduce((a,b)=>a+b,0))}. Các giá trị này chưa được hiệu chỉnh xác suất trên dữ liệu độc lập.`);
      }else{
        table(panel,['Lớp theo classes_','wₖᵀx+bₖ'],meta.classes.map((k,i)=>[names[k],number(r.scores[i])]));
        paragraph(panel,'Có thể cả 5 số đều âm. Chọn số lớn nhất, không chọn theo trị tuyệt đối. decision_function không phải xác suất và không bắt buộc cộng thành 1.','note');
      }
    } else {
      panel.append(node('h3','5 · Argmax → chỉ số → nhãn'));
      const winner=r.scores.indexOf(Math.max(...r.scores));
      table(panel,['Chỉ số','classes_[k]','Điểm', 'Quyết định'],meta.classes.map((k,i)=>[i,k,number(r.scores[i]),i===winner?'← Lớn nhất':'']));
      paragraph(panel,`argmax = ${winner}; classes_[${winner}] = ${r.predicted} → ${names[r.predicted]}.`,'formula');
      if(!r.nonzero)paragraph(panel,'Đầu vào bằng 0 vẫn có nhãn! LinearSVC dùng bias; MLP dùng ReLU(b₁) rồi lớp đầu ra. Đây là ví dụ vì sao cần cơ chế ngoài phạm vi và kiểm tra bằng chứng riêng.','note');
      paragraph(panel,'Dừng ở nhãn chủ đề. Trong chatbot, route() chỉ dùng nhãn để thu hẹp tìm kiếm khi phù hợp; quy tắc/chủ đề tường minh/ngữ cảnh có thể ưu tiên hơn. FAQ và Qwen là các bước khác.');
      const other=model==='mlp'?'linearsvc':'mlp';paragraph(panel,`Cùng câu này, ${other==='mlp'?'MLP':'LinearSVC'} dự đoán: ${names[sample.models[other].predicted]}. Không so trực tiếp độ lớn điểm của hai mô hình để chọn mô hình thắng.`);
    }
  }
  $('#case-select').addEventListener('change',renderLab);$('#model-select').addEventListener('change',renderLab);
  $('#teacher-case-select').addEventListener('change',()=>{$('#case-select').value=$('#teacher-case-select').value;renderLab();});
  for(const b of document.querySelectorAll('[data-stage]'))b.addEventListener('click',()=>{stage=Number(b.dataset.stage);renderLab();});
  $('#stage-prev').addEventListener('click',()=>{stage=Math.max(0,stage-1);renderLab();});
  $('#stage-next').addEventListener('click',()=>{stage=Math.min(4,stage+1);renderLab();});

  function svgPart(parent, tag, attrs, text) {
    const e=document.createElementNS('http://www.w3.org/2000/svg',tag);
    for(const [key,value] of Object.entries(attrs))e.setAttribute(key,String(value));
    if(text!==undefined)e.textContent=text;
    parent.append(e);return e;
  }
  function toyNetwork(parent, x, h, p) {
    const svg=svgPart(parent,'svg',{viewBox:'0 0 320 230',class:'toy-diagram',role:'img','aria-label':'Mạng minh họa hai đầu vào, hai nơ-ron ReLU, hai đầu ra softmax. Giá trị đổi theo thanh kéo.'});
    for(let i=0;i<2;i++)for(let j=0;j<2;j++){
      svgPart(svg,'line',{x1:54,y1:70+100*i,x2:138,y2:70+100*j,class:'network-edge'});
      svgPart(svg,'line',{x1:182,y1:70+100*i,x2:266,y2:70+100*j,class:'network-edge'});
    }
    [[32,x,['x₁','x₂']],[160,h,['h₁','h₂']],[288,p,['p(A)','p(B)']]].forEach(([cx,values,labels])=>values.forEach((value,i)=>{
      svgPart(svg,'circle',{cx,cy:70+i*100,r:23,class:cx===160&&value===0?'unit inactive':'unit'});
      svgPart(svg,'text',{x:cx,y:75+i*100,'text-anchor':'middle'},value.toFixed(3));
      svgPart(svg,'text',{x:cx,y:35+i*100,'text-anchor':'middle'},labels[i]);
    }));
    svgPart(svg,'text',{x:160,y:220,'text-anchor':'middle'},'Nhân trọng số → ReLU → softmax');
  }
  function toyBoundary(parent,x1,x2) {
    const svg=svgPart(parent,'svg',{viewBox:'0 0 320 275',class:'toy-diagram',role:'img','aria-label':'Điểm x trong mặt phẳng hai đặc trưng; đường f bằng 0 và hai đường biên f bằng cộng trừ 1 của SVM minh họa.'});
    const sx=x=>36+x/1.2*260, sy=y=>232-y/1.2*196;
    svgPart(svg,'line',{x1:36,y1:232,x2:302,y2:232,class:'axis'});svgPart(svg,'line',{x1:36,y1:232,x2:36,y2:25,class:'axis'});
    for(const v of [0,.6,1.2]){
      svgPart(svg,'text',{x:sx(v),y:250,'text-anchor':'middle'},String(v));
      svgPart(svg,'text',{x:27,y:sy(v)+4,'text-anchor':'end'},String(v));
    }
    for(const level of [-1,0,1]){
      const low=Math.max(0,(.3+level)/2), high=Math.min(1.2,(1.5+level)/2);
      svgPart(svg,'line',{x1:sx(low),y1:sy(2*low-.3-level),x2:sx(high),y2:sy(2*high-.3-level),class:level===0?'boundary':'margin'});
    }
    svgPart(svg,'circle',{cx:sx(x1),cy:sy(x2),r:6,class:'sample-point'});
    svgPart(svg,'text',{x:Math.min(273,sx(x1)+12),y:Math.max(20,sy(x2)-12)},'x');
    svgPart(svg,'text',{x:305,y:271,'text-anchor':'end'},'x₁');svgPart(svg,'text',{x:14,y:18},'x₂');
    svgPart(svg,'text',{x:172,y:17,'text-anchor':'middle'},'Liền: f=0 · Đứt: f=±1');
  }
  function renderToy() {
    const x1=Number($('#toy-x1').value),x2=Number($('#toy-x2').value),y=Number($('#toy-label').value);
    $('#x1-value').textContent=number(x1);$('#x2-value').textContent=number(x2);
    const z=[x1-x2,-x1+x2],h=z.map(v=>Math.max(0,v)),a=[2*h[0]-h[1],-h[0]+2*h[1]],m=Math.max(...a);
    const es=a.map(v=>Math.exp(v-m)),p=es.map(v=>v/(es[0]+es[1])),f=2*x1-x2-.3;
    $('#toy-mlp').replaceChildren();$('#toy-svc').replaceChildren();$('#toy-gradient').replaceChildren();
    toyNetwork($('#toy-mlp'),[x1,x2],h,p);toyBoundary($('#toy-svc'),x1,x2);
    paragraph($('#toy-mlp'),`z=[${z.map(number).join(', ')}] → h=[${h.map(number).join(', ')}] → logits=[${a.map(number).join(', ')}].`);
    paragraph($('#toy-mlp'),`p(A)=${number(p[0])}; p(B)=${number(p[1])}. ${Math.abs(p[0]-p[1])<1e-12?'Hòa điểm A/B.':`Chọn ${p[0]>p[1]?'A':'B'}.`} Loss nếu nhãn đúng A: −ln(pA)=${number(-Math.log(p[0]))}.`,'formula');
    paragraph($('#toy-svc'),`f=${number(f)} → ${Math.abs(f)<1e-12?'đúng ranh giới':f>0?'dự đoán +1':'dự đoán −1'}. Khoảng cách có dấu f/√5=${number(f/Math.sqrt(5))}.`);
    paragraph($('#toy-svc'),`m=y·f=${number(y*f)}; squared hinge=${number(Math.max(0,1-y*f)**2)}. ${y*f>=1?'Đủ biên.':y*f>0?'Đúng phía nhưng còn vi phạm biên.':'Chưa đúng phía của nhãn mục tiêu.'}`,'formula');
    const d2=[p[0]-1,p[1]],d1=[(2*d2[0]-d2[1])*(z[0]>0?1:0),(-d2[0]+2*d2[1])*(z[1]>0?1:0)];
    paragraph($('#toy-gradient'),`Nhãn đúng A → y=[1,0]. δ₂=p−y=[${d2.map(number).join(', ')}]. δ₁=(δ₂W₂ᵀ)⊙ReLU′(z)=[${d1.map(number).join(', ')}].`);
    table($('#toy-gradient'),['Gradient','Theo nơ-ron 1 / đầu ra A','Theo nơ-ron 2 / đầu ra B'],[
      ['∂L/∂W₁ hàng x₁',number(x1*d1[0]),number(x1*d1[1])],['∂L/∂W₁ hàng x₂',number(x2*d1[0]),number(x2*d1[1])],
      ['∂L/∂b₁',number(d1[0]),number(d1[1])],['∂L/∂W₂ hàng h₁',number(h[0]*d2[0]),number(h[0]*d2[1])],['∂L/∂W₂ hàng h₂',number(h[1]*d2[0]),number(h[1]*d2[1])],['∂L/∂b₂',number(d2[0]),number(d2[1])]
    ]);
  }
  ['#toy-x1','#toy-x2','#toy-label'].forEach(s=>$(s).addEventListener('input',renderToy));

  const glossary = [
    ['sample','Mẫu / sample','Một quan sát dùng để học hoặc dự đoán: ở đây là một câu hỏi. Một mẫu không phải một từ trong câu.'],
    ['label','Nhãn / label, target','Giá trị mục tiêu đã biết trong Train hoặc muốn dự đoán cho câu mới; ví dụ hoc_phi. Nhãn chuỗi được sklearn ánh xạ theo classes_.'],
    ['class','Lớp / class','Một loại đầu ra của bài toán phân loại. Năm chủ đề tạo 5 lớp; số lớp khác số lớp của mạng nơ-ron.'],
    ['classification','Phân loại / classification','Học hàm ánh xạ đặc trưng sang nhãn rời rạc. Khác regression dự đoán đại lượng liên tục, như học phí cụ thể.'],
    ['recognition','Nhận dạng / pattern recognition','Suy ra loại hoặc cấu trúc từ quan sát thông qua biểu diễn đặc trưng và quy tắc quyết định. Không đồng nghĩa máy hiểu toàn bộ nội dung như người.'],
    ['supervised','Học có giám sát / supervised learning','Huấn luyện từ mẫu có nhãn mục tiêu. MLP và LinearSVC ở đây đều thuộc nhóm này.'],
    ['feature','Đặc trưng / feature','Một đại lượng mô tả mẫu. Trong TF-IDF word, một cột ứng với một từ/ngram trong từ vựng. Đặc trưng ẩn của MLP là tổ hợp học được, không còn nhất thiết mang tên một từ.'],
    ['vector','Vector','Dãy số có thứ tự; thứ tự cột phải giữ nhất quán giữa train và predict. Hoán vị cột mà không hoán vị trọng số sẽ làm sai phép tính.'],
    ['matrix','Ma trận / matrix','Bảng số theo hàng và cột. X có hàng là mẫu, cột là đặc trưng; W kết nối các tọa độ/lớp.'],
    ['dimension','Chiều / dimension','Số tọa độ của biểu diễn. 327 chiều nghĩa là mỗi câu có 327 số, không có nghĩa cần 327 câu để suy luận.'],
    ['sparse','Thưa / sparse','Phần lớn phần tử bằng 0. Dạng sparse lưu hiệu quả những vị trí khác 0; giá trị 0 ở đây là đặc trưng không được kích hoạt, không phải dữ liệu bị thiếu.'],
    ['normalization','Chuẩn hóa văn bản / text normalization','Đưa các cách biểu diễn chữ về quy ước nhất quán. NFC, viết thường và gộp khoảng trắng khác với chuẩn L2 của vector.'],
    ['token','Token','Đơn vị do bộ tách tạo ra. Với tokenizer mặc định của TfidfVectorizer, “học phí” là hai token. Token ở đây khác token của Qwen.'],
    ['ngram','N-gram, unigram, bigram','Chuỗi n đơn vị kề nhau. Word unigram có 1 token, bigram có 2 token. Char n-gram dùng ký tự và là cấu hình khác.'],
    ['vocabulary','Từ vựng / vocabulary','Ánh xạ từ đặc trưng sang chỉ số cột, được học khi fit Train. Giới hạn max_features chỉ đặt trần, không ép đủ số cột.'],
    ['tf','TF / term frequency','Tín hiệu về số lần đặc trưng xuất hiện trong một văn bản. Dự án dùng TF log: 1+ln(c) nếu c>0; không chia TF cho tổng số từ trước khi nhân IDF.'],
    ['df','DF / document frequency','Số văn bản Train có chứa đặc trưng. Một từ lặp 10 lần trong cùng câu vẫn chỉ tăng DF của câu đó một lần.'],
    ['idf','IDF / inverse document frequency','Trọng số tăng khi đặc trưng có mặt trong ít văn bản Train. Dự án dùng ln((1+n)/(1+df))+1. Hiếm không có nghĩa chắc chắn hữu ích.'],
    ['tfidf','TF-IDF','TF nhân IDF rồi chuẩn L2 ở cấu hình này. Là biểu diễn từ vựng thống kê, không phải embedding Transformer.'],
    ['l2norm','Chuẩn L2 / Euclidean norm','Căn tổng bình phương các tọa độ. Chuẩn hóa vector khác 0 về độ dài 1 làm thay đổi độ lớn, vẫn giữ hướng vector.'],
    ['oov','Ngoài từ vựng / OOV','Token/ngram không có cột trong vocabulary đã học. Không được tự thêm cột khi transform. Tất cả OOV tạo vector 0.'],
    ['embedding','Embedding','Biểu diễn số được thiết kế/học để mã hóa đặc tính của đối tượng, thường dùng dày đặc trong mạng ngôn ngữ. TF-IDF của dự án không được gọi là embedding ngữ nghĩa kiểu Transformer.'],
    ['parameter','Tham số / parameter','Giá trị được học từ Train, ví dụ trọng số và bias. IDF/từ vựng cũng là trạng thái học được của tiền xử lý.'],
    ['hyperparameter','Siêu tham số / hyperparameter','Lựa chọn cấu hình trước hoặc trong quy trình chọn mô hình: số nơ-ron, alpha, C. Không phải từng trọng số được optimizer cập nhật.'],
    ['weight','Trọng số / weight','Hệ số nhân với một đầu vào. Dấu và độ lớn cho biết tác động trong phép tính đã chọn; không tự là giải thích nhân quả.'],
    ['bias','Bias / hệ số chệch','Số hạng cộng để dịch ngưỡng/ranh giới. Khác “bias” trong đánh đổi bias–variance hay thiên lệch dữ liệu xã hội.'],
    ['dot','Tích vô hướng / dot product','Nhân các tọa độ cùng vị trí rồi cộng. wᵀx là điểm cơ bản của SVM và một phần phép tính nơ-ron.'],
    ['affine','Biến đổi affine','Phép tuyến tính cộng bias: xW+b. Thường gọi gọn là lớp tuyến tính trong phần mềm, nhưng chính xác toán học là affine khi b khác 0.'],
    ['neuron','Nơ-ron / neuron, unit','Một đơn vị lấy tổng có trọng số cộng bias rồi qua hàm kích hoạt. Không phải bản sao đầy đủ nơ-ron sinh học.'],
    ['layer','Lớp mạng / layer','Nhóm đơn vị cùng bước biến đổi. “Lớp ẩn” là lớp nằm giữa đầu vào và đầu ra; khác “lớp học phí” trong phân loại.'],
    ['activation','Hàm kích hoạt / activation','Áp dụng lên tổng z, thường tạo phi tuyến. ReLU dùng trong lớp ẩn của dự án; softmax ở đầu ra xử lý đồng thời các logits.'],
    ['relu','ReLU','Rectified Linear Unit: max(0,z). Đạo hàm 1 ở dương, 0 ở âm; chọn 0 tại 0 trong triển khai này. Không chặn đầu ra dương về 1.'],
    ['logit','Logit','Ở đây là điểm đầu ra MLP trước softmax. Không phải phần trăm, không bắt buộc có giá trị dương.'],
    ['softmax','Softmax','Chuẩn hóa một vector điểm thành các số dương tổng 1 bằng hàm exp. Argmax không đổi, độ lớn xác suất còn phụ thuộc các điểm còn lại.'],
    ['probability','Xác suất dự đoán / predicted probability','Phân phối đầu ra theo mô hình. Chưa hiệu chỉnh không nên diễn giải “100 câu có p=0.8 thì chắc 80 câu đúng” khi chưa kiểm tra thực nghiệm.'],
    ['argmax','Argmax','Vị trí của giá trị lớn nhất. Cần tra nhãn theo classes_, không giả định thứ tự lớp trong báo cáo trùng thứ tự nội bộ.'],
    ['forward','Lan truyền thuận / forward pass','Tính các giá trị đầu vào→lớp ẩn→đầu ra với tham số hiện có. Có trong cả train và inference; bản thân forward không cập nhật trọng số.'],
    ['loss','Hàm mất mát / loss','Đại lượng phạt sai lệch dự đoán so với nhãn. Dự án dùng cross-entropy cho MLP, squared hinge cho LinearSVC.'],
    ['objective','Mục tiêu tối ưu / objective','Đại lượng bộ tối ưu cố giảm: thường gồm loss tổng hợp và phạt điều chuẩn. Accuracy là chỉ số đánh giá, không phải mục tiêu khả vi đang tối ưu của MLP.'],
    ['crossentropy','Cross-entropy / log loss','Với nhãn one-hot, loss là −ln xác suất của lớp đúng. Dự đoán rất tự tin vào lớp sai bị phạt lớn.'],
    ['onehot','Mã one-hot','Vector mục tiêu có 1 tại lớp đúng và 0 ở các lớp khác. Không phải vector TF-IDF đầu vào.'],
    ['derivative','Đạo hàm riêng / partial derivative','Độ nhạy của hàm đối với một biến khi giữ các biến khác cố định. Cho biết thay rất nhỏ trọng số đó tác động tới loss ra sao.'],
    ['gradient','Gradient','Vector các đạo hàm riêng theo tham số. Chỉ hướng tăng nhanh nhất cục bộ theo chuẩn Euclid; âm gradient là hướng giảm cục bộ cơ bản.'],
    ['chainrule','Quy tắc dây chuyền / chain rule','Đạo hàm của hàm hợp bằng tích các đạo hàm phù hợp. Là cơ sở toán học của backpropagation.'],
    ['backprop','Lan truyền ngược / backpropagation','Tính gradient của mạng hiệu quả từ đầu ra về đầu vào. Khác với optimizer chọn bước thay đổi tham số.'],
    ['optimizer','Bộ tối ưu / optimizer','Thuật toán dùng mục tiêu/gradient để tìm tham số tốt hơn. L-BFGS khác SGD và Adam; không gọi tất cả là Adam.'],
    ['learningrate','Tốc độ học / learning rate','Kích thước bước trong SGD và một số bộ tối ưu. learning_rate_init của MLPClassifier không điều khiển bước L-BFGS trong cấu hình đang dùng.'],
    ['lbfgs','L-BFGS','Limited-memory Broyden–Fletcher–Goldfarb–Shanno. Quasi-Newton dùng lịch sử hữu hạn để xấp xỉ thông tin độ cong, kết hợp line search.'],
    ['hessian','Hessian','Ma trận đạo hàm bậc hai, mô tả độ cong cục bộ của mục tiêu. L-BFGS không lưu ma trận Hessian đầy đủ của toàn bộ tham số.'],
    ['epoch','Epoch, batch, iteration','Epoch thường là một lượt qua tập Train; batch là nhóm mẫu dùng trong một cập nhật; iteration là vòng lặp thuật toán. n_iter_ của L-BFGS không nên gọi là số epoch Adam.'],
    ['convergence','Hội tụ / convergence','Bộ giải thỏa tiêu chí dừng trong sai số cho phép. Chưa chứng minh chất lượng ngoài mẫu, và với MLP không bảo đảm nghiệm toàn cục.'],
    ['regularization','Điều chuẩn / regularization','Thêm ràng buộc hoặc phạt để hạn chế nghiệm quá phức tạp. L2 phạt bình phương trọng số; khác thao tác chuẩn hóa L2 từng vector đầu vào.'],
    ['alpha','Alpha của MLP','Hệ số phạt L2; sklearn chia phần phạt theo số mẫu trong cấu hình Train này. Không phải tốc độ học.'],
    ['svm','SVM / SVC','Support Vector Machine / Support Vector Classification. Học ranh giới với đánh đổi biên và lỗi. LinearSVC là một triển khai SVM tuyến tính, không phải tên đầy đủ mọi loại SVM.'],
    ['hyperplane','Siêu phẳng / hyperplane','Tập điểm wᵀx+b=0. Đường thẳng ở 2D, mặt phẳng ở 3D, siêu phẳng ở không gian cao chiều.'],
    ['margin','Biên / margin','Cần phân biệt y·f(x) là biên chức năng và y·f(x)/‖w‖ là biên hình học theo nhãn. Khoảng giữa hai mặt f=±1 là 2/‖w‖.'],
    ['softmargin','Biên mềm / soft margin','Cho phép vi phạm biên để xử lý dữ liệu không tách hoàn hảo và cân bằng độ phức tạp. Không có nghĩa ranh giới bị làm mờ thành xác suất.'],
    ['hinge','Hinge và squared hinge','Hinge=max(0,1−y·f); squared hinge bình phương giá trị này. Mẫu đúng phía vẫn có thể bị phạt nếu chưa đủ biên.'],
    ['c','C của LinearSVC','Hệ số nhân phần phạt lỗi/vi phạm trong mục tiêu SVM. Nhìn tương đối: C nhỏ thiên về điều chuẩn mạnh hơn; C lớn phạt vi phạm mạnh hơn. Không so giá trị số C với alpha như cùng đơn vị.'],
    ['supportvector','Vector hỗ trợ / support vector','Trực giác là mẫu ở sát hoặc vi phạm biên góp phần xác định ranh giới. LinearSVC không có thuộc tính support_vectors_ để liệt kê trực tiếp như SVC.'],
    ['ovr','One-vs-Rest / OvR','K bộ phân loại nhị phân cho K lớp: lớp k so với tất cả lớp còn lại. Quyết định cuối lấy điểm cao nhất giữa K bộ.'],
    ['decisionfunction','Decision function','Điểm quyết định của classifier. Với LinearSVC đa lớp OvR, một điểm cho mỗi lớp; không phải xác suất hiệu chỉnh.'],
    ['kernel','Kernel','Hàm tích vô hướng trong không gian đặc trưng, cho phép một số SVM tạo ranh giới phi tuyến mà không biểu diễn tường minh mọi chiều. LinearSVC ở đây không dùng RBF kernel.'],
    ['convex','Lồi / convex','Mục tiêu lồi có tính chất mọi cực tiểu cục bộ là toàn cục; chất lượng nghiệm số vẫn tùy điều kiện dừng. MLP nhiều lớp thường là không lồi.'],
    ['primaldual','Primal / dual','Hai dạng bài toán tối ưu liên hệ nhau. dual=auto chọn dạng bộ giải thích hợp theo cấu hình và kích thước; không phải tự chọn mô hình có accuracy Test cao nhất.'],
    ['pipeline','Pipeline','Ghép tiền xử lý và classifier thành một đối tượng fit/predict. predict tự gọi transform của bước trước, giúp nhất quán với trạng thái đã fit.'],
    ['fit','fit, transform, predict','fit học trạng thái từ dữ liệu; transform đổi biểu diễn bằng trạng thái đã học; predict suy nhãn. fit_transform thường kết hợp học và biến đổi trên Train.'],
    ['artifact','Artifact / mô hình đã lưu','Tệp chứa trạng thái pipeline, trọng số, từ vựng và metadata. Nạp joblib để suy luận khác với chạy lại train.py.'],
    ['overfitting','Overfitting / quá khớp','Mô hình học đặc thù hoặc nhiễu Train, tổng quát hóa kém. Nhiều tham số so với dữ liệu là dấu hiệu rủi ro, chưa đủ để kết luận chỉ từ số lượng.'],
    ['underfitting','Underfitting / thiếu khớp','Giả thuyết/đặc trưng/điều chuẩn chưa đủ mô tả quy luật, thường cả Train và Validation đều kém.'],
    ['generalization','Tổng quát hóa / generalization','Khả năng dự đoán trên mẫu mới từ phân phối quan tâm. Không được đo đầy đủ bằng accuracy Train.'],
    ['biasvariance','Bias–variance','Cách phân tích sai số liên quan giả thuyết hạn chế và độ nhạy với mẫu Train. “Bias” này không phải hệ số b trong wᵀx+b.'],
    ['leakage','Rò rỉ dữ liệu / data leakage','Thông tin của tập đánh giá lọt vào quá trình học/chọn mô hình. Fit vectorizer trước khi tách dữ liệu cũng là một dạng rò rỉ.'],
    ['calibration','Hiệu chỉnh xác suất / calibration','Kiểm tra/điều chỉnh để độ tin cậy dự đoán phù hợp tần suất đúng thực nghiệm. Cần quy trình và dữ liệu phù hợp; softmax tự nó không bảo đảm calibration.'],
    ['distribution','Lệch phân phối / distribution shift','Dữ liệu vận hành khác dữ liệu phát triển: chủ đề mới, cách viết mới, quy định mới. Mô hình không tự học các thay đổi chỉ vì có người chat.'],
    ['precision','Precision / độ chính xác theo dự đoán lớp','Trong các mẫu bị gán lớp k, tỷ lệ thực sự là k. Khác Accuracy trên toàn bộ tập.'],
    ['recall','Recall / độ bao phủ lớp','Trong các mẫu thật thuộc lớp k, tỷ lệ được tìm đúng. Precision cao không tự suy ra Recall cao.'],
    ['f1','F1 và Macro-F1','F1 là trung bình điều hòa của Precision và Recall; Macro-F1 trung bình F1 các lớp, mỗi lớp trọng số bằng nhau. Không phải Accuracy đổi tên.'],
    ['confusion','Ma trận nhầm lẫn / confusion matrix','Bảng số mẫu theo nhãn thật và dự đoán. Phải kiểm tra thứ tự nhãn và trục trước khi đọc số nhầm.'],
    ['cosine','Cosine similarity','Tích vô hướng chia tích độ dài vector. Khi cả hai vector có chuẩn L2 bằng 1, cosine bằng tích vô hướng. Điểm truy hồi cosine khác điểm classifier.'],
    ['retrieval','Truy hồi / retrieval','Tìm và xếp hạng FAQ phù hợp trong kho. Phân loại chỉ chọn chủ đề; sinh văn bản chỉ diễn đạt. Ba nhiệm vụ cần được phân biệt khi đánh giá.'],
  ];
  function clean(s){return s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/đ/g,'d');}
  const termNodes=[];
  for(const [id,title,description] of glossary){const article=node('article',undefined,'term');article.id='term-'+id;article.append(node('h3',title),node('p',description));$('#terms').append(article);termNodes.push({article,text:clean(title+' '+description)});}
  function filterTerms(){const q=clean($('#term-search').value);let shown=0;for(const t of termNodes){t.article.hidden=!t.text.includes(q);if(!t.article.hidden)shown++;}$('#term-count').textContent=`${shown}/${glossary.length} thuật ngữ. Có thể tìm không dấu.`;}
  $('#term-search').addEventListener('input',filterTerms);
  function termHash(){if(location.hash.startsWith('#term-')){$('#term-search').value='';filterTerms();document.getElementById(location.hash.slice(1))?.scrollIntoView({block:'start'});}}
  window.addEventListener('hashchange',termHash);

  const questions=[
    ['Em trình bày toàn bộ đường đi của câu hỏi qua classifier?','Chuẩn hóa → token/ngram → TF-IDF bằng vocabulary và IDF đã fit trên Train → vector 327 chiều → MLP hoặc LinearSVC → argmax theo classes_. Sau classifier, ứng dụng còn định tuyến và kiểm tra FAQ.'],
    ['Tại sao mô hình không nhận trực tiếp chữ?','Các thuật toán này thực hiện phép toán số. TF-IDF là phép biểu diễn câu bằng vector cố định; tên từ chỉ là ánh xạ cột.'],
    ['Hai từ đồng nghĩa có chắc tạo vector giống nhau?','Không. TF-IDF word dựa từ/ngram, không tự ánh xạ đầy đủ từ đồng nghĩa. Char n-gram của bộ truy hồi là cơ chế khác, không phải bằng chứng classifier hiểu ngữ nghĩa.'],
    ['Tại sao 327 mà không phải 500 đặc trưng?','500 là max_features. Vocabulary học được từ 30 câu Train chỉ có 327 đặc trưng được giữ.'],
    ['Vì sao dùng cùng vectorizer khi train và predict?','Phải giữ cùng ý nghĩa và thứ tự cột cùng IDF. Fit lại câu mới làm đổi không gian đầu vào so với trọng số đã học.'],
    ['Một nơ-ron ẩn tính gì?','Nhân từng xᵢ với Wᵢⱼ rồi cộng, thêm bias bⱼ thành zⱼ; lấy max(0,zⱼ) để được hⱼ.'],
    ['Bias có cần khi x bằng 0 không?','Có. LinearSVC còn điểm b; MLP còn h=ReLU(b₁), sau đó a=hW₂+b₂. Do đó x=0 vẫn có thể nhận nhãn.'],
    ['Nếu mọi lớp chỉ tuyến tính thì sao?','Hợp các biến đổi affine vẫn là affine. Cần activation phi tuyến để nhiều lớp tăng dạng hàm biểu diễn.'],
    ['Softmax và argmax khác nhau ở đâu?','Softmax trả vector tổng 1. Argmax trả vị trí lớn nhất. Có thể chọn nhãn bằng argmax logits vì softmax giữ thứ tự.'],
    ['Softmax 0.95 có bảo đảm câu trả lời đúng 95% không?','Không. Đây là xác suất theo classifier, chưa hiệu chỉnh; chỉ nói về nhãn, không chứng minh FAQ và câu trả lời đúng.'],
    ['Backpropagation có phải optimizer không?','Không. Backprop tính gradient bằng chain rule; optimizer dùng gradient để chọn thay đổi tham số. Dự án dùng L-BFGS.'],
    ['Em có tự viết ReLU, backprop và liblinear trong chatbot không?','Code huấn luyện gọi sklearn. Trang bài học viết lại phép forward và ví dụ gradient để giải thích; thuật toán phục vụ thực tế vẫn từ thư viện.'],
    ['Vì sao đạo hàm cross-entropy sau softmax là p−y?','Khi ghép đạo hàm softmax và −Σy log p theo chain rule, với tổng nhãn one-hot bằng 1, các hạng rút gọn thành pₖ−yₖ. Đây là đạo hàm theo logits, chưa phải trực tiếp theo mọi trọng số.'],
    ['max_iter=1000 có phải đã học 1000 epoch không?','Không. Là giới hạn vòng bộ tối ưu; có thể dừng sớm theo tiêu chí khác. n_iter_ của artifact phản ánh số vòng đã ghi, không phải epoch Adam.'],
    ['Alpha tăng có ý nghĩa gì?','Tăng trọng số phạt L2 tương đối của MLP, khuyến khích trọng số nhỏ hơn. Có thể giảm overfitting hoặc gây underfitting; phải chọn bằng Validation.'],
    ['SVM tối đa hóa biên như thế nào?','Giảm norm của w để tăng bề rộng 2/‖w‖ dưới quy ước f=±1, đồng thời phạt mẫu vi phạm biên trong bài toán biên mềm.'],
    ['Dự đoán đúng nhãn thì squared hinge có bằng 0 không?','Chưa chắc. Nếu 0<y·f<1 thì đúng phía nhưng còn trong biên; loss vẫn dương. Cần y·f≥1 để phần loss này bằng 0.'],
    ['C lớn có phải điều chuẩn mạnh hơn không?','Trong mục tiêu ½‖w‖²+CΣloss, C lớn nhấn mạnh phạt vi phạm hơn tương đối. Thường nói C nhỏ là điều chuẩn mạnh hơn. Không suy ra C lớn luôn tốt.'],
    ['Làm sao LinearSVC phân biệt 5 lớp?','OvR học 5 bộ nhị phân. Với câu mới tính 5 điểm, chọn lớn nhất theo classes_. Không phải chỉ xét từng điểm có dương không.'],
    ['Nếu điểm LinearSVC đều âm thì có nhãn không?','Có. argmax vẫn chọn số ít âm nhất. Không lấy trị tuyệt đối, không coi điểm là phần trăm.'],
    ['Tại sao không so 0.9 của MLP với 0.3 của SVC?','Hai loại điểm khác thang đo và ý nghĩa. So sánh chất lượng bằng cùng tập đánh giá và chỉ số phù hợp.'],
    ['Mô hình nào tốt hơn trong dự án?','Validation hòa Macro-F1, lựa chọn ứng dụng ưu tiên LinearSVC theo quy tắc đã lưu. Cả hai đúng 7/10 Test đã từng được xem; dữ liệu ít nên không kết luận mô hình nào luôn tốt hơn.'],
    ['Dùng Test để chọn C có được không?','Làm vậy Test tham gia phát triển, gây đánh giá lạc quan. Chọn trên Validation; cần đánh giá độc lập mới nếu đã xem/chỉnh theo Test cũ.'],
    ['Qwen có được học từ 50 câu không?','Không. MLP và LinearSVC được huấn luyện cho phân loại. Qwen là mô hình có sẵn được gọi để diễn đạt FAQ khi đủ điều kiện.'],
    ['Muốn cải thiện mô hình thì làm gì có cơ sở?','Bổ sung dữ liệu đại diện có nhãn, kiểm tra chất lượng/chia nhóm tránh câu gần trùng, phân tích lỗi theo lớp, đánh giá độc lập và calibration nếu cần. Sau đó mới so cấu hình/đặc trưng theo cùng quy trình.'],
  ];
  for(const [q,a] of questions){const d=node('details');d.append(node('summary',q),node('p',a));$('#viva-questions').append(d);}
  const seen=new Set();
  for(const lesson of window.HauiDefenseLessons.lessons.filter(l=>['tfidf','mlp','svc','train'].includes(l.id))){
    const d=node('details');d.append(node('summary',lesson.title));paragraph(d,lesson.implementation);
    for(const ref of lesson.refs){const key=ref.path+':'+ref.line;if(seen.has(key))continue;seen.add(key);paragraph(d,`${ref.path}:${ref.line}–${ref.end_line}`,'code-ref');const pre=node('pre');pre.append(node('code',ref.code.split('\n').map((line,i)=>`${ref.line+i}  ${line}`).join('\n')));d.append(pre);}
    $('#code-excerpts').append(d);
  }
  $('#theme').addEventListener('click',()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';});
  renderLab();renderToy();filterTerms();termHash();
})();
