"""Parsing for classroom-case paired Markdown (M2-C3).

A classroom case has two different materials for one ClassCase: the
structured JSON (mapped by M2-C1) and a readable Markdown file such as
``materials/class-cases/lesson-19/case-001-analysis.md``. This layer
parses that Markdown — the type-A Markdown of the Phase 1 plan — and
associates it with the same ClassCase through a ``HAS_REPRESENTATION``
link with ``format=markdown``.

The pairing itself is never re-derived here: M2-C1 already identified
it in ``ClassCaseMapping.paired_markdown`` (a :class:`PairedMarkdownRef`
carrying the expected path, source URI/identity and existence state,
derived from the JSON file's own location). C3 consumes exactly that
reference:

* the Markdown's ``case_id`` is the ClassCase's ``case_id``, unchanged;
* the Markdown is parsed with the existing :class:`MarkdownAdapter`,
  so it keeps its own ParsedDocument identity, content hash, sections
  and character offsets — it is a second SourceDocument, not a second
  case and not an independent analysis source;
* JSON and Markdown contents are not required to agree and are never
  merged: each keeps its own source, path and version;
* no content role is inferred from semantics. Teacher explanation,
  user memo and AI calculation stay exactly as the file's own headings
  and paragraphs present them; links in the Markdown are preserved as
  text and are never fetched.

This type-A Markdown is strictly distinct from the type-B generated
daily-record Markdown (``daily-records/**/markdown/``), which renders
a CastRecord through ``RENDERS`` and belongs to M2-C2. In particular,
a case JSON's ``dailyRecord.markdownPath`` points at a type-B file and
is never read here; only ``paired_markdown.relative_path`` is.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from liuyao_kb.sources.adapters import MarkdownAdapter
from liuyao_kb.sources.case_json import (
    ClassCaseMapping,
    _resolve_within_root,
    map_class_case_file,
)
from liuyao_kb.sources.models import ParsedDocument, SourceType

CASE_MARKDOWN_PARSER_VERSION = "case-markdown-mapper/1"


class ClassCaseMarkdownError(ValueError):
    """A classroom-case paired Markdown could not be mapped."""


class HasRepresentationLink(BaseModel):
    """The ``HAS_REPRESENTATION`` link from a ClassCase to this Markdown."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relation: Literal["HAS_REPRESENTATION"] = "HAS_REPRESENTATION"
    format: Literal["markdown"] = "markdown"
    #: The one ClassCase both representations belong to.
    case_id: str = Field(min_length=1)
    #: Source identity of the case JSON's own SourceDocument.
    class_case_source_identity: str = Field(min_length=1)
    #: Source identity of the Markdown's own SourceDocument.
    markdown_source_identity: str = Field(min_length=1)


