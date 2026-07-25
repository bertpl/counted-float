"""Structural parity between the two branches of the inlined lazy-init idiom.

Counting sites increment the calling thread's counter directly and fall back to creating that
thread's state in an ``except AttributeError`` handler:

    try:
        _TLS.flop_counts.ADD += 1
    except AttributeError:  # first counted op on this thread
        _create_thread_state().ADD += 1

The idiom is written out at every site rather than factored into a helper - a call would cost
about as much as the increment it guards - so only a test can guarantee that a handler touches the
same counter field as the ``try`` body it backs.  A mismatch there fires on a thread's very first
counted operation and never again, which is why it survives both full line coverage and mutation
testing.

The helpers below take that example apart: the ``try``/``except AttributeError`` pair itself, the
``ADD += 1`` write inside each of its branches, and - for the sites whose branches bind the counter
to a local rather than incrementing it in place - the name each branch binds.

The test reads the source through the module's own file path, so under a mutation runner - which
works on its own copy of the package - it would be reading generated mutant variants instead of the
real source.  Those variants are not what this module guards, so it stands down there (see
``_is_mutation_sandbox_copy``).
"""

import ast
from pathlib import Path
from types import ModuleType

import pytest

from counted_float._core.counting import _counted_float, _math_patching

_LAZY_INIT_MODULES = [_counted_float, _math_patching]

# mutmut copies the package under this directory before mutating it (see [tool.mutmut] source_paths)
_MUTATION_SANDBOX_DIR = "mutants"


# =================================================================================================
#  Helpers
# =================================================================================================
def _module_id(module: ModuleType) -> str:
    """Bare module name, for readable parametrize ids."""
    return module.__name__.rsplit(".", 1)[-1]


def _is_mutation_sandbox_copy(path: Path) -> bool:
    """Whether this path is a mutation runner's copy of the source rather than the source itself.

    The runner rewrites every mutated function into a trampoline over generated variants, whose
    cold-start handlers are not the idiom documented above - so the structural assertions below
    have nothing meaningful to say about them.  Recognizing the copy keeps this test out of the
    way instead of teaching it the runner's generated shapes.
    """
    return _MUTATION_SANDBOX_DIR in path.parts


def _lazy_init_pairs(tree: ast.Module) -> list[tuple[ast.Try, ast.ExceptHandler]]:
    """Every `try` in the tree paired with its handler that catches AttributeError.

    The outer shape of the example in the module docstring.
    """
    return [
        (node, handler)
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name) and handler.type.id == "AttributeError"
    ]


def _counter_increments(body: list[ast.stmt]) -> list[tuple[str, str]]:
    """(field, increment source) for every `<expr>.FIELD += <expr>` directly in a branch body.

    The `ADD += 1` of the example in the module docstring, taken from one branch.  The increment
    is compared as source rather than as a value, so the sites that count a length-derived number
    of flops are held to the same expression on both branches.
    """
    return [
        (stmt.target.attr, ast.unparse(stmt.value))
        for stmt in body
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add) and isinstance(stmt.target, ast.Attribute)
    ]


def _bound_names(body: list[ast.stmt]) -> list[str]:
    """Names bound by an assignment directly in a branch body, in order.

    The variant of the example where a branch binds the counter to a local (`cnt = ...`) and the
    increments follow after the try/except, instead of incrementing in place.
    """
    names: list[str] = []
    for stmt in body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.append(stmt.target.id)
        elif isinstance(stmt, ast.Assign):
            names.extend(target.id for target in stmt.targets if isinstance(target, ast.Name))
    return names


# =================================================================================================
#  Tests
# =================================================================================================
@pytest.mark.parametrize("module", _LAZY_INIT_MODULES, ids=_module_id)
def test_lazy_init_handler_matches_its_try_branch(module: ModuleType):
    # --- arrange -----------------------------------------
    path = Path(module.__file__ or "")
    if _is_mutation_sandbox_copy(path):
        pytest.skip("reading a mutation runner's copy of the source, not the source itself")
    tree = ast.parse(path.read_text(encoding="utf-8"))

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
