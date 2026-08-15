"""Every attribute of `float` must be accounted for: overridden, or classified with a reason.

The math-surface test pins `math`'s callables so a function CPython adds later fails a test
instead of becoming a silently uncounted hole.  This is the same pin for `float`'s own attribute
surface, with two extensions that surface needs and the math one does not:

* **Behavior pins on the overridden members** — an override that exists but returns the wrong
  type (or counts the wrong thing) is invisible to a name-level check, so the pins assert count
  and return type, not mere presence.
* **Provenance pins on the classified members** — the float-defined and object-defined halves
  drift for different reasons, and a member migrating between them (e.g. `float` growing its own
  `__str__`) would change behavior without changing any name.

Enumeration is by *name* over `dir(float)` on the running interpreter — never by defining class:
which class defines a member varies among CPython builds (`__getattribute__` left
`float.__dict__` in 3.12.5), so the name set is the stable contract.
"""

import copy
import math
import pickle
import struct
from decimal import Decimal
from fractions import Fraction

import pytest

from counted_float import CountedFloat, FlopCountingContext, Verbosity
from counted_float._core.counting.float_surface import (
    _FLOAT_DEFINED_UNPATCHED,
    _OBJECT_DEFINED_UNPATCHED,
    _PROVENANCE_VARIES_BY_VERSION,
)

_TABLES = {
    "_FLOAT_DEFINED_UNPATCHED (inherited from float - say why no override is needed)": _FLOAT_DEFINED_UNPATCHED,
    "_OBJECT_DEFINED_UNPATCHED (inherited object plumbing - pinned for drift)": _OBJECT_DEFINED_UNPATCHED,
}


# =================================================================================================
#  Helpers
# =================================================================================================
def _unclassified(surface: set[str]) -> set[str]:
    """The members of `surface` that are neither overridden by CountedFloat nor classified."""
    overridden = surface & set(vars(CountedFloat))
    classified = set().union(*(set(table) for table in _TABLES.values()))
    return surface - overridden - classified


def _bits(value: float) -> bytes:
    """The exact binary64 representation, so nan payloads and zero signs compare too."""
    return struct.pack(">d", value)


# =================================================================================================
#  The surface is fully accounted for
# =================================================================================================
def test_every_float_attribute_is_classified_or_overridden():
    # --- arrange / act -------------------------
    unclassified = _unclassified(set(dir(float)))

    # --- assert --------------------------------
    assert not unclassified, (
        f"unclassified float attribute(s): {sorted(unclassified)}.\n"
        "Each one is either overridden on CountedFloat (and behavior-pinned below) or belongs "
        "in exactly one of:\n" + "\n".join(f"  - {table}" for table in _TABLES)
    )


def test_a_fake_member_is_reported_by_name():
    # the check must fail loudly on an unknown name -- a surface test that passes over an
    # augmented enumeration would also pass over a real CPython addition
    # --- arrange / act -------------------------
    unclassified = _unclassified(set(dir(float)) | {"definitely_not_a_float_member"})

    # --- assert --------------------------------
    assert unclassified == {"definitely_not_a_float_member"}


def test_no_table_classifies_an_absent_or_overridden_member():
    # --- arrange -------------------------------
    surface = set(dir(float))
    overridden = surface & set(vars(CountedFloat))

    # --- act -----------------------------------
    phantom = {name: table for table, names in _TABLES.items() for name in set(names) - surface}
    stale = {name: table for table, names in _TABLES.items() for name in set(names) & overridden}

    # --- assert --------------------------------
    assert not phantom, f"classified but absent from float on this interpreter: {phantom}"
    assert not stale, f"classified but overridden on CountedFloat (stale table entry): {stale}"


def test_the_tables_do_not_overlap():
    # --- arrange / act -------------------------
    overlapping = {
        name
        for name in set().union(*(set(t) for t in _TABLES.values()))
        if sum(name in table for table in _TABLES.values()) > 1
    }

    # --- assert --------------------------------
    assert not overlapping, f"float attribute(s) classified more than once: {overlapping}"


def test_every_entry_carries_a_reason():
    # --- arrange / act -------------------------
    reasonless = [name for table in _TABLES.values() for name, reason in table.items() if not reason.strip()]

    # --- assert --------------------------------
    assert not reasonless, f"entries with no stated reason: {reasonless}"


