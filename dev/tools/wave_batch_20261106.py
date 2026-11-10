"""Bounded pipeline for independent, waveform-only Huawei entries."""
from datetime import datetime, timedelta
import argparse
import json
from pathlib import Path
import re
import sys
import time

from wave_round_20261106 import controller, ROOT, OUT, QUARANTINE, OLD_SERVER
from wave_candidates_20261106 import VARIANTS, STRATEGIC, REVISIONS, EXPERIMENTS

core = controller()
sys.path.insert(0, str(ROOT / 'dev'))
from tools.submission_attribution import validate_submission_timing

Controller = core['Controller']
SubmissionLock = core['SubmissionLock']
connect = core['connect']
parse_quota = core['parse_quota']
now = core['now']
save = core['save']
read = core['read']
digest = core['digest']
TERMINAL = {'completed', 'failed'}
DAY = '2026-11-06'
LIMIT = 30
BATCH_IN_FLIGHT = 30
ACK_SECONDS = 100

def log(**data):
    print(json.dumps(data, ensure_ascii=False), flush=True)

class Batch:
    def __init__(self, ctl, page, max_minutes):
        self.ctl, self.page = ctl, page
        self.stop_at = time.monotonic() + max_minutes * 60
        self.signatures = {}
        self.run_lock = Path(ctl.config['runs_directory']) / '.submission.lock'
        for row in ctl.state['rounds']:
            if row.get('preflight',{}).get('passed') and not row.get('smoke_path_sha256'):
                row['smoke_path_sha256'] = self.smoke_signature(row)

    def rounds(self):
        return self.ctl.state['rounds']

    def check_foreign_jobs(self):
        local = {r.get('job_id') for r in self.rounds()}
        for job in self.ctl.jobs():
            if job['state'] in TERMINAL | {'snapshot_ready'} or job['job_id'] in QUARANTINE:
                continue
            if job['job_id'] not in local:
                raise RuntimeError(f"Another controller owns active job {job['job_id']}")
        for entry in self.rounds():
            if entry['state'] in {'submission_unknown','submission_started','delivery_uncertain'} and not entry.get('job_id'):
                raise RuntimeError(f"Unreconciled delivery for {entry['name']}")

    def provision(self, name):
        self.poll()
        state = self.ctl.state
        if state.get('wave_best') or state.get('wave_provisional'):
            return
        matches = [r for r in self.rounds() if r['name']==name and r.get('preflight',{}).get('passed')]
        if len(matches)!=1:
            raise RuntimeError('Provisional wave entry requires a unique passed preflight')
        entry=matches[0]
        contents=Path(entry['snapshot_path']).read_bytes()
        main=ROOT/'main.cpp'
        if digest(contents)!=entry['sha256'] or digest(main.read_bytes())!=state['initial_best_sha256']:
            raise RuntimeError('Unrecognized main.cpp or provisional source bytes')
        state['wave_provisional']={k:entry[k] for k in ('name','sha256','snapshot_path','job_id')}
        self.ctl.persist()
        staged=main.with_name('main.wave-staged.cpp')
        staged.write_bytes(contents)
        staged.replace(main)
        log(provisional_wave=state['wave_provisional'])

    def accept_wave(self, entry):
        state = self.ctl.state
        winner = state.get('wave_best')
        if winner and entry['score'] <= winner['score']:
            return
        archive = ROOT / entry['archive']
        contents = archive.read_bytes()
        if digest(contents) != entry['sha256']:
            raise RuntimeError('Wave winner archive has changed')
        main = ROOT / 'main.cpp'
        accepted = {state['initial_best_sha256'], entry['sha256'], state.get('wave_provisional',{}).get('sha256')}
        if winner:
            accepted.add(winner['sha256'])
        if digest(main.read_bytes()) not in accepted:
            raise RuntimeError('main.cpp changed outside the wave controller')
        staged = main.with_name('main.wave-staged.cpp')
        staged.write_bytes(contents)
        staged.replace(main)
        state['wave_best'] = {k: entry[k] for k in ('name','score','sha256','archive','job_id','submission_id','submitted_at')}
        self.ctl.persist()
        log(wave_best=state['wave_best'])

    def poll(self):
        records = self.page.records(refresh=True)
        needed = {self.ctl.store.load(r['job_id']).get('bound_submission_id') for r in self.active()}
        needed.discard(None)
        present = {r.submission_id for r in records[:8]}
        if not needed <= present:
            self.page.page.locator('.tiny-pager__page-size').click()
            option = self.page.page.locator('li.list-item').get_by_text('50',exact=True)
            with self.page.page.expect_response(self.page._is_api_response, timeout=10000):
                option.click()
            records = self.page.records(refresh=False)
            if len(records)<len(needed) or not all(r.submission_id for r in records):
                raise RuntimeError('Official 50-row history did not return stable IDs')
            if any(r.status in {'pending','unknown'} for r in records):
                records = self.page._with_rendered_terminals(records)
        quota = parse_quota(self.page.page.locator('body').inner_text())
        by_id = {r.submission_id: r for r in records if r.submission_id}
        for entry in self.rounds():
            job_id = entry.get('job_id')
            if not job_id:
                continue
            job = self.ctl.store.load(job_id)
            if entry['state'] in TERMINAL:
                if job['state']=='completed' and entry.get('archive'):
                    self.accept_wave(entry)
                continue
            if job['state'] in TERMINAL:
                self.ctl.finish(entry,job)
                if job['state']=='completed':
                    self.accept_wave(entry)
                continue
            self.ctl.store.validate_snapshot(job)
            bound = job.get('bound_submission_id')
            if not bound:
                continue
            row = by_id.get(bound)
            if row is None:
                self.signatures.pop(job_id,None)
                continue
            validate_submission_timing(dict(job,record=row.to_dict()))
            updated = dict(job)
            state = self.ctl.store.observe(updated, [row])
            if state in TERMINAL:
                signature = (bound, state, updated.get('score'), row.status_text)
                previous = self.signatures.get(job_id)
                if not previous or previous[0]!=signature:
                    self.signatures[job_id] = (signature,time.monotonic())
                    continue
                if time.monotonic()-previous[1]<2:
                    continue
            else:
                self.signatures.pop(job_id,None)
            self.ctl.store.save(updated)
            entry.update(state=state,submission_id=bound,submitted_at=row.submitted_at)
            if state in TERMINAL:
                self.ctl.finish(entry,updated)
                if state=='completed':
                    self.accept_wave(entry)
        self.ctl.state['last_quota'] = quota
        if quota['beijing_date']==DAY:
            self.ctl.state['last_authorized_quota'] = quota
        self.ctl.persist()
        return quota, records

    def active(self):
        return [r for r in self.rounds() if r.get('job_id') and r['state'] not in TERMINAL]

    def can_send(self, records):
        active = self.active()
        ids = [self.ctl.store.load(r['job_id']).get('bound_submission_id') for r in active]
        if any(not x for x in ids):
            raise RuntimeError('Unconfirmed upload exists. Resume only that job.')
        unknown = [r for r in records if r.status in {'pending','unknown'} and
                   r.submission_id not in [*ids,OLD_SERVER] and r.submitted_at[:10]==DAY]
        if unknown:
            raise RuntimeError('A new, unowned pending submission appeared')
        if len(ids)>=BATCH_IN_FLIGHT:
            return False
        return all(any(r.submission_id==uid for r in records[:-1]) for uid in ids)

    @staticmethod
    def smoke_signature(entry):
        smoke = read(Path(entry['snapshot_path']).parent / 'smoke.json')['rows']
        return digest(json.dumps([r['query_positions'] for r in smoke]).encode())

    def prepare(self,name):
        source = OUT / (name + '.cpp')
        contents = source.read_bytes()
        sha = digest(contents)
        existing = next((r for r in self.rounds() if r['sha256']==sha),None)
        if existing and (existing.get('job_id') or existing['state']!='prepared'):
            return None
        archived = read(self.ctl.manifest_path, {}).get('files',[])
        if any(j['sha256']==sha for j in self.ctl.jobs()) or any(r.get('sha256')==sha for r in archived):
            raise RuntimeError(f'Refusing historical source hash: {name}')
        core['candidate_review'](contents)
        code = contents.decode('utf-8')
        if re.search(r'fingerprint|deferred|n\s*==\s*\d+|\b(?:586|662|774)\b', code):
            raise RuntimeError(f'Table audit failed: {name}')
        key = REVISIONS.get(name,name)
        parts = VARIANTS.get(key) or STRATEGIC.get(key) or EXPERIMENTS[key]
        description = 'Waveform policy ' + ', '.join(part for part in parts if part)
        entry = existing or self.ctl.new_metadata(name,contents,description,source)
        try:
            self.ctl.preflight(entry)
        except Exception as exc:
            entry.update(state='preflight_failed',last_error=str(exc))
            self.ctl.persist()
            log(preflight_failed=name,error=str(exc))
            return None
        path_digest = self.smoke_signature(entry)
        entry['smoke_path_sha256'] = path_digest
        for prior in self.rounds():
            if prior is not entry and prior.get('smoke_path_sha256')==path_digest:
                entry.update(state='preflight_duplicate',last_error=f"All smoke query paths match {prior['name']}")
                self.ctl.persist()
                log(skipped=name,behavior_matches=prior['name'])
                return None
        self.ctl.persist()
        return entry

    def upload(self,entry):
        with SubmissionLock(self.run_lock):
            self.check_foreign_jobs()
            quota, baseline = self.poll()
            if now()[:10]!=DAY or time.monotonic()>=self.stop_at or quota['remaining']==0:
                return False
            if not self.can_send(baseline):
                return False
            if any(not row.submission_id for row in baseline):
                raise RuntimeError('No fresh server IDs in the submission history')
            button = self.page.page.get_by_role('button', name=self.ctl.config['upload_button_text'], exact=True)
            if button.count()!=1 or not button.is_enabled():
                raise RuntimeError('Official upload button is unavailable')
            snapshot = Path(entry['snapshot_path'])
            contents = snapshot.read_bytes()
            if digest(contents)!=entry['sha256']:
                raise RuntimeError('Frozen source changed')
            previous_ids = {r.submission_id for r in baseline}
            job = self.ctl.store.create(snapshot,baseline,contents=contents)
            entry.update(state='submission_started',submit_started_at=now(),quota_before=quota,job_id=job['job_id'])
            self.ctl.persist()
            if now()[:10]!=DAY:
                raise RuntimeError('Submission day ended before upload')
            attempted = datetime.now(core['TZ'])
            job.update(state='delivery_uncertain',submission_attempt_at=attempted.isoformat(),
                       submission_url=self.ctl.config['submission_url'])
            self.ctl.store.save(job)
            log(upload=entry['name'],job=job['job_id'],sha256=entry['sha256'],used=quota['used'],attempt=attempted.isoformat())
            try:
                self.page.upload(Path(job['snapshot_path']))
                job['upload_action_finished'] = True
                self.ctl.store.save(job)
            except Exception as exc:
                job['last_error'] = f'Upload action uncertain: {type(exc).__name__}'
                self.ctl.store.save(job)
                log(upload_outcome_uncertain=job['job_id'])
            # Allow the browser's own file upload to finish before a refresh.
            self.page.page.wait_for_timeout(10000)
            until = time.monotonic()+ACK_SECONDS
            while time.monotonic()<until:
                live, records = self.poll()
                fresh = [r for r in records if r.submission_id and r.submission_id not in previous_ids
                         and r.filename=='main.cpp' and r.submitted_at[:10]==DAY
                         and r.submitted_at>=max((old.submitted_at for old in baseline),default='')]
                if len(fresh)>1 or live['used']>quota['used']+1:
                    raise RuntimeError('Competing new submission rows or quota change; attribution stopped')
                if len(fresh)==1 and live['used']==quota['used']+1:
                    row = fresh[0]
                    validate_submission_timing(dict(job,record=row.to_dict()))
                    submitted = datetime.strptime(row.submitted_at,'%Y-%m-%d %H:%M:%S').replace(tzinfo=core['TZ'])
                    if submitted<attempted-timedelta(seconds=15):
                        raise RuntimeError('New row precedes this upload')
                    self.ctl.store.observe(job, [row])
                    if job.get('bound_submission_id') != row.submission_id:
                        raise RuntimeError('Job store did not bind the sole matching work ID')
                    job.update(state='pending',score=None)
                    job.pop('finished_at',None)
                    self.ctl.store.save(job)
                    self.ctl.attach(entry,job)
                    entry.update(submission_id=row.submission_id,submitted_at=row.submitted_at)
                    self.ctl.persist()
                    log(bound=entry['name'],work=row.submission_id,submitted_at=row.submitted_at,
                        official_quota=live['used'])
                    return True
                self.page.page.wait_for_timeout(4500)
            raise RuntimeError(f"No uniquely acknowledged row for {job['job_id']}; no further upload")

    def run(self,names, drain):
        self.check_foreign_jobs()
        for name in names:
            if now()[:10]!=DAY or time.monotonic()>=self.stop_at:
                break
            if any(r['name']==name and r.get('job_id') for r in self.rounds()):
                continue
            quota,_ = self.poll()
            if quota['remaining']==0:
                break
            entry = self.prepare(name)
            if entry is None:
                continue
            while now()[:10]==DAY and time.monotonic()<self.stop_at:
                quota, records = self.poll()
                if quota['remaining']==0:
                    break
                if self.can_send(records) and self.upload(entry):
                    break
                self.page.page.wait_for_timeout(9000)
        if drain:
            while self.active() and time.monotonic()<self.stop_at:
                self.poll()
                if self.active():
                    fresh_terminal = any(time.monotonic()-seen<3 for _,seen in self.signatures.values())
                    self.page.page.wait_for_timeout(5000 if fresh_terminal else 35000)
        quota,_ = self.poll()
        log(official_quota=quota['used'],remaining=quota['remaining'],pending=len(self.active()),
            wave_best=self.ctl.state.get('wave_best'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names',nargs='*',choices=None)
    parser.add_argument('--minutes',type=float,default=100)
    parser.add_argument('--drain',action='store_true')
    parser.add_argument('--provisional')
    args = parser.parse_args()
    if any(name not in VARIANTS and name not in STRATEGIC and name not in REVISIONS and name not in EXPERIMENTS for name in args.names):
        raise RuntimeError('Unknown candidate name')
    with SubmissionLock(OUT / '.round.lock'):
        ctl = Controller()
        with connect(ctl.config) as page:
            batch=Batch(ctl,page,args.minutes)
            if args.provisional:
                batch.provision(args.provisional)
            batch.run(args.names,args.drain)

if __name__=='__main__':
    main()
