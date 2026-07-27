"""Drop this directory from collection when the flops benchmarking extra is not installed.

Every module here imports the flops sub-package while it is being *collected*, so a skip marker
would come too late — the import has already failed by the time markers are consulted. Hence a
collection-time ignore: the glob below matches every test module in this directory.

Availability is the capability's own question, which is "does the flops sub-package import" — so
this stays right when the extra gains or loses a package. It is deliberately not a question about
numba: numba is shimmed, and the shim's code paths are exercised precisely by the runs that have no
numba, so keying on it would drop that coverage rather than protect anything.
"""

from counted_float._core.compatibility import CAP_FLOPS_BENCHMARKING

collect_ignore_glob = [] if CAP_FLOPS_BENCHMARKING.is_available() else ["*.py"]
