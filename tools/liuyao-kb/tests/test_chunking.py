"""Tests for the deterministic Markdown chunker (Phase 1 M4a).

All fixtures are synthetic. Real pilot files are exercised only by
the read-only trial run reported in the M4a checkpoint, never copied
into fixtures.
"""

from __future__ import annotations

import json
from itertools import pairwise

import pytest

from liuyao_kb.chunking import (
    CHUNKER_VERSION,
    MAX_CHUNK_CHARS,
    Chunk,
    chunk_document,
    chunk_sections,
)
from liuyao_kb.ids import make_document_id, make_revision_id
from liuyao_kb.sources import parse_generated_markdown_bytes
from liuyao_kb.sources.adapters import MarkdownAdapter, TextAdapter
from liuyao_kb.sources.models import MarkdownLocator, ParsedDocument, ParsedSection

REPO = "symbi/liuyao-learning-app"
PATH = "docs/lessons/lesson-19-notes-v0.1.md"
URI = f"repo://{REPO}/{PATH}"
DOC_ID = make_document_id("markdown", REPO, PATH)


def parse(text: str) -> ParsedDocument:
    return MarkdownAdapter().parse_text(text, source_uri=URI)


def chunk(text: str, **kwargs: object):
    return chunk_document(parse(text), document_id=DOC_ID, **kwargs)  # type: ignore[arg-type]


def body_paragraphs(document: ParsedDocument) -> list[ParsedSection]:
    return [
        section
        for section in document.sections
        if isinstance(section.locator, MarkdownLocator) and section.locator.paragraph is not None
    ]


def assert_offsets_restore(source_text: str, result) -> None:  # type: ignore[no-untyped-def]
    for item in result.chunks:
        assert source_text[item.start_offset : item.end_offset] == item.text
        assert item.end_offset - item.start_offset == len(item.text)
        assert len(item.text) <= MAX_CHUNK_CHARS


class TestBasicParagraphs:
    def test_single_paragraph_one_chunk(self) -> None:
        result = chunk("# 标题\n\n这是一个普通段落。\n")
        assert len(result.chunks) == 1
        only = result.chunks[0]
        assert only.text == "这是一个普通段落。"
        assert only.paragraph_ordinal == 0
        assert only.subchunk_index == 0
        assert only.heading_path == ("标题",)
        assert only.chunker_version == CHUNKER_VERSION
        assert result.stats.paragraphs == 1
        assert result.stats.chunks == 1

    def test_multiple_paragraphs_stay_separate(self) -> None:
        result = chunk("第一段。\n\n第二段。\n\n第三段。\n")
        assert [c.text for c in result.chunks] == ["第一段。", "第二段。", "第三段。"]
        assert [c.paragraph_ordinal for c in result.chunks] == [0, 1, 2]

    def test_short_paragraphs_are_never_merged(self) -> None:
        result = chunk("短。\n\n短。\n\n短。\n")
        assert len(result.chunks) == 3
        assert all(len(c.text) == 2 for c in result.chunks)

    def test_blank_lines_produce_no_chunks(self) -> None:
        result = chunk("\n\n\n段落一。\n\n\n\n段落二。\n\n\n")
        assert [c.text for c in result.chunks] == ["段落一。", "段落二。"]
        assert result.stats.empty_paragraphs_skipped == 0  # adapter drops blanks upstream

    def test_whitespace_only_section_is_skipped_by_chunker(self) -> None:
        section = ParsedSection(
            text="   \n  ",
            ordinal=0,
            locator=MarkdownLocator(
                heading=None, heading_level=None, paragraph=1, start_offset=0, end_offset=6
            ),
        )
        result = chunk_sections([section], document_id=DOC_ID)
        assert result.chunks == ()
        assert result.stats.empty_paragraphs_skipped == 1
        assert result.stats.paragraphs == 0

    def test_multiline_paragraph_keeps_internal_line_breaks(self) -> None:
        source = "第一行\n第二行\n"
        result = chunk(source)
        assert len(result.chunks) == 1
        assert result.chunks[0].text == "第一行\n第二行"
        assert_offsets_restore(source, result)


