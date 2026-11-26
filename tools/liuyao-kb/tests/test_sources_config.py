"""Tests for the source allowlist configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from liuyao_kb.sources.config import (
    CaseReferenceSection,
    CaseReferenceSettings,
    SourcesConfig,
    find_sources_config,
    load_sources_config,
)


def write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


class TestCaseReferencesValidation:
    """Explicit REFERENCES configuration never silently overrides
    or duplicates itself."""

    def _entry(self, case_id: str) -> CaseReferenceSettings:
        return CaseReferenceSettings(
            case_id=case_id,
            notes_path="docs/lessons/lesson-19-notes-v0.1.md",
            sections=[CaseReferenceSection(heading_prefix="7. ", role="primary")],
        )

    def test_duplicate_case_id_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="configured more than once"):
            SourcesConfig(case_references=[self._entry("L19-C02-x"), self._entry("L19-C02-x")])

    def test_duplicate_case_id_in_yaml_is_rejected(self, tmp_path: Path) -> None:
        entry = {
            "case_id": "L19-C02-x",
            "notes_path": "docs/lessons/lesson-19-notes-v0.1.md",
            "sections": [{"heading_prefix": "7. ", "role": "primary"}],
        }
        path = write_yaml(tmp_path / "sources.yaml", {"case_references": [entry, entry]})
        with pytest.raises(ValidationError, match="configured more than once"):
            load_sources_config(path)

    def test_duplicate_prefix_in_one_entry_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="listed more than once"):
            CaseReferenceSettings(
                case_id="L19-C02-x",
                notes_path="docs/lessons/lesson-19-notes-v0.1.md",
                sections=[
                    CaseReferenceSection(heading_prefix="7. ", role="primary"),
                    CaseReferenceSection(heading_prefix="7. ", role="secondary"),
                ],
            )


class TestDefaults:
    def test_unsafe_sources_are_off_by_default(self) -> None:
        sources = SourcesConfig()
        assert sources.raw_asr.enabled is False
        assert sources.raw_asr.index_content is False
        assert sources.raw_asr.allow_model_processing is False
        assert sources.daily_records.include is False
        assert sources.pdf.enabled is False
        assert sources.pdf.allow_model_processing is False
        assert sources.external_projects == []

    def test_curated_notes_are_enabled_by_default(self) -> None:
        sources = SourcesConfig()
        assert sources.curated_notes.enabled is True
        assert sources.class_cases.enabled is True

    def test_summary_lists_every_source_type(self) -> None:
        rows = SourcesConfig().summary()
        names = {row["source"] for row in rows}
        assert names == {
            "curated_lesson_note",
            "classroom_case",
            "raw_asr",
            "daily_casting",
            "pdf_reference",
            "external_project_doc",
            "case_references",
        }

    def test_summary_marks_raw_asr_as_low_confidence(self) -> None:
        rows = SourcesConfig().summary()
        raw = next(r for r in rows if r["source"] == "raw_asr")
        assert raw["trust"] == "low_confidence"
        assert raw["enabled"] is False


class TestLoading:
    def test_loads_a_minimal_file(self, tmp_path: Path) -> None:
        path = write_yaml(tmp_path / "sources.yaml", {"curated_notes": {"enabled": True}})
        sources = load_sources_config(path)
        assert sources.curated_notes.enabled is True

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_sources_config(tmp_path / "nope.yaml")

    def test_unknown_key_is_rejected(self, tmp_path: Path) -> None:
        path = write_yaml(tmp_path / "sources.yaml", {"raw_asr": {"typo_key": True}})
        with pytest.raises(ValidationError):
            load_sources_config(path)

    def test_non_mapping_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "sources.yaml"
        path.write_text("- just\n- a list\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_sources_config(path)


class TestDiscovery:
    def test_finds_an_explicit_path(self, tmp_path: Path) -> None:
        path = write_yaml(tmp_path / "sources.yaml", {})
        assert find_sources_config(path) == path

    def test_returns_none_when_absent(self, tmp_path: Path) -> None:
        import os

        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert find_sources_config(None) is None
        finally:
            os.chdir(cwd)
