"""M4c-A rehearsal: the real pilot plan, end to end, on FakeSession.

These tests pin the M4c pilot baseline. They load the committed
``sources.pilot.yaml`` (substituting only the machine-specific roots
with this repository checkout), build the real plan from the real
lesson-19 material, and rehearse the exact sequence M4c-B will run
against AuraDB:

1. first import -> node/relationship counts match the frozen
   expectation (88 nodes / 95 relationships, per-type breakdown);
2. immediate rerun -> every document unchanged, counts stable;
3. one document's transaction fails (chunk conflict) -> that document
   rolls back completely, the failure is reported, and the rest of
   the graph is untouched.

No real database is involved. If the pilot source material changes,
these counts are supposed to fail loudly: re-check the change, then
update the expectation and the M4c runbook together.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from fake_neo4j import FakeSession
from liuyao_kb.ids import make_revision_id
from liuyao_kb.ingest import IngestPlan, collect_plan, run_plan
from liuyao_kb.sources.config import load_sources_config

REPO_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = "symbi/liuyao-learning-app"

EXPECTED_NODES = {
    "SourceDocument": 7,
    "DocumentRevision": 7,
    "Chunk": 69,
    "Lesson": 1,
    "ClassCase": 2,
    "CastRecord": 2,
}
EXPECTED_RELS = {
    "CONTAINS": 69,
    "HAS_REVISION": 7,
    "HAS_REPRESENTATION": 4,
    "TAUGHT_IN": 2,
    "BASED_ON_RECORD": 2,
    "RENDERS": 2,
    "REFERENCES": 9,
}
EXPECTED_CHUNKS_PER_DOCUMENT = {
    "docs/lessons/lesson-19-notes-v0.1.md": 30,
    "materials/class-cases/lesson-19/case-002-analysis.md": 19,
    "materials/class-cases/lesson-19/case-003-analysis.md": 20,
}
PILOT_RECORD_IDS = {
    "13e9c29a-cdbc-41e0-912d-5e02fa7c54d3",
    "518d525a-838e-479d-8d2c-815296358b5e",
}


def _pilot_plan() -> IngestPlan:
    config = load_sources_config(REPO_ROOT / "tools/liuyao-kb/sources.pilot.yaml")
    config.curated_notes.root = REPO_ROOT
    config.class_cases.root = REPO_ROOT
    config.daily_records.root = REPO_ROOT
    return collect_plan(config, repository=REPOSITORY)


def _counts(session: FakeSession) -> tuple[Counter[str], Counter[str]]:
    nodes = Counter(label for (label, _key) in session.graph.nodes)
    rels = Counter(rel["type"] for rel in session.graph.rels)
    return nodes, rels


def test_pilot_plan_shape() -> None:
    plan = _pilot_plan()
    assert len(plan.documents) == 7
    assert sum(len(doc.chunks) for doc in plan.documents) == 69
    assert [lesson.lesson_id for lesson in plan.lessons] == ["lesson-19"]
    assert {case.case_id for case in plan.cases} == {
        "L19-C02-shop-operation-transfer",
        "L19-C03-female-marriage-multiple-guangui",
    }
    assert {record.record_id for record in plan.records} == PILOT_RECORD_IDS
    assert len(plan.record_links) == 2
    assert len(plan.renders_links) == 2
    references = [ref for _case, refs in plan.references for ref in refs]
    assert len(references) == 9
    assert Counter(ref.role for ref in references) == {"primary": 6, "secondary": 3}
    assert plan.skipped == ()


def test_pilot_first_import_matches_expected_counts() -> None:
    plan = _pilot_plan()
    session = FakeSession()
    report = run_plan(session, plan)
    assert report.ok, report.failures

    nodes, rels = _counts(session)
    assert dict(nodes) == EXPECTED_NODES
    assert dict(rels) == EXPECTED_RELS
    assert sum(nodes.values()) == 88
    assert sum(rels.values()) == 95

    # Per-document chunk counts, keyed by repository-relative path.
    for doc in plan.documents:
        contains = session.graph.find_rels(
            "CONTAINS", from_key=("DocumentRevision", doc.revision_id)
        )
        relative = doc.source_uri.rsplit("/", 1)[-1]
        expected = next(
            (n for path, n in EXPECTED_CHUNKS_PER_DOCUMENT.items() if path.endswith(relative)),
            0,
        )
        assert len(contains) == expected, doc.source_uri
        # current_revision_id points at exactly this imported revision.
        stored = session.graph.node("SourceDocument", doc.document_id)
        assert stored is not None
        assert stored["current_revision_id"] == doc.revision_id

    # CastRecord provenance reaches the report, without body text.
    assert {r.record_id for r in report.records} == PILOT_RECORD_IDS
    for record_result in report.records:
        assert record_result.outcome == "created"
        assert record_result.container_path.startswith("daily-records/2026/11/")
        assert record_result.json_pointer

    # RENDERS direction and endpoints, one by one: the importer creates
    # CastRecord -[:RENDERS]-> SourceDocument (the generated Markdown).
    # Each of the two pilot links must start at its own CastRecord and
    # end at that record's generated-Markdown document -- never the
    # reverse, never crossed between the two records.
    renders = session.graph.find_rels("RENDERS")
    assert len(renders) == 2
    expected_renders = {
        (("CastRecord", record_id), ("SourceDocument", document_id))
        for record_id, document_id in plan.renders_links
    }
    assert {(rel["from"], rel["to"]) for rel in renders} == expected_renders


def test_pilot_rerun_is_fully_unchanged_and_stable() -> None:
    plan = _pilot_plan()
    session = FakeSession()
    first = run_plan(session, plan)
    assert first.ok, first.failures
    counts_after_first = _counts(session)

    second = run_plan(session, plan)
    assert second.ok, second.failures
    assert {doc.outcome for doc in second.documents} == {"unchanged"}
    assert {r.outcome for r in second.records} == {"unchanged"}
    assert _counts(session) == counts_after_first


def test_single_document_failure_rolls_back_and_is_reported() -> None:
    plan = _pilot_plan()
    session = FakeSession()
    assert run_plan(session, plan).ok
    counts_before = _counts(session)

    # Forge a NEW revision of the notes document whose first chunk
    # reuses the real chunk_id (same text_hash) with tampered text:
    # the importer's in-transaction conflict check must abort that
    # document's whole write. (Same construction as the importer-level
    # conflict test; an unchanged-metadata copy would instead be
    # reported "unchanged" without any write, by design.)
    notes = next(doc for doc in plan.documents if len(doc.chunks) == 30)
    forged_revision_id = make_revision_id(notes.document_id, "0" * 64)
    forged_chunks = tuple(
        chunk.model_copy(
            update={
                "revision_id": forged_revision_id,
                **({"text": "Forged other text."} if index == 0 else {}),
            }
        )
        for index, chunk in enumerate(notes.chunks)
    )
    forged = notes.model_copy(
        update={
            "revision_id": forged_revision_id,
            "content_hash": "0" * 64,
            "chunks": forged_chunks,
        }
    )

    report = run_plan(session, IngestPlan(documents=(forged,)))
    assert not report.ok
    assert any(
        failure.item == f"document {notes.document_id}" and "ChunkConflictError" in failure.error
        for failure in report.failures
    )
    # Nothing moved: no new revision, no new chunks, pointer untouched.
    assert _counts(session) == counts_before
    stored = session.graph.node("SourceDocument", notes.document_id)
    assert stored is not None
    assert stored["current_revision_id"] == notes.revision_id
