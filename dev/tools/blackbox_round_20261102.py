"""November2: inherit immutable single-upload and attribution/recovery guards."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[2]
previous=runpy.run_path(str(ROOT/'dev/tools/blackbox_round_20261101.py'))
source=previous['source']
for old,new in [('DATE = "2026-11-01"','DATE = "2026-11-02"'),
                ('blackbox_20261101','blackbox_20261102'),
                ('data/versions/main_online_212686.cpp','data/versions/main_online_216258.cpp')]:
    if old not in source: raise RuntimeError('Missing dated anchor: '+old)
    source=source.replace(old,new)
# Refresh the human-readable ledger when a job is attached and when its result
# is registered. Report generation does not upload or alter the chosen source.
refresh='subprocess.run([sys.executable,"-X","utf8",str(self.root/"dev/tools/report_20261102.py")],cwd=self.root,capture_output=True,timeout=20)'
anchor='        self.attach(entry, job)\n        return self.wait(entry)'
if anchor not in source: raise RuntimeError('Job attachment interface changed')
source=source.replace(anchor,'        self.attach(entry, job)\n        '+refresh+'\n        return self.wait(entry)')
anchor='        return 0 if job["state"] == "completed" else 3'
if source.count(anchor)!=1: raise RuntimeError('Result registration interface changed')
source=source.replace(anchor,'        '+refresh+'\n'+anchor,1)
if __name__=='__main__':
    ns={'__name__':'november2_round','__file__':previous['previous']['base'].__file__}
    exec(compile(source,ns['__file__'],'exec'),ns)
    raise SystemExit(ns['main']())
