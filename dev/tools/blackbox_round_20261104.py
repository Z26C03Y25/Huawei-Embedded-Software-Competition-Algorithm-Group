"""November4: immutable single-upload controller with inherited recovery guards."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[2]
previous=runpy.run_path(str(ROOT/'dev/tools/blackbox_round_20261103.py'))
source=previous['source']
for old,new in [('DATE = "2026-11-03"','DATE = "2026-11-04"'),
                ('blackbox_20261103','blackbox_20261104'),('report_20261103.py','report_20261104.py')]:
    if old not in source: raise RuntimeError('Missing dated anchor: '+old)
    source=source.replace(old,new)
if __name__=='__main__':
    base=previous['previous']['previous']['previous']['base']
    ns={'__name__':'november4_round','__file__':base.__file__}
    exec(compile(source,ns['__file__'],'exec'),ns)
    raise SystemExit(ns['main']())
