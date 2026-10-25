"""Offline snapshot, identity tracking, persistence and process-lock tests."""

from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge.jobs import JobStore, SubmissionLock, observe, validate_snapshot
from online_judge.records import SubmissionRecord


ROOT = Path(__file__).resolve().parents[3]


def temporary_directory():
    # The desktop sandbox may redirect the system temp directory to a path
    # without write access; use the repository's ignored scratch directory.
    directory = ROOT / "dev/tmp"
    directory.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(prefix="online_jobs_", dir=directory)


def row(second=0, *, filename="main.cpp", status="pending", score=None,
        status_text="", row_id=None, submission_id=None, source=None):
    return SubmissionRecord(filename, "C++", f"2026-10-24 19:00:{second:02d}",
                            score, status, status_text, row_id=row_id,
                            submission_id=submission_id,
                            source=source or ("api" if submission_id is not None else "dom"))


class JobStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = temporary_directory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.store = JobStore(self.directory / "runs")
        self.source = self.directory / "working source.cpp"
        self.original = b"\xef\xbb\xbf// exact original bytes\r\nint main() { return 0; }\r\n"
        self.source.write_bytes(self.original)
        self.old = row(0, status="success", score=215968)
        self.job = self.store.create(self.source, [self.old])

    def test_snapshot_keeps_exact_original_bytes_after_workspace_changes(self):
        self.source.write_bytes(b"// a later working-tree edit\n")
        snapshot = Path(self.job["snapshot_path"])
        self.assertEqual(snapshot, self.store.root / self.job["job_id"] / "main.cpp")
        self.assertEqual(snapshot.read_bytes(), self.original)
        self.assertEqual(self.job["sha256"], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(self.job["size"], len(self.original))
        self.assertEqual(Path(self.job["source_path"]), self.source.resolve())
        self.assertEqual(self.job["state"], "snapshot_ready")
        self.assertEqual(self.job["baseline_identities"], [list(self.old.identity)])
        self.assertIsNone(self.store.validate_snapshot(self.job))
        self.assertIsNone(validate_snapshot(self.job))

    def test_snapshot_same_size_hash_modification_is_rejected(self):
        Path(self.job["snapshot_path"]).write_bytes(b"X" * len(self.original))
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.store.validate_snapshot(self.job)

    def test_snapshot_size_change_and_missing_file_are_rejected(self):
        snapshot = Path(self.job["snapshot_path"])
        snapshot.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "size"):
            self.store.validate_snapshot(self.job)
        snapshot.unlink()
        with self.assertRaisesRegex(ValueError, "missing|unreadable"):
            self.store.validate_snapshot(self.job)

    def test_snapshot_path_cannot_be_redirected_outside_its_job(self):
        self.job["snapshot_path"] = str(self.source)
        with self.assertRaisesRegex(ValueError, "outside"):
            self.store.validate_snapshot(self.job)

    def test_stale_score_change_and_other_filenames_do_not_bind(self):
        changed_old = row(0, status="success", score=0)
        other = row(1, filename="other.cpp", status="success", score=300000)
        self.assertEqual(self.store.observe(self.job, [other, changed_old]), "pending")
        self.assertIsNone(self.job["bound_identity"])
        self.assertIsNone(self.job["score"])
        self.assertTrue(self.job["last_error"])

    def test_pending_zero_then_explicit_final_zero(self):
        self.assertEqual(observe(self.job, [row(1, score=0), self.old]), "pending")
        self.assertIsNone(self.job["score"])
        self.assertEqual(self.job["bound_identity"], list(row(1).identity))
        self.assertEqual(observe(self.job, [row(1, status="success", score=0)]), "completed")
        self.assertEqual(self.job["score"], 0)
        self.assertIsNone(self.job["last_error"])

    def test_older_rows_revealed_by_refresh_or_pagination_do_not_bind(self):
        older = SubmissionRecord("main.cpp", "赛事", "2026-10-23 22:45:33",
                                 215968, "success", "success")
        self.assertEqual(observe(self.job, [older, self.old]), "pending")
        self.assertIsNone(self.job["bound_identity"])
        self.assertIsNone(self.job["score"])
        self.assertEqual(observe(self.job, [row(1, status="success", score=145904), older]),
                         "completed")
        self.assertEqual(self.job["score"], 145904)

    def test_api_baseline_saves_server_ids_without_changing_legacy_identity(self):
        old = row(0, status="success", score=215968, submission_id="work-old")
        job = self.store.create(self.source, [old])
        self.assertEqual(job["baseline_submission_ids"], ["work-old"])
        self.assertEqual(job["baseline_identities"], [list(old.identity)])
        self.assertIsNone(job["bound_submission_id"])
        self.assertEqual(old.identity, self.old.identity)

    def test_new_api_id_can_bind_in_the_same_display_second_as_baseline(self):
        old = row(0, status="success", score=215968, submission_id="work-old")
        job = self.store.create(self.source, [old])
        pending = row(0, score=0, submission_id="work-new")
        self.assertEqual(observe(job, [pending, old]), "pending")
        self.assertEqual(job["bound_submission_id"], "work-new")
        self.assertEqual(job["bound_identity"], list(old.identity))
        self.assertIsNone(job["score"])
        self.assertEqual(observe(job, [old]), "pending")
        final = row(0, status="success", score=0, submission_id="work-new")
        self.assertEqual(observe(job, [old, final]), "completed")
        self.assertEqual(job["score"], 0)

    def test_multiple_new_api_ids_in_one_second_remain_ambiguous(self):
        old = row(0, status="success", score=1000, submission_id="work-old")
        job = self.store.create(self.source, [old])
        first = row(0, submission_id="work-first")
        second = row(0, submission_id="work-second")
        self.assertEqual(observe(job, [second, first, old]), "ambiguous")
        self.assertIsNone(job["bound_submission_id"])
        self.assertEqual(job["ambiguous_submission_ids"], ["work-first", "work-second"])
        self.assertEqual(observe(job, [first, old]), "ambiguous")
        job["bound_submission_id"] = "work-first"
        final = row(0, status="success", score=0, submission_id="work-first")
        self.assertEqual(observe(job, [second, final]), "completed")
        self.assertEqual(job["score"], 0)

    def test_bound_api_id_is_followed_in_second_row_despite_same_second_alias(self):
        observe(self.job, [row(1, submission_id="work-target")])
        other = row(1, status="success", score=99999, submission_id="work-other")
        target = row(1, status="success", score=2070, submission_id="work-target")
        self.assertEqual(observe(self.job, [other, target]), "completed")
        self.assertEqual(self.job["score"], 2070)
        self.assertEqual(self.job["bound_submission_id"], "work-target")

    def test_bound_api_id_waits_through_dom_fallback_and_wrong_same_second_id(self):
        observe(self.job, [row(1, submission_id="work-target")])
        dom_final = row(1, status="success", score=77777)
        self.assertEqual(observe(self.job, [dom_final]), "pending")
        self.assertIsNone(self.job["score"])
        self.assertEqual(self.job["bound_submission_id"], "work-target")
        self.assertIn("API", self.job["last_error"])
        other = row(1, status="success", score=88888, submission_id="work-other")
        self.assertEqual(observe(self.job, [other]), "pending")
        self.assertEqual(self.job["bound_submission_id"], "work-target")
        target = row(1, status="success", score=0, submission_id="work-target")
        self.assertEqual(observe(self.job, [target]), "completed")
        self.assertEqual(self.job["score"], 0)

    def test_dom_baseline_api_switch_does_not_make_old_or_same_second_rows_new(self):
        old_api = row(0, status="success", score=215968, submission_id="work-old")
        same_second = row(0, submission_id="work-same-second")
        self.assertEqual(observe(self.job, [old_api, same_second]), "pending")
        self.assertIsNone(self.job["bound_submission_id"])
        self.assertIsNone(self.job["bound_identity"])
        newer = row(1, submission_id="work-new")
        self.assertEqual(observe(self.job, [newer, old_api]), "pending")
        self.assertEqual(self.job["bound_submission_id"], "work-new")

    def test_api_baseline_dom_switch_ignores_old_row_then_upgrades_new_identity(self):
        old_api = row(0, status="success", score=215968, submission_id="work-old")
        job = self.store.create(self.source, [old_api])
        self.assertEqual(observe(job, [self.old]), "pending")
        self.assertIsNone(job["bound_identity"])
        self.assertIsNone(job["bound_submission_id"])
        self.assertEqual(observe(job, [row(1), self.old]), "pending")
        self.assertIsNone(job["bound_submission_id"])
        upgraded = row(1, submission_id="work-new")
        self.assertEqual(observe(job, [upgraded, old_api]), "pending")
        self.assertEqual(job["bound_submission_id"], "work-new")

    def test_api_new_ids_from_older_pages_are_not_new_submissions(self):
        old_api = row(1, status="success", score=215968, submission_id="work-old")
        job = self.store.create(self.source, [old_api])
        older = row(0, status="success", score=300000, submission_id="work-older-page")
        self.assertEqual(observe(job, [older, old_api]), "pending")
        self.assertIsNone(job["bound_submission_id"])

    def test_mixed_baseline_does_not_promote_a_former_dom_row_to_new_api_upload(self):
        api_old = row(0, status="success", score=100, submission_id="work-old")
        dom_old = row(1, status="success", score=200)
        job = self.store.create(self.source, [dom_old, api_old])
        now_api = row(1, status="success", score=200, submission_id="work-former-dom")
        self.assertEqual(observe(job, [now_api, api_old]), "pending")
        self.assertIsNone(job["bound_identity"])

    def test_legacy_bound_identity_with_two_api_ids_requires_explicit_id_selection(self):
        observe(self.job, [row(1)])
        first = row(1, submission_id="work-first")
        second = row(1, submission_id="work-second")
        self.assertEqual(observe(self.job, [second, first]), "ambiguous")
        self.assertEqual(observe(self.job, [first]), "ambiguous")
        self.job["bound_submission_id"] = "work-second"
        target = row(1, status="success", score=0, submission_id="work-second")
        self.assertEqual(observe(self.job, [first, target]), "completed")

    def test_legacy_metadata_restarts_and_upgrades_unique_bound_identity_to_api_id(self):
        observe(self.job, [row(1)])
        self.job.pop("baseline_submission_ids")
        self.job.pop("bound_submission_id")
        self.store.save(self.job)
        loaded = self.store.load(self.job["job_id"])
        self.assertEqual(loaded["baseline_submission_ids"], [])
        self.assertIsNone(loaded["bound_submission_id"])
        self.assertEqual(loaded["bound_identity"], list(row(1).identity))
        target = row(1, submission_id="work-upgraded")
        self.assertEqual(observe(loaded, [target]), "pending")
        self.assertEqual(loaded["bound_submission_id"], "work-upgraded")
        self.store.save(loaded)
        restarted = self.store.load(loaded["job_id"])
        wrong = row(1, status="success", score=99999, submission_id="work-wrong")
        self.assertEqual(observe(restarted, [wrong]), "pending")
        target = row(1, status="success", score=0, submission_id="work-upgraded")
        self.assertEqual(observe(restarted, [wrong, target]), "completed")
        self.assertEqual(restarted["score"], 0)

    def test_missing_id_metadata_fields_can_be_recovered_from_full_saved_rows(self):
        old_api = row(0, status="success", score=100, submission_id="work-old")
        job = self.store.create(self.source, [old_api])
        observe(job, [row(1, submission_id="work-target")])
        job.pop("baseline_submission_ids")
        job.pop("bound_submission_id")
        self.store.save(job)
        loaded = self.store.load(job["job_id"])
        self.assertEqual(loaded["baseline_submission_ids"], ["work-old"])
        self.assertEqual(loaded["bound_submission_id"], "work-target")

    def test_success_without_score_keeps_waiting(self):
        self.assertEqual(observe(self.job, [row(1, status="success")]), "pending")
        self.assertIsNone(self.job["score"])
        self.assertIn("score", self.job["last_error"])
        self.assertEqual(observe(self.job, [row(1, status="success", score=154353)]), "completed")
        self.assertEqual(self.job["score"], 154353)

    def test_failure_is_terminal_and_not_a_completed_zero(self):
        failed = row(1, status="failed", score=0, status_text="Compilation failed")
        self.assertEqual(observe(self.job, [failed]), "failed")
        self.assertIsNone(self.job["score"])
        self.assertIn("Compilation", self.job["last_error"])
        self.assertEqual(observe(self.job, []), "failed")

    def test_multiple_new_rows_remain_ambiguous_until_explicit_binding(self):
        first, second = row(1), row(2)
        self.assertEqual(observe(self.job, [second, first, self.old]), "ambiguous")
        self.assertIsNone(self.job["bound_identity"])
        self.assertEqual(len(self.job["candidate_records"]), 2)
        # One row disappearing cannot establish which upload belongs to us.
        self.assertEqual(observe(self.job, [first]), "ambiguous")
        self.job["bound_identity"] = list(first.identity)
        self.assertEqual(observe(self.job, [second, row(1, status="success", score=0)]), "completed")
        self.assertEqual(self.job["score"], 0)

    def test_bound_target_is_followed_when_pushed_to_second_row(self):
        observe(self.job, [row(1, score=0), self.old])
        target = row(1, status="success", score=2070, row_id="changed-row-id")
        newer = row(2, status="success", score=99999)
        self.assertEqual(observe(self.job, [newer, target, self.old]), "completed")
        self.assertEqual(self.job["score"], 2070)
        self.assertEqual(self.job["bound_identity"], list(target.identity))

    def test_unknown_or_missing_bound_row_does_not_switch_identity(self):
        target = row(1)
        observe(self.job, [target])
        unknown = row(1, status="unknown", score=1234, status_text="new platform state")
        self.assertEqual(observe(self.job, [unknown]), "pending")
        self.assertIn("Unknown", self.job["last_error"])
        self.assertIsNone(self.job["score"])
        self.assertEqual(observe(self.job, [row(2, status="success", score=88888)]), "pending")
        self.assertIn("absent", self.job["last_error"])
        self.assertEqual(self.job["bound_identity"], list(target.identity))
        self.assertEqual(observe(self.job, [row(1, status="success", score=215968)]), "completed")
        self.assertEqual(self.job["score"], 215968)
        self.assertEqual(observe(self.job, []), "completed")

    def test_timeout_and_uncertain_jobs_stay_recoverable_without_resubmission(self):
        sha = self.job["sha256"]
        for state in ("snapshot_ready", "uploaded", "delivery_uncertain", "timed_out"):
            with self.subTest(state=state):
                self.job["state"] = state
                self.store.save(self.job)
                active = self.store.pending_for_hash(sha)
                self.assertEqual([job["job_id"] for job in active], [self.job["job_id"]])
                self.assertEqual(active[0]["state"], state)
        resumed = self.store.load(self.job["job_id"])
        self.assertEqual(observe(resumed, [row(1, status="success", score=0)]), "completed")
        self.store.save(resumed)
        self.assertEqual(self.store.pending_for_hash(sha), [])
        self.assertEqual(self.store.pending_for_hash("0" * 64), [])

    def test_save_atomically_replaces_complete_json(self):
        metadata = self.store.root / self.job["job_id"] / "job.json"
        before = metadata.read_bytes()
        self.job["state"] = "delivery_uncertain"
        real_replace = __import__("os").replace

        def inspect_replace(source, destination):
            self.assertEqual(metadata.read_bytes(), before)
            with Path(source).open(encoding="utf-8") as stream:
                self.assertEqual(json.load(stream)["state"], "delivery_uncertain")
            self.assertEqual(Path(destination), metadata)
            real_replace(source, destination)

        with mock.patch("online_judge.jobs.os.replace", side_effect=inspect_replace) as replace:
            self.store.save(self.job)
        replace.assert_called_once()
        self.assertEqual(self.store.load(self.job["job_id"]), self.job)
        self.assertEqual(list(metadata.parent.glob("*.tmp")), [])

    def test_failed_replace_preserves_previous_metadata(self):
        metadata = self.store.root / self.job["job_id"] / "job.json"
        before = metadata.read_bytes()
        self.job["state"] = "uploaded"
        with mock.patch("online_judge.jobs.os.replace", side_effect=OSError("simulated disk error")):
            with self.assertRaises(OSError):
                self.store.save(self.job)
        self.assertEqual(metadata.read_bytes(), before)
        self.assertEqual(list(metadata.parent.glob("*.tmp")), [])

    def test_job_id_path_traversal_is_rejected(self):
        for job_id in ("../other", "..", "a/b", "a\\b", "", "/absolute"):
            with self.subTest(job_id=job_id), self.assertRaises(ValueError):
                self.store.load(job_id)


