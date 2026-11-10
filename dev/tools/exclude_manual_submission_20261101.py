"""Retract one user-identified manual score; no browser or upload operations."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'automation'))
from online_judge.jobs import SubmissionLock

OUT=ROOT/'data/experiments/blackbox_20261101'
JOB='20261031T180128179361Z_a7c49c70c7b4'
SERVER='c0a66e12256e4b30a17c95c8d4299089'
SHA='90033fa06b7f3c6b4fbaf381dec162f1af2b9c8f4d104951e234f797b6c740ed'
REASON='User explicitly identified the 2026-11-01 02:04:15 / 146180 row as their own experimental submission and requested it be ignored. Automated half-scout delivery remains unconfirmed; abandon without retry or attributing this score.'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path,value):
    temporary=path.with_suffix(path.suffix+'.retraction.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)

def main():
    paths=[OUT/'state.json',OUT/'results.json',ROOT/'data/versions/online_search/results.json',
           ROOT/'data/versions/manifest.json',ROOT/'automation/online_judge/runs'/JOB/'job.json']
    audit=OUT/'attribution_rejections'/JOB
    audit.mkdir(parents=True,exist_ok=True)
    with SubmissionLock(OUT/'.round.lock'), SubmissionLock(ROOT/'automation/online_judge/runs/.submission.lock'):
        payloads=[read(p) for p in paths]
        original=audit/'original_records.json'
        if not original.exists():
            original.write_text(json.dumps(dict(reason=REASON,user_instruction='忽略 2026-11-01 02:04:15 /146180，是我自己写着玩的',
                captured_at=datetime.now(timezone.utc).isoformat(),
                records={p.relative_to(ROOT).as_posix():v for p,v in zip(paths,payloads)}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        state,results,index,manifest,job=payloads
        if job['sha256']!=SHA:
            raise RuntimeError('Unexpected source hash; do not retract')
        if job.get('bound_submission_id') not in (SERVER,None):
            raise RuntimeError('Unexpected bound work; do not retract')
        observation=job.get('rejected_observation') or dict(submission_id=SERVER,record=job.get('record'),score=146180)
        for row in state['rounds']+results:
            if row.get('job_id')!=JOB:
                continue
            row.update(state='failed',score=None,delta=None,accepted=False,
                       failure_kind='attribution_rejected',exclusion_reason=REASON,
                       delivery_confirmed=False,rejected_observation=observation)
            for key in ['archive','submission_id','submitted_at']:
                row.pop(key,None)
        index[:]=[r for r in index if r.get('job_id')!=JOB]
        relative='data/versions/online_search/scored_146180_90033fa06b7f.cpp'
        manifest['files'][:]=[r for r in manifest['files'] if r.get('path')!=relative]
        job.update(state='failed',score=None,record=None,bound_identity=None,bound_submission_id=None,
                   failure_kind='attribution_rejected',last_error=REASON,delivery_confirmed=False,
                   rejected_observation=observation,excluded_submission_ids=[SERVER])
        archived=ROOT/relative
        relocated=audit/'unscored_source.cpp'
        if archived.exists():
            if hashlib.sha256(archived.read_bytes()).hexdigest()!=SHA:
                raise RuntimeError('Archive bytes changed; do not move')
            if relocated.exists() and relocated.read_bytes()!=archived.read_bytes():
                raise RuntimeError('Retraction source collision')
            archived.replace(relocated)
        for path,value in zip(paths,payloads):
            write(path,value)
        print(json.dumps(dict(excluded_submission_id=SERVER,source_score=None,best=state['best_score'],
                              no_upload=True,no_retry=True),ensure_ascii=False))

if __name__=='__main__':
    main()
