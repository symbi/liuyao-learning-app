"""Synthetic-fixture tests for the M2-C2 generated-Markdown mapper.

No real daily records or personal memos are used; every Markdown and
JSON payload below is invented for these tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from liuyao_kb.sources import (
    DailyRecordMappingResult,
    DailyRecordsSettings,
    GeneratedMarkdownError,
    map_generated_markdown_file,
    parse_daily_container_bytes,
    parse_generated_markdown_bytes,
    record_id_from_filename,
    verify_against_container,
)
from liuyao_kb.sources.models import sha256_bytes

RECORD_ID = "11111111-2222-3333-4444-555555555555"
OTHER_ID = "99999999-8888-7777-6666-555555555555"
MD_RELATIVE = f"daily-records/2026/11/markdown/2026-11-21--{RECORD_ID}.md"
MD_URI = f"repo://symbi/liuyao-learning-app/{MD_RELATIVE}"
CONTAINER_RELATIVE = "daily-records/2026/11/2026-11-21.json"
CONTAINER_URI = f"repo://symbi/liuyao-learning-app/{CONTAINER_RELATIVE}"


def _markdown(
    embedded_id: str | None = RECORD_ID,
    *,
    embedded_json: str | None = None,
    include_raw_section: bool = True,
    extra_raw_section: bool = False,
    memo: str = "synthetic memo body",
) -> bytes:
    parts = [
        "# Synthetic Daily Record",
        "",
        "## Teacher Memo",
        "",
        memo,
        "",
        "## Conclusion",
        "",
        "synthetic conclusion body",
        "",
    ]
    if include_raw_section:
        payload = embedded_json
        if payload is None:
            record: dict[str, Any] = {"schemaVersion": 99, "savedAt": "2026-01-01T00:00:00Z"}
            if embedded_id is not None:
                record["id"] = embedded_id
            payload = json.dumps(record, indent=2)
        parts += ["## 原始记录 JSON", "", "```json", payload, "```", ""]
    if extra_raw_section:
        parts += [
            "## 原始记录 JSON",
            "",
            "```json",
            json.dumps({"id": embedded_id or RECORD_ID}),
            "```",
            "",
        ]
    return "\n".join(parts).encode("utf-8")


def _container_bytes(record_id: str = RECORD_ID) -> bytes:
    container = {
        "date": "2026-11-21",
        "additionalQuestions": [
            {"id": record_id, "isCase": True, "caseSource": "classroom", "question": "synthetic"}
        ],
    }
    return json.dumps(container).encode("utf-8")


def _container_result(record_id: str = RECORD_ID) -> DailyRecordMappingResult:
    return parse_daily_container_bytes(
        _container_bytes(record_id),
        source_uri=CONTAINER_URI,
        allowed_record_ids={record_id},
    )


class TestFilenameIds:
    def test_generated_name(self) -> None:
        assert record_id_from_filename(f"2026-11-21--{RECORD_ID}.md") == RECORD_ID
        assert record_id_from_filename(MD_RELATIVE) == RECORD_ID

    def test_unverifiable_names(self) -> None:
        assert record_id_from_filename("2026-11-21.md") is None
        assert record_id_from_filename("2026-11-21--.md") is None
        assert record_id_from_filename(f"2026-11-21--{RECORD_ID}.txt") is None


class TestParseGeneratedMarkdown:
    def test_happy_path_identity_and_body(self) -> None:
        data = _markdown()
        mapping = parse_generated_markdown_bytes(data, source_uri=MD_URI)
        assert mapping.record_id == RECORD_ID
        assert mapping.filename_record_id == RECORD_ID
        assert mapping.embedded_record_id == RECORD_ID
        assert mapping.source_identity == f"markdown:{MD_URI}"
        assert mapping.content_hash == sha256_bytes(data)
        assert mapping.embedded_raw_record.raw["schemaVersion"] == 99
        assert mapping.renders.relation == "RENDERS"
        assert mapping.renders.record_id == RECORD_ID
        assert mapping.renders.container_verified is False

    def test_body_excludes_raw_record_section(self) -> None:
        data = _markdown()
        mapping = parse_generated_markdown_bytes(data, source_uri=MD_URI)
        body_text = "\n".join(section.text for section in mapping.body_sections)
        assert "synthetic memo body" in body_text
        assert "synthetic conclusion body" in body_text
        assert "原始记录 JSON" not in body_text
        assert "schemaVersion" not in body_text
        assert len(mapping.body_sections) < len(mapping.document.sections)

    def test_body_locators_point_into_original_text(self) -> None:
        data = _markdown()
        text = data.decode("utf-8")
        mapping = parse_generated_markdown_bytes(data, source_uri=MD_URI)
        for section in mapping.body_sections:
            locator = section.locator
            assert text[locator.start_offset : locator.end_offset] == section.text
        span = mapping.embedded_raw_record
        assert text[span.section_start_offset :].startswith("## 原始记录 JSON")

    def test_filename_embedded_mismatch_is_an_error(self) -> None:
        with pytest.raises(GeneratedMarkdownError, match="mismatch"):
            parse_generated_markdown_bytes(_markdown(embedded_id=OTHER_ID), source_uri=MD_URI)

    def test_missing_raw_section_is_an_error(self) -> None:
        with pytest.raises(GeneratedMarkdownError, match="Missing"):
            parse_generated_markdown_bytes(_markdown(include_raw_section=False), source_uri=MD_URI)

    def test_malformed_embedded_json_is_an_error(self) -> None:
        with pytest.raises(GeneratedMarkdownError, match="not valid JSON"):
            parse_generated_markdown_bytes(_markdown(embedded_json="{not json"), source_uri=MD_URI)

    def test_embedded_id_missing_is_an_error(self) -> None:
        with pytest.raises(GeneratedMarkdownError, match="no non-empty string 'id'"):
            parse_generated_markdown_bytes(_markdown(embedded_id=None), source_uri=MD_URI)

    def test_duplicate_raw_sections_are_an_error(self) -> None:
        with pytest.raises(GeneratedMarkdownError, match="Duplicate"):
            parse_generated_markdown_bytes(_markdown(extra_raw_section=True), source_uri=MD_URI)

    def test_filename_without_record_id_is_an_error(self) -> None:
        uri = "repo://symbi/liuyao-learning-app/daily-records/2026/11/markdown/2026-11-21.md"
        with pytest.raises(GeneratedMarkdownError, match="does not carry a record id"):
            parse_generated_markdown_bytes(_markdown(), source_uri=uri)

    def test_heading_inside_fence_is_not_the_raw_section(self) -> None:
        fenced = (
            "# Synthetic\n\n```markdown\n## 原始记录 JSON\nnot the real section\n```\n\n"
        ).encode() + _markdown().split(b"\n", 1)[1]
        mapping = parse_generated_markdown_bytes(fenced, source_uri=MD_URI)
        assert mapping.record_id == RECORD_ID


class TestContainerVerification:
    def test_verify_links_renders_to_existing_cast_record(self) -> None:
        mapping = parse_generated_markdown_bytes(_markdown(), source_uri=MD_URI)
        container = _container_result()
        verified = verify_against_container(mapping, container)
        assert verified.renders.container_verified is True
        assert verified.renders.container_source_uri == CONTAINER_URI
        assert verified.renders.container_source_identity == container.source_identity
        assert verified.renders.record_id == RECORD_ID
        # The original mapping is unchanged and no record was created:
        # verification is idempotent and the container still holds exactly
        # the one CastRecord M2-C1 mapped.
        assert mapping.renders.container_verified is False
        assert verify_against_container(verified, container) == verified
        assert len(container.records) == 1

    def test_record_absent_from_container_is_an_error(self) -> None:
        mapping = parse_generated_markdown_bytes(_markdown(), source_uri=MD_URI)
        with pytest.raises(GeneratedMarkdownError, match="not among"):
            verify_against_container(mapping, _container_result(OTHER_ID))

    def test_unprocessed_container_is_an_error(self) -> None:
        mapping = parse_generated_markdown_bytes(_markdown(), source_uri=MD_URI)
        with pytest.raises(GeneratedMarkdownError, match="not processed"):
            verify_against_container(mapping, DailyRecordMappingResult(processed=False))


class TestFileLevel:
    def _write(self, root: Path, relative: str, payload: bytes) -> Path:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return target

    def test_map_file_with_container_verification(self, tmp_path: Path) -> None:
        self._write(tmp_path, MD_RELATIVE, _markdown())
        self._write(tmp_path, CONTAINER_RELATIVE, _container_bytes())
        settings = DailyRecordsSettings(
            include=True,
            allowed_records=[{"path": CONTAINER_RELATIVE, "record_id": RECORD_ID}],
        )
        mapping = map_generated_markdown_file(
            MD_RELATIVE,
            repository="symbi/liuyao-learning-app",
            source_root=tmp_path,
            container_path=CONTAINER_RELATIVE,
            settings=settings,
        )
        assert mapping.source_uri == MD_URI
        assert mapping.record_id == RECORD_ID
        assert mapping.renders.container_verified is True

    def test_map_file_without_container_stays_unverified(self, tmp_path: Path) -> None:
        self._write(tmp_path, MD_RELATIVE, _markdown())
        mapping = map_generated_markdown_file(
            MD_RELATIVE, repository="symbi/liuyao-learning-app", source_root=tmp_path
        )
        assert mapping.renders.container_verified is False

    def test_container_with_default_settings_cannot_verify(self, tmp_path: Path) -> None:
        self._write(tmp_path, MD_RELATIVE, _markdown())
        self._write(tmp_path, CONTAINER_RELATIVE, _container_bytes())
        with pytest.raises(GeneratedMarkdownError, match="not processed"):
            map_generated_markdown_file(
                MD_RELATIVE,
                repository="symbi/liuyao-learning-app",
                source_root=tmp_path,
                container_path=CONTAINER_RELATIVE,
            )


class TestSameNameHeadingsKept:
    def test_h1_h3_with_raw_heading_text_are_body(self) -> None:
        text = (
            "# 原始记录 JSON\n"
            "\n"
            "intro under the h1 heading\n"
            "\n"
            "### 原始记录 JSON\n"
            "\n"
            "body under the h3 heading\n"
            "\n"
            "## 原始记录 JSON\n"
            "\n"
            "```json\n" + json.dumps({"id": RECORD_ID, "schemaVersion": 99}) + "\n```\n"
        )
        mapping = parse_generated_markdown_bytes(text.encode(), source_uri=MD_URI)
        body_text = "\n".join(section.text for section in mapping.body_sections)
        # Ordinary H1/H3 sections with the same heading text are body:
        assert "intro under the h1 heading" in body_text
        assert "body under the h3 heading" in body_text
        assert body_text.count("原始记录 JSON") == 2  # the H1 and H3 heading lines
        # Only the identified H2 raw-record section is excluded:
        assert "schemaVersion" not in body_text
        excluded = [
            section for section in mapping.document.sections if section not in mapping.body_sections
        ]
        assert excluded
        for section in excluded:
            assert (
                mapping.embedded_raw_record.section_start_offset
                <= section.locator.start_offset
                < mapping.embedded_raw_record.section_end_offset
            )


class TestFenceRulesMatchMarkdownAdapter:
    def test_invalid_backtick_fence_before_section_does_not_hide_it(self) -> None:
        # A backtick fence whose info string contains a backtick is not
        # an opening fence for MarkdownAdapter; it must not swallow the
        # real raw-record heading either.
        text = (
            "# Synthetic Daily Record\n"
            "\n"
            "```not`a`fence\n"
            "\n"
            "## 原始记录 JSON\n"
            "\n"
            "```json\n" + json.dumps({"id": RECORD_ID, "schemaVersion": 99}) + "\n```\n"
        )
        mapping = parse_generated_markdown_bytes(text.encode(), source_uri=MD_URI)
        assert mapping.record_id == RECORD_ID

    def test_invalid_fence_inside_section_is_skipped_for_real_json(self) -> None:
        text = (
            "# Synthetic Daily Record\n"
            "\n"
            "## 原始记录 JSON\n"
            "\n"
            "```json`with`backticks\n"
            "\n"
            "```json\n" + json.dumps({"id": RECORD_ID, "schemaVersion": 99}) + "\n```\n"
        )
        mapping = parse_generated_markdown_bytes(text.encode(), source_uri=MD_URI)
        assert mapping.record_id == RECORD_ID
        assert mapping.embedded_raw_record.raw["schemaVersion"] == 99

    def test_unicode_line_separator_does_not_start_a_fence(self) -> None:
        # U+2028 is a line boundary for str.splitlines() but not for
        # MarkdownAdapter, which splits physical lines on "\n" only.
        # The fence-shaped text after U+2028 is mid-line body text for
        # both parsers, so the real raw-record section is still found.
        text = (
            "# Synthetic Daily Record\n"
            "\n"
            "body text\u2028```json\n"
            "\n"
            "## 原始记录 JSON\n"
            "\n"
            "```json\n" + json.dumps({"id": RECORD_ID, "schemaVersion": 99}) + "\n```\n"
        )
        mapping = parse_generated_markdown_bytes(text.encode(), source_uri=MD_URI)
        assert mapping.record_id == RECORD_ID
        body_text = "\n".join(section.text for section in mapping.body_sections)
        assert "body text" in body_text
