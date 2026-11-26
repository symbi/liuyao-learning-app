"""Neo4j importer and incremental sync (Phase 1 M4b).

The importer persists what the M2 adapters/mappers produce and the
M4a chunker cuts, following the M3 schema catalog and the identity /
locator layering frozen in PR #18:

* Nodes carry only the properties listed in
  :data:`liuyao_kb.neo4j.schema.NODE_SPECS`. The ``Chunk`` node
  stores the stable identity layer only (``chunk_id``, ``text``,
  ``text_hash``); the revision-specific locator
  (``paragraph_ordinal``, ``subchunk_index``, ``heading_path``,
  ``start_offset``, ``end_offset``) lives on the
  ``DocumentRevision -[:CONTAINS]-> Chunk`` relationship, and
  ``revision_id`` is expressed by that relationship's start node —
  never written onto the shared Chunk node, and the legacy catalog
  names ``ordinal`` / ``heading`` / ``page`` are never written to
  the Chunk node either.
* Sync state lives in the graph itself (plan section 8):
  ``SourceDocument.current_revision_id`` plus each
  ``DocumentRevision``'s ``content_hash`` / ``parser_version`` /
  ``chunker_version`` / ``status``. There is no local sync database
  and no Import Manifest; result DTOs are in-memory reports only.

Incremental rules:

* A revision whose stored hash, parser version and chunker version
  all match the import is *unchanged*: no write transaction runs.
* New content creates a new ``DocumentRevision``; historical
  revisions and their CONTAINS relationships are kept.
  ``current_revision_id`` moves only as the last statement of the
  same write transaction that writes the revision, its chunks and
  its CONTAINS set, so a failed import can never leave the pointer
  ahead of the data.
* Same content with a new ``chunker_version`` (or parser version)
  re-cuts only that revision: its CONTAINS relationships are
  deleted and rewritten inside one transaction; other revisions
  are untouched, and Chunk nodes are never deleted (a chunk may be
  shared with other revisions).
* Chunk identity is content-addressed: if a ``chunk_id`` already
  exists with different text or an inconsistent ``text_hash``, the
  import raises :class:`ChunkConflictError` and the transaction
  rolls back. Existing chunk text is never silently overwritten.

The importer talks to a minimal session protocol
(``execute_read`` / ``execute_write`` with transaction functions),
which the real ``neo4j.Session`` satisfies and tests fake in
memory. It never builds a driver or reads credentials itself.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from liuyao_kb.chunking import Chunk

#: DocumentRevision.status value once a revision's document,
#: chunks and CONTAINS set have been fully written.
REVISION_STATUS_IMPORTED = "imported"


class ImporterError(RuntimeError):
    """An import could not be completed safely."""


class ChunkConflictError(ImporterError):
    """A chunk_id already exists with different text or hash.

    The message carries only the chunk_id and hashes — never chunk
    text — so it is safe to print in CLI output and logs.
    """


class TxLike(Protocol):
    """The part of a Neo4j transaction this module consumes."""

    def run(self, query: str, **parameters: Any) -> Any: ...


class ImporterSession(Protocol):
    """The part of a Neo4j session this module consumes."""

    def execute_read(self, transaction_function: Any, *args: Any, **kwargs: Any) -> Any: ...

    def execute_write(self, transaction_function: Any, *args: Any, **kwargs: Any) -> Any: ...


# ---------------------------------------------------------------------------
# Import DTOs
# ---------------------------------------------------------------------------


class DocumentImport(BaseModel):
    """One document revision ready to persist.

    ``chunks`` are M4a occurrence DTOs; the importer splits their
    identity layer (Chunk node) from their locator layer (CONTAINS
    properties) at write time. Unchunked documents (class-case
    JSON, daily generated Markdown by default) carry no chunks and
    a ``chunker_version`` of None.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    trust_level: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    content_hash: str
    revision_ref: str | None = None
    parser_version: str = Field(min_length=1)
    chunker_version: str | None = None
    chunks: tuple[Chunk, ...] = ()

    @model_validator(mode="after")
    def _chunks_belong_to_this_revision(self) -> DocumentImport:
        if self.chunker_version is None and self.chunks:
            raise ValueError("an unchunked document (chunker_version=None) cannot carry chunks")
        for chunk in self.chunks:
            if chunk.document_id != self.document_id:
                raise ValueError(
                    f"chunk {chunk.chunk_id} belongs to document {chunk.document_id}, "
                    f"not {self.document_id}"
                )
            if chunk.revision_id is not None and chunk.revision_id != self.revision_id:
                raise ValueError(
                    f"chunk {chunk.chunk_id} belongs to revision {chunk.revision_id}, "
                    f"not {self.revision_id}"
                )
            if chunk.chunker_version != self.chunker_version:
                raise ValueError(
                    f"chunk {chunk.chunk_id} was cut by {chunk.chunker_version}, "
                    f"not {self.chunker_version}"
                )
        return self


