"""Micro-benchmark machinery, shared by the flops benchmark suite and by overhead evaluation.

It records elapsed time and nothing else. Cycles are a view a caller asks for by supplying a clock:
the flops suite does, since absolute per-op cost is its deliverable, and overhead evaluation does
not, since it reports a ratio. That is what keeps this layer free of psutil, and so usable from an
install carrying no extras.
"""

from ._interleaved_runner import InterleavedBenchmarkRunner, SliceController
from ._micro_benchmark import MicroBenchmark
from ._output import console, output_quiet
