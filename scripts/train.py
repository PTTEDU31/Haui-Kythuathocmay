import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import csv,json,time,sys,platform,hashlib
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,joblib,sklearn
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score,f1_score,classification_report,confusion_matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.engine import normalize,LABELS
rows=list(csv.DictReader((ROOT/'data'/'original_50.csv').open()))
train=[r for r in rows if r['split']=='Train'];val=[r for r in rows if r['split']=='Validation'];test=[r for r in rows if r['split']=='Test']
labels=sorted({r['intent'] for r in rows})
def split(rs):return [r['question'] for r in rs],[r['intent'] for r in rs]
x,y=split(train);vx,vy=split(val);tx,ty=split(test)
report={'created_at':datetime.now(timezone.utc).isoformat(),'dataset':{'total':50,'train':30,'validation':10,'test':10,'origin':'50 câu minh họa do tác giả biên soạn trong báo cáo; không phải câu hỏi thực tế độc lập.','sha256':hashlib.sha256((ROOT/'data'/'original_50.csv').read_bytes()).hexdigest()},'method':'TF-IDF học trên 30 câu Train. Mỗi họ mô hình chọn cấu hình theo Macro-F1 trên 10 câu Validation; chốt lựa chọn trước khi đánh giá 10 câu Test. Không tăng dữ liệu bằng câu diễn đạt lại từ Test.','seed':42,'labels':labels,'label_names':{l:LABELS[l] for l in labels},'models':[],'environment':{'python':platform.python_version(),'sklearn':sklearn.__version__,'cpu':platform.processor()},'limitations':['Test chỉ có 10 câu, hai câu mỗi nhãn; một lỗi làm accuracy thay đổi 10 điểm phần trăm.','Điểm mô hình phân loại không đo độ đúng của câu trả lời AI.','Dữ liệu minh họa nhỏ chưa chứng minh khả năng dùng ổn định trên câu hỏi sinh viên thực tế.','BiLSTM/PhoBERT chưa chạy; cần thêm dữ liệu độc lập trước khi so sánh.']}
finalists=[]
for name in ['MLP','LinearSVC']:
    candidates=[]
    configs=[{'hidden_layer_sizes':(h,),'alpha':a} for h in (16,32) for a in (.001,.01)] if name=='MLP' else [{'C':c} for c in (.1,1.0)]
    for config in configs:
        clf=MLPClassifier(**config,solver='lbfgs',max_iter=1000,random_state=42) if name=='MLP' else LinearSVC(**config,random_state=42)
        pipe=Pipeline([('tfidf',TfidfVectorizer(preprocessor=normalize,ngram_range=(1,2),max_features=5000,sublinear_tf=True)),('clf',clf)])
        t=time.perf_counter();pipe.fit(x,y);elapsed=time.perf_counter()-t
        pred=pipe.predict(vx);score=f1_score(vy,pred,average='macro',zero_division=0)
        candidates.append((score,pipe,config,elapsed))
    best=max(candidates,key=lambda r:r[0]);finalists.append((name,*best))
    print(name,'validation macro-F1',best[0],best[2],flush=True)
selected=max(finalists,key=lambda r:(r[1],r[0]=='LinearSVC'))
# Record selection before touching test outcomes.
(ROOT/'reports'/'selection.json').write_text(json.dumps({'selected':selected[0],'validation_macro_f1':selected[1],'reason':'Highest validation macro-F1; LinearSVC wins ties for lower runtime complexity.','test_seen':False},indent=2))
for name,score,pipe,config,elapsed in finalists:
    pred=pipe.predict(tx);lat=[]
    for _ in range(10):
        for q in tx:
            t=time.perf_counter();pipe.predict([q]);lat.append((time.perf_counter()-t)*1000)
    r={'name':name,'configuration':config,'validation_macro_f1':score,'test_accuracy':accuracy_score(ty,pred),'test_macro_f1':f1_score(ty,pred,average='macro',zero_division=0),'fit_seconds':round(elapsed,4),'latency_p50_ms':round(float(np.percentile(lat,50)),3),'latency_p95_ms':round(float(np.percentile(lat,95)),3),'confusion_matrix':confusion_matrix(ty,pred,labels=labels).tolist(),'per_class':classification_report(ty,pred,labels=labels,output_dict=True,zero_division=0),'predictions':[{'id':row['id'],'question':row['question'],'true':row['intent'],'predicted':str(p)} for row,p in zip(test,pred)]}
    report['models'].append(r)
    (ROOT/'models').mkdir(exist_ok=True);joblib.dump(pipe,ROOT/'models'/f'{name.lower()}.joblib')
joblib.dump(selected[2],ROOT/'models'/'intent.joblib')
report['selected_model']=selected[0]
report['application_retrieval']='Truy hồi kết hợp TF-IDF word n-gram và char n-gram, hỗ trợ câu không dấu; 7 chủ đề. Nhãn mô hình 5 lớp thực nghiệm được hiển thị riêng, không dùng để tuyên bố câu trả lời đúng.'
(ROOT/'reports'/'experiments.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'selected':report['selected_model'],'test':[{k:r[k] for k in ('name','test_accuracy','test_macro_f1')} for r in report['models']]},ensure_ascii=False))
