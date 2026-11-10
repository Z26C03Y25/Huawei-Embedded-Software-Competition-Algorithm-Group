"""2026-11-06 wave-only judging, one frozen source at a time."""
from pathlib import Path
import hashlib
import json
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/experiments/blackbox_20261106'
QUARANTINE = {'20261104T064432532409Z_831debfc7899', '20261105T061334716758Z_98f6d7520020'}
OLD_SERVER = '497612b60ba943ecb77f919d98f3289a'

def replace(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError(f'Expected one anchor: {old}')
    return source.replace(old, new, 1)

def judge():
    sha = sys.argv.pop(2)
    sys.argv.pop(1)
    path = ROOT / 'automation/online_judge/judge.py'
    sys.path[:0] = [str(ROOT / 'automation'), str(ROOT / 'dev')]
    source = path.read_text(encoding='utf-8')
    source = replace(source, 'if other_active:', f'if any(j["job_id"] not in {QUARANTINE!r} for j in other_active):')
    source = replace(source, 'if any(row.status == "pending" for row in baseline):',
                     f'if any(row.status == "pending" and row.submission_id != {OLD_SERVER!r} for row in baseline):')
    anchor = '            state = store.observe(job, records)'
    source = replace(source, anchor, '''            from tools.submission_attribution import validate_submission_timing
            if job.get("submission_attempt_at"):
                eligible = []
                for row in records:
                    try:
                        validate_submission_timing(dict(job, record=row.to_dict()))
                    except (ValueError, KeyError):
                        continue
                    eligible.append(row)
                records = eligible
''' + anchor)
    if sys.argv[1] == 'submit':
        path_to_upload = Path(sys.argv[sys.argv.index('--file') + 1])
        if hashlib.sha256(path_to_upload.read_bytes()).hexdigest() != sha:
            raise RuntimeError('Frozen candidate hash changed')
        if time.strftime('%Y-%m-%d', time.gmtime(time.time() + 8 * 3600)) != '2026-11-06':
            raise RuntimeError('The Beijing submission day has ended')
    ns = {'__name__': 'wave_judge', '__file__': str(path)}
    exec(compile(source, str(path), 'exec'), ns)
    return ns['main']()

def controller():
    path = ROOT / 'dev/tools/online_round_20261030.py'
    source = path.read_text(encoding='utf-8').replace('online_20261030"', 'blackbox_20261106"')
    source = replace(source, 'DATE = "2026-10-30"', 'DATE = "2026-11-06"')
    source = replace(source, 'if active:', f'if any(j["job_id"] not in {QUARANTINE!r} for j in active):')
    source = replace(source, 'if any(row.status == "pending" for row in records):',
                     f'if any(row.status == "pending" and row.submission_id != {OLD_SERVER!r} for row in records):')
    source = replace(source, 'str(self.root / "automation/online_judge/judge.py"), *args',
                     'str(self.root / "dev/tools/wave_round_20261106.py"), "--judge", entry["sha256"], *args')
    source = replace(source, '            started = time.monotonic()\n            entry["wait_windows"]',
                     '''            if entry.get("wait_windows", 0) >= 3:
                print("No confirmed score in three windows; continue by resuming the same job.", flush=True)
                return 2
            started = time.monotonic()
            entry["wait_windows"]''')
    source = replace(source, '                main.write_bytes(contents)\n', '')
    source = replace(source, '                if digest(main.read_bytes()) not in {self.state["best_sha256"], entry["sha256"]}:',
                     '                if digest(main.read_bytes()) not in {self.state["initial_best_sha256"], self.state["best_sha256"], self.state.get("wave_best", {}).get("sha256"), self.state.get("wave_provisional", {}).get("sha256"), entry["sha256"]}:')
    source = replace(source, 'AUTHORIZATION = ["先启动初始化等我登录，然后你根据线上结果持续优化30次争取达到第一名", "已登录‘"]',
                     'AUTHORIZATION = ["两小时快速耗尽30次机会，可以根据提交时间实现批量提交，但是提交方案不能一样。现在不能打表了，你只能根据波形自己决定"]')
    ns = {'__name__': 'wave_controller', '__file__': str(path)}
    exec(compile(source, str(path), 'exec'), ns)
    return ns

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--judge':
        return judge()
    ns = controller()
    if '--resume' in sys.argv:
        job_id = sys.argv[sys.argv.index('--resume')+1]
        with ns['SubmissionLock'](OUT / '.round.lock'):
            instance = ns['Controller']()
            for row in instance.state['rounds']:
                if row.get('job_id') == job_id and row.get('state') not in {'completed', 'failed'}:
                    row['wait_windows'] = 0
                    instance.persist()
            return instance.resume(job_id)
    return ns['main']()

if __name__ == '__main__':
    raise SystemExit(main())
