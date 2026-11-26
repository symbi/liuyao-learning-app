"""Tests for the M4b Neo4j importer against the in-memory fake.

All fixtures are synthetic. Assertions are on the fake graph's
resulting state — node/relationship properties, counts and
idempotency — never on call counts alone.
"""

from __future__ import annotations

import pytest

from fake_neo4j import FakeGraph, FakeSession
from liuyao_kb.chunking import CHUNKER_VERSION, Chunk, chunk_document
from liuyao_kb.ids import make_chunk_id, make_document_id, make_revision_id
from liuyao_kb.neo4j.importer import (
    CaseReferenceImport,
    CastRecordImport,
    ChunkConflictError,
    ClassCaseImport,
    DocumentImport,
    ImporterError,
    ImportOutcome,
    LessonImport,
    Neo4jImporter,
)
from liuyao_kb.sources.adapters import MarkdownAdapter

REPO = "symbi/liuyao-learning-app"
NOTES_PATH = "docs/lessons/lesson-99-notes.md"
NOTES_URI = f"repo://{REPO}/{NOTES_PATH}"
DOC_ID = make_document_id("markdown", REPO, NOTES_PATH)

TEXT_V1 = (
    "# Lesson 99\n\n## 1. First section\n\nAlpha paragraph stays.\n\nBeta paragraph changes.\n"
)
TEXT_V2 = (
    "# Lesson 99\n\n## 1. First section\n\nAlpha paragraph stays.\n\nBeta paragraph changed!\n"
)


def _document(text: str, path: str = NOTES_PATH) -> DocumentImport:
    uri = f"repo://{REPO}/{path}"
    document_id = make_document_id("markdown", REPO, path)
    parsed = MarkdownAdapter().parse_text(text, source_uri=uri)
    result = chunk_document(parsed, document_id=document_id)
    return DocumentImport(
        document_id=document_id,
        source_type="markdown",
        source_uri=uri,
        trust_level="primary",
        revision_id=make_revision_id(document_id, parsed.content_hash),
        content_hash=parsed.content_hash,
        parser_version=parsed.parser_version,
        chunker_version=CHUNKER_VERSION,
        chunks=result.chunks,
    )


def _contains_key(rel: dict) -> tuple:  # type: ignore[type-arg]
    """Hashable snapshot of one CONTAINS relationship for comparison."""
    props = tuple(
        sorted(
            (key, tuple(value) if isinstance(value, list) else value)
            for key, value in rel["props"].items()
        )
    )
    return (rel["to"], props)


def _recut(document: DocumentImport, version: str) -> DocumentImport:
    """Simulate the same segmentation produced by a future chunker."""
    chunks = tuple(
        chunk.model_copy(
            update={
                "chunker_version": version,
                "chunk_id": make_chunk_id(
                    document.document_id,
                    version,
                    chunk.paragraph_ordinal,
                    chunk.subchunk_index,
                    chunk.text_hash,
                ),
            }
        )
        for chunk in document.chunks
    )
    return document.model_copy(update={"chunker_version": version, "chunks": chunks})


