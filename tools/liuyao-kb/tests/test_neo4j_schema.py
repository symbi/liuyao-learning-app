"""Tests for the M3 Neo4j schema module and its CLI commands.

Everything here runs against an in-memory fake session; no test opens
a network connection or touches a real database. The fake understands
just enough Cypher to model constraint/index state, so idempotency
and conflict behavior are exercised for real.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from typer.testing import CliRunner

from liuyao_kb.cli import app
from liuyao_kb.neo4j.schema import (
    CORE_CONSTRAINTS,
    NODE_SPECS,
    RELATIONSHIP_SPECS,
    SchemaConflictError,
    SchemaError,
    apply_schema,
    count_smoke_nodes,
    ensure_vector_index,
    evaluate_constraints,
    identity_property_for,
    new_run_id,
    schema_status,
    smoke_chunk_id,
    smoke_index_name,
    validate_index_name,
    validate_run_id,
    vector_index_ddl,
    verify_vector_index,
    wait_until_online,
)

runner = CliRunner()


class FakeRecord:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def data(self) -> dict[str, Any]:
        return self._data


class FakeSession:
    """A minimal stateful stand-in for a Neo4j session.

    Models constraint and index state so CREATE/DROP statements have
    observable effects, and records every statement it receives.
    """

    def __init__(self) -> None:
        self.statements: list[str] = []
        self.constraints: dict[str, dict[str, Any]] = {}
        self.indexes: dict[str, dict[str, Any]] = {}
        self.smoke_nodes: dict[str, dict[str, Any]] = {}
        self.index_state_progression: dict[str, list[str]] = {}
        # Failure injection for cleanup/error-path tests.
        self.fail_drop_index = False
        self.fail_delete_node = False
        self.fail_query = False

    # -- statement handling -------------------------------------------------
    def run(self, query: str, **parameters: Any) -> list[FakeRecord]:
        self.statements.append(query)
        if query.startswith("SHOW CONSTRAINTS"):
            return [
                FakeRecord(
                    {
                        "name": name,
                        "type": c["type"],
                        "labelsOrTypes": c["labels"],
                        "properties": c["properties"],
                    }
                )
                for name, c in self.constraints.items()
            ]
        if query.startswith("SHOW INDEXES"):
            return [FakeRecord(self._index_row(name)) for name in self.indexes]
        if query.startswith("CREATE CONSTRAINT"):
            match = re.search(
                r"CREATE CONSTRAINT (\w+) IF NOT EXISTS FOR \(n:(\w+)\) "
                r"REQUIRE n\.(\w+) IS UNIQUE",
                query,
            )
            assert match is not None, query
            name, label, prop = match.groups()
            self.constraints.setdefault(
                name, {"type": "UNIQUENESS", "labels": [label], "properties": [prop]}
            )
            return []
        if query.startswith("CREATE VECTOR INDEX"):
            match = re.search(
                r"CREATE VECTOR INDEX (\w+) IF NOT EXISTS FOR \(n:(\w+)\) ON \(n\.(\w+)\)",
                query,
            )
            assert match is not None, query
            name, label, prop = match.groups()
            dims = int(re.search(r"`vector\.dimensions`: (\d+)", query).group(1))  # type: ignore[union-attr]
            self.indexes.setdefault(
                name,
                {
                    "type": "VECTOR",
                    "state": "ONLINE",
                    "labels": [label],
                    "properties": [prop],
                    "dimensions": dims,
                    "similarity": "cosine",
                },
            )
            return []
        if query.startswith("DROP INDEX"):
            if self.fail_drop_index:
                raise RuntimeError("injected drop failure")
            name = re.search(r"DROP INDEX (\w+)", query).group(1)  # type: ignore[union-attr]
            self.indexes.pop(name, None)
            return []
        if query.startswith("CREATE (n:Chunk"):
            self.smoke_nodes[parameters["chunk_id"]] = parameters
            return []
        if query.startswith("CALL db.index.vector.queryNodes"):
            if self.fail_query:
                raise RuntimeError("injected query failure")
            k = int(parameters.get("k", 5))
            return [
                FakeRecord({"chunk_id": chunk_id, "score": 1.0})
                for chunk_id in list(self.smoke_nodes)[:k]
            ]
        if "DETACH DELETE" in query:
            if self.fail_delete_node:
                raise RuntimeError("injected delete failure")
            node = self.smoke_nodes.get(parameters["chunk_id"])
            # The delete only lands when the stored node's run_id
            # matches the run_id the statement carries: this models
            # the run-scoped cleanup condition for real.
            if node is not None and node.get("run_id") == parameters.get("run_id"):
                self.smoke_nodes.pop(parameters["chunk_id"], None)
            return []
        if query.startswith("MATCH (n:Chunk"):
            if "chunk_id" in parameters:
                node = self.smoke_nodes.get(parameters["chunk_id"])
                if node is None:
                    return [FakeRecord({"count": 0})]
                if "run_id" in parameters and node.get("run_id") != parameters["run_id"]:
                    return [FakeRecord({"count": 0})]
                return [FakeRecord({"count": 1})]
            return [FakeRecord({"count": len(self.smoke_nodes)})]
        raise AssertionError(f"Unexpected query: {query}")

    def _index_row(self, name: str) -> dict[str, Any]:
        index = self.indexes[name]
        progression = self.index_state_progression.get(name)
        if progression:
            index = {**index, "state": progression.pop(0)}
        return {
            "name": name,
            "type": index["type"],
            "state": index["state"],
            "labelsOrTypes": index["labels"],
            "properties": index["properties"],
            "options": {
                "indexConfig": {
                    "vector.dimensions": index["dimensions"],
                    "vector.similarity_function": index["similarity"],
                }
            },
        }

    # -- helpers for tests ---------------------------------------------------
    def add_constraint(self, name: str, label: str, prop: str, type_: str = "UNIQUENESS") -> None:
        self.constraints[name] = {"type": type_, "labels": [label], "properties": [prop]}

    def add_index(
        self,
        name: str,
        *,
        dimensions: int = 8,
        label: str = "Chunk",
        prop: str = "embedding",
        similarity: str = "cosine",
        type_: str = "VECTOR",
        state: str = "ONLINE",
    ) -> None:
        self.indexes[name] = {
            "type": type_,
            "state": state,
            "labels": [label],
            "properties": [prop],
            "dimensions": dimensions,
            "similarity": similarity,
        }

    def add_smoke_node(self, chunk_id: str, run_id: str) -> None:
        """Plant a pre-existing smoke node as an earlier run left it."""
        self.smoke_nodes[chunk_id] = {
            "chunk_id": chunk_id,
            "run_id": run_id,
            "text": "leftover from an earlier run",
            "embedding": [1.0] + [0.0] * 7,
        }

    def ddl_statements(self) -> list[str]:
        return [
            s
            for s in self.statements
            if s.startswith(("CREATE CONSTRAINT", "CREATE VECTOR INDEX", "DROP INDEX"))
        ]


class TestCatalog:
    def test_all_plan_labels_present(self) -> None:
        labels = {spec.label for spec in NODE_SPECS}
        assert labels == {
            "SourceDocument",
            "DocumentRevision",
            "Chunk",
            "Lesson",
            "CastRecord",
            "ClassCase",
            "Concept",
            "RuleCandidate",
            "ExternalProject",
            "ReferencePackage",
        }

    def test_identity_properties(self) -> None:
        assert identity_property_for("SourceDocument") == "document_id"
        assert identity_property_for("DocumentRevision") == "revision_id"
        assert identity_property_for("Chunk") == "chunk_id"
        # The two identities that must never be conflated:
        assert identity_property_for("ClassCase") == "case_id"
        assert identity_property_for("CastRecord") == "record_id"

    def test_relationship_directions(self) -> None:
        by_type: dict[str, set[tuple[str, str]]] = {}
        for spec in RELATIONSHIP_SPECS:
            by_type.setdefault(spec.type, set()).add((spec.from_label, spec.to_label))
        assert ("ClassCase", "CastRecord") in by_type["BASED_ON_RECORD"]
        assert ("CastRecord", "SourceDocument") in by_type["RENDERS"]
        assert ("ClassCase", "SourceDocument") in by_type["HAS_REPRESENTATION"]
        assert ("ClassCase", "Lesson") in by_type["TAUGHT_IN"]
        assert ("RuleCandidate", "Chunk") in by_type["EXTRACTED_FROM"]
        assert ("SourceDocument", "SourceDocument") in by_type["TRANSCRIPT_OF"]
        # REFERENCES covers both chunked and unchunked (ASR) targets.
        assert ("ClassCase", "Chunk") in by_type["REFERENCES"]
        assert ("ClassCase", "SourceDocument") in by_type["REFERENCES"]

    def test_five_core_constraints(self) -> None:
        pairs = {(c.label, c.property) for c in CORE_CONSTRAINTS}
        assert pairs == {
            ("SourceDocument", "document_id"),
            ("DocumentRevision", "revision_id"),
            ("Chunk", "chunk_id"),
            ("CastRecord", "record_id"),
            ("ClassCase", "case_id"),
        }
        names = [c.name for c in CORE_CONSTRAINTS]
        assert len(names) == len(set(names)) == 5

    def test_constraint_ddl_is_idempotent_form(self) -> None:
        for constraint in CORE_CONSTRAINTS:
            ddl = constraint.ddl()
            assert "IF NOT EXISTS" in ddl
            assert f"FOR (n:{constraint.label})" in ddl
            assert f"REQUIRE n.{constraint.property} IS UNIQUE" in ddl


class TestApplyAndStatus:
    def test_status_reports_all_missing_on_empty_db(self) -> None:
        status = schema_status(FakeSession())
        assert not status.ok
        assert len(status.missing) == 5
        assert status.present == []

    def test_apply_creates_missing_then_is_idempotent(self) -> None:
        session = FakeSession()
        first = apply_schema(session)
        assert len(first.executed) == 5
        assert schema_status(session).ok
        second = apply_schema(session)
        assert second.executed == []
        assert len(second.already_present) == 5
        # No statement was ever destructive.
        assert not any("DROP" in s or "DELETE" in s for s in session.statements)

    def test_apply_dry_run_executes_nothing(self) -> None:
        session = FakeSession()
        result = apply_schema(session, dry_run=True)
        assert len(result.executed) == 5
        assert session.ddl_statements() == []
        assert not schema_status(session).ok

    def test_status_detects_missing_subset(self) -> None:
        session = FakeSession()
        session.add_constraint("chunk_chunk_id_unique", "Chunk", "chunk_id")
        status = schema_status(session)
        assert [c.name for c in status.present] == ["chunk_chunk_id_unique"]
        assert len(status.missing) == 4

    def test_conflicting_name_aborts_apply(self) -> None:
        session = FakeSession()
        # Same expected name, wrong property: a conflict, not a match.
        session.add_constraint("chunk_chunk_id_unique", "Chunk", "text_hash")
        with pytest.raises(SchemaConflictError):
            apply_schema(session)
        assert session.ddl_statements() == []

    def test_same_label_property_under_other_name_is_a_conflict(self) -> None:
        session = FakeSession()
        session.add_constraint("some_other_name", "Chunk", "chunk_id")
        status = evaluate_constraints(
            [
                type(
                    "S",
                    (),
                    {
                        "name": "some_other_name",
                        "type": "UNIQUENESS",
                        "labels": ("Chunk",),
                        "properties": ("chunk_id",),
                    },
                )()
            ]
        )
        assert status.conflicts
        assert not status.ok


class TestVectorIndex:
    def test_ddl_uses_cosine_and_explicit_dimensions(self) -> None:
        ddl = vector_index_ddl("m3_smoke_chunk_embedding", 8)
        assert "CREATE VECTOR INDEX m3_smoke_chunk_embedding IF NOT EXISTS" in ddl
        assert "FOR (n:Chunk) ON (n.embedding)" in ddl
        assert "`vector.dimensions`: 8" in ddl
        assert "`vector.similarity_function`: 'cosine'" in ddl

    def test_index_name_validation(self) -> None:
        assert validate_index_name("ok_name_1") == "ok_name_1"
        for bad in ("", "1abc", "a-b", "a b", "a;DROP"):
            with pytest.raises(SchemaError):
                validate_index_name(bad)

    def test_dimensions_validation(self) -> None:
        for bad in (0, -1, 4097):
            with pytest.raises(SchemaError):
                vector_index_ddl("ok_name", bad)

    def test_ensure_creates_then_reports_exists(self) -> None:
        session = FakeSession()
        assert ensure_vector_index(session, "idx_a", 8) == "created"
        assert ensure_vector_index(session, "idx_a", 8) == "exists"

    def test_conflicting_dimensions_raise_and_never_drop(self) -> None:
        session = FakeSession()
        session.add_index("idx_a", dimensions=16)
        with pytest.raises(SchemaConflictError):
            ensure_vector_index(session, "idx_a", 8)
        assert not any(s.startswith("DROP INDEX") for s in session.statements)
        assert "idx_a" in session.indexes

    def test_conflicting_similarity_raises(self) -> None:
        session = FakeSession()
        session.add_index("idx_a", dimensions=8, similarity="euclidean")
        with pytest.raises(SchemaConflictError):
            ensure_vector_index(session, "idx_a", 8)

    def test_wait_until_online_polls(self) -> None:
        session = FakeSession()
        session.add_index("idx_a", dimensions=8, state="POPULATING")
        session.index_state_progression["idx_a"] = ["POPULATING", "ONLINE"]
        state = wait_until_online(session, "idx_a", timeout_seconds=5, poll_seconds=0)
        assert state.state == "ONLINE"

    def test_wait_until_online_missing_index_raises(self) -> None:
        with pytest.raises(SchemaError):
            wait_until_online(FakeSession(), "nope", timeout_seconds=1, poll_seconds=0)

    def test_run_id_derivation(self) -> None:
        assert smoke_index_name("run00001") == "m3_smoke_run00001"
        assert smoke_chunk_id("run00001") == "m3-smoke:run00001"
        assert validate_run_id("abc12345") == "abc12345"
        for bad in ("", "short", "Has Upper", "has-dash", "has space", "a" * 33):
            with pytest.raises(SchemaError):
                validate_run_id(bad)
        generated = {new_run_id() for _ in range(50)}
        assert len(generated) == 50
        assert all(validate_run_id(run) == run for run in generated)

    def test_verify_roundtrip_and_cleanup(self) -> None:
        session = FakeSession()
        result = verify_vector_index(session, dimensions=8, run_id="run00001", timeout_seconds=5)
        assert result.ok
        assert result.run_id == "run00001"
        assert result.index_name == "m3_smoke_run00001"
        assert result.test_chunk_id == "m3-smoke:run00001"
        assert result.index_action == "created"
        assert result.index_state == "ONLINE"
        assert result.found_chunk_id == result.test_chunk_id
        assert result.score == pytest.approx(1.0)
        assert result.cleaned_node and result.cleaned_index
        assert result.cleanup_errors == ()
        assert count_smoke_nodes(session) == 0
        assert session.indexes == {}
        # Cleanup was scoped: one node delete by chunk_id, one index drop.
        deletes = [s for s in session.statements if "DETACH DELETE" in s]
        assert len(deletes) == 1
        assert "MATCH (n) DETACH DELETE n" not in session.statements

    def test_verify_generates_unique_run_scoped_names(self) -> None:
        session = FakeSession()
        first = verify_vector_index(session, dimensions=8, timeout_seconds=5)
        second = verify_vector_index(session, dimensions=8, timeout_seconds=5)
        assert first.ok and second.ok
        assert first.run_id != second.run_id
        assert first.index_name != second.index_name
        assert first.test_chunk_id != second.test_chunk_id

    def test_verify_refuses_preexisting_index_and_never_drops_it(self) -> None:
        session = FakeSession()
        # Even an identical-configuration index must not be reused:
        # this run did not create it, so it must not drop it either.
        session.add_index("m3_smoke_run00001", dimensions=8)
        with pytest.raises(SchemaError, match="already exists"):
            verify_vector_index(session, dimensions=8, run_id="run00001", timeout_seconds=5)
        assert "m3_smoke_run00001" in session.indexes
        assert not any(s.startswith("DROP INDEX") for s in session.statements)

    def test_verify_refuses_preexisting_node_and_preserves_it(self) -> None:
        session = FakeSession()
        # A leftover from an earlier run whose cleanup failed, under
        # the same (reused) run id: this run cannot prove ownership,
        # so it must abort and leave the node exactly as it found it.
        session.add_smoke_node("m3-smoke:run00009", "run00009")
        with pytest.raises(SchemaError, match="already exists"):
            verify_vector_index(session, dimensions=8, run_id="run00009", timeout_seconds=5)
        assert "m3-smoke:run00009" in session.smoke_nodes
        assert session.indexes == {}
        assert not any("DETACH DELETE" in s for s in session.statements)
        assert not any(s.startswith("DROP INDEX") for s in session.statements)

    def test_verify_cleanup_is_scoped_to_own_run_id(self) -> None:
        session = FakeSession()
        # Another run's leftover (different chunk_id and run_id) must
        # survive this run completely untouched.
        session.add_smoke_node("m3-smoke:other999", "other999")
        result = verify_vector_index(session, dimensions=8, run_id="run00010", timeout_seconds=5)
        assert result.ok
        assert "m3-smoke:other999" in session.smoke_nodes
        assert "m3-smoke:run00010" not in session.smoke_nodes
        # The delete statement itself carries the run_id condition.
        deletes = [s for s in session.statements if "DETACH DELETE" in s]
        assert len(deletes) == 1
        assert "m3_smoke_run_id" in deletes[0]

    def test_verify_index_cleanup_failure_is_reported_not_hidden(self) -> None:
        session = FakeSession()
        session.fail_drop_index = True
        result = verify_vector_index(session, dimensions=8, run_id="run00002", timeout_seconds=5)
        assert not result.ok
        assert result.found_chunk_id == result.test_chunk_id
        assert result.cleaned_node
        assert not result.cleaned_index
        assert result.cleanup_errors
        assert "m3_smoke_run00002" in session.indexes

    def test_verify_node_cleanup_failure_is_reported_not_hidden(self) -> None:
        session = FakeSession()
        session.fail_delete_node = True
        result = verify_vector_index(session, dimensions=8, run_id="run00003", timeout_seconds=5)
        assert not result.ok
        assert not result.cleaned_node
        assert result.cleaned_index
        assert result.cleanup_errors

    def test_verify_query_failure_still_cleans_up(self) -> None:
        session = FakeSession()
        session.fail_query = True
        with pytest.raises(SchemaError, match="cleanup: node_removed=True, index_removed=True"):
            verify_vector_index(session, dimensions=8, run_id="run00004", timeout_seconds=5)
        assert session.indexes == {}
        assert session.smoke_nodes == {}


class TestSchemaCli:
    @pytest.fixture(autouse=True)
    def _no_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("LIUYAO_KB_CONFIG_DIR", "/nonexistent-liuyao-kb-test")

    def test_init_dry_run_prints_five_constraints_without_credentials(self) -> None:
        result = runner.invoke(app, ["schema", "init", "--dry-run"])
        assert result.exit_code == 0
        assert result.output.count("CREATE CONSTRAINT") == 5
        assert "IF NOT EXISTS" in result.output

    def test_check_without_credentials_exits_nonzero(self) -> None:
        result = runner.invoke(app, ["schema", "check"])
        assert result.exit_code == 1
        assert "not configured" in result.output

    def test_verify_vector_rejects_invalid_run_id_before_db(self) -> None:
        result = runner.invoke(
            app,
            ["schema", "verify-vector", "--dimensions", "8", "--run-id", "Bad Run!"],
        )
        assert result.exit_code == 1
        assert "Refusing" in result.output

    def test_verify_vector_without_credentials_exits_nonzero(self) -> None:
        result = runner.invoke(app, ["schema", "verify-vector", "--dimensions", "8"])
        assert result.exit_code == 1
        assert "not configured" in result.output
