"""Neo4j schema definition and management for liuyao-kb (M3).

This module owns the Phase 1 graph structure declared in
``docs/phase1-implementation-plan.md`` section 7:

* the node labels and their key properties;
* the five core uniqueness constraints that make the stable IDs
  (``document_id``, ``revision_id``, ``chunk_id``, ``record_id``,
  ``case_id``) unique in the database;
* the relationship-type catalog (direction and semantics). Neo4j does
  not need relationship types to be created in advance, so the catalog
  is the contract M4 writes against, and the smoke test proves the
  critical ones can be created and read back;
* vector-index creation, status inspection and verification for the
  future ``Chunk.embedding`` property.

Rules that shape this module:

* All database access goes through :mod:`liuyao_kb.neo4j.driver`; this
  module never builds its own driver.
* Initialization is idempotent and fail-closed about conflicts: an
  existing constraint or index whose definition differs from the
  expected one is reported as a conflict. Nothing is ever dropped or
  rebuilt automatically.
* No production embedding dimension is chosen here. M5 decides the
  Gemini embedding model; until then vector indexes are created only
  with an explicitly supplied dimension, and the verification flow
  only touches clearly temporary test indexes.
* The vector smoke verification is run-scoped: every run gets a fresh
  Run ID, the temporary index name and the synthetic node's
  ``chunk_id`` are derived from it, a pre-existing index with that
  name aborts the run (it is never reused or dropped), and cleanup
  deletes only what that same run created. A cleanup failure is
  reported as a failure, never as success.
* ``case_id`` (ClassCase) and ``record_id`` (CastRecord) are two
  different identities on two different labels. They are never
  interchanged anywhere in this module.
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

#: Version of the schema definition in this module.
SCHEMA_VERSION = "m3-schema/1"

#: Default label/property the future production vector index targets.
VECTOR_LABEL = "Chunk"
VECTOR_PROPERTY = "embedding"
VECTOR_SIMILARITY = "cosine"

#: Marker property set on synthetic nodes created by the smoke test,
#: so leftovers are always identifiable (and assertable as absent).
SMOKE_MARKER_PROPERTY = "m3_smoke_test"
#: Property recording which smoke run created a synthetic node.
SMOKE_RUN_ID_PROPERTY = "m3_smoke_run_id"
#: chunk_id prefix reserved for smoke-test nodes.
SMOKE_CHUNK_ID_PREFIX = "m3-smoke:"
#: Prefix for temporary vector index names created by the smoke test.
SMOKE_INDEX_PREFIX = "m3_smoke_"

_RUN_ID_PATTERN = re.compile(r"^[a-z0-9]{8,32}$")


def new_run_id() -> str:
    """Return a fresh Run ID for one smoke-verification run."""
    return uuid.uuid4().hex[:16]


def validate_run_id(run_id: str) -> str:
    """Validate a caller-supplied Run ID (lowercase alphanumerics)."""
    if not _RUN_ID_PATTERN.match(run_id):
        raise SchemaError(f"Invalid run id {run_id!r}: use 8-32 lowercase letters or digits")
    return run_id


def smoke_index_name(run_id: str) -> str:
    """The temporary vector index name owned by one smoke run."""
    return f"{SMOKE_INDEX_PREFIX}{validate_run_id(run_id)}"


def smoke_chunk_id(run_id: str) -> str:
    """The synthetic Chunk id owned by one smoke run."""
    return f"{SMOKE_CHUNK_ID_PREFIX}{validate_run_id(run_id)}"


class SchemaError(RuntimeError):
    """A schema operation could not be completed."""


class SchemaConflictError(SchemaError):
    """Existing schema objects conflict with the expected definition.

    Raised instead of silently skipping, dropping or rebuilding: a
    human decides how to resolve a conflict.
    """


class RecordLike(Protocol):
    """The part of a Neo4j record this module consumes."""

    def data(self) -> dict[str, Any]: ...


class SessionLike(Protocol):
    """The part of a Neo4j session this module consumes."""

    def run(self, query: str, **parameters: Any) -> Iterable[RecordLike]: ...


# ---------------------------------------------------------------------------
# Catalog: node types, identity rules, relationships
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeSpec:
    """One node label from plan section 7 and its key properties."""

    label: str
    key_properties: tuple[str, ...]
    #: The property carrying the node's stable identity, if it has one.
    identity_property: str | None


NODE_SPECS: tuple[NodeSpec, ...] = (
    NodeSpec(
        "SourceDocument",
        ("document_id", "source_type", "source_uri", "trust_level", "current_revision_id"),
        "document_id",
    ),
    NodeSpec(
        "DocumentRevision",
        (
            "revision_id",
            "content_hash",
            "revision_ref",
            "parser_version",
            "chunker_version",
            "status",
        ),
        "revision_id",
    ),
    NodeSpec(
        "Chunk",
        (
            "chunk_id",
            "text",
            "text_hash",
            "ordinal",
            "page",
            "heading",
            "embedding",
            "embedding_model",
            "embedding_dimensions",
        ),
        "chunk_id",
    ),
    NodeSpec("Lesson", ("lesson_id", "lesson_number", "title"), "lesson_id"),
    NodeSpec(
        "CastRecord",
        ("record_id", "record_type", "date", "question", "casting_json"),
        "record_id",
    ),
    NodeSpec(
        "ClassCase",
        ("case_id", "lesson_id", "match_status", "verification_basis", "case_memo"),
        "case_id",
    ),
    NodeSpec("Concept", ("concept_id", "name", "aliases"), "concept_id"),
    NodeSpec(
        "RuleCandidate",
        ("candidate_id", "statement", "conditions", "uncertainty", "extractor_model", "status"),
        "candidate_id",
    ),
    NodeSpec(
        "ExternalProject",
        ("repo_url", "commit_sha", "license", "license_status"),
        None,
    ),
    NodeSpec(
        "ReferencePackage",
        ("package_id", "schema_version", "collector_version", "created_at", "validation_status"),
        "package_id",
    ),
)


def identity_property_for(label: str) -> str | None:
    """Return the stable-identity property for ``label``, if defined."""
    for spec in NODE_SPECS:
        if spec.label == label:
            return spec.identity_property
    return None


@dataclass(frozen=True)
class RelationshipSpec:
    """One relationship type: direction, endpoints and semantics."""

    type: str
    from_label: str
    to_label: str
    semantics: str


RELATIONSHIP_SPECS: tuple[RelationshipSpec, ...] = (
    RelationshipSpec(
        "HAS_REVISION", "SourceDocument", "DocumentRevision", "A document's versions."
    ),
    RelationshipSpec("CONTAINS", "DocumentRevision", "Chunk", "Chunks cut from one revision."),
    RelationshipSpec("MENTIONS", "Chunk", "Concept", "A chunk mentions a concept."),
    RelationshipSpec(
        "EXTRACTED_FROM",
        "RuleCandidate",
        "Chunk",
        "A candidate rule was extracted from a chunk; the candidate stays a candidate.",
    ),
    RelationshipSpec("TAUGHT_IN", "ClassCase", "Lesson", "The lesson a case was taught in."),
    RelationshipSpec(
        "HAS_REPRESENTATION",
        "ClassCase",
        "SourceDocument",
        "One file representation of the same case (property format=json|markdown). "
        "The case JSON and the paired classroom-case Markdown both use this; "
        "no second ClassCase is created for the Markdown.",
    ),
    RelationshipSpec(
        "REFERENCES",
        "ClassCase",
        "Chunk",
        "A case references an already-chunked source passage.",
    ),
    RelationshipSpec(
        "REFERENCES",
        "ClassCase",
        "SourceDocument",
        "A case references an unchunked source (mainly Raw ASR). The relationship "
        "carries the Locator plus confidence and correction status, so an ASR "
        "source needs no Chunk to be referenced.",
    ),
    RelationshipSpec(
        "TRANSCRIPT_OF",
        "SourceDocument",
        "SourceDocument",
        "An ASR transcript SourceDocument of the original audio SourceDocument.",
    ),
    RelationshipSpec(
        "BASED_ON_RECORD",
        "ClassCase",
        "CastRecord",
        "Created only when the case JSON's dailyRecord.recordId exactly matches "
        "the CastRecord's record_id. case_id and record_id are never interchanged.",
    ),
    RelationshipSpec(
        "RENDERS",
        "CastRecord",
        "SourceDocument",
        "The HTML-generated daily-record Markdown readable rendering of a "
        "CastRecord. Never used for classroom-case Markdown (that is "
        "HAS_REPRESENTATION).",
    ),
    RelationshipSpec(
        "HAS_SOURCE", "ExternalProject", "SourceDocument", "A source file of a project."
    ),
)


# ---------------------------------------------------------------------------
# Uniqueness constraints
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UniqueConstraint:
    """One expected uniqueness constraint."""

    name: str
    label: str
    property: str

    def ddl(self) -> str:
        """The idempotent CREATE CONSTRAINT statement for this constraint."""
        return (
            f"CREATE CONSTRAINT {self.name} IF NOT EXISTS "
            f"FOR (n:{self.label}) REQUIRE n.{self.property} IS UNIQUE"
        )


#: The five core constraints from plan section 7. Additional identity
#: constraints for other labels need a recorded design reason first;
#: they are deliberately not added here.
CORE_CONSTRAINTS: tuple[UniqueConstraint, ...] = (
    UniqueConstraint("source_document_document_id_unique", "SourceDocument", "document_id"),
    UniqueConstraint("document_revision_revision_id_unique", "DocumentRevision", "revision_id"),
    UniqueConstraint("chunk_chunk_id_unique", "Chunk", "chunk_id"),
    UniqueConstraint("cast_record_record_id_unique", "CastRecord", "record_id"),
    UniqueConstraint("class_case_case_id_unique", "ClassCase", "case_id"),
)


@dataclass(frozen=True)
class ConstraintState:
    """One constraint as read back from the database."""

    name: str
    type: str
    labels: tuple[str, ...]
    properties: tuple[str, ...]


@dataclass
class SchemaStatus:
    """Expected constraints compared with the database's actual state."""

    present: list[UniqueConstraint] = field(default_factory=list)
    missing: list[UniqueConstraint] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    #: Every index currently in the database, for visibility. M3
    #: requires no persistent vector index (that is an M5 decision),
    #: so indexes are reported, not judged.
    indexes: list[IndexState] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.conflicts


