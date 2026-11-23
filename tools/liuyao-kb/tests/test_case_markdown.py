"""Synthetic-fixture tests for the M2-C3 classroom-case Markdown mapper.

No real classroom-case content is used; every JSON and Markdown payload
below is invented for these tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from liuyao_kb.sources import (
    CaseMappingError,
    ClassCaseMarkdownError,
    EmptySourceError,
    InvalidSourceEncodingError,
    attach_paired_markdown,
    map_class_case_file,
    map_class_case_markdown_file,
    map_class_case_markdown_for_case_file,
    parse_class_case_bytes,
    parse_class_case_markdown_bytes,
)
from liuyao_kb.sources.models import sha256_bytes

REPO = "symbi/liuyao-learning-app"
CASE_ID = "L99-C01-synthetic-case"
JSON_RELATIVE = "materials/class-cases/lesson-99/case-001.json"
MD_RELATIVE = "materials/class-cases/lesson-99/case-001-analysis.md"
MD_URI = f"repo://{REPO}/{MD_RELATIVE}"

MD_TEXT = """# Synthetic Case Analysis

## 老师分析

teacher synthetic text with a [reference link](https://example.invalid/ref)

## 用户 Memo

user memo synthetic text

## AI 计算

ai calculation synthetic text

## 待核实

pending verification synthetic text
"""


def _case_json(case_id: str = CASE_ID, daily_record: dict[str, Any] | None = None) -> bytes:
    payload: dict[str, Any] = {
        "recordType": "class-case",
        "id": case_id,
        "lessonId": "lesson-99",
        "question": "synthetic question only in json",
        "matchStatus": "verified",
    }
    if daily_record is not None:
        payload["dailyRecord"] = daily_record
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _write(root: Path, relative: str, payload: bytes) -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def _write_case(
    root: Path,
    *,
    case_id: str = CASE_ID,
    json_relative: str = JSON_RELATIVE,
    md_text: str | None = MD_TEXT,
    daily_record: dict[str, Any] | None = None,
) -> None:
    _write(root, json_relative, _case_json(case_id, daily_record))
    if md_text is not None:
        md_relative = json_relative.removesuffix(".json") + "-analysis.md"
        _write(root, md_relative, md_text.encode("utf-8"))


class TestHappyPath:
    def test_map_for_case_file(self, tmp_path: Path) -> None:
        _write_case(tmp_path)
        case, md = map_class_case_markdown_for_case_file(
            JSON_RELATIVE, repository=REPO, source_root=tmp_path
        )
        assert md.case_id == case.case_id == CASE_ID
        assert md.source_uri == MD_URI
        assert md.source_identity == f"markdown:{MD_URI}"
        assert md.content_hash == sha256_bytes(MD_TEXT.encode("utf-8"))
        assert md.class_case_source_identity == case.source_identity
        link = md.has_representation
        assert link.relation == "HAS_REPRESENTATION"
        assert link.format == "markdown"
        assert link.case_id == CASE_ID
        assert link.markdown_source_identity == md.source_identity
        assert link.class_case_source_identity == case.source_identity

    def test_sections_headings_and_offsets_preserved(self, tmp_path: Path) -> None:
        _write_case(tmp_path)
        _, md = map_class_case_markdown_for_case_file(
            JSON_RELATIVE, repository=REPO, source_root=tmp_path
        )
        headings = {
            section.locator.heading
            for section in md.document.sections
            if section.locator.heading is not None
        }
        # Teacher, user memo and AI content stay under their own headings:
        assert {"老师分析", "用户 Memo", "AI 计算", "待核实"} <= headings
        for section in md.document.sections:
            locator = section.locator
            assert MD_TEXT[locator.start_offset : locator.end_offset] == section.text
        full_text = "\n".join(section.text for section in md.document.sections)
        # Links are preserved as text (and never fetched):
        assert "https://example.invalid/ref" in full_text

    def test_parse_bytes_with_revision_ref(self, tmp_path: Path) -> None:
        _write_case(tmp_path)
        case = map_class_case_file(JSON_RELATIVE, repository=REPO, source_root=tmp_path)
        md = parse_class_case_markdown_bytes(
            MD_TEXT.encode("utf-8"), class_case=case, revision_ref="rev-synthetic-1"
        )
        assert md.document.revision_ref == "rev-synthetic-1"
        assert md.case_id == CASE_ID

    def test_different_content_is_not_merged(self, tmp_path: Path) -> None:
        _write_case(tmp_path)
        case, md = map_class_case_markdown_for_case_file(
            JSON_RELATIVE, repository=REPO, source_root=tmp_path
        )
        md_text = "\n".join(section.text for section in md.document.sections)
        assert "teacher synthetic text" in md_text
        assert "synthetic question only in json" not in md_text
        assert case.raw["question"] == "synthetic question only in json"

    def test_repeat_mapping_is_idempotent(self, tmp_path: Path) -> None:
        _write_case(tmp_path)
        first = map_class_case_markdown_for_case_file(
            JSON_RELATIVE, repository=REPO, source_root=tmp_path
        )
        second = map_class_case_markdown_for_case_file(
            JSON_RELATIVE, repository=REPO, source_root=tmp_path
        )
        assert first == second
        assert first[1].has_representation == second[1].has_representation


class TestTypeABoundary:
    def test_daily_record_markdown_path_is_never_read(self, tmp_path: Path) -> None:
        type_b_relative = "daily-records/2026/11/markdown/2026-11-21--synthetic.md"
        daily_record = {
            "jsonPath": "daily-records/2026/11/2026-11-21.json",
            "markdownPath": type_b_relative,
            "recordId": "synthetic-record-id",
        }
        _write_case(tmp_path, daily_record=daily_record)
        _write(tmp_path, type_b_relative, b"# TYPE-B MARKER\n")
        _, md = map_class_case_markdown_for_case_file(
            JSON_RELATIVE, repository=REPO, source_root=tmp_path
        )
        md_text = "\n".join(section.text for section in md.document.sections)
        assert md.source_uri == MD_URI  # the type-A paired file
        assert "TYPE-B MARKER" not in md_text
        assert "teacher synthetic text" in md_text

    def test_same_filename_in_two_lessons_stays_distinct(self, tmp_path: Path) -> None:
        _write_case(
            tmp_path,
            case_id="L19-SYNTHETIC",
            json_relative="materials/class-cases/lesson-19/case-001.json",
            md_text="# Lesson 19 synthetic\n",
        )
        _write_case(
            tmp_path,
            case_id="L20-SYNTHETIC",
            json_relative="materials/class-cases/lesson-20/case-001.json",
            md_text="# Lesson 20 synthetic\n",
        )
        _, md19 = map_class_case_markdown_for_case_file(
            "materials/class-cases/lesson-19/case-001.json",
            repository=REPO,
            source_root=tmp_path,
        )
        _, md20 = map_class_case_markdown_for_case_file(
            "materials/class-cases/lesson-20/case-001.json",
            repository=REPO,
            source_root=tmp_path,
        )
        assert md19.case_id == "L19-SYNTHETIC"
        assert md20.case_id == "L20-SYNTHETIC"
        assert md19.source_identity != md20.source_identity
        assert "lesson-19" in md19.source_uri
        assert "lesson-20" in md20.source_uri


class TestFailureModes:
    def test_missing_paired_markdown_errors_and_case_survives(self, tmp_path: Path) -> None:
        _write_case(tmp_path, md_text=None)
        case = map_class_case_file(JSON_RELATIVE, repository=REPO, source_root=tmp_path)
        assert case.paired_markdown is not None
        assert case.paired_markdown.exists is False
        with pytest.raises(ClassCaseMarkdownError, match="missing"):
            map_class_case_markdown_file(case, source_root=tmp_path)
        # The ClassCase mapping itself is untouched:
        assert case.case_id == CASE_ID
        assert case.paired_markdown.relative_path == MD_RELATIVE

    def test_no_paired_reference_is_an_error(self) -> None:
        case = parse_class_case_bytes(_case_json(), source_uri=f"repo://{REPO}/{JSON_RELATIVE}")
        assert case.paired_markdown is None
        with pytest.raises(ClassCaseMarkdownError, match="no paired Markdown reference"):
            parse_class_case_markdown_bytes(MD_TEXT.encode("utf-8"), class_case=case)

    def test_unverified_existence_is_an_error(self, tmp_path: Path) -> None:
        _write_case(tmp_path)
        case = parse_class_case_bytes(_case_json(), source_uri=f"repo://{REPO}/{JSON_RELATIVE}")
        case = attach_paired_markdown(case, repository=REPO, case_json_relative_path=JSON_RELATIVE)
        assert case.paired_markdown is not None
        assert case.paired_markdown.exists is None
        with pytest.raises(ClassCaseMarkdownError, match="has not been verified"):
            map_class_case_markdown_file(case, source_root=tmp_path)

    def test_invalid_utf8_fails(self, tmp_path: Path) -> None:
        _write_case(tmp_path, md_text=None)
        _write(tmp_path, MD_RELATIVE, b"\xff\xfe not utf-8")
        case = map_class_case_file(JSON_RELATIVE, repository=REPO, source_root=tmp_path)
        with pytest.raises(InvalidSourceEncodingError):
            map_class_case_markdown_file(case, source_root=tmp_path)

    def test_empty_markdown_fails(self, tmp_path: Path) -> None:
        _write_case(tmp_path, md_text=None)
        _write(tmp_path, MD_RELATIVE, b"")
        case = map_class_case_file(JSON_RELATIVE, repository=REPO, source_root=tmp_path)
        with pytest.raises(EmptySourceError):
            map_class_case_markdown_file(case, source_root=tmp_path)

    def test_path_escape_fails(self, tmp_path: Path) -> None:
        _write_case(tmp_path)
        case = map_class_case_file(JSON_RELATIVE, repository=REPO, source_root=tmp_path)
        assert case.paired_markdown is not None
        escaped = case.paired_markdown.model_copy(
            update={"relative_path": "../outside-analysis.md", "exists": True}
        )
        case = case.model_copy(update={"paired_markdown": escaped})
        with pytest.raises(CaseMappingError):
            map_class_case_markdown_file(case, source_root=tmp_path)

    def test_symlink_escape_is_reported_missing(self, tmp_path: Path) -> None:
        _write_case(tmp_path, md_text=None)
        outside = tmp_path.parent / "outside-analysis.md"
        outside.write_text("# outside\n", encoding="utf-8")
        (tmp_path / MD_RELATIVE).symlink_to(outside)
        case = map_class_case_file(JSON_RELATIVE, repository=REPO, source_root=tmp_path)
        assert case.paired_markdown is not None
        assert case.paired_markdown.exists is False
        with pytest.raises(ClassCaseMarkdownError, match="missing"):
            map_class_case_markdown_file(case, source_root=tmp_path)

    def test_parse_bytes_rejects_missing_paired(self, tmp_path: Path) -> None:
        _write_case(tmp_path, md_text=None)
        case = map_class_case_file(JSON_RELATIVE, repository=REPO, source_root=tmp_path)
        assert case.paired_markdown is not None
        assert case.paired_markdown.exists is False
        with pytest.raises(ClassCaseMarkdownError, match="missing"):
            parse_class_case_markdown_bytes(MD_TEXT.encode("utf-8"), class_case=case)

    def test_parse_bytes_rejects_unverified_paired(self) -> None:
        case = parse_class_case_bytes(_case_json(), source_uri=f"repo://{REPO}/{JSON_RELATIVE}")
        case = attach_paired_markdown(case, repository=REPO, case_json_relative_path=JSON_RELATIVE)
        assert case.paired_markdown is not None
        assert case.paired_markdown.exists is None
        with pytest.raises(ClassCaseMarkdownError, match="has not been verified"):
            parse_class_case_markdown_bytes(MD_TEXT.encode("utf-8"), class_case=case)
