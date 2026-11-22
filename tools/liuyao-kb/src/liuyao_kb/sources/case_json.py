"""Deterministic JSON mapping for classroom cases and daily records (M2-C1).

This layer turns two kinds of JSON files into typed mappings. It performs
no Neo4j writes, no chunking, no model calls and no chart recomputation:
the hexagram structure and the teacher analysis are carried exactly as the
source files state them, with the complete original JSON preserved.

Identity rules (Phase 1 frozen decision 14):

* A classroom case JSON (``recordType=class-case``) maps to a ClassCase
  whose ``case_id`` is the JSON ``id`` field.
* A daily-records container is never a case. Only ``additionalQuestions[]``
  subrecords whose (container path, ``id``) pair is explicitly allowlisted
  map to CastRecords, keyed by ``record_id``.
* A ClassCase links to a CastRecord only when the case JSON's
  ``dailyRecord.recordId`` exactly equals the CastRecord's ``record_id``.
  Dates, chart names, question text and similarity are never used.
* Classification flags (``isCase``, ``caseSource``) are preserved as
  metadata only; they never promote a record to a ClassCase.

Paired Markdown (type A): a class-case JSON may have a companion
Markdown file in the same directory (``case-xxx.json`` next to
``case-xxx-analysis.md``). The JSON and the Markdown are two *different*
materials of the same ClassCase; their contents are not required to
agree, and neither is a copy of the other. M2-C1 only *identifies* the
companion -- its expected repository-relative path, whether the file
exists, and its association to the same ``case_id`` -- reusing the
repository source URI / source identity helpers. It never reads or
parses the Markdown body; that is M2-C3's job. This companion is not the
``dailyRecord.markdownPath`` target: that path points at an
auto-generated daily-records Markdown (type B), a CastRecord rendering
handled by the M2-C2 design, with a different identity model.

``matchStatus`` handling: ``verified`` is the canonical value; the legacy
``matched`` is normalized to ``verified`` with the raw value preserved.
Unknown or missing values are kept and flagged as needing review -- never
silently dropped and never treated as verified. ``verified`` asserts case
identity only; it does not claim the teacher ASR was audio-verified.
"""

from __future__ import annotations

import json
import math
from collections.abc import Collection, Mapping, Sequence
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from liuyao_kb.sources.config import DailyRecordsSettings
from liuyao_kb.sources.models import (
    JsonLocator,
    SourceType,
    build_source_identity,
    json_pointer,
    repository_source_uri,
    sha256_bytes,
)

CASE_JSON_PARSER_VERSION = "case-json-mapper/1"


class CaseMappingError(ValueError):
    """Base error for case/daily-record JSON mapping failures."""


class InvalidCaseJsonError(CaseMappingError):
    """The JSON bytes cannot be decoded or do not have the required shape."""


class AllowlistError(CaseMappingError):
    """The daily-record allowlist is violated or cannot be satisfied."""


class MatchStatus(StrEnum):
    """Normalized case-identity match status for a classroom case."""

    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    NOT_FOUND = "not_found"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"


#: Legacy spellings that normalize to a canonical MatchStatus.
_MATCH_STATUS_ALIASES: dict[str, MatchStatus] = {"matched": MatchStatus.VERIFIED}

_CANONICAL_MATCH_STATUSES: dict[str, MatchStatus] = {
    status.value: status for status in MatchStatus if status is not MatchStatus.UNKNOWN
}


def normalize_match_status(raw: Any) -> tuple[MatchStatus | None, str | None, bool]:
    """Normalize a raw ``matchStatus`` value.

    Returns ``(status, raw_text, needs_review)``. ``raw_text`` is the
    original string when the value was a string, else ``None`` (the full
    original JSON is always preserved on the mapping itself). Missing or
    null values yield ``(None, None, True)``; unknown values yield
    ``(MatchStatus.UNKNOWN, raw, True)``; the legacy alias ``matched``
    yields ``verified`` with the raw value preserved.
    """

    if raw is None:
        return None, None, True
    if not isinstance(raw, str):
        return MatchStatus.UNKNOWN, None, True
    if raw in _CANONICAL_MATCH_STATUSES:
        return _CANONICAL_MATCH_STATUSES[raw], raw, False
    if raw in _MATCH_STATUS_ALIASES:
        return _MATCH_STATUS_ALIASES[raw], raw, False
    return MatchStatus.UNKNOWN, raw, True


