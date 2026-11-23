"""Mapping for HTML-generated daily-record Markdown (M2-C2).

The HTML app exports one Markdown file per daily-record subrecord under
``daily-records/**/markdown/``. Such a file is a readable rendering of
exactly one CastRecord from the daily JSON container — it is not a new
case and not a second record. This layer:

* parses the Markdown with the existing :class:`MarkdownAdapter`, so the
  body keeps its sections, offsets and source identity;
* extracts the embedded ``## 原始记录 JSON`` block, which carries the
  subrecord's structured JSON, and reads its ``id``;
* cross-checks three identities — the record id in the file name
  (``<date>--<record_id>.md``), the embedded JSON ``id``, and (when the
  container mapping is supplied) the ``additionalQuestions[].id`` mapped
  by M2-C1 — and fails explicitly on any missing, duplicated or
  conflicting identity instead of guessing;
* exposes the body sections with the raw-record section excluded, so
  downstream chunking never indexes the embedded structured JSON twice;
* expresses the association as a ``RENDERS`` link to the existing
  CastRecord identity. It never creates a ClassCase or a second
  CastRecord, and it performs no Neo4j writes (that is M3).

This is the type-B Markdown of the Phase 1 plan. The type-A classroom
case Markdown (``materials/class-cases/*-analysis.md``) belongs to
M2-C3 and is never handled here.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from liuyao_kb.sources.adapters import MarkdownAdapter
from liuyao_kb.sources.case_json import (
    DailyRecordMappingResult,
    _resolve_within_root,
    map_daily_records_file,
)
from liuyao_kb.sources.config import DailyRecordsSettings
from liuyao_kb.sources.models import (
    MarkdownLocator,
    ParsedDocument,
    ParsedSection,
    SourceType,
    build_source_identity,
    repository_source_uri,
    sha256_bytes,
)

DAILY_MARKDOWN_PARSER_VERSION = "daily-markdown-mapper/1"

#: Heading of the section that embeds the subrecord's structured JSON.
RAW_RECORD_HEADING = "原始记录 JSON"

_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(\S.*?)[ \t]*$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_NON_FINITE = {"NaN", "Infinity", "-Infinity"}


class GeneratedMarkdownError(ValueError):
    """A generated daily-record Markdown failed identity verification."""


def _freeze_json(value: Any) -> Any:
    """Recursively freeze decoded JSON so stored raw data is immutable."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def record_id_from_filename(file_name: str) -> str | None:
    """Return the record id carried by a generated Markdown file name.

    Generated files are named ``<date>--<record_id>.md``. Anything that
    does not follow the pattern yields ``None`` (an unverifiable name),
    never a guessed id.
    """
    base = file_name.rsplit("/", 1)[-1]
    if not base.lower().endswith(".md"):
        return None
    stem = base[:-3]
    if "--" not in stem:
        return None
    candidate = stem.rsplit("--", 1)[1].strip()
    return candidate or None


class EmbeddedRawRecord(BaseModel):
    """The structured JSON embedded in the raw-record section."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str = Field(min_length=1)
    #: SHA-256 of the embedded JSON text exactly as written in the file.
    content_hash: str
    #: Character span of the whole raw-record section in the source text.
    section_start_offset: int = Field(ge=0)
    section_end_offset: int = Field(ge=0)
    #: The complete embedded JSON object, deep-frozen.
    raw: Mapping[str, Any]

    @field_validator("raw", mode="after")
    @classmethod
    def _freeze_raw(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return cast(Mapping[str, Any], _freeze_json(dict(value)))


class RendersLink(BaseModel):
    """The ``RENDERS`` association from the Markdown to its CastRecord."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relation: Literal["RENDERS"] = "RENDERS"
    #: The CastRecord this Markdown renders (never a ClassCase).
    record_id: str = Field(min_length=1)
    markdown_source_identity: str = Field(min_length=1)
    #: Container identity fields, set only after container verification.
    container_source_uri: str | None = None
    container_source_identity: str | None = None
    container_verified: bool = False