def test_classified_members_have_their_stated_provenance():
    # members whose defining class varies among supported interpreters are exempt by name,
    # so the pin holds one arrangement to account without encoding a single micro release's layout
    # --- arrange / act -------------------------
    not_float_defined = sorted(
        name
        for name in _FLOAT_DEFINED_UNPATCHED
        if name not in vars(float) and name not in _PROVENANCE_VARIES_BY_VERSION
    )
    not_object_defined = sorted(
        name for name in _OBJECT_DEFINED_UNPATCHED if name in vars(float) and name not in _PROVENANCE_VARIES_BY_VERSION
    )

    # --- assert --------------------------------
    assert not not_float_defined, f"classified as float-defined but not in float.__dict__: {not_float_defined}"
    assert not not_object_defined, (
        f"classified as object plumbing but defined by float itself: {not_object_defined} — "
        "a member migrating to float-defined changes behavior (e.g. what str(x) prints) and "
        "must be re-triaged, not re-labeled"
    )
    # the exemptions are names, so a typo would silently exempt nothing forever
    classified = set(_FLOAT_DEFINED_UNPATCHED) | set(_OBJECT_DEFINED_UNPATCHED)
    unclassified_exemptions = sorted(_PROVENANCE_VARIES_BY_VERSION - classified)
    assert not unclassified_exemptions, (
        f"exempted from the provenance pin but not classified: {unclassified_exemptions}"
    )


# =================================================================================================
#  Behavior pins - the complex protocol
# =================================================================================================
@pytest.mark.parametrize("value", [1.5, -2.5, 0.0, -0.0, math.inf, -math.inf, math.nan], ids=repr)
def test_real_and_conjugate_preserve_countedness_at_zero_cost(thread_counter, value):
    # --- arrange -------------------------------
    x = CountedFloat(value)

    # --- act -----------------------------------
    results = [x.real, x.conjugate()]

    # --- assert --------------------------------
    for result in results:
        assert isinstance(result, CountedFloat)
        assert _bits(result) == _bits(value)  # bit-identical, nan sign and payload included
    assert thread_counter.total_count() == 0


def test_real_dropping_countedness_no_longer_kills_downstream_counting(thread_counter):
    # the defect that motivated the override: a plain-float .real demoted runtime data to a
    # value-folded constant, so 10.0 / x.real counted MUL or DIV depending on x's value
    # --- act -----------------------------------
    _ = CountedFloat(10.0) / CountedFloat(3.0).real

    # --- assert --------------------------------
    assert thread_counter.DIV == 1
    assert thread_counter.total_count() == 1


@pytest.mark.parametrize("value", [1.5, -0.0, math.nan, -math.nan, math.inf], ids=repr)
def test_imag_is_the_ports_plain_constant(thread_counter, value):
    # --- act -----------------------------------
    result = CountedFloat(value).imag

    # --- assert --------------------------------
    assert type(result) is float  # receiver-independent: the port's compile-time constant
    assert _bits(result) == _bits(0.0)  # exactly +0.0, whatever the receiver's sign or payload
    assert thread_counter.total_count() == 0


# =================================================================================================
#  Behavior pins - is_integer
# =================================================================================================
@pytest.mark.parametrize(
    ("value", "expected"),
    [(1.5, False), (2.0, True), (-0.0, True), (2.0**53, True), (math.inf, False), (math.nan, False)],
    ids=repr,
)
def test_is_integer_counts_the_floor_and_compare(thread_counter, value, expected):
    # --- act -----------------------------------
    result = CountedFloat(value).is_integer()

    # --- assert --------------------------------
    assert result is expected
    assert type(result) is bool
    # RND, not F2I: C's floor is double->double and no int materializes -- the price of the
    # counted spelling  x // 1.0 == x.  Charged unconditionally, non-finite fast path included.
    assert thread_counter.RND == 1
    assert thread_counter.COMP == 1
    assert thread_counter.total_count() == 2


