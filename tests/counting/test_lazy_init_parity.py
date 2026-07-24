"""Structural parity between the two branches of the inlined lazy-init idiom.

Counting sites increment the calling thread's counter directly and fall back to creating that
thread's state in an `except AttributeError` handler.  The idiom is written out at every site
rather than factored into a helper - a call would cost about as much as the increment it guards -
so only a test can guarantee that a handler touches the same counter field as the `try` body it
backs.  A mismatch there fires on a thread's very first counted operation and never again, which
is why it survives both full line coverage and mutation testing.
"""

import ast
from pathlib import Path
from types import ModuleType

import pytest

from counted_float._core.counting import _counted_float, _math_patching

_LAZY_INIT_MODULES = [_counted_float, _math_patching]


def _module_id(module: ModuleType) -> str:
    """Bare module name, for readable parametrize ids."""
    return module.__name__.rsplit(".", 1)[-1]


def _lazy_init_pairs(tree: ast.Module) -> list[tuple[ast.Try, ast.ExceptHandler]]:
    """Every `try` in the tree paired with its handler that catches AttributeError."""
    return [
        (node, handler)
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name) and handler.type.id == "AttributeError"
    ]


def _counter_increments(body: list[ast.stmt]) -> list[tuple[str, str]]:
    """(field, increment source) for every `<expr>.FIELD += <expr>` directly in a branch body.

    The increment is compared as source rather than as a value, so the sites that count a
    length-derived number of flops are held to the same expression on both branches.
    """
    return [
        (stmt.target.attr, ast.unparse(stmt.value))
        for stmt in body
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add) and isinstance(stmt.target, ast.Attribute)
    ]


def _bound_names(body: list[ast.stmt]) -> list[str]:
    """Names bound by an assignment directly in a branch body, in order."""
    names: list[str] = []
    for stmt in body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.append(stmt.target.id)
        elif isinstance(stmt, ast.Assign):
            names.extend(target.id for target in stmt.targets if isinstance(target, ast.Name))
    return names


@pytest.mark.parametrize("module", _LAZY_INIT_MODULES, ids=_module_id)
def test_lazy_init_handler_matches_its_try_branch(module: ModuleType):
    # --- arrange -----------------------------------------
    source = Path(module.__file__ or "").read_text(encoding="utf-8")
    tree = ast.parse(source)

    # --- act ---------------------------------------------
    pairs = _lazy_init_pairs(tree)

    # --- assert ------------------------------------------
    # renaming the idiom out of existence must fail here, not pass vacuously over zero matches
    assert pairs, f"no lazy-init try/except AttributeError pairs found in {module.__name__}"

    for try_node, handler in pairs:
        where = f"{_module_id(module)}:{try_node.lineno}"
        increments = _counter_increments(try_node.body)
        bindings = _bound_names(try_node.body)
        assert increments or bindings, f"{where}: try branch neither counts nor binds - unknown idiom"
        assert _counter_increments(handler.body) == increments, f"{where}: handler counts something else"
        assert _bound_names(handler.body) == bindings, f"{where}: handler binds something else"