class LessonImport(BaseModel):
    """One Lesson node (identity plus whatever metadata is known)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lesson_id: str = Field(min_length=1)
    lesson_number: int | None = None
    title: str | None = None


class ClassCaseImport(BaseModel):
    """One ClassCase plus its representation links.

    ``match_status`` is the normalized status (for example the
    legacy ``matched`` arrives here as ``verified``);
    ``match_status_raw`` preserves the original spelling and is
    stored as provenance on the JSON HAS_REPRESENTATION
    relationship, never silently dropped.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    lesson_id: str | None = None
    match_status: str | None = None
    match_status_raw: str | None = None
    verification_basis: tuple[str, ...] = ()
    case_memo: str | None = None
    json_document_id: str = Field(min_length=1)
    markdown_document_id: str | None = None


class CastRecordImport(BaseModel):
    """One allowlisted daily-record subrecord as a CastRecord.

    ``container_path`` and ``json_pointer`` are the record's
    provenance (which container file, which subrecord). The M3
    node catalog fixes CastRecord's properties, so provenance is
    carried on this DTO and the import report rather than as extra
    node properties; the record's generated Markdown, when
    imported, anchors the file level in the graph via RENDERS.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str = Field(min_length=1)
    record_type: str = Field(min_length=1)
    date: str | None = None
    question: str | None = None
    #: The subrecord's complete JSON payload as a canonical string
    #: (plan section 7: nested Liuyao JSON is stored as a string).
    casting_json: str = Field(min_length=1)
    container_path: str = Field(min_length=1)
    json_pointer: str = ""


class CaseReferenceImport(BaseModel):
    """One ClassCase -[:REFERENCES]-> Chunk link."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(min_length=1)
    #: "primary" for the case's main notes section, "secondary" for
    #: supporting mentions such as a summary-table row's block.
    role: str = Field(min_length=1)


class ImportOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class DocumentImportResult(BaseModel):
    """What one document import did (in-memory report, not state)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    revision_id: str
    outcome: ImportOutcome
    chunks: int = 0
    contains: int = 0


class CastRecordImportResult(BaseModel):
    """What one CastRecord import did, with its source provenance.

    The provenance fields (container path + JSON pointer) are the
    audit trail the report can offer without body text: which
    container file and which subrecord the CastRecord came from.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str
    container_path: str
    json_pointer: str
    outcome: ImportOutcome


# ---------------------------------------------------------------------------
# Cypher (fixed statement set; the test fake dispatches on these)
# ---------------------------------------------------------------------------

Q_READ_DOCUMENT_STATE = """
MATCH (d:SourceDocument {document_id: $document_id})
OPTIONAL MATCH (d)-[:HAS_REVISION]->(r:DocumentRevision {revision_id: $revision_id})
RETURN d.current_revision_id AS current_revision_id,
       r.content_hash AS content_hash,
       r.parser_version AS parser_version,
       r.chunker_version AS chunker_version,
       r.status AS status
"""

Q_FIND_CHUNKS = """
MATCH (c:Chunk) WHERE c.chunk_id IN $chunk_ids
RETURN c.chunk_id AS chunk_id, c.text AS text, c.text_hash AS text_hash
"""

