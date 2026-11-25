"""Tests for the stable ID formulas (plan section 8, defined in M3).

Pure functions only: no database, no network, no source files.
"""

from __future__ import annotations

import pytest

from liuyao_kb.ids import (
    hash_text,
    make_chunk_id,
    make_document_id,
    make_revision_id,
)

HASH_A = "a" * 64
HASH_B = "0123456789abcdef" * 4


class TestDocumentId:
    def test_composition(self) -> None:
        assert (
            make_document_id("markdown", "symbi/liuyao-learning-app", "docs/lessons/lesson-19.md")
            == "markdown|symbi/liuyao-learning-app|docs/lessons/lesson-19.md"
        )

    def test_stable_and_distinct(self) -> None:
        first = make_document_id("markdown", "symbi/liuyao-learning-app", "docs/a.md")
        assert first == make_document_id("markdown", "symbi/liuyao-learning-app", "docs/a.md")
        assert first != make_document_id("markdown", "symbi/liuyao-learning-app", "docs/b.md")
        assert first != make_document_id("text", "symbi/liuyao-learning-app", "docs/a.md")
        assert first != make_document_id("markdown", "symbi/liuyao-learning-raw", "docs/a.md")

    def test_path_normalization(self) -> None:
        assert make_document_id("markdown", "repo", "./docs/a.md") == make_document_id(
            "markdown", "repo", "docs/a.md"
        )

    def test_rejects_unsafe_components(self) -> None:
        for bad_path in ("", "/abs/path.md", "../escape.md", "docs/../escape.md", "docs\\win.md"):
            with pytest.raises(ValueError):
                make_document_id("markdown", "repo", bad_path)
        with pytest.raises(ValueError):
            make_document_id("", "repo", "docs/a.md")
        with pytest.raises(ValueError):
            make_document_id("markdown", "repo|evil", "docs/a.md")


class TestRevisionId:
    def test_composition(self) -> None:
        document_id = make_document_id("markdown", "repo", "docs/a.md")
        assert make_revision_id(document_id, HASH_A) == f"{document_id}|{HASH_A}"

    def test_content_change_changes_revision_but_not_document(self) -> None:
        document_id = make_document_id("markdown", "repo", "docs/a.md")
        assert make_revision_id(document_id, HASH_A) != make_revision_id(document_id, HASH_B)

    def test_rejects_non_sha256(self) -> None:
        document_id = make_document_id("markdown", "repo", "docs/a.md")
        for bad in ("", "abc", "A" * 64, "g" * 64):
            with pytest.raises(ValueError):
                make_revision_id(document_id, bad)


class TestChunkId:
    def test_composition(self) -> None:
        document_id = make_document_id("markdown", "repo", "docs/a.md")
        assert (
            make_chunk_id(document_id, "chunker/1", HASH_A, 0)
            == f"{document_id}|chunker/1|{HASH_A}|0"
        )

    def test_occurrence_index_disambiguates_identical_text(self) -> None:
        document_id = make_document_id("markdown", "repo", "docs/a.md")
        assert make_chunk_id(document_id, "chunker/1", HASH_A, 0) != make_chunk_id(
            document_id, "chunker/1", HASH_A, 1
        )

    def test_chunker_version_is_part_of_identity(self) -> None:
        document_id = make_document_id("markdown", "repo", "docs/a.md")
        assert make_chunk_id(document_id, "chunker/1", HASH_A, 0) != make_chunk_id(
            document_id, "chunker/2", HASH_A, 0
        )

    def test_rejects_bad_occurrence_index(self) -> None:
        document_id = make_document_id("markdown", "repo", "docs/a.md")
        for bad in (-1, True, "0"):
            with pytest.raises(ValueError):
                make_chunk_id(document_id, "chunker/1", HASH_A, bad)  # type: ignore[arg-type]


class TestHashText:
    def test_matches_sha256_rule(self) -> None:
        digest = hash_text("六爻")
        assert len(digest) == 64
        assert digest == digest.lower()
        assert hash_text("六爻") == digest
        assert hash_text("六爻 ") != digest
