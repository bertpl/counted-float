"""Drop this directory from collection when the flops benchmarking extra is not installed.

Every module here imports the flops sub-package while it is being *collected*, so a skip marker
would come too late — the import has already failed by then. Hence a collection-time ignore; the
glob matches every test module in this directory.
"""

from counted_float._core.compatibility import Capability

collect_ignore_glob = [] if Capability.FLOPS_BENCHMARKING.is_available() else ["*.py"]
