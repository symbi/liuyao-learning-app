"""End-to-end pipeline tests over a synthetic repository tree.

collect_plan runs the real M2 mappers and the M4a chunker over
invented lesson-19-shaped material; run_plan executes the plan
against the in-memory Neo4j fake. No real classroom case, daily
record or private material is used.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fake_neo4j import FakeSession
from liuyao_kb.ids import make_document_id
from liuyao_kb.ingest import CaseReferenceSpec, collect_plan, run_plan
from liuyao_kb.neo4j.importer import ImportOutcome
from liuyao_kb.sources import AllowedDailyRecord, DailyRecordsSettings, SourcesConfig
from liuyao_kb.sources.config import ClassCasesSettings, CuratedNotesSettings, RawAsrSettings

REPO = "symbi/liuyao-learning-app"
RECORD_ID = "11111111-2222-3333-4444-555555555555"
OTHER_ID = "99999999-8888-7777-6666-555555555555"
CONTAINER = "daily-records/2026/11/2026-11-22.json"
NOTES_PATH = "docs/lessons/lesson-19-notes-v0.1.md"
NOTES_DOC_ID = make_document_id("markdown", REPO, NOTES_PATH)

NOTES = """# 第十九课整理稿 - 合成

## 3. 求财与项目

Case two primary explanation paragraph.

## 7. 婚姻案例

Case three primary explanation paragraph.

## 10. HTML 案例后续核对要求

Summary table paragraph covering both cases.
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _case_json(case_id: str, match_status: str, daily_record: dict[str, Any] | None) -> str:
    document: dict[str, Any] = {
        "recordType": "class-case",
        "id": case_id,
        "lessonId": "lesson-19",
        "matchStatus": match_status,
        "verificationBasis": ["synthetic basis"],
    }
    if daily_record is not None:
        document["dailyRecord"] = daily_record
    return json.dumps(document, ensure_ascii=False)


def _generated_md(record_id: str) -> str:
    embedded = json.dumps({"schemaVersion": 99, "id": record_id}, indent=2)
    return (
        "# Synthetic Daily Record\n\n## Teacher Memo\n\nsynthetic memo body\n\n"
        f"## 原始记录 JSON\n\n```json\n{embedded}\n```\n"
    )


def build_repo(root: Path) -> SourcesConfig:
    _write(root / NOTES_PATH, NOTES)
    cases = root / "materials/class-cases/lesson-19"
    _write(
        cases / "case-002.json",
        _case_json(
            "L19-C02-synthetic",
            "matched",
            {
                "recordId": RECORD_ID,
                "jsonPath": CONTAINER,
                "markdownPath": f"daily-records/2026/11/markdown/2026-11-22--{RECORD_ID}.md",
            },
        ),
    )
    _write(cases / "case-002-analysis.md", "# Case Two\n\nPaired markdown body.\n")
    _write(cases / "case-003.json", _case_json("L19-C03-synthetic", "verified", None))
    _write(cases / "case-003-analysis.md", "# Case Three\n\nPaired markdown body.\n")

    container = {
        "recordDate": "2026-11-22",
        "additionalQuestions": [
            {
                "id": RECORD_ID,
                "recordType": "additionalQuestion",
                "isCase": True,
                "caseSource": "classroom",
                "date": "2026-11-22",
                "question": "synthetic question",
            },
            {
                "id": OTHER_ID,
                "recordType": "additionalQuestion",
                "isCase": True,
                "caseSource": "classroom",
                "date": "2026-11-22",
                "question": "not allowlisted",
            },
        ],
    }
    _write(root / CONTAINER, json.dumps(container, ensure_ascii=False))
    _write(
        root / f"daily-records/2026/11/markdown/2026-11-22--{RECORD_ID}.md",
        _generated_md(RECORD_ID),
    )
    return SourcesConfig(
        curated_notes=CuratedNotesSettings(root=root),
        class_cases=ClassCasesSettings(root=root),
        daily_records=DailyRecordsSettings(
            include=True,
            root=root,
            allowed_records=[AllowedDailyRecord(path=CONTAINER, record_id=RECORD_ID)],
        ),
    )


