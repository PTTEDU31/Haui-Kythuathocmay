import os,json,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.main import password_hash
p=ROOT/'data'/'admin-auth.json'
if p.exists():print('Admin authentication already initialized; preserving existing credentials.');raise SystemExit
password='HaUI-'+secrets.token_urlsafe(15)
salt=secrets.token_hex(16);p.write_text(json.dumps({'salt':salt,'hash':password_hash(password,salt)}));p.chmod(0o600)
out=ROOT/'data'/'initial-admin-password.txt';out.write_text(password);out.chmod(0o600)
print('Initialized administrator password; see protected data/initial-admin-password.txt')
