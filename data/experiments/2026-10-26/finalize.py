"""Close today's confirmed run, protect the best bytes and refresh learning docs."""
from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent
state=json.loads((D/'session.json').read_text(encoding='utf-8'));assert state['quota']['date']=='2026-10-26' and state['quota']['remaining']==0
assert len(state['results'])==30
rows=json.loads((ROOT/'data/versions/online_search/results.json').read_text(encoding='utf-8'));best=max(rows,key=lambda r:r['score'])
for row in state['results']:
    job=json.loads((ROOT/'automation/online_judge/runs'/row['job_id']/'job.json').read_text(encoding='utf-8'))
    assert job['state']=='completed' and job['score']==row['score']
    assert hashlib.sha256(Path(job['snapshot_path']).read_bytes()).hexdigest()==row['sha256']
    assert job.get('bound_submission_id')==row['submission_id']
score=best['score'];digest=best['sha256'];snapshot=ROOT/'automation/online_judge/runs'/best['job_id']/'main.cpp';contents=snapshot.read_bytes()
assert hashlib.sha256(contents).hexdigest()==digest and (ROOT/'main.cpp').read_bytes()==contents
alias=ROOT/f'data/versions/main_online_{score}.cpp'
if alias.exists():assert alias.read_bytes()==contents
else:alias.write_bytes(contents)
p=ROOT/'data/versions/manifest.json';manifest=json.loads(p.read_text(encoding='utf-8'))
for entry in manifest['files']:assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256']
path=str(alias.relative_to(ROOT)).replace('\\','/')
if not any(r['path']==path for r in manifest['files']):manifest['files'].append(dict(path=path,score=score,sha256=digest,job_id=best['job_id'],submission_id=best['submission_id']))
manifest.update(recorded_at='2026-10-26',recorded_best_score=score);p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'README.md';s=p.read_text(encoding='utf-8');s=re.sub(r'已记录最高正式总分 \*\*\d+\*\*（\d{4}-\d{2}-\d{2}）。',f'已记录最高正式总分 **{score}**（2026-10-26）。',s,count=1);s=s.replace('data/versions/main_online_199291.cpp',path);p.write_text(s,encoding='utf-8')
p=ROOT/'docs/README.en.md';s=p.read_text(encoding='utf-8');s=re.sub(r'\*\*\d+ as of \d{4}-\d{2}-\d{2}\*\*',f'**{score} as of 2026-10-26**',s,count=1);p.write_text(s,encoding='utf-8')
p=ROOT/'docs/README.md';s=p.read_text(encoding='utf-8');s=s.replace('入口与199291归档字节相同',f'入口与{score}归档字节相同');p.write_text(s,encoding='utf-8')
p=ROOT/'data/versions/README.md';s=p.read_text(encoding='utf-8');s=s.replace('以下“当前”状态对应2026-10-25的快照；后续实验以正式记录为准。','当前入口采用2026-10-26最高正式字节；历史分数保留对照。')
s=s.replace('| main_online_199291.cpp |',f'| [main_online_{score}.cpp](main_online_{score}.cpp) | 2026-10-26 最高正式分归档 | **{score}** |\n| main_online_199291.cpp |',1)
s=s.replace('| 仓库根目录 main.cpp | 与 main_online_199291.cpp 完全一致 | **199291** |',f'| 仓库根目录 main.cpp | 与 main_online_{score}.cpp 完全一致 | **{score}** |')
s=s.replace('归档 SHA256：','归档 SHA256：\n\n'+f'- main_online_{score}.cpp：{digest}。',1).replace('当前：2026-10-25 01:27:22','历史最高（10月25）：2026-10-25 01:27:22')
s += f"\n当前：{best['submitted_at']}（北京时间）的作品 {best['submission_id']} 已独立连续确认 {score}。本日30次全部正式完成，官方30/30、剩余0。见[当日分析](../../docs/daily_research/2026-10-26-analysis.md)。\n";p.write_text(s,encoding='utf-8')
p=ROOT/'docs/concepts/solver-walkthrough.md';s=p.read_text(encoding='utf-8');s=s.replace('本文对应已记录199291版。',f'本文对应已记录{score}版；[2026-10-26分析](../daily_research/2026-10-26-analysis.md)解释参数的正式证据。')
s=s.replace('平滑、低波动且没有明显竞争峰时，三点二次顶点与稳健多点拟合一致，可在预测中心±6内验证。满足收尾条件后停车，否则回到常规精修。','平滑、显著且没有明显竞争峰时，比较三点二次顶点v1与±24邻域的多点拟合顶点v2，要求abs(v1-v2)<10。先将区间向外取整为[floor(min(v1,v2))-3, ceil(max(v1,v2))+3]，并保留预测中心±3，再截断到已探索范围。在该区间逐点读取原始值；原始冠军严格处于窗口内部才可收尾，否则回到常规半径8的精修。')
p.write_text(s,encoding='utf-8')
p=ROOT/'docs/reference/known-limitations.md';s=p.read_text(encoding='utf-8');s=s.replace('最后+882分同时修改模型收尾与常规半径；独立贡献尚待消融。更小窗口、更多竞争区和新退火场景也不能在正式实验之前称为有效改进。','此前882分的消融已完成：半径12时模型贡献32分，半径缩小贡献775分；最新版本继续使用自适应原始值核查。详见[正式消融与反例修复](../daily_research/2026-10-26-analysis.md)。更多竞争区和新退火场景仍须按正式分数评判。')
s=s.replace('## 尚未验证的方向','新增的两顶点分歧反例已冻结到data/experiments/2026-10-26/counterexamples，并加入精确命中诊断。它已由自适应核查修复；上述旧反例仍保留。\n\n## 尚未验证的方向');p.write_text(s,encoding='utf-8')
for filename in ['持续线上优化总结.md','下一轮优化分析.md']:
    p=ROOT/'docs'/filename;s=p.read_text(encoding='utf-8');header=f'> 2026-10-26更新：最高正式分{score}，今日30/30已确认完成；最新[当日分析](daily_research/2026-10-26-analysis.md)与[运行记录](daily_research/2026-10-26.md)已保存。以下保留10月25日分析的原始上下文。\n\n'
    if not s.startswith('> 2026-10-26更新：'):p.write_text(header+s,encoding='utf-8')
summary=dict(date='2026-10-26',new_submissions=len(state['results']),official_quota=state['quota'],best_score=score,previous_best=199291,improvement=score-199291,target_met=score>=200000,continued_after_target=True,best_job_id=best['job_id'],best_submission_id=best['submission_id'],best_sha256=digest,best_source=path,unresolved_jobs=0,main_restored_to_formal_best=True,status='daily_quota_exhausted_offline_preparation',leader_reference=dict(score=220045,team='遥遥领先',refreshed_at='2026-10-25T23:50:00+08:00',captured_at='2026-10-26T01:40:51+08:00',scope='first_page',network_reads_today=1),validation='Pending final offline core/diagnostic check; synthetic results never replace official totals')
(D/'final_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(best_score=score,improvement=score-199291,sha256=digest,submissions=30,quota=state['quota']),ensure_ascii=True))