class GeneratedMarkdownMapping(BaseModel):
    """One generated daily-record Markdown, identity-verified."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: SourceType = SourceType.MARKDOWN
    source_identity: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    #: SHA-256 of the complete Markdown file bytes.
    content_hash: str
    parser_version: str = DAILY_MARKDOWN_PARSER_VERSION
    #: The verified record identity (file name id == embedded JSON id).
    record_id: str = Field(min_length=1)
    filename_record_id: str = Field(min_length=1)
    embedded_record_id: str = Field(min_length=1)
    embedded_raw_record: EmbeddedRawRecord
    #: Full MarkdownAdapter parse of the file (all sections).
    document: ParsedDocument
    #: Sections excluding the raw-record section — the chunkable body.
    body_sections: tuple[ParsedSection, ...] = ()
    renders: RendersLink


def _iter_lines(text: str) -> list[tuple[int, str]]:
    """Yield (start_offset, line_without_newline) pairs."""
    lines: list[tuple[int, str]] = []
    offset = 0
    for chunk in text.splitlines(keepends=True):
        lines.append((offset, chunk.rstrip("\r\n")))
        offset += len(chunk)
    return lines


def _raw_record_spans(text: str) -> list[tuple[int, int]]:
    """Locate ``## 原始记录 JSON`` section spans, ignoring fenced code."""
    lines = _iter_lines(text)
    spans: list[tuple[int, int]] = []
    section_start: int | None = None
    in_fence = False
    fence_char = ""
    fence_length = 0
    for start, content in lines:
        fence_match = _FENCE_RE.match(content)
        if in_fence:
            if (
                fence_match is not None
                and fence_match.group(1)[0] == fence_char
                and len(fence_match.group(1)) >= fence_length
                and not fence_match.group(2).strip()
            ):
                in_fence = False
            continue
        if fence_match is not None:
            in_fence = True
            fence_char = fence_match.group(1)[0]
            fence_length = len(fence_match.group(1))
            continue
        heading_match = _HEADING_RE.match(content)
        if heading_match is not None:
            if section_start is not None:
                spans.append((section_start, start))
                section_start = None
            heading_text = re.sub(r"[ \t]+#+$", "", heading_match.group(2)).strip()
            if len(heading_match.group(1)) == 2 and heading_text == RAW_RECORD_HEADING:
                section_start = start
    if section_start is not None:
        spans.append((section_start, len(text)))
    return spans


