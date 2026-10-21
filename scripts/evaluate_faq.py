"""Technical FAQ selection evaluation, separate from the 50-question intent test."""
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.engine import Engine


def main():
    path=ROOT/'data/technical_faq_cases.json'
    data=json.loads(path.read_text())
    engine=Engine()
    engine.rebuild(json.loads((ROOT/'data/faqs.json').read_text()))
    report=dict(created_at=datetime.now(timezone.utc).isoformat(),
                provenance=data['provenance'], cases_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                faq_sha256=hashlib.sha256((ROOT/'data/faqs.json').read_bytes()).hexdigest(),
                model_sha256={m:hashlib.sha256((ROOT/'models'/f'{m}.joblib').read_bytes()).hexdigest() for m in engine.models},
                definitions={'correct_faq':'status=answered và FAQ ID thuộc danh sách chấp nhận được biên soạn trong tình huống kỹ thuật.',
                             'correct_behavior':'Đúng status dự kiến; nếu answered phải đúng FAQ ID.',
                             'answered_precision':'Số FAQ đúng / tất cả câu đã trả lời trong các tình huống kỹ thuật.',
                             'faq_accuracy':'Số FAQ đúng / số tình huống dự kiến có FAQ; tính cả hỏi lại/từ chối là chưa chọn được FAQ.',
                             'scope':'Chỉ kiểm tra kỹ thuật; không suy ra chất lượng thực tế, xác suất đúng hay tỷ lệ phát hiện ngoài miền.'},
                modes=[])
    for mode in ('auto','mlp','linearsvc','retrieval'):
        outcomes=[]
        for case in data['cases']:
            r=engine.route(case['question'],case.get('history'),model_mode=mode)
            faq=r['sources'][0]['id'] if r.get('sources') else None
            correct_faq=r['status']=='answered' and faq in case['acceptable_faq_ids']
            correct=r['status']==case['expected_status'] and (case['expected_status']!='answered' or correct_faq)
            outcomes.append(dict(**case, actual_status=r['status'], selected_faq_id=faq,
                                 retrieval_score=r.get('retrieval_score'), classification=r.get('classification'),
                                 routing=r.get('routing'), correct_faq=correct_faq, correct_behavior=correct))
        correct=sum(r['correct_faq'] for r in outcomes)
        expected=sum(r['expected_status']=='answered' for r in outcomes)
        answered=sum(r['actual_status']=='answered' for r in outcomes)
        report['modes'].append(dict(mode=mode, total=len(outcomes), expected_answered=expected, answered=answered,
                                   correct_faq=correct, faq_accuracy=correct/expected,
                                   answered_precision=correct/answered if answered else None,
                                   correct_behavior=sum(r['correct_behavior'] for r in outcomes),
                                   statuses=dict(Counter(r['actual_status'] for r in outcomes)), outcomes=outcomes))
    (ROOT/'reports/faq-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for m in report['modes']:
        print(m['mode'], 'FAQ',m['correct_faq'],'/',m['expected_answered'],'answered',m['answered'],
              'behavior',m['correct_behavior'],'/',m['total'], 'errors', [r['id'] for r in m['outcomes'] if not r['correct_behavior']])


if __name__=='__main__': main()