SPECS = (
    CaseReferenceSpec(
        case_id="L19-C03-synthetic",
        notes_document_id=NOTES_DOC_ID,
        sections=(("7. ", "primary"),),
    ),
    CaseReferenceSpec(
        case_id="L19-C02-synthetic",
        notes_document_id=NOTES_DOC_ID,
        sections=(("3. ", "primary"), ("10. ", "secondary")),
    ),
)


class TestPilotShapedPlan:
    def test_collect_and_run(self, tmp_path: Path) -> None:
        sources = build_repo(tmp_path)
        plan = collect_plan(sources, repository=REPO, reference_specs=SPECS)

        # The container JSON itself never becomes a document.
        assert all(not document.source_uri.endswith(CONTAINER) for document in plan.documents)
        # Daily generated MD is imported unchunked by default.
        daily_docs = [d for d in plan.documents if "markdown/2026-11-22--" in d.source_uri]
        assert len(daily_docs) == 1
        assert daily_docs[0].chunks == ()
        assert daily_docs[0].chunker_version is None
        # Only the allowlisted record is planned.
        assert [record.record_id for record in plan.records] == [RECORD_ID]
        assert plan.record_links == (("L19-C02-synthetic", RECORD_ID),)
        assert plan.chunk_count() > 0

        session = FakeSession()
        report = run_plan(session, plan)
        assert report.ok, report.failures
        graph = session.graph

        cases = graph.nodes_with_label("ClassCase")
        assert len(cases) == 2  # one per case, never one per representation
        case_two = graph.node("ClassCase", "L19-C02-synthetic")
        assert case_two is not None
        assert case_two["match_status"] == "verified"  # matched -> verified
        reps = graph.find_rels("HAS_REPRESENTATION", from_key=("ClassCase", "L19-C02-synthetic"))
        assert len(reps) == 2
        json_rep = next(rel for rel in reps if rel["props"]["format"] == "json")
        assert json_rep["props"]["match_status_raw"] == "matched"  # raw preserved

        assert len(graph.nodes_with_label("CastRecord")) == 1
        assert graph.node("CastRecord", OTHER_ID) is None
        based = graph.find_rels("BASED_ON_RECORD")
        assert len(based) == 1
        assert based[0]["from"] == ("ClassCase", "L19-C02-synthetic")
        assert based[0]["to"] == ("CastRecord", RECORD_ID)
        renders = graph.find_rels("RENDERS")
        assert len(renders) == 1
        assert renders[0]["from"] == ("CastRecord", RECORD_ID)

        lesson = graph.node("Lesson", "lesson-19")
        assert lesson is not None and lesson["lesson_number"] == 19
        assert len(graph.find_rels("TAUGHT_IN")) == 2

        refs_two = graph.find_rels("REFERENCES", from_key=("ClassCase", "L19-C02-synthetic"))
        roles_two = {rel["props"]["role"] for rel in refs_two}
        assert roles_two == {"primary", "secondary"}
        refs_three = graph.find_rels("REFERENCES", from_key=("ClassCase", "L19-C03-synthetic"))
        assert refs_three and all(rel["props"]["role"] == "primary" for rel in refs_three)

        # A second full run changes nothing.
        counts = graph.counts()
        report_two = run_plan(session, plan)
        assert report_two.ok
        assert all(result.outcome is ImportOutcome.UNCHANGED for result in report_two.documents)
        assert graph.counts() == counts

    def test_asr_is_never_imported(self, tmp_path: Path) -> None:
        _write(tmp_path / "lessons/lesson-19/transcript-asr-raw.txt", "uncorrected asr")
        sources = SourcesConfig(
            curated_notes=CuratedNotesSettings(enabled=False),
            class_cases=ClassCasesSettings(enabled=False),
            raw_asr=RawAsrSettings(enabled=True, root=tmp_path),
        )
        plan = collect_plan(sources, repository=REPO)
        assert plan.documents == ()
        assert plan.chunk_count() == 0
        assert any("raw_asr" in note for note in plan.skipped)
