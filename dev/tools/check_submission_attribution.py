"""Regression check for delayed manual rows; no network or submissions."""
from submission_attribution import validate_submission_timing

def check(attempt,submitted,accept):
    job=dict(submission_attempt_at=attempt,record=dict(submitted_at=submitted))
    try:
        validate_submission_timing(job)
    except ValueError:
        assert not accept,job
    else:
        assert accept,job

check('2026-11-01T02:01:28.189922+08:00','2026-11-01 02:04:15',False)
check('2026-11-01T02:07:05.128069+08:00','2026-11-01 02:07:06',True)
check('2026-10-31T23:35:11.719727+00:00','2026-11-01 07:35:13',True)
check('2026-11-01T07:35:11+08:00','2026-11-01 07:30:11',False)
check('2026-11-01T07:35:11','2026-11-01 07:35:12',False)
check('2026-11-01T07:39:13.240356+08:00','2026-11-01 07:39:11',True)
print('6 attribution timing checks passed; timing alone does not prove source ownership.')
