import os,json,sqlite3,time,hashlib,hmac,secrets,threading,io,zipfile,re
from pathlib import Path
from datetime import date,datetime,timezone
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from fastapi import FastAPI,HTTPException,Request,Response,Depends,UploadFile,File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,ConfigDict
import httpx
from .engine import Engine,ROOT,LABELS,safe_url,normalize,active

DB=ROOT/'data'/'student.db';STATIC=Path(__file__).parent/'static'
ENGINE=Engine();rate_lock=threading.Lock();rates=defaultdict(deque)
def conn():
    c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=20000');return c
def now():return datetime.now(timezone.utc).isoformat()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def password_hash(p,salt):return hashlib.scrypt(p.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def read_settings():
    p=ROOT/'data'/'ai-settings.json'
    if p.exists():return json.loads(p.read_text())
    return {'enabled':True,'provider':'ollama','model':'qwen3:4b','base_url':'','api_key':''}
def init_db():
    DB.parent.mkdir(exist_ok=True,parents=True)
    with conn() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS faqs(id TEXT PRIMARY KEY, question TEXT NOT NULL,answer TEXT NOT NULL,intent TEXT NOT NULL,aliases TEXT DEFAULT '',source_url TEXT NOT NULL,source_title TEXT NOT NULL,reviewed_at TEXT NOT NULL,valid_until TEXT,status TEXT NOT NULL DEFAULT 'draft',kind TEXT DEFAULT 'guidance');
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES sessions(id),role TEXT NOT NULL,content TEXT NOT NULL,result TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS feedback(message_id TEXT PRIMARY KEY REFERENCES messages(id),value INTEGER NOT NULL,note TEXT DEFAULT '',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS admin_sessions(token TEXT PRIMARY KEY,expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,action TEXT NOT NULL,target TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,name TEXT NOT NULL,text TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',created_at TEXT NOT NULL);
        ''')
        if not c.execute('SELECT count(*) FROM faqs').fetchone()[0]:
            p=ROOT/'data'/'faqs.json'
            if p.exists():
                for r in json.loads(p.read_text()):
                    keys=list(r);c.execute('INSERT INTO faqs('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',list(r.values()))
    reload_engine()
def reload_engine():
    with conn() as c:rows=[dict(r) for r in c.execute('SELECT * FROM faqs')]
    ENGINE.rebuild(rows)
def audit(c,action,target=''):c.execute('INSERT INTO audit(action,target,created_at) VALUES(?,?,?)',(action,target,now()))
def limit(request,key,max_count,seconds=60):
    ip=request.client.host if request.client else 'unknown';k=(ip,key);t=time.monotonic()
    with rate_lock:
        d=rates[k]
        while d and d[0]<t-seconds:d.popleft()
        if len(d)>=max_count:raise HTTPException(429,'Bạn thao tác hơi nhanh. Vui lòng thử lại sau ít phút.',headers={'Retry-After':str(seconds)})
        d.append(t)
        if len(rates)>10000:
            for old in list(rates):
                if not rates[old] or rates[old][-1]<t-600:rates.pop(old,None)
def visitor(request,response):
    raw=request.cookies.get('haui_visitor','');sid=digest(raw) if raw else ''
    with conn() as c:
        found=c.execute('SELECT id FROM sessions WHERE id=?',(sid,)).fetchone() if sid else None
        if not found:
            raw=secrets.token_urlsafe(32);sid=digest(raw)
            c.execute('INSERT INTO sessions VALUES(?,?)',(sid,now()))
            response.set_cookie('haui_visitor',raw,max_age=2592000,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE')=='1')
    return sid
def admin(request:Request):
    token=request.cookies.get('haui_admin','')
    with conn() as c:r=c.execute('SELECT expires FROM admin_sessions WHERE token=?',(digest(token),)).fetchone()
    if not token or not r or r['expires']<time.time():raise HTTPException(401,'Vui lòng đăng nhập quản trị.')
    return True

@asynccontextmanager
async def lifespan(app):
    init_db();yield
app=FastAPI(title='HaUI Assist',version='1.0.0',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

@app.middleware('http')
async def guard(request,call_next):
    if request.method in ('POST','PUT','DELETE','PATCH'):
        origin=request.headers.get('origin')
        if origin and urlparse(origin).netloc!=request.headers.get('host'):
            return Response('Origin not allowed',status_code=403)
        try:length=int(request.headers.get('content-length','0'))
        except ValueError:return Response('Bad length',status_code=400)
        if length>10*1024*1024:return Response('Tệp quá lớn (tối đa 8 MB).',status_code=413)
    result=await call_next(request)
    result.headers['X-Content-Type-Options']='nosniff'
    result.headers['X-Frame-Options']='DENY'
    result.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    result.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    result.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if request.url.path.startswith('/api'):result.headers['Cache-Control']='no-store'
    return result

class Chat(BaseModel):
    question:str=Field(min_length=1,max_length=1500)
    use_ai:bool=True
class Login(BaseModel):password:str=Field(min_length=1,max_length=256)
class ChangePassword(BaseModel):
    current_password:str=Field(min_length=1,max_length=256)
    new_password:str=Field(min_length=12,max_length=256)
class Feedback(BaseModel):
    message_id:str;value:int=Field(ge=-1,le=1);note:str=Field(default='',max_length=500)
class Faq(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=5,max_length=300)
    answer:str=Field(min_length=15,max_length=10000)
    intent:str
    aliases:str=Field(default='',max_length=3000)
    source_url:str=Field(max_length=2000)
    source_title:str=Field(min_length=3,max_length=300)
    reviewed_at:date
    valid_until:date|None=None
    status:str='draft'
    kind:str='guidance'
class AISettings(BaseModel):
    enabled:bool=True;provider:str='ollama';model:str=Field(default='qwen3:4b',min_length=1,max_length=150)
    base_url:str=Field(default='',max_length=300);api_key:str|None=Field(default=None,max_length=500)

@app.get('/api/health')
def health():
    with conn() as c:c.execute('SELECT 1')
    return {'status':'ok','version':'1.0.0','knowledge_items':len(ENGINE.rows),'index_version':ENGINE.version}
@app.get('/api/bootstrap')
def bootstrap(request:Request,response:Response):
    visitor(request,response)
    settings=read_settings()
    return {'name':'HaUI Assist','university':'Đại học Công nghiệp Hà Nội','topics':LABELS,'faq_count':len(ENGINE.rows),'ai':{'enabled':settings['enabled'],'provider':settings['provider'],'model':settings['model']},'privacy':'Lịch sử được lưu trên máy chủ nội bộ và chỉ hiển thị trong trình duyệt của bạn. Không nhập mật khẩu, mã OTP hay thông tin nhạy cảm.','scope':'Thông tin công khai và hướng dẫn tra cứu. Chưa kết nối hệ thống điểm, tài khoản hoặc công nợ cá nhân.'}
@app.get('/api/history')
def history(request:Request,response:Response):
    sid=visitor(request,response)
    with conn() as c:rows=c.execute('SELECT * FROM messages WHERE session_id=? ORDER BY rowid DESC LIMIT 60',(sid,)).fetchall()
    return [{'id':r['id'],'role':r['role'],'content':r['content'],'result':json.loads(r['result']) if r['result'] else None,'created_at':r['created_at']} for r in reversed(rows)]
@app.delete('/api/history')
def clear_history(request:Request,response:Response):
    sid=visitor(request,response)
    with conn() as c:
        c.execute('DELETE FROM feedback WHERE message_id IN (SELECT id FROM messages WHERE session_id=?)',(sid,))
        c.execute('DELETE FROM messages WHERE session_id=?',(sid,))
    return {'ok':True}
@app.post('/api/chat')
def chat(body:Chat,request:Request,response:Response):
    limit(request,'chat',20);sid=visitor(request,response);q=body.question.strip()
    if not q or not normalize(q):raise HTTPException(422,'Bạn hãy nhập một câu hỏi có nội dung.')
    started=time.perf_counter()
    with conn() as c:
        past=c.execute("SELECT result FROM messages WHERE session_id=? AND role='assistant' ORDER BY rowid DESC LIMIT 4",(sid,)).fetchall()
    result=ENGINE.route(q,[json.loads(r['result']) for r in reversed(past) if r['result']])
    if body.use_ai:result=ENGINE.generate(q,result,read_settings())
    else:result['generation']={'used':False,'reason':'disabled_for_request'}
    result.pop('evidence',None);result['latency_ms']=round((time.perf_counter()-started)*1000)
    result['id']=secrets.token_hex(12)
    with conn() as c:
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',(secrets.token_hex(12),sid,'user',q,None,now()))
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?,?)',(result['id'],sid,'assistant',result['answer'],json.dumps(result,ensure_ascii=False),now()))
    return result
@app.post('/api/feedback')
def feedback(body:Feedback,request:Request,response:Response):
    limit(request,'feedback',30);sid=visitor(request,response)
    with conn() as c:
        r=c.execute("SELECT id FROM messages WHERE id=? AND session_id=? AND role='assistant'",(body.message_id,sid)).fetchone()
        if not r:raise HTTPException(404,'Không tìm thấy câu trả lời.')
        c.execute('INSERT OR REPLACE INTO feedback VALUES(?,?,?,?)',(body.message_id,body.value,body.note,now()))
    return {'ok':True}
@app.get('/api/knowledge')
def knowledge(q:str='',intent:str=''):
    if len(q)>500:raise HTTPException(422,'Từ khóa quá dài.')
    rows=ENGINE.search(q,intent or None,50) if q.strip() else [r for r in ENGINE.rows if active(r) and (not intent or r['intent']==intent)]
    return {'items':[{k:v for k,v in r.items() if k!='aliases'} for r in rows],'topics':LABELS}
@app.get('/api/experiments')
def experiments():
    p=ROOT/'reports'/'experiments.json'
    return json.loads(p.read_text()) if p.exists() else {'status':'pending'}
@app.get('/api/ai-status')
def ai_status():
    s=read_settings()
    try:
        if s['provider']=='ollama':
            r=httpx.get('http://127.0.0.1:11435/api/tags',timeout=3);r.raise_for_status()
            ready=any(m['name']==s['model'] for m in r.json().get('models',[]))
        else:ready=bool(s.get('api_key') and s.get('base_url'))
    except Exception:ready=False
    return {'enabled':s['enabled'],'ready':ready,'provider':s['provider'],'model':s['model']}
@app.post('/api/admin/login')
def login(body:Login,request:Request,response:Response):
    limit(request,'login',5,300)
    p=ROOT/'data'/'admin-auth.json'
    if not p.exists():raise HTTPException(503,'Chưa thiết lập tài khoản quản trị.')
    auth=json.loads(p.read_text())
    if not hmac.compare_digest(password_hash(body.password,auth['salt']),auth['hash']):raise HTTPException(401,'Mật khẩu chưa đúng.')
    token=secrets.token_urlsafe(40)
    with conn() as c:
        c.execute('DELETE FROM admin_sessions WHERE expires<?',(time.time(),))
        c.execute('INSERT INTO admin_sessions VALUES(?,?)',(digest(token),time.time()+8*3600));audit(c,'login')
    response.set_cookie('haui_admin',token,max_age=8*3600,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE')=='1')
    return {'ok':True}
@app.post('/api/admin/logout')
def logout(request:Request,response:Response):
    with conn() as c:c.execute('DELETE FROM admin_sessions WHERE token=?',(digest(request.cookies.get('haui_admin','')),))
    response.delete_cookie('haui_admin');return {'ok':True}
@app.post('/api/admin/password',dependencies=[Depends(admin)])
def change_password(body:ChangePassword,request:Request):
    limit(request,'password_change',5,300)
    p=ROOT/'data'/'admin-auth.json';auth=json.loads(p.read_text())
    if not hmac.compare_digest(password_hash(body.current_password,auth['salt']),auth['hash']):raise HTTPException(401,'Mật khẩu hiện tại chưa đúng.')
    if body.new_password==body.current_password:raise HTTPException(422,'Mật khẩu mới cần khác mật khẩu hiện tại.')
    salt=secrets.token_hex(16);tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps({'salt':salt,'hash':password_hash(body.new_password,salt)}));tmp.chmod(0o600);tmp.replace(p)
    initial=ROOT/'data'/'initial-admin-password.txt'
    if initial.exists():initial.unlink()
    with conn() as c:
        c.execute('DELETE FROM admin_sessions WHERE token!=?',(digest(request.cookies.get('haui_admin','')),));audit(c,'admin_password_changed')
    return {'ok':True}
@app.get('/api/admin/overview',dependencies=[Depends(admin)])
def overview():
    with conn() as c:
        stats={k:c.execute(sql).fetchone()[0] for k,sql in {'questions':"SELECT count(*) FROM messages WHERE role='user'",'positive':'SELECT count(*) FROM feedback WHERE value=1','negative':'SELECT count(*) FROM feedback WHERE value=-1','drafts':"SELECT count(*) FROM faqs WHERE status='draft'"}.items()}
        faqs=[dict(r) for r in c.execute('SELECT * FROM faqs ORDER BY intent,question')]
        docs=[dict(r) for r in c.execute('SELECT * FROM documents ORDER BY created_at DESC')]
        audits=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 30')]
    s=read_settings();s['api_key_set']=bool(s.pop('api_key',None))
    return {'stats':stats,'faqs':faqs,'documents':docs,'audit':audits,'settings':s,'topics':LABELS}
def validate_faq(body):
    if body.intent not in LABELS:raise HTTPException(422,'Nhóm câu hỏi không hợp lệ.')
    if body.status not in ('approved','draft','archived'):raise HTTPException(422,'Trạng thái không hợp lệ.')
    if body.kind not in ('guidance','policy','notice'):raise HTTPException(422,'Loại nguồn không hợp lệ.')
    if not safe_url(body.source_url):raise HTTPException(422,'Nguồn phải là HTTPS trên tên miền chính thức haui.edu.vn.')
    if body.reviewed_at>date.today():raise HTTPException(422,'Ngày rà soát không được nằm trong tương lai.')
    if body.valid_until and body.valid_until<body.reviewed_at:raise HTTPException(422,'Ngày hết hiệu lực phải sau ngày rà soát.')
    return body.model_dump(mode='json')
@app.post('/api/admin/faqs',dependencies=[Depends(admin)])
def create_faq(body:Faq):
    r=validate_faq(body);r['id']=secrets.token_hex(8)
    with conn() as c:
        keys=list(r);c.execute('INSERT INTO faqs('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',list(r.values()));audit(c,'faq_create_'+r['status'],r['id'])
    reload_engine();return r
@app.put('/api/admin/faqs/{id}',dependencies=[Depends(admin)])
def update_faq(id:str,body:Faq):
    r=validate_faq(body)
    with conn() as c:
        if not c.execute('SELECT id FROM faqs WHERE id=?',(id,)).fetchone():raise HTTPException(404,'Không tìm thấy FAQ.')
        c.execute('UPDATE faqs SET '+','.join(k+'=?' for k in r)+' WHERE id=?',list(r.values())+[id]);audit(c,'faq_update_'+r['status'],id)
    reload_engine();return {**r,'id':id}
@app.post('/api/admin/documents',dependencies=[Depends(admin)])
async def upload_document(file:UploadFile=File(...)):
    ext=Path(file.filename or '').suffix.lower()
    if ext not in ('.txt','.pdf','.docx'):raise HTTPException(422,'Chỉ nhận TXT, PDF và DOCX.')
    raw=bytearray()
    while block:=await file.read(65536):
        raw.extend(block)
        if len(raw)>8*1024*1024:raise HTTPException(413,'Tệp lớn hơn 8 MB.')
    try:
        if ext=='.txt':text=raw.decode('utf-8-sig')
        elif ext=='.docx':
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if sum(x.file_size for x in z.infolist())>40*1024*1024:raise ValueError('Nội dung giải nén quá lớn.')
            from docx import Document
            d=Document(io.BytesIO(raw));text='\n'.join(p.text for p in d.paragraphs)
            text+='\n'+'\n'.join(' | '.join(cell.text for cell in row.cells) for table in d.tables for row in table.rows)
        else:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(raw))
            if len(reader.pages)>150:raise ValueError('Tối đa 150 trang.')
            text='\n'.join(p.extract_text() or '' for p in reader.pages)
        text=text.strip()[:120000]
        if len(text)<30:raise ValueError('Không trích xuất được đủ văn bản; tệp scan cần OCR trước.')
    except Exception as e:raise HTTPException(422,'Không đọc được tài liệu. Dùng TXT UTF-8, PDF có văn bản hoặc DOCX hợp lệ.') from e
    id=secrets.token_hex(10);name=Path(file.filename or 'document').name[:200]
    with conn() as c:
        c.execute('INSERT INTO documents VALUES(?,?,?,?,?)',(id,name,text,'draft',now()));audit(c,'document_upload_draft',id)
    return {'id':id,'name':name,'text':text,'status':'draft','message':'Tài liệu được lưu ở bản nháp. Tạo câu trả lời, gắn nguồn chính thức và duyệt trước khi dùng.'}
@app.put('/api/admin/ai',dependencies=[Depends(admin)])
def ai_settings(body:AISettings):
    if body.provider not in ('ollama','openai-compatible'):raise HTTPException(422,'Nhà cung cấp không hợp lệ.')
    if body.provider=='openai-compatible':
        u=urlparse(body.base_url)
        import ipaddress
        if u.scheme!='https' or not u.hostname or u.username or u.password:raise HTTPException(422,'API cần địa chỉ HTTPS hợp lệ.')
        try:
            if not ipaddress.ip_address(u.hostname).is_global:raise HTTPException(422,'API bên ngoài phải dùng địa chỉ công khai.')
        except ValueError:pass
        if u.hostname in ('localhost','metadata.google.internal') or u.hostname.endswith(('.local','.internal')):raise HTTPException(422,'Tên máy API không hợp lệ.')
    r=body.model_dump();old=read_settings()
    if r['api_key'] is None:r['api_key']=old.get('api_key','')
    p=ROOT/'data'/'ai-settings.json';tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(r,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(p)
    with conn() as c:audit(c,'ai_settings_changed',r['provider'])
    return {'ok':True}
@app.get('/')
def index():return FileResponse(STATIC/'index.html',headers={'Cache-Control':'no-cache'})
app.mount('/static',StaticFiles(directory=STATIC),name='static')
