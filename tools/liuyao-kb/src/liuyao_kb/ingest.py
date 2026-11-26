"""Ingest orchestration (Phase 1 M4b).

``collect_plan`` turns the sources allowlist into a concrete,
in-memory import plan by running the existing M2 adapters/mappers
and the M4a chunker — nothing here invents a parallel parsing or
mapping path. ``run_plan`` executes a plan through
:class:`liuyao_kb.neo4j.importer.Neo4jImporter`. A plan is a report
of what *would* be imported; it is never a second source of sync
truth (sync state lives in Neo4j, plan section 8).

Scope notes:

* Curated lesson notes are chunked (the main course-text source).
* Class-case JSON becomes a SourceDocument without chunks; its
  paired Markdown is chunked; both hang off one ClassCase via
  HAS_REPRESENTATION.
* Daily records enter only through the fail-closed allowlist.
  The container JSON never becomes a SourceDocument. A generated
  daily Markdown becomes a SourceDocument linked by RENDERS and
  is *not* chunked by default; if that ever changes, the input
  must be the M2-C2 mapping's ``body_sections``, never the raw
  file (the raw file re-includes the embedded record JSON).
* Raw ASR is never imported here: no chunks, no embeddings, only
  the source references the case mappings already carry.
* Case -> notes REFERENCES links are created only from explicit
  :class:`CaseReferenceSpec` assignments (a notes section heading
  prefix per case, with a primary/secondary role). Nothing is
  inferred from text similarity, and no offset is fabricated: a
  reference points at whole chunks of the named section.
"""

from __future__ import annotations

import json
import re
from functools import partial
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from liuyao_kb.chunking import CHUNKER_VERSION, Chunk, chunk_document
from liuyao_kb.ids import make_document_id, make_revision_id
from liuyao_kb.neo4j.importer import (
    CaseReferenceImport,
    CastRecordImport,
    CastRecordImportResult,
    ClassCaseImport,
    DocumentImport,
    DocumentImportResult,
    ImporterSession,
    LessonImport,
    Neo4jImporter,
)
from liuyao_kb.sources import (
    ClassCaseMapping,
    SourcesConfig,
    link_daily_records,
    map_class_case_file,
    map_class_case_markdown_file,
    map_daily_records_file,
    map_generated_markdown_file,
)
from liuyao_kb.sources.adapters import MarkdownAdapter

_LESSON_PATTERN = re.compile(r"lesson-(\d+)")


class CaseReferenceSpec(BaseModel):
    """Explicit case -> notes-section reference assignment.

    ``sections`` pairs a heading prefix (matched against the
    chunk's heading_path entries, for example ``"7. "`` for the
    seventh numbered section) with a role: ``primary`` for the
    case's main section, ``secondary`` for supporting blocks such
    as the summary-table section.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    notes_document_id: str = Field(min_length=1)
    sections: tuple[tuple[str, str], ...] = ()


class IngestPlan(BaseModel):
    """Everything one ingest run would write (in-memory only)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    documents: tuple[DocumentImport, ...] = ()
    lessons: tuple[LessonImport, ...] = ()
    cases: tuple[ClassCaseImport, ...] = ()
    records: tuple[CastRecordImport, ...] = ()
    #: (case_id, record_id) pairs established by exact recordId
    #: matching against records that are part of this plan.
    record_links: tuple[tuple[str, str], ...] = ()
    #: (record_id, document_id) RENDERS links for generated MD.
    renders_links: tuple[tuple[str, str], ...] = ()
    #: case_id -> REFERENCES links to chunks of this plan.
    references: tuple[tuple[str, tuple[CaseReferenceImport, ...]], ...] = ()
    #: Human-readable notes about sources intentionally not
    #: imported (never contains source body text).
    skipped: tuple[str, ...] = ()

    def chunk_count(self) -> int:
        return sum(len(document.chunks) for document in self.documents)


class IngestFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item: str
    error: str