def _freeze_json(value: Any) -> Any:
    """Validate JSON-compatibility and copy into immutable containers."""
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidCaseJsonError("JSON object keys must be strings")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidCaseJsonError("JSON numbers must be finite")
        return value
    raise InvalidCaseJsonError("value is not JSON-compatible")


def _thaw_json(value: Any) -> Any:
    """Convert frozen containers back into ordinary JSON values."""
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json(item) for item in value]
    return value


class _RawJsonModel(BaseModel):
    """Base model carrying a complete, immutable copy of raw JSON."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw: Mapping[str, Any] = Field(default_factory=dict, validate_default=True)

    @field_validator("raw", mode="after")
    @classmethod
    def _freeze_raw(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return cast(Mapping[str, Any], _freeze_json(value))

    @field_serializer("raw")
    def _serialize_raw(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], _thaw_json(value))


class DailyRecordRef(_RawJsonModel):
    """The ``dailyRecord`` block of a class-case JSON, as written.

    Both historical path spellings are honoured: case-001 uses ``path``,
    case-002 uses ``jsonPath`` (plus ``markdownPath``). If both spellings
    are present they must agree; a conflict is an error, never a silent
    choice. The complete original block is preserved in ``raw``.
    """

    record_id: str | None = None
    json_path: str | None = None
    markdown_path: str | None = None


class PairedMarkdownRef(BaseModel):
    """Identification of a class-case JSON's companion Markdown (type A).

    Carries location and association only -- never Markdown content.
    ``exists`` is True/False when a repository root was available to
    check, and None when no root was provided (unchecked is never
    reported as missing).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    #: The ClassCase this companion belongs to (same identity as the JSON).
    case_id: str = Field(min_length=1)
    #: Expected repository-relative POSIX path of the Markdown file.
    relative_path: str = Field(min_length=1)
    #: Canonical repo:// source URI of the Markdown file.
    source_uri: str = Field(min_length=1)
    #: Source identity of the Markdown as its own SourceDocument.
    source_identity: str = Field(min_length=1)
    source_type: SourceType = SourceType.MARKDOWN
    exists: bool | None = None


