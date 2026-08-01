"""Fresh-thread first-op coverage of the lazy-init increment idiom.

Every instrumented operator and every patched ``math.*`` replacement inlines a lazy-init
handler for a thread's first counted op:

    try:
        _TLS.flop_counts.<field> += 1
    except AttributeError:  # first counted op on this thread
        _create_thread_state().<field> += 1

That ``except`` branch fires ONLY on a thread's very first counted op: a FlopCountingContext
otherwise creates the thread state on entry, so an op run inside one always takes the ``try``
branch.  A malformed handler in a single site -- wrong field, missing ``except`` -- therefore
stays invisible unless that specific op is the first counted op on a brand-new thread, which the
rest of the suite never arranges (pytest-xdist reuses workers, so some other op warms the thread
first).

Each case here spawns a pristine thread whose first action is exactly one op, and asserts it
counts what the same op counts on the (warm) main thread -- so the ``except`` branch is checked
against the ``try`` branch, per site.  The op list is the arithmetic/comparison/unary operators
and the patch registry's own keys, so a newly instrumented op or patch is covered automatically.
"""

import math
import threading
from collections.abc import Callable

import pytest

from counted_float import CountedFloat, FlopCountingContext
from counted_float._core.counting import _math_patching
from counted_float._core.counting._thread_counter import THREAD_COUNTER

CF = CountedFloat
_PATCH_NAMES = sorted(_math_patching._PATCHES.keys())  # excludes fma/sumprod on interpreters without them


# =================================================================================================
#  Helpers
# =================================================================================================
def _counts_as_dict(fc) -> dict[str, int]:
    """The non-zero flop-count fields of a FlopCounts, as a plain dict for comparison."""
    return {name: getattr(fc, name) for name in fc.field_names() if getattr(fc, name)}


def _first_op_counts_on_fresh_thread(call: Callable[[], object]) -> dict[str, int]:
    """Run ``call`` as the very first counter-touching action on a pristine thread; return its counts.

    Freshness is guaranteed by construction: each call spawns a brand-new ``threading.Thread``, i.e.
    a new OS thread with its own ``threading.local`` storage, so the module-level ``_TLS`` holds no
    ``flop_counts`` for it (unlike the pytest-xdist workers, which are reused and quickly warm). The
    op is therefore unavoidably that thread's first counter access -- which is the whole point: it
    forces the per-op ``except AttributeError`` lazy-init handler, the branch a warm thread (or a
    context entry) never reaches.  A raise inside the thread is re-raised on the main thread so it
    fails the test rather than hanging or vanishing.
    """
    captured: dict[str, object] = {}

    def target() -> None:
        try:
            call()  # first counted op on this thread -> hits the except branch
            captured["counts"] = _counts_as_dict(THREAD_COUNTER.flop_counts())
        except BaseException as exc:  # noqa: BLE001 -- surfaced on the main thread below
            captured["error"] = exc

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    if "error" in captured:
        raise captured["error"]  # type: ignore[misc]
    return captured["counts"]  # type: ignore[return-value]