def read_constraints(session: SessionLike) -> list[ConstraintState]:
    """Read all constraints via SHOW CONSTRAINTS."""
    rows = session.run(
        "SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties "
        "RETURN name, type, labelsOrTypes, properties"
    )
    states: list[ConstraintState] = []
    for record in rows:
        data = record.data()
        states.append(
            ConstraintState(
                name=str(data["name"]),
                type=str(data["type"]),
                labels=tuple(str(v) for v in (data.get("labelsOrTypes") or [])),
                properties=tuple(str(v) for v in (data.get("properties") or [])),
            )
        )
    return states


def evaluate_constraints(actual: list[ConstraintState]) -> SchemaStatus:
    """Compare the database's constraints with the expected core set."""
    status = SchemaStatus()
    by_name = {state.name: state for state in actual}
    by_label_property = {(s.labels, s.properties): s for s in actual if s.type == "UNIQUENESS"}
    for expected in CORE_CONSTRAINTS:
        same_name = by_name.get(expected.name)
        if same_name is not None:
            if (
                same_name.type == "UNIQUENESS"
                and same_name.labels == (expected.label,)
                and same_name.properties == (expected.property,)
            ):
                status.present.append(expected)
            else:
                status.conflicts.append(
                    f"Constraint {expected.name!r} exists but is "
                    f"{same_name.type} on {same_name.labels}/{same_name.properties}, "
                    f"expected UNIQUENESS on ({expected.label})/({expected.property})"
                )
            continue
        twin = by_label_property.get(((expected.label,), (expected.property,)))
        if twin is not None:
            status.conflicts.append(
                f"A UNIQUENESS constraint on ({expected.label}).{expected.property} "
                f"exists under a different name {twin.name!r}; expected {expected.name!r}"
            )
            continue
        status.missing.append(expected)
    return status


