"""Skip this directory whole when the flops benchmarking modules are not importable.

Every module here imports the flops sub-package at module level, and that sub-package is exactly
what the benchmarking extra gates — so the condition belongs at the directory rather than being
restated in each file. Collection-time ignoring rather than a skip marker, because the import that
would fail happens while the module is being collected.
"""

from counted_float._core.compatibility import FLOPS_BENCHMARKING

collect_ignore_glob = [] if FLOPS_BENCHMARKING.is_importable() else ["*.py"]