Q_MERGE_DOCUMENT = """
MERGE (d:SourceDocument {document_id: $document_id})
SET d.source_type = $source_type,
    d.source_uri = $source_uri,
    d.trust_level = $trust_level
"""

Q_MERGE_REVISION = """
MATCH (d:SourceDocument {document_id: $document_id})
MERGE (r:DocumentRevision {revision_id: $revision_id})
SET r.content_hash = $content_hash,
    r.revision_ref = $revision_ref,
    r.parser_version = $parser_version,
    r.chunker_version = $chunker_version,
    r.status = $status
MERGE (d)-[:HAS_REVISION]->(r)
"""

Q_MERGE_CHUNKS = """
UNWIND $chunks AS chunk
MERGE (c:Chunk {chunk_id: chunk.chunk_id})
ON CREATE SET c.text = chunk.text, c.text_hash = chunk.text_hash
"""

Q_DELETE_CONTAINS = """
MATCH (r:DocumentRevision {revision_id: $revision_id})-[rel:CONTAINS]->(:Chunk)
DELETE rel
"""

Q_MERGE_CONTAINS = """
UNWIND $contains AS item
MATCH (r:DocumentRevision {revision_id: $revision_id})
MATCH (c:Chunk {chunk_id: item.chunk_id})
MERGE (r)-[rel:CONTAINS]->(c)
SET rel.paragraph_ordinal = item.paragraph_ordinal,
    rel.subchunk_index = item.subchunk_index,
    rel.heading_path = item.heading_path,
    rel.start_offset = item.start_offset,
    rel.end_offset = item.end_offset
"""

Q_SET_CURRENT_REVISION = """
MATCH (d:SourceDocument {document_id: $document_id})
SET d.current_revision_id = $revision_id
"""

Q_MERGE_LESSON = """
MERGE (l:Lesson {lesson_id: $lesson_id})
SET l.lesson_number = $lesson_number, l.title = $title
"""

Q_MERGE_CASE = """
MERGE (k:ClassCase {case_id: $case_id})
SET k.lesson_id = $lesson_id,
    k.match_status = $match_status,
    k.verification_basis = $verification_basis,
    k.case_memo = $case_memo
"""

Q_MERGE_HAS_REPRESENTATION = """
MATCH (k:ClassCase {case_id: $case_id})
MATCH (d:SourceDocument {document_id: $document_id})
MERGE (k)-[rel:HAS_REPRESENTATION]->(d)
SET rel.format = $format, rel.match_status_raw = $match_status_raw
"""

Q_MERGE_TAUGHT_IN = """
MATCH (k:ClassCase {case_id: $case_id})
MATCH (l:Lesson {lesson_id: $lesson_id})
MERGE (k)-[:TAUGHT_IN]->(l)
RETURN l.lesson_id AS lesson_id
"""

Q_READ_CAST_RECORD = """
MATCH (rec:CastRecord {record_id: $record_id})
RETURN rec.record_type AS record_type,
       rec.date AS date,
       rec.question AS question,
       rec.casting_json AS casting_json
"""

Q_MERGE_CAST_RECORD = """
MERGE (rec:CastRecord {record_id: $record_id})
SET rec.record_type = $record_type,
    rec.date = $date,
    rec.question = $question,
    rec.casting_json = $casting_json
"""

Q_CASE_REPRESENTATION_DOCS = """
MATCH (k:ClassCase {case_id: $case_id})-[:HAS_REPRESENTATION]->(d:SourceDocument)
RETURN d.document_id AS document_id
"""

Q_LINK_BASED_ON_RECORD = """
MATCH (k:ClassCase {case_id: $case_id})
MATCH (rec:CastRecord {record_id: $record_id})
MERGE (k)-[:BASED_ON_RECORD]->(rec)
RETURN k.case_id AS case_id
"""

Q_LINK_RENDERS = """
MATCH (rec:CastRecord {record_id: $record_id})
MATCH (d:SourceDocument {document_id: $document_id})
MERGE (rec)-[:RENDERS]->(d)
RETURN rec.record_id AS record_id
"""

