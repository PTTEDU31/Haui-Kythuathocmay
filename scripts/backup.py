import sqlite3,tarfile,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];dest=ROOT/'backups';dest.mkdir(exist_ok=True)
stamp=time.strftime('%Y%m%d-%H%M%S');snapshot=dest/f'snapshot-{stamp}.db'
with sqlite3.connect(ROOT/'data'/'student.db') as src,sqlite3.connect(snapshot) as dst:src.backup(dst)
os.chmod(snapshot,0o600)
out=dest/f'backup-{stamp}.tar.gz'
with tarfile.open(out,'w:gz') as tar:
    tar.add(snapshot,arcname='data/student.db')
    for name in ['data/admin-auth.json','data/ai-settings.json','data/faqs.json','models/intent.joblib','reports/experiments.json']:
        p=ROOT/name
        if p.exists():tar.add(p,arcname=name)
out.chmod(0o600);snapshot.unlink()
backups=sorted(dest.glob('backup-*.tar.gz'))
for old in backups[:-14]:old.unlink()
print(out)
