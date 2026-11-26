"""Tests for the CLI.

The CLI must work with no credentials configured, because ``doctor`` is
what tells the user what to fix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from liuyao_kb.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test in an empty directory with no inherited credentials."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LIUYAO_KB_CONFIG_DIR", str(tmp_path))
    for key in (
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_DATABASE",
        "GEMINI_API_KEY",
        "LIUYAO_KB_SOURCES",
    ):
        monkeypatch.delenv(key, raising=False)


class TestDoctor:
    def test_runs_without_credentials(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1  # missing credentials is a failure state
        assert "Neo4j credentials" in result.stdout

    def test_json_output_is_machine_readable(self) -> None:
        result = runner.invoke(app, ["doctor", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        names = {check["name"] for check in payload["checks"]}
        assert "Neo4j credentials" in names

    def test_neo4j_ok_without_gemini_is_not_failed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from liuyao_kb.neo4j import driver

        monkeypatch.setattr(
            driver,
            "check_connection",
            lambda _settings: {
                "ok": True,
                "target": "neo4j+s://abc123.databases.neo4j.io",
                "username": "abc123",
                "database": "abc123",
                "profile": "neo4j://abc123.databases.neo4j.io:7687",
                "server_version": "5.27-aura",
                "edition": "enterprise",
                "error": None,
                "hint": None,
            },
        )
        monkeypatch.setenv("NEO4J_URI", "neo4j+s://abc123.databases.neo4j.io")
        monkeypatch.setenv("NEO4J_USERNAME", "abc123")
        monkeypatch.setenv("NEO4J_PASSWORD", "super-secret-value")
        monkeypatch.setenv("NEO4J_DATABASE", "abc123")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        result = runner.invoke(app, ["doctor", "--json"])
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        gemini = next(check for check in payload["checks"] if check["name"] == "Gemini API key")
        assert gemini["status"] == "skipped"
        assert "super-secret-value" not in result.stdout

    def test_never_prints_a_password(self, tmp_path: Path, monkeypatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "NEO4J_URI=neo4j+s://abc123.databases.neo4j.io\n"
            "NEO4J_USERNAME=abc123\n"
            "NEO4J_PASSWORD=super-secret-value\n"
            "NEO4J_DATABASE=abc123\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("LIUYAO_KB_CONFIG_DIR", str(tmp_path))
        result = runner.invoke(app, ["doctor", "--json"])
        assert "super-secret-value" not in result.stdout


class TestSourcesList:
    def test_reports_a_missing_config(self) -> None:
        result = runner.invoke(app, ["sources", "list"])
        assert result.exit_code == 1
        assert "No sources config found" in result.stdout

    def test_lists_sources(self, tmp_path: Path) -> None:
        (tmp_path / "sources.yaml").write_text(
            yaml.safe_dump({"curated_notes": {"enabled": True}}), encoding="utf-8"
        )
        result = runner.invoke(app, ["sources", "list"])
        assert result.exit_code == 0
        assert "curated_lesson_note" in result.stdout
        assert "raw_asr" in result.stdout

    def test_json_output(self, tmp_path: Path) -> None:
        (tmp_path / "sources.yaml").write_text(
            yaml.safe_dump({"curated_notes": {"enabled": True}}), encoding="utf-8"
        )
        result = runner.invoke(app, ["sources", "list", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["sources"]


class TestIngestDryRun:
    def test_dry_run_reports_the_plan(self, tmp_path: Path) -> None:
        (tmp_path / "sources.yaml").write_text(
            yaml.safe_dump({"curated_notes": {"enabled": True}}), encoding="utf-8"
        )
        result = runner.invoke(app, ["ingest", "run", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.stdout

    def test_write_requires_a_repository(self, tmp_path: Path) -> None:
        (tmp_path / "sources.yaml").write_text(
            yaml.safe_dump({"curated_notes": {"enabled": True}}), encoding="utf-8"
        )
        result = runner.invoke(app, ["ingest", "run", "--no-dry-run"])
        assert result.exit_code == 1
        assert "--repository is required" in result.stdout

    def test_missing_config_is_reported(self) -> None:
        result = runner.invoke(app, ["ingest", "run", "--dry-run"])
        assert result.exit_code == 1
        assert "No sources config found" in result.stdout


class TestIngestReferencesAndFailures:
    """The CLI itself must build REFERENCES from the sources config,
    and a plan link whose endpoint is missing must fail the run."""

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_dry_run_builds_references_from_config(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        self._write(
            repo / "docs/lessons/lesson-19-notes-v0.1.md",
            "# Lesson 19\n\n## 3. Section Three\n\nPrimary paragraph for case two.\n\n"
            "## 7. Section Seven\n\nPrimary paragraph for case three.\n\n"
            "## 10. Section Ten\n\nSummary paragraph.\n",
        )
        cases = repo / "materials/class-cases/lesson-19"
        for case_id, stem in (
            ("L19-C02-synthetic", "case-002"),
            ("L19-C03-synthetic", "case-003"),
        ):
            self._write(
                cases / f"{stem}.json",
                json.dumps(
                    {
                        "recordType": "class-case",
                        "id": case_id,
                        "lessonId": "lesson-19",
                        "matchStatus": "verified",
                    }
                ),
            )
            self._write(cases / f"{stem}-analysis.md", f"# {case_id}\n\nPaired body.\n")
        config = {
            "curated_notes": {"root": str(repo)},
            "class_cases": {"root": str(repo)},
            "case_references": [
                {
                    "case_id": "L19-C03-synthetic",
                    "notes_path": "docs/lessons/lesson-19-notes-v0.1.md",
                    "sections": [{"heading_prefix": "7. ", "role": "primary"}],
                },
                {
                    "case_id": "L19-C02-synthetic",
                    "notes_path": "docs/lessons/lesson-19-notes-v0.1.md",
                    "sections": [
                        {"heading_prefix": "3. ", "role": "primary"},
                        {"heading_prefix": "10. ", "role": "secondary"},
                    ],
                },
            ],
        }
        (tmp_path / "sources.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
        result = runner.invoke(
            app, ["ingest", "run", "--dry-run", "--repository", "symbi/liuyao-learning-app"]
        )
        assert result.exit_code == 0, result.stdout
        assert "3 references" in result.stdout

    def _build_repo(self, tmp_path: Path, case_references: list[dict]) -> None:
        repo = tmp_path / "repo"
        self._write(
            repo / "docs/lessons/lesson-19-notes-v0.1.md",
            "# Lesson 19\n\n## 3. Section Three\n\nPrimary paragraph for case two.\n\n"
            "## 7. Section Seven\n\nPrimary paragraph for case three.\n\n"
            "## 10. Section Ten\n\nSummary paragraph.\n",
        )
        cases = repo / "materials/class-cases/lesson-19"
        for case_id, stem in (
            ("L19-C02-synthetic", "case-002"),
            ("L19-C03-synthetic", "case-003"),
        ):
            self._write(
                cases / f"{stem}.json",
                json.dumps(
                    {
                        "recordType": "class-case",
                        "id": case_id,
                        "lessonId": "lesson-19",
                        "matchStatus": "verified",
                    }
                ),
            )
            self._write(cases / f"{stem}-analysis.md", f"# {case_id}\n\nPaired body.\n")
        config = {
            "curated_notes": {"root": str(repo)},
            "class_cases": {"root": str(repo)},
            "case_references": case_references,
        }
        (tmp_path / "sources.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    def test_dry_run_with_unknown_configured_case_fails(self, tmp_path: Path) -> None:
        self._build_repo(
            tmp_path,
            [
                {
                    "case_id": "L19-C99-absent",
                    "notes_path": "docs/lessons/lesson-19-notes-v0.1.md",
                    "sections": [{"heading_prefix": "7. ", "role": "primary"}],
                }
            ],
        )
        result = runner.invoke(
            app, ["ingest", "run", "--dry-run", "--repository", "symbi/liuyao-learning-app"]
        )
        assert result.exit_code == 1
        assert "L19-C99-absent" in result.stdout

    def test_dry_run_with_unmatched_prefix_fails(self, tmp_path: Path) -> None:
        self._build_repo(
            tmp_path,
            [
                {
                    "case_id": "L19-C02-synthetic",
                    "notes_path": "docs/lessons/lesson-19-notes-v0.1.md",
                    "sections": [{"heading_prefix": "99. ", "role": "primary"}],
                }
            ],
        )
        result = runner.invoke(
            app, ["ingest", "run", "--dry-run", "--repository", "symbi/liuyao-learning-app"]
        )
        assert result.exit_code == 1
        assert "99. " in result.stdout
        assert "matched no chunk" in " ".join(result.stdout.split())

    def test_write_with_missing_link_endpoint_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from contextlib import contextmanager
        from typing import Any

        import liuyao_kb.cli as cli_module
        import liuyao_kb.ingest as ingest_module
        from fake_neo4j import FakeSession
        from liuyao_kb.ingest import IngestPlan

        (tmp_path / "sources.yaml").write_text(
            yaml.safe_dump({"curated_notes": {"enabled": True}}), encoding="utf-8"
        )
        plan = IngestPlan(record_links=(("L19-C02-synthetic", "missing-record-id"),))
        monkeypatch.setattr(ingest_module, "collect_plan", lambda sources, repository: plan)

        @contextmanager
        def fake_session() -> Any:
            yield FakeSession()

        monkeypatch.setattr(cli_module, "_schema_session", fake_session)
        result = runner.invoke(
            app,
            ["ingest", "run", "--no-dry-run", "--repository", "symbi/liuyao-learning-app"],
        )
        assert result.exit_code == 1
        assert "based_on_record" in result.stdout
        assert "Failed:" in result.stdout
