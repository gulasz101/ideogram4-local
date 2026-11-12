"""GUL-1431: the worker takes the M1 Max GPU slot around local jobs only.

Stdlib only. A fake hook script records its calls to a file.
"""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import ideogram4_local  # noqa: E402


class GpuSlotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.calls = root / "calls"
        self.hook = root / "gpu-slot.sh"
        self.hook.write_text(
            "#!/bin/bash\necho \"$* pid=$GPU_SLOT_OWNER_PID\" >> \"%s\"\nexit ${FAKE_HOOK_RC:-0}\n" % self.calls,
            encoding="utf-8",
        )
        self.hook.chmod(self.hook.stat().st_mode | stat.S_IEXEC)
        self.db = root / "jobs.db"
        self.output = root / "out" / "x.png"
        self.backend = ideogram4_local.SQLiteQueueBackend(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _calls(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def _run(self, engine, generate):
        self.backend.submit("text", "a fox", self.output, 1216, 832, False, engine=engine)
        with patch.object(ideogram4_local, "GPU_SLOT_HOOK", self.hook), \
             patch.object(ideogram4_local, "generate", generate):
            ideogram4_local._run_one_job(self.backend, lock=None)

    @staticmethod
    def _ok(**kwargs):
        return kwargs["output"]

    def test_local_engines_take_and_release_the_slot(self):
        for engine in ("ideogram4", "flux2-klein"):
            self.calls.unlink(missing_ok=True)
            self._run(engine, self._ok)
            calls = self._calls()
            self.assertEqual([c.split(" pid=")[0] for c in calls], [f"begin {engine}", "end"], engine)
            self.assertTrue(calls[0].endswith(f"pid={os.getpid()}"))

    def test_nanobanana_skips_the_slot(self):
        self._run("nanobanana", self._ok)
        self.assertEqual(self._calls(), [])

    def test_slot_is_released_when_the_job_fails(self):
        def boom(**kwargs):
            raise RuntimeError("sd-cli died")

        self._run("ideogram4", boom)
        self.assertEqual([c.split(" pid=")[0] for c in self._calls()], ["begin ideogram4", "end"])
        jobs = self.backend.list_jobs()
        self.assertEqual(jobs[0]["status"], "failed")

    def test_failing_hook_does_not_block_the_job(self):
        with patch.dict(os.environ, {"FAKE_HOOK_RC": "1"}):
            self._run("ideogram4", self._ok)
        self.assertEqual(self.backend.list_jobs()[0]["status"], "done")

    def test_missing_hook_is_a_noop(self):
        self.backend.submit("text", "a fox", self.output, 1216, 832, False, engine="ideogram4")
        with patch.object(ideogram4_local, "GPU_SLOT_HOOK", Path(self.tmp.name) / "nope.sh"), \
             patch.object(ideogram4_local, "generate", self._ok):
            ideogram4_local._run_one_job(self.backend, lock=None)
        self.assertEqual(self.backend.list_jobs()[0]["status"], "done")


if __name__ == "__main__":
    unittest.main()
