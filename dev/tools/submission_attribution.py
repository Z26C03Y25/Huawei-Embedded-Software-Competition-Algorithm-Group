"""Reject implausibly timed row attribution before using an official score."""
from datetime import datetime, timedelta, timezone

CHINA=timezone(timedelta(hours=8))

def validate_submission_timing(job, maximum_delay=60):
    """A time match is necessary here, but does not prove uploaded source bytes."""
    attempt=datetime.fromisoformat(job['submission_attempt_at'])
    if attempt.tzinfo is None:
        raise ValueError('Upload attempt must have an explicit timezone')
    submitted=datetime.strptime(job['record']['submitted_at'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=CHINA)
    delay=(submitted-attempt).total_seconds()
    # Server and client clocks need not agree to the second. Current observed
    # official acknowledgements can precede the client clock by about3 seconds.
    if not -15<=delay<=maximum_delay:
        raise ValueError(f'Submission row is {delay:.1f}s from the upload attempt; source attribution needs review, not another upload')
    return delay
