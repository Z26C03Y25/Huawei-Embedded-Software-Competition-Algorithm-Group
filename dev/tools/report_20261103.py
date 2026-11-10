"""Summarize November3 official results; optionally adopt a verified improvement."""
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261103'
s=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
if '--adopt' in sys.argv and s['best_score']>s['initial_best_score']:
    inspection=OUT/'inspection.json'
    if not inspection.exists():
        inspection.write_text(json.dumps(dict(main_sha256=s['initial_best_sha256'],
            note='Initial main bytes inspected before first November3 upload.'),indent=2)+'\n',encoding='utf-8')
    path=ROOT/'dev/tools/adopt_blackbox_best_20261031.py'
    code=path.read_text(encoding='utf-8').replace('blackbox_20261031','blackbox_20261103').replace('2026-10-31','2026-11-03')
    ns={'__name__':'november3_adoption','__file__':str(path)}
    exec(compile(code,str(path),'exec'),ns); ns['main']()
rows=json.loads((OUT/'results.json').read_text(encoding='utf-8')) if (OUT/'results.json').exists() else []
pending=[r for r in s['rounds'] if r['state'] not in ['completed','failed']]
lines=['# 2026-11-03 线上实验','',
       f"起始{s['initial_best_score']}；当前最高{s['best_score']}。位置先验来自用户提供的102例主峰分布；正式选择仍只依据线上总分。",'',
       '| 候选 | 提交时间（北京时间） | 状态 | 父版 | 正式总分 | 差值 |','|---|---|---|---:|---:|---:|']
for r in rows:
    lines.append(f"| {r['name']} | {r.get('submitted_at','—')} | 已确认 | {r['parent_score']} | {r.get('score')} | {r.get('delta')} |")
for r in pending:
    lines.append(f"| {r['name']} | {r.get('submit_started_at','—')} | 待判分 | {r['parent_score']} | — | — |")
lines+=['',f"已确认{len(rows)}条；待判{len(pending)}条。相同源码不复测；不确定任务只恢复原任务。",'',
        '[位置先验设计](../peak_prior_20261102/README.md) · [前一天实验](../blackbox_20261102/README.md)']
(OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
nav=ROOT/'docs/research/README.md'; link='[2026-11-03位置先验线上实验](../../data/experiments/blackbox_20261103/README.md)'
text=nav.read_text(encoding='utf-8')
if link not in text: nav.write_text(text+'\n'+link+'\n',encoding='utf-8')
print(json.dumps(dict(best=s['best_score'],confirmed=len(rows),pending=[r['name'] for r in pending]),ensure_ascii=False))
