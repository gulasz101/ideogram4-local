import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

STUDIO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_DIR))

import imagegen  # noqa: E402

SSH_PREFIX = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "m1max"]
SCP_PREFIX = ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]


class FakeRunner:
    """Records argv and replays canned results; optionally acts like scp."""

    def __init__(self, responses=None, on_scp=None):
        self.calls = []
        self.responses = list(responses or [])
        self.on_scp = on_scp

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        if argv[0] == "scp" and self.on_scp is not None:
            self.on_scp(argv)
        if not self.responses:
            return imagegen.Result(0, "", "")
        return self.responses.pop(0)


def run_cli(argv, runner, env=None):
    out, err = io.StringIO(), io.StringIO()
    with patch.dict(os.environ, env or {}, clear=False):
        with redirect_stdout(out), redirect_stderr(err):
            code = imagegen.main(argv, runner=runner)
    return code, out.getvalue(), err.getvalue()


def job(**overrides):
    row = {
        "id": "job1",
        "status": "pending",
        "prompt_type": "json",
        "prompt_value": "{}",
        "output_path": "/Users/x/git/ideogram4-local/output/studio/2026-10-20/job1.png",
        "width": 1216,
        "height": 832,
        "verbose": 0,
        "created_at": "2026-10-20T10:00:00.000000",
        "started_at": None,
        "finished_at": None,
        "pid": None,
        "error": None,
    }
    row.update(overrides)
    return row


class SubmitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prompt = Path(self.tmp.name) / "My Prompt File.json"
        self.prompt.write_text('{"high_level_description": "x"}', encoding="utf-8")

    @patch("imagegen._today_str", return_value="2026-10-20")
    @patch("imagegen.secrets.token_hex", return_value="a1b2c3d4")
    def test_submit_builds_exact_scp_and_ssh_argv(self, _token, _today):
        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "loading model\nSubmitted job x\nabc123DEF\n", ""),
            ]
        )

        code, out, err = run_cli(["submit", "--prompt-json", str(self.prompt)], runner)

        self.assertEqual(code, 0, err)
        self.assertEqual(out, "abc123DEF\n")
        self.assertEqual(
            runner.calls[0],
            SSH_PREFIX + ["mkdir -p git/ideogram4-local/studio-incoming"],
        )
        self.assertEqual(
            runner.calls[1],
            SCP_PREFIX
            + [
                str(self.prompt.resolve()),
                "m1max:git/ideogram4-local/studio-incoming/my-prompt-file-a1b2c3d4.json",
            ],
        )
        self.assertEqual(
            runner.calls[2],
            SSH_PREFIX
            + [
                "cd git/ideogram4-local && python3 ideogram4_local.py submit "
                "--prompt-json studio-incoming/my-prompt-file-a1b2c3d4.json "
                "-o output/studio/2026-10-20/my-prompt-file-a1b2c3d4.png -W 1216 -H 832"
            ],
        )

    @patch("imagegen._today_str", return_value="2026-10-20")
    @patch("imagegen.secrets.token_hex", return_value="a1b2c3d4")
    def test_submit_quotes_remote_paths_with_spaces(self, _token, _today):
        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "abc123DEF\n", ""),
            ]
        )

        code, out, err = run_cli(
            ["submit", "--prompt-json", str(self.prompt), "--name", "My Fancy Prompt!"],
            runner,
            env={"IMAGEGEN_REMOTE_DIR": "git/my ideogram 4"},
        )

        self.assertEqual(code, 0, err)
        self.assertEqual(out, "abc123DEF\n")
        self.assertEqual(
            runner.calls[0][-1],
            "mkdir -p 'git/my ideogram 4/studio-incoming'",
        )
        self.assertEqual(
            runner.calls[1][-1],
            "m1max:git/my ideogram 4/studio-incoming/my-fancy-prompt-a1b2c3d4.json",
        )
        self.assertIn(
            "cd 'git/my ideogram 4' && python3 ideogram4_local.py submit",
            runner.calls[2][-1],
        )

    @patch("imagegen._today_str", return_value="2026-10-20")
    @patch("imagegen.secrets.token_hex", return_value="a1b2c3d4")
    def test_submit_uses_absolute_local_scp_path_with_colon(self, _token, _today):
        prompt = Path(self.tmp.name) / "a:b.json"
        prompt.write_text('{"high_level_description": "x"}', encoding="utf-8")
        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "abc123DEF\n", ""),
            ]
        )

        code, out, err = run_cli(["submit", "--prompt-json", str(prompt)], runner)

        self.assertEqual(code, 0, err)
        local_arg = runner.calls[1][-2]
        self.assertTrue(local_arg.startswith("/"), local_arg)
        self.assertEqual(local_arg, str(prompt.resolve()))

    @patch("imagegen._today_str", return_value="2026-10-20")
    @patch("imagegen.secrets.token_hex", return_value="a1b2c3d4")
    def test_submit_json_reports_job_and_remote_output(self, _token, _today):
        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "log\nabc123DEF\n", ""),
            ]
        )

        code, out, err = run_cli(
            ["submit", "--prompt-json", str(self.prompt), "--json"],
            runner,
            env={"IMAGEGEN_REMOTE_DIR": "git/ideogram4-local"},
        )

        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["job_id"], "abc123DEF")
        self.assertEqual(payload["engine"], "ideogram4")
        self.assertEqual(
            payload["remote_output"],
            "output/studio/2026-10-20/my-prompt-file-a1b2c3d4.png",
        )
        self.assertIn("submitted_at", payload)

    def test_submit_rejects_unsupported_engine(self):
        runner = FakeRunner()

        code, out, err = run_cli(
            ["submit", "--prompt-json", str(self.prompt), "--engine", "sdxl"],
            runner,
        )

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Unsupported engine 'sdxl'", err)
        self.assertIn("choose ideogram4 or flux2-klein", err)
        self.assertEqual(runner.calls, [])

    def test_submit_rejects_missing_prompt_file(self):
        runner = FakeRunner()

        code, _out, err = run_cli(
            ["submit", "--prompt-json", str(Path(self.tmp.name) / "nope.json")],
            runner,
        )

        self.assertEqual(code, 1)
        self.assertIn("not found", err)
        self.assertEqual(runner.calls, [])

    def test_ideogram_rejects_flux_only_flags(self):
        for extra in (
            ["--prompt-file", str(self.prompt)],
            ["--seed", "7"],
        ):
            with self.subTest(extra=extra):
                runner = FakeRunner()
                code, out, err = run_cli(
                    ["submit", "--prompt-json", str(self.prompt)] + extra, runner
                )
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertEqual(runner.calls, [])
                self.assertTrue(err.strip())

    def test_ideogram_requires_prompt_json(self):
        runner = FakeRunner()

        code, out, err = run_cli(
            ["submit", "--prompt", "a robot with a wrench"], runner
        )

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("--prompt-json", err)
        self.assertEqual(runner.calls, [])


class FluxSubmitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prompt_text = "a fox in a server room during a power cut"

    @patch("imagegen._today_str", return_value="2026-10-20")
    @patch("imagegen.secrets.token_hex", return_value="a1b2c3d4")
    def test_submit_builds_exact_flux_argv(self, _token, _today):
        uploaded = {}

        def on_scp(argv):
            uploaded["local"] = Path(argv[-2])
            uploaded["content"] = Path(argv[-2]).read_text(encoding="utf-8")
            uploaded["remote"] = argv[-1]

        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "Submitting...\nabc123DEF\n", ""),
            ],
            on_scp=on_scp,
        )

        code, out, err = run_cli(
            ["submit", "--engine", "flux2-klein", "--prompt", self.prompt_text],
            runner,
        )

        self.assertEqual(code, 0, err)
        self.assertEqual(out, "abc123DEF\n")
        stem = "a-fox-in-a-server-room-a1b2c3d4"  # first six words, then the token
        self.assertEqual(
            uploaded["remote"],
            "m1max:git/ideogram4-local/studio-incoming/{}.txt".format(stem),
        )
        self.assertEqual(uploaded["content"], self.prompt_text)
        self.assertEqual(uploaded["local"].suffix, ".txt")
        self.assertFalse(uploaded["local"].exists(), "temp prompt must be deleted")
        self.assertEqual(
            runner.calls[2],
            SSH_PREFIX
            + [
                "cd git/ideogram4-local && python3 ideogram4_local.py submit "
                "--engine flux2-klein --prompt-file studio-incoming/{}.txt "
                "-o output/studio/2026-10-20/{}.png -W 1216 -H 832".format(stem, stem)
            ],
        )

    @patch("imagegen._today_str", return_value="2026-10-20")
    @patch("imagegen.secrets.token_hex", return_value="a1b2c3d4")
    def test_submit_appends_seed(self, _token, _today):
        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "abc123DEF\n", ""),
            ]
        )

        code, out, err = run_cli(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt",
                self.prompt_text,
                "--seed",
                "7",
            ],
            runner,
        )

        self.assertEqual(code, 0, err)
        self.assertEqual(out, "abc123DEF\n")
        self.assertTrue(runner.calls[2][-1].endswith("-W 1216 -H 832 --seed 7"))

    @patch("imagegen._today_str", return_value="2026-10-20")
    @patch("imagegen.secrets.token_hex", return_value="a1b2c3d4")
    def test_submit_prompt_file_uses_its_stem(self, _token, _today):
        prompt = Path(self.tmp.name) / "Forest At Dusk.txt"
        prompt.write_text("a mossy forest at dusk\n", encoding="utf-8")
        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "abc123DEF\n", ""),
            ]
        )

        code, out, err = run_cli(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt-file",
                str(prompt),
            ],
            runner,
        )

        self.assertEqual(code, 0, err)
        self.assertEqual(out, "abc123DEF\n")
        self.assertEqual(
            runner.calls[1][-1],
            "m1max:git/ideogram4-local/studio-incoming/forest-at-dusk-a1b2c3d4.txt",
        )
        self.assertEqual(runner.calls[1][-2], str(prompt.resolve()))
        self.assertIn("forest-at-dusk-a1b2c3d4", runner.calls[2][-1])

    def test_flux_json_reports_the_engine(self):
        runner = FakeRunner(
            [
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "", ""),
                imagegen.Result(0, "abc123DEF\n", ""),
            ]
        )

        code, out, err = run_cli(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt",
                self.prompt_text,
                "--json",
            ],
            runner,
        )

        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["job_id"], "abc123DEF")
        self.assertEqual(payload["engine"], "flux2-klein")
        self.assertTrue(payload["remote_output"].endswith(".png"))

    def test_flux_rejects_prompt_json(self):
        runner = FakeRunner()

        code, out, err = run_cli(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt-json",
                str(Path(self.tmp.name) / "x.json"),
            ],
            runner,
        )

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("natural-language prompt", err)
        self.assertEqual(runner.calls, [])

    def test_flux_requires_exactly_one_prompt_source(self):
        runner = FakeRunner()

        code, _out, err = run_cli(["submit", "--engine", "flux2-klein"], runner)
        self.assertEqual(code, 1)
        self.assertIn("exactly one", err)

        prompt = Path(self.tmp.name) / "x.txt"
        prompt.write_text("a fox", encoding="utf-8")
        code, _out, err = run_cli(
            [
                "submit",
                "--engine",
                "flux2-klein",
                "--prompt",
                "a fox",
                "--prompt-file",
                str(prompt),
            ],
            runner,
        )
        self.assertEqual(code, 1)
        self.assertIn("exactly one", err)
        self.assertEqual(runner.calls, [])

    def test_flux_rejects_empty_prompt(self):
        runner = FakeRunner()

        code, out, err = run_cli(
            ["submit", "--engine", "flux2-klein", "--prompt", "   "], runner
        )

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("empty", err)
        self.assertEqual(runner.calls, [])


