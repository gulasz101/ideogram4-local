"""Phase 6 queue/worker tests: engine routing, migration and the FLUX runner.

Stdlib only and no torch: the worker has to stay importable on Homebrew Python.
"""

import importlib.util
import io
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import ideogram4_local  # noqa: E402

OLD_SCHEMA = """
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    prompt_type TEXT NOT NULL,
    prompt_value TEXT NOT NULL,
    output_path TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    verbose INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    pid INTEGER,
    error TEXT
);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created ON jobs(created_at);
"""


def columns(db_path):
    connection = sqlite3.connect(db_path)
    try:
        return [row[1] for row in connection.execute("PRAGMA table_info(jobs)")]
    finally:
        connection.close()


def main_with_argv(argv, db_path):
    out, err = io.StringIO(), io.StringIO()
    with patch.object(sys, "argv", ["ideogram4_local.py"] + argv):
        with patch.object(ideogram4_local, "DB_PATH", db_path):
            with redirect_stdout(out), redirect_stderr(err):
                code = ideogram4_local.main()
    return code, out.getvalue(), err.getvalue()


class QueueTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "jobs.db"

    def _old_schema_db(self):
        connection = sqlite3.connect(self.db)
        connection.executescript(OLD_SCHEMA)
        connection.executemany(
            """
            INSERT INTO jobs (id, status, prompt_type, prompt_value, output_path,
                              width, height, created_at)
            VALUES (?, 'done', 'json', '{}', ?, 1216, 832, ?)
            """,
            [
                ("old1", "/tmp/old1.png", "2026-10-01T10:00:00"),
                ("old2", "/tmp/old2.png", "2026-10-01T11:00:00"),
            ],
        )
        connection.commit()
        connection.close()


class MigrationTests(QueueTestCase):
    def test_old_schema_gains_engine_and_seed(self):
        self._old_schema_db()

        backend = ideogram4_local.SQLiteQueueBackend(self.db)

        self.assertIn("engine", columns(self.db))
        self.assertIn("seed", columns(self.db))
        rows = backend.list_jobs()
        self.assertEqual({row["engine"] for row in rows}, {"ideogram4"})
        self.assertEqual({row["seed"] for row in rows}, {None})
        self.assertEqual({row["status"] for row in rows}, {"done"})

    def test_second_init_is_a_noop(self):
        self._old_schema_db()
        first = ideogram4_local.SQLiteQueueBackend(self.db)
        before = first.list_jobs()

        second = ideogram4_local.SQLiteQueueBackend(self.db)

        self.assertEqual(second.list_jobs(), before)
        self.assertEqual(columns(self.db).count("engine"), 1)
        self.assertEqual(columns(self.db).count("seed"), 1)


class SubmitTests(QueueTestCase):
    def test_flux_job_gets_an_integer_seed(self):
        backend = ideogram4_local.SQLiteQueueBackend(self.db)

        job_id = backend.submit(
            prompt_type="text",
            prompt_value="a fox in a server room",
            output_path=Path("/tmp/fox.png"),
            width=1216,
            height=832,
            verbose=False,
            engine="flux2-klein",
        )

        job = backend.get(job_id)
        self.assertEqual(job["engine"], "flux2-klein")
        self.assertIsInstance(job["seed"], int)
        self.assertGreaterEqual(job["seed"], 0)
        self.assertLess(job["seed"], 2**32)

    def test_flux_job_keeps_an_explicit_seed(self):
        backend = ideogram4_local.SQLiteQueueBackend(self.db)

        job_id = backend.submit(
            "text", "a fox", Path("/tmp/fox.png"), 1216, 832, False,
            engine="flux2-klein", seed=7,
        )

        self.assertEqual(backend.get(job_id)["seed"], 7)

    def test_default_job_is_ideogram4_without_a_seed(self):
        backend = ideogram4_local.SQLiteQueueBackend(self.db)

        job_id = backend.submit(
            "json", "{}", Path("/tmp/x.png"), 1216, 832, False
        )

        job = backend.get(job_id)
        self.assertEqual(job["engine"], "ideogram4")
        self.assertIsNone(job["seed"])

    def test_unknown_engine_is_rejected(self):
        backend = ideogram4_local.SQLiteQueueBackend(self.db)

        with self.assertRaises(ValueError):
            backend.submit(
                "text", "x", Path("/tmp/x.png"), 1216, 832, False, engine="sdxl"
            )
        self.assertEqual(backend.list_jobs(), [])


