"""Fit additive, disjoint-N action effects from official totals only; no upload."""
from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261031'

def main():
    results=json.loads((OUT/'results.json').read_text(encoding='utf-8')) if (OUT/'results.json').exists() else []
    state=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
    rows={r['name']:r for r in results if r.get('state')=='completed'}
    models={}
    for prefix in ['continue','gap_audit_16','neighbor_confirm_3','neighbor_clean_3',
                   'inline_triplets_raw','inline_triplets_clean','interval_sweep_retry_v2']:
        effects={}
        model_baseline=212320 if prefix=='interval_sweep_retry_v2' else 210599
        for group in ['all','short','mid','long','midlong','shortmid','shortlong']:
            row=rows.get(prefix+'_'+group) or (rows.get(prefix) if group=='all' else None)
            if row:
                effects[group]=row['delta']
        inferred={}
        if 'all' in effects:
            missing=[g for g in ['short','mid','long'] if g not in effects]
            if len(missing)==1:
                inferred[missing[0]]=effects['all']-sum(effects[g] for g in ['short','mid','long'] if g in effects)
        models[prefix]=dict(measured_deltas=effects,inferred_deltas=inferred,
                            assumption='Same frozen parent, fixed hidden cases and stable execution. Inferred cells require direct validation before adoption.')
        if 'all' in effects and 'short' in effects:
            models[prefix]['two_group_fit']={'N<=500':effects['short'],
                                            'N>500':effects['all']-effects['short']}
            models[prefix]['two_group_predicted_score']=model_baseline+max(0,effects['short'])+max(0,effects['all']-effects['short'])
            if 'midlong' in effects:
                models[prefix]['two_group_validation_residual']=effects['midlong']-(effects['all']-effects['short'])
        coefficients={g:effects.get(g,inferred.get(g)) for g in ['short','mid','long']}
        if all(v is not None for v in coefficients.values()):
            models[prefix]['fitted_group_coefficients']=coefficients
            models[prefix]['predicted_positive_groups']=[g for g,v in coefficients.items() if v>0]
            models[prefix]['predicted_score']=model_baseline+sum(max(0,v) for v in coefficients.values())
            models[prefix]['prediction_is_official_result']=False
        if all(k in effects for k in ['all','short','mid','long']):
            models[prefix]['additivity_residual']=effects['all']-sum(effects[g] for g in ['short','mid','long'])
    band_fit={}
    if 'triplets_upper_mid' in rows:
        upper=rows['triplets_upper_mid']['score']-210599
        lower=212320-rows['triplets_upper_mid']['score']
        band_fit={'501..575':lower,'576..650':upper}
        if 'triplet_band_501_538' in rows:
            left=rows['triplet_band_501_538']['score']-210599
            band_fit.update({'501..538':left,'539..575':lower-left})
        if 'triplet_band_576_613' in rows:
            left=rows['triplet_band_576_613']['score']-210599
            band_fit.update({'576..613':left,'614..650':upper-left})
    payload=dict(official_only=True,baseline_score=210599,best_score=state['best_score'],models=models,band_fit=band_fit,
                 completed=len(rows),pending=[{'name':r['name'],'job_id':r.get('job_id'),'state':r['state']}
                                             for r in state['rounds'] if r['state'] not in ['completed','failed']],
                 workspace_main_sha256=hashlib.sha256((ROOT/'main.cpp').read_bytes()).hexdigest())
    confirmations=[{k:r.get(k) for k in ['job_id','submission_id','score','sha256']}
                   for r in results if r.get('state')=='completed' and r.get('sha256')==state['best_sha256']
                   and r.get('score')==state['best_score']]
    payload['attempted_jobs']=state.get('delivered_attempt_jobs',0)
    payload['failed_jobs']=sum(r.get('state')=='failed' for r in results)
    payload['best_source_confirmations']=confirmations
    payload['independent_best_repeat_confirmed']=len({r['submission_id'] for r in confirmations if r['submission_id']})>=2
    (OUT/'fit.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 2026-10-31 线上总分黑盒实验','',
           '本地只检查编译、交互、Q/O及停车，不用合成得分挑选候选。每次只上传冻结源码一次，超时恢复原作业。',
           '', '可核验父版为210599。页面另有210666记录，但暂未找到绑定源码，不能把其他源码标成该分数。原工作区main.cpp在采用确认优胜版时另存备份，采用信息见adoption.json；实验优胜版亦单独归档。',
           '', f"已投递{payload['attempted_jobs']}次，失败{payload['failed_jobs']}次；最高{state['best_score']}；同源码不同作品独立重测确认：{payload['independent_best_repeat_confirmed']}。",
           '', '| 实验 | 正式总分 | 相对父版 | 接纳 |','|---|---:|---:|---|']
    for row in results:
        lines.append(f"| {row['name']} | {row.get('score')} | {row.get('delta')} | {row.get('accepted')} |")
    for row in payload['pending']:
        lines.append(f"| {row['name']} | 待确认：{row['state']} | — | 未接纳 |")
    lines += ['', '## 分组拟合', '',
              '同一改动按N≤500、501～650、>650互斥启用，拟合各组的总得分改变量。全N改变量应为三组之和；它不提供逐例峰形或零分归因。未直接测试的推断不得当作正式成绩。', '']
    for name,model in models.items():
        lines += [f'- {name}：已测{model["measured_deltas"]}；条件推断{model["inferred_deltas"]}。']
        if 'two_group_fit' in model:
            lines += [f'  二分拟合：{model["two_group_fit"]}；仅启用正收益组的预测总分{model["two_group_predicted_score"]}，不是新正式成绩。']
    lines += ['', '进一步互斥N分段的条件拟合：'+str(band_fit)+'。由差值推断的单段不是单独正式成绩；组合需要直接验证。',
              '', '相邻点用于核查连续峰与孤立高点。原始数组的最高值始终保留；任何中位数/清洗只允许影响趋势建议，不能替代正式目标。',
              '', 'raw/clean对照保持相同的动作生成规则，但清洗会影响后续分支和查询位置。因此比较的是完整策略效果，不能解释成在完全相同数据上的独立降噪收益。',
              '', '这是一组黑盒策略对照，未声称能反演隐藏数组或由总分证明减少了多少零分。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
