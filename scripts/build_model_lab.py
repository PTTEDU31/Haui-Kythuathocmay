"""Build public, read-only worked examples from the saved sklearn artifacts.

Never trains, imports app.main, reads settings/SQLite, or invokes a provider.
All arithmetic is checked against sklearn on all 50 public dataset questions
and the additional teaching examples before publishing the snapshot.
"""
import csv
import hashlib
import json
import re
import sys
from unittest.mock import patch
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from code_viewer_assets import include_code_viewer

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.text import normalize_classification


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_case(pipe, question, train):
    vectorizer = pipe.named_steps['tfidf']
    clf = pipe.named_steps['clf']
    counts = Counter(vectorizer.build_analyzer()(question))
    x = vectorizer.transform([question]).toarray()[0]
    terms = vectorizer.get_feature_names_out()
    documents = [set(vectorizer.build_analyzer()(q)) for q in train]
    features = []
    raw = np.zeros_like(x)
    for index in np.flatnonzero(x):
        term = terms[index]
        df = sum(term in doc for doc in documents)
        tf = 1 + np.log(counts[term])
        idf = np.log((1 + len(train)) / (1 + df)) + 1
        np.testing.assert_allclose(idf, vectorizer.idf_[index], atol=1e-12)
        raw[index] = tf * idf
        features.append(dict(index=int(index), term=term, count=counts[term],
                             df=df, tf=float(tf), idf=float(idf), raw=float(raw[index]), x=float(x[index])))
    norm = float(np.linalg.norm(raw))
    np.testing.assert_allclose(raw / norm if norm else raw, x, atol=1e-12)
    result = dict(features=features, raw_norm=norm, nonzero=len(features),
                  vector=x.tolist(),
                  normalized=normalize_classification(question), tokens=vectorizer.build_tokenizer()(normalize_classification(question)),
                  ignored=[term for term in counts if term not in vectorizer.vocabulary_],
                  predicted=str(pipe.predict([question])[0]))
    if hasattr(clf, 'coefs_'):
        z = x @ clf.coefs_[0] + clf.intercepts_[0]
        h = np.maximum(z, 0)
        logits = h @ clf.coefs_[1] + clf.intercepts_[1]
        e = np.exp(logits - np.max(logits))
        p = e / e.sum()
        np.testing.assert_allclose(p, pipe.predict_proba([question])[0], atol=1e-12)
        result.update(hidden_z=z.tolist(), hidden=h.tolist(), logits=logits.tolist(), scores=p.tolist())
        for feature in features:
            feature['weights'] = clf.coefs_[0][feature['index']].tolist()
    else:
        scores = clf.coef_ @ x + clf.intercept_
        np.testing.assert_allclose(scores, pipe.decision_function([question])[0], atol=1e-12)
        result['scores'] = scores.tolist()
        for feature in features:
            feature['weights'] = clf.coef_[:, feature['index']].tolist()
    assert str(clf.classes_[np.argmax(result['scores'])]) == result['predicted']
    return result


def route_snapshot(engine, question, model):
    # Observe calls while preserving the actual classifier's implementation.
    with patch.object(engine, 'classify', wraps=engine.classify) as classifier:
        result = engine.route(question, model_mode=model)
    return dict(status=result['status'], intent=result.get('intent'), intent_label=result.get('intent_label'),
                answer=result['answer'], routing=result.get('routing'),
                fallback_reason=result.get('fallback_reason'),
                classifier_called=bool(classifier.call_count),
                classifier_used=bool((result.get('routing') or {}).get('classifier_used')),
                faq_ids=[source['id'] for source in result.get('sources', [])])


def build():
    rows = list(csv.DictReader((ROOT / 'data/original_50.csv').open(encoding='utf-8')))
    train = [row['question'] for row in rows if row['split'] == 'Train']
    questions = [
        'Em đã chuyển khoản mà hệ thống vẫn chưa ghi nhận',
        'Quy định học phí năm học 2026–2027 ở đâu?',
        'Điều kiện xét học bổng là gì?',
        'Em muốn xem lịch thi và phòng thi',
        'Làm sao đăng ký học phần?',
        'Em muốn phúc khảo điểm thi',
        'zzzxxyy qqqvvv',
        'Thời tiết Hà Nội hôm nay thế nào?',
        'Em muốn đăng ký ký túc xá',
    ]
    data = dict(created_at=datetime.now(timezone.utc).isoformat(),
                dataset_sha256=digest(ROOT / 'data/original_50.csv'), train_size=len(train),
                dataset_counts={label: {split: sum(row['intent'] == label and row['split'] == split for row in rows)
                                        for split in ['Train', 'Validation', 'Test']}
                                for label in sorted({row['intent'] for row in rows})},
                selection=json.loads((ROOT / 'reports/selection.json').read_text()), models={},
                cases=[dict(question=q, models={}) for q in questions])
    checked = 0
    for name in ['mlp', 'linearsvc']:
        path = ROOT / f'models/{name}.joblib'
        pipe = joblib.load(path)
        v, clf = pipe.named_steps['tfidf'], pipe.named_steps['clf']
        meta = dict(classes=clf.classes_.tolist(), dimensions=len(v.vocabulary_), vocabulary=v.get_feature_names_out().tolist(), artifact_sha256=digest(path),
                    iterations=int(np.max(clf.n_iter_)), parameters=clf.get_params(),
                    biases=[x.tolist() for x in clf.intercepts_] if name == 'mlp' else clf.intercept_.tolist())
        if name == 'mlp':
            meta.update(shapes=[list(w.shape) for w in clf.coefs_], output_weights=clf.coefs_[1].tolist(),
                        parameter_count=sum(w.size for w in clf.coefs_ + clf.intercepts_))
        for row in rows:
            inspect_case(pipe, row['question'], train)
            checked += 1
        for case in data['cases']:
            case['models'][name] = inspect_case(pipe, case['question'], train)
            checked += 1
        data['models'][name] = meta
    data['verified_cases'] = checked
    # Use a fresh local Engine and only the public FAQ JSON, never the live DB.
    from app.engine import Engine, ROOT as ENGINE_ROOT
    assert ENGINE_ROOT.resolve() == ROOT.resolve()
    engine = Engine()
    faq_path = ROOT / 'data/faqs.json'
    engine.rebuild(json.loads(faq_path.read_text()))
    for case in data['cases']:
        case['routes'] = {name: route_snapshot(engine, case['question'], name) for name in data['models']}
    data['route_source'] = dict(path='data/faqs.json', sha256=digest(faq_path), faq_count=len(engine.rows))
    assert all(digest(ROOT / f'models/{name}.joblib') == model['artifact_sha256'] for name, model in data['models'].items())
    serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    target = ROOT / 'app/static/model-lab-data.js'
    target.write_text('/* Generated by scripts/build_model_lab.py. Public examples, no runtime trace. */\nwindow.ModelLabData=' + serialized + ';\n')
    page = ROOT / 'app/static/hoc-mo-hinh.html'
    html = page.read_text()
    for filename in ['model-lab-data.js', 'model-lab.js', 'model-lab.css']:
        version = digest(ROOT / 'app/static' / filename)[:12]
        pattern = rf'((?:src|href)="/static/{re.escape(filename)})(?:\?[^\"]*)?(\")'
        html, matches = re.subn(pattern, lambda match: match[1] + '?v=' + version + match[2], html)
        assert matches == 1, filename
    page.write_text(include_code_viewer(html))
    print(f'Published {len(questions)} examples; checked {checked} model passes against sklearn. {target.stat().st_size} bytes.')


if __name__ == '__main__':
    build()