Q_MERGE_REFERENCES = """
UNWIND $refs AS ref
MATCH (k:ClassCase {case_id: $case_id})
MATCH (c:Chunk {chunk_id: ref.chunk_id})
MERGE (k)-[rel:REFERENCES]->(c)
SET rel.role = ref.role
RETURN count(rel) AS written
"""


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------


def _check_chunk_conflicts(tx: TxLike, chunks: tuple[Chunk, ...]) -> None:
    """Raise ChunkConflictError if any chunk_id is taken by other text."""
    if not chunks:
        return
    rows = tx.run(Q_FIND_CHUNKS, chunk_ids=[c.chunk_id for c in chunks])
    existing = {row["chunk_id"]: row for row in rows}
    for chunk in chunks:
        row = existing.get(chunk.chunk_id)
        if row is None:
            continue
        if row["text"] != chunk.text or row["text_hash"] != chunk.text_hash:
            raise ChunkConflictError(
                f"chunk_id {chunk.chunk_id} already exists with different content "
                f"(stored text_hash={row['text_hash']}, incoming text_hash={chunk.text_hash}); "
                "refusing to overwrite an existing Chunk node"
            )


def _write_chunks_and_contains(tx: TxLike, document: DocumentImport) -> None:
    if document.chunks:
        tx.run(
            Q_MERGE_CHUNKS,
            chunks=[
                {"chunk_id": c.chunk_id, "text": c.text, "text_hash": c.text_hash}
                for c in document.chunks
            ],
        )
        tx.run(
            Q_MERGE_CONTAINS,
            revision_id=document.revision_id,
            contains=[
                {
                    "chunk_id": c.chunk_id,
                    "paragraph_ordinal": c.paragraph_ordinal,
                    "subchunk_index": c.subchunk_index,
                    "heading_path": list(c.heading_path),
                    "start_offset": c.start_offset,
                    "end_offset": c.end_offset,
                }
                for c in document.chunks
            ],
        )