# =================================================================================================
#  Operators
# =================================================================================================
# reflected forms use an int left operand so the reflected dunder is actually reached (a float left
# would be handled by float.__op__ directly); non-folding operands so every op registers a count
_OPERATORS: list[tuple[str, Callable[[], object]]] = [
    ("add", lambda: CF(1.5) + CF(2.5)),
    ("radd", lambda: 2 + CF(2.5)),
    ("sub", lambda: CF(1.5) - CF(2.5)),
    ("rsub", lambda: 2 - CF(2.5)),
    ("mul", lambda: CF(1.5) * CF(2.5)),
    ("rmul", lambda: 2 * CF(2.5)),
    ("truediv", lambda: CF(1.5) / CF(2.5)),
    ("rtruediv", lambda: 2 / CF(2.5)),
    ("floordiv", lambda: CF(7.0) // CF(2.5)),
    ("rfloordiv", lambda: 7 // CF(2.5)),
    ("mod", lambda: CF(7.0) % CF(2.5)),
    ("rmod", lambda: 7 % CF(2.5)),
    ("divmod", lambda: divmod(CF(7.0), CF(2.5))),
    ("rdivmod", lambda: divmod(7, CF(2.5))),
    ("pow", lambda: CF(2.0) ** CF(3.0)),
    ("pow_const_exponent", lambda: CF(2.5) ** 2),
    ("rpow", lambda: 3 ** CF(2.5)),
    ("abs", lambda: abs(CF(-2.5))),
    ("neg", lambda: -CF(2.5)),
    ("round", lambda: round(CF(2.5))),
    ("round_ndigits", lambda: round(CF(2.567), 2)),
    ("floor", lambda: math.floor(CF(2.5))),
    ("ceil", lambda: math.ceil(CF(2.5))),
    ("trunc", lambda: math.trunc(CF(2.5))),
    ("int", lambda: int(CF(2.5))),
    ("new_from_int", lambda: CF(3)),
    ("is_integer", lambda: CF(2.0).is_integer()),
    ("eq", lambda: CF(1.5) == CF(2.5)),
    ("ne", lambda: CF(1.5) != CF(2.5)),
    ("lt", lambda: CF(1.5) < CF(2.5)),
    ("le", lambda: CF(1.5) <= CF(2.5)),
    ("gt", lambda: CF(1.5) > CF(2.5)),
    ("ge", lambda: CF(1.5) >= CF(2.5)),
    # constant-operand fold paths keep their own lazy-init sites, distinct from the generic
    # branches above (which take a CountedFloat or int operand)
    ("truediv_const_divisor", lambda: CF(1.5) / 3.0),
    # divisor 1.0 folds in count_div (no counter access), so __floordiv__'s own RND increment is
    # the first access on the thread -- exercising its handler rather than count_div's
    ("floordiv_by_one", lambda: CF(7.0) // 1.0),
    ("mul_minus_one", lambda: CF(2.5) * -1.0),
    ("round_ndigits_zero", lambda: round(CF(2.567), 0)),
    ("rsub_minus_zero", lambda: CF(2.0).__rsub__(-0.0)),
    ("rpow_countedfloat_base", lambda: CF(2.0).__rpow__(CF(3.0))),
]
if hasattr(float, "from_number"):
    # Python 3.14+ only, registered conditionally like the version-gated math patches below
    _OPERATORS.append(("from_number_int", lambda: CF.from_number(3)))


@pytest.mark.parametrize(("op_id", "call"), _OPERATORS, ids=[op_id for op_id, _ in _OPERATORS])
def test_operator_first_op_on_fresh_thread(op_id: str, call: Callable[[], object]) -> None:
    # --- arrange (reference: the same op on the warm main thread) ---
    with FlopCountingContext() as ctx:
        call()
        reference = _counts_as_dict(ctx.flop_counts())

    # --- act (first op on a pristine thread hits the lazy-init handler) ---
    fresh = _first_op_counts_on_fresh_thread(call)

    # --- assert -----------------------------
    assert reference, f"{op_id} counted nothing on the main thread -- not an instrumented op"
    assert fresh == reference


# =================================================================================================
#  Patched math.* functions
# =================================================================================================
# one in-domain call per registered patch, with CountedFloat args so counting actually fires;
# fma/sumprod are listed unconditionally but only exercised where _PATCHES registers them
_PATCH_ARGS: dict[str, tuple[object, ...]] = {
    "sqrt": (CF(2.0),),
    "cbrt": (CF(2.0),),
    "log": (CF(2.0),),
    "log2": (CF(2.0),),
    "log10": (CF(2.0),),
    "exp": (CF(0.5),),
    "exp2": (CF(0.5),),
    "pow": (CF(2.0), CF(3.0)),
    "sin": (CF(0.5),),
    "cos": (CF(0.5),),
    "tan": (CF(0.5),),
    "asin": (CF(0.5),),
    "acos": (CF(0.5),),
    "atan": (CF(0.5),),
    "atan2": (CF(1.0), CF(2.0)),
    "hypot": (CF(3.0), CF(4.0)),
    "expm1": (CF(0.5),),
    "log1p": (CF(0.5),),
    "fmod": (CF(5.0), CF(3.0)),
    "fabs": (CF(-2.0),),
    "sinh": (CF(0.5),),
    "cosh": (CF(0.5),),
    "tanh": (CF(0.5),),
    "asinh": (CF(0.5),),
    "acosh": (CF(2.0),),
    "atanh": (CF(0.5),),
    "degrees": (CF(2.0),),
    "radians": (CF(90.0),),
    "dist": ([CF(1.0), CF(2.0)], [CF(4.0), CF(6.0)]),
    "prod": ([CF(2.0), CF(3.0), CF(4.0)],),
    "fsum": ([CF(0.1)] * 4,),
    "copysign": (CF(3.0), CF(-2.0)),
    "gamma": (CF(2.0),),
    "lgamma": (CF(2.0),),
    "erf": (CF(0.5),),
    "erfc": (CF(0.5),),
    "remainder": (CF(5.0), CF(3.0)),
    "fma": (CF(2.0), CF(3.0), CF(4.0)),
    "sumprod": ([CF(2.0)], [CF(3.0)]),
}


@pytest.mark.parametrize("fname", _PATCH_NAMES)
def test_math_patch_first_op_on_fresh_thread(fname: str) -> None:
    def call() -> object:
        return getattr(math, fname)(*_PATCH_ARGS[fname])

    # a context installs the patch module-wide, so the pristine thread below sees the patch too
    # --- arrange / act ---------------------
    with FlopCountingContext() as ctx:
        call()  # reference on the warm main thread (try branch)
        reference = _counts_as_dict(ctx.flop_counts())
        fresh = _first_op_counts_on_fresh_thread(call)  # pristine thread (except branch)

    # --- assert -----------------------------
    assert reference, f"math.{fname} counted nothing -- its argument fixture may be wrong"
    assert fresh == reference


def test_patch_args_cover_every_registered_patch() -> None:
    # a newly registered patch must gain a _PATCH_ARGS entry, or its fresh-thread case would KeyError
    # --- assert -----------------------------
    assert set(_math_patching._PATCHES) <= set(_PATCH_ARGS)


# alternate patch code paths the registry-keyed test above misses (it uses one argument tuple per
# function): math.log's two-arg runtime-base form, and math.fma's constant-product (z-only) branch
_ALT_PATCH_CASES: list[tuple[str, Callable[[], object]]] = [
    ("log_runtime_base", lambda: math.log(CF(8.0), CF(2.0))),
]
if hasattr(math, "fma"):
    _ALT_PATCH_CASES.append(("fma_constant_product", lambda: math.fma(2.0, 3.0, CF(4.0))))


@pytest.mark.parametrize(("case_id", "call"), _ALT_PATCH_CASES, ids=[c[0] for c in _ALT_PATCH_CASES])
def test_math_patch_alternate_path_first_op_on_fresh_thread(case_id: str, call: Callable[[], object]) -> None:
    # --- arrange / act (a context installs the patch module-wide, so the pristine thread sees it) ---
    with FlopCountingContext() as ctx:
        call()
        reference = _counts_as_dict(ctx.flop_counts())
        fresh = _first_op_counts_on_fresh_thread(call)

    # --- assert -----------------------------
    assert reference, f"{case_id} counted nothing"
    assert fresh == reference
