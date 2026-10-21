"""Re-run the fixed TC1/TC2 experiment; never manufacture a fresh holdout."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import csv
import hashlib
import json
import platform
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.text import NORMALIZATION_VERSION, normalize_classification
from app.engine import LABELS, RESEARCH_LABELS

SEED = 42
TFIDF = dict(ngram_range=(1, 2), max_features=500, min_df=1,
             strip_accents=None, sublinear_tf=True, norm='l2', lowercase=False)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')


def measure(pipe, rows):
    actual = [r['intent'] for r in rows]
    predicted = pipe.predict([r['question'] for r in rows])
    return dict(accuracy=accuracy_score(actual, predicted),
                macro_f1=f1_score(actual, predicted, labels=RESEARCH_LABELS, average='macro', zero_division=0),
                per_class=classification_report(actual, predicted, labels=RESEARCH_LABELS, output_dict=True, zero_division=0),
                confusion_matrix=confusion_matrix(actual, predicted, labels=RESEARCH_LABELS).tolist(),
                predictions=[dict(id=r['id'], question=r['question'], true=r['intent'], predicted=str(p))
                             for r, p in zip(rows, predicted)])


def main():
    dataset = ROOT/'data'/'original_50.csv'
    rows = list(csv.DictReader(dataset.open(encoding='utf-8', newline='')))
    splits = {s: [r for r in rows if r['split'] == s] for s in ('Train', 'Validation', 'Test')}
    assert len(rows) == 50 and [len(splits[s]) for s in splits] == [30, 10, 10]
    assert set(r['intent'] for r in rows) == set(RESEARCH_LABELS)
    assert len({r['id'] for r in rows}) == 50
    assert all(r['group_id'] == r['id'] for r in rows)
    environment = dict(python=platform.python_version(), sklearn=sklearn.__version__,
                       numpy=np.__version__, scipy=scipy.__version__, joblib=joblib.__version__,
                       platform=platform.platform(), cpu=platform.processor(),
                       threads={k: os.environ[k] for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')})
    report = dict(created_at=timestamp(), seed=SEED, environment=environment,
                  dataset=dict(total=50, train=30, validation=10, test=10, sha256=sha(dataset),
                               version='TC1-original-50-fixed-split',
                               origin='50 câu minh họa do tác giả biên soạn trong DOCX; không phải phản hồi sinh viên thực tế.',
                               source_sha256=sha(next((ROOT/'sources').glob('*.docx'))),
                               split_ids={s: [r['id'] for r in rs] for s, rs in splits.items()}),
                  labels=list(RESEARCH_LABELS), label_names={k: LABELS[k] for k in RESEARCH_LABELS},
                  label_encoding='Nhãn chuỗi trong sklearn; thứ tự báo cáo theo Bảng 1.7 DOCX. classes_ lưu riêng để giải mã điểm.',
                  normalization=dict(version=NORMALIZATION_VERSION, callable='app.text.normalize_classification',
                                     rules='Unicode NFC, chữ thường, khoảng trắng; giữ dấu và từ phủ định; không stopword, không mở rộng viết tắt.'),
                  tfidf_configuration=TFIDF,
                  method='TF-IDF chỉ fit trên 30 câu Train. Chọn từng họ theo Macro-F1 Validation; hòa trong họ lấy cấu hình đầu theo thứ tự đã định. Chọn ứng dụng theo Macro-F1 Validation, hòa ưu tiên LinearSVC. Lưu selection.json trước khi tính Test, không refit Train+Validation.',
                  evaluation_status='Tái thực nghiệm trên tập Test đã từng được xem; không phải đánh giá độc lập mới.',
                  research_primary='MLP', models=[], candidates=[],
                  limitations=['Test đã từng được xem trong lần triển khai trước; lần chạy này không tạo holdout độc lập.',
                               'Test chỉ có 10 câu, hai câu mỗi nhãn; một lỗi thay đổi accuracy 10 điểm phần trăm.',
                               'Dữ liệu tự biên soạn nhỏ; chưa đo chất lượng trên phản hồi sinh viên thực tế.',
                               'Điểm phân loại và điểm truy hồi không phải xác suất câu trả lời đúng đã hiệu chỉnh.',
                               'Ngưỡng truy hồi là quy tắc kỹ thuật, chưa tối ưu hay đo nhận biết ngoài phạm vi trên tập độc lập.',
                               'BiLSTM/PhoBERT chưa chạy. Qwen/Ollama chỉ hỗ trợ diễn đạt FAQ, không được huấn luyện bằng 50 câu.'])
    finalists = []
    for name in ('MLP', 'LinearSVC'):
        configs = ([dict(hidden_layer_sizes=(h,), alpha=a) for h in (16, 32) for a in (.001, .01)]
                   if name == 'MLP' else [dict(C=c) for c in (.1, 1.)])
        candidates = []
        for config in configs:
            clf = (MLPClassifier(**config, solver='lbfgs', max_iter=1000, random_state=SEED)
                   if name == 'MLP' else LinearSVC(**config, random_state=SEED))
            pipe = Pipeline([('tfidf', TfidfVectorizer(preprocessor=normalize_classification, **TFIDF)), ('clf', clf)])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                start = time.perf_counter()
                pipe.fit([r['question'] for r in splits['Train']], [r['intent'] for r in splits['Train']])
                elapsed = time.perf_counter()-start
            convergence = dict(n_iter=np.asarray(clf.n_iter_).tolist(),
                               convergence_warning=any(issubclass(w.category, ConvergenceWarning) for w in caught),
                               warnings=[str(w.message) for w in caught],
                               loss=float(clf.loss_) if name == 'MLP' else None,
                               note='n_iter là vòng lặp bộ tối ưu; không gọi là epoch Adam. Không có loss_curve_ với lbfgs.')
            validation = measure(pipe, splits['Validation'])
            item = dict(name=name, configuration=config, validation=validation, fit_seconds=round(elapsed, 6),
                        feature_count=len(pipe.named_steps['tfidf'].vocabulary_), convergence=convergence)
            report['candidates'].append(item)
            candidates.append((pipe, item))
        pipe, item = max(candidates, key=lambda c: c[1]['validation']['macro_f1'])
        finalists.append((name, pipe, item))
        print(name, item['configuration'], 'Validation Macro-F1', item['validation']['macro_f1'], flush=True)
    name, selected_pipe, best = max(finalists, key=lambda c: (c[2]['validation']['macro_f1'], c[0] == 'LinearSVC'))
    selection = dict(selected=name, selected_at=timestamp(), validation_macro_f1=best['validation']['macro_f1'],
                     configuration=best['configuration'], dataset_sha256=sha(dataset),
                     research_primary='MLP', test_previously_seen=True, test_evaluated_in_this_run=False,
                     reason='Macro-F1 Validation cao nhất; hòa ưu tiên LinearSVC vì suy luận tuyến tính đơn giản. Không chọn bằng Test.',
                     evaluation_status=report['evaluation_status'],
                     family_selections={n: i['configuration'] for n, p, i in finalists})
    (ROOT/'reports').mkdir(exist_ok=True)
    write(ROOT/'reports'/'selection.json', selection)  # Persist before first Test predict.
    report['selection'] = selection
    report['test_evaluation_started_at'] = timestamp()
    (ROOT/'models').mkdir(exist_ok=True)
    for name, pipe, item in finalists:
        test = measure(pipe, splits['Test'])
        train = measure(pipe, splits['Train'])
        latency = []
        for _ in range(10):
            for row in splits['Test']:
                start = time.perf_counter(); pipe.predict([row['question']])
                latency.append((time.perf_counter()-start)*1000)
        metadata = dict(dataset_sha256=sha(dataset), normalization=report['normalization'], seed=SEED,
                        feature_count=item['feature_count'], labels=list(RESEARCH_LABELS),
                        classes=pipe.classes_.tolist(), tfidf_configuration=TFIDF,
                        classifier_parameters=pipe.named_steps['clf'].get_params(), environment=environment,
                        convergence=item['convergence'])
        metadata = json.loads(json.dumps(metadata))  # Same schema in joblib and JSON.
        pipe.research_metadata_ = metadata
        path = ROOT/'models'/f'{name.lower()}.joblib'
        joblib.dump(pipe, path)
        report['models'].append(dict(**item, metadata=metadata, train=train, test=test,
                                     validation_macro_f1=item['validation']['macro_f1'],
                                     test_accuracy=test['accuracy'], test_macro_f1=test['macro_f1'],
                                     confusion_matrix=test['confusion_matrix'], per_class=test['per_class'], predictions=test['predictions'],
                                     latency_p50_ms=round(float(np.percentile(latency, 50)), 3),
                                     latency_p95_ms=round(float(np.percentile(latency, 95)), 3),
                                     artifact=str(path.relative_to(ROOT)), artifact_sha256=sha(path)))
    joblib.dump(selected_pipe, ROOT/'models'/'intent.joblib')
    report['test_evaluation_completed_at'] = timestamp()
    report['selected_model'] = selection['selected']
    report['application_retrieval'] = ('Nhãn phân loại định hướng truy hồi FAQ trong 5 chủ đề khi không có chủ đề tường minh. '
        'An toàn, nhiều chủ đề, ngữ cảnh và chủ đề tường minh được ưu tiên; CTSV/KTX là mở rộng, không gán ép vào 5 lớp. '
        'Truy hồi word/char không dấu kiểm tra bằng chứng riêng; thiếu khớp thì hỏi lại/từ chối. Có chế độ auto, MLP, LinearSVC và chỉ truy hồi tại trang Thực nghiệm.')
    write(ROOT/'reports'/'experiments.json', report)
    print(json.dumps(dict(selected=report['selected_model'], test=[{k: r[k] for k in ('name', 'test_accuracy', 'test_macro_f1', 'feature_count')} for r in report['models']]), ensure_ascii=False))


if __name__ == '__main__':
    main()
