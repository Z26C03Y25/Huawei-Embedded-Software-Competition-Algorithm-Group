"""Run a bounded sequential batch, reassessing immediately on a new best."""
from pathlib import Path
import sys,json,importlib.util
p=Path(__file__).with_name('session.py');spec=importlib.util.spec_from_file_location('daily',p);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
for trial in range(int(sys.argv[1]) if len(sys.argv)>1 else 3):
    s=json.loads(d.STATE.read_text(encoding='utf-8'));before=len(s['results']);best=max(199291,*[r['score'] for r in s['results']])
    d.main()
    s=json.loads(d.STATE.read_text(encoding='utf-8'))
    if len(s['results'])==before or max(r['score'] for r in s['results'])>best:break