class WorkerTests(QueueTestCase):
    def setUp(self):
        super().setUp()
        self.output = Path(self.tmp.name) / "drafts" / "fox.png"
        self.flux_python = Path(self.tmp.name) / "venv-python"
        self.flux_python.write_text("#!/bin/sh\n", encoding="utf-8")

    def _fake_run(self, created=True):
        def fake_run(cmd, **kwargs):
            fake_run.cmd = cmd
            fake_run.kwargs = kwargs
            if created:
                Path(cmd[cmd.index("-o") + 1]).write_bytes(b"\x89PNG")
            return subprocess.CompletedProcess(cmd, 0)

        return fake_run

    def test_generate_dispatches_to_the_flux_runner(self):
        fake_run = self._fake_run()
        prompt = "a fox in a server room, warm monitor light"

        with patch.object(ideogram4_local, "FLUX_PYTHON", self.flux_python):
            with patch.object(ideogram4_local, "SD_CLI", Path("/nonexistent/sd-cli")):
                with patch.object(ideogram4_local.subprocess, "run", fake_run):
                    expected = ideogram4_local._flux_cmd(
                        self.output, 1216, 832, 7
                    )
                    result = ideogram4_local.generate(
                        "text",
                        prompt,
                        self.output,
                        width=1216,
                        height=832,
                        engine="flux2-klein",
                        seed=7,
                    )

        self.assertEqual(result, self.output)
        self.assertEqual(fake_run.cmd, expected)
        self.assertEqual(fake_run.kwargs["input"], prompt)
        self.assertTrue(fake_run.kwargs["text"])
        self.assertEqual(fake_run.kwargs["env"]["HF_HUB_OFFLINE"], "1")
        self.assertEqual(
            fake_run.kwargs["env"]["PYTORCH_MPS_HIGH_WATERMARK_RATIO"], "0.0"
        )

    def test_generate_raises_when_the_flux_python_is_missing(self):
        with patch.object(
            ideogram4_local, "FLUX_PYTHON", Path(self.tmp.name) / "missing"
        ):
            with self.assertRaises(RuntimeError) as caught:
                ideogram4_local.generate(
                    "text", "a fox", self.output, engine="flux2-klein", seed=1
                )

        self.assertIn("FLUX python not found", str(caught.exception))

    def test_generate_rejects_a_nonzero_exit(self):
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1)

        with patch.object(ideogram4_local, "FLUX_PYTHON", self.flux_python):
            with patch.object(ideogram4_local.subprocess, "run", fake_run):
                with self.assertRaises(RuntimeError):
                    ideogram4_local.generate(
                        "text", "a fox", self.output, engine="flux2-klein", seed=1
                    )

    def test_generate_rejects_an_unknown_engine(self):
        with self.assertRaises(RuntimeError):
            ideogram4_local.generate("text", "a fox", self.output, engine="bogus")

    def test_run_one_job_forwards_engine_and_seed(self):
        backend = ideogram4_local.SQLiteQueueBackend(self.db)
        job_id = backend.submit(
            "text", "a fox", self.output, 1216, 832, False,
            engine="flux2-klein", seed=99,
        )
        captured = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            Path(kwargs["output"]).parent.mkdir(parents=True, exist_ok=True)
            Path(kwargs["output"]).write_bytes(b"\x89PNG")
            return kwargs["output"]

        with patch.object(ideogram4_local, "generate", fake_generate):
            worked = ideogram4_local._run_one_job(backend, lock=None)

        self.assertTrue(worked)
        self.assertEqual(captured["engine"], "flux2-klein")
        self.assertEqual(captured["seed"], 99)
        self.assertEqual(backend.get(job_id)["status"], "done")


class CliTests(QueueTestCase):
    def test_submit_flux_prompt_file_stores_a_text_row(self):
        prompt = Path(self.tmp.name) / "fox.txt"
        prompt.write_text("a fox in a server room\n", encoding="utf-8")
        output = Path(self.tmp.name) / "fox.png"

        code, out, err = main_with_argv(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt-file",
                str(prompt),
                "-o",
                str(output),
            ],
            self.db,
        )

        self.assertEqual(code, 0, err)
        job = ideogram4_local.SQLiteQueueBackend(self.db).get(out.strip())
        self.assertEqual(job["prompt_type"], "text")
        self.assertEqual(job["prompt_value"], "a fox in a server room")
        self.assertEqual(job["engine"], "flux2-klein")
        self.assertIsInstance(job["seed"], int)

    def test_flux_rejects_prompt_json(self):
        code, out, err = main_with_argv(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt-json",
                str(Path(self.tmp.name) / "x.json"),
                "-o",
                str(Path(self.tmp.name) / "x.png"),
            ],
            self.db,
        )

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("natural-language prompt", err)

    def test_width_must_be_a_multiple_of_16(self):
        code, out, err = main_with_argv(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt",
                "a fox",
                "-W",
                "1000",
                "-o",
                str(Path(self.tmp.name) / "x.png"),
            ],
            self.db,
        )

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("-W", err)

    def test_ideogram_rejects_a_seed(self):
        prompt = Path(self.tmp.name) / "x.json"
        prompt.write_text("{}", encoding="utf-8")

        code, out, err = main_with_argv(
            [
                "submit",
                "--prompt-json",
                str(prompt),
                "--seed",
                "7",
                "-o",
                str(Path(self.tmp.name) / "x.png"),
            ],
            self.db,
        )

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--seed", err)

    def test_empty_prompt_is_rejected(self):
        code, out, err = main_with_argv(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt",
                "   ",
                "-o",
                str(Path(self.tmp.name) / "x.png"),
            ],
            self.db,
        )

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("empty", err)

    def test_unknown_engine_is_rejected(self):
        code, _out, err = main_with_argv(
            [
                "submit",
                "--engine",
                "sdxl",
                "--prompt",
                "a fox",
                "-o",
                str(Path(self.tmp.name) / "x.png"),
            ],
            self.db,
        )

        self.assertEqual(code, 2)
        self.assertIn("sdxl", err)


class RunnerTests(unittest.TestCase):
    def _load_runner(self):
        path = REPO_ROOT / "flux2_klein.py"
        spec = importlib.util.spec_from_file_location("flux2_klein", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_runner_imports_without_torch(self):
        self.assertNotIn("torch", sys.modules)

        module = self._load_runner()

        self.assertNotIn("torch", sys.modules)
        self.assertEqual(module.MODEL_ID, "black-forest-labs/FLUX.2-klein-4B")

    def test_parser_defaults(self):
        module = self._load_runner()

        args = module.build_parser().parse_args(["-o", "x.png", "--seed", "1"])

        self.assertEqual((args.width, args.height, args.steps), (1216, 832, 4))


if __name__ == "__main__":
    unittest.main()
