"""Markdown document chunking for the knowledge base.

Splits a Markdown string by H2/H3 headings (after stripping the H1 title),
then applies a token-aware sliding window (≈256 tokens, 32 overlap) within
each section.  Tracks the nearest heading so chunks can be cited as
'Document Title › Heading'.

Pure function — no I/O, fully deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_APPROX_TOKENS_PER_WORD = 1.3


def _approx_tokens(text: str) -> int:
    return int(len(text.split()) * _APPROX_TOKENS_PER_WORD)


@dataclass
class RawChunk:
    chunk_index: int
    heading: str | None
    content: str
    token_count: int


def chunk_document(text: str, max_tokens: int = 256, overlap_tokens: int = 32) -> list[RawChunk]:
    """Return a list of RawChunk objects for a Markdown document.

    Strategy:
    1. Split on H1/H2/H3 headings to preserve semantic sections.
    2. For each section, slide a window of max_tokens (measured in approximate
       word-token count) with an overlap_tokens prefix from the previous window.
    3. H1 is treated as the document title and not used as a section heading.
    """
    sections = _split_by_headings(text)
    chunks: list[RawChunk] = []
    idx = 0
    for heading, body in sections:
        body = body.strip()
        if not body:
            continue
        words = body.split()
        window_words = _tokens_to_words(max_tokens)
        overlap_words = _tokens_to_words(overlap_tokens)
        if len(words) <= window_words:
            chunk_text = f"{heading}\n\n{body}" if heading else body
            chunks.append(RawChunk(
                chunk_index=idx,
                heading=heading,
                content=chunk_text.strip(),
                token_count=_approx_tokens(chunk_text),
            ))
            idx += 1
        else:
            start = 0
            while start < len(words):
                window = words[start: start + window_words]
                chunk_text_parts = []
                if heading:
                    chunk_text_parts.append(heading)
                    chunk_text_parts.append("")
                chunk_text_parts.append(" ".join(window))
                chunk_text = "\n".join(chunk_text_parts).strip()
                chunks.append(RawChunk(
                    chunk_index=idx,
                    heading=heading,
                    content=chunk_text,
                    token_count=_approx_tokens(chunk_text),
                ))
                idx += 1
                step = window_words - overlap_words
                start += max(1, step)
    return chunks


def _tokens_to_words(tokens: int) -> int:
    return max(1, int(tokens / _APPROX_TOKENS_PER_WORD))


def _split_by_headings(text: str) -> list[tuple[str | None, str]]:
    """Split text into (heading, body) pairs at H2/H3 boundaries.

    The H1 title (if present) is stripped; its body up to the first H2 is
    included as an un-headed section.
    """
    lines = text.splitlines(keepends=True)
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    buffer: list[str] = []

    for line in lines:
        m = _HEADING_RE.match(line.rstrip("\n"))
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            if level == 1:
                # H1 is document title — flush any preceding buffer, start fresh
                if buffer:
                    sections.append((current_heading, "".join(buffer)))
                current_heading = None
                buffer = []
            else:
                # H2 or H3 marks a new section
                if buffer:
                    sections.append((current_heading, "".join(buffer)))
                current_heading = title
                buffer = []
        else:
            buffer.append(line)

    if buffer:
        sections.append((current_heading, "".join(buffer)))
    return sections
