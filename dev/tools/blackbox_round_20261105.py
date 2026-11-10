"""November5 single-source controller. Explicit user authorization:30 slots today."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[2]
previous=runpy.run_path(str(ROOT/'dev/tools/blackbox_round_20261104.py'))
source=previous['source']
for old,new in [('DATE = "2026-11-04"','DATE = "2026-11-05"'),('blackbox_20261104','blackbox_20261105'),('report_20261104.py','report_20261105.py'),('data/versions/main_online_216258.cpp','data/versions/main_online_224148.cpp')]:
 if old not in source:raise RuntimeError('Dated anchor changed:'+old)
 source=source.replace(old,new)
source=source.replace('AUTHORIZATION = [','AUTHORIZATION = ["继续优化，30次机会", "你就是探针后期在综合就行", ',1)
if __name__=='__main__':
 ns={'__name__':'november5_round','__file__':str(ROOT/'dev/tools/online_round_20261030.py')}
 exec(compile(source,ns['__file__'],'exec'),ns)
 raise SystemExit(ns['main']())