def _extract_embedded_json(text: str, span: tuple[int, int], source_uri: str) -> str:
    """Return the fenced JSON text inside the raw-record section span."""
    section = text[span[0] : span[1]]
    lines = section.splitlines()
    opening: int | None = None
    fence_char = ""
    fence_length = 0
    for index, content in enumerate(lines):
        fence_match = _FENCE_RE.match(content)
        if opening is None:
            if fence_match is not None:
                info = fence_match.group(2).strip().lower()
                if info not in ("", "json"):
                    raise GeneratedMarkdownError(
                        f"Raw-record section fence is not JSON in {source_uri}"
                    )
                opening = index
                fence_char = fence_match.group(1)[0]
                fence_length = len(fence_match.group(1))
            continue
        if (
            fence_match is not None
            and fence_match.group(1)[0] == fence_char
            and len(fence_match.group(1)) >= fence_length
            and not fence_match.group(2).strip()
        ):
            return "\n".join(lines[opening + 1 : index])
    raise GeneratedMarkdownError(
        f"Raw-record section has no complete fenced JSON block in {source_uri}"
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GeneratedMarkdownError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_non_finite(name: str) -> Any:
    raise GeneratedMarkdownError(f"non-finite JSON number is not allowed: {name}")


def _parse_embedded_json(json_text: str, source_uri: str) -> dict[str, Any]:
    try:
        value = json.loads(
            json_text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except GeneratedMarkdownError:
        raise
    except json.JSONDecodeError as error:
        raise GeneratedMarkdownError(
            f"Embedded raw-record JSON is not valid JSON in {source_uri}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise GeneratedMarkdownError(f"Embedded raw-record JSON must be an object in {source_uri}")
    return value


def parse_generated_markdown_bytes(
    data: bytes | bytearray | memoryview,
    *,
    source_uri: str,
    source_identity: str | None = None,
) -> GeneratedMarkdownMapping:
    """Parse and identity-verify one generated daily-record Markdown.

    The file name id is taken from ``source_uri``'s final segment. The
    file name id and the embedded JSON id must both exist and be equal;
    any missing, duplicated or conflicting identity is an explicit
    :class:`GeneratedMarkdownError`, never a guess.
    """
    raw_bytes = bytes(data)
    document = MarkdownAdapter().parse_bytes(raw_bytes, source_uri=source_uri)
    identity = source_identity or build_source_identity(SourceType.MARKDOWN, source_uri)
    text = raw_bytes.decode("utf-8")

    filename_record_id = record_id_from_filename(source_uri)
    if filename_record_id is None:
        raise GeneratedMarkdownError(
            f"File name does not carry a record id ('<date>--<record_id>.md'): {source_uri}"
        )
    spans = _raw_record_spans(text)
    if not spans:
        raise GeneratedMarkdownError(f"Missing '## {RAW_RECORD_HEADING}' section in {source_uri}")
    if len(spans) > 1:
        raise GeneratedMarkdownError(
            f"Duplicate '## {RAW_RECORD_HEADING}' sections in {source_uri}"
        )
    span = spans[0]
    json_text = _extract_embedded_json(text, span, source_uri)
    embedded = _parse_embedded_json(json_text, source_uri)
    embedded_id = embedded.get("id")
    if not isinstance(embedded_id, str) or not embedded_id.strip():
        raise GeneratedMarkdownError(
            f"Embedded raw-record JSON has no non-empty string 'id' in {source_uri}"
        )
    if embedded_id != filename_record_id:
        raise GeneratedMarkdownError(
            f"Record id mismatch in {source_uri}: file name carries "
            f"{filename_record_id!r} but embedded JSON carries {embedded_id!r}"
        )
    body_sections = tuple(
        section
        for section in document.sections
        if not (
            isinstance(section.locator, MarkdownLocator)
            and section.locator.heading == RAW_RECORD_HEADING
        )
    )
    return GeneratedMarkdownMapping(
        source_identity=identity,
        source_uri=source_uri,
        content_hash=sha256_bytes(raw_bytes),
        record_id=embedded_id,
        filename_record_id=filename_record_id,
        embedded_record_id=embedded_id,
        embedded_raw_record=EmbeddedRawRecord(
            record_id=embedded_id,
            content_hash=sha256_bytes(json_text.encode("utf-8")),
            section_start_offset=span[0],
            section_end_offset=span[1],
            raw=embedded,
        ),
        document=document,
        body_sections=body_sections,
        renders=RendersLink(
            record_id=embedded_id,
            markdown_source_identity=identity,
        ),
    )


def verify_against_container(
    mapping: GeneratedMarkdownMapping,
    container: DailyRecordMappingResult,
) -> GeneratedMarkdownMapping:
    """Verify the Markdown's record against the C1 container mapping.

    The record id must be one of the CastRecords M2-C1 actually mapped
    for the container (allowlist and ``only_cases`` already applied
    there). Anything else — absent, skipped or filtered out — is an
    explicit error, so a rendering can never attach to a record the
    importer did not accept. Returns a copy whose ``renders`` link
    carries the container identity; the input mapping is unchanged.
    """
    if not container.processed:
        raise GeneratedMarkdownError(
            "Container mapping was not processed; cannot verify the Markdown record"
        )
    known = {record.record_id for record in container.records}
    if mapping.record_id not in known:
        raise GeneratedMarkdownError(
            f"Record {mapping.record_id!r} from {mapping.source_uri} is not among "
            f"the mapped CastRecords of container {container.source_uri}"
        )
    link = mapping.renders.model_copy(
        update={
            "container_source_uri": container.source_uri,
            "container_source_identity": container.source_identity,
            "container_verified": True,
        }
    )
    return mapping.model_copy(update={"renders": link})


def map_generated_markdown_file(
    path: str | Path,
    *,
    repository: str,
    source_root: str | Path,
    container_path: str | Path | None = None,
    settings: DailyRecordsSettings | None = None,
) -> GeneratedMarkdownMapping:
    """Read and map one generated Markdown file inside ``source_root``.

    Path handling is the shared M2-C1 logic: relative paths resolve
    against ``source_root`` and the resolved path is boundary-checked
    before it is read. When ``container_path`` is given, the container
    JSON is mapped through M2-C1 with ``settings`` (default settings,
    i.e. ``include=False``, cannot verify a container and raise) and
    the Markdown is verified against the mapped CastRecords.
    """
    resolved, relative = _resolve_within_root(Path(path), Path(source_root))
    source_uri = repository_source_uri(repository, relative)
    identity = build_source_identity(SourceType.MARKDOWN, source_uri)
    mapping = parse_generated_markdown_bytes(
        resolved.read_bytes(), source_uri=source_uri, source_identity=identity
    )
    if container_path is not None:
        container = map_daily_records_file(
            container_path,
            repository=repository,
            source_root=source_root,
            settings=settings if settings is not None else DailyRecordsSettings(),
        )
        mapping = verify_against_container(mapping, container)
    return mapping


__all__ = [
    "DAILY_MARKDOWN_PARSER_VERSION",
    "RAW_RECORD_HEADING",
    "EmbeddedRawRecord",
    "GeneratedMarkdownError",
    "GeneratedMarkdownMapping",
    "RendersLink",
    "map_generated_markdown_file",
    "parse_generated_markdown_bytes",
    "record_id_from_filename",
    "verify_against_container",
]
