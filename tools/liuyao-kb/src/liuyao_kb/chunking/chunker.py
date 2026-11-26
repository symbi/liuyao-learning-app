"""Deterministic Markdown chunker (Phase 1 M4a).

The chunker consumes the M2 Markdown adapter's output
(:class:`~liuyao_kb.sources.models.ParsedDocument` /
:class:`~liuyao_kb.sources.models.ParsedSection`) and cuts it into
:class:`Chunk` records for the M4b importer. It is a pure function of
its inputs: no database, no network, no model calls, and the same
input with the same ``chunker_version`` always produces byte-identical
output.

Fixed v1 rules (user decision 2026-11-25, recorded in the
implementation plan section 8 — do not change casually):

* One non-empty Markdown body paragraph produces one Chunk. Short
  paragraphs are never merged; there is no overlap.
* A Chunk holds at most ``MAX_CHUNK_CHARS`` (1,200) Unicode
  characters, counted as Python string length (code points), never
  UTF-8 bytes.
* A longer paragraph is split first at sentence boundaries — as
  many whole sentences as fit are packed into one Chunk — and a
  single sentence that is still too long is hard-split at
  deterministic character boundaries. Splitting never drops,
  duplicates, or reorders a character: concatenating a paragraph's
  chunk texts reproduces the paragraph exactly.
* Heading sections produce no Chunk; they maintain the
  ``heading_path`` hierarchy carried by the following body chunks.

Offsets are 0-based half-open ``[start_offset, end_offset)``
character offsets into the decoded source text of the document
revision — the same coordinate space the Markdown adapter uses, so
``source_text[chunk.start_offset:chunk.end_offset] == chunk.text``
holds for every chunk by construction (the adapter guarantees it for
sections, and every chunk is an exact slice of one section).

Chunk identity follows :func:`liuyao_kb.ids.make_chunk_id`:
``document_id + chunker_version + paragraph_ordinal +
subchunk_index + chunk_text_hash``. Neither ``revision_id`` nor the
absolute offsets take part, so editing one paragraph re-identifies
only that paragraph's chunks.

Known v1 boundaries:

* Fenced code blocks are body blocks for the adapter, so they are
  chunked like other paragraphs; an oversized fence is split by the
  same sentence/character rules (code has few sentence boundaries,
  so it is usually hard-split). No code-aware splitting in v1.
* Tables and lists are ordinary multi-line paragraph blocks for the
  adapter and are chunked as such; no row/cell structure is added.
* Sentence-boundary recognition is a small deterministic rule set
  (see :func:`_sentence_spans`), not a linguistic segmenter.
* The daily-record generated Markdown is NOT chunked from the raw
  adapter output: its embedded ``## 原始记录 JSON`` section is
  excluded upstream by the M2-C2 mapping, and the importer feeds
  the chunker that mapping's ``body_sections`` via
  :func:`chunk_sections`. Chunking a raw daily file directly would
  re-include the embedded JSON — the chunker cannot detect it.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from liuyao_kb.ids import hash_text, make_chunk_id, make_revision_id
from liuyao_kb.sources.models import MarkdownLocator, ParsedDocument, ParsedSection

#: Version token recorded on every chunk and inside every chunk_id.
#: Bump it whenever the splitting rules change; a new version is a
#: new chunk-ID space for the whole document by design.
CHUNKER_VERSION = "chunker-1"

#: Maximum number of Unicode characters (Python string length) in
#: one Chunk under the v1 rules.
MAX_CHUNK_CHARS = 1200

# Sentence-ending punctuation that always closes a sentence,
# whether or not a space follows (the CJK marks) — the ASCII marks
# are included because in this corpus they are used the same way.
_SENTENCE_ENDERS = frozenset("。！？；!?;")  # noqa: RUF001 — the fullwidth marks are the subject
# Closing quotes/brackets that belong to the sentence they follow.
_CLOSERS = frozenset("」』〕】〉》”’\"'）)]")  # noqa: RUF001 — same
_ELLIPSIS = "…"


class Chunk(BaseModel):
    """One retrievable text chunk of one document revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    #: The revision this chunk was cut from. Carried for provenance
    #: only; it is NOT part of the chunk's identity.
    revision_id: str | None = None
    text: str = Field(min_length=1)
    #: SHA-256 of ``text`` (the same value embedded in ``chunk_id``).
    text_hash: str
    #: Heading hierarchy in effect at this chunk, outermost first.
    #: Empty when the paragraph precedes the first heading.
    heading_path: tuple[str, ...] = ()
    #: 0-based ordinal of the body paragraph within the chunked
    #: section sequence (heading sections and skipped empty sections
    #: do not consume an ordinal).
    paragraph_ordinal: int = Field(ge=0)
    #: 0-based index of this chunk inside its paragraph; 0 unless
    #: the paragraph was split for length.
    subchunk_index: int = Field(ge=0)
    #: 0-based half-open offsets into the revision's source text.
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    chunker_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _span_matches_text(self) -> Chunk:
        if self.end_offset - self.start_offset != len(self.text):
            raise ValueError(
                "end_offset - start_offset must equal len(text): chunks are "
                "exact slices of the source text"
            )
        return self


