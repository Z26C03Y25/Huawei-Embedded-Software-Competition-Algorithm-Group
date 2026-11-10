"""November3: immutable single-upload controller with November2 safeguards."""
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
previous=runpy.run_path(str(ROOT/'dev/tools/blackbox_round_20261102.py'))
source=previous['source']
for old,new in [('DATE = "2026-11-02"','DATE = "2026-11-03"'),
                ('blackbox_20261102','blackbox_20261103')]:
    if old not in source: raise RuntimeError('Missing dated anchor: '+old)
    source=source.replace(old,new)
source=source.replace('report_20261102.py','report_20261103.py')
if __name__=='__main__':
    ns={'__name__':'november3_round','__file__':previous['previous']['previous']['base'].__file__}
    exec(compile(source,ns['__file__'],'exec'),ns)
    raise SystemExit(ns['main']())
