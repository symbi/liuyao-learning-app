"""Tests for M2-B Markdown and TXT source adapters.

All fixtures are small synthetic strings. No private memo, raw ASR, or real
course content is copied here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from liuyao_kb.sources.adapters import (
    MARKDOWN_PARSER_VERSION,
    TEXT_PARSER_VERSION,
    EmptySourceError,
    InvalidSourceEncodingError,
    MarkdownAdapter,
    TextAdapter,
    parse_markdown_text,
    parse_text_text,
)
from liuyao_kb.sources.models import (
    MarkdownLocator,
    TextLocator,
    repository_source_uri,
    sha256_bytes,
    sha256_text,
    source_identity_from_repository,
)

APP_REPO = "symbi/liuyao-learning-app"
RAW_REPO = "symbi/liuyao-learning-raw"

MARKDOWN_FIXTURE = (
    "# 第五课 六亲持世\n"
    "\n"
    "世爻是卦的主轴。\n"
    "这一段有两行。\n"
    "\n"
    "## 持世分类\n"
    "\n"
    "子孙持世主平安。\n"
    "\n"
    "### 案例说明\n"
    "\n"
    "课堂案例只作说明。\n"
    "\n"
    "## 课后练习\n"
    "\n"
    "复盘今天的卦例。\n"
)

TEXT_FIXTURE = "第一段讲用神。\n同一段第二行。\n\n第二段讲原神。\n\n第三段。\n"


def assert_offsets_match(source_text: str, document_sections: object) -> None:
    """Every section text must be the exact slice its locator points at."""

    for section in document_sections:  # type: ignore[attr-defined]
        locator = section.locator
        assert source_text[locator.start_offset : locator.end_offset] == section.text


class TestMarkdownAdapter:
    def test_heading_and_nested_heading_structure(self) -> None:
        document = MarkdownAdapter().parse_text(
            MARKDOWN_FIXTURE,
            source_uri=repository_source_uri(APP_REPO, "docs/lessons/lesson-05.md"),
        )

        assert document.title == "第五课 六亲持世"
        assert document.parser_version == MARKDOWN_PARSER_VERSION
        headings = [
            (section.locator.heading, section.locator.heading_level)
            for section in document.sections
            if isinstance(section.locator, MarkdownLocator) and section.locator.paragraph is None
        ]
        assert headings == [
            ("第五课 六亲持世", 1),
            ("持世分类", 2),
            ("案例说明", 3),
            ("课后练习", 2),
        ]

    def test_paragraphs_keep_belonging_heading_and_global_numbering(self) -> None:
        document = parse_markdown_text(
            MARKDOWN_FIXTURE,
            source_uri=repository_source_uri(APP_REPO, "docs/lessons/lesson-05.md"),
        )

        paragraphs = [
            section
            for section in document.sections
            if isinstance(section.locator, MarkdownLocator)
            and section.locator.paragraph is not None
        ]
        assert [section.locator.paragraph for section in paragraphs] == [1, 2, 3, 4]  # type: ignore[misc]
        assert paragraphs[0].locator.heading == "第五课 六亲持世"  # type: ignore[attr-defined]
        assert paragraphs[0].locator.heading_level == 1  # type: ignore[attr-defined]
        assert paragraphs[1].locator.heading == "持世分类"  # type: ignore[attr-defined]
        assert paragraphs[2].locator.heading == "案例说明"  # type: ignore[attr-defined]
        assert paragraphs[2].locator.heading_level == 3  # type: ignore[attr-defined]
        assert paragraphs[3].locator.heading == "课后练习"  # type: ignore[attr-defined]

    def test_multi_line_paragraph_is_preserved_exactly(self) -> None:
        document = parse_markdown_text(
            MARKDOWN_FIXTURE,
            source_uri=repository_source_uri(APP_REPO, "docs/lessons/lesson-05.md"),
        )

        assert document.sections[1].text == "世爻是卦的主轴。\n这一段有两行。"
        assert_offsets_match(MARKDOWN_FIXTURE, document.sections)

    def test_content_before_first_heading_has_no_heading(self) -> None:
        source = "前言一段。\n\n# 标题\n\n正文。\n"
        document = parse_markdown_text(source, source_uri="repo://example/notes/a.md")

        first = document.sections[0]
        assert isinstance(first.locator, MarkdownLocator)
        assert first.locator.heading is None
        assert first.locator.heading_level is None
        assert document.title == "标题"
        assert_offsets_match(source, document.sections)

    def test_fenced_block_is_not_split_or_misread_as_heading(self) -> None:
        source = "# 说明\n\n```text\n# 这不是标题\n\n空行也不分段\n```\n\n正文。\n"
        document = parse_markdown_text(source, source_uri="repo://example/notes/a.md")

        texts = [section.text for section in document.sections]
        assert "# 说明" in texts
        assert "```text\n# 这不是标题\n\n空行也不分段\n```" in texts
        assert document.sections[-1].text == "正文。"
        assert_offsets_match(source, document.sections)

    def test_unicode_chinese_text_and_hash(self) -> None:
        data = MARKDOWN_FIXTURE.encode("utf-8")
        document = MarkdownAdapter().parse_bytes(
            data,
            source_uri=repository_source_uri(APP_REPO, "docs/lessons/lesson-05.md"),
        )

        assert document.content_hash == sha256_bytes(data)
        assert document.content_hash == sha256_text(MARKDOWN_FIXTURE)
        assert "世爻" in document.sections[1].text


class TestTextAdapter:
    def test_multiple_paragraphs_with_locators(self) -> None:
        document = TextAdapter().parse_text(
            TEXT_FIXTURE,
            source_uri=repository_source_uri(RAW_REPO, "lessons/lesson-05.txt"),
        )

        assert document.parser_version == TEXT_PARSER_VERSION
        assert document.title is None
        assert [section.text for section in document.sections] == [
            "第一段讲用神。\n同一段第二行。",
            "第二段讲原神。",
            "第三段。",
        ]
        locators = [section.locator for section in document.sections]
        assert all(isinstance(locator, TextLocator) for locator in locators)
        assert [locator.paragraph for locator in locators if isinstance(locator, TextLocator)] == [
            1,
            2,
            3,
        ]
        assert_offsets_match(TEXT_FIXTURE, document.sections)

    def test_parse_text_text_wrapper(self) -> None:
        document = parse_text_text("只有一段。", source_uri="repo://example/notes/a.txt")
        assert len(document.sections) == 1
        assert document.sections[0].text == "只有一段。"


class TestEmptyAndInvalidInput:
    @pytest.mark.parametrize("adapter", [MarkdownAdapter(), TextAdapter()])
    def test_empty_bytes_are_rejected(self, adapter: MarkdownAdapter | TextAdapter) -> None:
        with pytest.raises(EmptySourceError):
            adapter.parse_bytes(b"", source_uri="repo://example/notes/a.md")

    @pytest.mark.parametrize("adapter", [MarkdownAdapter(), TextAdapter()])
    def test_whitespace_only_text_is_rejected(self, adapter: MarkdownAdapter | TextAdapter) -> None:
        with pytest.raises(EmptySourceError):
            adapter.parse_text("  \n\n\t \n", source_uri="repo://example/notes/a.md")

    @pytest.mark.parametrize("adapter", [MarkdownAdapter(), TextAdapter()])
    def test_invalid_utf8_is_rejected(self, adapter: MarkdownAdapter | TextAdapter) -> None:
        with pytest.raises(InvalidSourceEncodingError):
            adapter.parse_bytes(b"\xff\xfe invalid \x80", source_uri="repo://example/notes/a.md")

    def test_wrong_input_types_are_rejected(self) -> None:
        with pytest.raises(TypeError):
            MarkdownAdapter().parse_bytes(
                "not bytes",  # type: ignore[arg-type]
                source_uri="repo://example/notes/a.md",
            )
        with pytest.raises(TypeError):
            TextAdapter().parse_text(
                b"not text",  # type: ignore[arg-type]
                source_uri="repo://example/notes/a.txt",
            )

    def test_absolute_machine_path_uri_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="machine absolute path"):
            parse_markdown_text("# 标题\n", source_uri="/Users/someone/private/lesson.md")


class TestSourceNamespace:
    def test_repository_uri_convention(self) -> None:
        uri = repository_source_uri(APP_REPO, "docs/lessons/lesson-05.md")
        assert uri == "repo://symbi/liuyao-learning-app/docs/lessons/lesson-05.md"

    def test_same_relative_path_in_two_repositories_has_different_identity(self) -> None:
        relative = "docs/lessons/lesson-05.md"
        app_document = MarkdownAdapter().parse_repository_bytes(
            MARKDOWN_FIXTURE.encode("utf-8"),
            repository=APP_REPO,
            relative_path=relative,
            revision_ref="commit-app",
        )
        raw_document = MarkdownAdapter().parse_repository_bytes(
            MARKDOWN_FIXTURE.encode("utf-8"),
            repository=RAW_REPO,
            relative_path=relative,
            revision_ref="commit-raw",
        )

        assert app_document.source_uri != raw_document.source_uri
        assert app_document.source_identity != raw_document.source_identity
        assert app_document.source_identity == source_identity_from_repository(
            app_document.source_type, APP_REPO, relative
        )
        # The same content hash and different revisions do not blur identity.
        assert app_document.content_hash == raw_document.content_hash
        assert app_document.revision_ref == "commit-app"
        assert raw_document.revision_ref == "commit-raw"

    def test_text_identity_also_uses_namespace(self) -> None:
        relative = "lessons/lesson-05.txt"
        app_identity = source_identity_from_repository("text", APP_REPO, relative)
        raw_identity = source_identity_from_repository("text", RAW_REPO, relative)
        assert app_identity == "text:repo://symbi/liuyao-learning-app/lessons/lesson-05.txt"
        assert raw_identity == "text:repo://symbi/liuyao-learning-raw/lessons/lesson-05.txt"
        assert app_identity != raw_identity

    def test_parse_file_never_embeds_local_paths(self, tmp_path: Path) -> None:
        checkout_a = tmp_path / "checkout-a"
        checkout_b = tmp_path / "checkout-b"
        relative = Path("docs/lessons/lesson-05.md")
        for checkout in (checkout_a, checkout_b):
            target = checkout / relative
            target.parent.mkdir(parents=True)
            target.write_text(MARKDOWN_FIXTURE, encoding="utf-8")

        document_a = MarkdownAdapter().parse_file(
            checkout_a / relative, repository=APP_REPO, relative_path=relative
        )
        document_b = MarkdownAdapter().parse_file(
            checkout_b / relative, repository=RAW_REPO, relative_path=relative
        )

        for document in (document_a, document_b):
            assert str(tmp_path) not in document.source_uri
            assert str(tmp_path) not in document.source_identity
            assert "/Users/" not in document.source_uri
        assert document_a.source_identity != document_b.source_identity
        assert document_a.metadata["repository"] == APP_REPO

    def test_revision_ref_is_separate_from_identity(self) -> None:
        uri = repository_source_uri(APP_REPO, "docs/lessons/lesson-05.md")
        first = parse_markdown_text(MARKDOWN_FIXTURE, source_uri=uri, revision_ref="aaa111")
        second = parse_markdown_text(MARKDOWN_FIXTURE, source_uri=uri, revision_ref="bbb222")

        assert first.source_identity == second.source_identity
        assert first.revision_ref != second.revision_ref

    def test_hash_is_stable_across_parses(self) -> None:
        uri = repository_source_uri(APP_REPO, "docs/lessons/lesson-05.md")
        first = parse_markdown_text(MARKDOWN_FIXTURE, source_uri=uri)
        second = parse_markdown_text(MARKDOWN_FIXTURE, source_uri=uri)

        assert first.content_hash == second.content_hash == sha256_text(MARKDOWN_FIXTURE)
        assert first == second

    @pytest.mark.parametrize(
        "repository",
        ["liuyao-learning-app", "symbi/", "/liuyao-learning-app", "a/b/c", "../escape"],
    )
    def test_invalid_repository_slugs_are_rejected(self, repository: str) -> None:
        with pytest.raises(ValueError):
            repository_source_uri(repository, "docs/lessons/lesson-05.md")

    @pytest.mark.parametrize(
        "relative_path",
        ["", "/abs/path.md", "../escape.md", "docs/../../escape.md"],
    )
    def test_invalid_relative_paths_are_rejected(self, relative_path: str) -> None:
        with pytest.raises(ValueError):
            repository_source_uri(APP_REPO, relative_path)