class IngestReport(BaseModel):
    """Outcome of executing one plan (in-memory report only)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    documents: tuple[DocumentImportResult, ...] = ()
    #: Per-record outcomes with source provenance (container path
    #: and JSON pointer; never body text).
    records: tuple[CastRecordImportResult, ...] = ()
    lessons_imported: int = 0
    cases_imported: int = 0
    records_imported: int = 0
    record_links: int = 0
    renders_links: int = 0
    references_written: int = 0
    failures: tuple[IngestFailure, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.failures


# ---------------------------------------------------------------------------
# Plan collection
# ---------------------------------------------------------------------------


def _glob(root: Path, includes: list[str], excludes: list[str]) -> list[Path]:
    included: set[Path] = set()
    for pattern in includes:
        included.update(p for p in root.glob(pattern) if p.is_file())
    for pattern in excludes:
        included.difference_update(p for p in root.glob(pattern) if p.is_file())
    return sorted(included)


def _markdown_document(
    *,
    document_id: str,
    source_uri: str,
    trust_level: str,
    content_hash: str,
    revision_ref: str | None,
    parser_version: str,
    chunks: tuple[Chunk, ...],
) -> DocumentImport:
    """A Markdown document that WAS chunked with the current chunker.

    ``chunker_version`` is recorded even when the document produced
    zero chunks (a headings-only file): the revision was chunked,
    it simply had no body paragraphs.
    """
    return DocumentImport(
        document_id=document_id,
        source_type="markdown",
        source_uri=source_uri,
        trust_level=trust_level,
        revision_id=make_revision_id(document_id, content_hash),
        content_hash=content_hash,
        revision_ref=revision_ref,
        parser_version=parser_version,
        chunker_version=CHUNKER_VERSION,
        chunks=tuple(chunks),
    )


def _collect_notes(sources: SourcesConfig, repository: str, plan: dict[str, Any]) -> None:
    settings = sources.curated_notes
    if not settings.enabled:
        return
    if settings.root is None:
        raise ValueError("curated_notes.root is not configured")
    root = settings.root.expanduser()
    adapter = MarkdownAdapter()
    lessons: dict[str, LessonImport] = {}
    for path in _glob(root, settings.include_globs, settings.exclude_globs):
        relative = path.relative_to(root).as_posix()
        parsed = adapter.parse_file(path, repository=repository, relative_path=relative)
        document_id = make_document_id("markdown", repository, relative)
        result = chunk_document(parsed, document_id=document_id)
        plan["documents"].append(
            _markdown_document(
                document_id=document_id,
                source_uri=parsed.source_uri,
                trust_level="primary",
                content_hash=parsed.content_hash,
                revision_ref=parsed.revision_ref,
                parser_version=parsed.parser_version,
                chunks=result.chunks,
            )
        )
        match = _LESSON_PATTERN.search(relative)
        if match:
            number = int(match.group(1))
            lesson_id = f"lesson-{number}"
            existing = lessons.get(lesson_id)
            if existing is None or (existing.title is None and parsed.title is not None):
                lessons[lesson_id] = LessonImport(
                    lesson_id=lesson_id, lesson_number=number, title=parsed.title
                )
    plan["lessons"].extend(lessons.values())


def _verification_basis(raw: dict[str, Any]) -> tuple[str, ...]:
    value = raw.get("verificationBasis")
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, str) and value:
        return (value,)
    return ()


def _collect_cases(
    sources: SourcesConfig, repository: str, plan: dict[str, Any]
) -> list[ClassCaseMapping]:
    settings = sources.class_cases
    if not settings.enabled:
        return []
    if settings.root is None:
        raise ValueError("class_cases.root is not configured")
    root = settings.root.expanduser()
    mappings: list[ClassCaseMapping] = []
    for path in _glob(root, settings.include_globs, []):
        relative = path.relative_to(root).as_posix()
        mapping = map_class_case_file(path, repository=repository, source_root=root)
        mappings.append(mapping)
        json_document_id = make_document_id("classroom_case", repository, relative)
        plan["documents"].append(
            DocumentImport(
                document_id=json_document_id,
                source_type="classroom_case",
                source_uri=mapping.source_uri,
                trust_level="classroom",
                revision_id=make_revision_id(json_document_id, mapping.content_hash),
                content_hash=mapping.content_hash,
                parser_version=mapping.parser_version,
                chunker_version=None,
                chunks=(),
            )
        )
        markdown_document_id: str | None = None
        paired = mapping.paired_markdown
        if paired is not None and paired.exists:
            md_mapping = map_class_case_markdown_file(mapping, source_root=root)
            parsed = md_mapping.document
            markdown_document_id = make_document_id("markdown", repository, paired.relative_path)
            result = chunk_document(parsed, document_id=markdown_document_id)
            plan["documents"].append(
                _markdown_document(
                    document_id=markdown_document_id,
                    source_uri=md_mapping.source_uri,
                    trust_level="classroom",
                    content_hash=md_mapping.content_hash,
                    revision_ref=parsed.revision_ref,
                    parser_version=md_mapping.parser_version,
                    chunks=result.chunks,
                )
            )
        elif paired is not None and paired.exists is False:
            plan["skipped"].append(
                f"class case {mapping.case_id}: paired markdown missing at "
                f"{paired.relative_path}; JSON representation imported only"
            )
        raw = mapping.model_dump()["raw"]
        plan["cases"].append(
            ClassCaseImport(
                case_id=mapping.case_id,
                lesson_id=mapping.lesson_id,
                match_status=mapping.match_status.value if mapping.match_status else None,
                match_status_raw=mapping.match_status_raw,
                verification_basis=_verification_basis(raw),
                case_memo=raw.get("caseMemo") if isinstance(raw.get("caseMemo"), str) else None,
                json_document_id=json_document_id,
                markdown_document_id=markdown_document_id,
            )
        )
    return mappings


def _collect_daily(sources: SourcesConfig, repository: str, plan: dict[str, Any]) -> list[Any]:
    settings = sources.daily_records
    if not settings.include:
        return []
    if settings.root is None:
        raise ValueError("daily_records.root is not configured")
    root = settings.root.expanduser()
    record_mappings: list[Any] = []
    containers = sorted({entry.path for entry in settings.allowed_records})
    for relative in containers:
        result = map_daily_records_file(
            root / relative, repository=repository, source_root=root, settings=settings
        )
        if not result.processed:
            continue
        for record in result.records:
            record_mappings.append(record)
            raw = record.model_dump()["raw"]
            plan["records"].append(
                CastRecordImport(
                    record_id=record.record_id,
                    record_type=str(raw.get("recordType") or "additional_question"),
                    date=raw.get("date") if isinstance(raw.get("date"), str) else None,
                    question=raw.get("question") if isinstance(raw.get("question"), str) else None,
                    casting_json=json.dumps(raw, ensure_ascii=False, sort_keys=True),
                    container_path=relative,
                    json_pointer=record.locator.json_pointer,
                )
            )
            container_stem = Path(relative).stem
            md_relative = (
                f"{Path(relative).parent.as_posix()}/markdown/"
                f"{container_stem}--{record.record_id}.md"
            )
            if (root / md_relative).is_file():
                # Container verification (M2-C2): the Markdown's
                # record must be one of the CastRecords the C1
                # mapper actually mapped for this container under
                # the same allowlist — an identity-level check tying
                # the rendering to the accepted container mapping.
                # It is not a full content-equality proof between
                # the embedded JSON and the container subrecord; the
                # M2 mapper offers no such comparison.
                md_mapping = map_generated_markdown_file(
                    root / md_relative,
                    repository=repository,
                    source_root=root,
                    container_path=relative,
                    settings=settings,
                )
                document_id = make_document_id("markdown", repository, md_relative)
                plan["documents"].append(
                    DocumentImport(
                        document_id=document_id,
                        source_type="markdown",
                        source_uri=md_mapping.source_uri,
                        trust_level="personal",
                        revision_id=make_revision_id(document_id, md_mapping.content_hash),
                        content_hash=md_mapping.content_hash,
                        parser_version=md_mapping.parser_version,
                        chunker_version=None,
                        chunks=(),
                    )
                )
                plan["renders_links"].append((record.record_id, document_id))
            else:
                plan["skipped"].append(
                    f"daily record {record.record_id}: generated markdown not found at "
                    f"{md_relative}; record imported without RENDERS"
                )
    return record_mappings


def _resolve_references(plan: dict[str, Any], specs: tuple[CaseReferenceSpec, ...]) -> None:
    documents = {document.document_id: document for document in plan["documents"]}
    resolved: dict[str, tuple[CaseReferenceImport, ...]] = {}
    for spec in specs:
        notes = documents.get(spec.notes_document_id)
        if notes is None:
            plan["skipped"].append(
                f"case {spec.case_id}: notes document {spec.notes_document_id} is not "
                "part of this plan; references skipped"
            )
            continue
        chosen: dict[str, str] = {}
        for prefix, role in spec.sections:
            for chunk in notes.chunks:
                if any(heading.startswith(prefix) for heading in chunk.heading_path):
                    chosen.setdefault(chunk.chunk_id, role)
        if chosen:
            resolved[spec.case_id] = tuple(
                CaseReferenceImport(chunk_id=chunk_id, role=role)
                for chunk_id, role in chosen.items()
            )
        else:
            plan["skipped"].append(
                f"case {spec.case_id}: no chunks matched the assigned notes sections; "
                "references skipped (nothing is fabricated)"
            )
    plan["references"] = tuple(resolved.items())


def collect_plan(
    sources: SourcesConfig,
    *,
    repository: str,
    reference_specs: tuple[CaseReferenceSpec, ...] = (),
) -> IngestPlan:
    """Build the import plan for one allowlist configuration.

    ``repository`` is the explicit ``owner/name`` slug every M2
    file-level API requires; it is a parameter, not a config field,
    matching how the mappers themselves take it.

    REFERENCES assignments come from the sources configuration
    (``case_references``, the reviewable entry the CLI uses);
    ``reference_specs`` passed by a caller override the configured
    assignment for the same case_id. Nothing is inferred.
    """
    plan: dict[str, Any] = {
        "documents": [],
        "lessons": [],
        "cases": [],
        "records": [],
        "record_links": [],
        "renders_links": [],
        "references": (),
        "skipped": [],
    }
    _collect_notes(sources, repository, plan)
    case_mappings = _collect_cases(sources, repository, plan)
    record_mappings = _collect_daily(sources, repository, plan)
    if case_mappings and record_mappings:
        imported_ids = {record.record_id for record in plan["records"]}
        for linked in link_daily_records(case_mappings, record_mappings):
            if linked.linked_record_id is not None and linked.linked_record_id in imported_ids:
                plan["record_links"].append((linked.case_id, linked.linked_record_id))
    if sources.raw_asr.enabled:
        plan["skipped"].append(
            "raw_asr: ASR content is never imported by the M4b pipeline "
            "(metadata-only track); nothing was read or chunked"
        )
    if sources.pdf.enabled:
        plan["skipped"].append("pdf: PDF import is deferred; nothing was imported")
    if sources.external_projects:
        plan["skipped"].append(
            "external_projects: Reference Package intake is M6 and deferred; nothing was imported"
        )
    specs_by_case: dict[str, CaseReferenceSpec] = {}
    for entry in sources.case_references:
        specs_by_case[entry.case_id] = CaseReferenceSpec(
            case_id=entry.case_id,
            notes_document_id=make_document_id("markdown", repository, entry.notes_path),
            sections=tuple((section.heading_prefix, section.role) for section in entry.sections),
        )
    for spec in reference_specs:
        specs_by_case[spec.case_id] = spec
    _resolve_references(plan, tuple(specs_by_case.values()))
    return IngestPlan(**plan)


# ---------------------------------------------------------------------------
# Plan execution
# ---------------------------------------------------------------------------


def run_plan(session: ImporterSession, plan: IngestPlan) -> IngestReport:
    """Execute one plan; per-item failures are reported, never hidden."""
    importer = Neo4jImporter(session)
    failures: list[IngestFailure] = []
    documents: list[DocumentImportResult] = []
    record_results: list[CastRecordImportResult] = []
    lessons_imported = 0
    cases_imported = 0
    records_imported = 0
    record_links = 0
    renders_links = 0
    references_written = 0

    failed = object()

    def attempt(item: str, action: Any) -> Any:
        try:
            return action()
        except Exception as exc:
            failures.append(IngestFailure(item=item, error=f"{type(exc).__name__}: {exc}"))
            return failed

    for lesson in plan.lessons:
        if (
            attempt(f"lesson {lesson.lesson_id}", partial(importer.import_lesson, lesson))
            is not failed
        ):
            lessons_imported += 1
    for document in plan.documents:
        result = attempt(
            f"document {document.document_id}",
            partial(importer.import_document, document),
        )
        if result is not failed:
            documents.append(result)
    for record in plan.records:
        record_result = attempt(
            f"record {record.record_id}", partial(importer.import_cast_record, record)
        )
        if record_result is not failed:
            record_results.append(record_result)
            records_imported += 1
    for case in plan.cases:
        if attempt(f"case {case.case_id}", partial(importer.import_class_case, case)) is not failed:
            cases_imported += 1
    for case_id, record_id in plan.record_links:
        linked = attempt(
            f"based_on_record {case_id} -> {record_id}",
            partial(importer.link_case_record, case_id, record_id),
        )
        if linked:
            record_links += 1
    for record_id, document_id in plan.renders_links:
        linked = attempt(
            f"renders {record_id} -> {document_id}",
            partial(importer.link_record_renders, record_id, document_id),
        )
        if linked:
            renders_links += 1
    for case_id, references in plan.references:
        written = attempt(
            f"references {case_id}",
            partial(importer.import_case_references, case_id, references),
        )
        if written:
            references_written += int(written)

    return IngestReport(
        documents=tuple(documents),
        records=tuple(record_results),
        lessons_imported=lessons_imported,
        cases_imported=cases_imported,
        records_imported=records_imported,
        record_links=record_links,
        renders_links=renders_links,
        references_written=references_written,
        failures=tuple(failures),
    )
