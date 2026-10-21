"""Socket-free API smoke checks using only a disposable, synthetic database.

This complements pytest; it does not replace the host's full TestClient suite.
"""
import asyncio
import json
import os
import secrets
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE))


async def check(app, engine, root, password_hash):
    # Keep event-loop progress independent of the cross-thread wakeup restriction
    # observed in the sandbox's TestClient portal. All requests stay in process.
    async def heartbeat():
        while True: await asyncio.sleep(.02)
    task=asyncio.create_task(heartbeat())
    checks=[]
    try:
        salt=secrets.token_hex(16)
        (root/'data/admin-auth.json').write_text(json.dumps({'salt':salt,'hash':password_hash('Synthetic-Only-2026',salt)}))
        (root/'data/ai-settings.json').write_text(json.dumps({'enabled':False,'provider':'ollama','model':'fake','base_url':'','api_key':''}))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://inprocess') as c:
                r=await c.get('/api/health')
                assert r.status_code==200 and r.json()['knowledge_items']==25
                assert r.headers['x-content-type-options']=='nosniff'
                checks.append('Health, source count and response headers')
                r=await c.get('/api/experiments')
                assert r.status_code==200 and r.json()['research_primary']=='MLP'
                assert r.json()['dataset']['total']==50
                assert r.json()['faq_evaluation']['modes'][0]['total']==20
                checks.append('Experiment API exposes the retrained report')
                for mode,kind in [('mlp','predict_proba'),('linearsvc','decision_function')]:
                    r=await c.post('/api/experiments/route',json={'question':'Em đã chuyển khoản mà hệ thống vẫn chưa ghi nhận','model_mode':mode})
                    assert r.status_code==200, r.text
                    v=r.json()
                    assert v['classification']['score_type']==kind
                    assert v['routing']['classifier_used'] and v['sources'][0]['id']=='FAQ-004'
                    assert 'evidence' not in v and 'generation' not in v
                assert (await c.get('/api/history')).json()==[]
                checks.append('MLP/LinearSVC research routes use labels with distinct score semantics and leave history empty')
                assert (await c.post('/api/experiments/route',json={'question':'học phí','model_mode':'bad'})).status_code==422
                assert (await c.post('/api/experiments/route',json={'question':'   '})).status_code==422
                assert (await c.post('/api/experiments/route',json={'question':'học phí'},headers={'Origin':'https://evil.example'})).status_code==403
                checks.append('Research input validation and cross-origin protection')
                before=engine.default_model
                for question,intent in [('Quy định học phí năm học 2026–2027 ở đâu?','hoc_phi'),('Em muốn đăng ký ktx','ky_tuc_xa')]:
                    r=await c.post('/api/chat',json={'question':question,'use_ai':False})
                    assert r.status_code==200 and r.json()['intent']==intent
                    assert r.json()['sources'] and not r.json()['generation']['used']
                assert engine.default_model==before
                checks.append('Normal chat retains automatic selection, extension routing and source citations')
                r=await c.post('/api/chat',json={'question':'Học phí thiên văn sao hỏa lượng tử','use_ai':False})
                assert r.json()['status']=='clarify' and not r.json()['sources']
                checks.append('Topic words alone cannot supply evidence')
                assert (await c.get('/api/admin/overview')).status_code==401
                assert (await c.post('/api/admin/login',json={'password':'Synthetic-Only-2026'})).status_code==200
                body=dict(question='Câu hỏi kiểm tra trong tiến trình',answer='Nội dung kiểm tra nguồn được duyệt trong cơ sở dữ liệu tạm.',intent='hoc_phi',source_url='https://www.haui.edu.vn/vn',source_title='HaUI kiểm tra',reviewed_at=datetime.now().date().isoformat(),status='draft')
                r=await c.post('/api/admin/faqs',json=body)
                assert r.status_code==200
                identifier=r.json()['id']
                assert identifier not in [x['id'] for x in engine.rows]
                body['status']='approved'
                assert (await c.put('/api/admin/faqs/'+identifier,json=body)).status_code==200
                assert identifier in [x['id'] for x in engine.rows]
                checks.append('Synthetic admin authentication, draft exclusion and approved FAQ rebuild')
                r=await c.get('/')
                assert r.status_code==200 and 'experiment-content' in r.text
                assert (await c.get('/static/app.js')).status_code==200
                checks.append('HTML and experiment JavaScript assets are served')
                assert (await c.delete('/api/history')).status_code==200
                assert (await c.get('/api/history')).json()==[]
                checks.append('Disposable visitor history can be cleared')
    finally:
        task.cancel()
    return checks


def main():
    with tempfile.TemporaryDirectory(prefix='haui-alignment-api-') as temporary:
        root=Path(temporary)
        for folder in ('data','models','reports'): (root/folder).mkdir()
        shutil.copy(SOURCE/'data/faqs.json',root/'data/faqs.json')
        for name in ('experiments.json','selection.json','faq-evaluation.json'): shutil.copy(SOURCE/'reports'/name,root/'reports'/name)
        for name in ('mlp.joblib','linearsvc.joblib'): shutil.copy(SOURCE/'models'/name,root/'models'/name)
        os.environ['STUDENT_ROOT']=str(root)
        from app.main import app,ENGINE,password_hash
        checks=asyncio.run(check(app,ENGINE,root,password_hash))
    report=dict(created_at=datetime.now(timezone.utc).isoformat(),method='httpx.ASGITransport, synthetic temporary data, AI disabled, no network sockets',passed=len(checks),checks=checks,
                limitation='Complements pytest. Full TestClient suite and browser still require host verification in an environment allowing their execution.')
    (SOURCE/'reports/report-alignment-inprocess.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__': main()
