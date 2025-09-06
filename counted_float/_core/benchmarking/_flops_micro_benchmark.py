from typing import Callable

import numpy as np

from ._micro_benchmark import MicroBenchmark


class FlopsMicroBenchmark(MicroBenchmark):
    """
    Base class for benchmark that checks speed of a certain type of floating point operation.

    This is set up as follows:
      - we configure the benchmark with a 'size' and a function 'f'
      - we prepare the inputs: 2 1D numpy arrays of size 'size': in_f1, in_f2
         - initialized as random floating point numbers in range [0, 10]
      - we prepare the output arrays: of size 'size': out_f, out_i
         - 1 output array per type of result: float, int
         - initialized with zeros
      - the function f will loop over a&b and write the result to c
         - the function should be implemented such that it does not use vectorized operations, we want to avoid
             using vectorized CPU instructions (AVX, etc...): we want to measure the speed of the regular, scalar
             operations
         - we numba.jit the function, to make sure it is compiled to machine code, to avoid Python overhead to dominate
             the benchmark
         - 'size' should be chosen large enough to avoid the overhead of the benchmarking framework to be noticeable
         - 'size' should be chosen small enough to fit in the CPU cache, to avoid being RAM-bandwidth limited

    Despite all these measures, it is not expected that the benchmark will be fully accurate in absolute terms.
    In real-life the speed of execution of floating point operations on a CPU will also be influenced by branching,
    memory access patterns, etc...
    The main goal is to find a reasonably accurate estimate of the relative cost of the main types of floating point
    operations, so we can make representative estimates of the number of FLOPS executed by instrumented algorithms.
    """

    def __init__(self, name: str, f: Callable, size: int):
        super().__init__(name=name)
        self.size = size
        self.f = f
        self.n_operations = 0
        # input arrays
        self.in_f1: np.ndarray = np.zeros(size, dtype=float)
        self.in_f2: np.ndarray = np.zeros(size, dtype=float)
        # output arrays
        self.out_f: np.ndarray = np.zeros(size, dtype=float)
        self.out_i: np.ndarray = np.zeros(size, dtype=int)

    def _prepare_benchmark(self, n_operations: int):
        self.n_operations = n_operations
        # input arrays
        self.in_f1 = 10 * np.random.rand(self.size)
        self.in_f2 = 10 * np.random.rand(self.size)
        # output arrays
        self.out_f: np.ndarray = np.full(self.size, 0.0, dtype=float)
        self.out_i: np.ndarray = np.full(self.size, 0, dtype=int)

    def _run_benchmark(self):
        # repeat 'f' n_operations times, each time on the same data
        for _ in range(self.n_operations):
            self.f(self.size, self.in_f1, self.in_f2, self.out_f, self.out_i)
