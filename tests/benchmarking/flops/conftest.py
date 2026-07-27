"""Drop this directory from collection when the flops benchmarking extra is not installed.

Every module here imports the flops sub-package while it is being *collected*, so a skip marker
would come too late — the import has already failed by then. Hence `collect_ignore_glob`, a pytest
conftest hook read during collection: files matching it are never collected, let alone imported.
(`collect_ignore` is the same thing for literal paths.) The glob below matches every test module in
this directory.
"""

from counted_float._core.compatibility import Capability

collect_ignore_glob = [] if Capability.FLOPS_BENCHMARKING.is_available() else ["*.py"]
