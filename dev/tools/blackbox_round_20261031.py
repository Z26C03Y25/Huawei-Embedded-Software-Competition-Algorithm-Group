"""A single online-total experiment. Reuses immutable snapshots and job recovery.

Local checks cover protocol only. No local score is used for selection.
Never replaces the externally edited workspace main.cpp.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'dev'))
from tools import online_round_20261030 as base

# Keep the established upload identity, lock, quota and recovery implementation.
# Only the dated output, recorded authorization, parent and promotion destination
# differ. Fail rather than silently patching an unexpected implementation.
source = Path(base.__file__).read_text(encoding='utf-8')
changes = [
    ('DATE = "2026-10-30"', 'DATE = "2026-10-31"'),
    ('data/experiments/online_20261030', 'data/experiments/blackbox_20261031'),
    ('AUTHORIZATION = ["先启动初始化等我登录，然后你根据线上结果持续优化30次争取达到第一名", "已登录‘"]',
     'AUTHORIZATION = ["本地数据测试可能不准，你根据线上成绩拟合，只能黑盒测试，你只会拿到总分，去拟合", "先启动初始化等我登录，然后你根据线上结果持续优化30次争取达到第一名"]'),
    ('main = (self.root / "main.cpp").read_bytes()',
     'main = (self.root / "data/versions/main_online_210599.cpp").read_bytes()'),
    ('main = self.root / "main.cpp"', 'main = self.out / "best.cpp"'),
    ('parent = (self.out / "best.cpp").read_bytes()',
     'metadata = read(Path(source).with_suffix(".metadata.json"), {})\n        parent = Path(metadata["parent"]).read_bytes() if metadata.get("parent") else (self.out / "best.cpp").read_bytes()'),
    ('if digest(parent) != self.state["best_sha256"]:',
     'if digest(parent) not in {r.get("sha256") for r in read(self.index_path, [])}:'),
    ('parent_sha256=digest(parent), parent_score=self.state["best_score"],',
     'parent_sha256=digest(parent), parent_score=max(r["score"] for r in read(self.index_path, []) if r.get("sha256")==digest(parent)),')
]
for old, new in changes:
    if old not in source:
        raise RuntimeError('Round controller interface changed; review required: '+old)
    source=source.replace(old,new)

if __name__=='__main__':
    # __file__ must stay at the original module location for ROOT calculation.
    namespace={'__name__':'blackbox_round_impl','__file__':base.__file__}
    exec(compile(source,base.__file__,'exec'),namespace)
    raise SystemExit(namespace['main']())
