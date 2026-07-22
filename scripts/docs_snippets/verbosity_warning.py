import math

from counted_float import CountedFloat, FlopCountingContext, Verbosity

cf = CountedFloat(2.5)

with FlopCountingContext(verbosity=Verbosity.WARNING):
    for _ in range(1000):
        _ = math.ldexp(cf, 3)
    _ = math.isclose(cf, 2.5)
