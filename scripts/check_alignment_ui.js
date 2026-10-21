'use strict';
// Component smoke test of the experiment renderer, without a browser or sockets.
// DOM stubs cannot verify CSS/layout; host browser QA is still required.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'app/static/app.js'),'utf8');
const report=JSON.parse(fs.readFileSync(path.join(root,'reports/experiments.json'),'utf8'));
const elements=new Map();
const $=selector=>{
 if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',disabled:false,value:''});
 return elements.get(selector);
};
const requests=[];
const context={$,Date,JSON,String,api:async(url,options)=>{
 if(url==='/api/experiments')return {...report,faq_evaluation:JSON.parse(fs.readFileSync(path.join(root,'reports/faq-evaluation.json'),'utf8'))};
 assert.equal(url,'/api/experiments/route');
 const body=JSON.parse(options.body);requests.push(body);
 return {status:'answered',answer:'<img src=x onerror=alert(1)> Nội dung có nguồn.',intent_label:'Học phí',sources:[{id:'FAQ-004'}],retrieval_score:.4715,
  routing:{reason:'classifier',classifier_used:true},
  classification:{intent:'hoc_phi',model:body.model_mode==='mlp'?'MLPClassifier':'LinearSVC',score_type:body.model_mode==='mlp'?'predict_proba':'decision_function',scores:{hoc_phi:.7},note:'Chưa hiệu chỉnh'}};
}};
vm.createContext(context);
const esc=source.slice(source.indexOf('const esc='),source.indexOf('const icon='));
const renderer=source.slice(source.indexOf('async function loadExperiments()'),source.indexOf('async function loadAdmin()'));
vm.runInContext(esc+'const pct=v=>(v*100).toFixed(1)+"%";\n'+renderer,context);
(async()=>{
 await context.loadExperiments();
 const html=$('#experiment-content').innerHTML;
 assert(html.includes(report.evaluation_status));
 assert(html.includes('327 / 500'));
 assert.equal((html.match(/class="cm-table"/g)||[]).length,2);
 for(const mode of ['auto','mlp','linearsvc','retrieval'])assert(html.includes(`value="${mode}"`));
 assert(html.includes('Chỉ số từng nhãn'));
 assert(html.includes('9 / 13') && html.includes('10 / 13'));
 assert(html.includes('Test đã từng')||html.includes('Test đã từng được xem'));
 $('#research-question').value='Em đã chuyển khoản mà hệ thống vẫn chưa ghi nhận';
 for(const mode of ['mlp','linearsvc']){
  $('#research-model').value=mode;
  await $('#research-form').onsubmit({preventDefault(){}});
  assert.equal(requests.at(-1).model_mode,mode);
  const result=$('#research-result').innerHTML;
  assert(result.includes(mode==='mlp'?'predict_proba':'decision_function'));
  assert(result.includes('&lt;img'));
  assert(!result.includes('<img'));
  assert.equal($('#research-run').disabled,false);
 }
 const output={created_at:new Date().toISOString(),passed:6,checks:['Rerun warning and actual feature count','Two confusion matrices','Four model options only in experiment renderer','Per-class metrics and Test predictions','Model-specific submission and score display','Escaped result content and enabled submit button'],limitation:'Node VM with DOM stubs checks rendering logic, not browser layout. Chromium launch is blocked by sandbox.'};
 fs.writeFileSync(path.join(root,'reports/report-alignment-ui.json'),JSON.stringify(output,null,2)+'\n');
 console.log(JSON.stringify(output));
})().catch(e=>{console.error(e);process.exitCode=1});