# =================================================================================================
#  Behavior pins - as_integer_ratio
# =================================================================================================
def test_as_integer_ratio_is_uncounted_and_warns_when_reporting(thread_counter, capsys):
    # --- arrange -------------------------------
    from counted_float._core.counting.verbosity import uncounted_warnings

    uncounted_warnings._reported.clear()  # the reported-sites record is process-wide

    # --- act -----------------------------------
    quiet = CountedFloat(1.5).as_integer_ratio()
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        loud = CountedFloat(1.5).as_integer_ratio()

    # --- assert --------------------------------
    assert quiet == loud == (3, 2)
    assert thread_counter.total_count() == 0
    lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    (line,) = lines  # the quiet call reported nothing; the reporting context exactly one line
    assert line.split()[:2] == ["WARN", "float.as_integer_ratio"]


# =================================================================================================
#  Behavior pins - construction and exits
# =================================================================================================
def test_new_source_matrix(thread_counter):
    """int counts I2F; float, str, Decimal and Fraction convert uncounted (stated gaps)."""
    # --- act / assert --------------------------
    for source, expected_i2f in [(3, 1), (True, 1), (1.5, 0), ("1.5", 0), (Decimal("1.5"), 0), (Fraction(3, 2), 0)]:
        thread_counter.reset()
        result = CountedFloat(source)  # ty: ignore[invalid-argument-type] -- str/Decimal sources are the incidental paths under test
        assert isinstance(result, CountedFloat)
        assert expected_i2f == thread_counter.I2F
        assert thread_counter.total_count() == expected_i2f


def test_float_call_is_the_explicit_uncounted_exit(thread_counter):
    # --- act -----------------------------------
    result = float(CountedFloat(1.5))

    # --- assert --------------------------------
    assert type(result) is float  # exactly plain: the value has left the counting model
    assert thread_counter.total_count() == 0


def test_fromhex_preserves_countedness_at_zero_cost(thread_counter):
    # --- act -----------------------------------
    result = CountedFloat.fromhex("0x1.8p+1")

    # --- assert --------------------------------
    assert isinstance(result, CountedFloat)
    assert float(result) == 3.0  # compared through the uncounted exit, so the pin below holds
    assert thread_counter.total_count() == 0  # the parse is a stated gap: no FlopType prices it
    assert float(CountedFloat.fromhex(CountedFloat(1.5).hex())) == 1.5  # round-trips through hex()


@pytest.mark.skipif(not hasattr(float, "from_number"), reason="float.from_number exists from Python 3.14")
def test_from_number_counts_i2f_for_int_sources(thread_counter):
    """The 3.14 constructor answers like CountedFloat(n): same source, same price."""
    # --- act / assert --------------------------
    for source, expected_i2f in [(3, 1), (True, 1), (1.5, 0), (CountedFloat(2.5), 0), (Decimal("1.5"), 0)]:
        thread_counter.reset()
        result = CountedFloat.from_number(source)
        assert isinstance(result, CountedFloat)
        assert expected_i2f == thread_counter.I2F
        assert thread_counter.total_count() == expected_i2f
    with pytest.raises(TypeError):
        CountedFloat.from_number("1.5")  # rejected by the underlying call, nothing counted
    assert thread_counter.total_count() == 0  # compute-first contract: the raising call left no phantom flop


# =================================================================================================
#  Behavior pins - presentation
# =================================================================================================
def test_repr_is_the_single_loud_presentation_mechanism(thread_counter):
    # --- arrange -------------------------------
    x = CountedFloat(1.5)

    # --- act / assert --------------------------
    # float defines no __str__, so every empty-spec spelling falls through to __repr__
    assert "__str__" not in vars(CountedFloat)
    for loud in (str(x), f"{x}", format(x, ""), repr(x)):
        assert loud == "CountedFloat(1.5)"
    # any non-empty spec formats the plain value -- the loud/quiet boundary is exactly spec == ''
    assert f"{x:.2f}" == "1.50"
    assert format(x, ">5") == "  1.5"
    assert thread_counter.total_count() == 0


def test_percent_formatting_stays_uncounted(thread_counter):
    # the '%' presentation type multiplies by 100 in binary64 first -- a labeled uncounted
    # exception, pinned so the zero is a decision rather than an accident
    # --- act -----------------------------------
    rendered = format(CountedFloat(0.07), ".1%")

    # --- assert --------------------------------
    assert rendered == "7.0%"
    assert thread_counter.total_count() == 0