class ChunkingStats(BaseModel):
    """Counts describing one chunking run (no source text)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    #: Body paragraphs consumed (each produced at least one chunk).
    paragraphs: int = Field(ge=0)
    #: Heading sections consumed (they produce no chunks).
    heading_sections: int = Field(ge=0)
    #: Whitespace-only body sections skipped without a chunk.
    empty_paragraphs_skipped: int = Field(ge=0)
    chunks: int = Field(ge=0)
    #: Paragraphs that produced more than one chunk.
    split_paragraphs: int = Field(ge=0)
    max_chunk_chars: int = Field(ge=0)
    total_chunk_chars: int = Field(ge=0)


class ChunkingResult(BaseModel):
    """The chunks cut from one document (or section sequence)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    revision_id: str | None = None
    chunker_version: str = Field(min_length=1)
    chunks: tuple[Chunk, ...] = ()
    stats: ChunkingStats


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Split ``text`` into contiguous sentence spans covering it fully.

    Deterministic v1 rules:

    * The CJK sentence-ending marks (ideographic full stop and the
      fullwidth exclamation, question and semicolon marks) and the
      ASCII marks ``! ? ;`` close a sentence; a following run of
      closing quotes/brackets belongs to that sentence.
    * A run of ``…`` closes a sentence the same way.
    * An ASCII ``.`` closes a sentence only when it is not between
      two digits (decimal points) and is followed by whitespace, a
      closing quote/bracket, or the end of the text — so domains
      and file names (``example.com``) stay intact. A run of dots
      (``...``) counts as one ending.
    * A trailing fragment without terminal punctuation is a final
      span. The spans are contiguous and ordered: joining the span
      texts reproduces ``text`` exactly.
    """
    spans: list[tuple[int, int]] = []
    start = 0
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        end: int | None = None
        if char in _SENTENCE_ENDERS:
            end = index + 1
        elif char == _ELLIPSIS:
            end = index
            while end < length and text[end] == _ELLIPSIS:
                end += 1
        elif char == ".":
            run_end = index
            while run_end < length and text[run_end] == ".":
                run_end += 1
            before = text[index - 1] if index > 0 else ""
            after = text[run_end] if run_end < length else ""
            is_decimal = before.isdigit() and after.isdigit()
            is_followed_by_break = run_end >= length or after.isspace() or after in _CLOSERS
            if not is_decimal and is_followed_by_break:
                end = run_end
            else:
                index = run_end
                continue
        if end is None:
            index += 1
            continue
        while end < length and text[end] in _CLOSERS:
            end += 1
        spans.append((start, end))
        start = end
        index = end
    if start < length:
        spans.append((start, length))
    return spans


def _split_paragraph(text: str) -> list[tuple[int, int]]:
    """Cut one paragraph into contiguous spans of at most MAX_CHUNK_CHARS.

    Whole sentences are packed greedily; a sentence longer than the
    cap is hard-split at exact character boundaries. The returned
    spans are contiguous and ordered, and joining their texts
    reproduces ``text`` exactly.
    """
    if len(text) <= MAX_CHUNK_CHARS:
        return [(0, len(text))]
    pieces: list[tuple[int, int]] = []
    current_start: int | None = None
    current_end = 0
    for span_start, span_end in _sentence_spans(text):
        if span_end - span_start > MAX_CHUNK_CHARS:
            if current_start is not None:
                pieces.append((current_start, current_end))
                current_start = None
            position = span_start
            while position < span_end:
                piece_end = min(position + MAX_CHUNK_CHARS, span_end)
                pieces.append((position, piece_end))
                position = piece_end
            continue
        if current_start is None:
            current_start, current_end = span_start, span_end
        elif span_end - current_start <= MAX_CHUNK_CHARS:
            current_end = span_end
        else:
            pieces.append((current_start, current_end))
            current_start, current_end = span_start, span_end
    if current_start is not None:
        pieces.append((current_start, current_end))
    return pieces


def _require_document_id(document_id: str) -> str:
    if not isinstance(document_id, str) or not document_id or document_id != document_id.strip():
        raise ValueError(f"document_id must be a non-empty composed id, got {document_id!r}")
    return document_id


def chunk_sections(
    sections: Iterable[ParsedSection],
    *,
    document_id: str,
    revision_id: str | None = None,
    chunker_version: str = CHUNKER_VERSION,
) -> ChunkingResult:
    """Cut chunks from an explicit sequence of parsed sections.

    ``sections`` must come from the Markdown adapter (every locator
    a :class:`MarkdownLocator`); anything else raises ``ValueError``
    — this chunker is Markdown-only by design. Heading sections
    update the heading path and produce no chunk; body sections are
    chunked per the v1 rules. ``paragraph_ordinal`` counts body
    paragraphs within *this* sequence, so callers chunking a subset
    (for example a daily record's ``body_sections``) get ordinals
    relative to that subset.
    """
    document_id = _require_document_id(document_id)
    chunks: list[Chunk] = []
    heading_stack: list[tuple[int, str]] = []
    paragraphs = 0
    heading_sections = 0
    empty_skipped = 0
    split_paragraphs = 0
    max_chunk_chars = 0
    total_chunk_chars = 0

    for section in sections:
        locator = section.locator
        if not isinstance(locator, MarkdownLocator):
            raise ValueError(
                "chunker-1 accepts Markdown sections only; got locator of type "
                f"{type(locator).__name__} — parse the source with the Markdown adapter"
            )
        if locator.paragraph is None:
            # A heading section: update the hierarchy, emit nothing.
            heading_sections += 1
            level = locator.heading_level if locator.heading_level is not None else 1
            heading_text = locator.heading if locator.heading is not None else section.text
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading_text))
            continue
        if not section.text.strip():
            empty_skipped += 1
            continue
        paragraph_ordinal = paragraphs
        paragraphs += 1
        heading_path = tuple(text for _, text in heading_stack)
        pieces = _split_paragraph(section.text)
        if len(pieces) > 1:
            split_paragraphs += 1
        for subchunk_index, (piece_start, piece_end) in enumerate(pieces):
            piece_text = section.text[piece_start:piece_end]
            text_hash = hash_text(piece_text)
            chunks.append(
                Chunk(
                    chunk_id=make_chunk_id(
                        document_id,
                        chunker_version,
                        paragraph_ordinal,
                        subchunk_index,
                        text_hash,
                    ),
                    document_id=document_id,
                    revision_id=revision_id,
                    text=piece_text,
                    text_hash=text_hash,
                    heading_path=heading_path,
                    paragraph_ordinal=paragraph_ordinal,
                    subchunk_index=subchunk_index,
                    start_offset=locator.start_offset + piece_start,
                    end_offset=locator.start_offset + piece_end,
                    chunker_version=chunker_version,
                )
            )
            max_chunk_chars = max(max_chunk_chars, len(piece_text))
            total_chunk_chars += len(piece_text)

    return ChunkingResult(
        document_id=document_id,
        revision_id=revision_id,
        chunker_version=chunker_version,
        chunks=tuple(chunks),
        stats=ChunkingStats(
            paragraphs=paragraphs,
            heading_sections=heading_sections,
            empty_paragraphs_skipped=empty_skipped,
            chunks=len(chunks),
            split_paragraphs=split_paragraphs,
            max_chunk_chars=max_chunk_chars,
            total_chunk_chars=total_chunk_chars,
        ),
    )


def chunk_document(
    document: ParsedDocument,
    *,
    document_id: str,
    revision_id: str | None = None,
    chunker_version: str = CHUNKER_VERSION,
) -> ChunkingResult:
    """Cut chunks from one parsed Markdown document.

    ``document_id`` is the document's stable identity (see
    :func:`liuyao_kb.ids.make_document_id`), supplied by the caller
    because it is composed from source type, repository and path —
    facts the parsed document alone does not carry. When
    ``revision_id`` is omitted it is derived deterministically as
    ``make_revision_id(document_id, document.content_hash)``.
    """
    document_id = _require_document_id(document_id)
    if revision_id is None:
        revision_id = make_revision_id(document_id, document.content_hash)
    return chunk_sections(
        document.sections,
        document_id=document_id,
        revision_id=revision_id,
        chunker_version=chunker_version,
    )


__all__ = [
    "CHUNKER_VERSION",
    "MAX_CHUNK_CHARS",
    "Chunk",
    "ChunkingResult",
    "ChunkingStats",
    "chunk_document",
    "chunk_sections",
]