class TestHeadingPaths:
    def test_nested_heading_path(self) -> None:
        source = "# 一级\n\n## 二级\n\n### 三级\n\n正文。\n\n## 二级之二\n\n正文二。\n"
        result = chunk(source)
        assert result.chunks[0].heading_path == ("一级", "二级", "三级")
        assert result.chunks[1].heading_path == ("一级", "二级之二")
        assert result.stats.heading_sections == 4

    def test_paragraph_before_first_heading_has_empty_path(self) -> None:
        result = chunk("卷首语。\n\n# 标题\n\n正文。\n")
        assert result.chunks[0].heading_path == ()
        assert result.chunks[1].heading_path == ("标题",)

    def test_heading_sections_produce_no_chunks(self) -> None:
        result = chunk("# 只有标题\n\n## 还是标题\n")
        assert result.chunks == ()
        assert result.stats.heading_sections == 2
        assert result.stats.paragraphs == 0


class TestLengthAndSplitting:
    def test_boundary_lengths(self) -> None:
        for length, expected_chunks in ((1199, 1), (1200, 1), (1201, 2)):
            result = chunk("字" * length)
            assert len(result.chunks) == expected_chunks
            assert all(len(c.text) <= MAX_CHUNK_CHARS for c in result.chunks)
            assert "".join(c.text for c in result.chunks) == "字" * length

    def test_chinese_sentences_pack_greedily(self) -> None:
        sentence = "句" * 99 + "。"  # 100 chars per sentence
        paragraph = sentence * 15  # 1500 chars -> 1200 + 300
        result = chunk(paragraph)
        assert len(result.chunks) == 2
        assert len(result.chunks[0].text) == 1200
        assert len(result.chunks[1].text) == 300
        assert result.chunks[0].text.endswith("。")
        assert [c.subchunk_index for c in result.chunks] == [0, 1]
        assert result.stats.split_paragraphs == 1

    def test_english_sentences_pack_and_preserve_spaces(self) -> None:
        sentence = "Alpha beta gamma. "  # 18 chars, ends with ". "
        paragraph = sentence * 100  # 1800 chars
        result = chunk(paragraph)
        assert "".join(c.text for c in result.chunks) == paragraph
        assert all(len(c.text) <= MAX_CHUNK_CHARS for c in result.chunks)
        # Every chunk boundary falls at a sentence edge: each chunk
        # except possibly the last ends with the sentence-final "."
        # (the following space opens the next sentence's span).
        for item in result.chunks[:-1]:
            assert item.text.endswith(".")

    def test_mixed_terminal_punctuation(self) -> None:
        paragraph = ("问" * 400 + "？") + ("叹" * 400 + "！") + ("述" * 400 + "。")  # noqa: RUF001
        result = chunk(paragraph)
        # 401 + 401 fit together (802 <= 1200); the third stands alone.
        assert [len(c.text) for c in result.chunks] == [802, 401]
        assert result.chunks[0].text.endswith("！")  # noqa: RUF001
        assert "".join(c.text for c in result.chunks) == paragraph

    def test_single_oversized_sentence_hard_splits(self) -> None:
        paragraph = "连" * 2500
        result = chunk(paragraph)
        assert [len(c.text) for c in result.chunks] == [1200, 1200, 100]
        assert [c.subchunk_index for c in result.chunks] == [0, 1, 2]
        assert "".join(c.text for c in result.chunks) == paragraph

    def test_decimal_points_and_domains_are_not_boundaries(self) -> None:
        paragraph = "值为3.14，见 example.com 的说明。" * 100  # noqa: RUF001
        result = chunk(paragraph)
        assert "".join(c.text for c in result.chunks) == paragraph
        joined = "".join(c.text for c in result.chunks)
        assert joined.count("3.14") == 100
        assert joined.count("example.com") == 100
        for item in result.chunks:
            assert "3.14" not in item.text or item.text.count("3.14") >= 1
            assert not item.text.endswith("3.")
            assert not item.text.startswith("14，")  # noqa: RUF001

    def test_emoji_and_non_bmp_characters_count_as_single_chars(self) -> None:
        paragraph = "😀" * 1201  # len() == 1201 in Python
        result = chunk(paragraph)
        assert [len(c.text) for c in result.chunks] == [1200, 1]
        mixed = "𐍈" * 600 + "。" + "😀" * 500  # 1101 chars, one paragraph
        result = chunk(mixed)
        assert len(result.chunks) == 1
        assert result.chunks[0].text == mixed

    def test_no_character_is_lost_duplicated_or_reordered(self) -> None:
        samples = [
            "第一句。第二句！第三句？第四句；第五句。",  # noqa: RUF001
            "No punctuation at all " + "x" * 2000,
            '带"引号"的句子。"被引用的话。"后续内容。',
            "省略号……后面还有。Next sentence here. 结束了",
            "多\n行\n段落。\n第二行继续" + "长" * 1300,
        ]
        for sample in samples:
            document = parse(sample)
            result = chunk_document(document, document_id=DOC_ID)
            paragraphs = body_paragraphs(document)
            assert len(paragraphs) == 1
            assert "".join(c.text for c in result.chunks) == paragraphs[0].text
            assert_offsets_restore(sample, result)


