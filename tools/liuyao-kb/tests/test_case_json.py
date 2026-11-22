"""Tests for the M2-C1 case/daily-record JSON mapping layer.

All fixtures are synthetic. No real classroom case, daily record or
private material is copied into this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from liuyao_kb.sources import (
    AllowlistError,
    DailyRecordsSettings,
    InvalidCaseJsonError,
    MatchStatus,
    SourcesConfig,
    link_daily_records,
    map_class_case_file,
    map_daily_records_file,
    parse_class_case_bytes,
    parse_daily_container_bytes,
)
from liuyao_kb.sources.models import sha256_bytes

CASE_URI = "repo://symbi/liuyao-learning-app/materials/class-cases/lesson-99/case-001.json"
DAILY_URI = "repo://symbi/liuyao-learning-app/daily-records/2099/01/2099-01-01.json"


def _bytes(document: Any) -> bytes:
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def _minimal_case(**overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "recordType": "class-case",
        "id": "L99-C01-synthetic",
        "lessonId": "lesson-99",
        "matchStatus": "verified",
    }
    document.update(overrides)
    return document


def _container(*subrecords: dict[str, Any], **extra: Any) -> dict[str, Any]:
    document: dict[str, Any] = {"additionalQuestions": list(subrecords)}
    document.update(extra)
    return document


def _subrecord(record_id: str, **overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": record_id,
        "recordType": "additionalQuestion",
        "isCase": False,
        "question": {"category": "synthetic"},
    }
    record.update(overrides)
    return record


class TestClassCaseMapping:
    def test_minimal_valid_case(self) -> None:
        data = _bytes(_minimal_case())
        mapping = parse_class_case_bytes(data, source_uri=CASE_URI)
        assert mapping.case_id == "L99-C01-synthetic"
        assert mapping.lesson_id == "lesson-99"
        assert mapping.match_status is MatchStatus.VERIFIED
        assert mapping.match_status_raw == "verified"
        assert mapping.match_status_needs_review is False
        assert mapping.content_hash == sha256_bytes(data)
        assert mapping.locator.record_id == "L99-C01-synthetic"
        assert mapping.locator.json_pointer == ""
        assert mapping.daily_record is None
        assert mapping.linked_record_id is None

    def test_case001_style_daily_record_path(self) -> None:
        # Historical shape A: dailyRecord carries "path" only.
        mapping = parse_class_case_bytes(
            _bytes(
                _minimal_case(
                    dailyRecord={
                        "path": "daily-records/2099/01/2099-01-01.json",
                        "recordId": "rec-a",
                    }
                )
            ),
            source_uri=CASE_URI,
        )
        assert mapping.daily_record is not None
        assert mapping.daily_record.record_id == "rec-a"
        assert mapping.daily_record.json_path == "daily-records/2099/01/2099-01-01.json"
        assert mapping.daily_record.markdown_path is None

    def test_case002_style_daily_record_json_path(self) -> None:
        # Historical shape B: dailyRecord carries "jsonPath"/"markdownPath".
        mapping = parse_class_case_bytes(
            _bytes(
                _minimal_case(
                    dailyRecord={
                        "jsonPath": "daily-records/2099/01/2099-01-01.json",
                        "markdownPath": "daily-records/2099/01/markdown/x.md",
                        "recordId": "rec-b",
                        "savedAt": "2099-01-01T00:00:00Z",
                    }
                )
            ),
            source_uri=CASE_URI,
        )
        assert mapping.daily_record is not None
        assert mapping.daily_record.json_path == "daily-records/2099/01/2099-01-01.json"
        assert mapping.daily_record.markdown_path == "daily-records/2099/01/markdown/x.md"
        # The complete original block survives, including extra keys.
        assert mapping.daily_record.raw["savedAt"] == "2099-01-01T00:00:00Z"

    def test_conflicting_path_aliases_are_an_error(self) -> None:
        with pytest.raises(InvalidCaseJsonError, match="Conflicting dailyRecord path aliases"):
            parse_class_case_bytes(
                _bytes(
                    _minimal_case(
                        dailyRecord={"path": "a.json", "jsonPath": "b.json", "recordId": "r"}
                    )
                ),
                source_uri=CASE_URI,
            )

    def test_differing_casting_shapes_are_preserved_not_rebuilt(self) -> None:
        shape_a = {"casting": {"lines": [{"position": 1, "value": 7}], "method": "coins"}}
        shape_b = {
            "casting": {"lines": "free-form synthetic shape", "hiddenSpirit": None},
            "teacherAnalysis": {"segments": [1, 2]},
        }
        for shape in (shape_a, shape_b):
            mapping = parse_class_case_bytes(_bytes(_minimal_case(**shape)), source_uri=CASE_URI)
            dumped = mapping.model_dump(mode="json")
            assert dumped["raw"]["casting"] == shape["casting"]

    def test_unknown_optional_and_null_fields_preserved(self) -> None:
        document = _minimal_case(
            futureField={"nested": [1, None, "x"]},
            optionalNote=None,
            verificationBasis=["synthetic basis"],
        )
        mapping = parse_class_case_bytes(_bytes(document), source_uri=CASE_URI)
        dumped = mapping.model_dump(mode="json")
        assert dumped["raw"] == document

    def test_wrong_record_type_rejected(self) -> None:
        with pytest.raises(InvalidCaseJsonError, match="recordType"):
            parse_class_case_bytes(
                _bytes(_minimal_case(recordType="additionalQuestion")), source_uri=CASE_URI
            )

    def test_missing_or_blank_id_rejected(self) -> None:
        document = _minimal_case()
        del document["id"]
        with pytest.raises(InvalidCaseJsonError, match="'id'"):
            parse_class_case_bytes(_bytes(document), source_uri=CASE_URI)
        with pytest.raises(InvalidCaseJsonError, match="'id'"):
            parse_class_case_bytes(_bytes(_minimal_case(id="  ")), source_uri=CASE_URI)


class TestMatchStatusNormalization:
    def test_matched_normalizes_to_verified_with_raw_preserved(self) -> None:
        mapping = parse_class_case_bytes(
            _bytes(_minimal_case(matchStatus="matched")), source_uri=CASE_URI
        )
        assert mapping.match_status is MatchStatus.VERIFIED
        assert mapping.match_status_raw == "matched"
        assert mapping.match_status_needs_review is False

    @pytest.mark.parametrize("status", ["needs_review", "not_found", "disputed"])
    def test_other_canonical_statuses_kept(self, status: str) -> None:
        mapping = parse_class_case_bytes(
            _bytes(_minimal_case(matchStatus=status)), source_uri=CASE_URI
        )
        assert mapping.match_status is MatchStatus(status)
        assert mapping.match_status_needs_review is False

    def test_unknown_status_flagged_not_dropped(self) -> None:
        mapping = parse_class_case_bytes(
            _bytes(_minimal_case(matchStatus="confirmed-ish")), source_uri=CASE_URI
        )
        assert mapping.match_status is MatchStatus.UNKNOWN
        assert mapping.match_status_raw == "confirmed-ish"
        assert mapping.match_status_needs_review is True

    def test_missing_status_flagged(self) -> None:
        document = _minimal_case()
        del document["matchStatus"]
        mapping = parse_class_case_bytes(_bytes(document), source_uri=CASE_URI)
        assert mapping.match_status is None
        assert mapping.match_status_raw is None
        assert mapping.match_status_needs_review is True

    def test_non_string_status_flagged(self) -> None:
        mapping = parse_class_case_bytes(_bytes(_minimal_case(matchStatus=3)), source_uri=CASE_URI)
        assert mapping.match_status is MatchStatus.UNKNOWN
        assert mapping.match_status_needs_review is True


class TestDailyContainerMapping:
    def test_only_allowlisted_subrecords_are_mapped(self) -> None:
        data = _bytes(_container(_subrecord("rec-1"), _subrecord("rec-2"), _subrecord("rec-3")))
        result = parse_daily_container_bytes(
            data, source_uri=DAILY_URI, allowed_record_ids={"rec-2"}
        )
        assert [r.record_id for r in result.records] == ["rec-2"]
        assert result.skipped_record_ids == ("rec-1", "rec-3")
        record = result.records[0]
        assert record.locator.json_pointer == "/additionalQuestions/1"
        assert record.locator.record_id == "rec-2"
        assert record.content_hash == sha256_bytes(data)

    def test_case_flags_do_not_promote_to_class_case(self) -> None:
        # A classroom-flagged subrecord still maps to a CastRecord only;
        # the mapping layer never fabricates a ClassCase from flags.
        data = _bytes(_container(_subrecord("rec-9", isCase=True, caseSource="classroom")))
        result = parse_daily_container_bytes(
            data, source_uri=DAILY_URI, allowed_record_ids={"rec-9"}
        )
        assert len(result.records) == 1
        record = result.records[0]
        assert record.is_case is True
        assert record.case_source == "classroom"
        assert record.source_type.value == "daily_record"

    def test_daily_fortune_and_container_are_never_mapped(self) -> None:
        data = _bytes(
            _container(
                _subrecord("rec-1"),
                dailyFortune={"id": "fortune-1"},
                recordType="daily-container",
            )
        )
        result = parse_daily_container_bytes(data, source_uri=DAILY_URI, allowed_record_ids=set())
        assert result.records == ()
        assert result.skipped_record_ids == ("rec-1",)

    def test_allowlisted_id_missing_is_an_explicit_error(self) -> None:
        data = _bytes(_container(_subrecord("rec-1")))
        with pytest.raises(AllowlistError, match="not found"):
            parse_daily_container_bytes(data, source_uri=DAILY_URI, allowed_record_ids={"rec-404"})

    def test_duplicate_subrecord_ids_are_an_explicit_error(self) -> None:
        data = _bytes(_container(_subrecord("rec-1"), _subrecord("rec-1")))
        with pytest.raises(AllowlistError, match="Duplicate subrecord id"):
            parse_daily_container_bytes(data, source_uri=DAILY_URI, allowed_record_ids={"rec-1"})

    def test_subrecord_raw_preserved(self) -> None:
        original = _subrecord("rec-1", caseMemo="synthetic memo", extraUnknown=[True, None])
        result = parse_daily_container_bytes(
            _bytes(_container(original)), source_uri=DAILY_URI, allowed_record_ids={"rec-1"}
        )
        assert result.records[0].model_dump(mode="json")["raw"] == original


class TestLinking:
    def _case(self, record_id: str | None) -> Any:
        daily = {"recordId": record_id, "path": "daily-records/x.json"} if record_id else None
        return parse_class_case_bytes(_bytes(_minimal_case(dailyRecord=daily)), source_uri=CASE_URI)

    def test_exact_record_id_match_links(self) -> None:
        case = self._case("rec-2")
        result = parse_daily_container_bytes(
            _bytes(_container(_subrecord("rec-1"), _subrecord("rec-2"))),
            source_uri=DAILY_URI,
            allowed_record_ids={"rec-1", "rec-2"},
        )
        (linked,) = link_daily_records([case], result.records)
        assert linked.linked_record_id == "rec-2"

    def test_unmatched_reference_is_kept_not_fabricated(self) -> None:
        case = self._case("rec-absent")
        result = parse_daily_container_bytes(
            _bytes(_container(_subrecord("rec-1"))),
            source_uri=DAILY_URI,
            allowed_record_ids={"rec-1"},
        )
        (linked,) = link_daily_records([case], result.records)
        assert linked.linked_record_id is None
        assert linked.daily_record is not None
        assert linked.daily_record.record_id == "rec-absent"

    def test_no_daily_record_block_stays_unlinked(self) -> None:
        case = self._case(None)
        (linked,) = link_daily_records([case], [])
        assert linked.linked_record_id is None


class TestAllowlistSettings:
    def test_defaults_are_fail_closed(self) -> None:
        settings = DailyRecordsSettings()
        assert settings.include is False
        assert settings.allowed_records == []
        assert settings.allowed_ids_for("daily-records/2099/01/2099-01-01.json") == ()

    def test_allowed_ids_for_path(self) -> None:
        settings = DailyRecordsSettings(
            include=True,
            allowed_records=[
                {"path": "daily-records/2099/01/2099-01-01.json", "record_id": "rec-1"},
                {"path": "daily-records/2099/01/2099-01-02.json", "record_id": "rec-2"},
            ],
        )
        assert settings.allowed_ids_for("daily-records/2099/01/2099-01-01.json") == ("rec-1",)

    def test_duplicate_config_entries_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate allowed_records entry"):
            DailyRecordsSettings(
                allowed_records=[
                    {"path": "daily-records/a.json", "record_id": "rec-1"},
                    {"path": "daily-records/a.json", "record_id": "rec-1"},
                ]
            )

    def test_same_id_under_two_paths_rejected(self) -> None:
        with pytest.raises(ValidationError, match="two different paths"):
            DailyRecordsSettings(
                allowed_records=[
                    {"path": "daily-records/a.json", "record_id": "rec-1"},
                    {"path": "daily-records/b.json", "record_id": "rec-1"},
                ]
            )

    @pytest.mark.parametrize("bad_path", ["../outside.json", "/abs/path.json", ""])
    def test_unsafe_allowlist_paths_rejected(self, bad_path: str) -> None:
        with pytest.raises(ValidationError):
            DailyRecordsSettings(allowed_records=[{"path": bad_path, "record_id": "rec-1"}])

    def test_sources_config_round_trip_with_allowlist(self) -> None:
        config = SourcesConfig.model_validate(
            {
                "daily_records": {
                    "include": True,
                    "allowed_records": [{"path": "daily-records/a.json", "record_id": "rec-1"}],
                }
            }
        )
        assert config.daily_records.allowed_ids_for("daily-records/a.json") == ("rec-1",)


class TestFileLevelMapping:
    def _write(self, root: Path, relative: str, document: Any) -> Path:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_bytes(document))
        return target

    def test_map_class_case_file(self, tmp_path: Path) -> None:
        target = self._write(
            tmp_path, "materials/class-cases/lesson-99/case-001.json", _minimal_case()
        )
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=tmp_path
        )
        assert mapping.source_uri == CASE_URI
        assert mapping.source_identity == f"classroom_case:{CASE_URI}"
        assert mapping.case_id == "L99-C01-synthetic"

    def test_include_false_reads_nothing(self, tmp_path: Path) -> None:
        missing = tmp_path / "daily-records" / "2099" / "01" / "2099-01-01.json"
        result = map_daily_records_file(
            missing,
            repository="symbi/liuyao-learning-app",
            source_root=tmp_path,
            settings=DailyRecordsSettings(include=False),
        )
        assert result.processed is False
        assert result.records == ()

    def test_map_daily_records_file_with_allowlist(self, tmp_path: Path) -> None:
        relative = "daily-records/2099/01/2099-01-01.json"
        target = self._write(
            tmp_path, relative, _container(_subrecord("rec-1"), _subrecord("rec-2"))
        )
        settings = DailyRecordsSettings(
            include=True,
            allowed_records=[{"path": relative, "record_id": "rec-2"}],
        )
        result = map_daily_records_file(
            target,
            repository="symbi/liuyao-learning-app",
            source_root=tmp_path,
            settings=settings,
        )
        assert result.processed is True
        assert [r.record_id for r in result.records] == ["rec-2"]
        assert result.skipped_record_ids == ("rec-1",)
        assert result.source_uri == DAILY_URI

    def test_file_outside_root_is_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside-case.json"
        outside.write_bytes(_bytes(_minimal_case()))
        with pytest.raises(AllowlistError, match="outside the allowed repository root"):
            map_class_case_file(
                outside, repository="symbi/liuyao-learning-app", source_root=tmp_path
            )


class TestStrictDecoding:
    def test_invalid_utf8_is_an_error(self) -> None:
        with pytest.raises(InvalidCaseJsonError, match="not valid UTF-8"):
            parse_class_case_bytes(b'{"recordType": "class-case", \xff}', source_uri=CASE_URI)

    def test_malformed_json_is_an_error(self) -> None:
        with pytest.raises(InvalidCaseJsonError, match="Invalid JSON"):
            parse_class_case_bytes(b'{"recordType": ', source_uri=CASE_URI)

    def test_duplicate_object_keys_are_an_error(self) -> None:
        data = b'{"recordType": "class-case", "recordType": "class-case", "id": "x"}'
        with pytest.raises(InvalidCaseJsonError, match="duplicate JSON object key"):
            parse_class_case_bytes(data, source_uri=CASE_URI)

    def test_non_object_top_level_is_an_error(self) -> None:
        with pytest.raises(InvalidCaseJsonError, match="must be an object"):
            parse_daily_container_bytes(b"[1, 2]", source_uri=DAILY_URI, allowed_record_ids=set())


class TestPairedMarkdown:
    """Type-A companion Markdown identification (M2-C1 scope: no parsing)."""

    def _write_case(self, root: Path, relative: str, document: Any) -> Path:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_bytes(document))
        return target

    def test_companion_exists(self, tmp_path: Path) -> None:
        relative = "materials/class-cases/lesson-99/case-001.json"
        target = self._write_case(tmp_path, relative, _minimal_case())
        companion = tmp_path / "materials/class-cases/lesson-99/case-001-analysis.md"
        companion.write_text("# synthetic companion\n", encoding="utf-8")
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=tmp_path
        )
        ref = mapping.paired_markdown
        assert ref is not None
        assert ref.case_id == mapping.case_id
        assert ref.relative_path == "materials/class-cases/lesson-99/case-001-analysis.md"
        assert ref.source_uri == (
            "repo://symbi/liuyao-learning-app/materials/class-cases/lesson-99/case-001-analysis.md"
        )
        assert ref.source_identity == f"markdown:{ref.source_uri}"
        assert ref.exists is True

    def test_companion_missing_keeps_path_and_mapping(self, tmp_path: Path) -> None:
        relative = "materials/class-cases/lesson-99/case-001.json"
        target = self._write_case(tmp_path, relative, _minimal_case())
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=tmp_path
        )
        ref = mapping.paired_markdown
        assert ref is not None
        assert ref.relative_path.endswith("case-001-analysis.md")
        assert ref.exists is False
        assert mapping.case_id == "L99-C01-synthetic"

    def test_same_filename_in_different_lessons_never_confused(self, tmp_path: Path) -> None:
        paths = []
        for lesson in ("lesson-01", "lesson-02"):
            relative = f"materials/class-cases/{lesson}/case-001.json"
            target = self._write_case(tmp_path, relative, _minimal_case())
            mapping = map_class_case_file(
                target, repository="symbi/liuyao-learning-app", source_root=tmp_path
            )
            assert mapping.paired_markdown is not None
            paths.append(mapping.paired_markdown.relative_path)
        assert paths == [
            "materials/class-cases/lesson-01/case-001-analysis.md",
            "materials/class-cases/lesson-02/case-001-analysis.md",
        ]

    def test_daily_record_markdown_path_is_not_the_companion(self, tmp_path: Path) -> None:
        # The dailyRecord.markdownPath target (type B) existing on disk
        # must not make the type-A companion count as present.
        relative = "materials/class-cases/lesson-99/case-001.json"
        document = _minimal_case(
            dailyRecord={
                "recordId": "rec-1",
                "jsonPath": "daily-records/2099/01/2099-01-01.json",
                "markdownPath": "daily-records/2099/01/markdown/rec-1.md",
            }
        )
        target = self._write_case(tmp_path, relative, document)
        b_type = tmp_path / "daily-records/2099/01/markdown/rec-1.md"
        b_type.parent.mkdir(parents=True, exist_ok=True)
        b_type.write_text("# generated daily markdown\n", encoding="utf-8")
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=tmp_path
        )
        assert mapping.daily_record is not None
        assert mapping.daily_record.markdown_path == "daily-records/2099/01/markdown/rec-1.md"
        ref = mapping.paired_markdown
        assert ref is not None
        assert ref.relative_path == "materials/class-cases/lesson-99/case-001-analysis.md"
        assert ref.exists is False

    def test_companion_body_is_never_read(self, tmp_path: Path) -> None:
        relative = "materials/class-cases/lesson-99/case-001.json"
        target = self._write_case(tmp_path, relative, _minimal_case())
        companion = tmp_path / "materials/class-cases/lesson-99/case-001-analysis.md"
        companion.write_bytes(b"\xff\xfe not valid utf-8, not valid markdown \x00")
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=tmp_path
        )
        ref = mapping.paired_markdown
        assert ref is not None
        assert ref.exists is True
        # Identification only: the ref carries no content of any kind.
        assert not hasattr(ref, "raw")
        assert not hasattr(ref, "text")

    def test_unchecked_without_root_is_not_reported_missing(self) -> None:
        from liuyao_kb.sources import resolve_paired_markdown

        ref = resolve_paired_markdown(
            repository="symbi/liuyao-learning-app",
            case_id="L99-C01-synthetic",
            case_json_relative_path="materials/class-cases/lesson-99/case-001.json",
        )
        assert ref.exists is None
        assert ref.relative_path.endswith("case-001-analysis.md")

    def test_bytes_parser_stays_pure_and_leaves_companion_unset(self) -> None:
        mapping = parse_class_case_bytes(_bytes(_minimal_case()), source_uri=CASE_URI)
        assert mapping.paired_markdown is None

    def test_attach_to_bytes_parsed_mapping(self, tmp_path: Path) -> None:
        from liuyao_kb.sources import attach_paired_markdown

        mapping = parse_class_case_bytes(_bytes(_minimal_case()), source_uri=CASE_URI)
        attached = attach_paired_markdown(
            mapping,
            repository="symbi/liuyao-learning-app",
            case_json_relative_path="materials/class-cases/lesson-99/case-001.json",
            source_root=tmp_path,
        )
        assert attached.paired_markdown is not None
        assert attached.paired_markdown.exists is False
        assert mapping.paired_markdown is None

    def test_derivation_rejects_non_json_path(self) -> None:
        from liuyao_kb.sources import paired_markdown_relative_path

        assert (
            paired_markdown_relative_path("materials/class-cases/lesson-99/case-001.json")
            == "materials/class-cases/lesson-99/case-001-analysis.md"
        )
        with pytest.raises(InvalidCaseJsonError, match="non-JSON path"):
            paired_markdown_relative_path("materials/class-cases/lesson-99/notes.md")


class TestPairedMarkdownSymlinks:
    """Existence checks must respect the repository boundary."""

    RELATIVE = "materials/class-cases/lesson-99/case-001.json"

    def _write_case(self, root: Path) -> Path:
        target = root / self.RELATIVE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_bytes(_minimal_case()))
        return target

    def _companion(self, root: Path) -> Path:
        return root / "materials/class-cases/lesson-99/case-001-analysis.md"

    def _symlink(self, target: Path, link: Path) -> None:
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"symlink creation unsupported on this platform: {error}")

    def test_plain_companion_file(self, tmp_path: Path) -> None:
        root = tmp_path / "repo"
        target = self._write_case(root)
        self._companion(root).write_text("# synthetic\n", encoding="utf-8")
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=root
        )
        assert mapping.paired_markdown is not None
        assert mapping.paired_markdown.exists is True

    def test_in_repo_symlink_counts_as_existing(self, tmp_path: Path) -> None:
        root = tmp_path / "repo"
        target = self._write_case(root)
        real = root / "materials/class-cases/lesson-99/real-companion.md"
        real.write_text("# synthetic\n", encoding="utf-8")
        self._symlink(real, self._companion(root))
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=root
        )
        assert mapping.paired_markdown is not None
        assert mapping.paired_markdown.exists is True

    def test_symlink_escaping_repo_does_not_count_as_existing(self, tmp_path: Path) -> None:
        root = tmp_path / "repo"
        target = self._write_case(root)
        outside = tmp_path / "outside-companion.md"
        outside.write_text("# outside the repo\n", encoding="utf-8")
        self._symlink(outside, self._companion(root))
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=root
        )
        assert mapping.paired_markdown is not None
        assert mapping.paired_markdown.exists is False

    def test_directory_at_companion_path_is_not_a_file(self, tmp_path: Path) -> None:
        root = tmp_path / "repo"
        target = self._write_case(root)
        self._companion(root).mkdir(parents=True)
        mapping = map_class_case_file(
            target, repository="symbi/liuyao-learning-app", source_root=root
        )
        assert mapping.paired_markdown is not None
        assert mapping.paired_markdown.exists is False
