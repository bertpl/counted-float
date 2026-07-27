"""Timing machinery shared by everything that measures: neutral ground, owned by neither caller.

It records elapsed time and nothing else. Cycles are a view a caller asks for by supplying a clock,
which is what keeps this layer free of any dependency an install tier might not carry.
"""

from ._interleaved_runner import InterleavedBenchmarkRunner, SliceController
from ._micro_benchmark import MicroBenchmark
from ._output import console, output_quiet
