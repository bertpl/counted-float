from counted_float._core.benchmarking.micro import MicroBenchmark
from counted_float._core.counting import CountedFloat
from counted_float._core.models import MyBaseModel
from counted_float._core.utils import format_time_duration


# =================================================================================================
#  Result class
# =================================================================================================
class CountedFloatBenchmarkResults(MyBaseModel):
    float_time_nsec: float
    counted_float_time_nsec: float

    def show(self):
        print("CountedFloat Benchmark Results:")
        print(f"  Bisection using float        : {format_time_duration(self.float_time_nsec)} / execution")
        print(f"  Bisection using CountedFloat : {format_time_duration(self.counted_float_time_nsec)} / execution")
        ratio = self.counted_float_time_nsec / self.float_time_nsec
        print()
        print(f"CountedFloat is {ratio:.1f}x slower than float")


# =================================================================================================
#  MicroBenchmarks
# =================================================================================================
def _zero_function(x: float) -> float:
    # function for which we want to find a root
    return (x * x * x) - 7.0


class BenchmarkFloat(MicroBenchmark):
    def __init__(self):
        super().__init__(name="float")
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int):
        self._n_executions = n_executions

    def _run_benchmark(self):
        for _ in range(self._n_executions):
            # Execute bisection to find root of _zero_function in interval [-1e50,1e50],
            # using standard float() arithmetic
            a = -1e50
            b = 1e50
            fa = _zero_function(a)
            fb = _zero_function(b)
            while b - a > 1e-15:
                mid = 0.5 * (a + b)
                fmid = _zero_function(mid)
                if fmid < 0:
                    a = mid
                    fa = fmid
                else:
                    b = mid
                    fb = fmid


class BenchmarkCountedFloat(MicroBenchmark):
    def __init__(self):
        super().__init__(name="CountedFloat")
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int):
        self._n_executions = n_executions

    def _run_benchmark(self):
        for _ in range(self._n_executions):
            # Execute bisection to find root of _zero_function in interval [-1e50,1e50],
            # with identical implementation as BenchmarkFloat, except that we initialize a,b as CountedFloats,
            # which will make sure all the remaining operations are also executed using CountedFloat arithmetic
            a = CountedFloat(-1e50)
            b = CountedFloat(1e50)
            fa = _zero_function(a)
            fb = _zero_function(b)
            while b - a > 1e-15:
                mid = 0.5 * (a + b)
                fmid = _zero_function(mid)
                if fmid < 0:
                    a = mid
                    fa = fmid
                else:
                    b = mid
                    fb = fmid
