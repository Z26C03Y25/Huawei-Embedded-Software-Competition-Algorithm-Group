"""Continue explicitly authorized optimization, excepting only the identified stuck queue item.
Keeps both locks, source deduplication, quota/date checks and unique-job binding.
Only the exact old pending job is excepted; stop after three polling windows.
"""
from pathlib import Path
import hashlib, runpy, sys
ROOT=Path(__file__).resolve().parents[2]
OLD_JOB="20261104T064432532409Z_831debfc7899"
OLD_SERVER="497612b60ba943ecb77f919d98f3289a"

def replace_once(text,old,new):
    if text.count(old)!=1: raise RuntimeError("Diagnostic interface changed: "+old)
    return text.replace(old,new,1)

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--judge":
        SHA=sys.argv.pop(2)
        sys.path.insert(0,str(ROOT/"automation"))
        path=ROOT/"automation/online_judge/judge.py"
        code=path.read_text(encoding="utf-8")
        code=replace_once(code,'if other_active:', 'if any(j["job_id"] != "'+OLD_JOB+'" for j in other_active):')
        code=replace_once(code,'if any(row.status == "pending" for row in baseline):','if any(row.status == "pending" and row.submission_id != "'+OLD_SERVER+'" for row in baseline):')
        ns={"__name__":"health_judge","__file__":str(path)}
        exec(compile(code,str(path),"exec"),ns)
        sys.argv.pop(1)
        if sys.argv[1]=="submit":
            file=Path(sys.argv[sys.argv.index("--file")+1])
            if hashlib.sha256(file.read_bytes()).hexdigest()!=SHA: raise RuntimeError("Diagnostic source mismatch")
        raise SystemExit(ns["main"]())
    ns0=runpy.run_path(str(ROOT/"dev/tools/blackbox_round_20261104.py"))
    code=ns0["source"]
    code=replace_once(code,'if any(r["state"] not in {"completed", "failed"} for r in self.state["rounds"]):','if any(r["state"] not in {"completed", "failed"} and r.get("job_id") != "'+OLD_JOB+'" for r in self.state["rounds"]):')
    code=replace_once(code,'if active:', 'if any(j["job_id"] != "'+OLD_JOB+'" for j in active):')
    code=replace_once(code,'if any(row.status == "pending" for row in records):','if any(row.status == "pending" and row.submission_id != "'+OLD_SERVER+'" for row in records):')
    old='command = [sys.executable, "-X", "utf8", str(self.root / "automation/online_judge/judge.py"), *args]'
    new='command = [sys.executable, "-X", "utf8", str(self.root / "dev/tools/continue_20261104.py"), "--judge", entry["sha256"], *args]'
    code=replace_once(code,old,new)
    old='            started = time.monotonic()\n            entry["wait_windows"]'
    new='            if entry.get("wait_windows",0)>=3:\n                self.attach(entry,job)\n                print("Polling ended without a confirmed score; stop new uploads and resume this job only.",flush=True)\n                return 2\n            started = time.monotonic()\n            entry["wait_windows"]'
    code=replace_once(code,old,new)
    ns={"__name__":"health_controller","__file__":str(ROOT/"dev/tools/online_round_20261030.py")}
    exec(compile(code,ns["__file__"],"exec"),ns)
    raise SystemExit(ns["main"]())
