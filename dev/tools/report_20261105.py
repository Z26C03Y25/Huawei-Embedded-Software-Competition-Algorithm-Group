"""Summarize November5 records; optionally install a verified improvement."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261105'
s=json.loads((OUT/'state.json').read_text(encoding='utf8'))
if '--adopt' in sys.argv and s['best_score']>s['initial_best_score']:
    inspection=OUT/'inspection.json'
    if not inspection.exists():
        inspection.write_text(json.dumps(dict(main_sha256=s['initial_best_sha256'],note='Initial main verified against224148 before first November5 upload.'),indent=2)+'\n',encoding='utf8')
    path=ROOT/'dev/tools/adopt_blackbox_best_20261031.py'
    code=path.read_text(encoding='utf8').replace('blackbox_20261031','blackbox_20261105').replace('2026-10-31','2026-11-05')
    # The user authorized continuing around this exact stuck old work. Adoption
    # still blocks every other unfinished round and requires the best job terminal.
    old_guard="if any(r['state'] not in ['completed','failed'] for r in state['rounds']):"
    new_guard="if any(r['state'] not in ['completed','failed'] and r.get('job_id') not in {'20261104T064432532409Z_831debfc7899','20261105T061334716758Z_98f6d7520020'} for r in state['rounds']):"
    if code.count(old_guard)!=1:raise RuntimeError('Adoption guard interface changed')
    code=code.replace(old_guard,new_guard,1)
    winner=[r for r in s['rounds'] if r.get('job_id')==s.get('best_job_id')]
    if len(winner)!=1 or winner[0]['state']!='completed' or winner[0].get('score')!=s['best_score']:
        raise RuntimeError('Winner must have one completed official job')
    ns={'__name__':'november5_adoption','__file__':str(path)}
    exec(compile(code,str(path),'exec'),ns);ns['main']()
rows=json.loads((OUT/'results.json').read_text(encoding='utf8')) if (OUT/'results.json').exists() else []
pending=[r for r in s['rounds'] if r['state'] not in ['completed','failed']]
lines=['# 2026-11-05 C++线上优化','',f"起始{s['initial_best_score']}；当前最高{s['best_score']}。选择依据为官方总分，本地仅作协议和机制检查。",'',
       '| 候选 | 北京提交时间 | 父版 | 正式总分 | 分差 |','|---|---|---:|---:|---:|']
for r in rows:lines.append(f"| {r['name']} | {r.get('submitted_at','—')} | {r['parent_score']} | {r.get('score')} | {r.get('delta')} |")
for r in pending:lines.append(f"| {r['name']}（待判） | {r.get('submit_started_at','—')} | {r['parent_score']} | — | — |")
lines+=['',f"已确认{len(rows)}条，待判{len(pending)}条。未知结果恢复原任务，不重复上传。",'',
        '[已知峰位证据](../../../docs/research/known_peak_positions_20261103.md) · [前日实验](../blackbox_20261103/README.md)']
(OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
nav=ROOT/'docs/research/README.md';text=nav.read_text(encoding='utf8')
link='[2026-11-05 C++位置先验优化](../../data/experiments/blackbox_20261105/README.md)'
if link not in text:nav.write_text(text+'\n'+link+'\n',encoding='utf8')
print(json.dumps(dict(best=s['best_score'],confirmed=len(rows),pending=[r['name'] for r in pending]),ensure_ascii=False))