class TestDocumentImport:
    def test_first_import_creates_full_structure(self) -> None:
        session = FakeSession()
        document = _document(TEXT_V1)
        result = Neo4jImporter(session).import_document(document)

        assert result.outcome is ImportOutcome.CREATED
        graph = session.graph
        doc_node = graph.node("SourceDocument", DOC_ID)
        assert doc_node is not None
        assert doc_node["source_type"] == "markdown"
        assert doc_node["trust_level"] == "primary"
        assert doc_node["current_revision_id"] == document.revision_id

        revision = graph.node("DocumentRevision", document.revision_id)
        assert revision is not None
        assert revision["content_hash"] == document.content_hash
        assert revision["chunker_version"] == CHUNKER_VERSION
        assert revision["status"] == "imported"
        assert len(graph.find_rels("HAS_REVISION")) == 1

        assert len(graph.nodes_with_label("Chunk")) == len(document.chunks)
        contains = graph.find_rels("CONTAINS")
        assert len(contains) == len(document.chunks)
        by_chunk = {chunk.chunk_id: chunk for chunk in document.chunks}
        for rel in contains:
            assert rel["from"] == ("DocumentRevision", document.revision_id)
            chunk = by_chunk[rel["to"][1]]
            # The locator lives on the relationship, in full.
            assert rel["props"]["paragraph_ordinal"] == chunk.paragraph_ordinal
            assert rel["props"]["subchunk_index"] == chunk.subchunk_index
            assert rel["props"]["heading_path"] == list(chunk.heading_path)
            assert rel["props"]["start_offset"] == chunk.start_offset
            assert rel["props"]["end_offset"] == chunk.end_offset
            # The Chunk node carries the identity layer only.
            node = graph.node("Chunk", chunk.chunk_id)
            assert node is not None
            assert set(node) == {"chunk_id", "text", "text_hash"}
            assert node["text"] == chunk.text

    def test_second_identical_import_is_unchanged_and_writes_nothing(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        document = _document(TEXT_V1)
        importer.import_document(document)
        counts_before = session.graph.counts()
        writes_before = session.write_calls

        result = importer.import_document(document)

        assert result.outcome is ImportOutcome.UNCHANGED
        assert session.graph.counts() == counts_before
        assert session.write_calls == writes_before  # no write transaction at all

    def test_content_change_creates_new_revision_and_keeps_the_old(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        v1 = _document(TEXT_V1)
        v2 = _document(TEXT_V2)
        assert v1.revision_id != v2.revision_id
        importer.import_document(v1)
        result = importer.import_document(v2)

        assert result.outcome is ImportOutcome.UPDATED
        graph = session.graph
        assert graph.node("DocumentRevision", v1.revision_id) is not None
        assert graph.node("DocumentRevision", v2.revision_id) is not None
        assert graph.node("SourceDocument", DOC_ID)["current_revision_id"] == v2.revision_id
        assert len(graph.find_rels("HAS_REVISION")) == 2
        # Both revisions keep their own CONTAINS sets.
        assert graph.find_rels("CONTAINS", from_key=("DocumentRevision", v1.revision_id))
        assert graph.find_rels("CONTAINS", from_key=("DocumentRevision", v2.revision_id))

    def test_edit_one_paragraph_reuses_unchanged_chunk_nodes(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        v1 = _document(TEXT_V1)
        v2 = _document(TEXT_V2)
        importer.import_document(v1)
        chunks_before = len(session.graph.nodes_with_label("Chunk"))
        importer.import_document(v2)

        alpha_v1 = next(c for c in v1.chunks if c.text.startswith("Alpha"))
        alpha_v2 = next(c for c in v2.chunks if c.text.startswith("Alpha"))
        assert alpha_v1.chunk_id == alpha_v2.chunk_id  # unchanged paragraph, same id
        # Only the changed paragraph added a node.
        assert len(session.graph.nodes_with_label("Chunk")) == chunks_before + 1

    def test_locators_are_independent_per_revision(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        v1 = _document(TEXT_V1)
        # Same paragraphs, renamed heading and an inserted heading
        # line shifting every offset: chunk ids stay, locators move.
        shifted = TEXT_V1.replace("## 1. First section", "## 1. Renamed section")
        shifted = shifted.replace("Alpha paragraph stays.", "Alpha paragraph stays.")
        v2 = _document("## 0. Preamble heading\n\n" + shifted)
        importer.import_document(v1)
        importer.import_document(v2)

        graph = session.graph
        shared = {c.chunk_id for c in v1.chunks} & {c.chunk_id for c in v2.chunks}
        assert shared  # the two body paragraphs are shared chunks
        for chunk_id in shared:
            rel_v1 = graph.find_rels(
                "CONTAINS",
                from_key=("DocumentRevision", v1.revision_id),
                to_key=("Chunk", chunk_id),
            )[0]
            rel_v2 = graph.find_rels(
                "CONTAINS",
                from_key=("DocumentRevision", v2.revision_id),
                to_key=("Chunk", chunk_id),
            )[0]
            assert rel_v1["props"]["heading_path"] != rel_v2["props"]["heading_path"]
            assert rel_v1["props"]["start_offset"] != rel_v2["props"]["start_offset"]
        # Rewriting v2 never touched v1's locator values.
        alpha = next(c for c in v1.chunks if c.text.startswith("Alpha"))
        rel_v1 = graph.find_rels(
            "CONTAINS",
            from_key=("DocumentRevision", v1.revision_id),
            to_key=("Chunk", alpha.chunk_id),
        )[0]
        assert rel_v1["props"]["start_offset"] == alpha.start_offset
        assert rel_v1["props"]["heading_path"] == list(alpha.heading_path)

    def test_new_chunker_version_replaces_only_own_contains(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        document = _document(TEXT_V1)
        bystander = _document(TEXT_V2, path="docs/lessons/lesson-98-notes.md")
        importer.import_document(document)
        importer.import_document(bystander)
        graph = session.graph
        bystander_contains_before = {
            _contains_key(rel)
            for rel in graph.find_rels(
                "CONTAINS", from_key=("DocumentRevision", bystander.revision_id)
            )
        }
        assert bystander_contains_before

        recut = _recut(document, "chunker-2")
        assert recut.revision_id == document.revision_id  # identity ignores chunker version
        result = importer.import_document(recut)

        assert result.outcome is ImportOutcome.UPDATED
        revision = graph.node("DocumentRevision", document.revision_id)
        assert revision is not None and revision["chunker_version"] == "chunker-2"
        own = graph.find_rels("CONTAINS", from_key=("DocumentRevision", document.revision_id))
        assert {rel["to"][1] for rel in own} == {c.chunk_id for c in recut.chunks}
        # Old chunk nodes are kept (they may be shared with other
        # revisions); the document stays current on this revision.
        for chunk in document.chunks:
            assert graph.node("Chunk", chunk.chunk_id) is not None
        assert graph.node("SourceDocument", DOC_ID)["current_revision_id"] == document.revision_id  # type: ignore[index]
        # The bystander document's CONTAINS set is byte-identical.
        bystander_contains_after = {
            _contains_key(rel)
            for rel in graph.find_rels(
                "CONTAINS", from_key=("DocumentRevision", bystander.revision_id)
            )
        }
        assert bystander_contains_before == bystander_contains_after

    def test_chunk_conflict_aborts_and_preserves_existing_chunk(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        document = _document(TEXT_V1)
        importer.import_document(document)
        original = session.graph.node("Chunk", document.chunks[0].chunk_id)
        assert original is not None

        forged_chunk = document.chunks[0].model_copy(update={"text": "Forged other text."})
        forged = document.model_copy(
            update={
                "revision_id": make_revision_id(DOC_ID, "0" * 64),
                "content_hash": "0" * 64,
                "chunks": (forged_chunk,),
            }
        )
        with pytest.raises(ChunkConflictError):
            importer.import_document(forged)

        graph = session.graph
        assert graph.node("Chunk", forged_chunk.chunk_id)["text"] == original["text"]  # type: ignore[index]
        assert graph.node("DocumentRevision", forged.revision_id) is None
        assert graph.node("SourceDocument", DOC_ID)["current_revision_id"] == document.revision_id  # type: ignore[index]

    def test_mid_write_failure_rolls_back_everything(self) -> None:
        graph = FakeGraph()
        session = FakeSession(graph)
        importer = Neo4jImporter(session)
        v1 = _document(TEXT_V1)
        importer.import_document(v1)
        counts_before = graph.counts()

        # Fail on the CONTAINS write of the next import (the 5th
        # statement of its write transaction).
        session.fail_on_write_call = session.write_calls + 5
        v2 = _document(TEXT_V2)
        with pytest.raises(RuntimeError, match="injected write failure"):
            importer.import_document(v2)

        assert graph.counts() == counts_before
        assert graph.node("DocumentRevision", v2.revision_id) is None
        assert graph.node("SourceDocument", DOC_ID)["current_revision_id"] == v1.revision_id  # type: ignore[index]

        session.fail_on_write_call = None
        result = importer.import_document(v2)
        assert result.outcome is ImportOutcome.UPDATED
        assert graph.node("SourceDocument", DOC_ID)["current_revision_id"] == v2.revision_id  # type: ignore[index]

    def test_document_import_rejects_chunks_without_chunker_version(self) -> None:
        document = _document(TEXT_V1)
        with pytest.raises(ValueError, match="unchunked"):
            DocumentImport(
                document_id=document.document_id,
                source_type=document.source_type,
                source_uri=document.source_uri,
                trust_level=document.trust_level,
                revision_id=document.revision_id,
                content_hash=document.content_hash,
                parser_version=document.parser_version,
                chunker_version=None,
                chunks=document.chunks,
            )


def _plain_document(document_id: str, source_type: str = "markdown") -> DocumentImport:
    return DocumentImport(
        document_id=document_id,
        source_type=source_type,
        source_uri=f"repo://{REPO}/x",
        trust_level="classroom",
        revision_id=make_revision_id(document_id, "a" * 64),
        content_hash="a" * 64,
        parser_version="synthetic-1",
        chunker_version=None,
        chunks=(),
    )


class TestCaseRecordAndLinks:
    def _seed_case(self, session: FakeSession) -> tuple[DocumentImport, DocumentImport]:
        importer = Neo4jImporter(session)
        json_doc = _plain_document(
            make_document_id(
                "classroom_case", REPO, "materials/class-cases/lesson-99/case-001.json"
            ),
            "classroom_case",
        )
        md_doc = _plain_document(
            make_document_id(
                "markdown", REPO, "materials/class-cases/lesson-99/case-001-analysis.md"
            )
        )
        importer.import_document(json_doc)
        importer.import_document(md_doc)
        importer.import_lesson(LessonImport(lesson_id="lesson-99", lesson_number=99, title="L99"))
        importer.import_class_case(
            ClassCaseImport(
                case_id="L99-C01-synthetic",
                lesson_id="lesson-99",
                match_status="verified",
                match_status_raw="matched",
                verification_basis=("synthetic basis",),
                json_document_id=json_doc.document_id,
                markdown_document_id=md_doc.document_id,
            )
        )
        return json_doc, md_doc

    def test_one_case_two_representations_and_taught_in(self) -> None:
        session = FakeSession()
        json_doc, md_doc = self._seed_case(session)
        graph = session.graph

        cases = graph.nodes_with_label("ClassCase")
        assert len(cases) == 1
        assert cases[0]["match_status"] == "verified"
        assert cases[0]["verification_basis"] == ["synthetic basis"]

        reps = graph.find_rels("HAS_REPRESENTATION")
        assert len(reps) == 2
        by_target = {rel["to"][1]: rel["props"] for rel in reps}
        assert by_target[json_doc.document_id]["format"] == "json"
        assert by_target[json_doc.document_id]["match_status_raw"] == "matched"
        assert by_target[md_doc.document_id]["format"] == "markdown"
        assert "match_status_raw" not in by_target[md_doc.document_id]

        taught = graph.find_rels("TAUGHT_IN")
        assert len(taught) == 1
        assert taught[0]["from"] == ("ClassCase", "L99-C01-synthetic")
        assert taught[0]["to"] == ("Lesson", "lesson-99")

    def test_record_links_renders_and_idempotent_rerun(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        self._seed_case(session)
        record = CastRecordImport(
            record_id="rec-1",
            record_type="additionalQuestion",
            date="2099-01-01",
            question=None,
            casting_json='{"id": "rec-1"}',
            container_path="daily-records/2099/01/2099-01-01.json",
            json_pointer="/additionalQuestions/0",
        )
        daily_doc = _plain_document(
            make_document_id(
                "markdown", REPO, "daily-records/2099/01/markdown/2099-01-01--rec-1.md"
            )
        )
        importer.import_cast_record(record)
        importer.import_document(daily_doc)
        assert importer.link_case_record("L99-C01-synthetic", "rec-1") is True
        assert importer.link_record_renders("rec-1", daily_doc.document_id) is True
        counts = session.graph.counts()

        # Full rerun: no duplicated nodes or relationships.
        self._seed_case(session)
        importer.import_cast_record(record)
        importer.import_document(daily_doc)
        assert importer.link_case_record("L99-C01-synthetic", "rec-1") is True
        assert importer.link_record_renders("rec-1", daily_doc.document_id) is True
        assert session.graph.counts() == counts

        graph = session.graph
        based = graph.find_rels("BASED_ON_RECORD")
        assert len(based) == 1
        assert based[0]["from"] == ("ClassCase", "L99-C01-synthetic")
        assert based[0]["to"] == ("CastRecord", "rec-1")
        renders = graph.find_rels("RENDERS")
        assert len(renders) == 1
        assert renders[0]["from"] == ("CastRecord", "rec-1")
        assert renders[0]["to"] == ("SourceDocument", daily_doc.document_id)
        node = graph.node("CastRecord", "rec-1")
        assert node is not None and node["record_type"] == "additionalQuestion"

    def test_link_to_missing_record_is_an_error(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        self._seed_case(session)
        with pytest.raises(ImporterError, match="BASED_ON_RECORD cannot be created"):
            importer.link_case_record("L99-C01-synthetic", "no-such-record")
        assert session.graph.find_rels("BASED_ON_RECORD") == []

    def test_renders_to_missing_document_is_an_error(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        importer.import_cast_record(
            CastRecordImport(
                record_id="rec-1",
                record_type="additionalQuestion",
                casting_json='{"id": "rec-1"}',
                container_path="daily-records/2099/01/2099-01-01.json",
            )
        )
        with pytest.raises(ImporterError, match="RENDERS cannot be created"):
            importer.link_record_renders("rec-1", "document_missing")
        assert session.graph.find_rels("RENDERS") == []

    def test_case_import_fails_and_rolls_back_when_representation_missing(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        json_doc = _plain_document(
            make_document_id(
                "classroom_case", REPO, "materials/class-cases/lesson-99/case-001.json"
            ),
            "classroom_case",
        )
        importer.import_document(json_doc)  # the paired MD document is NOT imported
        importer.import_lesson(LessonImport(lesson_id="lesson-99", lesson_number=99, title="L99"))
        with pytest.raises(ImporterError, match="HAS_REPRESENTATION target"):
            importer.import_class_case(
                ClassCaseImport(
                    case_id="L99-C01-synthetic",
                    lesson_id="lesson-99",
                    match_status="verified",
                    json_document_id=json_doc.document_id,
                    markdown_document_id=make_document_id(
                        "markdown", REPO, "materials/class-cases/lesson-99/case-001-analysis.md"
                    ),
                )
            )
        graph = session.graph
        assert graph.node("ClassCase", "L99-C01-synthetic") is None  # rolled back
        assert graph.find_rels("HAS_REPRESENTATION") == []
        assert graph.find_rels("TAUGHT_IN") == []

    def test_case_import_fails_and_rolls_back_when_lesson_missing(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        json_doc = _plain_document(
            make_document_id(
                "classroom_case", REPO, "materials/class-cases/lesson-99/case-001.json"
            ),
            "classroom_case",
        )
        md_doc = _plain_document(
            make_document_id(
                "markdown", REPO, "materials/class-cases/lesson-99/case-001-analysis.md"
            )
        )
        importer.import_document(json_doc)
        importer.import_document(md_doc)
        lessons_before = len(session.graph.nodes_with_label("Lesson"))
        with pytest.raises(ImporterError, match="TAUGHT_IN cannot be created"):
            importer.import_class_case(
                ClassCaseImport(
                    case_id="L99-C01-synthetic",
                    lesson_id="lesson-99",
                    match_status="verified",
                    json_document_id=json_doc.document_id,
                    markdown_document_id=md_doc.document_id,
                )
            )
        graph = session.graph
        # Nothing from the case transaction survives, and no
        # identity-only placeholder Lesson was created.
        assert graph.node("ClassCase", "L99-C01-synthetic") is None
        assert graph.find_rels("HAS_REPRESENTATION") == []
        assert graph.find_rels("TAUGHT_IN") == []
        assert len(graph.nodes_with_label("Lesson")) == lessons_before == 0

    def test_cast_record_lifecycle_reports_provenance_and_outcome(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        record = CastRecordImport(
            record_id="rec-1",
            record_type="additionalQuestion",
            date="2099-01-01",
            question=None,
            casting_json='{"id": "rec-1", "v": 1}',
            container_path="daily-records/2099/01/2099-01-01.json",
            json_pointer="/additionalQuestions/0",
        )
        created = importer.import_cast_record(record)
        assert created.outcome is ImportOutcome.CREATED
        assert created.record_id == "rec-1"
        assert created.container_path == "daily-records/2099/01/2099-01-01.json"
        assert created.json_pointer == "/additionalQuestions/0"

        writes_before = session.write_calls
        unchanged = importer.import_cast_record(record)
        assert unchanged.outcome is ImportOutcome.UNCHANGED
        assert session.write_calls == writes_before  # no write for an identical record

        changed = record.model_copy(update={"casting_json": '{"id": "rec-1", "v": 2}'})
        updated = importer.import_cast_record(changed)
        assert updated.outcome is ImportOutcome.UPDATED
        node = session.graph.node("CastRecord", "rec-1")
        assert node is not None and node["casting_json"] == '{"id": "rec-1", "v": 2}'
        # The result DTO never carries body content.
        assert "casting_json" not in updated.model_dump()

    def test_references_require_existing_chunks(self) -> None:
        session = FakeSession()
        importer = Neo4jImporter(session)
        self._seed_case(session)
        document = _document(TEXT_V1)
        importer.import_document(document)
        chunk_id = document.chunks[0].chunk_id

        written = importer.import_case_references(
            "L99-C01-synthetic", (CaseReferenceImport(chunk_id=chunk_id, role="primary"),)
        )
        assert written == 1
        refs = session.graph.find_rels("REFERENCES")
        assert len(refs) == 1
        assert refs[0]["from"] == ("ClassCase", "L99-C01-synthetic")
        assert refs[0]["to"] == ("Chunk", chunk_id)
        assert refs[0]["props"]["role"] == "primary"

        with pytest.raises(ImporterError, match="referenced chunks exist"):
            importer.import_case_references(
                "L99-C01-synthetic",
                (CaseReferenceImport(chunk_id="chunk_missing", role="primary"),),
            )
        assert len(session.graph.find_rels("REFERENCES")) == 1  # nothing half-written


def test_chunk_dto_is_an_occurrence_not_a_node() -> None:
    """The same chunk_id in two revisions stays two occurrences."""
    session = FakeSession()
    importer = Neo4jImporter(session)
    v1 = _document(TEXT_V1)
    v2 = _document(TEXT_V2)
    importer.import_document(v1)
    importer.import_document(v2)
    shared = {c.chunk_id for c in v1.chunks} & {c.chunk_id for c in v2.chunks}
    assert shared
    for chunk_id in shared:
        occurrences = session.graph.find_rels("CONTAINS", to_key=("Chunk", chunk_id))
        assert len(occurrences) == 2  # one per revision, independently stored
        assert len(session.graph.nodes_with_label("Chunk")) >= 1
    assert isinstance(v1.chunks[0], Chunk)