class StatusTests(unittest.TestCase):
    def test_queue_ahead_and_eta_for_pending_job(self):
        target = job(id="target", status="pending", created_at="2026-10-20T10:00:00")
        listing = [
            job(id="newer-running", status="running", created_at="2026-10-20T11:00:00"),
            job(id="old-pending-1", status="pending", created_at="2026-10-20T08:00:00"),
            job(id="old-running", status="running", created_at="2026-10-20T09:00:00"),
            job(id="old-done", status="done", created_at="2026-10-20T07:00:00"),
            target,
        ]
        runner = FakeRunner(
            [
                imagegen.Result(0, json.dumps(target), ""),
                imagegen.Result(0, json.dumps(listing), ""),
            ]
        )

        code, out, err = run_cli(["status", "target"], runner)

        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["queue_ahead"], 2)
        self.assertEqual(payload["eta_minutes"], 3 * 21)
        self.assertEqual(
            runner.calls[0],
            SSH_PREFIX
            + ["cd git/ideogram4-local && python3 ideogram4_local.py status target"],
        )
        self.assertEqual(
            runner.calls[1],
            SSH_PREFIX
            + [
                "cd git/ideogram4-local && python3 ideogram4_local.py list --limit 200"
            ],
        )

    def test_eta_is_zero_for_finished_job(self):
        target = job(id="target", status="done", created_at="2026-10-20T10:00:00")
        listing = [
            job(id="old-running", status="running", created_at="2026-10-20T09:00:00"),
            target,
        ]
        runner = FakeRunner(
            [
                imagegen.Result(0, json.dumps(target), ""),
                imagegen.Result(0, json.dumps(listing), ""),
            ]
        )

        code, out, err = run_cli(["status", "target"], runner)

        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["queue_ahead"], 1)
        self.assertEqual(payload["eta_minutes"], 0)

    def test_mixed_queue_eta_counts_each_engine(self):
        target = job(
            id="target",
            status="pending",
            created_at="2026-10-20T10:00:00",
            engine="flux2-klein",
        )
        listing = [
            job(
                id="ideogram-running",
                status="running",
                created_at="2026-10-20T08:00:00",
                engine="ideogram4",
            ),
            job(
                id="flux-pending",
                status="pending",
                created_at="2026-10-20T09:00:00",
                engine="flux2-klein",
                seed=1234,
            ),
            target,
        ]
        runner = FakeRunner(
            [
                imagegen.Result(0, json.dumps(target), ""),
                imagegen.Result(0, json.dumps(listing), ""),
            ]
        )

        code, out, err = run_cli(["status", "target"], runner)

        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["queue_ahead"], 2)
        self.assertEqual(payload["eta_minutes"], 21 + 3 + 3)

    def test_status_surfaces_remote_error(self):
        runner = FakeRunner([imagegen.Result(1, "", "Job not found: nope")])

        code, out, err = run_cli(["status", "nope"], runner)

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Job not found: nope", err)


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest = Path(self.tmp.name) / "staging"

    def test_fetch_done_job_exits_zero(self):
        target = job(id="job1", status="done")
        runner = FakeRunner(
            [imagegen.Result(0, json.dumps(target), "")],
            on_scp=lambda argv: Path(argv[-1]).write_bytes(b"\x89PNG" + b"0" * 64),
        )

        code, out, err = run_cli(
            ["fetch", "job1", "--dest", str(self.dest)], runner
        )

        self.assertEqual(code, 0, err)
        local = Path(out.strip())
        self.assertEqual(local, self.dest.resolve() / "job1.png")
        self.assertGreater(local.stat().st_size, 0)
        self.assertEqual(
            runner.calls[1],
            SCP_PREFIX
            + [
                "m1max:/Users/x/git/ideogram4-local/output/studio/2026-10-20/job1.png",
                str(local),
            ],
        )

    def test_fetch_pending_job_exits_three(self):
        target = job(id="job1", status="running")
        runner = FakeRunner([imagegen.Result(0, json.dumps(target), "")])

        code, out, err = run_cli(
            ["fetch", "job1", "--dest", str(self.dest)], runner
        )

        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("running", err)
        self.assertEqual(len(runner.calls), 1)

    def test_fetch_failed_job_exits_four_with_error(self):
        target = job(id="job1", status="failed", error="CUDA out of memory")
        runner = FakeRunner([imagegen.Result(0, json.dumps(target), "")])

        code, out, err = run_cli(
            ["fetch", "job1", "--dest", str(self.dest)], runner
        )

        self.assertEqual(code, 4)
        self.assertEqual(out, "")
        self.assertIn("CUDA out of memory", err)
        self.assertEqual(len(runner.calls), 1)

    def test_fetch_empty_download_exits_one(self):
        target = job(id="job1", status="done")
        runner = FakeRunner(
            [imagegen.Result(0, json.dumps(target), "")],
            on_scp=lambda argv: Path(argv[-1]).write_bytes(b""),
        )

        code, out, err = run_cli(
            ["fetch", "job1", "--dest", str(self.dest)], runner
        )

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("empty", err)


class HelperTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(imagegen.slugify("My Fancy Prompt!"), "my-fancy-prompt")
        self.assertEqual(imagegen.slugify("--already--safe--"), "already-safe")
        self.assertEqual(imagegen.slugify("!!!"), "prompt")

    def test_parse_json_tolerates_log_lines(self):
        parsed = imagegen.parse_json_output('note: hi\n[{"id": "a"}]\n')
        self.assertEqual(parsed, [{"id": "a"}])


if __name__ == "__main__":
    unittest.main()