def test_truthiness_stays_uncounted_and_the_counted_spelling_counts(thread_counter):
    # --- arrange -------------------------------
    x = CountedFloat(1.5)

    # --- act / assert --------------------------
    assert bool(x)
    assert not CountedFloat(0.0)  # the implicit spelling, through `not`
    assert thread_counter.total_count() == 0  # implicit interpreter tests are bookkeeping
    assert x != 0.0
    assert thread_counter.COMP == 1  # the algorithmic spelling pays its COMP


def test_hex_is_an_uncounted_str_exit(thread_counter):
    # --- act -----------------------------------
    result = CountedFloat(1.5).hex()

    # --- assert --------------------------------
    assert type(result) is str
    assert thread_counter.total_count() == 0


# =================================================================================================
#  Behavior pins - pickling, both routes
# =================================================================================================
@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
@pytest.mark.parametrize("value", [1.5, -0.0, math.inf, math.nan], ids=repr)
def test_pickle_round_trip_preserves_countedness_at_zero_count(thread_counter, value, protocol):
    """Protocols 0-1 rebuild via copyreg and float(); 2+ via __getnewargs__ and __new__.

    The two routes share no code, so a single-protocol test leaves half of this unguarded.
    """
    # --- act -----------------------------------
    restored = pickle.loads(pickle.dumps(CountedFloat(value), protocol=protocol))  # noqa: S301

    # --- assert --------------------------------
    assert isinstance(restored, CountedFloat)
    assert thread_counter.total_count() == 0  # deserialization is not the algorithm converting
    if protocol >= 1:
        # protocol 0 pickles floats as repr text, which loses nan payloads -- plain-float
        # behavior, so bit-exactness is only the contract from protocol 1 up
        assert _bits(restored) == _bits(value)
    else:
        assert restored == value or (math.isnan(restored) and math.isnan(value))


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_each_protocol_takes_its_documented_route(protocol):
    """The route itself, not only its outcome: both would pass if one of them vanished.

    Protocols 0-1 route through `copyreg._reconstructor`, which the pickle stream names
    outright; protocols 2+ use `__getnewargs__` and the class's own `__new__`, and name no
    reconstructor at all.
    """
    # --- act -----------------------------------
    stream = pickle.dumps(CountedFloat(1.5), protocol=protocol)

    # --- assert --------------------------------
    assert (b"_reconstructor" in stream) is (protocol <= 1)


def test_protocol_0_loses_the_nan_payload_that_later_protocols_keep():
    """The stated exception to bit-exactness, pinned so it stays a known limit of protocol 0."""
    # --- arrange -------------------------------
    payload_nan = CountedFloat(struct.unpack(">d", bytes.fromhex("7ff8deadbeef0000"))[0])

    # --- act -----------------------------------
    restored = {p: pickle.loads(pickle.dumps(payload_nan, protocol=p)) for p in (0, 1, 2)}  # noqa: S301

    # --- assert --------------------------------
    # protocol 0 stores floats as repr text, so the payload cannot survive the round trip
    assert _bits(restored[0]) != _bits(payload_nan)
    assert math.isnan(restored[0])  # still a nan, just not the same one
    for protocol in (1, 2):
        assert _bits(restored[protocol]) == _bits(payload_nan)


@pytest.mark.parametrize("copier", [copy.copy, copy.deepcopy], ids=["copy", "deepcopy"])
def test_copy_preserves_countedness_at_zero_count(thread_counter, copier):
    # --- act -----------------------------------
    result = copier(CountedFloat(1.5))

    # --- assert --------------------------------
    assert isinstance(result, CountedFloat)
    assert float(result) == 1.5  # compared through the uncounted exit, so the pin below holds
    assert thread_counter.total_count() == 0


def test_pickle_mechanism_pins(thread_counter):
    """Pin the mechanism, not just the outcome: what each pickle member hands the machinery."""
    # --- arrange -------------------------------
    x = CountedFloat(1.5)

    # --- act -----------------------------------
    newargs = x.__getnewargs__()
    state = x.__getstate__()
    reconstructor, args = x.__reduce__()[:2]

    # --- assert --------------------------------
    assert newargs == (1.5,)
    assert type(newargs[0]) is float  # a plain float: re-entry counts nothing
    assert state is None  # no instance state exists, because __slots__ is empty
    assert isinstance(reconstructor(*args), CountedFloat)  # the direct-call route also rebuilds counted
    assert thread_counter.total_count() == 0
