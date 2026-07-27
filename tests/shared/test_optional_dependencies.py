from counted_float._core.compatibility import CLI, FLOPS_BENCHMARKING, OptionalCapability, is_importable


# =================================================================================================
#  is_importable
# =================================================================================================
def test_is_importable_true_for_a_module_of_the_standard_library():
    # --- act ---------------------------------------------
    result = is_importable("math")

    # --- assert ------------------------------------------
    assert result is True


def test_is_importable_false_for_a_module_that_does_not_exist():
    # --- act ---------------------------------------------
    result = is_importable("counted_float_no_such_module")

    # --- assert ------------------------------------------
    assert result is False


def test_is_importable_reports_a_module_that_raises_on_import_as_absent(tmp_path, monkeypatch):
    # a distribution can be installed and still unusable -- a broken wheel, an ABI mismatch. What the
    # caller can act on is whether the import works, so an importable-but-raising module reads False.
    # --- arrange -----------------------------------------
    module_name = "counted_float_raises_on_import"
    (tmp_path / f"{module_name}.py").write_text("raise ImportError('deliberately unimportable')\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    # --- act ---------------------------------------------
    result = is_importable(module_name)

    # --- assert ------------------------------------------
    assert result is False


def test_is_importable_caches_its_answer():
    # --- arrange -----------------------------------------
    is_importable("math")

    # --- act ---------------------------------------------
    hits_before = is_importable.cache_info().hits
    is_importable("math")

    # --- assert ------------------------------------------
    assert is_importable.cache_info().hits == hits_before + 1


# =================================================================================================
#  OptionalCapability
# =================================================================================================
def test_capability_is_importable_requires_every_module():
    # --- arrange -----------------------------------------
    partly_present = OptionalCapability(
        name="Something",
        extra="something",
        modules=("math", "counted_float_no_such_module"),
    )

    # --- act / assert ------------------------------------
    assert partly_present.is_importable() is False


def test_capability_is_importable_true_when_all_modules_resolve():
    # --- arrange -----------------------------------------
    all_present = OptionalCapability(name="Something", extra="something", modules=("math", "json"))

    # --- act / assert ------------------------------------
    assert all_present.is_importable() is True


def test_capability_explains_only_its_own_missing_modules():
    # --- act / assert ------------------------------------
    assert CLI.explains(ModuleNotFoundError(name="click")) is True
    assert CLI.explains(ModuleNotFoundError(name="something_unrelated")) is False


def test_capability_message_names_the_extra_that_installs_it():
    # --- act ---------------------------------------------
    message = FLOPS_BENCHMARKING.missing_dependency_message()

    # --- assert ------------------------------------------
    assert FLOPS_BENCHMARKING.name in message
    assert f"counted-float[{FLOPS_BENCHMARKING.extra}]" in message


def test_the_declared_capabilities_cover_the_modules_their_guards_translate():
    # the guards match a failed import against these tuples, so a module dropping out of one would
    # silently turn its actionable message back into a raw ModuleNotFoundError
    # --- act / assert ------------------------------------
    assert CLI.modules == ("click",)
    assert set(FLOPS_BENCHMARKING.modules) == {"numba", "numpy", "psutil", "cpuinfo"}
