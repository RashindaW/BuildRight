"""Lightweight prompt-injection heuristics.

This is a tripwire (log + flag), NOT the primary defense. The real defenses are:
(1) the system prompt's instruction hierarchy + untrusted-input fencing, and
(2) the deterministic output validator. This just flags obvious attempts for
audit/metrics.
"""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"ignore\b[\w\s]{0,30}\b(instructions|rules)", re.I),
    re.compile(r"disregard\b[\w\s]{0,30}\b(above|previous|rules|instructions)", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"pretend (to be|you)", re.I),
    re.compile(r"reveal (your|the) (prompt|instructions|system)", re.I),
    re.compile(r"developer mode", re.I),
]


def looks_like_injection(text: str) -> bool:
    return any(p.search(text) for p in _PATTERNS)
