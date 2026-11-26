"""In-memory Neo4j fake for importer/pipeline tests.

The fake implements the *semantics* of the importer's fixed Cypher
statement set against an in-memory graph — MERGE creates or reuses
nodes/relationships by identity, SET with a null value removes the
property (Neo4j semantics), CONTAINS deletion is scoped to one
revision, and a failed write transaction rolls the whole graph
back to its pre-transaction snapshot. Tests assert on the
resulting graph state, not on call counts.
"""

from __future__ import annotations

import copy
from typing import Any

from liuyao_kb.neo4j import importer as imp

IDENTITY_PROPERTIES = {
    "SourceDocument": "document_id",
    "DocumentRevision": "revision_id",
    "Chunk": "chunk_id",
    "Lesson": "lesson_id",
    "ClassCase": "case_id",
    "CastRecord": "record_id",
}

NodeKey = tuple[str, str]  # (label, identity value)


class FakeRecord(dict[str, Any]):
    """A dict record with the Neo4j Record.data() accessor."""

    def data(self) -> dict[str, Any]:
        return dict(self)


class FakeResult(list[FakeRecord]):
    def single(self) -> FakeRecord | None:
        if not self:
            return None
        if len(self) > 1:
            raise ValueError("expected at most one record")
        return self[0]


def _apply_set(props: dict[str, Any], values: dict[str, Any]) -> None:
    """Neo4j SET semantics: a null value removes the property."""
    for key, value in values.items():
        if value is None:
            props.pop(key, None)
        else:
            props[key] = value