class ClassCaseMapping(_RawJsonModel):
    """A classroom case JSON mapped to its ClassCase identity."""

    source_type: SourceType = SourceType.CLASSROOM_CASE
    source_identity: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    content_hash: str
    parser_version: str = CASE_JSON_PARSER_VERSION
    locator: JsonLocator
    case_id: str = Field(min_length=1)
    lesson_id: str | None = None
    record_type: str
    match_status: MatchStatus | None = None
    match_status_raw: str | None = None
    match_status_needs_review: bool = False
    daily_record: DailyRecordRef | None = None
    #: Set only by exact recordId matching against mapped CastRecords.
    linked_record_id: str | None = None
    #: Type-A companion Markdown identification. Set only by the
    #: file-level resolver; the pure bytes parser leaves it None.
    paired_markdown: PairedMarkdownRef | None = None

    @field_validator("content_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("content_hash must be a lowercase SHA-256 hex digest")
        return value


class CastRecordMapping(_RawJsonModel):
    """One allowlisted daily-record subrecord mapped to a CastRecord."""

    source_type: SourceType = SourceType.DAILY_RECORD
    source_identity: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    content_hash: str
    parser_version: str = CASE_JSON_PARSER_VERSION
    locator: JsonLocator
    record_id: str = Field(min_length=1)
    #: Classification flags, preserved as metadata only. They are never
    #: proof of a verified classroom-case match.
    is_case: bool | None = None
    case_source: str | None = None

    @field_validator("content_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("content_hash must be a lowercase SHA-256 hex digest")
        return value


class DailyRecordMappingResult(BaseModel):
    """Outcome of mapping one daily-records container."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    processed: bool
    source_identity: str | None = None
    source_uri: str | None = None
    content_hash: str | None = None
    records: tuple[CastRecordMapping, ...] = ()
    #: Subrecord ids present in the container but not allowlisted.
    skipped_record_ids: tuple[str, ...] = ()
    #: Allowlisted ids excluded by the only_cases filter (isCase not true).
    filtered_record_ids: tuple[str, ...] = ()


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidCaseJsonError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_non_finite(token: str) -> Any:
    raise InvalidCaseJsonError(f"non-finite JSON number is not allowed: {token}")


def _decode_json_object(data: bytes | bytearray | memoryview, source_uri: str) -> dict[str, Any]:
    """Decode strict UTF-8 JSON bytes into a top-level object, or fail."""
    if isinstance(data, (bytearray, memoryview)):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("expected bytes input; decode text before mapping")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InvalidCaseJsonError(
            f"Source is not valid UTF-8: {source_uri} (byte offset {error.start}: {error.reason})"
        ) from error
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except InvalidCaseJsonError:
        raise
    except json.JSONDecodeError as error:
        raise InvalidCaseJsonError(
            f"Invalid JSON in {source_uri}: line {error.lineno} column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(parsed, dict):
        raise InvalidCaseJsonError(f"Top-level JSON value must be an object: {source_uri}")
    return parsed


def _optional_str(container: Mapping[str, Any], key: str, source_uri: str) -> str | None:
    value = container.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidCaseJsonError(f"Field {key!r} must be a string or null: {source_uri}")
    return value


def _parse_daily_record_ref(value: Any, source_uri: str) -> DailyRecordRef | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise InvalidCaseJsonError(f"Field 'dailyRecord' must be an object or null: {source_uri}")
    record_id = _optional_str(value, "recordId", source_uri)
    path = _optional_str(value, "path", source_uri)
    json_path = _optional_str(value, "jsonPath", source_uri)
    if path is not None and json_path is not None and path != json_path:
        raise InvalidCaseJsonError(
            "Conflicting dailyRecord path aliases ('path' != 'jsonPath'); "
            f"refusing to choose silently: {source_uri}"
        )
    return DailyRecordRef(
        record_id=record_id,
        json_path=json_path if json_path is not None else path,
        markdown_path=_optional_str(value, "markdownPath", source_uri),
        raw=dict(value),
    )


def parse_class_case_bytes(
    data: bytes | bytearray | memoryview,
    *,
    source_uri: str,
    source_identity: str | None = None,
) -> ClassCaseMapping:
    """Map one class-case JSON document (bytes) to a ClassCaseMapping."""
    document = _decode_json_object(data, source_uri)
    identity = source_identity or build_source_identity(SourceType.CLASSROOM_CASE, source_uri)
    record_type = document.get("recordType")
    if record_type != "class-case":
        raise InvalidCaseJsonError(
            f"Expected recordType 'class-case', got {record_type!r}: {source_uri}"
        )
    case_id = document.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise InvalidCaseJsonError(
            f"Class-case JSON must carry a non-empty string 'id': {source_uri}"
        )
    status, status_raw, needs_review = normalize_match_status(document.get("matchStatus"))
    return ClassCaseMapping(
        source_identity=identity,
        source_uri=source_uri,
        content_hash=sha256_bytes(bytes(data)),
        locator=JsonLocator(record_id=case_id, json_pointer=""),
        case_id=case_id,
        lesson_id=_optional_str(document, "lessonId", source_uri),
        record_type=record_type,
        match_status=status,
        match_status_raw=status_raw,
        match_status_needs_review=needs_review,
        daily_record=_parse_daily_record_ref(document.get("dailyRecord"), source_uri),
        raw=document,
    )


def parse_daily_container_bytes(
    data: bytes | bytearray | memoryview,
    *,
    source_uri: str,
    allowed_record_ids: Collection[str],
    source_identity: str | None = None,
    only_cases: bool = True,
) -> DailyRecordMappingResult:
    """Map the allowlisted subrecords of one daily-records container.

    Only ``additionalQuestions[]`` is considered; other container content
    (for example ``dailyFortune``) is never mapped. Allowlisted ids that
    are absent, and duplicated subrecord ids, are explicit errors.

    With ``only_cases`` on (the original ``DailyRecordsSettings``
    semantics), an allowlisted subrecord is mapped only when it is
    explicitly marked ``isCase: true``; allowlisted records filtered out
    this way are reported in ``filtered_record_ids``, never silently
    dropped. The flag is classification only: a mapped record is always
    a CastRecord, never a ClassCase.
    """
    document = _decode_json_object(data, source_uri)
    identity = source_identity or build_source_identity(SourceType.DAILY_RECORD, source_uri)
    content_hash = sha256_bytes(bytes(data))
    subrecords = document.get("additionalQuestions", [])
    if not isinstance(subrecords, list):
        raise InvalidCaseJsonError(f"Field 'additionalQuestions' must be an array: {source_uri}")
    allowed = set(allowed_record_ids)
    seen: dict[str, int] = {}
    records: list[CastRecordMapping] = []
    skipped: list[str] = []
    filtered: list[str] = []
    for index, item in enumerate(subrecords):
        if not isinstance(item, Mapping):
            raise InvalidCaseJsonError(
                f"additionalQuestions[{index}] must be an object: {source_uri}"
            )
        record_id = item.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            raise InvalidCaseJsonError(
                f"additionalQuestions[{index}] must carry a non-empty string 'id': {source_uri}"
            )
        if record_id in seen:
            raise AllowlistError(f"Duplicate subrecord id {record_id!r} in container: {source_uri}")
        seen[record_id] = index
        if record_id not in allowed:
            skipped.append(record_id)
            continue
        is_case = item.get("isCase")
        if is_case is not None and not isinstance(is_case, bool):
            raise InvalidCaseJsonError(
                f"Subrecord {record_id!r} field 'isCase' must be a boolean or null: {source_uri}"
            )
        if only_cases and is_case is not True:
            filtered.append(record_id)
            continue
        records.append(
            CastRecordMapping(
                source_identity=identity,
                source_uri=source_uri,
                content_hash=content_hash,
                locator=JsonLocator(
                    record_id=record_id,
                    json_pointer=json_pointer(["additionalQuestions", str(index)]),
                ),
                record_id=record_id,
                is_case=is_case,
                case_source=_optional_str(item, "caseSource", source_uri),
                raw=dict(item),
            )
        )
    missing = sorted(allowed - set(seen))
    if missing:
        raise AllowlistError(
            f"Allowlisted record id(s) not found in container {source_uri}: " + ", ".join(missing)
        )
    return DailyRecordMappingResult(
        processed=True,
        source_identity=identity,
        source_uri=source_uri,
        content_hash=content_hash,
        records=tuple(records),
        skipped_record_ids=tuple(skipped),
        filtered_record_ids=tuple(filtered),
    )


def link_daily_records(
    cases: Sequence[ClassCaseMapping],
    records: Sequence[CastRecordMapping],
) -> tuple[ClassCaseMapping, ...]:
    """Resolve ClassCase -> CastRecord links by exact recordId equality.

    A case whose ``dailyRecord.recordId`` has no mapped CastRecord keeps
    its original reference with ``linked_record_id=None``; no link is ever
    fabricated from dates, names or text similarity.
    """
    known = {record.record_id for record in records}
    linked: list[ClassCaseMapping] = []
    for case in cases:
        ref_id = case.daily_record.record_id if case.daily_record is not None else None
        target = ref_id if ref_id is not None and ref_id in known else None
        linked.append(case.model_copy(update={"linked_record_id": target}))
    return tuple(linked)


def paired_markdown_relative_path(case_json_relative_path: str) -> str:
    """Derive the companion Markdown path from the case JSON's own path.

    The derivation uses only the JSON file's repository-relative path
    and file name (same directory, ``<stem>-analysis.md``) -- never the
    ``case_id`` value inside the JSON. The full relative path is kept,
    so identical file names in different lesson directories can never
    be confused.
    """
    normalized = case_json_relative_path.strip().replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.suffix != ".json" or not pure.name:
        raise InvalidCaseJsonError(
            f"Cannot derive a companion Markdown path from a non-JSON path: "
            f"{case_json_relative_path}"
        )
    return pure.with_name(f"{pure.stem}-analysis.md").as_posix()


def resolve_paired_markdown(
    *,
    repository: str,
    case_id: str,
    case_json_relative_path: str,
    source_root: str | Path | None = None,
) -> PairedMarkdownRef:
    """Identify (never read) the type-A companion Markdown of a case JSON.

    ``exists`` is checked only when ``source_root`` is provided; without
    a root it stays None rather than being reported as missing.
    """
    relative = paired_markdown_relative_path(case_json_relative_path)
    source_uri = repository_source_uri(repository, relative)
    exists: bool | None = None
    if source_root is not None:
        root = Path(source_root).expanduser().resolve()
        candidate = (root / relative).resolve()
        # A symlink at the expected path must not escape the repository:
        # only a regular file whose resolved path stays inside the root
        # counts as existing. The file body is never read here.
        exists = candidate.is_relative_to(root) and candidate.is_file()
    return PairedMarkdownRef(
        case_id=case_id,
        relative_path=relative,
        source_uri=source_uri,
        source_identity=build_source_identity(SourceType.MARKDOWN, source_uri),
        exists=exists,
    )


def attach_paired_markdown(
    mapping: ClassCaseMapping,
    *,
    repository: str,
    case_json_relative_path: str,
    source_root: str | Path | None = None,
) -> ClassCaseMapping:
    """Return a copy of ``mapping`` with its companion Markdown identified."""
    ref = resolve_paired_markdown(
        repository=repository,
        case_id=mapping.case_id,
        case_json_relative_path=case_json_relative_path,
        source_root=source_root,
    )
    return mapping.model_copy(update={"paired_markdown": ref})


def _resolve_within_root(path: Path, source_root: Path) -> tuple[Path, str]:
    """Resolve ``path`` against ``source_root`` and verify the boundary.

    Relative paths are interpreted relative to ``source_root``, never the
    process working directory; absolute paths are resolved as given.
    ``resolve()`` follows symlinks, so a link escaping the root is
    rejected. Returns the resolved absolute path — the path callers must
    actually read — together with its repository-relative POSIX path, so
    the boundary check and the read can never diverge.
    """
    root = source_root.expanduser().resolve()
    expanded = path.expanduser()
    resolved = (root / expanded).resolve() if not expanded.is_absolute() else expanded.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        raise AllowlistError(f"Path is outside the allowed repository root: {path}") from None
    return resolved, PurePosixPath(relative.as_posix()).as_posix()


def _relative_to_root(path: Path, source_root: Path) -> str:
    return _resolve_within_root(path, source_root)[1]


def map_class_case_file(
    path: str | Path,
    *,
    repository: str,
    source_root: str | Path,
) -> ClassCaseMapping:
    """Read and map one class-case JSON file inside ``source_root``."""
    resolved, relative = _resolve_within_root(Path(path), Path(source_root))
    source_uri = repository_source_uri(repository, relative)
    identity = build_source_identity(SourceType.CLASSROOM_CASE, source_uri)
    mapping = parse_class_case_bytes(
        resolved.read_bytes(), source_uri=source_uri, source_identity=identity
    )
    return attach_paired_markdown(
        mapping,
        repository=repository,
        case_json_relative_path=relative,
        source_root=source_root,
    )


def map_daily_records_file(
    path: str | Path,
    *,
    repository: str,
    source_root: str | Path,
    settings: DailyRecordsSettings,
) -> DailyRecordMappingResult:
    """Map one daily-records container under a fail-closed allowlist.

    With ``settings.include`` off, nothing is read and an unprocessed
    result is returned. With it on, only the subrecords allowlisted for
    this container's repository-relative path are mapped.
    """
    if not settings.include:
        return DailyRecordMappingResult(processed=False)
    resolved, relative = _resolve_within_root(Path(path), Path(source_root))
    allowed_ids = settings.allowed_ids_for(relative)
    source_uri = repository_source_uri(repository, relative)
    identity = build_source_identity(SourceType.DAILY_RECORD, source_uri)
    return parse_daily_container_bytes(
        resolved.read_bytes(),
        source_uri=source_uri,
        allowed_record_ids=allowed_ids,
        source_identity=identity,
        only_cases=settings.only_cases,
    )
