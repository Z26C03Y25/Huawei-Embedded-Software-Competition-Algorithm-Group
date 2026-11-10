"""Read live exhausted quota and verify the saved winner; never uploads."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'dev'),str(ROOT/'automation')]
from online_judge.browser import connect,load_config
from tools.online_round_20261030 import parse_quota

OUT=ROOT/'data/experiments/blackbox_20261101'
state=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
if any(r['state'] not in ['completed','failed'] for r in state['rounds']):
    raise RuntimeError('Unresolved experiment; resume before finalizing')
canonical=ROOT/f"data/versions/main_online_{state['best_score']}.cpp"
for source in [ROOT/'main.cpp',OUT/'best.cpp',canonical]:
    if hashlib.sha256(source.read_bytes()).hexdigest()!=state['best_sha256']:
        raise RuntimeError('Winner source mismatch: '+str(source))
with connect(load_config()) as page:
    records=page.records(refresh=True)
    if any(r.status=='pending' for r in records):
        raise RuntimeError('Platform still judging; finish original work before stopping')
    quota=parse_quota(page.page.locator('body').inner_text())
if quota['beijing_date']!='2026-11-01' or quota['remaining']!=0:
    raise RuntimeError('Today is not yet exhausted: '+json.dumps(quota,ensure_ascii=False))
(OUT/'final_quota.json').write_text(json.dumps(quota,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(quota=quota,best_score=state['best_score'],best_sha256=state['best_sha256'],
                     gain=state['best_score']-state['initial_best_score'],no_upload=True),ensure_ascii=False))