class TestOffsets:
    def test_offsets_restore_every_chunk(self) -> None:
        source = "# 标题\n\n第一段文字。\n\n## 小节\n\n第二段文字，比较长。\n"  # noqa: RUF001
        result = chunk(source)
        assert_offsets_restore(source, result)

    def test_subchunk_offsets_are_contiguous(self) -> None:
        source = "前" * 10 + "\n\n" + "句" * 3000 + "\n\n" + "后" * 10
        result = chunk(source)
        middle = [c for c in result.chunks if c.paragraph_ordinal == 1]
        assert len(middle) == 3
        for previous, following in pairwise(middle):
            assert previous.end_offset == following.start_offset
        assert_offsets_restore(source, result)

    def test_chunk_spans_never_overlap(self) -> None:
        source = "# T\n\n" + "甲" * 500 + "\n\n" + "乙" * 1500 + "\n\n" + "丙" * 700
        result = chunk(source)
        spans = sorted((c.start_offset, c.end_offset) for c in result.chunks)
        for (_, prev_end), (next_start, _) in pairwise(spans):
            assert prev_end <= next_start


class TestChunkIdStability:
    def test_repeat_runs_are_identical(self) -> None:
        source = "# 题\n\n段落一。\n\n段落二比较长" + "长" * 1300 + "\n\n段落三。\n"
        first = chunk(source)
        second = chunk(source)
        assert [c.chunk_id for c in first.chunks] == [c.chunk_id for c in second.chunks]
        assert first == second

    def test_identical_paragraphs_get_distinct_ids(self) -> None:
        result = chunk("相同段落。\n\n相同段落。\n")
        assert len(result.chunks) == 2
        assert result.chunks[0].text_hash == result.chunks[1].text_hash
        assert result.chunks[0].chunk_id != result.chunks[1].chunk_id

    def test_editing_one_paragraph_changes_only_its_ids(self) -> None:
        before = chunk("段落甲。\n\n段落乙。\n\n段落丙。\n")
        after = chunk("段落甲。\n\n段落乙被修改了。\n\n段落丙。\n")
        assert before.chunks[0].chunk_id == after.chunks[0].chunk_id
        assert before.chunks[1].chunk_id != after.chunks[1].chunk_id
        assert before.chunks[2].chunk_id == after.chunks[2].chunk_id

    def test_length_change_does_not_move_later_ids(self) -> None:
        before = chunk("甲。\n\n乙。\n\n丙。\n")
        after = chunk("甲。\n\n" + "乙" * 900 + "。\n\n丙。\n")
        assert before.chunks[2].start_offset != after.chunks[2].start_offset  # offsets moved
        assert before.chunks[2].chunk_id == after.chunks[2].chunk_id  # identity did not

    def test_editing_into_a_duplicate_keeps_the_other_paragraphs_id(self) -> None:
        # The case a content-occurrence index would fail: paragraph 2
        # becomes a duplicate of paragraph 0; paragraph 2's own later
        # twin (paragraph 3... here paragraph index 2) must not move.
        before = chunk("同文。\n\n异文。\n\n同文。\n")
        after = chunk("同文。\n\n同文。\n\n同文。\n")
        assert before.chunks[0].chunk_id == after.chunks[0].chunk_id
        assert before.chunks[2].chunk_id == after.chunks[2].chunk_id

    def test_subchunk_ids_are_unique_and_repeatable(self) -> None:
        source = "长" * 2500
        first = chunk(source)
        second = chunk(source)
        ids = [c.chunk_id for c in first.chunks]
        assert len(set(ids)) == len(ids) == 3
        assert ids == [c.chunk_id for c in second.chunks]

    def test_chunker_version_change_creates_a_new_id_space(self) -> None:
        source = "段落。\n"
        v1 = chunk(source)
        v2 = chunk(source, chunker_version="chunker-2")
        assert v2.chunker_version == "chunker-2"
        assert v1.chunks[0].chunk_id != v2.chunks[0].chunk_id
        assert v1.chunks[0].text == v2.chunks[0].text

    def test_heading_rename_does_not_change_body_chunk_ids(self) -> None:
        before = chunk("# 旧标题\n\n正文不变。\n")
        after = chunk("# 新标题\n\n正文不变。\n")
        assert before.chunks[0].chunk_id == after.chunks[0].chunk_id
        assert after.chunks[0].heading_path == ("新标题",)

    def test_revision_id_is_provenance_not_identity(self) -> None:
        document = parse("段落。\n")
        sections = document.sections
        first = chunk_sections(sections, document_id=DOC_ID, revision_id="doc|rev-a")
        second = chunk_sections(sections, document_id=DOC_ID, revision_id="doc|rev-b")
        assert [c.chunk_id for c in first.chunks] == [c.chunk_id for c in second.chunks]
        assert first.chunks[0].revision_id == "doc|rev-a"
        assert second.chunks[0].revision_id == "doc|rev-b"

    def test_revision_id_defaults_to_content_derived_value(self) -> None:
        document = parse("段落。\n")
        result = chunk_document(document, document_id=DOC_ID)
        expected = make_revision_id(DOC_ID, document.content_hash)
        assert result.revision_id == expected
        assert all(c.revision_id == expected for c in result.chunks)