def schema_status(session: SessionLike) -> SchemaStatus:
    """Read the database and evaluate it against the expected schema."""
    status = evaluate_constraints(read_constraints(session))
    status.indexes = read_indexes(session)
    return status


@dataclass
class ApplyResult:
    """What an apply run did (or, for a dry run, would do)."""

    executed: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    dry_run: bool = False


def apply_schema(session: SessionLike, *, dry_run: bool = False) -> ApplyResult:
    """Create the missing core constraints. Idempotent; never destructive.

    Raises :class:`SchemaConflictError` before executing anything when
    an existing constraint conflicts with the expected definition.
    """
    status = schema_status(session)
    if status.conflicts:
        raise SchemaConflictError(
            "Existing constraints conflict with the expected schema; "
            "nothing was changed. " + "; ".join(status.conflicts)
        )
    result = ApplyResult(
        already_present=[c.name for c in status.present],
        dry_run=dry_run,
    )
    for constraint in status.missing:
        statement = constraint.ddl()
        if not dry_run:
            # Schema statements run one at a time (auto-commit); they
            # cannot share an explicit transaction with other work.
            session.run(statement)
        result.executed.append(statement)
    return result


# ---------------------------------------------------------------------------
# Vector index
# ---------------------------------------------------------------------------

_INDEX_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def validate_index_name(name: str) -> str:
    """Validate an index name that will be inlined into Cypher."""
    if not _INDEX_NAME_PATTERN.match(name):
        raise SchemaError(
            f"Invalid index name {name!r}: use letters, digits and underscores, "
            "starting with a letter"
        )
    return name


