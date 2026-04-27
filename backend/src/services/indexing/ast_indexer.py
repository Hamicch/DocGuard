"""AST-based Python symbol extractor.

Parses a Python source file using the stdlib ``ast`` module and returns a flat
list of ``CodeSymbol`` objects covering module-level functions, classes, and
public methods.  No third-party dependencies — stdlib only.
"""

from __future__ import annotations

import ast
import textwrap

import structlog

from src.domain.models import CodeSymbol

logger = structlog.get_logger(__name__)


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Reconstruct a readable signature string from an AST function node."""
    args = node.args

    parts: list[str] = []

    # positional-only (Python 3.8+)
    for _i, arg in enumerate(args.posonlyargs):
        parts.append(arg.arg)
    if args.posonlyargs:
        parts.append("/")

    # regular args
    num_defaults = len(args.defaults)
    num_args = len(args.args)
    for i, arg in enumerate(args.args):
        default_index = i - (num_args - num_defaults)
        if default_index >= 0:
            parts.append(f"{arg.arg}=...")
        else:
            parts.append(arg.arg)

    # *args
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    elif args.kwonlyargs:
        parts.append("*")

    # keyword-only
    for i, arg in enumerate(args.kwonlyargs):
        if args.kw_defaults[i] is not None:
            parts.append(f"{arg.arg}=...")
        else:
            parts.append(arg.arg)

    # **kwargs
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")

    return f"{node.name}({', '.join(parts)})"


def _extract_docstring(
    node: ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module,
) -> str | None:
    """Return the docstring of a function/class node, or None."""
    return ast.get_docstring(node)


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _symbols_from_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
    symbol_type: str = "function",
) -> CodeSymbol:
    return CodeSymbol(
        name=node.name,
        symbol_type=symbol_type,
        signature=_build_signature(node),
        docstring=_extract_docstring(node),
        file_path=file_path,
        line_number=node.lineno,
    )


def _symbols_from_class(node: ast.ClassDef, file_path: str) -> list[CodeSymbol]:
    symbols: list[CodeSymbol] = []

    # The class itself
    symbols.append(
        CodeSymbol(
            name=node.name,
            symbol_type="class",
            signature=node.name,
            docstring=_extract_docstring(node),
            file_path=file_path,
            line_number=node.lineno,
        )
    )

    # Public methods inside the class
    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(child, ast.ClassDef):
            # Nested class — skip to avoid double-counting; caller handles top-level only
            break
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and _is_public(child.name):
            symbols.append(
                _symbols_from_function(child, file_path, symbol_type="method")
            )

    return symbols


def index_python(file_path: str, source: str) -> list[CodeSymbol]:
    """Parse *source* as Python and return all public symbols.

    Args:
        file_path: Repository-relative path used to populate ``CodeSymbol.file_path``.
        source:    Full source text of the Python file.

    Returns:
        Flat list of ``CodeSymbol`` instances.  Empty list on parse error
        (error is logged; callers should not crash on bad files in a PR).
    """
    try:
        tree = ast.parse(textwrap.dedent(source), filename=file_path)
    except SyntaxError as exc:
        logger.warning("ast_indexer.parse_error", file=file_path, error=str(exc))
        return []

    symbols: list[CodeSymbol] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if _is_public(node.name):
                symbols.append(_symbols_from_function(node, file_path))
        elif isinstance(node, ast.ClassDef) and _is_public(node.name):
            symbols.extend(_symbols_from_class(node, file_path))

    logger.debug("ast_indexer.done", file=file_path, symbol_count=len(symbols))
    return symbols