class TestRevisionOccurrenceLayering:
    """One chunk_id, two revisions: the occurrences coexist.

    The Chunk DTO carries a stable identity layer (chunk_id, text,
    text_hash, chunker_version) and a revision-specific locator
    layer (revision_id, heading_path, offsets). The same paragraph
    appearing in two revisions under different headings keeps its
    chunk_id while its locators differ — in Neo4j that is one
    Chunk node with two CONTAINS relationships, so the two DTOs
    must be able to exist side by side without overwriting.
    """

    def test_same_paragraph_in_two_revisions_shares_id_not_locators(self) -> None:
        first = chunk("# 甲标题\n\n相同正文段落。\n")
        second = chunk("# 更长的乙标题\n\n相同正文段落。\n")
        a, b = first.chunks[0], second.chunks[0]
        # Identity layer is shared.
        assert a.chunk_id == b.chunk_id
        assert a.text == b.text
        assert a.text_hash == b.text_hash
        assert a.chunker_version == b.chunker_version
        # Locator layer differs per revision.
        assert a.revision_id != b.revision_id
        assert a.heading_path == ("甲标题",)
        assert b.heading_path == ("更长的乙标题",)
        assert a.start_offset != b.start_offset
        # Both occurrences coexist independently.
        occurrences = {(c.revision_id, c.chunk_id): c for c in (a, b)}
        assert len(occurrences) == 2
        assert occurrences[(a.revision_id, a.chunk_id)].heading_path == ("甲标题",)
        assert occurrences[(b.revision_id, b.chunk_id)].heading_path == ("更长的乙标题",)

    def test_dto_objects_with_same_id_are_independent(self) -> None:
        shared = {
            "chunk_id": "doc|chunker-1|0|0|" + "a" * 64,
            "document_id": "doc",
            "text": "正文",
            "text_hash": "a" * 64,
            "chunker_version": CHUNKER_VERSION,
        }
        one = Chunk(
            **shared,
            revision_id="doc|rev-1",
            heading_path=("标题一",),
            paragraph_ordinal=0,
            subchunk_index=0,
            start_offset=10,
            end_offset=12,
        )
        two = Chunk(
            **shared,
            revision_id="doc|rev-2",
            heading_path=("标题二", "小节"),
            paragraph_ordinal=0,
            subchunk_index=0,
            start_offset=42,
            end_offset=44,
        )
        assert one.chunk_id == two.chunk_id
        assert one != two
        assert one.revision_id != two.revision_id
        assert one.heading_path != two.heading_path
        assert (one.start_offset, one.end_offset) != (two.start_offset, two.end_offset)


