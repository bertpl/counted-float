from typing import Callable

import numpy as np

from counted_float._core.benchmarking.micro import MicroBenchmark

from ._array_generator import ArrayGenerator


class FlopsMicroBenchmark(MicroBenchmark):
    """
    Base class for benchmark that estimates execution time (in cpu cycles) of certain combinations of floating-point
      operations.  These can then be combined to estimate execution time (in cpu cycles) of individual floating-point
      operations

    This is set up as follows:
      - we configure the benchmark with a 'size' and a function 'f'
      - we prepare the inputs: 1 1D numpy array of size 'size': in_f
         - initialized with random values (adhering to certain properties) as appropriate by the child class
      - we prepare the output arrays: of size 'size': out_f, out_i
         - 1 output array per type of result: float, int
         - initialized with zeros
      - the function f will loop over a&b and write the result to c
         - the function should be implemented such that it does not use vectorized operations, we want to avoid
             using vectorized CPU instructions (AVX, etc...): we want to measure the speed of the regular, scalar
             operations
         - the function should be implemented such that the floating point operations form dependent chains of operations,
            to avoid the out-of-order superscalar nature of most modern CPUs to manage to run certain operations
            (partially or fully) in parallel.
         - we numba.jit the function, to make sure it is compiled to machine code, to avoid Python overhead to dominate
             the benchmark
         - choice of 'size':
            - should be chosen large enough to avoid the overhead of the benchmarking framework to be noticeable
            - should be chosen small enough to fit in the CPU's L1 data cache, to avoid being RAM-bandwidth limited
            - 1000 should be an appropriate value, leading to 24KB of data for the 3 arrays, which fits in L1 data cache
              of all tested CPUs.

    Despite all these measures, it is not expected that the benchmark will be fully accurate in absolute terms.
    In real-life the speed of execution of floating point operations on a CPU will also be influenced by branching,
    memory access patterns, etc...
    The main goal is to find a reasonably accurate estimate of the relative cost of the main types of floating point
    operations, so we can make representative estimates of the number of FLOPS executed by instrumented algorithms.
    """

    def __init__(self, name: str, size: int, array_init: ArrayGenerator, f: Callable):
        super().__init__(name=name, single_execution=f"{size} iterations")
        self.size = size
        self.array_init = array_init
        self.f = f
        self.n_executions = 0
        # input arrays
        self.in_f: np.ndarray = np.zeros(size, dtype=float)
        # output arrays
        self.out_f: np.ndarray = np.zeros(size, dtype=float)
        self.out_i: np.ndarray = np.zeros(size, dtype=int)

    def _prepare_benchmark(self, n_executions: int):
        self.n_executions = n_executions
        # input array
        self.in_f = self.array_init.new_array(self.size)
        # output arrays
        self.out_f: np.ndarray = np.full(self.size, 0.0, dtype=float)
        self.out_i: np.ndarray = np.full(self.size, 0, dtype=int)

    def _run_benchmark(self):
        # call 'f' with appropriate n_executions & size parameters
        self.f(self.n_executions, self.size, self.in_f, self.out_f, self.out_i)
