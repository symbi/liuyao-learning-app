"""Markdown and plain-text source adapters for Phase 1 M2-B.

These adapters convert one source file into the common M2-A
:class:`~liuyao_kb.sources.models.ParsedDocument` representation. They are
pure parsers: no Neo4j, Gemini, network, or other external service is called.

Conventions shared by both adapters:

* ``source_uri`` must be an explicit, stable identifier supplied by the
  caller. Namespaced ``repo://<owner>/<repository>/<relative-path>`` URIs
  (see :func:`liuyao_kb.sources.models.repository_source_uri`) are the
  recommended form, so the same relative path in two repositories produces
  different ``source_identity`` values. Machine absolute paths are rejected
  and are never embedded in a URI or identity. A Git commit or other source
  version is carried separately in ``revision_ref``.
* ``content_hash`` is the SHA-256 of the original UTF-8 bytes, before any
  parsing. Parsing never normalizes or rewrites the text.
* Offsets are character offsets into the decoded text, and for every
  section ``text[locator.start_offset:locator.end_offset] == section.text``.
* A paragraph is a maximal run of non-blank lines. Blank lines (empty or
  whitespace-only) are separators only; every other line's content is
  preserved exactly, including internal line breaks. Nothing else is
  silently dropped.
* Markdown fenced blocks follow the usual fence rules without a full
  CommonMark parser: a fence has at most three leading spaces; a closing
  fence must use the opening character, be at least as long as the opener,
  and carry nothing after it but spaces or tabs. Shorter runs, the other
  fence character, and fence-shaped lines with trailing text are content
  inside the block, never block boundaries.
* Empty and whitespace-only sources raise :class:`EmptySourceError`, and
  bytes that are not valid UTF-8 raise :class:`InvalidSourceEncodingError`.
  An empty source is never reported as a successful zero-content import.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from liuyao_kb.sources.models import (
    MarkdownLocator,
    ParsedDocument,
    ParsedSection,
    SourceType,
    TextLocator,
    build_source_identity,
    repository_source_uri,
    sha256_bytes,
    sha256_text,
)

MARKDOWN_PARSER_VERSION = "markdown-1"
TEXT_PARSER_VERSION = "text-1"


class SourceAdapterError(ValueError):
    """Base error for explicit source adapter failures."""


class EmptySourceError(SourceAdapterError):
    """Raised when a source has no non-whitespace content."""


class InvalidSourceEncodingError(SourceAdapterError):
    """Raised when source bytes are not valid UTF-8."""


_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(\S.*?)[ \t]*$")
# A fence line has at most three leading spaces, then a run of at least
# three backticks or tildes, then the rest of the line (an info string on an
# opening fence; only spaces/tabs on a closing fence).
_FENCE_LINE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_CLOSING_HASHES_RE = re.compile(r"[ \t]+#+$")
_ABSOLUTE_PATH_RE = re.compile(r"^([A-Za-z]:[\\/]|/|\\\\)")


class _Line:
    """One physical line: content span plus the offset of the next line."""

    __slots__ = ("content", "content_end", "start")

    def __init__(self, start: int, content_end: int, content: str) -> None:
        self.start = start
        self.content_end = content_end
        self.content = content


def _iter_lines(text: str) -> list[_Line]:
    """Split text into physical lines without losing any offsets."""

    lines: list[_Line] = []
    position = 0
    length = len(text)
    while position < length:
        newline = text.find("\n", position)
        if newline == -1:
            content_end = length
            next_position = length
        else:
            content_end = (
                newline - 1 if newline > position and text[newline - 1] == "\r" else newline
            )
            next_position = newline + 1
        lines.append(_Line(position, content_end, text[position:content_end]))
        position = next_position
    return lines


def _validate_source_uri(source_uri: str) -> str:
    """Return a stripped explicit source URI, rejecting machine paths."""

    if not isinstance(source_uri, str):
        raise TypeError("source_uri must be a string")
    uri = source_uri.strip()
    if not uri:
        raise ValueError("source_uri must not be empty")
    if _ABSOLUTE_PATH_RE.match(uri) or uri.startswith("file://"):
        raise ValueError("source_uri must be a stable namespaced URI, not a machine absolute path")
    return uri


def _decode_bytes(data: bytes | bytearray | memoryview, source_uri: str) -> str:
    """Decode source bytes as strict UTF-8 with an explicit failure."""

    if isinstance(data, (bytearray, memoryview)):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("parse_bytes expects bytes; use parse_text for str input")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InvalidSourceEncodingError(
            f"Source is not valid UTF-8: {source_uri} (byte offset {error.start}: {error.reason})"
        ) from error


def _require_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("parse_text expects a string")
    return text


def _require_non_empty(text: str, source_uri: str) -> None:
    if not text.strip():
        raise EmptySourceError(f"Source contains no readable content: {source_uri}")


def _paragraph_blocks(lines: list[_Line]) -> list[tuple[int, int]]:
    """Group consecutive non-blank lines into (start, end) paragraph spans."""

    blocks: list[tuple[int, int]] = []
    current: list[_Line] = []
    for line in lines:
        if line.content.strip():
            current.append(line)
        elif current:
            blocks.append((current[0].start, current[-1].content_end))
            current = []
    if current:
        blocks.append((current[0].start, current[-1].content_end))
    return blocks


def _parse_text_document(
    text: str,
    *,
    content_hash: str,
    source_uri: str,
    revision_ref: str | None,
    metadata: Mapping[str, Any] | None,
) -> ParsedDocument:
    _require_non_empty(text, source_uri)
    sections = tuple(
        ParsedSection(
            text=text[start:end],
            ordinal=ordinal,
            locator=TextLocator(paragraph=ordinal + 1, start_offset=start, end_offset=end),
        )
        for ordinal, (start, end) in enumerate(_paragraph_blocks(_iter_lines(text)))
    )
    return ParsedDocument(
        source_type=SourceType.TEXT,
        source_identity=build_source_identity(SourceType.TEXT, source_uri),
        source_uri=source_uri,
        content_hash=content_hash,
        revision_ref=revision_ref,
        parser_version=TEXT_PARSER_VERSION,
        sections=sections,
        metadata=dict(metadata) if metadata else {},
    )


def _is_opening_fence(match: re.Match[str]) -> bool:
    """Whether a fence-shaped line opens a fenced block.

    An opening fence may carry an info string, except that a backtick
    fence's info string must not itself contain a backtick.
    """

    run = match.group(1)
    return run[0] == "~" or "`" not in match.group(2)


def _is_closing_fence(match: re.Match[str], fence_char: str, fence_length: int) -> bool:
    """Whether a fence-shaped line closes the currently open fenced block.

    A closing fence must use the same character as the opener, be at least
    as long as the opener, and have nothing after it but spaces or tabs.
    A shorter run, a different character, or trailing text such as
    ``python`` makes the line ordinary fenced content instead.
    """

    run = match.group(1)
    if run[0] != fence_char or len(run) < fence_length:
        return False
    return not match.group(2).strip(" \t")


def _parse_markdown_document(
    text: str,
    *,
    content_hash: str,
    source_uri: str,
    revision_ref: str | None,
    metadata: Mapping[str, Any] | None,
) -> ParsedDocument:
    _require_non_empty(text, source_uri)

    sections: list[ParsedSection] = []
    paragraph = 0
    title: str | None = None
    current_heading: str | None = None
    current_level: int | None = None
    current_block: list[_Line] = []
    in_fence = False
    fence_char = ""
    fence_length = 0

    def flush_block() -> None:
        nonlocal paragraph
        if not current_block:
            return
        start = current_block[0].start
        end = current_block[-1].content_end
        paragraph += 1
        sections.append(
            ParsedSection(
                text=text[start:end],
                ordinal=len(sections),
                locator=MarkdownLocator(
                    heading=current_heading,
                    heading_level=current_level,
                    paragraph=paragraph,
                    start_offset=start,
                    end_offset=end,
                ),
            )
        )
        current_block.clear()

    for line in _iter_lines(text):
        stripped = line.content.strip()
        fence_match = _FENCE_LINE_RE.match(line.content)
        if in_fence:
            # Fenced content is preserved verbatim: no heading detection and
            # no paragraph split on blank lines inside the fence. Only a
            # valid closing fence (same character, at least the opening
            # length, nothing but spaces/tabs after it, at most three
            # leading spaces) ends the block; every other line is content.
            if fence_match is not None and _is_closing_fence(fence_match, fence_char, fence_length):
                in_fence = False
                fence_char = ""
                fence_length = 0
            current_block.append(line)
            continue
        if fence_match is not None and _is_opening_fence(fence_match):
            run = fence_match.group(1)
            in_fence = True
            fence_char = run[0]
            fence_length = len(run)
            current_block.append(line)
            continue
        heading_match = _HEADING_RE.match(line.content)
        if heading_match is not None:
            flush_block()
            level = len(heading_match.group(1))
            heading_text = _CLOSING_HASHES_RE.sub("", heading_match.group(2)).strip()
            current_heading = heading_text
            current_level = level
            if level == 1 and title is None:
                title = heading_text
            sections.append(
                ParsedSection(
                    text=text[line.start : line.content_end],
                    ordinal=len(sections),
                    locator=MarkdownLocator(
                        heading=heading_text,
                        heading_level=level,
                        paragraph=None,
                        start_offset=line.start,
                        end_offset=line.content_end,
                    ),
                )
            )
            continue
        if not stripped:
            flush_block()
            continue
        current_block.append(line)
    flush_block()

    return ParsedDocument(
        source_type=SourceType.MARKDOWN,
        source_identity=build_source_identity(SourceType.MARKDOWN, source_uri),
        source_uri=source_uri,
        content_hash=content_hash,
        revision_ref=revision_ref,
        parser_version=MARKDOWN_PARSER_VERSION,
        title=title,
        sections=tuple(sections),
        metadata=dict(metadata) if metadata else {},
    )


def _read_file_bytes(path: str | Path) -> bytes:
    """Read a local file's bytes; the path itself never enters the result."""

    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(f"Source file not found: {file_path.name}")
    return file_path.read_bytes()


