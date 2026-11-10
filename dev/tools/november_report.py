"""Local evidence report and explicitly invoked adoption; never uploads."""
from pathlib import Path
import argparse,json,runpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261101'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--adopt',action='store_true')
    args=p.parse_args()
    if not (OUT/'inspection.json').exists():
        # Initial incumbent was verified before the first November submission.
        initial=json.loads((ROOT/'data/experiments/blackbox_20261031/inspection.json').read_text(encoding='utf-8'))
        (OUT/'inspection.json').write_text(json.dumps(initial,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.adopt:
        path=ROOT/'dev/tools/adopt_blackbox_best_20261031.py'
        code=path.read_text(encoding='utf-8').replace('blackbox_20261031','blackbox_20261101').replace('2026-10-31','2026-11-01')
        ns={'__name__':'november_adoption','__file__':str(path)}
        exec(compile(code,str(path),'exec'),ns)
        ns['main']()
    state=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
    results=json.loads((OUT/'results.json').read_text(encoding='utf-8')) if (OUT/'results.json').exists() else []
    lines=['# 2026-11-01 线上结构优化','',
           '用户授权用完今日30次线上机会。后续禁止同代码复测；固定种子的随机策略可复现，改变规则或种子才是新候选。此前已投递的基线对照只取回原作品结果。以正式总分选择，本地仅检查编译、交互、Q/O和真实停车。未知结果恢复同一作品，不重复上传。',
           '',f"初始最高212686；当前最高{state['best_score']}。总分不能恢复逐例零分原因或数量。",
           '', '| 候选 | 父版 | 正式总分 | 分差 | 采用 | 状态 |','|---|---:|---:|---:|---|---|']
    for r in results:
        status='排除误归属；本候选成绩未确认，不重传' if r.get('failure_kind')=='attribution_rejected' else r['state']
        lines.append(f"| {r['name']} | {r['parent_score']} | {r.get('score')} | {r.get('delta')} | {r.get('accepted')} | {status} |")
    pending=[dict(name=r['name'],state=r['state'],job_id=r.get('job_id')) for r in state['rounds'] if r['state'] not in ['completed','failed']]
    excluded=[r['name'] for r in results if r.get('failure_kind')=='attribution_rejected']
    def scored(name):
        return next((r for r in results if r['name']==name and r['state']=='completed'),None)
    resolved=scored('resolved_descent_half_scout')
    resolved_long=scored('resolved_descent_long')
    if resolved:
        lines+=['',f"已确认有效机制：在两侧半高点均已读到、最近至少三次显著下降且无上升/回升时，才缩短峰后探测。正式总分{resolved['score']}，相对212686提高{resolved['score']-212686}；不能仅从总分确定哪些样例或哪一项扣分改善。"]
    if resolved and resolved_long:
        delta=resolved_long['score']-212686
        lines+=['',f"互斥N分组：N>650已直接测得贡献{delta:+d}；N<=650合计条件推断{resolved['score']-212686-delta:+d}。条件推断利用相同基线和仅按N启用的确定性策略，不等于逐例成绩；后续不同机制的组合收益仍须实测。"]
    quota_path=OUT/'final_quota.json'
    if quota_path.exists():
        quota=json.loads(quota_path.read_text(encoding='utf-8'))
        lines+=['',f"结束时实时核对：{quota['used']}/{quota['maximum']}，剩余{quota['remaining']}次；记录时间{quota['captured_at']}。不为恢复最后上传文件而复测最高分源码。"]
    if excluded:
        lines+=['', '归属更正：2026-11-01 02:04:15 的146180分由用户明确说明为其手动实验，已从正式成绩索引及候选拟合中剔除。不能据此判断减半探测成功或失败；宽缓上升节省查询实验是独立候选。原观察与源码保存在 attribution_rejections 中，不修改源码字节。']
    doubao=next((r for r in results if r['name']=='doubao_casefix' and r['state']=='completed'),None)
    if doubao:
        lines+=['',f"豆包代码测试：修正版正式总分{doubao['score']}，相对212686差{doubao['score']-212686:+d}。保留[用户原文](doubao_original.cpp)；[测试版本](doubao_casefix.cpp)只修正case3..6为合法switch分支，并处理告警，不重新设计其采样或评分。四处分支修正会改变执行行为，不能将这个分数称作未经修改原文的成绩。",
                '', '源码审查发现：transientSpikes只收录已读位置，但pool.add在已读位置直接返回，且所有调用均未传transient=true，所以毛刺降权条件无法命中；弱证书只记录级别、没有停止作用；候选覆盖分支的(i*candidates.size())%candidates.size()恒为0。这些是可由源码确定的实现问题，不能由总分断言各自造成多少损失。']
    lines+=['',f'待确认：{pending}', '', '[最高分入口](../../../main.cpp) · [前一日结果](../blackbox_20261031/README.md)']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(best=state['best_score'],confirmed_scores=sum(r.get('state')=='completed' and type(r.get('score')) is int for r in results),excluded=excluded,attempts=state.get('delivered_attempt_jobs',0),pending=pending),ensure_ascii=False))

if __name__=='__main__':
    main()