class FakeGraph:
    """Nodes keyed by (label, identity); relationships as a list."""

    def __init__(self) -> None:
        self.nodes: dict[NodeKey, dict[str, Any]] = {}
        self.rels: list[dict[str, Any]] = []

    # -- inspection helpers for tests --------------------------------

    def node(self, label: str, key: str) -> dict[str, Any] | None:
        return self.nodes.get((label, key))

    def nodes_with_label(self, label: str) -> list[dict[str, Any]]:
        return [props for (node_label, _), props in self.nodes.items() if node_label == label]

    def find_rels(
        self,
        rel_type: str | None = None,
        from_key: NodeKey | None = None,
        to_key: NodeKey | None = None,
    ) -> list[dict[str, Any]]:
        found = []
        for rel in self.rels:
            if rel_type is not None and rel["type"] != rel_type:
                continue
            if from_key is not None and rel["from"] != from_key:
                continue
            if to_key is not None and rel["to"] != to_key:
                continue
            found.append(rel)
        return found

    def counts(self) -> tuple[int, int]:
        return len(self.nodes), len(self.rels)

    # -- mutation primitives ------------------------------------------

    def merge_node(self, label: str, key: str) -> dict[str, Any]:
        node_key = (label, key)
        if node_key not in self.nodes:
            self.nodes[node_key] = {IDENTITY_PROPERTIES[label]: key}
        return self.nodes[node_key]

    def merge_rel(
        self,
        rel_type: str,
        from_key: NodeKey,
        to_key: NodeKey,
        props: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for rel in self.rels:
            if rel["type"] == rel_type and rel["from"] == from_key and rel["to"] == to_key:
                if props:
                    _apply_set(rel["props"], props)
                return rel
        rel = {"type": rel_type, "from": from_key, "to": to_key, "props": {}}
        if props:
            _apply_set(rel["props"], props)
        self.rels.append(rel)
        return rel

    def snapshot(self) -> Any:
        return copy.deepcopy((self.nodes, self.rels))

    def restore(self, snapshot: Any) -> None:
        self.nodes, self.rels = copy.deepcopy(snapshot)


class FakeTx:
    """Dispatches the importer's statements against a FakeGraph."""

    def __init__(self, session: FakeSession, *, write: bool) -> None:
        self._session = session
        self._graph = session.graph
        self._write = write

    def run(self, query: str, **parameters: Any) -> FakeResult:
        session = self._session
        if self._write:
            session.write_calls += 1
            if (
                session.fail_on_write_call is not None
                and session.write_calls == session.fail_on_write_call
            ):
                raise RuntimeError("injected write failure")
        else:
            session.read_calls += 1
        handler = _HANDLERS.get(query)
        if handler is None:
            raise AssertionError(f"FakeTx does not implement this statement: {query!r}")
        return handler(self._graph, parameters)


class FakeSession:
    """execute_read / execute_write with transactional rollback."""

    def __init__(
        self, graph: FakeGraph | None = None, *, fail_on_write_call: int | None = None
    ) -> None:
        self.graph = graph if graph is not None else FakeGraph()
        self.fail_on_write_call = fail_on_write_call
        self.write_calls = 0
        self.read_calls = 0

    def execute_read(self, transaction_function: Any, *args: Any, **kwargs: Any) -> Any:
        return transaction_function(FakeTx(self, write=False), *args, **kwargs)

    def execute_write(self, transaction_function: Any, *args: Any, **kwargs: Any) -> Any:
        snapshot = self.graph.snapshot()
        try:
            return transaction_function(FakeTx(self, write=True), *args, **kwargs)
        except Exception:
            self.graph.restore(snapshot)
            raise


# ---------------------------------------------------------------------------
# Statement handlers (one per importer Cypher constant)
# ---------------------------------------------------------------------------


def _read_document_state(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    document = graph.node("SourceDocument", params["document_id"])
    if document is None:
        return FakeResult()
    row: dict[str, Any] = {
        "current_revision_id": document.get("current_revision_id"),
        "content_hash": None,
        "parser_version": None,
        "chunker_version": None,
        "status": None,
    }
    revision_key = ("DocumentRevision", params["revision_id"])
    revision = graph.node(*revision_key)
    linked = graph.find_rels(
        "HAS_REVISION", from_key=("SourceDocument", params["document_id"]), to_key=revision_key
    )
    if revision is not None and linked:
        for field in ("content_hash", "parser_version", "chunker_version", "status"):
            row[field] = revision.get(field)
    return FakeResult([FakeRecord(row)])


def _find_chunks(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    rows = []
    for chunk_id in params["chunk_ids"]:
        chunk = graph.node("Chunk", chunk_id)
        if chunk is not None:
            rows.append(
                FakeRecord(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk.get("text"),
                        "text_hash": chunk.get("text_hash"),
                    }
                )
            )
    return FakeResult(rows)


def _merge_document(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    node = graph.merge_node("SourceDocument", params["document_id"])
    _apply_set(
        node,
        {
            "source_type": params["source_type"],
            "source_uri": params["source_uri"],
            "trust_level": params["trust_level"],
        },
    )
    return FakeResult()


def _merge_revision(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    document_key = ("SourceDocument", params["document_id"])
    if graph.node(*document_key) is None:
        return FakeResult()  # MATCH fails: nothing happens
    node = graph.merge_node("DocumentRevision", params["revision_id"])
    _apply_set(
        node,
        {
            "content_hash": params["content_hash"],
            "revision_ref": params["revision_ref"],
            "parser_version": params["parser_version"],
            "chunker_version": params["chunker_version"],
            "status": params["status"],
        },
    )
    graph.merge_rel("HAS_REVISION", document_key, ("DocumentRevision", params["revision_id"]))
    return FakeResult()


def _merge_chunks(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    for chunk in params["chunks"]:
        if graph.node("Chunk", chunk["chunk_id"]) is None:
            node = graph.merge_node("Chunk", chunk["chunk_id"])
            node["text"] = chunk["text"]
            node["text_hash"] = chunk["text_hash"]
    return FakeResult()


def _delete_contains(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    revision_key = ("DocumentRevision", params["revision_id"])
    graph.rels = [
        rel for rel in graph.rels if not (rel["type"] == "CONTAINS" and rel["from"] == revision_key)
    ]
    return FakeResult()


def _merge_contains(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    revision_key = ("DocumentRevision", params["revision_id"])
    if graph.node(*revision_key) is None:
        return FakeResult()
    for item in params["contains"]:
        chunk_key = ("Chunk", item["chunk_id"])
        if graph.node(*chunk_key) is None:
            continue
        graph.merge_rel(
            "CONTAINS",
            revision_key,
            chunk_key,
            {
                "paragraph_ordinal": item["paragraph_ordinal"],
                "subchunk_index": item["subchunk_index"],
                "heading_path": list(item["heading_path"]),
                "start_offset": item["start_offset"],
                "end_offset": item["end_offset"],
            },
        )
    return FakeResult()


def _set_current_revision(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    document = graph.node("SourceDocument", params["document_id"])
    if document is not None:
        document["current_revision_id"] = params["revision_id"]
    return FakeResult()


def _merge_lesson(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    node = graph.merge_node("Lesson", params["lesson_id"])
    _apply_set(node, {"lesson_number": params["lesson_number"], "title": params["title"]})
    return FakeResult()


def _merge_case(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    node = graph.merge_node("ClassCase", params["case_id"])
    _apply_set(
        node,
        {
            "lesson_id": params["lesson_id"],
            "match_status": params["match_status"],
            "verification_basis": params["verification_basis"],
            "case_memo": params["case_memo"],
        },
    )
    return FakeResult()


def _merge_has_representation(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    case_key = ("ClassCase", params["case_id"])
    document_key = ("SourceDocument", params["document_id"])
    if graph.node(*case_key) is None or graph.node(*document_key) is None:
        return FakeResult()
    graph.merge_rel(
        "HAS_REPRESENTATION",
        case_key,
        document_key,
        {"format": params["format"], "match_status_raw": params["match_status_raw"]},
    )
    return FakeResult()


def _merge_taught_in(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    case_key = ("ClassCase", params["case_id"])
    if graph.node(*case_key) is None:
        return FakeResult()
    graph.merge_node("Lesson", params["lesson_id"])
    graph.merge_rel("TAUGHT_IN", case_key, ("Lesson", params["lesson_id"]))
    return FakeResult()


def _merge_cast_record(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    node = graph.merge_node("CastRecord", params["record_id"])
    _apply_set(
        node,
        {
            "record_type": params["record_type"],
            "date": params["date"],
            "question": params["question"],
            "casting_json": params["casting_json"],
        },
    )
    return FakeResult()


def _link_based_on_record(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    case_key = ("ClassCase", params["case_id"])
    record_key = ("CastRecord", params["record_id"])
    if graph.node(*case_key) is None or graph.node(*record_key) is None:
        return FakeResult()
    graph.merge_rel("BASED_ON_RECORD", case_key, record_key)
    return FakeResult([FakeRecord({"case_id": params["case_id"]})])


def _link_renders(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    record_key = ("CastRecord", params["record_id"])
    document_key = ("SourceDocument", params["document_id"])
    if graph.node(*record_key) is None or graph.node(*document_key) is None:
        return FakeResult()
    graph.merge_rel("RENDERS", record_key, document_key)
    return FakeResult([FakeRecord({"record_id": params["record_id"]})])


def _merge_references(graph: FakeGraph, params: dict[str, Any]) -> FakeResult:
    case_key = ("ClassCase", params["case_id"])
    written = 0
    if graph.node(*case_key) is not None:
        for ref in params["refs"]:
            chunk_key = ("Chunk", ref["chunk_id"])
            if graph.node(*chunk_key) is None:
                continue
            graph.merge_rel("REFERENCES", case_key, chunk_key, {"role": ref["role"]})
            written += 1
    return FakeResult([FakeRecord({"written": written})])


_HANDLERS = {
    imp.Q_READ_DOCUMENT_STATE: _read_document_state,
    imp.Q_FIND_CHUNKS: _find_chunks,
    imp.Q_MERGE_DOCUMENT: _merge_document,
    imp.Q_MERGE_REVISION: _merge_revision,
    imp.Q_MERGE_CHUNKS: _merge_chunks,
    imp.Q_DELETE_CONTAINS: _delete_contains,
    imp.Q_MERGE_CONTAINS: _merge_contains,
    imp.Q_SET_CURRENT_REVISION: _set_current_revision,
    imp.Q_MERGE_LESSON: _merge_lesson,
    imp.Q_MERGE_CASE: _merge_case,
    imp.Q_MERGE_HAS_REPRESENTATION: _merge_has_representation,
    imp.Q_MERGE_TAUGHT_IN: _merge_taught_in,
    imp.Q_MERGE_CAST_RECORD: _merge_cast_record,
    imp.Q_LINK_BASED_ON_RECORD: _link_based_on_record,
    imp.Q_LINK_RENDERS: _link_renders,
    imp.Q_MERGE_REFERENCES: _merge_references,
}
