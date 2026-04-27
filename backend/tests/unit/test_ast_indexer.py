"""Unit tests for the Python AST indexer."""

from __future__ import annotations

import pytest

from src.services.indexing.ast_indexer import index_python


# ── helpers ───────────────────────────────────────────────────────────────────


def symbols_by_name(source: str, file_path: str = "test.py") -> dict[str, object]:
    return {s.name: s for s in index_python(file_path, source)}


# ── module-level functions ────────────────────────────────────────────────────


def test_extracts_simple_function() -> None:
    source = """\
def greet(name: str) -> str:
    \"\"\"Say hello.\"\"\"
    return f"Hello, {name}"
"""
    result = index_python("test.py", source)
    assert len(result) == 1
    sym = result[0]
    assert sym.name == "greet"
    assert sym.symbol_type == "function"
    assert sym.docstring == "Say hello."
    assert sym.line_number == 1
    assert "name" in sym.signature


def test_extracts_async_function() -> None:
    source = "async def fetch(url: str) -> bytes: ...\n"
    result = index_python("test.py", source)
    assert len(result) == 1
    assert result[0].name == "fetch"
    assert result[0].symbol_type == "function"


def test_skips_private_functions() -> None:
    source = """\
def public(): ...
def _private(): ...
def __dunder__(): ...
"""
    names = {s.name for s in index_python("test.py", source)}
    assert names == {"public"}


def test_function_without_docstring() -> None:
    source = "def no_doc(): ...\n"
    result = index_python("test.py", source)
    assert result[0].docstring is None


def test_function_signature_defaults() -> None:
    source = "def fn(a, b=1, *args, c, d=2, **kw): ...\n"
    sig = index_python("test.py", source)[0].signature
    assert "b=..." in sig
    assert "*args" in sig
    assert "d=..." in sig
    assert "**kw" in sig


def test_function_signature_keyword_only() -> None:
    source = "def fn(*, kw_only): ...\n"
    sig = index_python("test.py", source)[0].signature
    assert "*" in sig
    assert "kw_only" in sig


# ── classes ───────────────────────────────────────────────────────────────────


def test_extracts_class() -> None:
    source = """\
class MyService:
    \"\"\"A service.\"\"\"

    def run(self, x: int) -> None:
        \"\"\"Run it.\"\"\"
        ...
"""
    result = index_python("test.py", source)
    names = {s.name for s in result}
    assert "MyService" in names
    assert "run" in names


def test_class_symbol_type() -> None:
    source = "class Foo: ...\n"
    result = index_python("test.py", source)
    cls = next(s for s in result if s.name == "Foo")
    assert cls.symbol_type == "class"


def test_method_symbol_type() -> None:
    source = """\
class Foo:
    def bar(self): ...
"""
    result = index_python("test.py", source)
    method = next(s for s in result if s.name == "bar")
    assert method.symbol_type == "method"


def test_skips_private_methods() -> None:
    source = """\
class Foo:
    def public(self): ...
    def _private(self): ...
"""
    names = {s.name for s in index_python("test.py", source)}
    assert "_private" not in names
    assert "public" in names


def test_skips_private_class() -> None:
    source = "class _Internal: ...\n"
    assert index_python("test.py", source) == []


# ── file_path propagation ─────────────────────────────────────────────────────


def test_file_path_set_on_symbols() -> None:
    source = "def fn(): ...\n"
    result = index_python("src/foo/bar.py", source)
    assert result[0].file_path == "src/foo/bar.py"


# ── error handling ────────────────────────────────────────────────────────────


def test_syntax_error_returns_empty_list() -> None:
    source = "def broken(:\n"
    result = index_python("test.py", source)
    assert result == []


def test_empty_file_returns_empty_list() -> None:
    assert index_python("test.py", "") == []


# ── mixed module ──────────────────────────────────────────────────────────────


def test_mixed_module() -> None:
    source = """\
CONSTANT = 42

def top_level(): ...

class Service:
    def method(self): ...
    def _hidden(self): ...

def _skip(): ...
"""
    names = {s.name for s in index_python("test.py", source)}
    assert names == {"top_level", "Service", "method"}
