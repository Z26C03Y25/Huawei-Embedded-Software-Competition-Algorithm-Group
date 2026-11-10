"""Summarize November2 official results; optionally adopt a verified improvement."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261102'
s=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
if '--adopt' in sys.argv and s['best_score']>s['initial_best_score']:
    inspection=OUT/'inspection.json'
    if not inspection.exists():
        inspection.write_text(json.dumps(dict(main_sha256=s['initial_best_sha256'],note='Initial main bytes inspected before first November2 upload.'),indent=2)+'\n',encoding='utf-8')
    path=ROOT/'dev/tools/adopt_blackbox_best_20261031.py'
    code=path.read_text(encoding='utf-8').replace('blackbox_20261031','blackbox_20261102').replace('2026-10-31','2026-11-02')
    ns={'__name__':'november2_adoption','__file__':str(path)}
    exec(compile(code,str(path),'exec'),ns)
    ns['main']()
rows=json.loads((OUT/'results.json').read_text(encoding='utf-8')) if (OUT/'results.json').exists() else []
pending=[r for r in s['rounds'] if r['state'] not in ['completed','failed']]
lines=['# 2026-11-02 线上实验','',f"起始216258；当前最高{s['best_score']}。本地仅检查协议与预算，选择依据是线上总分；不复测相同源码。",'',
       '| 新机制 | 提交时间（北京时间） | 状态 | 父版 | 正式总分 | 差值 |','|---|---|---|---:|---:|---:|']
for r in rows:
    lines.append(f"| {r['name']} | {r.get('submitted_at','—')} | 已确认 | {r['parent_score']} | {r.get('score')} | {r.get('delta')} |")
for r in pending:
    jobpath=ROOT/'automation/online_judge/runs'/r.get('job_id','_unbound')/'job.json'
    job=json.loads(jobpath.read_text(encoding='utf-8')) if jobpath.exists() else {}
    stamp=(job.get('record') or {}).get('submitted_at',r.get('submit_started_at','—'))
    lines.append(f"| {r['name']} | {stamp} | 待判分 | {r['parent_score']} | — | — |")
    lines+=['',f"待判作品：{r['name']}；本地任务 `{r.get('job_id')}`；服务器作品 `{job.get('bound_submission_id') or '尚未绑定'}`。",'']
lines+=['',f"已确认{len(rows)}条；待判{len(pending)}条。本地timed_out表示单次等待窗口结束，不是正式零分或判题失败。",'',
        '末态补扫只在旧版确实可以返回旧赢家且该停车对所有目标都必零时触发。补扫不扩展最右位置；若旧版无法返回而当前位置可能正分，则保留原路径。',
        '', '饱和值实验仅在读到2147483647后使用精确候选集下界，并在已知平台延续时向中心加速。单次总分相同不能证明分支未触发，也不能反演逐例零分。',
        '', '[前一天实验](../blackbox_20261101/README.md)']
(OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
nav=ROOT/'docs/research/README.md'
link='[2026-11-02线上新机制实验](../../data/experiments/blackbox_20261102/README.md)'
text=nav.read_text(encoding='utf-8')
if link not in text: nav.write_text(text+'\n'+link+'\n',encoding='utf-8')
print(json.dumps(dict(best=s['best_score'],confirmed=len(rows),pending=[r['name'] for r in pending]),ensure_ascii=False))