class Neo4jImporter:
    """Idempotent, incremental persistence over one Neo4j session."""

    def __init__(self, session: ImporterSession) -> None:
        self._session = session

    # -- documents ----------------------------------------------------

    def import_document(self, document: DocumentImport) -> DocumentImportResult:
        state = self._session.execute_read(self._read_state, document)

        if state is not None and state["content_hash"] is not None:
            if state["content_hash"] != document.content_hash:
                raise ImporterError(
                    f"revision {document.revision_id} already exists with a different "
                    "content_hash; revision ids are content-derived, so this indicates "
                    "corrupted state and the import is refused"
                )
            same_versions = (
                state["parser_version"] == document.parser_version
                and state["chunker_version"] == document.chunker_version
            )
            if same_versions and state["status"] == REVISION_STATUS_IMPORTED:
                return DocumentImportResult(
                    document_id=document.document_id,
                    revision_id=document.revision_id,
                    outcome=ImportOutcome.UNCHANGED,
                    chunks=len(document.chunks),
                    contains=len(document.chunks),
                )
            # Same content, new parser/chunker version: re-cut only
            # this revision's CONTAINS set, in one transaction. The
            # current pointer moves only when this revision already
            # is the current one (or none is set): re-cutting a
            # historical revision must not move the pointer back.
            move_pointer = state["current_revision_id"] in (None, document.revision_id)
            self._session.execute_write(self._rewrite_revision, document, True, move_pointer)
            return DocumentImportResult(
                document_id=document.document_id,
                revision_id=document.revision_id,
                outcome=ImportOutcome.UPDATED,
                chunks=len(document.chunks),
                contains=len(document.chunks),
            )

        existed = state is not None
        self._session.execute_write(self._rewrite_revision, document, False, True)
        return DocumentImportResult(
            document_id=document.document_id,
            revision_id=document.revision_id,
            outcome=ImportOutcome.UPDATED if existed else ImportOutcome.CREATED,
            chunks=len(document.chunks),
            contains=len(document.chunks),
        )

    @staticmethod
    def _read_state(tx: TxLike, document: DocumentImport) -> dict[str, Any] | None:
        rows = list(
            tx.run(
                Q_READ_DOCUMENT_STATE,
                document_id=document.document_id,
                revision_id=document.revision_id,
            )
        )
        if not rows:
            return None
        return dict(rows[0].data())

    @staticmethod
    def _rewrite_revision(
        tx: TxLike, document: DocumentImport, recut: bool, move_pointer: bool
    ) -> None:
        # Conflict check first: a conflict must abort before any write.
        _check_chunk_conflicts(tx, document.chunks)
        tx.run(
            Q_MERGE_DOCUMENT,
            document_id=document.document_id,
            source_type=document.source_type,
            source_uri=document.source_uri,
            trust_level=document.trust_level,
        )
        tx.run(
            Q_MERGE_REVISION,
            document_id=document.document_id,
            revision_id=document.revision_id,
            content_hash=document.content_hash,
            revision_ref=document.revision_ref,
            parser_version=document.parser_version,
            chunker_version=document.chunker_version,
            status=REVISION_STATUS_IMPORTED,
        )
        if recut:
            tx.run(Q_DELETE_CONTAINS, revision_id=document.revision_id)
        _write_chunks_and_contains(tx, document)
        if move_pointer:
            # The pointer moves last, inside the same transaction.
            tx.run(
                Q_SET_CURRENT_REVISION,
                document_id=document.document_id,
                revision_id=document.revision_id,
            )

    # -- lessons, cases, records --------------------------------------

    def import_lesson(self, lesson: LessonImport) -> None:
        def work(tx: TxLike) -> None:
            tx.run(
                Q_MERGE_LESSON,
                lesson_id=lesson.lesson_id,
                lesson_number=lesson.lesson_number,
                title=lesson.title,
            )

        self._session.execute_write(work)

    def import_class_case(self, case: ClassCaseImport) -> None:
        def work(tx: TxLike) -> None:
            tx.run(
                Q_MERGE_CASE,
                case_id=case.case_id,
                lesson_id=case.lesson_id,
                match_status=case.match_status,
                verification_basis=list(case.verification_basis) or None,
                case_memo=case.case_memo,
            )
            tx.run(
                Q_MERGE_HAS_REPRESENTATION,
                case_id=case.case_id,
                document_id=case.json_document_id,
                format="json",
                match_status_raw=case.match_status_raw,
            )
            if case.markdown_document_id is not None:
                tx.run(
                    Q_MERGE_HAS_REPRESENTATION,
                    case_id=case.case_id,
                    document_id=case.markdown_document_id,
                    format="markdown",
                    match_status_raw=None,
                )
            if case.lesson_id is not None:
                # MATCH-only on both endpoints: a Lesson is created
                # exclusively by import_lesson. If it was not
                # imported first, the statement matches nothing and
                # the case import fails and rolls back — an
                # identity-only placeholder Lesson is never created.
                taught_rows = list(
                    tx.run(Q_MERGE_TAUGHT_IN, case_id=case.case_id, lesson_id=case.lesson_id)
                )
                if not taught_rows:
                    raise ImporterError(
                        f"case {case.case_id}: TAUGHT_IN cannot be created: "
                        f"lesson {case.lesson_id} is not imported; the case "
                        "import is rolled back"
                    )
            # MATCH-based writes fail silently when an endpoint is
            # absent, so verify inside the same transaction: a
            # missing representation document (for example because
            # its own import failed earlier) must fail the whole
            # case import and roll back, never half-link the case.
            found = {
                row["document_id"]
                for row in tx.run(Q_CASE_REPRESENTATION_DOCS, case_id=case.case_id)
            }
            expected = {case.json_document_id}
            if case.markdown_document_id is not None:
                expected.add(case.markdown_document_id)
            missing = expected - found
            if missing:
                raise ImporterError(
                    f"case {case.case_id}: HAS_REPRESENTATION target document(s) "
                    f"not imported: {', '.join(sorted(missing))}; the case import "
                    "is rolled back"
                )

        self._session.execute_write(work)

    def import_cast_record(self, record: CastRecordImport) -> CastRecordImportResult:
        """Create or update one CastRecord, reporting what happened.

        The current content is replaced when the subrecord changed
        (outcome ``updated``); an identical record is ``unchanged``
        and performs no write. The frozen M3 catalog gives
        CastRecord no revision/audit properties and the container
        is not a SourceDocument, so prior record content is *not*
        retained in the graph — that history gap is a documented,
        deferred schema-design item (plan section 8), not something
        this importer silently pretends to solve. The per-run
        report carries the outcome plus provenance (container path,
        JSON pointer) without body text.
        """

        def read(tx: TxLike) -> dict[str, Any] | None:
            rows = list(tx.run(Q_READ_CAST_RECORD, record_id=record.record_id))
            return dict(rows[0].data()) if rows else None

        existing = self._session.execute_read(read)
        if existing is not None and (
            existing["record_type"] == record.record_type
            and existing["date"] == record.date
            and existing["question"] == record.question
            and existing["casting_json"] == record.casting_json
        ):
            return CastRecordImportResult(
                record_id=record.record_id,
                container_path=record.container_path,
                json_pointer=record.json_pointer,
                outcome=ImportOutcome.UNCHANGED,
            )

        def work(tx: TxLike) -> None:
            tx.run(
                Q_MERGE_CAST_RECORD,
                record_id=record.record_id,
                record_type=record.record_type,
                date=record.date,
                question=record.question,
                casting_json=record.casting_json,
            )

        self._session.execute_write(work)
        return CastRecordImportResult(
            record_id=record.record_id,
            container_path=record.container_path,
            json_pointer=record.json_pointer,
            outcome=ImportOutcome.UPDATED if existing is not None else ImportOutcome.CREATED,
        )

    def link_case_record(self, case_id: str, record_id: str) -> bool:
        """Create BASED_ON_RECORD; a missing endpoint is an error.

        Callers must only pass links already established by exact
        recordId matching (M2 ``link_daily_records``) against records
        that were actually imported. If either endpoint is absent
        the plan asked for a link that cannot exist, so this raises
        :class:`ImporterError` instead of silently skipping it.
        """

        def work(tx: TxLike) -> bool:
            rows = list(tx.run(Q_LINK_BASED_ON_RECORD, case_id=case_id, record_id=record_id))
            if not rows:
                raise ImporterError(
                    f"BASED_ON_RECORD cannot be created: case {case_id} or "
                    f"record {record_id} is not imported"
                )
            return True

        return bool(self._session.execute_write(work))

    def link_record_renders(self, record_id: str, document_id: str) -> bool:
        """Create CastRecord -[:RENDERS]-> SourceDocument (generated MD).

        A missing endpoint raises :class:`ImporterError`, for the
        same reason as :meth:`link_case_record`.
        """

        def work(tx: TxLike) -> bool:
            rows = list(tx.run(Q_LINK_RENDERS, record_id=record_id, document_id=document_id))
            if not rows:
                raise ImporterError(
                    f"RENDERS cannot be created: record {record_id} or "
                    f"document {document_id} is not imported"
                )
            return True

        return bool(self._session.execute_write(work))

    def import_case_references(
        self, case_id: str, references: tuple[CaseReferenceImport, ...]
    ) -> int:
        """Create REFERENCES links to already-imported chunks.

        Fails loudly when a referenced chunk does not exist: a
        reference must never be silently dropped or fabricated.
        """
        if not references:
            return 0

        def work(tx: TxLike) -> int:
            rows = list(
                tx.run(
                    Q_MERGE_REFERENCES,
                    case_id=case_id,
                    refs=[{"chunk_id": ref.chunk_id, "role": ref.role} for ref in references],
                )
            )
            written = rows[0]["written"] if rows else 0
            if written != len(references):
                raise ImporterError(
                    f"case {case_id}: only {written} of {len(references)} referenced "
                    "chunks exist; references are written only to imported chunks"
                )
            return int(written)

        return int(self._session.execute_write(work))