def validate_dimensions(dimensions: int) -> int:
    """Validate an explicitly supplied vector dimension count."""
    if not isinstance(dimensions, int) or isinstance(dimensions, bool):
        raise SchemaError(f"Vector dimensions must be an integer, got {dimensions!r}")
    if dimensions < 1 or dimensions > 4096:
        raise SchemaError(f"Vector dimensions must be within 1..4096, got {dimensions}")
    return dimensions


def vector_index_ddl(
    name: str,
    dimensions: int,
    *,
    label: str = VECTOR_LABEL,
    property: str = VECTOR_PROPERTY,
) -> str:
    """The idempotent CREATE VECTOR INDEX statement (cosine similarity)."""
    validate_index_name(name)
    dims = validate_dimensions(dimensions)
    return (
        f"CREATE VECTOR INDEX {name} IF NOT EXISTS "
        f"FOR (n:{label}) ON (n.{property}) "
        f"OPTIONS {{indexConfig: {{"
        f"`vector.dimensions`: {dims}, "
        f"`vector.similarity_function`: '{VECTOR_SIMILARITY}'"
        f"}}}}"
    )


@dataclass(frozen=True)
class IndexState:
    """One index as read back from the database."""

    name: str
    type: str
    state: str
    labels: tuple[str, ...]
    properties: tuple[str, ...]
    dimensions: int | None
    similarity: str | None


def read_indexes(session: SessionLike) -> list[IndexState]:
    """Read all indexes via SHOW INDEXES."""
    rows = session.run(
        "SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties, options "
        "RETURN name, type, state, labelsOrTypes, properties, options"
    )
    states: list[IndexState] = []
    for record in rows:
        data = record.data()
        options = data.get("options") or {}
        config = options.get("indexConfig") or {}
        raw_dims = config.get("vector.dimensions")
        raw_similarity = config.get("vector.similarity_function")
        states.append(
            IndexState(
                name=str(data["name"]),
                type=str(data["type"]),
                state=str(data["state"]),
                labels=tuple(str(v) for v in (data.get("labelsOrTypes") or [])),
                properties=tuple(str(v) for v in (data.get("properties") or [])),
                dimensions=int(raw_dims) if raw_dims is not None else None,
                similarity=str(raw_similarity) if raw_similarity is not None else None,
            )
        )
    return states


def find_index(session: SessionLike, name: str) -> IndexState | None:
    """Return the state of the index called ``name``, if it exists."""
    for state in read_indexes(session):
        if state.name == name:
            return state
    return None


def check_vector_index_config(
    state: IndexState,
    dimensions: int,
    *,
    label: str = VECTOR_LABEL,
    property: str = VECTOR_PROPERTY,
) -> None:
    """Raise SchemaConflictError if ``state`` is not the expected index."""
    problems: list[str] = []
    if state.type != "VECTOR":
        problems.append(f"type is {state.type}, expected VECTOR")
    if state.labels != (label,):
        problems.append(f"labels are {state.labels}, expected ({label!r},)")
    if state.properties != (property,):
        problems.append(f"properties are {state.properties}, expected ({property!r},)")
    if state.dimensions != dimensions:
        problems.append(f"dimensions are {state.dimensions}, expected {dimensions}")
    if state.similarity != VECTOR_SIMILARITY:
        problems.append(f"similarity is {state.similarity}, expected {VECTOR_SIMILARITY!r}")
    if problems:
        raise SchemaConflictError(
            f"Index {state.name!r} exists with a different configuration "
            f"({'; '.join(problems)}). It was not modified; resolve the "
            "conflict explicitly instead of dropping or rebuilding it."
        )


