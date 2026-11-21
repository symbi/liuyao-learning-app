"""Tests for M2-A common source parsing models."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from liuyao_kb.sources.models import (
    JsonLocator,
    MarkdownLocator,
    ParsedDocument,
    ParsedSection,
    PdfLocator,
    SourceType,
    TextLocator,
    build_source_identity,
    canonical_source_uri,
    sha256_bytes,
    sha256_text,
    source_identity_from_path,
)


class TestHashAndIdentity:
    def test_sha256_text_is_lowercase_hex(self) -> None:
        digest = sha256_text("hello")
        assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_sha256_bytes_matches_text_for_utf8(self) -> None:
        assert sha256_bytes("你好".encode()) == sha256_text("你好")

    def test_source_identity_is_relative_to_repository_root(self, tmp_path: Path) -> None:
        source = tmp_path / "docs" / "lessons" / "lesson-05-notes-v0.1.md"
        identity = source_identity_from_path(
            SourceType.MARKDOWN,
            source,
            source_root=tmp_path,
        )
        assert identity == "markdown:docs/lessons/lesson-05-notes-v0.1.md"

    def test_explicit_uri_is_not_rewritten(self) -> None:
        uri = "https://example.com/lesson-05.md"
        assert canonical_source_uri(uri) == uri
        assert build_source_identity(SourceType.MARKDOWN, uri) == f"markdown:{uri}"

    def test_revision_ref_is_not_coupled_to_git(self) -> None:
        document = ParsedDocument(
            source_type=SourceType.TEXT,
            source_identity="text:fixtures/lesson.txt",
            source_uri="fixtures/lesson.txt",
            content_hash=sha256_text("lesson text"),
            revision_ref="release-2026-11",
            parser_version="text-1",
        )
        assert document.revision_ref == "release-2026-11"


class TestLocators:
    def test_markdown_locator_preserves_heading_paragraph_and_offsets(self) -> None:
        locator = MarkdownLocator(
            heading="世爻与用神",
            heading_level=2,
            paragraph=3,
            start_offset=120,
            end_offset=180,
        )
        assert locator.heading == "世爻与用神"
        assert locator.paragraph == 3

    def test_pdf_locator_is_one_based(self) -> None:
        locator = PdfLocator(page_number=2, start_offset=10, end_offset=42)
        assert locator.page_number == 2

    def test_json_locator_uses_record_id_and_json_pointer(self) -> None:
        locator = JsonLocator(record_id="case-001", json_pointer="/casting/lines/0")
        assert locator.record_id == "case-001"
        assert locator.json_pointer == "/casting/lines/0"

    def test_invalid_text_offsets_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TextLocator(paragraph=1, start_offset=5, end_offset=4)

    def test_pdf_page_number_is_positive(self) -> None:
        with pytest.raises(ValidationError):
            PdfLocator(page_number=0, start_offset=0, end_offset=1)

    def test_invalid_markdown_offsets_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarkdownLocator(start_offset=7, end_offset=6)


class TestParsedDocument:
    def test_accepts_valid_sha256_document(self) -> None:
        document = ParsedDocument(
            source_type=SourceType.MARKDOWN,
            source_identity="markdown:docs/lessons/lesson-05-notes-v0.1.md",
            source_uri="docs/lessons/lesson-05-notes-v0.1.md",
            content_hash=sha256_text("# Lesson"),
            revision_ref="abc123",
            parser_version="markdown-1",
            title="Lesson",
            sections=(
                ParsedSection(
                    text="# Lesson",
                    ordinal=0,
                    locator=MarkdownLocator(
                        heading="Lesson",
                        heading_level=1,
                        paragraph=1,
                        start_offset=0,
                        end_offset=8,
                    ),
                ),
            ),
        )
        assert len(document.sections) == 1

    def test_rejects_invalid_sha256(self) -> None:
        with pytest.raises(ValidationError):
            ParsedDocument(
                source_type=SourceType.TEXT,
                source_identity="text:fixture.txt",
                source_uri="fixture.txt",
                content_hash="not-a-digest",
                parser_version="text-1",
            )

    def test_model_is_frozen_and_rejects_extra_fields(self) -> None:
        document = ParsedDocument(
            source_type=SourceType.TEXT,
            source_identity="text:fixture.txt",
            source_uri="fixture.txt",
            content_hash=sha256_text("text"),
            parser_version="text-1",
        )
        with pytest.raises(ValidationError):
            document.title = "changed"  # type: ignore[misc]
