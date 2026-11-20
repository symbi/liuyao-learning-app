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

    def test_write_is_refused_in_m1(self, tmp_path: Path) -> None:
        (tmp_path / "sources.yaml").write_text(
            yaml.safe_dump({"curated_notes": {"enabled": True}}), encoding="utf-8"
        )
        result = runner.invoke(app, ["ingest", "run", "--no-dry-run"])
        assert result.exit_code == 1
        assert "not implemented until M4" in result.stdout

    def test_missing_config_is_reported(self) -> None:
        result = runner.invoke(app, ["ingest", "run", "--dry-run"])
        assert result.exit_code == 1
        assert "No sources config found" in result.stdout