def ensure_vector_index(
    session: SessionLike,
    name: str,
    dimensions: int,
    *,
    label: str = VECTOR_LABEL,
    property: str = VECTOR_PROPERTY,
) -> str:
    """Create the vector index if missing; verify it if present.

    Returns ``"created"`` or ``"exists"``. A present-but-different
    index raises :class:`SchemaConflictError`; it is never dropped.
    """
    validate_index_name(name)
    dims = validate_dimensions(dimensions)
    existing = find_index(session, name)
    if existing is not None:
        check_vector_index_config(existing, dims, label=label, property=property)
        return "exists"
    session.run(vector_index_ddl(name, dims, label=label, property=property))
    return "created"


def wait_until_online(
    session: SessionLike,
    name: str,
    *,
    timeout_seconds: float = 60.0,
    poll_seconds: float = 1.0,
) -> IndexState:
    """Poll SHOW INDEXES until ``name`` is ONLINE (or raise)."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        state = find_index(session, name)
        if state is None:
            raise SchemaError(f"Index {name!r} does not exist")
        if state.state == "ONLINE":
            return state
        if state.state == "FAILED":
            raise SchemaError(f"Index {name!r} is in FAILED state")
        if time.monotonic() >= deadline:
            raise SchemaError(
                f"Index {name!r} did not come ONLINE within {timeout_seconds}s "
                f"(last state {state.state})"
            )
        time.sleep(poll_seconds)


@dataclass
class VectorVerification:
    """Outcome of the temporary-index smoke verification."""

    index_name: str
    run_id: str
    dimensions: int
    index_action: str
    index_state: str
    test_chunk_id: str
    found_chunk_id: str | None
    score: float | None
    cleaned_node: bool
    cleaned_index: bool
    cleanup_errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return (
            self.found_chunk_id == self.test_chunk_id
            and self.cleaned_node
            and self.cleaned_index
            and not self.cleanup_errors
        )


def _smoke_vector(dimensions: int) -> list[float]:
    """A deterministic synthetic embedding for the smoke test."""
    vector = [0.0] * dimensions
    vector[0] = 1.0
    return vector


def _count_exact_smoke_node(session: SessionLike, chunk_id: str, run_id: str) -> int:
    """Count leftover copies of one run's synthetic node (must be 0).

    Matches on all three ownership facts together: the exact
    ``chunk_id``, the smoke marker, and this run's Run ID.
    """
    rows = session.run(
        f"MATCH (n:Chunk {{chunk_id: $chunk_id, {SMOKE_MARKER_PROPERTY}: true, "
        f"{SMOKE_RUN_ID_PROPERTY}: $run_id}}) RETURN count(n) AS count",
        chunk_id=chunk_id,
        run_id=run_id,
    )
    for record in rows:
        return int(record.data()["count"])
    return 0


def _count_nodes_with_chunk_id(session: SessionLike, chunk_id: str) -> int:
    """Count any Chunk nodes carrying ``chunk_id``, whoever created them."""
    rows = session.run(
        "MATCH (n:Chunk {chunk_id: $chunk_id}) RETURN count(n) AS count",
        chunk_id=chunk_id,
    )
    for record in rows:
        return int(record.data()["count"])
    return 0


def verify_vector_index(
    session: SessionLike,
    *,
    dimensions: int,
    run_id: str | None = None,
    timeout_seconds: float = 60.0,
) -> VectorVerification:
    """Prove a temporary vector index works end to end, then clean up.

    Run-scoped lifecycle (cloud M3 task book section 4.6):

    * the run gets a Run ID (generated, or ``run_id`` when supplied);
      the temporary index name and the synthetic node's ``chunk_id``
      are both derived from it, so two runs never collide;
    * if an index with the run's name already exists before the run
      starts, the run aborts: a pre-existing index is never reused
      and never dropped by this function;
    * likewise, if any node already carries the run's synthetic
      ``chunk_id`` before the run starts (for example a leftover from
      an earlier run whose cleanup failed, under a reused Run ID),
      the run aborts before creating anything: that node cannot be
      proven to be this run's, so it is never adopted or deleted;
    * the run creates its index, waits for ONLINE, inserts one
      synthetic Chunk node carrying the smoke marker and the Run ID,
      and queries the index for that vector;
    * cleanup removes exactly that node (matched by its exact
      ``chunk_id``, the marker, AND this run's Run ID together) and
      drops the index only when this run actually created it.
      Cleanup runs even when a step fails, and a cleanup failure is
      reported as a failure (via ``cleanup_errors`` / ``ok``), never
      silently as success.
    """
    dims = validate_dimensions(dimensions)
    run = validate_run_id(run_id) if run_id is not None else new_run_id()
    index_name = smoke_index_name(run)
    test_chunk_id = smoke_chunk_id(run)
    vector = _smoke_vector(dims)

    if find_index(session, index_name) is not None:
        raise SchemaError(
            f"Temporary index {index_name!r} already exists before run {run}; "
            "refusing to reuse or drop an index this run did not create. "
            "Re-run with a fresh run id."
        )
    if _count_nodes_with_chunk_id(session, test_chunk_id) > 0:
        raise SchemaError(
            f"A node with smoke chunk_id {test_chunk_id!r} already exists "
            f"before run {run}; refusing to adopt or delete a node this "
            "run did not create. Inspect and remove the leftover "
            "manually, or re-run with a fresh run id."
        )

    created = False
    index_state = "UNKNOWN"
    found_chunk_id: str | None = None
    score: float | None = None
    primary_error: Exception | None = None
    try:
        session.run(vector_index_ddl(index_name, dims))
        created = True
        state = wait_until_online(session, index_name, timeout_seconds=timeout_seconds)
        index_state = state.state
        session.run(
            "CREATE (n:Chunk {chunk_id: $chunk_id, text: $text, "
            f"{SMOKE_MARKER_PROPERTY}: true, {SMOKE_RUN_ID_PROPERTY}: $run_id, "
            "embedding: $embedding})",
            chunk_id=test_chunk_id,
            text="m3 synthetic smoke-test chunk",
            run_id=run,
            embedding=vector,
        )
        rows = session.run(
            "CALL db.index.vector.queryNodes($index_name, $k, $embedding) "
            "YIELD node, score RETURN node.chunk_id AS chunk_id, score AS score",
            index_name=index_name,
            k=5,
            embedding=vector,
        )
        for record in rows:
            data = record.data()
            if data.get("chunk_id") == test_chunk_id:
                found_chunk_id = test_chunk_id
                raw_score = data.get("score")
                score = float(raw_score) if raw_score is not None else None
    except Exception as exc:  # cleanup below still runs; re-raised after it
        primary_error = exc

    # Scoped cleanup: exactly this run's synthetic node, and the index
    # only when this run created it. Never a database-wide delete,
    # never another run's (or a production) index.
    cleaned_node = False
    cleaned_index = False
    cleanup_errors: list[str] = []
    try:
        session.run(
            f"MATCH (n:Chunk {{chunk_id: $chunk_id, {SMOKE_MARKER_PROPERTY}: true, "
            f"{SMOKE_RUN_ID_PROPERTY}: $run_id}}) DETACH DELETE n",
            chunk_id=test_chunk_id,
            run_id=run,
        )
        cleaned_node = _count_exact_smoke_node(session, test_chunk_id, run) == 0
    except Exception as exc:
        cleanup_errors.append(f"smoke node cleanup failed: {exc}")
    if created:
        try:
            session.run(f"DROP INDEX {index_name} IF EXISTS")
        except Exception as exc:
            cleanup_errors.append(f"smoke index cleanup failed: {exc}")
    try:
        cleaned_index = find_index(session, index_name) is None
    except Exception as exc:
        cleanup_errors.append(f"smoke index cleanup check failed: {exc}")
    if not cleaned_index and not cleanup_errors:
        if created:
            cleanup_errors.append(
                f"index {index_name!r} still exists after this run's cleanup drop"
            )
        else:
            cleanup_errors.append(
                f"index {index_name!r} exists but was not created by this run; left untouched"
            )

    if primary_error is not None:
        detail = (
            f"Vector verification failed for run {run}: {primary_error} "
            f"(cleanup: node_removed={cleaned_node}, index_removed={cleaned_index}"
        )
        if cleanup_errors:
            detail += f", cleanup_errors={cleanup_errors}"
        raise SchemaError(detail + ")") from primary_error
    return VectorVerification(
        index_name=index_name,
        run_id=run,
        dimensions=dims,
        index_action="created",
        index_state=index_state,
        test_chunk_id=test_chunk_id,
        found_chunk_id=found_chunk_id,
        score=score,
        cleaned_node=cleaned_node,
        cleaned_index=cleaned_index,
        cleanup_errors=tuple(cleanup_errors),
    )


def count_smoke_nodes(session: SessionLike) -> int:
    """Count leftover smoke-test nodes (must be 0 after cleanup)."""
    rows = session.run(
        f"MATCH (n:Chunk {{{SMOKE_MARKER_PROPERTY}: true}}) RETURN count(n) AS count"
    )
    for record in rows:
        return int(record.data()["count"])
    return 0
