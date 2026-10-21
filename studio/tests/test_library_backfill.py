import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library_backfill import _first_paragraph_after, backfill  # noqa: E402

MAX_ROOT = "/Users/wojciechgula/wojtek.second.brain.obsidian.vault"


class LibraryBackfillTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="library-backfill-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.vault = self.tmp / "vault"
        self.library = self.tmp / "lib"
        (self.vault / "tech_blog").mkdir(parents=True)
        self.db = self.tmp / "jobs.db"
        self._create_db()

    def _create_db(self):
        connection = sqlite3.connect(self.db)
        connection.execute(
            """
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
            )
            """
        )
        self.rows = [
            # embedded in a draft post
            (
                "jobEmbedded",
                "done",
                "json",
                json.dumps(
                    {
                        "high_level_description": "embedded header",
                        "generation": {
                            "steps": 20,
                            "safety_bypass": True,
                            "safety_bypass_mode": "single_pass",
                        },
                    }
                ),
                f"{MAX_ROOT}/tech_blog/assets/2026-10-01/header.png",
                1216,
                832,
                "2026-10-01T10:00:00.000000",
                "2026-10-01T10:10:00.000000",
            ),
            # never embedded
            (
                "jobUnused",
                "done",
                "json",
                json.dumps({"high_level_description": "unused", "generation": {}}),
                f"{MAX_ROOT}/tech_blog/assets/2026-10-01/unused.png",
                1216,
                832,
                "2026-10-01T11:00:00.000000",
                "2026-10-01T11:10:00.000000",
            ),
            # two jobs, same output; the later finished_at owns it
            (
                "jobOld",
                "done",
                "json",
                json.dumps({"high_level_description": "old", "generation": {}}),
                f"{MAX_ROOT}/tech_blog/assets/2026-10-02/shared.png",
                1216,
                832,
                "2026-10-02T10:00:00.000000",
                "2026-10-02T10:10:00.000000",
            ),
            (
                "jobNew",
                "done",
                "json",
                json.dumps({"high_level_description": "new", "generation": {}}),
                f"{MAX_ROOT}/tech_blog/assets/2026-10-02/shared.png",
                1216,
                832,
                "2026-10-02T12:00:00.000000",
                "2026-10-02T12:10:00.000000",
            ),
            # max-only
            (
                "jobMaxOnly",
                "done",
                "json",
                json.dumps({"high_level_description": "max only", "generation": {}}),
                "/Users/wojciechgula/git/ideogram4-local/output/max-only.png",
                1216,
                832,
                "2026-10-03T10:00:00.000000",
                "2026-10-03T10:10:00.000000",
            ),
            # failed job: must not get a record
            (
                "jobFailed",
                "failed",
                "json",
                "{}",
                f"{MAX_ROOT}/tech_blog/assets/2026-10-04/failed.png",
                1216,
                832,
                "2026-10-04T10:00:00.000000",
                "2026-10-04T10:10:00.000000",
            ),
            # text prompt
            (
                "jobText",
                "done",
                "text",
                "a small happy robot holding a wrench, flat vector icon",
                f"{MAX_ROOT}/tech_blog/assets/2026-10-05/text.png",
                1024,
                1024,
                "2026-10-05T10:00:00.000000",
                "2026-10-05T10:10:00.000000",
            ),
        ]
        connection.executemany(
            """
            INSERT INTO jobs (id, status, prompt_type, prompt_value, output_path,
                              width, height, created_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self.rows,
        )
        connection.commit()
        connection.close()

    def _write_post(self):
        post = self.vault / "tech_blog/2026-10-01-post.md"
        post.parent.mkdir(parents=True, exist_ok=True)
        post.write_text(
            "---\n"
            'title: "A post"\n'
            "status: draft\n"
            "---\n"
            "\n"
            "# A post\n"
            "\n"
            "## First section\n"
            "\n"
            "![A test alt](assets/2026-10-01/header.png)\n"
            "\n"
            "The first paragraph after the embed explains why this image exists. "
            + ("It keeps going for a while. " * 30)
            + "\n"
            "\n"
            "## Later section\n"
            "\n"
            "More text.\n",
            encoding="utf-8",
        )
        for asset in (
            "assets/2026-10-01/header.png",
            "assets/2026-10-01/unused.png",
            "assets/2026-10-02/shared.png",
            "assets/2026-10-05/text.png",
        ):
            path = self.vault / "tech_blog" / asset
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"png")

    def _run(self, dry_run=False):
        return backfill(
            db=self.db,
            vault=self.vault,
            max_vault_root=MAX_ROOT,
            library_dir=self.library,
            dry_run=dry_run,
        )

    def _record(self, name):
        matches = list(self.library.rglob(name))
        self.assertEqual(len(matches), 1, f"expected exactly one {name}")
        return matches[0]

    def test_embedded_record(self):
        self._write_post()
        self._run()
        record = self._record("2026-10-01-header--jobEmbedded.md")
        text = record.read_text(encoding="utf-8")
        self.assertIn('posts: ["tech_blog/2026-10-01-post.md"]', text)
        self.assertIn('post_status: "draft"', text)
        self.assertIn("![[tech_blog/assets/2026-10-01/header.png]]", text)
        self.assertIn('From [[2026-10-01-post]], section "First section":', text)
        self.assertIn("> A test alt", text)
        excerpt_line = [line for line in text.splitlines() if line.startswith("> The first")][0]
        self.assertLessEqual(len(excerpt_line) - 2, 400)

    def test_unused_vault_image(self):
        self._write_post()
        self._run()
        text = self._record("2026-10-01-unused--jobUnused.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("posts: []", text)
        self.assertIn("No post embeds this image.", text)
        self.assertIn('asset_location: "vault"', text)
        self.assertIn("asset_present: true", text)

    def test_obsidian_wikilink_embed(self):
        wiki = self.vault / "tech_blog/2026-10-06-wiki.md"
        wiki.write_text(
            "---\nstatus: published\n---\n\n"
            "## Wiki section\n\n"
            "![[assets/2026-10-01/unused.png]]\n\n"
            "A paragraph after the wiki embed.\n",
            encoding="utf-8",
        )
        self._run()
        text = self._record("2026-10-01-unused--jobUnused.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('posts: ["tech_blog/2026-10-06-wiki.md"]', text)
        self.assertIn('post_status: "published"', text)
        self.assertIn('From [[2026-10-06-wiki]], section "Wiki section":', text)
        self.assertIn("> A paragraph after the wiki embed.", text)

    def test_superseded_pair(self):
        self._write_post()
        self._run()
        old = self._record("2026-10-02-shared--jobOld.md").read_text(encoding="utf-8")
        new = self._record("2026-10-02-shared--jobNew.md").read_text(encoding="utf-8")
        self.assertIn('superseded_by: "jobNew"', old)
        self.assertIn("superseded_by: null", new)
        self.assertNotIn("![[tech_blog/assets/2026-10-02/shared.png]]", old)
        self.assertIn("![[tech_blog/assets/2026-10-02/shared.png]]", new)

    def test_max_only(self):
        self._run()
        text = self._record("2026-10-03-max-only--jobMaxOnly.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'asset: "/Users/wojciechgula/git/ideogram4-local/output/max-only.png"',
            text,
        )
        self.assertIn('asset_location: "max-only"', text)
        self.assertIn("asset_present: false", text)
        self.assertNotIn("![[]]", text)

    def test_failed_job_has_no_record(self):
        self._run()
        self.assertEqual(list(self.library.rglob("2026-10-04-*")), [])

    def test_text_prompt(self):
        self._run()
        text = self._record("2026-10-05-text--jobText.md").read_text(encoding="utf-8")
        self.assertIn('prompt_type: "text"', text)
        self.assertIn("generation: null", text)
        self.assertIn("```\na small happy robot", text)

    def test_second_run_is_byte_identical(self):
        self._write_post()
        first = self._run()
        self.assertEqual(first["created"], 6)
        before = {
            path.relative_to(self.library): path.read_bytes()
            for path in self.library.rglob("*")
            if path.is_file()
        }
        second = self._run()
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["skipped"], 6)
        after = {
            path.relative_to(self.library): path.read_bytes()
            for path in self.library.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)
        self.assertIn(self.library / "index.md", list(self.library.rglob("*")))

    def test_existing_hand_edited_record_is_kept(self):
        self._write_post()
        self._run()
        record = self._record("2026-10-01-header--jobEmbedded.md")
        edited = record.read_text(encoding="utf-8") + "\n## My verdict\n\nkeep me\n"
        record.write_text(edited, encoding="utf-8")
        counts = self._run()
        self.assertEqual(counts["created"], 0)
        self.assertEqual(record.read_text(encoding="utf-8"), edited)

    def test_dry_run_writes_nothing(self):
        self._write_post()
        counts = self._run(dry_run=True)
        self.assertEqual(counts["created"], 6)
        self.assertEqual(list(self.library.rglob("*")), [])

    def test_excerpt_skips_fenced_code_after_embed(self):
        lines = [
            "![x](assets/a.png)",
            "",
            "```bash",
            "kubectl get pods",
            "",
            "kubectl logs foo",
            "```",
            "",
            "Real prose here.",
        ]
        self.assertEqual(_first_paragraph_after(lines, 0), "Real prose here.")

    def test_index_is_deterministic(self):
        self._write_post()
        self._run()
        first = (self.library / "index.md").read_bytes()
        self._run()
        self.assertEqual((self.library / "index.md").read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
