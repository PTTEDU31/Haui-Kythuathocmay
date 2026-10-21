"""Run via SSH when the application administrator password is forgotten."""
from pathlib import Path
import sys,getpass,json,secrets
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.main import password_hash,conn
p=getpass.getpass('New application admin password (at least 12 characters): ')
if len(p)<12 or p!=getpass.getpass('Confirm password: '):raise SystemExit('Passwords do not match or are too short.')
salt=secrets.token_hex(16);target=ROOT/'data'/'admin-auth.json';tmp=target.with_suffix('.tmp')
tmp.write_text(json.dumps({'salt':salt,'hash':password_hash(p,salt)}));tmp.chmod(0o600);tmp.replace(target)
with conn() as c:c.execute('DELETE FROM admin_sessions')
initial=ROOT/'data'/'initial-admin-password.txt'
if initial.exists():initial.unlink()
print('Password changed. All administrator sessions revoked.')
