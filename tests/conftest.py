import os,tempfile,shutil,json,hashlib,secrets,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]
TEST_ROOT=Path(tempfile.mkdtemp(prefix='haui-tests-'))
for folder in ['data','models','reports']:
    (TEST_ROOT/folder).mkdir()
for name in ['faqs.json']:
    shutil.copy(SOURCE/'data'/name,TEST_ROOT/'data'/name)
for p in (SOURCE/'reports').glob('*.json'):shutil.copy(p,TEST_ROOT/'reports'/p.name)
for p in (SOURCE/'models').glob('*.joblib'):shutil.copy(p,TEST_ROOT/'models'/p.name)
os.environ['STUDENT_ROOT']=str(TEST_ROOT)
sys.path.insert(0,str(SOURCE))
from app.main import password_hash,init_db
salt=secrets.token_hex(16)
(TEST_ROOT/'data'/'admin-auth.json').write_text(json.dumps({'salt':salt,'hash':password_hash('Test-Admin-Password-2026',salt)}))
init_db()
import pytest
from fastapi.testclient import TestClient
from app.main import app
@pytest.fixture(scope='session')
def client():
    with TestClient(app) as c:yield c
@pytest.fixture
def logged(client):
    client.cookies.clear()
    r=client.post('/api/admin/login',json={'password':'Test-Admin-Password-2026'});assert r.status_code==200
    return client

def pytest_sessionfinish(session,exitstatus):shutil.rmtree(TEST_ROOT,ignore_errors=True)