class SubmissionLockTests(unittest.TestCase):
    def test_lock_refuses_a_second_process_and_releases_without_deleting_file(self):
        child = """from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / "automation"))
from online_judge.jobs import SubmissionLock
try:
    with SubmissionLock(Path(sys.argv[1])):
        print('acquired')
except RuntimeError:
    print('busy')
    sys.exit(23)
"""
        with temporary_directory() as directory:
            path = Path(directory) / "submission.lock"
            command = [sys.executable, "-c", child, str(path)]
            with SubmissionLock(path):
                result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                        text=True, timeout=10)
                self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
                self.assertIn("busy", result.stdout)
            self.assertTrue(path.exists())
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("acquired", result.stdout)
            self.assertTrue(path.exists())

    def test_exception_releases_lock_and_same_instance_cannot_reenter(self):
        with temporary_directory() as directory:
            path = Path(directory) / "submission.lock"
            lock = SubmissionLock(path)
            with self.assertRaisesRegex(ValueError, "body"):
                with lock:
                    with self.assertRaisesRegex(RuntimeError, "already held"):
                        lock.__enter__()
                    raise ValueError("body")
            with SubmissionLock(path):
                with self.assertRaises(RuntimeError):
                    with SubmissionLock(path):
                        self.fail("A concurrent lock unexpectedly succeeded")


if __name__ == "__main__":
    unittest.main()
