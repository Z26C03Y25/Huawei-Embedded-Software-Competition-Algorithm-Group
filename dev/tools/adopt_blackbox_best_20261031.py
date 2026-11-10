"""Install the confirmed online winner, preserving the original workspace source."""
from pathlib import Path
import hashlib, json, re
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/experiments/blackbox_20261031'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    state=json.loads((OUT/'state.json').read_text(encoding='utf-8'))
    if any(r['state'] not in ['completed','failed'] for r in state['rounds']):
        raise RuntimeError('Finish the existing online job before adopting')
    inspection=json.loads((OUT/'inspection.json').read_text(encoding='utf-8'))
    adoption_path=OUT/'adoption.json'
    previous=json.loads(adoption_path.read_text(encoding='utf-8')) if adoption_path.exists() else {}
    if previous.get('original_sha256'):
        inspection['main_sha256']=previous['original_sha256']
    main_path=ROOT/'main.cpp'
    old=main_path.read_bytes()
    if sha(old) not in {inspection['main_sha256'],previous.get('adopted_sha256'),state['best_sha256']}:
        raise RuntimeError('main.cpp changed during this experiment; preserved without overwrite')
    best=(OUT/'best.cpp').read_bytes()
    if sha(best)!=state['best_sha256']:
        raise RuntimeError('Best-source hash mismatch')
    manifest=json.loads((ROOT/'data/versions/manifest.json').read_text(encoding='utf-8'))
    if not any(r['sha256']==sha(best) and r.get('score')==state['best_score'] for r in manifest['files']):
        raise RuntimeError('Best-source official archive binding missing')
    saved=OUT/'workspace_main_before.cpp'
    if not saved.exists():
        saved.write_bytes(old)
    if sha(saved.read_bytes())!=inspection['main_sha256']:
        raise RuntimeError('Original-source backup hash mismatch')
    main_path.write_bytes(best)
    score=state['best_score']
    root_readme=ROOT/'README.md'
    text=root_readme.read_text(encoding='utf-8')
    text,count=re.subn(r'已记录最高正式总分 .*',
        f'已记录最高正式总分 **{score}**（2026-10-31，正式评测确认）。[最高分源码](data/versions/main_online_{score}.cpp) · [本轮线上黑盒实验](data/experiments/blackbox_20261031/README.md)',text,count=1)
    if count!=1:
        raise RuntimeError('README score anchor changed')
    root_readme.write_text(text,encoding='utf-8')
    nav=ROOT/'docs/README.md'
    text=nav.read_text(encoding='utf-8')
    text=re.sub(r'最新研究：.*',
        f'最新研究：[线上总分黑盒拟合](../data/experiments/blackbox_20261031/README.md)（2026-10-31），已确认最高{score}。前置分析见[多维特征与算法设计](research/README.md)。',text,count=1)
    text=re.sub(r'当前入口与\d+归档字节相同。',f'当前入口与{score}归档字节相同。',text)
    nav.write_text(text,encoding='utf-8')
    versions=ROOT/'data/versions/README.md'
    text=versions.read_text(encoding='utf-8')
    text=re.sub(r'本页分数是已记录的正式反馈，.*',
        f'本页分数是已记录的正式反馈，不是本地重放官方隐藏数据的结果。当前入口采用正式{score}的已核验字节。历史分数保留对照，已评分源码保持原字节，新实验创建新文件。',text,count=1)
    text=re.sub(r'\| 仓库根目录 main.cpp \|.*',
        f'| 仓库根目录 main.cpp | 与 main_online_{score}.cpp 完全一致 | **{score}** |',text,count=1)
    if f'[main_online_{score}.cpp]' not in text:
        text=text.replace('| --- | --- | --- |',
            f'| --- | --- | --- |\n| [main_online_{score}.cpp](main_online_{score}.cpp) | 2026-10-31 线上黑盒拟合确认版 | **{score}** |',1)
    text=text.replace('当前最高：2026-10-27','历史最高：2026-10-27')
    versions.write_text(text,encoding='utf-8')
    record=dict(adopted_score=score,adopted_sha256=sha(best),original_sha256=inspection['main_sha256'],
                original_backup=str(saved.relative_to(ROOT)),best_job_id=state.get('best_job_id'))
    adoption_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
