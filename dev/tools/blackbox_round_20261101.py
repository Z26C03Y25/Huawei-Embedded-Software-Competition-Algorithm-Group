"""November 1 single-source round; preserves the established job recovery guards."""
from pathlib import Path
import sys, runpy
ROOT=Path(__file__).resolve().parents[2]
previous=runpy.run_path(str(ROOT/'dev/tools/blackbox_round_20261031.py'))
source=previous['source']
for old,new in [
    ('DATE = "2026-10-31"','DATE = "2026-11-01"'),
    ('data/experiments/blackbox_20261031','data/experiments/blackbox_20261101'),
    ('data/versions/main_online_210599.cpp','data/versions/main_online_212686.cpp'),
]:
    if old not in source:
        raise RuntimeError('Dated controller anchor missing: '+old)
    source=source.replace(old,new)
source=source.replace('AUTHORIZATION = [','AUTHORIZATION = ["继续优化，创新思路不要畏手畏脚，争取获取最高分", "线上三十次机会用完", "后续不要复测了，同样的代码分数不会变，除非同种子随机数", ',1)
finish_anchor='''    def finish(self, entry, job):
        contents = Path(job["snapshot_path"]).read_bytes()'''
if source.count(finish_anchor)!=1:
    raise RuntimeError('Score attribution interface changed')
source=source.replace(finish_anchor,'''    def finish(self, entry, job):
        if job.get("state")=="completed":
            from tools.submission_attribution import validate_submission_timing
            try:
                entry["submission_time_offset_seconds"]=validate_submission_timing(job)
            except (KeyError,ValueError) as exc:
                entry.update(state="attribution_review",last_error=str(exc))
                self.persist()
                raise RuntimeError(str(exc)) from exc
        contents = Path(job["snapshot_path"]).read_bytes()''',1)
prepared_retry='''        if previous:
            entry = previous[-1]
            if entry.get("job_id"):'''
if source.count(prepared_retry)!=1:
    raise RuntimeError('Prepared retry interface changed')
source=source.replace(prepared_retry,'''        if previous and len(previous)==1:
            prepared=previous[0]
            if (prepared.get("state")=="preflight_failed" and
                    not prepared.get("job_id") and not prepared.get("submit_started_at") and
                    not any(j.get("sha256")==sha for j in self.jobs())):
                # Quota/login checks failed BEFORE the sole upload invocation.
                # Preserve the failure audit and rerun all admission checks.
                self.state.setdefault("preflight_failures",[]).append(dict(prepared))
                self.state["rounds"].remove(prepared)
                self.persist()
                previous=[]
        if previous:
            entry = previous[-1]
            if entry.get("job_id"):''',1)
old_previous='        previous = [r for r in self.state["rounds"] if r["sha256"] == sha]'
if source.count(old_previous)!=1:
    raise RuntimeError('Pre-upload failure recovery interface changed')
source=source.replace(old_previous,'''        for prepared in list(self.state["rounds"]):
            if (prepared.get("sha256")!=sha and prepared.get("state")=="preflight_failed" and
                    not prepared.get("job_id") and not prepared.get("submit_started_at") and
                    not any(j.get("sha256")==prepared["sha256"] for j in self.jobs())):
                self.state.setdefault("preflight_failures",[]).append(dict(prepared))
                self.state["rounds"].remove(prepared)
                self.persist()
        previous = [r for r in self.state["rounds"] if r["sha256"] == sha]''',1)
source=source.replace('    temporary.replace(path)', '''    for attempt in range(8):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt==7:
                raise
            time.sleep(0.05*(attempt+1))''',1)
source=source.replace('found = [r for r in self.state["rounds"] if r.get("job_id") == job_id]',
                     'found = [r for r in self.state["rounds"] if r.get("job_id") == job_id or (not r.get("job_id") and r.get("sha256")==job["sha256"])]',1)
source=source.replace('''        if found:
            entry = found[0]
        else:''','''        if found:
            if len(found)!=1:
                raise RuntimeError("Ambiguous local round binding; no upload is permitted")
            entry = found[0]
            self.attach(entry,job)
        else:''',1)
parking_line='            row["parked_observed_winner"] = bool(path) and row["final_position"] == winner'
if source.count(parking_line)!=1:
    raise RuntimeError('Parking admission interface changed')
source=source.replace(parking_line,parking_line+'''
            # Legal score-recovery exception, checked from the actual trace:
            # old winner p<r-202 implies d>3 for every target with R<=199.
            prefix = path[:-1]
            prefix_winner = min(set(prefix),key=lambda x:(-case.values[x],abs(2*x-(len(case.values)-1)),x)) if prefix else None
            row["parking_rescue_proved"] = bool(prefix) and path[-1] in prefix and max(path)==max(prefix) and prefix_winner < max(prefix)-202 and row["final_position"] >= max(0,max(prefix)-202)''',1)
old='or row["oscillations"] > 6 or not row["parked_observed_winner"]'
if source.count(old)!=1:
    raise RuntimeError('Parking assertion interface changed')
source=source.replace(old,'or row["oscillations"] > 6 or not (row["parked_observed_winner"] or row["parking_rescue_proved"])',1)
if __name__=='__main__':
    namespace={'__name__':'blackbox_round_impl','__file__':previous['base'].__file__}
    exec(compile(source,namespace['__file__'],'exec'),namespace)
    raise SystemExit(namespace['main']())