class TextAdapter:
    """Adapter for plain-text (``.txt``) sources."""

    parser_version = TEXT_PARSER_VERSION

    def parse_bytes(
        self,
        data: bytes | bytearray | memoryview,
        *,
        source_uri: str,
        revision_ref: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ParsedDocument:
        uri = _validate_source_uri(source_uri)
        if isinstance(data, (bytearray, memoryview)):
            data = bytes(data)
        text = _decode_bytes(data, uri)
        return _parse_text_document(
            text,
            content_hash=sha256_bytes(data),
            source_uri=uri,
            revision_ref=revision_ref,
            metadata=metadata,
        )

    def parse_text(
        self,
        text: str,
        *,
        source_uri: str,
        revision_ref: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ParsedDocument:
        uri = _validate_source_uri(source_uri)
        text = _require_text(text)
        return _parse_text_document(
            text,
            content_hash=sha256_text(text),
            source_uri=uri,
            revision_ref=revision_ref,
            metadata=metadata,
        )

    def parse_repository_bytes(
        self,
        data: bytes | bytearray | memoryview,
        *,
        repository: str,
        relative_path: str | Path,
        revision_ref: str | None = None,
    ) -> ParsedDocument:
        """Parse bytes addressed by a namespaced ``repo://`` URI."""

        uri = repository_source_uri(repository, relative_path)
        return self.parse_bytes(
            data,
            source_uri=uri,
            revision_ref=revision_ref,
            metadata={"repository": repository.strip()},
        )

    def parse_file(
        self,
        path: str | Path,
        *,
        repository: str,
        relative_path: str | Path,
        revision_ref: str | None = None,
    ) -> ParsedDocument:
        """Read a local file and parse it under its repository namespace."""

        return self.parse_repository_bytes(
            _read_file_bytes(path),
            repository=repository,
            relative_path=relative_path,
            revision_ref=revision_ref,
        )


class MarkdownAdapter:
    """Adapter for Markdown sources (ATX headings, fenced blocks kept intact)."""

    parser_version = MARKDOWN_PARSER_VERSION

    def parse_bytes(
        self,
        data: bytes | bytearray | memoryview,
        *,
        source_uri: str,
        revision_ref: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ParsedDocument:
        uri = _validate_source_uri(source_uri)
        if isinstance(data, (bytearray, memoryview)):
            data = bytes(data)
        text = _decode_bytes(data, uri)
        return _parse_markdown_document(
            text,
            content_hash=sha256_bytes(data),
            source_uri=uri,
            revision_ref=revision_ref,
            metadata=metadata,
        )

    def parse_text(
        self,
        text: str,
        *,
        source_uri: str,
        revision_ref: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ParsedDocument:
        uri = _validate_source_uri(source_uri)
        text = _require_text(text)
        return _parse_markdown_document(
            text,
            content_hash=sha256_text(text),
            source_uri=uri,
            revision_ref=revision_ref,
            metadata=metadata,
        )

    def parse_repository_bytes(
        self,
        data: bytes | bytearray | memoryview,
        *,
        repository: str,
        relative_path: str | Path,
        revision_ref: str | None = None,
    ) -> ParsedDocument:
        """Parse bytes addressed by a namespaced ``repo://`` URI."""

        uri = repository_source_uri(repository, relative_path)
        return self.parse_bytes(
            data,
            source_uri=uri,
            revision_ref=revision_ref,
            metadata={"repository": repository.strip()},
        )

    def parse_file(
        self,
        path: str | Path,
        *,
        repository: str,
        relative_path: str | Path,
        revision_ref: str | None = None,
    ) -> ParsedDocument:
        """Read a local file and parse it under its repository namespace."""

        return self.parse_repository_bytes(
            _read_file_bytes(path),
            repository=repository,
            relative_path=relative_path,
            revision_ref=revision_ref,
        )


def parse_markdown_bytes(
    data: bytes | bytearray | memoryview,
    *,
    source_uri: str,
    revision_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ParsedDocument:
    """Parse Markdown bytes into a :class:`ParsedDocument`."""

    return MarkdownAdapter().parse_bytes(
        data, source_uri=source_uri, revision_ref=revision_ref, metadata=metadata
    )


def parse_markdown_text(
    text: str,
    *,
    source_uri: str,
    revision_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ParsedDocument:
    """Parse Markdown text into a :class:`ParsedDocument`."""

    return MarkdownAdapter().parse_text(
        text, source_uri=source_uri, revision_ref=revision_ref, metadata=metadata
    )


def parse_text_bytes(
    data: bytes | bytearray | memoryview,
    *,
    source_uri: str,
    revision_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ParsedDocument:
    """Parse plain-text bytes into a :class:`ParsedDocument`."""

    return TextAdapter().parse_bytes(
        data, source_uri=source_uri, revision_ref=revision_ref, metadata=metadata
    )


def parse_text_text(
    text: str,
    *,
    source_uri: str,
    revision_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ParsedDocument:
    """Parse a plain-text string into a :class:`ParsedDocument`."""

    return TextAdapter().parse_text(
        text, source_uri=source_uri, revision_ref=revision_ref, metadata=metadata
    )
