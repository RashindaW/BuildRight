"""The optional LlamaIndex retriever stays import-safe without the dependency."""

from __future__ import annotations

import importlib.util

import pytest


def test_module_imports_without_llamaindex():
    # Importing the module must never require llama-index.
    from app.ai import llamaindex_retriever  # noqa: F401


def test_builder_raises_clear_error_when_dep_absent():
    from app.ai.llamaindex_retriever import build_kb_retriever
    if importlib.util.find_spec("llama_index") is not None:
        pytest.skip("llama-index installed; guard path not exercised")
    with pytest.raises(ImportError, match="llama-index-core"):
        build_kb_retriever(None)