class ClassCaseMarkdownMapping(BaseModel):
    """One classroom-case paired Markdown, parsed and associated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: SourceType = SourceType.MARKDOWN
    source_identity: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    #: SHA-256 of the complete Markdown file bytes.
    content_hash: str
    parser_version: str = CASE_MARKDOWN_PARSER_VERSION
    #: Identical to the ClassCase's case_id — never re-derived.
    case_id: str = Field(min_length=1)
    class_case_source_uri: str = Field(min_length=1)
    class_case_source_identity: str = Field(min_length=1)
    #: Full MarkdownAdapter parse of the file (all sections).
    document: ParsedDocument
    has_representation: HasRepresentationLink


def parse_class_case_markdown_bytes(
    data: bytes | bytearray | memoryview,
    *,
    class_case: ClassCaseMapping,
    revision_ref: str | None = None,
) -> ClassCaseMarkdownMapping:
    """Parse paired-Markdown bytes for an already-mapped ClassCase.

    The source URI and identity come from the ClassCase's
    ``paired_markdown`` reference (M2-C1); a ClassCase without one is
    an explicit error. Encoding and emptiness failures propagate from
    the MarkdownAdapter unchanged.
    """
    paired = class_case.paired_markdown
    if paired is None:
        raise ClassCaseMarkdownError(
            f"ClassCase {class_case.case_id!r} has no paired Markdown reference"
        )
    if paired.case_id != class_case.case_id:
        raise ClassCaseMarkdownError(
            f"Paired Markdown case_id {paired.case_id!r} does not match "
            f"ClassCase case_id {class_case.case_id!r}"
        )
    document = MarkdownAdapter().parse_bytes(
        bytes(data), source_uri=paired.source_uri, revision_ref=revision_ref
    )
    if document.source_identity != paired.source_identity:
        raise ClassCaseMarkdownError(
            f"Parsed Markdown identity {document.source_identity!r} does not match "
            f"the paired reference identity {paired.source_identity!r}"
        )
    link = HasRepresentationLink(
        case_id=class_case.case_id,
        class_case_source_identity=class_case.source_identity,
        markdown_source_identity=paired.source_identity,
    )
    return ClassCaseMarkdownMapping(
        source_identity=paired.source_identity,
        source_uri=paired.source_uri,
        content_hash=document.content_hash,
        case_id=class_case.case_id,
        class_case_source_uri=class_case.source_uri,
        class_case_source_identity=class_case.source_identity,
        document=document,
        has_representation=link,
    )


def map_class_case_markdown_file(
    class_case: ClassCaseMapping,
    *,
    source_root: str | Path,
    revision_ref: str | None = None,
) -> ClassCaseMarkdownMapping:
    """Read and parse the paired Markdown for a mapped ClassCase.

    ``class_case`` must come from M2-C1's file-level mapping against
    the same ``source_root``, so the paired reference's existence state
    is known: an unchecked reference (``exists is None``) or a missing
    file (``exists is False``) is an explicit error here, never a
    silent skip — and the ClassCase mapping itself is left untouched
    either way. The file actually read is ``paired_markdown``'s
    repository-relative path resolved through the shared M2-C1 path
    logic, so the boundary check and the read use the same resolved
    path and out-of-root or symlink escapes fail explicitly.
    """
    paired = class_case.paired_markdown
    if paired is None:
        raise ClassCaseMarkdownError(
            f"ClassCase {class_case.case_id!r} has no paired Markdown reference"
        )
    if paired.exists is None:
        raise ClassCaseMarkdownError(
            f"Paired Markdown existence has not been verified for case "
            f"{class_case.case_id!r}: {paired.relative_path}"
        )
    if paired.exists is False:
        raise ClassCaseMarkdownError(
            f"Paired Markdown is missing for case {class_case.case_id!r}: {paired.relative_path}"
        )
    resolved, relative = _resolve_within_root(Path(paired.relative_path), Path(source_root))
    if relative != paired.relative_path:
        raise ClassCaseMarkdownError(
            f"Paired Markdown path {paired.relative_path!r} resolved to a "
            f"different repository path {relative!r}"
        )
    return parse_class_case_markdown_bytes(
        resolved.read_bytes(), class_case=class_case, revision_ref=revision_ref
    )


def map_class_case_markdown_for_case_file(
    path: str | Path,
    *,
    repository: str,
    source_root: str | Path,
    revision_ref: str | None = None,
) -> tuple[ClassCaseMapping, ClassCaseMarkdownMapping]:
    """Map a class-case JSON file and its paired Markdown together.

    The JSON is mapped by M2-C1 (which identifies and existence-checks
    the paired Markdown); the Markdown is then mapped by this module.
    Both mappings are returned so the caller keeps the ClassCase even
    if the Markdown step is handled separately.
    """
    class_case = map_class_case_file(path, repository=repository, source_root=source_root)
    markdown = map_class_case_markdown_file(
        class_case, source_root=source_root, revision_ref=revision_ref
    )
    return class_case, markdown


__all__ = [
    "CASE_MARKDOWN_PARSER_VERSION",
    "ClassCaseMarkdownError",
    "ClassCaseMarkdownMapping",
    "HasRepresentationLink",
    "map_class_case_markdown_file",
    "map_class_case_markdown_for_case_file",
    "parse_class_case_markdown_bytes",
]