class TestChunkModel:
    def test_span_must_match_text_length(self) -> None:
        with pytest.raises(ValueError):
            Chunk(
                chunk_id="x",
                document_id=DOC_ID,
                text="abc",
                text_hash="a" * 64,
                paragraph_ordinal=0,
                subchunk_index=0,
                start_offset=0,
                end_offset=2,
                chunker_version=CHUNKER_VERSION,
            )


class TestAdapterIntegration:
    def test_table_and_list_blocks_are_chunked_not_dropped(self) -> None:
        source = (
            "# 数据\n\n"
            "| 列一 | 列二 |\n| --- | --- |\n| 甲 | 乙 |\n\n"
            "- 项目一\n- 项目二\n- 项目三\n"
        )
        result = chunk(source)
        joined = "\n".join(c.text for c in result.chunks)
        assert "| 甲 | 乙 |" in joined
        assert "- 项目二" in joined
        assert_offsets_restore(source, result)

    def test_fenced_block_is_one_paragraph_and_keeps_blank_lines(self) -> None:
        source = "说明。\n\n```text\n第一行\n\n第三行\n```\n"
        result = chunk(source)
        fence_chunks = [c for c in result.chunks if "```text" in c.text]
        assert len(fence_chunks) == 1
        assert "第一行\n\n第三行" in fence_chunks[0].text
        assert_offsets_restore(source, result)

    def test_text_documents_are_rejected(self) -> None:
        document = TextAdapter().parse_text("plain text", source_uri="repo://r/x.txt")
        with pytest.raises(ValueError, match="Markdown"):
            chunk_document(document, document_id=DOC_ID)

    def test_daily_markdown_embedded_json_never_reaches_chunks(self) -> None:
        record_id = "11111111-2222-3333-4444-555555555555"
        payload = json.dumps({"id": record_id, "schemaVersion": 99})
        markdown = (
            "# Synthetic Daily Record\n\n"
            "## Teacher Memo\n\n"
            "synthetic memo body\n\n"
            "## 原始记录 JSON\n\n"
            f"```json\n{payload}\n```\n"
        )
        mapping = parse_generated_markdown_bytes(
            markdown.encode("utf-8"),
            source_uri=f"repo://{REPO}/daily-records/2026/11/markdown/2026-11-21--{record_id}.md",
        )
        result = chunk_sections(mapping.body_sections, document_id=DOC_ID)
        assert result.chunks  # the memo body is chunked
        for item in result.chunks:
            assert "原始记录" not in item.text
            assert "schemaVersion" not in item.text
            assert record_id not in item.text

    def test_case_markdown_shape_chunks_with_heading_paths(self) -> None:
        source = (
            "# 第十九课案例：合成\n\n"  # noqa: RUF001
            "> **匹配状态：已匹配（verified）**\n\n"  # noqa: RUF001
            "## 1. 资料链与匹配依据\n\n"
            "合成案例正文第一段。\n\n"
            "合成案例正文第二段。\n"
        )
        result = chunk(source)
        assert len(result.chunks) == 3
        assert result.chunks[-1].heading_path == ("第十九课案例：合成", "1. 资料链与匹配依据")  # noqa: RUF001
        assert_offsets_restore(source, result)
